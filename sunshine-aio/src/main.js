import { app, BrowserWindow, dialog, ipcMain } from 'electron';
import path from 'node:path';
import started from 'electron-squirrel-startup';
import { createDefaultLogger } from './logger.js';

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
  createWindow();
});

// Quit when all windows are closed
app.on('window-all-closed', () => {
  logger.info('All windows closed, quitting app');
  app.quit();
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
