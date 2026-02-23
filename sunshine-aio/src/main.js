import { app, BrowserWindow } from 'electron';
import path from 'node:path';
import started from 'electron-squirrel-startup';

// Handle creating/removing shortcuts on Windows when installing/uninstalling.
if (started) {
  app.quit();
}

// Global exception handler for main process
process.on('uncaughtException', (error) => {
  console.error('[MAIN] Uncaught Exception:', error);
  app.exit(1);
});

process.on('unhandledRejection', (reason) => {
  console.error('[MAIN] Unhandled Rejection:', reason);
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
