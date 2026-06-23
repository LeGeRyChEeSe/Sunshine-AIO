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
  app.exit(1);
});

process.on('unhandledRejection', (reason) => {
  const err = reason instanceof Error ? reason : new Error(String(reason));
  logger.error('Unhandled promise rejection in main process', err);
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

  // Forward renderer-reported errors back to the main-process logger so they
  // share a single log file. Renderer cannot touch the FS directly.
  ipcMain.handle('log:write', (_event, payload) => {
    if (!payload || typeof payload !== 'object') {
      logger.warn('Renderer sent invalid log payload');
      return { ok: false };
    }
    const { level, message, meta } = payload;
    const safeLevel = ['debug', 'info', 'warn', 'error'].includes(level) ? level : 'info';
    logger[safeLevel](`[renderer] ${typeof message === 'string' ? message : ''}`, meta);
    return { ok: true };
  });

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

app.on('will-quit', () => {
  logger.info('App will quit, flushing logger');
  // Best-effort flush — we are about to exit anyway.
  try {
    logger.flush();
  } catch (flushError) {
    process.stderr.write(`Logger flush failed: ${flushError.message}\n`);
  }
});
