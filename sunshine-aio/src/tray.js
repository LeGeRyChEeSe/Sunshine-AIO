import { Tray, Menu, nativeImage, app } from 'electron';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { restoreMainWindow } from './windowFocus.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

/**
 * TrayManager
 *
 * Owns the system-tray icon for Sunshine AIO. Responsibilities:
 *   - Create a tray icon with a context menu (Open / Quit).
 *   - Restore (show + focus) the main window when the user clicks the
 *     tray icon.
 *   - Provide a clean shutdown path so the tray icon is removed from
 *     the Windows notification area when the app exits (otherwise a
 *     stray icon lingers after the process dies).
 *
 * Design notes:
 *
 *   * The tray icon is decoupled from any one BrowserWindow. The
 *     constructor takes a `getMainWindow()` accessor so tests can pass
 *     a stub and production code can re-resolve the window after
 *     recreation (close + reopen).
 *
 *   * Click vs. right-click handling follows Electron's idiomatic
 *     split: `click` for restore (Windows shows no context menu on
 *     left-click), `right-click` to open the menu. The menu is built
 *     via `Tray.setContextMenu` so it auto-opens on right-click.
 *
 *   * The icon path is resolved relative to the bundled module so the
 *     same code works in dev (`src/tray.js`) and in the Vite-bundled
 *     output (`.vite/build/tray.js`). If the icon file is missing we
 *     fall back to `nativeImage.createEmpty()` rather than throwing —
 *     a missing icon should never crash app startup.
 *
 *   * Electron modules (Tray, Menu, nativeImage, app) are accepted
 *     via the `electronDeps` option so unit tests can inject fakes
 *     without booting Electron. In production we fall back to the
 *     real `electron` import.
 */
export class TrayManager {
  /**
   * @param {object} options
   * @param {() => (object | null)} options.getMainWindow
   *        Accessor returning the current main window (may be null).
   * @param {object | null} [options.icon]
   *        Pre-built tray icon. If omitted, the manager tries to load
   *        `assets/tray-icon.png` from the app root and falls back to
   *        an empty image.
   * @param {string} [options.tooltip] - Tooltip shown on hover.
   * @param {Function} [options.onQuit]
   *        Callback invoked when the user picks "Quit" from the tray
   *        menu. Defaults to `app.quit()`.
   * @param {object} [options.electronDeps]
   *        Injectable electron-like dependency bundle for tests.
   *        Shape: { Tray, Menu, nativeImage, app }. Defaults to the
   *        real electron module.
   */
  constructor({ getMainWindow, icon = null, tooltip = 'Sunshine AIO', onQuit, electronDeps } = {}) {
    if (typeof getMainWindow !== 'function') {
      throw new TypeError('TrayManager: getMainWindow must be a function');
    }
    const deps = electronDeps || { Tray, Menu, nativeImage, app };
    this._deps = deps;
    this._getMainWindow = getMainWindow;
    this._tooltip = tooltip;
    this._onQuit = typeof onQuit === 'function' ? onQuit : () => deps.app.quit();
    this._tray = null;
    this._disposed = false;
    this._icon = icon || this._loadDefaultIcon();
  }

  /**
   * Build / activate the tray icon. Safe to call once; repeated calls
   * are no-ops (this protects against double-init in hot-reload).
   *
   * @param {{ logger?: { info: Function, warn: Function, error: Function } }} [deps]
   * @returns {boolean} true if a tray was created, false if already
   *                    initialized or after disposal.
   */
  init(deps = {}) {
    if (this._tray) return false;
    if (this._disposed) return false;
    const logger = deps.logger;
    try {
      const { Tray: TrayCtor } = this._deps;
      this._tray = new TrayCtor(this._icon);
      this._tray.setToolTip(this._tooltip);
      this._tray.setContextMenu(this._buildContextMenu());
      this._tray.on('click', () => this._restoreWindow());
      this._tray.on('double-click', () => this._restoreWindow());
      if (logger && typeof logger.info === 'function') {
        logger.info('Tray icon initialized');
      }
      return true;
    } catch (err) {
      if (logger && typeof logger.error === 'function') {
        logger.error('Failed to create tray icon', err);
      }
      this._tray = null;
      return false;
    }
  }

  /**
   * Destroy the tray icon. Idempotent. Should be invoked from
   * `app.on('before-quit')` to ensure the Windows notification area
   * does not retain a ghost icon after the process exits.
   */
  dispose() {
    if (this._tray) {
      try {
        this._tray.destroy();
      } catch {
        // Some platforms throw if the tray is already destroyed; we
        // intentionally swallow that to keep dispose idempotent.
      }
      this._tray = null;
    }
    this._disposed = true;
  }

  /**
   * Whether the tray icon is currently active. Exposed for tests and
   * for the main process to gate minimize-to-tray behavior.
   */
  isActive() {
    return this._tray !== null && !this._disposed;
  }

  /**
   * Build the right-click context menu. Exposed (rather than inlined)
   * so tests can introspect the menu structure without booting Electron.
   */
  _buildContextMenu() {
    const { Menu: MenuCtor } = this._deps;
    return MenuCtor.buildFromTemplate([
      {
        label: 'Open',
        click: () => this._restoreWindow(),
      },
      { type: 'separator' },
      {
        label: 'Quit',
        click: () => this._onQuit(),
      },
    ]);
  }

  /**
   * Restore the main window: show it if hidden, focus it, and
   * un-minimize if minimized. No-op when the window is unavailable.
   * The implementation lives in the shared `windowFocus` helper so
   * the tray and notification surfaces cannot drift apart.
   */
  _restoreWindow() {
    restoreMainWindow(this._getMainWindow, { eventName: 'tray.restore' });
  }

  /**
   * Resolve the default tray icon. Looks for `assets/tray-icon.png`
   * next to the bundled module and returns an empty image when not
   * found so tray creation never throws on missing assets.
   */
  _loadDefaultIcon() {
    const { nativeImage: NI } = this._deps;
    try {
      const iconPath = path.join(__dirname, '..', 'assets', 'tray-icon.png');
      const img = NI.createFromPath(iconPath);
      if (img && !img.isEmpty()) return img;
    } catch {
      // fall through
    }
    return NI.createEmpty();
  }
}

/**
 * Singleton accessor for the main process. Modules that want the
 * tray manager without holding a reference (e.g. IPC handlers) can
 * `getTrayManager()` after `initTrayManager()` has been called by
 * `main.js`.
 */
let _singleton = null;

export const initTrayManager = (deps) => {
  if (_singleton) return _singleton;
  _singleton = new TrayManager(deps);
  _singleton.init(deps);
  return _singleton;
};

export const getTrayManager = () => _singleton;

export const disposeTrayManager = () => {
  if (_singleton) {
    _singleton.dispose();
    _singleton = null;
  }
};
