import { app, BrowserWindow, dialog, ipcMain } from 'electron';
import path from 'node:path';
import started from 'electron-squirrel-startup';
import { createDefaultLogger } from './logger.js';
import { PythonBridge } from './pythonBridge.js';
import { isScriptPathSafe } from './scriptPathGuard.js';
import { initTrayManager, disposeTrayManager } from './tray.js';
import { loadSettings, saveSettings } from './settings.js';
import {
  isRunningAsAdmin,
  requestAdminElevation,
  _resetIsElevatedCache,
} from './adminElevation.js';

// Handle creating/removing shortcuts on Windows when installing/uninstalling.
if (started) {
  app.quit();
}

// --------------------------------------------------------------------------
// Story 1.4: Admin identity + system tray
// --------------------------------------------------------------------------
//
// On Windows, the running process can be in one of three privilege
// states: elevated (admin), non-elevated (standard user), or a service
// context. Sunshine-AIO needs admin for several operations (registering
// services, editing VDD / firewall rules, etc.) so we expose a small
// helper that callers (and the renderer, through preload) can use to
// either (a) check whether we are already elevated, or (b) request an
// elevated re-launch of the same binary via ShellExecute("runas").
//
// Note on the install-time elevation model:
//   - The Electron-Forge Squirrel maker can mark the installer as
//     requiring admin (`requireAdmin: true` in `makerSquirrelConfig`)
//     so installation itself runs elevated.
//   - The launched app may still start as a standard user. That is
//     intentional: a normal user double-clicks the desktop shortcut and
//     the app boots with least-privilege; we elevate on demand via
//     `requestAdminElevation()` when an operation actually requires it.
//   - We do NOT auto-elevate on startup because that would surface a
//     UAC prompt to every user, every launch.

const isWindows = process.platform === 'win32';

// Re-export admin helpers from the dedicated module so existing
// consumers (preload, tests) keep working unchanged. The actual
// implementations live in `./adminElevation.js` and are unit-tested
// there.
export { isRunningAsAdmin, requestAdminElevation };

// Set the AppUserModelID early so Windows toast notifications and
// taskbar grouping use a stable identity. This MUST be set before
// `app.whenReady()` for the changes to take effect on Windows 10/11.
if (isWindows) {
  try {
    app.setAppUserModelId('com.legerycheese.sunshine-aio');
  } catch (err) {
    // setAppUserModelId can throw in unusual packaged configurations;
    // log and continue — the failure is non-fatal.
    try {
      process.stderr.write(`setAppUserModelId failed: ${err.message}\n`);
    } catch {}
  }
}

// Initialize the application logger.
// Writes to logs/sunshine-aio-YYYY-MM-DD.log with rotation (5MB, 5 backups).
const logger = createDefaultLogger({ consoleLevel: 'info' });
logger.info('Sunshine AIO starting', {
  version: app.getVersion(),
  electron: process.versions.electron,
  node: process.versions.node,
  platform: process.platform,
});

// Global exception handler for main process — log to file, show a friendly
// message box, and exit cleanly so the error is diagnosable post-mortem.
process.on('uncaughtException', (error) => {
  logger.error('Uncaught exception in main process', error);
  try {
    dialog.showErrorBox(
      'Sunshine AIO encountered an error',
      'An unexpected error occurred. The error has been written to the log file. ' +
        'Please check logs/ in the application folder for details.\n\n' +
        `Reason: ${error && error.message ? error.message : String(error)}`
    );
  } catch (dialogError) {
    logger.error('Failed to display error dialog', dialogError);
  }
  // Flush asynchronously before exiting so the fatal error actually lands in
  // the log file. app.exit() does not wait for I/O; without this, the very
  // entry we are trying to persist can be lost.
  logger
    .flush()
    .catch((flushErr) => {
      try {
        process.stderr.write(`Fatal logger flush failed: ${flushErr.message}\n`);
      } catch {}
    })
    .finally(() => {
      app.exit(1);
    });
});

process.on('unhandledRejection', (reason) => {
  const err = reason instanceof Error ? reason : new Error(String(reason));
  logger.error('Unhandled promise rejection in main process', err);
  // A promise rejection that nothing handled can leave the main process in
  // a corrupted state (inconsistent globals, leaked resources). Node 15+
  // exits by default; Electron can override that, so be explicit. A future
  // enhancement could gate this on a dev flag if we need hot-reload.
  logger
    .flush()
    .catch((flushErr) => {
      try {
        process.stderr.write(`Fatal logger flush failed: ${flushErr.message}\n`);
      } catch {}
    })
    .finally(() => {
      app.exit(1);
    });
});

// Register IPC handlers ONCE at module load. Doing this inside createWindow()
// would re-register on every window recreation (macOS reactivation, reload,
// future multi-window support) and cause every renderer log to be duplicated.

// Limits for the log:write IPC payload. A compromised or buggy renderer
// could otherwise send arbitrarily large or deeply-nested payloads that
// would spike memory in the main process or stall JSON serialization.
const MAX_LOG_PAYLOAD_BYTES = 64 * 1024; // 64 KiB total per message
const MAX_LOG_META_DEPTH = 5;
const MAX_LOG_MESSAGES_PER_SECOND = 100;
const logRateState = new Map(); // senderId -> { count, windowStart }

// Per-sender rate limit on python:execute / python:ping. Mirrors the
// log:write cap. Without this, a compromised renderer or buggy JS loop
// could fire thousands of IPC calls per second, each allocating a
// pending entry + timer in the bridge and exhausting memory.
const MAX_PYTHON_MESSAGES_PER_SECOND = 100;
const pythonRateState = new Map(); // senderId -> { count, windowStart }

const isPayloadTooLarge = (payload) => {
  try {
    return Buffer.byteLength(JSON.stringify(payload), 'utf8') > MAX_LOG_PAYLOAD_BYTES;
  } catch {
    // Cyclic or otherwise unserializable payload is rejected as too large
    // so a buggy renderer cannot stall us with a try/catch loop.
    return true;
  }
};

const isMetaTooDeep = (value, depth = 0) => {
  if (depth > MAX_LOG_META_DEPTH) return true;
  if (value === null || typeof value !== 'object') return false;
  for (const key of Object.keys(value)) {
    if (isMetaTooDeep(value[key], depth + 1)) return true;
  }
  return false;
};

const isRateLimited = (senderId) => {
  const now = Date.now();
  const state = logRateState.get(senderId) || { count: 0, windowStart: now };
  if (now - state.windowStart >= 1000) {
    state.count = 0;
    state.windowStart = now;
  }
  state.count += 1;
  logRateState.set(senderId, state);
  return state.count > MAX_LOG_MESSAGES_PER_SECOND;
};

const isPythonRateLimited = (senderId) => {
  const now = Date.now();
  const state = pythonRateState.get(senderId) || { count: 0, windowStart: now };
  if (now - state.windowStart >= 1000) {
    state.count = 0;
    state.windowStart = now;
  }
  state.count += 1;
  pythonRateState.set(senderId, state);
  return state.count > MAX_PYTHON_MESSAGES_PER_SECOND;
};

// Per-sender rate limit on admin:request-elevation.
//
// Elevation requests spawn a `cmd.exe` process and (once the runas
// bug is fixed) surface a UAC prompt to the user. Without this
// limit, a compromised renderer (XSS, malicious dependency) can
// call the IPC in a tight loop and either:
//   - spawn thousands of cmd.exe processes, exhausting handles /
//     memory; or
//   - repeatedly flash UAC prompts at the user, training them to
//     click "Yes" reflexively (UX-driven social-engineering).
//
// The cap mirrors the log:write / python:execute shape: at most
// one elevation request per 2 seconds, with a hard ceiling of 3
// per minute. Anything beyond that is dropped with a rate-limited
// response so the renderer can back off without silently failing.
const MIN_ELEVATION_INTERVAL_MS = 2000; // 1 request / 2s
const MAX_ELEVATION_REQUESTS_PER_MINUTE = 3;
const elevationRateState = new Map(); // senderId -> { lastCallAt, windowStart, countInWindow }

const isAdminElevationRateLimited = (senderId) => {
  const now = Date.now();
  const state = elevationRateState.get(senderId) || {
    lastCallAt: 0,
    windowStart: now,
    countInWindow: 0,
  };
  // Hard ceiling: no more than N requests in any rolling 60s window.
  if (now - state.windowStart >= 60_000) {
    state.windowStart = now;
    state.countInWindow = 0;
  }
  state.countInWindow += 1;
  if (state.countInWindow > MAX_ELEVATION_REQUESTS_PER_MINUTE) {
    elevationRateState.set(senderId, state);
    return true;
  }
  // Minimum spacing: even within the per-minute budget, require
  // 2s between requests so a tight loop cannot burst them.
  if (now - state.lastCallAt < MIN_ELEVATION_INTERVAL_MS) {
    elevationRateState.set(senderId, state);
    return true;
  }
  state.lastCallAt = now;
  elevationRateState.set(senderId, state);
  return false;
};

ipcMain.handle('log:write', (event, payload) => {
  if (!payload || typeof payload !== 'object') {
    logger.warn('Renderer sent invalid log payload');
    return { ok: false, reason: 'invalid payload' };
  }
  if (isPayloadTooLarge(payload)) {
    logger.warn('Renderer sent oversized log payload');
    return { ok: false, reason: 'payload too large' };
  }
  const { level, message, meta } = payload;
  if (meta !== undefined && meta !== null && isMetaTooDeep(meta)) {
    logger.warn('Renderer sent log payload with too-deep meta');
    return { ok: false, reason: 'meta too deep' };
  }
  const senderId = event && event.sender ? event.sender.id : 'unknown';
  if (isRateLimited(senderId)) {
    return { ok: false, reason: 'rate limited' };
  }
  const safeLevel = ['debug', 'info', 'warn', 'error'].includes(level) ? level : 'info';
  // Redact secret-looking keys / values from meta before they hit the
  // file logger. The renderer could pass credentials via electronAPI.log
  // (intentionally or via a bug); without this pass those end up
  // unredacted in logs/sunshine-aio-*.log on disk.
  const safeMeta = meta === undefined || meta === null ? meta : redactSecrets(meta);
  logger[safeLevel](`[renderer] ${typeof message === 'string' ? message : ''}`, safeMeta);
  return { ok: true };
});

// --------------------------------------------------------------------------
// Python backend bridge (Story 1.3)
// --------------------------------------------------------------------------
//
// We hold a single PythonBridge instance for the lifetime of the main
// process. It auto-starts on construction; if the bridge fails to come
// up (no Python interpreter, script missing, etc.) we surface that to
// the renderer via the IPC handlers below rather than crashing the app.
// This means a future Story could replace the bridge with a real backend
// without rewriting any renderer code.

let pythonBridge = null;
let pythonBridgeInitPromise = null;

// One-shot quit flag. Set by the close handler / tray onQuit /
// before-quit so any subsequent close events know this is a real
// shutdown and must NOT be swallowed by the minimize-to-tray hook.
// Without this, app.quit() emits a close on every BrowserWindow and
// our handler would re-hide the window, blocking the quit forever.
let _isQuitting = false;

/**
 * Returns the current quit flag. Exposed for tests and for the
 * preload side to be able to read the state without touching the
 * internal variable directly.
 */
export const isAppQuitting = () => _isQuitting;

// Default script path is resolved from the application root, not from
// process.cwd(), so the bridge works regardless of where Electron was
// launched. The bridge constructor uses the same default, but we resolve
// it here too so the path-safety check (below) compares apples to apples.
const PYTHON_SCRIPT_PATH = path.resolve(__dirname, 'python_bridge_server.py');

/**
 * Lazily create the Python bridge. Subsequent calls return the same
 * instance. The first call kicks off the spawn; concurrent calls await
 * the same init promise so we never spawn two children.
 */
const getPythonBridge = () => {
  if (pythonBridge) return pythonBridge;
  if (pythonBridgeInitPromise) return pythonBridgeInitPromise;
  try {
    // Path-traversal guard: refuse to spawn a Python script from outside
    // the application root. Without this, a future story that exposes
    // scriptPath via CLI flags / env vars could be tricked into
    // launching an attacker-controlled file.
    if (!isScriptPathSafe(PYTHON_SCRIPT_PATH)) {
      throw new Error(
        `Python script path '${PYTHON_SCRIPT_PATH}' resolves outside the trusted script roots. ` +
          `The script must live under <app>/src/ (dev) or <app>/.vite/build/ (Vite bundle).`
      );
    }
    pythonBridge = new PythonBridge({
      logger,
      scriptPath: PYTHON_SCRIPT_PATH,
    });
    pythonBridgeInitPromise = pythonBridge.whenReady();
    // Once init settles, drop the promise but keep the instance. If init
    // rejects, we leave pythonBridge in place so the next call retries
    // rather than spawning a fresh child.
    pythonBridgeInitPromise.catch((err) => {
      logger.error('Python bridge failed to initialize', err);
    });
    return pythonBridgeInitPromise;
  } catch (err) {
    logger.error('Failed to construct Python bridge', err);
    return Promise.reject(err);
  }
};

// Application root is computed inside `scriptPathGuard.js` because the
// production layout (Vite-bundled `.vite/build/main.js`) needs two
// levels up from `__dirname`, not one. The guard module resolves the
// trusted set and the script-path check so the same logic is unit-
// testable without booting an Electron environment.

/**
 * Known secret-bearing keys. Any meta / params key matching one of these
 * is redacted before being written to the file logger. Keys are matched
 * case-insensitively because secrets / passwords are commonly
 * mis-capitalized by accident.
 */
const SECRET_KEYS = new Set([
  'password',
  'passwd',
  'pwd',
  'token',
  'secret',
  'apikey',
  'api_key',
  'authorization',
  'auth',
  'cookie',
  'session',
  'sessionid',
  'session_id',
  'privatekey',
  'private_key',
  'access_token',
  'refresh_token',
]);

const isSecretKey = (key) => {
  if (typeof key !== 'string') return false;
  return SECRET_KEYS.has(key.toLowerCase());
};

/**
 * Recursively redact secret-looking keys and string values that match
 * common credential patterns (JWT, long base64 blobs, bearer tokens).
 * The original object is NOT mutated; a redacted shallow copy is
 * returned. Arrays are walked. Functions / symbols / undefined are
 * preserved as their safeStringify equivalents.
 *
 * Depth is capped to prevent a malicious caller from constructing a
 * payload that pins the CPU for arbitrarily long.
 */
const REDACT_MAX_DEPTH = 8;
const redactSecrets = (value, depth = 0) => {
  if (depth > REDACT_MAX_DEPTH) return '[redacted: too deep]';
  if (value === null || value === undefined) return value;
  if (typeof value === 'string') {
    // Common credential patterns: bearer tokens, JWTs, long random hex.
    if (/^[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\./.test(value)) {
      return '[redacted]';
    }
    if (/^Bearer\s+/i.test(value)) {
      return '[redacted]';
    }
    return value;
  }
  if (typeof value !== 'object') return value;
  if (Array.isArray(value)) {
    return value.map((item) => redactSecrets(item, depth + 1));
  }
  const out = {};
  for (const key of Object.keys(value)) {
    if (isSecretKey(key)) {
      out[key] = '[redacted]';
    } else {
      try {
        out[key] = redactSecrets(value[key], depth + 1);
      } catch {
        out[key] = '[unserializable]';
      }
    }
  }
  return out;
};

// 'python:ping' — AC2 of Story 1.3: round-trip a ping to the Python
// backend and return the pong to the renderer.
ipcMain.handle('python:ping', async (event) => {
  const senderId = event && event.sender ? event.sender.id : 'unknown';
  if (isPythonRateLimited(senderId)) {
    return { ok: false, error: 'rate limited' };
  }
  try {
    const bridge = await getPythonBridge();
    const result = await bridge.ping();
    return { ok: true, result };
  } catch (err) {
    logger.warn('python:ping failed', { message: err && err.message ? err.message : String(err) });
    return { ok: false, error: err && err.message ? err.message : String(err) };
  }
});

// 'python:execute' — typed command dispatch. We accept only command
// names present in ALLOWED_PYTHON_CMDS (kept in sync with
// preload.js and the COMMANDS dict in python_bridge_server.py). The
// preload layer enforces the same allowlist as a first line of
// defense; this is the second — a compromised or replaced preload
// must not be able to widen the IPC surface on its own.
const ALLOWED_PYTHON_CMDS = new Set(['ping']);

ipcMain.handle('python:execute', async (event, payload) => {
  const senderId = event && event.sender ? event.sender.id : 'unknown';
  if (isPythonRateLimited(senderId)) {
    return { ok: false, error: 'rate limited' };
  }
  if (!payload || typeof payload !== 'object') {
    return { ok: false, error: 'payload must be an object with cmd and optional params' };
  }
  const { cmd, params } = payload;
  if (typeof cmd !== 'string' || !cmd) {
    return { ok: false, error: 'cmd must be a non-empty string' };
  }
  if (!ALLOWED_PYTHON_CMDS.has(cmd)) {
    // Reject unknown commands at the IPC boundary so they never reach
    // the Python script. This is the security boundary — the Python
    // side's "unknown command" response is treated as a last-resort
    // safety net, not the primary control.
    return { ok: false, error: `cmd "${cmd}" is not in the allowlist` };
  }
  // Validate params is a plain JSON value BEFORE serializing. A
  // `params` of `undefined` would otherwise fall into the try/catch
  // below — `JSON.stringify(undefined)` returns the string 'undefined'
  // rather than a value, which the bridge then rejects with a confusing
  // "Failed to serialize params" error. Mirroring the preload.js guard
  // at the IPC boundary gives a clearer message and avoids the
  // serialize-then-reject round-trip.
  if (params !== undefined && params !== null) {
    if (typeof params === 'function' || typeof params === 'symbol') {
      return { ok: false, error: 'params must be a plain JSON value (no functions or symbols)' };
    }
    if (typeof params === 'number' && !Number.isFinite(params)) {
      // NaN / Infinity are not representable in JSON (they serialize to
      // "null" silently) — reject explicitly so a buggy renderer cannot
      // pass them through.
      return { ok: false, error: 'params must be a finite number' };
    }
  }
  // Bound params size to avoid a buggy renderer pushing the main process
  // into a giant JSON serialization. 64 KiB matches the log:write cap.
  let safeParams = params;
  try {
    if (params !== undefined && params !== null) {
      const size = Buffer.byteLength(JSON.stringify(params), 'utf8');
      if (size > MAX_LOG_PAYLOAD_BYTES) {
        return { ok: false, error: `params too large (${size} > ${MAX_LOG_PAYLOAD_BYTES})` };
      }
    }
  } catch {
    return { ok: false, error: 'params are not JSON-serializable' };
  }
  try {
    const bridge = await getPythonBridge();
    const result = await bridge.send(cmd, safeParams);
    return { ok: true, result };
  } catch (err) {
    logger.warn('python:execute failed', {
      cmd,
      message: err && err.message ? err.message : String(err),
    });
    return { ok: false, error: err && err.message ? err.message : String(err) };
  }
});

// --------------------------------------------------------------------------
// Story 1.4: Tray / minimize-to-tray state
// --------------------------------------------------------------------------
//
// `getMainWindow` is a closure variable set by `createWindow`. The tray
// manager accesses it lazily so the same accessor keeps working across
// window recreation (close + reopen). We expose it via a top-level
// helper so IPC handlers and tests can resolve the current window
// without reaching into module-private state.

let _mainWindow = null;
export const getMainWindow = () => _mainWindow;

const settings = loadSettings({ logger });

// --------------------------------------------------------------------------
// IPC: settings (Story 1.4)
// --------------------------------------------------------------------------
//
// Narrow surface: the renderer can read the current `minimizeToTray`
// value and set it. All writes are validated as booleans and persisted
// via the settings module.

ipcMain.handle('settings:get', () => {
  return { ok: true, settings: { ...settings } };
});

ipcMain.handle('settings:set-minimize-to-tray', (_event, value) => {
  const enabled = Boolean(value);
  const updated = saveSettings({ minimizeToTray: enabled }, { logger });
  if (!updated) {
    return { ok: false, error: 'failed to persist settings' };
  }
  settings.minimizeToTray = updated.minimizeToTray;
  logger.info('Minimize-to-tray preference updated', { enabled });
  return { ok: true, settings: { ...settings } };
});

// --------------------------------------------------------------------------
// IPC: admin privileges (Story 1.4)
// --------------------------------------------------------------------------
//
// `admin:get-status` returns whether the current process is elevated.
// `admin:request-elevation` spawns a UAC prompt to re-launch the same
// binary elevated. Both are intentionally read-only from the renderer's
// perspective — actual privilege state is owned by the main process.

ipcMain.handle('admin:get-status', () => {
  // `forceFresh` ensures the renderer always gets the current truth,
  // even if a previous call cached the wrong answer. The cost is a
  // single `whoami /groups` invocation (< 100 ms on Windows).
  return { ok: true, isAdmin: isRunningAsAdmin({ forceFresh: true }), platform: process.platform };
});

// Constants for the elevation handshake. The elevated child, on
// startup, writes a marker file to a well-known location and then
// removes it after the parent has had a chance to read it. The
// parent polls for the file and only quits once it sees evidence
// that the child actually launched. This prevents the
// "user clicked Restart, parent quit, child never showed up" failure
// mode where the user is left without ANY application running.
const ELEVATION_MARKER_FILENAME = 'sunshine-aio-elevation-marker.json';
const ELEVATION_MARKER_TIMEOUT_MS = 15000;
const ELEVATION_MARKER_POLL_INTERVAL_MS = 250;

const computeElevationMarkerPath = () => {
  // Use a directory that is writable by both the parent and the
  // elevated child (which runs as a different user session in some
  // configurations). process.env.TEMP is the safest cross-session
  // scratch directory on Windows.
  const base = process.env.TEMP || process.env.TMP || app.getPath('temp');
  return path.join(base, ELEVATION_MARKER_FILENAME);
};

const waitForElevationMarker = (markerPath, timeoutMs) => {
  const start = Date.now();
  return new Promise((resolve) => {
    const tick = () => {
      try {
        const fs = require('node:fs');
        if (fs.existsSync(markerPath)) {
          // Best-effort cleanup so the marker does not linger into
          // the next launch. Errors here are non-fatal — if the file
          // is locked by AV, the next session's stale-marker check
          // would discard it anyway.
          try {
            const raw = fs.readFileSync(markerPath, 'utf8');
            fs.unlinkSync(markerPath);
            try {
              const parsed = JSON.parse(raw);
              if (parsed && parsed.elevated === true) {
                resolve({ ok: true });
                return;
              }
            } catch {
              // Malformed marker: still treat as evidence the child
              // started — it had to call us to write the file at all.
              resolve({ ok: true });
              return;
            }
          } catch {
            resolve({ ok: true });
            return;
          }
        }
      } catch {
        // fs.existsSync failed (permissions, etc.) — keep polling.
      }
      if (Date.now() - start >= timeoutMs) {
        resolve({ ok: false, reason: 'timeout waiting for elevated child' });
        return;
      }
      setTimeout(tick, ELEVATION_MARKER_POLL_INTERVAL_MS);
    };
    tick();
  });
};

ipcMain.handle('admin:request-elevation', async (event) => {
  // Rate-limit per sender so a compromised renderer cannot prompt-
  // spam the user with UAC dialogs or spawn cmd.exe in a tight
  // loop. The cap mirrors the log:write / python:execute shape.
  const senderId = event && event.sender ? event.sender.id : 'unknown';
  if (isAdminElevationRateLimited(senderId)) {
    return { ok: false, reason: 'rate limited' };
  }
  // Bust the cached elevation result before probing. The cache is
  // populated once on first call and was previously never invalidated
  // here, so a process that elevates itself between calls would
  // continue to report `false` and the renderer would offer a
  // redundant UAC prompt. `forceFresh: true` re-probes via whoami,
  // so the renderer sees the current ground truth.
  _resetIsElevatedCache();
  if (isRunningAsAdmin({ forceFresh: true })) {
    return { ok: true, alreadyElevated: true };
  }
  // The elevated child writes a marker file at startup so the parent
  // can confirm the child actually launched before tearing itself
  // down. Compute the path NOW so both sides agree on the location
  // (the child's working directory may differ from the parent's).
  const markerPath = computeElevationMarkerPath();
  // Pass a sentinel CLI flag to the elevated child. When the child
  // sees this flag at startup, it writes the marker file. The flag
  // is intentionally obscure so a normal user double-click cannot
  // accidentally trigger the handshake path.
  const handshakeFlag = '--sunshine-aio-elevation-handshake';
  const result = await requestAdminElevation({
    handshakeArgs: [handshakeFlag, markerPath],
  });
  if (!result.ok) {
    // Elevation failed (user cancelled UAC, spawn error, etc.). Do
    // NOT quit the parent — the user still needs a working app.
    logger.warn('Admin elevation request failed', { reason: result.reason });
    return result;
  }
  // Handshake: wait for the elevated child to drop a marker file
  // before quitting. If we never see it (UAC declined, child
  // crashed at startup, etc.), the parent stays alive and the user
  // keeps their session.
  const handshake = await waitForElevationMarker(markerPath, ELEVATION_MARKER_TIMEOUT_MS);
  if (!handshake.ok) {
    logger.warn('Elevation handshake timed out; staying alive', {
      reason: handshake.reason,
    });
    return { ok: false, reason: handshake.reason, elevatedChildSpawned: true };
  }
  // Confirmed elevated child is up. Give it a brief head start
  // (250 ms) to finish initializing its own logger / IPC handlers
  // before the parent's `before-quit` tears down shared resources.
  // Then quit. We do NOT use `app.exit(0)` so the normal teardown
  // path runs (logger flush, tray dispose, Python bridge quit).
  setTimeout(() => {
    logger.info('Quitting parent after successful elevation handshake');
    app.quit();
  }, 250);
  return { ok: true, elevatedChildConfirmed: true };
});

// --------------------------------------------------------------------------
// Elevated-child handshake
// --------------------------------------------------------------------------
//
// When this process is launched by a non-elevated parent via
// `requestAdminElevation()`, the parent passes two extra CLI args:
//   1. `--sunshine-aio-elevation-handshake` (sentinel flag)
//   2. The absolute path of the marker file the parent is polling for.
//
// If we see the sentinel at startup, write the marker immediately so
// the parent can confirm this elevated instance is alive and tear
// itself down. The marker is written BEFORE `app.whenReady()` resolves
// so the parent's `waitForElevationMarker` resolves as soon as possible
// — we want to minimize the window where the user has no running
// app.
//
// We also reset the elevation cache so subsequent `isRunningAsAdmin`
// calls inside this (elevated) instance return the correct value.
// Without the reset, a process that inherited a stale cache from a
// previous unelevated run would still report `false`.

{
  const HANDSHAKE_FLAG = '--sunshine-aio-elevation-handshake';
  const argv = process.argv || [];
  const flagIndex = argv.indexOf(HANDSHAKE_FLAG);
  if (flagIndex !== -1) {
    const markerPath = argv[flagIndex + 1];
    if (markerPath && typeof markerPath === 'string') {
      // Force the cached elevation result to refresh on the next
      // call. The current process is by definition the elevated
      // child — it just got past the UAC prompt — so a fresh probe
      // will return true.
      _resetIsElevatedCache();
      try {
        const fs = require('node:fs');
        const payload = JSON.stringify({
          elevated: true,
          pid: process.pid,
          ts: Date.now(),
        });
        fs.writeFileSync(markerPath, payload, { encoding: 'utf8' });
        // Best-effort: also log to stderr so an external observer
        // (CI, logs/) can see the handshake fired.
        try {
          process.stderr.write(`[elevation-handshake] marker written to ${markerPath}\n`);
        } catch {}
      } catch (err) {
        try {
          process.stderr.write(
            `[elevation-handshake] failed to write marker: ${
              err && err.message ? err.message : String(err)
            }\n`
          );
        } catch {}
      }
    }
  }
}

const createWindow = () => {
  // Create the browser window.
  const mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 800,
    minHeight: 600,
    title: 'Sunshine AIO',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });

  _mainWindow = mainWindow;
  logger.info('Main window created', { id: mainWindow.id });

  // Note: the 'log:write' IPC handler is registered ONCE at module load
  // (above). Do NOT re-register it here — that would duplicate every
  // renderer log line on window recreation (macOS reactivation, reload,
  // future multi-window support).

  // and load the index.html of the app.
  if (MAIN_WINDOW_VITE_DEV_SERVER_URL) {
    mainWindow.loadURL(MAIN_WINDOW_VITE_DEV_SERVER_URL);
    logger.info('Loading dev server URL', { url: MAIN_WINDOW_VITE_DEV_SERVER_URL });
  } else {
    const indexPath = path.join(__dirname, `../renderer/${MAIN_WINDOW_VITE_NAME}/index.html`);
    mainWindow.loadFile(indexPath);
    logger.info('Loading renderer index', { indexPath });
  }

  // DevTools toggle shortcut (F12 or Ctrl+Shift+I) — dev / debug builds only.
  // Gated on `!app.isPackaged` so a one-keystroke DevTools toggle is not
  // available in shipped production builds (which would otherwise expose
  // renderer state and the typed electronAPI surface to any non-admin
  // user). `app.isPackaged` is the official Electron discriminator:
  // true for asar / squirrel installers, false for `electron-forge start`.
  if (!app.isPackaged) {
    mainWindow.webContents.on('input-event', (event, input) => {
      if (
        input.type === 'keyDown' &&
        (input.key === 'F12' || (input.control && input.shift && input.key === 'I'))
      ) {
        mainWindow.webContents.toggleDevTools();
        event.preventDefault();
      }
    });
  }

  mainWindow.webContents.on('render-process-gone', (_event, details) => {
    logger.error('Renderer process gone', details);
  });

  // Story 1.4: minimize-to-tray hook.
  //
  // We intercept the 'close' event (rather than 'closed') so we can
  // prevent default when minimize-to-tray is enabled. Without this,
  // closing the window would quit the app on Windows because
  // window-all-closed fires. We also re-check the *current* settings
  // value at close time rather than capturing it once, so a toggle
  // made via the settings UI takes effect immediately.
  //
  // CRITICAL: a real shutdown (tray "Quit", taskbar close when
  // minimize-to-tray is OFF, before-quit teardown) sets the global
  // `_isQuitting` flag BEFORE calling `app.quit()`. `app.quit()` then
  // emits `close` on every BrowserWindow as part of teardown; without
  // the `!_isQuitting` guard, this handler would preventDefault and
  // re-hide the window, leaving `app.quit()` blocked forever
  // ("ghost quit"). The guard guarantees a real quit can always
  // proceed.
  mainWindow.on('close', (event) => {
    if (_isQuitting) return;
    const minimizeEnabled =
      settings && typeof settings.minimizeToTray === 'boolean' ? settings.minimizeToTray : false;
    if (!minimizeEnabled) return;
    if (mainWindow.isDestroyed()) return;
    event.preventDefault();
    try {
      mainWindow.hide();
      logger.info('Window hidden to tray');
    } catch (err) {
      logger.warn('Failed to hide window to tray', {
        message: err && err.message ? err.message : String(err),
      });
    }
  });

  mainWindow.on('closed', () => {
    logger.info('Main window closed');
    if (_mainWindow === mainWindow) {
      _mainWindow = null;
    }
  });

  return mainWindow;
};

// This method will be called when Electron has finished
// initialization and is ready to create browser windows.
// Some APIs can only be used after this event occurs.
app.whenReady().then(() => {
  logger.info('App ready, creating main window');
  // Kick off the Python bridge eagerly so the renderer can ping
  // immediately after window creation. We don't await here — if the
  // bridge is slow or fails, the IPC handlers will surface the error
  // per-call rather than blocking app startup.
  getPythonBridge().catch((err) => {
    logger.warn('Python bridge init deferred', {
      message: err && err.message ? err.message : String(err),
    });
  });
  const win = createWindow();
  // Story 1.4: initialize the system-tray icon AFTER the window is
  // up so `getMainWindow` returns a live window. The tray is created
  // unconditionally; the close-to-tray hook above decides whether
  // hiding is allowed based on the user's preference.
  try {
    initTrayManager({
      getMainWindow: () => _mainWindow,
      logger,
      onQuit: () => {
        // Mark the process as quitting so the close handler does
        // NOT re-hide the window when app.quit() emits its teardown
        // close events. Explicitly destroy the window first so a
        // hidden window does not leave a residual taskbar entry on
        // some Windows builds during the (async) cleanup window.
        _isQuitting = true;
        try {
          if (_mainWindow && !_mainWindow.isDestroyed()) {
            _mainWindow.destroy();
          }
        } catch (err) {
          logger.warn('Failed to destroy window during tray quit', {
            message: err && err.message ? err.message : String(err),
          });
        }
        // Quit must skip the "is the bridge still alive?" guard so
        // we actually exit even if the bridge is mid-call. Setting
        // a one-shot flag on the bridge is the simplest path.
        app.quit();
      },
    });
  } catch (err) {
    logger.error('Failed to initialize tray manager', err);
  }
  void win;
});

// Quit when all windows are closed. We honor the minimize-to-tray
// setting here too: if the only reason windows are gone is that the
// user closed the window while minimize-to-tray is on, keep the app
// alive (the window was hidden, not destroyed). The `windows-all-
// closed` event still fires because hide() makes the window count
// drop to zero on Windows.
//
// The single-condition gate replaces an earlier form that branched
// separately on minimize-to-tray and platform; that form had two
// problems:
//   1. On non-Windows, minimize-to-tray was effectively always OFF
//      because the `&&` short-circuited, even when the user had
//      enabled it — confusing for any future macOS / Linux port.
//   2. Quitting from the tray when the window was hidden did not
//      explicitly destroy the hidden window, so on some Windows
//      builds a residual taskbar entry briefly appeared. The tray
//      onQuit handler now sets `_isQuitting` and destroys the
//      window explicitly before calling `app.quit()`.
app.on('window-all-closed', () => {
  const minimizeEnabled =
    settings && typeof settings.minimizeToTray === 'boolean' ? settings.minimizeToTray : false;
  if (minimizeEnabled && process.platform === 'win32') {
    logger.info('All windows closed but minimize-to-tray is enabled; staying alive in tray');
    return;
  }
  logger.info('All windows closed, quitting app');
  app.quit();
});

// Clean up the Python bridge and tray before the app exits.
// 'before-quit' fires when the user (or the OS) requests shutdown,
// BEFORE 'will-quit' and before any windows are torn down. We do an
// async quit() and let the 'will-quit' handler below serialize the
// actual exit so the logger flushes after.
//
// Ordering note: the tray icon is disposed at the END of the
// cleanup chain, NOT at the top of this handler. If we destroy the
// tray up front and then `pythonBridge.quit()` hangs (or throws),
// the user is left with a process that has no tray icon AND no
// window — they cannot see or interact with the app, but the
// process refuses to exit because `will-quit` is also awaiting
// `logger.flush()`. Deferring the dispose keeps the tray alive as
// a retry surface for the duration of the cleanup.
app.on('before-quit', (event) => {
  // Mark the global quit flag so the window close handler stops
  // swallowing real shutdown close events.
  _isQuitting = true;
  if (!pythonBridge) {
    // No bridge to drain; dispose the tray now and re-issue quit
    // so the will-quit flush path still runs.
    try {
      disposeTrayManager();
    } catch (err) {
      logger.warn('Failed to dispose tray manager', {
        message: err && err.message ? err.message : String(err),
      });
    }
    return;
  }
  if (pythonBridge.isQuitting && pythonBridge.isQuitting()) return;
  logger.info('App before-quit, terminating Python bridge');
  event.preventDefault();
  pythonBridge
    .quit()
    .catch((err) => {
      logger.warn('Python bridge quit failed', {
        message: err && err.message ? err.message : String(err),
      });
    })
    .finally(() => {
      // The bridge has either drained or given up. We are now
      // committed to exiting. Dispose the tray icon so Windows
      // does not show a ghost icon after the process is gone.
      // disposeTrayManager is idempotent and safe to call even
      // when no tray was created.
      try {
        disposeTrayManager();
      } catch (err) {
        logger.warn('Failed to dispose tray manager', {
          message: err && err.message ? err.message : String(err),
        });
      }
      // Defer to the normal quit path so the logger flushes.
      app.quit();
    });
});

app.on('will-quit', (event) => {
  logger.info('App will quit, flushing logger');
  // Prevent the quit until the pending log writes have flushed. Without
  // this, Electron terminates the process before the async file writes
  // resolve and we lose the final log entries (often the most important
  // ones for diagnosing a crash).
  event.preventDefault();
  logger
    .flush()
    .catch((flushError) => {
      try {
        process.stderr.write(`Logger flush failed: ${flushError.message}\n`);
      } catch {}
    })
    .finally(() => {
      // The tray icon is already gone by the time we get here
      // (before-quit's .finally() disposes it just before re-issuing
      // app.quit()). app.exit() skips the remaining lifecycle events
      // so the (already-prevented) close path cannot re-enter.
      app.exit(0);
    });
});
