import { app, BrowserWindow, dialog, ipcMain, session } from 'electron';
import path from 'node:path';
import fs from 'node:fs';
import started from 'electron-squirrel-startup';
import { createDefaultLogger } from './logger.js';
import { PythonBridge } from './pythonBridge.js';
import { isScriptPathSafe } from './scriptPathGuard.js';

// Handle creating/removing shortcuts on Windows when installing/uninstalling.
if (started) {
  app.quit();
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
// Hard cap on the rate-state map to prevent unbounded growth. Each
// distinct `event.sender.id` (including destroyed WebContents from
// window reloads, devtools, future multi-window) gets a new entry;
// without eviction, these accumulate forever in long-running sessions.
// 256 is comfortably larger than the realistic number of concurrent
// renderers we expect to handle.
const MAX_RATE_STATE_ENTRIES = 256;
// How long a rate-state entry may sit idle before being evicted. 60s
// matches the rate window; any state older than that has already
// window-reset at least once and is safe to drop.
const RATE_STATE_TTL_MS = 60_000;

// Per-sender rate limit on python:execute / python:ping. Mirrors the
// log:write cap. Without this, a compromised renderer or buggy JS loop
// could fire thousands of IPC calls per second, each allocating a
// pending entry + timer in the bridge and exhausting memory.
const MAX_PYTHON_MESSAGES_PER_SECOND = 100;
const pythonRateState = new Map(); // senderId -> { count, windowStart }

/**
 * Evict stale rate-state entries. Walks both maps, drops any entry
 * whose `windowStart` is older than `RATE_STATE_TTL_MS`, and if the
 * map is still over `MAX_RATE_STATE_ENTRIES` after that, evicts the
 * oldest entries (lowest `windowStart`) until the cap is respected.
 * The function is called on every rate check so the cost is O(n) per
 * check but n is bounded.
 */
const evictStaleRateState = (map, now) => {
  for (const [key, state] of map) {
    if (now - state.windowStart > RATE_STATE_TTL_MS) {
      map.delete(key);
    }
  }
  if (map.size > MAX_RATE_STATE_ENTRIES) {
    const sorted = [...map.entries()].sort((a, b) => a[1].windowStart - b[1].windowStart);
    const overflow = sorted.length - MAX_RATE_STATE_ENTRIES;
    for (let i = 0; i < overflow; i += 1) {
      map.delete(sorted[i][0]);
    }
  }
};

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
  evictStaleRateState(logRateState, now);
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
  evictStaleRateState(pythonRateState, now);
  const state = pythonRateState.get(senderId) || { count: 0, windowStart: now };
  if (now - state.windowStart >= 1000) {
    state.count = 0;
    state.windowStart = now;
  }
  state.count += 1;
  pythonRateState.set(senderId, state);
  return state.count > MAX_PYTHON_MESSAGES_PER_SECOND;
};

/**
 * Evict rate-state entries for a specific sender when its WebContents
 * is destroyed. Without this, an entry for a window that was closed
 * (e.g. user closed the devtools or a future second window) would
 * linger in the map until the TTL sweep. We hook this from
 * `createWindow` via `webContents.on('destroyed', ...)`.
 */
const evictRateStateForSender = (senderId) => {
  logRateState.delete(senderId);
  pythonRateState.delete(senderId);
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

// Default script path is resolved from the application root, not from
// process.cwd(), so the bridge works regardless of where Electron was
// launched. The bridge constructor uses the same default, but we resolve
// it here too so the path-safety check (below) compares apples to apples.
const PYTHON_SCRIPT_PATH = path.resolve(__dirname, 'python_bridge_server.py');

// Fail fast at startup if the script is missing. The bridge construction
// path lazily raises the same error inside `getPythonBridge()`, but by
// then the user has already seen a window and tried to interact with
// it — surface the error with a dialog AT START so the user knows what
// is wrong before they try to ping the backend. A missing script is a
// build / install problem and is not recoverable at runtime.
try {
  if (!fs.existsSync(PYTHON_SCRIPT_PATH)) {
    const msg =
      `Python bridge script not found at ${PYTHON_SCRIPT_PATH}. ` +
      `The Sunshine AIO install may be incomplete or the script was moved by an update. ` +
      `Reinstall the application or restore the file at the expected location.`;
    logger.error(msg);
    try {
      dialog.showErrorBox('Python bridge script missing', msg);
    } catch (dialogErr) {
      logger.error('Failed to display missing-script dialog', dialogErr);
    }
  } else {
    // On POSIX systems, verify the file is executable. On Windows the
    // .py extension is associated with the launcher so an explicit
    // X_OK check is unnecessary; we still probe it but ignore failures
    // on win32.
    try {
      fs.accessSync(PYTHON_SCRIPT_PATH, fs.constants.R_OK);
    } catch (accessErr) {
      logger.error('Python bridge script is not readable', {
        path: PYTHON_SCRIPT_PATH,
        message: accessErr.message,
      });
    }
  }
} catch (checkErr) {
  // A probe error must not crash app startup. Log and continue — the
  // IPC handlers will surface the error per-call if the script is
  // genuinely missing.
  logger.warn('Failed to pre-check Python bridge script', {
    message: checkErr && checkErr.message ? checkErr.message : String(checkErr),
  });
}

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
    return { ok: false, error: 'rate limited', code: 'RATE_LIMITED' };
  }
  try {
    const bridge = await getPythonBridge();
    const result = await bridge.ping();
    return { ok: true, result };
  } catch (err) {
    // Public error surface: map the internal error to a structured
    // response with a stable `code` so the renderer can show a
    // meaningful toast. We deliberately do NOT include the original
    // message (which can contain absolute paths or interpreter
    // locations) in the renderer-visible field — that data is logged
    // server-side only.
    const code = mapPythonErrorCode(err);
    const message = publicPythonErrorMessage(err, code);
    logger.warn('python:ping failed', {
      code,
      message: err && err.message ? err.message : String(err),
    });
    return { ok: false, error: message, code };
  }
});

/**
 * Map an internal bridge error to a stable, renderer-safe code.
 * The renderer uses this code to display a meaningful error message
 * and to decide whether to retry. Codes are part of the IPC contract.
 */
const mapPythonErrorCode = (err) => {
  if (!err) return 'INTERNAL_ERROR';
  const name = err.name || '';
  if (name === 'TimeoutError') return 'TIMEOUT';
  if (name === 'ProcessExitError') return 'BRIDGE_UNAVAILABLE';
  if (name === 'JsonProtocolError') return 'PROTOCOL_ERROR';
  if (name === 'BackpressureError') return 'BACKPRESSURE';
  const msg = (err.message || '').toLowerCase();
  if (msg.includes('not running') || msg.includes('did not become ready')) {
    return 'NOT_READY';
  }
  if (msg.includes('unknown') && msg.includes('cmd')) {
    return 'UNKNOWN_COMMAND';
  }
  return 'INTERNAL_ERROR';
};

/**
 * Produce a renderer-safe error message. Never includes absolute file
 * paths, interpreter paths, or stack traces — those are logged
 * server-side only. The renderer is treated as semi-trusted even
 * with contextIsolation enabled.
 */
const publicPythonErrorMessage = (err, code) => {
  switch (code) {
    case 'TIMEOUT':
      return 'Python request timed out';
    case 'BRIDGE_UNAVAILABLE':
      return 'Python backend is not running';
    case 'NOT_READY':
      return 'Python backend is not ready';
    case 'PROTOCOL_ERROR':
      return 'Python backend returned an invalid response';
    case 'BACKPRESSURE':
      return 'Python backend is busy — try again in a moment';
    case 'UNKNOWN_COMMAND':
      return 'Python backend does not recognize the request';
    case 'RATE_LIMITED':
      return 'Too many requests — slow down';
    default:
      return 'Python backend error';
  }
};

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
    return { ok: false, error: 'Too many requests — slow down', code: 'RATE_LIMITED' };
  }
  if (!payload || typeof payload !== 'object') {
    return {
      ok: false,
      error: 'payload must be an object with cmd and optional params',
      code: 'BAD_PAYLOAD',
    };
  }
  const { cmd, params } = payload;
  if (typeof cmd !== 'string' || !cmd) {
    return { ok: false, error: 'cmd must be a non-empty string', code: 'BAD_CMD' };
  }
  if (!ALLOWED_PYTHON_CMDS.has(cmd)) {
    // Reject unknown commands at the IPC boundary so they never reach
    // the Python script. This is the security boundary — the Python
    // side's "unknown command" response is treated as a last-resort
    // safety net, not the primary control.
    return { ok: false, error: 'Command is not allowed', code: 'UNKNOWN_COMMAND' };
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
      return {
        ok: false,
        error: 'params must be a plain JSON value',
        code: 'BAD_PARAMS',
      };
    }
    if (typeof params === 'number' && !Number.isFinite(params)) {
      // NaN / Infinity are not representable in JSON (they serialize to
      // "null" silently) — reject explicitly so a buggy renderer cannot
      // pass them through.
      return { ok: false, error: 'params must be a finite number', code: 'BAD_PARAMS' };
    }
  }
  // Bound params size to avoid a buggy renderer pushing the main process
  // into a giant JSON serialization. 64 KiB matches the log:write cap.
  let safeParams = params;
  try {
    if (params !== undefined && params !== null) {
      const size = Buffer.byteLength(JSON.stringify(params), 'utf8');
      if (size > MAX_LOG_PAYLOAD_BYTES) {
        return {
          ok: false,
          error: 'params too large',
          code: 'PARAMS_TOO_LARGE',
        };
      }
    }
  } catch {
    return { ok: false, error: 'params are not JSON-serializable', code: 'BAD_PARAMS' };
  }
  try {
    const bridge = await getPythonBridge();
    const result = await bridge.send(cmd, safeParams);
    return { ok: true, result };
  } catch (err) {
    // Public error surface: same mapping as python:ping. The raw
    // `err.message` is NEVER returned to the renderer — it can leak
    // install paths, library versions, and other environment details.
    // We log the full message server-side and return a stable code
    // plus a redacted user-visible message. We also propagate any
    // structured fields the bridge attached (e.g. err.code, err.response)
    // so the renderer can surface WHY the command failed (BAD_CMD,
    // protocol-level details, etc.) — but we strip the raw line.
    const code = mapPythonErrorCode(err);
    const message = publicPythonErrorMessage(err, code);
    const responseDetails = err && err.response ? sanitizeResponse(err.response) : undefined;
    logger.warn('python:execute failed', {
      cmd,
      code,
      message: err && err.message ? err.message : String(err),
    });
    return {
      ok: false,
      error: message,
      code,
      ...(responseDetails ? { details: responseDetails } : {}),
    };
  }
});

/**
 * Strip dangerous fields from a Python response before forwarding to
 * the renderer. The renderer is semi-trusted even with
 * contextIsolation enabled; we never want to leak raw stack traces,
 * absolute paths, or interpreter versions.
 */
const sanitizeResponse = (response) => {
  if (!response || typeof response !== 'object') return undefined;
  const safe = {};
  for (const key of Object.keys(response)) {
    // Allow only a tiny set of well-known fields.
    if (['code', 'ok', 'error'].includes(key)) {
      safe[key] = response[key];
    }
  }
  return Object.keys(safe).length > 0 ? safe : undefined;
};

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
      // Hardening flags: explicitly disable powerful features we
      // never use. A future story that needs one of these can opt
      // in. (allowRunningInsecureContent defaults to false; we set
      // it explicitly so the security posture is documented here.)
      allowRunningInsecureContent: false,
      experimentalFeatures: false,
      // webSecurity defaults to true; we set it explicitly so a
      // future refactor that touches this block does not silently
      // weaken the boundary.
      webSecurity: true,
      // Disable the <webview> tag entirely. We never use it; allowing
      // it would re-introduce the same contextIsolation bypass that
      // we worked to lock down.
      webviewTag: false,
    },
  });

  logger.info('Main window created', { id: mainWindow.id });

  // Security: explicitly deny window.open from the renderer. Electron
  // defaults to deny in newer versions, but we register the handler
  // explicitly so a future refactor that touches the IPC / nav code
  // does not silently regress.
  mainWindow.webContents.setWindowOpenHandler(() => ({ action: 'deny' }));

  // Security: deny any in-window navigation triggered by the
  // renderer (e.g. an <a href>, location.href assignment, or a
  // compromised renderer via XSS). Without this, a future bug that
  // renders untrusted DOM data could navigate the main BrowserWindow
  // to an attacker-controlled URL — leaving the app displaying
  // hostile content under the file:// origin and bypassing the
  // contextIsolation boundary.
  mainWindow.webContents.on('will-navigate', (event, navigationUrl) => {
    // Allow the initial load (dev server URL OR the bundled
    // renderer index). All other navigations are denied.
    const allowed =
      (typeof MAIN_WINDOW_VITE_DEV_SERVER_URL !== 'undefined' &&
        MAIN_WINDOW_VITE_DEV_SERVER_URL &&
        navigationUrl === MAIN_WINDOW_VITE_DEV_SERVER_URL) ||
      (navigationUrl.startsWith('file://') === false && false); // never match
    if (!allowed) {
      // Allow the file:// navigations that point to the bundled
      // renderer. We compute the index path the same way loadFile
      // does below so a future change to the renderer layout is
      // caught by a single-source-of-truth edit.
      const allowedIndex = path.join(
        app.getAppPath(),
        '.vite',
        'renderer',
        MAIN_WINDOW_VITE_NAME,
        'index.html'
      );
      const allowedFileUrl = `file:///${allowedIndex.replace(/\\/g, '/')}`;
      if (navigationUrl !== allowedFileUrl) {
        event.preventDefault();
        logger.warn('Blocked navigation attempt', { url: navigationUrl });
      }
    }
  });

  // Security: deny <webview> attachment. A future Story that adds a
  // <webview> tag would inherit Electron's permissive defaults
  // (sandbox=false unless explicitly set) and could load arbitrary
  // external content. We block it here so a future contributor
  // cannot accidentally re-introduce the attack surface.
  mainWindow.webContents.on('will-attach-webview', (event) => {
    event.preventDefault();
    logger.warn('Blocked webview attach attempt');
  });

  // Note: the 'log:write' IPC handler is registered ONCE at module load
  // (above). Do NOT re-register it here — that would duplicate every
  // renderer log line on window recreation (macOS reactivation, reload,
  // future multi-window support).

  // and load the index.html of the app.
  if (MAIN_WINDOW_VITE_DEV_SERVER_URL) {
    mainWindow.loadURL(MAIN_WINDOW_VITE_DEV_SERVER_URL);
    logger.info('Loading dev server URL', { url: MAIN_WINDOW_VITE_DEV_SERVER_URL });
  } else {
    // In production, the renderer build output lives at
    // <app>/.vite/renderer/<name>/index.html (the electron-forge Vite
    // plugin layout). Resolve from `app.getAppPath()` rather than
    // `__dirname` so the path is correct regardless of cwd and survives
    // any future re-bundling step. Verify the file exists before
    // loadFile() — otherwise Electron renders a blank window and the
    // user gets no actionable error.
    const indexPath = path.join(
      app.getAppPath(),
      '.vite',
      'renderer',
      MAIN_WINDOW_VITE_NAME,
      'index.html'
    );
    if (!fs.existsSync(indexPath)) {
      const msg = `Renderer index.html not found at ${indexPath}. The Vite renderer build may have failed or the output layout changed.`;
      logger.error(msg);
      try {
        dialog.showErrorBox('Renderer not found', msg);
      } catch (dialogErr) {
        logger.error('Failed to display renderer-missing dialog', dialogErr);
      }
      // Do NOT call loadFile() on a missing path — Electron's behavior
      // on missing files is to render an empty window with no error,
      // which is the worst possible UX.
    } else {
      mainWindow.loadFile(indexPath);
      logger.info('Loading renderer index', { indexPath });
    }
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

  // Evict rate-state entries when the WebContents is destroyed so a
  // closed window does not leak a Map entry until the 60s TTL sweep.
  // Important under window reloads (Ctrl+R in devtools) and future
  // multi-window support.
  mainWindow.webContents.on('destroyed', () => {
    evictRateStateForSender(mainWindow.webContents.id);
  });

  mainWindow.on('closed', () => {
    logger.info('Main window closed');
  });
};

// This method will be called when Electron has finished
// initialization and is ready to create browser windows.
// Some APIs can only be used after this event occurs.
app.whenReady().then(() => {
  logger.info('App ready, creating main window');

  // Install a strict response-header CSP. The <meta> CSP in
  // index.html is the second line of defense — this is the first.
  // A response-header CSP cannot be removed by a compromised
  // renderer via DOM mutation and is enforced against XHR/fetch /
  // WebSocket / navigation events. The directives are deliberately
  // tight: no remote scripts, no inline scripts, no eval, no
  // arbitrary connect-src, no embedded objects, no nested browsing
  // contexts, no form submissions.
  const STRICT_CSP = [
    "default-src 'self'",
    "script-src 'self'",
    "style-src 'self'",
    "img-src 'self' data:",
    "font-src 'self'",
    "connect-src 'self'",
    "object-src 'none'",
    "base-uri 'none'",
    "frame-ancestors 'none'",
    "form-action 'none'",
  ].join('; ');
  try {
    session.defaultSession.webRequest.onHeadersReceived((details, callback) => {
      callback({
        responseHeaders: {
          ...details.responseHeaders,
          'Content-Security-Policy': [STRICT_CSP],
          'X-Content-Type-Options': ['nosniff'],
          'Permissions-Policy': [
            // Disable every powerful feature by default. A future
            // story that needs one of these can opt in explicitly.
            'camera=(), microphone=(), geolocation=(), payment=(), usb=(), ' +
              'midi=(), bluetooth=(), accelerometer=(), gyroscope=(), ' +
              'magnetometer=(), ambient-light-sensor=(), serial=(), ' +
              'hid=(), encrypted-media=(), publickey-credentials-get=()',
          ],
        },
      });
    });
  } catch (err) {
    logger.warn('Failed to install CSP headers', {
      message: err && err.message ? err.message : String(err),
    });
  }

  // Kick off the Python bridge eagerly so the renderer can ping
  // immediately after window creation. We don't await here — if the
  // bridge is slow or fails, the IPC handlers will surface the error
  // per-call rather than blocking app startup.
  getPythonBridge().catch((err) => {
    logger.warn('Python bridge init deferred', {
      message: err && err.message ? err.message : String(err),
    });
  });
  createWindow();
});

// Quit when all windows are closed
app.on('window-all-closed', () => {
  logger.info('All windows closed, quitting app');
  app.quit();
});

// Clean up the Python bridge before the app exits. 'before-quit' fires
// when the user (or the OS) requests shutdown, BEFORE 'will-quit' and
// before any windows are torn down. We do an async quit() and let the
// 'will-quit' handler below serialize the actual exit so the logger
// flushes after.
app.on('before-quit', (event) => {
  if (!pythonBridge) return;
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
      app.exit(0);
    });
});
