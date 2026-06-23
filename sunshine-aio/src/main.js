import { app, BrowserWindow, dialog, ipcMain } from 'electron';
import path from 'node:path';
import started from 'electron-squirrel-startup';
import { createDefaultLogger } from './logger.js';
import { PythonBridge } from './pythonBridge.js';

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
  logger[safeLevel](`[renderer] ${typeof message === 'string' ? message : ''}`, meta);
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

/**
 * Lazily create the Python bridge. Subsequent calls return the same
 * instance. The first call kicks off the spawn; concurrent calls await
 * the same init promise so we never spawn two children.
 */
const getPythonBridge = () => {
  if (pythonBridge) return pythonBridge;
  if (pythonBridgeInitPromise) return pythonBridgeInitPromise;
  try {
    pythonBridge = new PythonBridge({ logger });
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

// 'python:ping' — AC2 of Story 1.3: round-trip a ping to the Python
// backend and return the pong to the renderer.
ipcMain.handle('python:ping', async () => {
  try {
    const bridge = await getPythonBridge();
    const result = await bridge.ping();
    return { ok: true, result };
  } catch (err) {
    logger.warn('python:ping failed', { message: err && err.message ? err.message : String(err) });
    return { ok: false, error: err && err.message ? err.message : String(err) };
  }
});

// 'python:execute' — generic command dispatch. We accept any command
// name; the bridge enforces command whitelisting on the Python side.
ipcMain.handle('python:execute', async (_event, payload) => {
  if (!payload || typeof payload !== 'object') {
    return { ok: false, error: 'payload must be an object with cmd and optional params' };
  }
  const { cmd, params } = payload;
  if (typeof cmd !== 'string' || !cmd) {
    return { ok: false, error: 'cmd must be a non-empty string' };
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

  // DevTools toggle shortcut (F12 or Ctrl+Shift+I) - available in both dev and prod
  mainWindow.webContents.on('input-event', (event, input) => {
    if (
      input.type === 'keyDown' &&
      (input.key === 'F12' || (input.control && input.shift && input.key === 'I'))
    ) {
      mainWindow.webContents.toggleDevTools();
      event.preventDefault();
    }
  });

  mainWindow.webContents.on('render-process-gone', (_event, details) => {
    logger.error('Renderer process gone', details);
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
  if (pythonBridge._quitting) return;
  pythonBridge._quitting = true;
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
