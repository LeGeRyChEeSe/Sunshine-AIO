import { app, BrowserWindow } from 'electron';
import path from 'node:path';
import fs from 'node:fs';
import started from 'electron-squirrel-startup';

// Handle creating/removing shortcuts on Windows when installing/uninstalling.
if (started) {
  app.quit();
}

// Logs directory for fatal error breadcrumbs (mirrors Python Logger.py pattern)
const LOG_DIR = path.join(app.getPath('userData'), 'logs');
const writeFatalLog = (label, payload) => {
  try {
    if (!fs.existsSync(LOG_DIR)) {
      fs.mkdirSync(LOG_DIR, { recursive: true });
    }
    const file = path.join(LOG_DIR, `fatal-${new Date().toISOString().replace(/[:.]/g, '-')}.log`);
    fs.writeFileSync(file, `[${label}] ${payload}\n`, { encoding: 'utf8' });
  } catch {
    // Best-effort: never let logging take down the error handler.
  }
};

// Global exception handler for main process
process.on('uncaughtException', (error) => {
  console.error('[MAIN] Uncaught Exception:', error);
  writeFatalLog('uncaughtException', `${error?.stack || error}`);
  app.exit(1);
});

process.on('unhandledRejection', (reason) => {
  console.error('[MAIN] Unhandled Rejection:', reason);
  writeFatalLog('unhandledRejection', `${reason?.stack || reason}`);
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

  // and load the index.html of the app.
  if (MAIN_WINDOW_VITE_DEV_SERVER_URL) {
    mainWindow.loadURL(MAIN_WINDOW_VITE_DEV_SERVER_URL);
  } else {
    mainWindow.loadFile(path.join(__dirname, `../renderer/${MAIN_WINDOW_VITE_NAME}/index.html`));
  }

  // Dev-only convenience shortcuts (F5 reload, F12/Ctrl+Shift+I DevTools).
  // Note: 'input-event' fires after the input is processed; event.preventDefault()
  // does NOT suppress the browser's native reload/DevTools behavior, so we cannot
  // fully prevent F5 from also reloading natively. The explicit reload() call
  // here is intentional for dev ergonomics.
  // SECURITY: gated to non-packaged builds to keep DevTools out of production.
  if (!app.isPackaged) {
    mainWindow.webContents.on('input-event', (_event, input) => {
      if (input.type !== 'keyDown') {
        return;
      }
      if (input.key === 'F5') {
        mainWindow.webContents.reload();
      }
      if (input.key === 'F12' || (input.control && input.shift && input.key === 'I')) {
        mainWindow.webContents.toggleDevTools();
      }
    });
  }
};

// This method will be called when Electron has finished
// initialization and is ready to create browser windows.
// Some APIs can only be used after this event occurs.
app.whenReady().then(() => {
  createWindow();
});

// Quit when all windows are closed
app.on('window-all-closed', () => {
  app.quit();
});
