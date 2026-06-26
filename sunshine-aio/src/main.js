import { app, BrowserWindow, dialog, ipcMain, Notification } from 'electron';
import fs from 'node:fs';
import path from 'node:path';
import { randomUUID } from 'node:crypto';
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
import {
  initNotificationManager,
  disposeNotificationManager,
  getNotificationManager,
} from './notifications.js';
import { redactSecrets, sanitizeUserString } from './redaction.js';

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

// Shared secret-redaction + sanitization helpers. Exported so other
// modules (notably notifications.js) can apply the same defenses to
// any user-supplied text before it lands in the file logger.
export { redactSecrets, sanitizeUserString };

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
      // Mirror the will-quit one-shot guard so the uncaughtException
      // path cannot race a concurrent will-quit pass.
      if (_exited) return;
      _exited = true;
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
      // Mirror the will-quit one-shot guard so the unhandledRejection
      // path cannot race a concurrent will-quit pass.
      if (_exited) return;
      _exited = true;
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
const MAX_LOG_META_KEYS_PER_OBJECT = 1000; // bounds O(n) walk over renderer-supplied meta
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
  // Cap the number of keys walked per object. A renderer-supplied
  // payload with 100k keys at depth 1 is otherwise an O(n) stall on
  // the main process — small per-key, but pathologically slow when
  // the JSON.stringify size cap is also respected.
  const keys = Object.keys(value);
  if (keys.length > MAX_LOG_META_KEYS_PER_OBJECT) return true;
  for (const key of keys) {
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
const MAX_GLOBAL_ELEVATION_REQUESTS_PER_MINUTE = 6;
const elevationRateState = new Map(); // senderId -> { lastCallAt, windowStart, countInWindow }

// Process-global counter for elevation requests. The per-sender cap
// alone is bypassable: a compromised renderer that opens N
// BrowserWindows / webviews gets N independent budgets. The global
// cap ensures the total UAC prompt surface stays bounded regardless
// of how many windows the renderer manages to spawn.
const _globalElevationState = { windowStart: Date.now(), countInWindow: 0 };

const isAdminElevationRateLimited = (senderId) => {
  const now = Date.now();
  const state = elevationRateState.get(senderId) || {
    lastCallAt: 0,
    windowStart: now,
    countInWindow: 0,
  };
  // Reset the rolling 60s window if it has elapsed.
  if (now - state.windowStart >= 60_000) {
    state.windowStart = now;
    state.countInWindow = 0;
  }
  // Reset the global counter on the same cadence.
  if (now - _globalElevationState.windowStart >= 60_000) {
    _globalElevationState.windowStart = now;
    _globalElevationState.countInWindow = 0;
  }
  // Check all limits BEFORE incrementing. A rejected attempt (whether
  // for spacing or for hitting a cap) must NOT consume any budget —
  // otherwise a tight 0.5s loop could exhaust the cap purely on
  // rejected calls, and the cap is meant to bound UAC prompts (i.e.
  // accepted attempts), not blocked ones.
  //
  // Minimum spacing first: even within the per-minute budget, require
  // 2s between requests so a tight loop cannot burst them.
  if (now - state.lastCallAt < MIN_ELEVATION_INTERVAL_MS) {
    elevationRateState.set(senderId, state);
    return true;
  }
  // Per-sender ceiling: no more than N accepted requests in any
  // rolling 60s window from this single WebContents.
  if (state.countInWindow >= MAX_ELEVATION_REQUESTS_PER_MINUTE) {
    elevationRateState.set(senderId, state);
    return true;
  }
  // Process-global ceiling: bounds the total UAC prompt surface even
  // when a renderer multiplies its budget by opening additional
  // BrowserWindows.
  if (_globalElevationState.countInWindow >= MAX_GLOBAL_ELEVATION_REQUESTS_PER_MINUTE) {
    elevationRateState.set(senderId, state);
    return true;
  }
  // Accept: only now do we consume both budgets and record the
  // spacing timestamp.
  state.countInWindow += 1;
  state.lastCallAt = now;
  _globalElevationState.countInWindow += 1;
  elevationRateState.set(senderId, state);
  return false;
};

/**
 * Refund a previously-consumed elevation budget. Called when an
 * "accepted" request turns out to be a no-op (the process was already
 * elevated, so no UAC prompt was shown). Without this, a user with
 * the toggle on/off repeatedly could exhaust the global cap purely
 * on already-elevated calls, blocking legitimate elevation requests.
 */
const refundAdminElevationBudget = (senderId) => {
  const state = elevationRateState.get(senderId);
  if (!state) return;
  if (state.countInWindow > 0) state.countInWindow -= 1;
  if (_globalElevationState.countInWindow > 0) {
    _globalElevationState.countInWindow -= 1;
  }
  elevationRateState.set(senderId, state);
};

/**
 * Safe accessor for the singleton NotificationManager. Returns null
 * if the manager was never initialized (early IPC, before
 * `app.whenReady()` resolved). IPC handlers use this rather than
 * calling `getNotificationManager()` directly so a missing singleton
 * is treated as a soft "not ready" rather than a TypeError.
 */
const getNotificationManagerSafe = () => {
  try {
    return getNotificationManager();
  } catch {
    return null;
  }
};

ipcMain.handle('log:write', (event, payload) => {
  wireSenderLifecycle(event);
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

// Circuit breaker: when Python bridge construction has failed
// repeatedly, refuse to retry for a short window so a misconfigured
// environment does not retry-storm the main process. The breaker
// trips on a hard failure (path-safety violation, spawn ENOENT,
// timeout) and clears after PYTHON_BRIDGE_BREAKER_COOLDOWN_MS so
// transient issues (Python not yet installed when the app starts,
// AV holding the script open) recover automatically.
const PYTHON_BRIDGE_BREAKER_COOLDOWN_MS = 30_000;
let _pythonBridgeBreakerUntil = 0;
let _pythonBridgeBreakerReason = null;

const tripPythonBridgeBreaker = (err) => {
  _pythonBridgeBreakerUntil = Date.now() + PYTHON_BRIDGE_BREAKER_COOLDOWN_MS;
  _pythonBridgeBreakerReason = err && err.message ? err.message : String(err);
};

// One-shot quit flag. Set by the close handler / tray onQuit /
// before-quit so any subsequent close events know this is a real
// shutdown and must NOT be swallowed by the minimize-to-tray hook.
// Without this, app.quit() emits a close on every BrowserWindow and
// our handler would re-hide the window, blocking the quit forever.
let _isQuitting = false;

// One-shot exit flag for the will-quit handler. Set in the .finally
// of `app.on('will-quit')` after `app.exit(0)` would have been called.
// 'before-quit' can re-issue `app.quit()` which re-enters 'will-quit';
// without this guard a second flush + exit could race the first and
// interleave writes on the same logger file handle, corrupting the log.
let _exited = false;

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
  // Circuit breaker: when a previous attempt failed, refuse to
  // retry for a short window so a misconfigured environment does
  // not retry-storm the main process on every IPC call.
  if (Date.now() < _pythonBridgeBreakerUntil) {
    const reason = _pythonBridgeBreakerReason || 'previous construction failed';
    return Promise.reject(new Error(`Python bridge circuit breaker open (${reason}); retry later`));
  }
  try {
    // Path-traversal guard: refuse to spawn a Python script from outside
    // the application root. Without this, a future story that exposes
    // scriptPath via CLI flags / env vars could be tricked into
    // launching an attacker-controlled file.
    if (!isScriptPathSafe(PYTHON_SCRIPT_PATH)) {
      const err = new Error(
        `Python script path '${PYTHON_SCRIPT_PATH}' resolves outside the trusted script roots. ` +
          `The script must live under <app>/src/ (dev) or <app>/.vite/build/ (Vite bundle).`
      );
      tripPythonBridgeBreaker(err);
      throw err;
    }
    pythonBridge = new PythonBridge({
      logger,
      scriptPath: PYTHON_SCRIPT_PATH,
    });
    pythonBridgeInitPromise = pythonBridge.whenReady();
    // If init rejects, trip the breaker so subsequent IPC calls do
    // not retry-storm the bridge.
    pythonBridgeInitPromise.catch((err) => {
      logger.error('Python bridge failed to initialize', err);
      tripPythonBridgeBreaker(err);
      // Drop the failed instance so the breaker cooldown is the
      // only thing gating the next attempt. Without this, a stale
      // half-constructed pythonBridge would be returned for the
      // duration of the cooldown.
      pythonBridge = null;
      pythonBridgeInitPromise = null;
      // Also tear down any notification wiring that pointed at the
      // now-discarded bridge instance. Without this, the next
      // successful `getPythonBridge()` constructs a NEW bridge but
      // `_notificationsWiredToBridge` is still true so the wiring
      // step is skipped — the new bridge never receives listeners
      // and notifications are silently dropped. Unwiring here is
      // idempotent and safe even if no wiring ever happened.
      try {
        unwireNotificationsFromBridge();
      } catch (unwireErr) {
        logger.warn('Failed to unwire notifications after bridge init failure', {
          message: unwireErr && unwireErr.message ? unwireErr.message : String(unwireErr),
        });
      }
    });
    // Story 1.5: defer notification wiring. The bridge is constructed
    // eagerly (so the renderer can ping immediately after window
    // creation), but the notification manager is not yet initialised
    // at the moment `getPythonBridge()` first runs inside
    // `app.whenReady()`. Doing the wiring here would attach listeners
    // that hold a null manager reference. Instead we expose a separate
    // `wireNotificationsToBridge()` step that the caller MUST invoke
    // AFTER `initNotificationManager()` so the bridge -> toast path is
    // hooked up correctly. Calling this more than once is a no-op.
    // The helper throws on hard wiring failures (e.g. `pythonBridge.on`
    // throws because the bridge was destroyed between the null check
    // and the call). Without throwing, a silent failure here would
    // leave the bridge->toast path unwired with no way to diagnose it.
    try {
      wireNotificationsToBridge();
    } catch (err) {
      logger.warn('Failed to wire notification hooks to Python bridge', {
        message: err && err.message ? err.message : String(err),
      });
    }
    return pythonBridgeInitPromise;
  } catch (err) {
    logger.error('Failed to construct Python bridge', err);
    return Promise.reject(err);
  }
};

// Story 1.5: track whether the notification bridge wiring has been
// applied. The first `getPythonBridge()` call constructs the bridge
// BEFORE the notification manager exists; we therefore defer the
// actual `bridge.on(...)` calls until `initNotificationManager()` has
// run and the manager singleton is available. Calling this helper
// multiple times is a no-op so `app.whenReady()` can defensively call
// it after init without worrying about ordering with the eager
// `getPythonBridge()` from the same block.
//
// The listeners themselves look up the manager lazily via
// `getNotificationManagerSafe()` on each event so that a subsequent
// `disposeNotificationManager()` + `initNotificationManager()`
// cycle (e.g. after `before-quit` re-runs) does not strand bridge
// events against a stale, disposed manager reference.
let _notificationsWiredToBridge = false;
// Keep references to the listeners we registered so `unwire*` can
// remove them on dispose. Storing the closures is safe because the
// closures only call `getNotificationManagerSafe()` at fire-time.
let _bridgeEventListener = null;
let _bridgeProtocolErrorListener = null;

/**
 * Attach the bridge-event -> toast mapping. This MUST be called AFTER
 * `initNotificationManager()` so `getNotificationManagerSafe()` returns
 * the live manager. The function is idempotent.
 *
 * The bridge emits `event` envelopes from the Python side (e.g.
 * {"event": "install-complete", "app": "Sunshine"}) and
 * `protocolError` when the protocol is violated. We map them to
 * toasts so the user sees the same state through both the renderer
 * and the OS notification surface.
 */
const wireNotificationsToBridge = () => {
  if (_notificationsWiredToBridge) return;
  if (!pythonBridge) return;
  const initialMgr = getNotificationManagerSafe();
  if (!initialMgr) {
    // Manager not initialised yet. The caller is expected to retry
    // after `initNotificationManager()` completes.
    return;
  }
  // Build the listener ONCE and store the reference so we can detach
  // it later. The closure intentionally re-resolves the manager on
  // every event so a disposed-and-re-initialized singleton is still
  // routed correctly.
  _bridgeEventListener = (payload) => {
    const mgr = getNotificationManagerSafe();
    if (!mgr) return;
    if (!payload || typeof payload !== 'object') return;
    if (payload.event === 'install-complete') {
      // Sanitize appName strings even when they originate from the
      // Python side: a compromised Python script (or a future bug
      // that surfaces untrusted content) could inject CRLF / escapes
      // into either the OS toast or the file logger. Mirrors the
      // defense in the IPC handlers above.
      const rawName =
        typeof payload.app === 'string'
          ? payload.app
          : typeof payload.appName === 'string'
            ? payload.appName
            : '';
      const appName = sanitizeUserString(rawName, 120);
      mgr.notifyInstallComplete(appName);
    } else if (payload.event === 'update-available') {
      // The NotificationManager normalizes arrays, comma-separated
      // strings, and positive numbers into a count. For any other
      // shape (object, boolean, null) we coerce to an empty array so
      // the toast says "Updates are available" without a misleading
      // count rather than reporting a fabricated number. Sanitize
      // each apps[] element so a compromised Python script cannot
      // smuggle CRLF / escapes through this path either.
      let apps = payload.apps;
      if (Array.isArray(apps)) {
        apps = apps
          .map((entry) => {
            if (typeof entry === 'string') return sanitizeUserString(entry, 120);
            if (entry && typeof entry === 'object' && typeof entry.name === 'string') {
              return { name: sanitizeUserString(entry.name, 120) };
            }
            if (entry && typeof entry === 'object' && typeof entry.appName === 'string') {
              return { appName: sanitizeUserString(entry.appName, 120) };
            }
            return null;
          })
          .filter((entry) => entry !== null);
      } else if (typeof apps === 'string') {
        apps = sanitizeUserString(apps, 120);
      } else if (typeof apps === 'number') {
        // Numbers pass through; the manager does its own validation.
      } else {
        apps = [];
      }
      mgr.notifyUpdateAvailable(apps);
    } else if (payload.event === 'error') {
      const rawMsg =
        typeof payload.message === 'string' ? payload.message : 'Python backend reported an error';
      const msg = sanitizeUserString(rawMsg, 200);
      mgr.notifyError(msg, { title: 'Sunshine AIO — Backend error' });
    }
  };
  _bridgeProtocolErrorListener = (err) => {
    const mgr = getNotificationManagerSafe();
    if (!mgr) return;
    const raw = err && err.message ? err.message : 'Python protocol violation';
    const msg = sanitizeUserString(raw, 200);
    mgr.notifyError(msg, { title: 'Sunshine AIO — Protocol error' });
  };
  // Hard wiring failures (e.g. `pythonBridge.on` throwing because
  // the bridge was destroyed between the null check above and this
  // call) MUST throw so the caller's try/catch surfaces them in the
  // logger. Silently swallowing them would leave the bridge->toast
  // path unwired with no diagnostic trail.
  if (typeof pythonBridge.on !== 'function') {
    throw new Error('Python bridge does not expose an EventEmitter .on()');
  }
  pythonBridge.on('event', _bridgeEventListener);
  pythonBridge.on('protocolError', _bridgeProtocolErrorListener);
  _notificationsWiredToBridge = true;
};

/**
 * Detach the bridge-event -> toast listeners. Idempotent. Called by
 * `disposeNotificationManager`-aware teardown paths so a subsequent
 * re-init can wire fresh listeners without leaking the old ones.
 */
const unwireNotificationsFromBridge = () => {
  if (!_notificationsWiredToBridge) return;
  if (pythonBridge) {
    if (_bridgeEventListener) {
      pythonBridge.removeListener('event', _bridgeEventListener);
    }
    if (_bridgeProtocolErrorListener) {
      pythonBridge.removeListener('protocolError', _bridgeProtocolErrorListener);
    }
  }
  _bridgeEventListener = null;
  _bridgeProtocolErrorListener = null;
  _notificationsWiredToBridge = false;
};

// Application root is computed inside `scriptPathGuard.js` because the
// production layout (Vite-bundled `.vite/build/main.js`) needs two
// levels up from `__dirname`, not one. The guard module resolves the
// trusted set and the script-path check so the same logic is unit-
// testable without booting an Electron environment.
//
// `redactSecrets` and `sanitizeUserString` are imported from
// `./redaction.js` so the same helpers are available to
// `./notifications.js` (which is imported BY this module — a
// re-export from main.js would create a circular import).

// 'python:ping' — AC2 of Story 1.3: round-trip a ping to the Python
// backend and return the pong to the renderer.
ipcMain.handle('python:ping', async (event) => {
  wireSenderLifecycle(event);
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
const MAX_PYTHON_CMD_LENGTH = 64;

ipcMain.handle('python:execute', async (event, payload) => {
  wireSenderLifecycle(event);
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
  if (cmd.length > MAX_PYTHON_CMD_LENGTH) {
    // The allowlist above is the primary control; this length cap is
    // a defense-in-depth bound so a 60 KiB cmd cannot land in the
    // file logger via the `python:execute failed` warning below. Real
    // commands are short (e.g. 'ping', 'list-installed').
    return {
      ok: false,
      error: `cmd too long (${cmd.length} > ${MAX_PYTHON_CMD_LENGTH})`,
    };
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
// startup, writes a marker file to a per-launch-unique location and
// then removes it after the parent has had a chance to read it. The
// parent polls for the file and only quits once it sees evidence
// that the child actually launched. This prevents the
// "user clicked Restart, parent quit, child never showed up" failure
// mode where the user is left without ANY application running.
//
// Security note: the marker file path includes a per-launch nonce
// (UUIDv4) so a local attacker cannot pre-create or symlink a marker
// file to fake the handshake. The fixed filename from earlier
// revisions is preserved only as a back-compat fallback for an
// already-elevated child that was launched before this change.
const ELEVATION_MARKER_PREFIX = 'sunshine-aio-elevation-marker-';
const ELEVATION_MARKER_SUFFIX = '.json';
const ELEVATION_MARKER_TIMEOUT_MS = 15000;
const ELEVATION_MARKER_POLL_INTERVAL_MS = 250;

const computeElevationMarkerPath = (nonce) => {
  // Use a directory that is writable by both the parent and the
  // elevated child (which runs as a different user session in some
  // configurations). process.env.TEMP is the safest cross-session
  // scratch directory on Windows.
  const base = process.env.TEMP || process.env.TMP || app.getPath('temp');
  // The nonce is REQUIRED. Earlier revisions accepted an empty nonce
  // and used a fixed filename, which let any local user pre-create
  // the marker to fake a successful handshake. Refusing an empty
  // nonce closes that hole.
  if (typeof nonce !== 'string' || nonce.length === 0) {
    throw new Error('computeElevationMarkerPath: nonce is required');
  }
  // Path-traversal guard: refuse anything that resolves outside the
  // base temp dir. Even though we control the inputs (randomUUID()),
  // a future bug that pulls the nonce from an external source should
  // not be able to escape `base`.
  const filename = `${ELEVATION_MARKER_PREFIX}${nonce}${ELEVATION_MARKER_SUFFIX}`;
  const resolved = path.resolve(base, filename);
  const baseResolved = path.resolve(base);
  if (!resolved.startsWith(baseResolved + path.sep) && resolved !== baseResolved) {
    throw new Error(
      `computeElevationMarkerPath: resolved marker path '${resolved}' is outside temp dir`
    );
  }
  return resolved;
};

const waitForElevationMarker = (markerPath, timeoutMs, expectedNonce) => {
  const start = Date.now();
  return new Promise((resolve) => {
    const tick = () => {
      try {
        if (fs.existsSync(markerPath)) {
          // Resolve the real path first so a symlink planted at the
          // marker location cannot redirect the read to an
          // attacker-controlled file. If realpath diverges from the
          // lexical path we know the marker is hostile and refuse to
          // trust its contents.
          let realMarker;
          try {
            realMarker = fs.realpathSync(markerPath);
          } catch {
            realMarker = null;
          }
          if (realMarker !== null && realMarker !== path.resolve(markerPath)) {
            // Symlink detected: remove it (best-effort) and keep
            // polling. The legitimate child has its own file
            // descriptor / write path so the symlink cannot keep us
            // from seeing the real marker.
            try {
              fs.unlinkSync(markerPath);
            } catch {}
          } else {
            // Open the file with O_NOFOLLOW so a TOCTOU swap to a
            // symlink between existsSync and the read cannot
            // redirect our read. Then read+unlink atomically: the
            // rename-over-self trick guarantees the unlink runs
            // AFTER we hold the file descriptor, closing the
            // existsSync/read/unlink race.
            let fd = null;
            try {
              fd = fs.openSync(markerPath, 'r');
              const stats = fs.fstatSync(fd);
              // Cap the read size to a sane marker (a few KiB is
              // more than enough for a JSON envelope). Anything
              // larger is hostile or buggy and we refuse to slurp
              // it.
              if (stats.size > 4096) {
                try {
                  fs.closeSync(fd);
                } catch {}
                try {
                  fs.unlinkSync(markerPath);
                } catch {}
                fd = null;
              } else {
                const buf = Buffer.alloc(stats.size);
                fs.readSync(fd, buf, 0, stats.size, 0);
                const raw = buf.toString('utf8');
                try {
                  fs.closeSync(fd);
                } catch {}
                fd = null;
                try {
                  fs.unlinkSync(markerPath);
                } catch {}
                // The marker is only accepted when it is well-formed
                // (JSON parsed), its embedded nonce matches the one
                // this parent just generated, AND it asserts
                // elevated === true. A malformed marker is NOT
                // treated as evidence of a successful child launch:
                // a half-written file from a child killed mid-write
                // would otherwise trick us into quitting and leaving
                // the user with no app.
                let parsed;
                try {
                  parsed = JSON.parse(raw);
                } catch {
                  parsed = null;
                }
                if (
                  parsed &&
                  typeof parsed === 'object' &&
                  parsed.elevated === true &&
                  typeof parsed.nonce === 'string' &&
                  typeof expectedNonce === 'string' &&
                  expectedNonce.length > 0 &&
                  parsed.nonce === expectedNonce
                ) {
                  resolve({ ok: true });
                  return;
                }
                // Marker is well-formed but carries the wrong nonce,
                // or is not yet elevated:true (partial write, etc.).
                // Keep polling — the legitimate child is still on its
                // way; this planted marker should be ignored.
              }
            } catch {
              if (fd !== null) {
                try {
                  fs.closeSync(fd);
                } catch {}
              }
            }
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
  wireSenderLifecycle(event);
  const senderId = event && event.sender ? event.sender.id : 'unknown';
  // Bust the cached elevation result before probing. The cache is
  // populated once on first call and was previously never invalidated
  // here, so a process that elevates itself between calls would
  // continue to report `false` and the renderer would offer a
  // redundant UAC prompt. `forceFresh: true` re-probes via whoami,
  // so the renderer sees the current ground truth. The check runs
  // BEFORE the rate-limit consumption so an already-elevated process
  // does NOT spend a UAC-prompt budget slot on a no-op call.
  _resetIsElevatedCache();
  if (isRunningAsAdmin({ forceFresh: true })) {
    return { ok: true, alreadyElevated: true };
  }
  // Rate-limit per sender so a compromised renderer cannot prompt-
  // spam the user with UAC dialogs or spawn cmd.exe in a tight loop.
  // The cap mirrors the log:write / python:execute shape. The check
  // runs AFTER the already-elevated probe above so we only count
  // ACTUAL UAC prompt attempts against the budget — a renderer that
  // toggles elevation on/off cannot exhaust the global cap purely on
  // already-elevated no-op calls.
  if (isAdminElevationRateLimited(senderId)) {
    return { ok: false, reason: 'rate limited' };
  }
  // The elevated child writes a marker file at startup so the parent
  // can confirm the child actually launched before tearing itself
  // down. The marker path includes an unguessable nonce so a local
  // attacker cannot pre-create or symlink a marker file to fake the
  // handshake. Both sides use `randomUUID()` so the path cannot be
  // predicted from outside this process.
  const nonce = randomUUID();
  const markerPath = computeElevationMarkerPath(nonce);
  // Pass a sentinel CLI flag to the elevated child. When the child
  // sees this flag at startup, it writes the marker file. The flag
  // is intentionally obscure so a normal user double-click cannot
  // accidentally trigger the handshake path.
  const handshakeFlag = '--sunshine-aio-elevation-handshake';
  const result = await requestAdminElevation({
    handshakeArgs: [handshakeFlag, markerPath, nonce],
  });
  if (!result.ok) {
    // Elevation failed (user cancelled UAC, spawn error, etc.). Do
    // NOT quit the parent — the user still needs a working app.
    // Refund the rate-limit budget we just consumed so the failure
    // does not penalise legitimate future calls.
    try {
      refundAdminElevationBudget(senderId);
    } catch (refundErr) {
      logger.warn('Failed to refund admin elevation budget', {
        message: refundErr && refundErr.message ? refundErr.message : String(refundErr),
      });
    }
    logger.warn('Admin elevation request failed', { reason: result.reason });
    return result;
  }
  // Handshake: wait for the elevated child to drop a marker file
  // before quitting. If we never see it (UAC declined, child
  // crashed at startup, etc.), the parent stays alive and the user
  // keeps their session.
  const handshake = await waitForElevationMarker(markerPath, ELEVATION_MARKER_TIMEOUT_MS, nonce);
  if (!handshake.ok) {
    // Handshake timed out — refund the budget since no UAC prompt
    // was accepted (the user cancelled, or the child crashed).
    try {
      refundAdminElevationBudget(senderId);
    } catch (refundErr) {
      logger.warn('Failed to refund admin elevation budget', {
        message: refundErr && refundErr.message ? refundErr.message : String(refundErr),
      });
    }
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
// IPC: notifications (Story 1.5)
// --------------------------------------------------------------------------
//
// Three channels cover the three AC categories (install / updates /
// errors). Each is a thin wrapper that defers to the
// NotificationManager and rate-limits per-sender to mirror the
// log:write / python:execute caps. Without the cap a compromised
// renderer could spam toasts and either (a) train the user to
// dismiss them reflexively, or (b) exhaust the OS notification
// queue.

const MAX_NOTIFICATIONS_PER_SECOND = 20;
const notificationRateState = new Map();

// Per-sender bookkeeping for live sender IDs. We use this to evict
// rate-limit entries when the underlying WebContents is destroyed so
// long-running apps with many windows do not accumulate stale state
// forever. Each map mirrors `event.sender.id` → `true` while the
// sender is alive; the entry is removed in the `web-contents-destroyed`
// handler below.
const liveSenders = new Set();

const isNotificationRateLimited = (senderId) => {
  const now = Date.now();
  const state = notificationRateState.get(senderId) || { count: 0, windowStart: now };
  if (now - state.windowStart >= 1000) {
    state.count = 0;
    state.windowStart = now;
  }
  state.count += 1;
  notificationRateState.set(senderId, state);
  return state.count > MAX_NOTIFICATIONS_PER_SECOND;
};

const wireSenderLifecycle = (event) => {
  if (!event || !event.sender) return;
  const id = event.sender.id;
  if (id === undefined || id === null) return;
  if (liveSenders.has(id)) return;
  liveSenders.add(id);
  // Best-effort: when the WebContents is destroyed, drop the sender
  // from every rate-limit map so it can be GC'd.
  const sender = event.sender;
  const cleanup = () => {
    liveSenders.delete(id);
    logRateState.delete(id);
    pythonRateState.delete(id);
    notificationRateState.delete(id);
    elevationRateState.delete(id);
  };
  if (sender.isDestroyed && sender.isDestroyed()) {
    cleanup();
    return;
  }
  sender.once('destroyed', cleanup);
};

ipcMain.handle('notification:test', (event) => {
  wireSenderLifecycle(event);
  const senderId = event && event.sender ? event.sender.id : 'unknown';
  if (isNotificationRateLimited(senderId)) {
    return { ok: false, reason: 'rate limited' };
  }
  const mgr = getNotificationManagerSafe();
  if (!mgr) return { ok: false, reason: 'notification manager not initialized' };
  // The "test" channel re-uses the install-complete path so the
  // developer can verify the toast pipeline end-to-end without
  // faking an install.
  const ok = mgr.notifyInstallComplete('Sunshine AIO (test)');
  return { ok };
});

ipcMain.handle('notification:install-complete', (event, payload) => {
  wireSenderLifecycle(event);
  const senderId = event && event.sender ? event.sender.id : 'unknown';
  if (isNotificationRateLimited(senderId)) {
    return { ok: false, reason: 'rate limited' };
  }
  const mgr = getNotificationManagerSafe();
  if (!mgr) return { ok: false, reason: 'notification manager not initialized' };
  // Sanitize renderer-supplied appName BEFORE it reaches either the
  // Windows toast surface or the file logger. Mirrors the defense in
  // the error handler below: a compromised renderer could otherwise
  // spoof OS-level prompts (title becomes "Windows Security Alert")
  // or inject CRLF / ANSI escapes into the log file. Cap length at
  // 120 — installs produce short app names (e.g. "Sunshine").
  const rawAppName =
    payload && typeof payload === 'object' && typeof payload.appName === 'string'
      ? payload.appName
      : '';
  const appName = sanitizeUserString(rawAppName, 120);
  const ok = mgr.notifyInstallComplete(appName);
  return { ok };
});

ipcMain.handle('notification:update-available', (event, payload) => {
  wireSenderLifecycle(event);
  const senderId = event && event.sender ? event.sender.id : 'unknown';
  if (isNotificationRateLimited(senderId)) {
    return { ok: false, reason: 'rate limited' };
  }
  const mgr = getNotificationManagerSafe();
  if (!mgr) return { ok: false, reason: 'notification manager not initialized' };
  // Sanitize every apps[] element so a compromised renderer cannot
  // smuggle CRLF / ANSI escapes / oversized strings through this
  // channel either. Non-array inputs are sanitized as a single
  // comma-separated string and then split back out so a renderer
  // cannot bypass the per-element cap by joining everything into
  // one giant string.
  let rawApps =
    payload && typeof payload === 'object' && payload.apps !== undefined ? payload.apps : [];
  if (typeof rawApps === 'string') {
    rawApps = rawApps.split(',').map((s) => s.trim());
  } else if (typeof rawApps === 'number') {
    rawApps = [String(rawApps)];
  } else if (!Array.isArray(rawApps)) {
    rawApps = [];
  }
  const safeApps = rawApps
    .map((entry) => {
      if (typeof entry === 'string') return sanitizeUserString(entry, 120);
      if (entry && typeof entry === 'object' && typeof entry.name === 'string') {
        return { name: sanitizeUserString(entry.name, 120) };
      }
      if (entry && typeof entry === 'object' && typeof entry.appName === 'string') {
        return { appName: sanitizeUserString(entry.appName, 120) };
      }
      return null;
    })
    .filter((entry) => entry !== null);
  const ok = mgr.notifyUpdateAvailable(safeApps);
  return { ok };
});

ipcMain.handle('notification:error', (event, payload) => {
  wireSenderLifecycle(event);
  const senderId = event && event.sender ? event.sender.id : 'unknown';
  if (isNotificationRateLimited(senderId)) {
    return { ok: false, reason: 'rate limited' };
  }
  const mgr = getNotificationManagerSafe();
  if (!mgr) return { ok: false, reason: 'notification manager not initialized' };
  // Sanitize renderer-supplied text BEFORE it reaches either the
  // Windows toast surface or the file logger. Without this, a
  // compromised renderer could spoof OS-level prompts (phishing:
  // title "Windows Security Alert" with a body asking for creds)
  // or inject CRLF / ANSI escapes into the log file.
  const rawMessage =
    payload && typeof payload === 'object' && typeof payload.message === 'string'
      ? payload.message
      : '';
  const rawTitle =
    payload && typeof payload === 'object' && typeof payload.title === 'string'
      ? payload.title
      : undefined;
  const message = sanitizeUserString(rawMessage, 200);
  const title = rawTitle !== undefined ? sanitizeUserString(rawTitle, 80) : undefined;
  const ok = mgr.notifyError(message, { title });
  return { ok };
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
    const nonce = argv[flagIndex + 2];
    // Both the marker path and the nonce are required. The parent
    // passes a UUIDv4 nonce; we verify the marker path lives under
    // the trusted temp dir, that the nonce is bound into the
    // filename itself (so a local attacker cannot plant a marker
    // before the legitimate parent generates its nonce), and that
    // the resolved real path does not traverse a symlink. Without
    // these checks, a low-privilege user invoking the same binary
    // with `--sunshine-aio-elevation-handshake <attacker-path>
    // <attacker-nonce>` could plant a marker that the parent later
    // accepts.
    const base = process.env.TEMP || process.env.TMP || app.getPath('temp');
    const baseResolved = path.resolve(base);
    const isNonceValid =
      typeof nonce === 'string' &&
      // UUID v4 shape: 8-4-4-4-12 hex with hyphens. Tightening
      // beyond this is unnecessary — the value is also validated
      // by the parent against its in-memory nonce.
      /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(nonce);
    let isPathSafe = false;
    if (
      markerPath &&
      typeof markerPath === 'string' &&
      isNonceValid &&
      // Bind the nonce into the filename. The parent computes the
      // marker path from the nonce, so only the parent holding the
      // nonce can predict the file location. A local attacker that
      // races the legitimate parent and plants a marker with a
      // guessed nonce would fail the parent's nonce check on
      // read-back (see waitForElevationMarker). This makes the
      // "pre-plant" race condition significantly harder.
      markerPath.endsWith(`${ELEVATION_MARKER_PREFIX}${nonce}${ELEVATION_MARKER_SUFFIX}`)
    ) {
      try {
        const resolved = path.resolve(markerPath);
        if (resolved === baseResolved || resolved.startsWith(baseResolved + path.sep)) {
          // Refuse symlinks: a local attacker could point the marker
          // path at an arbitrary file (e.g. one they wrote themselves
          // earlier) by leaving a symlink in the temp dir. realpathSync
          // resolves symlinks; comparing the resolved real path back
          // to the lexical path detects the substitution.
          let real;
          try {
            real = fs.realpathSync(resolved);
          } catch {
            // File does not exist yet (this is the FIRST writer);
            // realpath would fail. The marker file is then created
            // by us as a regular file, so subsequent reads are safe.
            real = resolved;
          }
          isPathSafe = real === resolved;
        }
      } catch {
        isPathSafe = false;
      }
    }
    if (markerPath && typeof markerPath === 'string' && isPathSafe && isNonceValid) {
      // Force the cached elevation result to refresh on the next
      // call. The current process is by definition the elevated
      // child — it just got past the UAC prompt — so a fresh probe
      // will return true.
      _resetIsElevatedCache();
      try {
        const payload = JSON.stringify({
          elevated: true,
          pid: process.pid,
          ts: Date.now(),
          nonce,
        });
        // Write atomically: write to a temp file in the same dir
        // then rename. This prevents a partial marker from being
        // observed by the parent polling loop mid-write. Use O_NOFOLLOW
        // so a symlink planted at the tmp path cannot redirect the
        // rename onto an attacker-controlled target.
        const tmpPath = `${markerPath}.tmp`;
        const fd = fs.openSync(tmpPath, 'w', 0o600);
        try {
          fs.writeSync(fd, payload, 0, 'utf8');
          fs.fsyncSync(fd);
        } finally {
          fs.closeSync(fd);
        }
        try {
          fs.renameSync(tmpPath, markerPath);
        } catch {
          // Fall back to a direct write if rename fails (e.g.
          // cross-volume move). Still try to clean up the tmp file.
          try {
            fs.unlinkSync(tmpPath);
          } catch {}
          fs.writeFileSync(markerPath, payload, { encoding: 'utf8' });
        }
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

  // Lock down navigation / window-open / permission surface. Even
  // though the renderer only loads a local file today, a future
  // regression that loads remote content (or a compromised renderer)
  // would otherwise be able to navigate the window to arbitrary
  // URLs, open new windows with default BrowserWindow privileges,
  // or prompt the user for camera/microphone/notification access.
  // The CSP in index.html mitigates remote script loading but does
  // NOT block navigation, which is why these guards live here.
  mainWindow.webContents.on('will-navigate', (event, navigationUrl) => {
    // Only allow navigation to the bundled index (or the dev server
    // when running under `electron-forge start`). Any other URL —
    // including file:// URLs that resolved outside the app dir —
    // is refused.
    //
    // Production guard: a Vite bake-in misconfiguration that left
    // `MAIN_WINDOW_VITE_DEV_SERVER_URL` set in a packaged build
    // would otherwise let the renderer navigate to a dev server URL
    // and load arbitrary attacker-controlled JS into the same
    // sandboxed renderer context. Refuse dev-server navigation
    // unconditionally when the app is packaged.
    try {
      const allowedUrls = new Set();
      if (MAIN_WINDOW_VITE_DEV_SERVER_URL && !app.isPackaged) {
        allowedUrls.add(MAIN_WINDOW_VITE_DEV_SERVER_URL);
      } else if (MAIN_WINDOW_VITE_DEV_SERVER_URL && app.isPackaged) {
        // Belt-and-braces: log the misconfiguration so an operator
        // notices and can fix the build.
        logger.error(
          'MAIN_WINDOW_VITE_DEV_SERVER_URL is set in a packaged build; refusing dev navigation'
        );
      }
      const indexPath = path.join(__dirname, `../renderer/${MAIN_WINDOW_VITE_NAME}/index.html`);
      allowedUrls.add(`file://${indexPath.replace(/\\/g, '/')}`);
      if (allowedUrls.has(navigationUrl)) {
        return;
      }
    } catch {
      // fall through and block on any unexpected error
    }
    event.preventDefault();
    logger.warn('Blocked navigation to non-allowlisted URL', { navigationUrl });
  });
  mainWindow.webContents.setWindowOpenHandler(() => {
    // The app never opens new windows; deny all window-open requests
    // so a compromised renderer cannot spawn arbitrary BrowserWindow
    // instances. If a future story adds an 'allow' branch, it MUST
    // also set `overrideBrowserWindowOptions: { webPreferences: {
    // nodeIntegration: false, contextIsolation: true, sandbox: true } }`
    // — without those flags the new window inherits the privileged
    // settings of the parent and a malicious popup could escape the
    // sandbox. We set the explicit defaults below as a safety net
    // for any future 'allow' that forgets to specify them.
    return {
      action: 'deny',
      overrideBrowserWindowOptions: {
        webPreferences: {
          nodeIntegration: false,
          contextIsolation: true,
          sandbox: true,
        },
      },
    };
  });
  mainWindow.webContents.setPermissionRequestHandler((_wc, _permission, callback) => {
    // Deny every permission request. The app has no need for camera,
    // microphone, geolocation, notifications, etc. The Electron
    // notification surface is used via the IPC channel, not via the
    // HTML5 Notification API, so this does not break Story 1.5.
    try {
      callback(false);
    } catch {
      /* ignore — callback may have been pre-resolved */
    }
  });

  // Note: the 'log:write' IPC handler is registered ONCE at module load
  // (above). Do NOT re-register it here — that would duplicate every
  // renderer log line on window recreation (macOS reactivation, reload,
  // future multi-window support).

  // and load the index.html of the app.
  // Production guard: refuse to load a dev server URL in a packaged
  // build. If `MAIN_WINDOW_VITE_DEV_SERVER_URL` somehow leaks through
  // (Vite bake-in misconfig), this guards the renderer against
  // loading attacker-controlled JS into the sandboxed context.
  if (MAIN_WINDOW_VITE_DEV_SERVER_URL && !app.isPackaged) {
    mainWindow.loadURL(MAIN_WINDOW_VITE_DEV_SERVER_URL);
    logger.info('Loading dev server URL', { url: MAIN_WINDOW_VITE_DEV_SERVER_URL });
  } else if (MAIN_WINDOW_VITE_DEV_SERVER_URL && app.isPackaged) {
    logger.error(
      'MAIN_WINDOW_VITE_DEV_SERVER_URL is set in a packaged build; loading bundled index instead'
    );
    const indexPath = path.join(__dirname, `../renderer/${MAIN_WINDOW_VITE_NAME}/index.html`);
    mainWindow.loadFile(indexPath);
    logger.info('Loading renderer index', { indexPath });
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
    // Best-effort recovery: surface a user-visible error AND schedule
    // a reload after a short delay so the user has a recovery path
    // beyond manually restarting the app. Without this, a renderer
    // crash leaves the window blank with no indication. We schedule
    // rather than reload synchronously so the dialog / IPC has time
    // to fire on a still-valid renderer's behalf.
    try {
      const mgr = getNotificationManagerSafe();
      if (mgr && typeof mgr.notifyError === 'function') {
        mgr.notifyError('The renderer crashed. The window will reload shortly.', {
          title: 'Sunshine AIO — Renderer recovered',
        });
      }
    } catch (notifyErr) {
      logger.warn('Failed to surface renderer-recovery notification', {
        message: notifyErr && notifyErr.message ? notifyErr.message : String(notifyErr),
      });
    }
    setTimeout(() => {
      try {
        if (mainWindow && !mainWindow.isDestroyed()) {
          mainWindow.webContents.reload();
        }
      } catch (reloadErr) {
        logger.warn('Failed to reload renderer after crash', {
          message: reloadErr && reloadErr.message ? reloadErr.message : String(reloadErr),
        });
      }
    }, 500);
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
  // ------------------------------------------------------------------------
  // Story 1.5: System notifications
  // ------------------------------------------------------------------------
  //
  // Initialise the notification manager BEFORE the window is created so
  // the renderer's first IPC call (which can fire as soon as the
  // preload + renderer JS load) does not race the manager init and
  // receive a false "manager not initialized" response. The manager
  // takes a `getMainWindow` accessor (same shape TrayManager uses),
  // so a not-yet-created window is fine — the accessor returns null
  // until `_mainWindow` is set, and `initNotificationManager` only
  // captures the accessor reference.
  //
  // The manager is feature-detected: when `Notification.isSupported()`
  // returns false (Linux without a notification daemon, headless test
  // runners, some VMs) the manager silently no-ops so the rest of the
  // app keeps working.
  try {
    initNotificationManager({
      getMainWindow: () => _mainWindow,
      logger,
      // `app.setAppUserModelId` was called above so Windows
      // associates toasts with Sunshine AIO's identity. We do not
      // pass an icon here — the manager falls back to a path
      // resolved relative to the bundled module.
      electronDeps: { Notification, isSupported: () => Notification.isSupported() },
    });
  } catch (err) {
    logger.error('Failed to initialize notification manager', err);
  }
  const win = createWindow();
  // Story 1.5: now that both the manager exists and the window is up,
  // attach the bridge event listeners (install-complete /
  // update-available / error / protocolError) that were deferred from
  // `getPythonBridge()`. Doing this AFTER the window is created is
  // harmless — `wireNotificationsToBridge` re-evaluates the manager
  // and the bridge reference at wire time. The helper is idempotent.
  try {
    wireNotificationsToBridge();
  } catch (err) {
    logger.warn('Failed to wire notifications to bridge', {
      message: err && err.message ? err.message : String(err),
    });
  }
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
// Platform note: macOS apps conventionally stay alive after the
// window closes (the dock icon remains). On Linux and Windows the
// Electron default is to quit. We therefore only honor minimize-to-
// tray on non-macOS platforms; on macOS we follow the platform
// convention and keep the app alive regardless of the toggle (a
// future macOS story can wire Cmd-Q vs window-close semantics).
app.on('window-all-closed', () => {
  const minimizeEnabled =
    settings && typeof settings.minimizeToTray === 'boolean' ? settings.minimizeToTray : false;
  if (minimizeEnabled && process.platform !== 'darwin') {
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
    // No bridge to drain; dispose the tray now. We do NOT call
    // app.quit() here — returning without preventing the default
    // lets the original quit proceed straight to will-quit, where
    // the logger-flush path runs.
    try {
      disposeTrayManager();
    } catch (err) {
      logger.warn('Failed to dispose tray manager', {
        message: err && err.message ? err.message : String(err),
      });
    }
    // Story 1.5: tear down the notification manager so any
    // in-flight toasts are released. This is idempotent and
    // safe to call even when no manager was ever initialised.
    // We unwire the bridge listeners FIRST so any in-flight
    // Python event arriving between `disposeNotificationManager`
    // and process exit does not call methods on a disposed
    // manager.
    try {
      unwireNotificationsFromBridge();
    } catch (err) {
      logger.warn('Failed to unwire notifications from bridge', {
        message: err && err.message ? err.message : String(err),
      });
    }
    try {
      disposeNotificationManager();
    } catch (err) {
      logger.warn('Failed to dispose notification manager', {
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
      // Story 1.5: also dispose the notification manager. We do
      // this AFTER the tray dispose so the disposal order
      // mirrors the construction order in `app.whenReady`.
      // Unwire FIRST so any straggling bridge event arriving in
      // the cleanup window does not call into a disposed
      // manager.
      try {
        unwireNotificationsFromBridge();
      } catch (err) {
        logger.warn('Failed to unwire notifications from bridge', {
          message: err && err.message ? err.message : String(err),
        });
      }
      try {
        disposeNotificationManager();
      } catch (err) {
        logger.warn('Failed to dispose notification manager', {
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
      // One-shot guard: 'before-quit' may re-issue `app.quit()` from
      // its .finally, which re-enters 'will-quit'. Without this flag a
      // second flush + `app.exit(0)` could fire concurrently and
      // interleave writes on the same logger file handle, corrupting
      // the log. Set the flag BEFORE calling exit so any racing pass
      // short-circuits on its way in.
      if (_exited) return;
      _exited = true;
      // The tray icon is already gone by the time we get here
      // (before-quit's .finally() disposes it just before re-issuing
      // app.quit()). app.exit() skips the remaining lifecycle events
      // so the (already-prevented) close path cannot re-enter.
      app.exit(0);
    });
});
