/**
 * Sunshine AIO — System notifications (Story 1.5)
 *
 * Wraps Electron's `Notification` API with a small, test-friendly
 * surface so the rest of the app can request toast-style Windows
 * notifications without having to know which features are supported on
 * the current host.
 *
 * Why a wrapper:
 *   - Centralises permission / feature-detection: Electron's
 *     `Notification.isSupported()` is the only way to know if the host
 *     can actually surface toasts (some Linux desktops, headless
 *     test runners, and CI VMs all return false). We probe once,
 *     cache the result, and degrade gracefully.
 *   - Centralises click-to-focus wiring. A user who clicks a
 *     notification expects the app window to come to the front; that
 *     needs the live BrowserWindow reference, which the notification
 *     layer cannot own on its own. The wrapper takes a
 *     `getMainWindow()` accessor (the same shape TrayManager uses) so
 *     production code can supply it once and tests can inject a
 *     stub.
 *   - Centralises logging. Every emitted notification is mirrored to
 *     the main-process logger so we have an audit trail in
 *     `logs/sunshine-aio-*.log` even when the user dismisses the
 *     toast without clicking.
 *
 * Public API:
 *   - class NotificationManager
 *       - constructor({ getMainWindow, iconPath, logger, electronDeps })
 *       - isSupported() -> boolean
 *       - setEnabled(boolean)
 *       - isEnabled() -> boolean
 *       - notifyInstallComplete(appName, opts?) -> boolean
 *       - notifyUpdateAvailable(apps, opts?) -> boolean
 *       - notifyError(message, opts?) -> boolean
 *       - dispose()
 *   - initNotificationManager(deps) -> NotificationManager
 *   - getNotificationManager() -> NotificationManager | null
 *   - disposeNotificationManager()
 *
 * Click-to-focus contract:
 *   When the user clicks a notification, the manager invokes
 *   `getMainWindow()` and, if the window exists, calls
 *   `show()` + `focus()` + (if minimized) `unminimize()`. This
 *   mirrors the tray-icon click handler so the two entry points feel
 *   identical to the user.
 */

import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Default timeout. Windows actually shows toasts for ~5 seconds by
// default, but Electron's `Notification` lets us override the OS
// default. We pick a slightly longer window so a user who clicked
// away to read something else still has time to see the toast before
// it disappears. The 8s value matches common chat-app defaults.
const DEFAULT_TIMEOUT_MS = 8000;

// Default icon path resolved relative to the bundled module so dev
// (`src/notifications.js`) and the Vite-bundled output
// (`.vite/build/notifications.js`) both work. If the file is missing
// the manager falls back to a null icon path — Electron accepts
// `undefined` and shows the system default app icon.
const DEFAULT_ICON_RELATIVE = path.join('..', 'assets', 'app-icon.png');

// Default strings. Kept in one place so the user-facing copy is easy
// to update without grepping the codebase.
const STRINGS = Object.freeze({
  installCompleteTitle: 'Sunshine AIO — Installation Complete',
  installCompleteBody: (appName) => `${appName} has been installed successfully.`,
  updatesAvailableTitle: 'Sunshine AIO — Updates Available',
  updatesAvailableBody: (count) => {
    if (!Number.isFinite(count) || count <= 0) {
      return 'Updates are available for your installed applications.';
    }
    if (count === 1) {
      return '1 update is available for an installed application.';
    }
    return `${count} updates are available for installed applications.`;
  },
  errorTitle: 'Sunshine AIO — Error',
  errorBody: (message) => {
    if (typeof message === 'string' && message.trim().length > 0) {
      // Cap to 200 chars to keep the toast small and to bound the
      // risk of leaking large error payloads into the OS notification
      // system.
      const trimmed = message.trim();
      return trimmed.length > 200 ? `${trimmed.slice(0, 197)}...` : trimmed;
    }
    return 'An unexpected error occurred. See the log file for details.';
  },
});

/**
 * Safely coerce an arbitrary value to a trimmed, non-empty string.
 * Returns `null` if nothing usable can be extracted — the caller can
 * then decide on a sensible fallback.
 */
const toTrimmedString = (value) => {
  if (typeof value === 'string') {
    const trimmed = value.trim();
    return trimmed.length > 0 ? trimmed : null;
  }
  if (value === null || value === undefined) return null;
  try {
    const s = String(value).trim();
    return s.length > 0 ? s : null;
  } catch {
    return null;
  }
};

/**
 * Build a friendly install-complete body for a single app name.
 * Returns the (possibly renamed) app name string.
 */
const normalizeAppName = (appName) => {
  const s = toTrimmedString(appName);
  if (s) return s;
  return 'The application';
};

/**
 * Coerce an "apps" argument into a positive integer count and a
 * representative label. The notification body is the count; the
 * optional label is used as the title's subtitle when the count is
 * exactly 1 so the user can see *which* app has an update.
 */
const normalizeUpdateList = (apps) => {
  if (Array.isArray(apps)) {
    const names = apps
      .map((entry) => {
        if (typeof entry === 'string') return toTrimmedString(entry);
        if (entry && typeof entry === 'object') {
          return toTrimmedString(entry.name) || toTrimmedString(entry.appName);
        }
        return null;
      })
      .filter((s) => s !== null);
    return { count: names.length, firstName: names[0] || null };
  }
  if (typeof apps === 'string') {
    // Allow a comma-separated list as a convenience for callers
    // that just want a single notification.
    const parts = apps
      .split(',')
      .map((p) => toTrimmedString(p))
      .filter((s) => s !== null);
    return { count: parts.length, firstName: parts[0] || null };
  }
  if (typeof apps === 'number' && Number.isFinite(apps) && apps > 0) {
    return { count: Math.floor(apps), firstName: null };
  }
  return { count: 0, firstName: null };
};

/**
 * Try to extract an Electron Notification constructor from the
 * injected deps. Returns null if the host cannot render toasts.
 */
const resolveNotificationCtor = (deps) => {
  if (!deps) return null;
  const direct = deps.Notification;
  if (typeof direct === 'function') return direct;
  if (deps.electron && typeof deps.electron.Notification === 'function') {
    return deps.electron.Notification;
  }
  return null;
};

const resolveIsSupported = (deps, NotificationCtor) => {
  if (typeof deps.isSupported === 'function') {
    try {
      return Boolean(deps.isSupported());
    } catch {
      return false;
    }
  }
  if (NotificationCtor && typeof NotificationCtor.isSupported === 'function') {
    try {
      return Boolean(NotificationCtor.isSupported());
    } catch {
      return false;
    }
  }
  // Without an explicit probe we cannot tell, but we also cannot
  // guarantee the constructor will not throw on `new`. Default to
  // "supported" so the caller at least gets a chance; the actual
  // constructor will throw synchronously if the platform refuses.
  return true;
};

export class NotificationManager {
  /**
   * @param {object} options
   * @param {() => (object | null)} options.getMainWindow
   *        Accessor returning the current main window (may be null).
   *        Used by the click-to-focus handler. Same shape as the
   *        TrayManager accessor so the two stay symmetric.
   * @param {string} [options.iconPath]
   *        Absolute or relative path to the app icon. Defaults to a
   *        path resolved relative to this module.
   * @param {object} [options.logger]
   *        Logger instance — every emitted notification is mirrored
   *        here. Optional but strongly recommended in production.
   * @param {object} [options.electronDeps]
   *        Injectable electron-like dependency bundle. Shape:
   *          { Notification?: Function, isSupported?: () => boolean }
   *        Tests inject a fake; production falls back to the real
   *        `electron` import.
   * @param {boolean} [options.enabled=true]
   *        Whether to actually surface toasts. The manager still
   *        logs the notification even when disabled (so the audit
   *        trail is preserved) but does not construct a
   *        Notification object.
   */
  constructor({ getMainWindow, iconPath, logger, electronDeps, enabled = true } = {}) {
    if (typeof getMainWindow !== 'function') {
      throw new TypeError('NotificationManager: getMainWindow must be a function');
    }
    const deps = electronDeps || defaultElectronDeps();
    this._deps = deps;
    this._getMainWindow = getMainWindow;
    this._iconPath = iconPath || path.join(__dirname, DEFAULT_ICON_RELATIVE);
    this._logger = logger || null;
    this._enabled = enabled !== false;
    this._NotificationCtor = resolveNotificationCtor(deps);
    this._supported = resolveIsSupported(deps, this._NotificationCtor);
    this._disposed = false;
  }

  /**
   * Returns true when the host can actually surface toast
   * notifications. Cached at construction time — re-probing per call
   * would be a sync IPC for no benefit.
   */
  isSupported() {
    return this._supported && this._NotificationCtor !== null;
  }

  /**
   * Enable / disable toast emission. The manager still records the
   * request in the logger (so the audit trail is preserved) but does
   * not construct a Notification object when disabled.
   */
  setEnabled(value) {
    this._enabled = Boolean(value);
  }

  isEnabled() {
    return Boolean(this._enabled);
  }

  /**
   * Show a "Installation Complete" toast.
   * @param {string} appName
   * @param {{ silent?: boolean }} [opts]
   * @returns {boolean} true if a toast was shown, false otherwise.
   */
  notifyInstallComplete(appName, opts = {}) {
    const safeName = normalizeAppName(appName);
    return this._show({
      type: 'install-complete',
      title: STRINGS.installCompleteTitle,
      body: STRINGS.installCompleteBody(safeName),
      meta: { appName: safeName },
      silent: opts.silent === true,
    });
  }

  /**
   * Show an "Updates Available" toast.
   * @param {string[] | number | string} apps
   *        - An array of app names (or `{ name }` objects) -> count + first
   *        - A number -> count
   *        - A comma-separated string -> count
   * @param {{ silent?: boolean }} [opts]
   * @returns {boolean} true if a toast was shown, false otherwise.
   */
  notifyUpdateAvailable(apps, opts = {}) {
    const { count, firstName } = normalizeUpdateList(apps);
    const subtitle = count === 1 && firstName ? ` (${firstName})` : '';
    return this._show({
      type: 'update-available',
      title: `${STRINGS.updatesAvailableTitle}${subtitle}`,
      body: STRINGS.updatesAvailableBody(count),
      meta: { count, firstName },
      silent: opts.silent === true,
    });
  }

  /**
   * Show an error toast.
   * @param {string} message
   * @param {{ silent?: boolean, title?: string }} [opts]
   * @returns {boolean} true if a toast was shown, false otherwise.
   */
  notifyError(message, opts = {}) {
    const title = toTrimmedString(opts.title) || STRINGS.errorTitle;
    return this._show({
      type: 'error',
      title,
      body: STRINGS.errorBody(message),
      meta: {
        // Only store a short preview in meta — never the full
        // payload, so a leaked log line cannot expose a giant
        // error blob.
        messagePreview: STRINGS.errorBody(message),
      },
      silent: opts.silent === true,
    });
  }

  /**
   * Tear down internal state. Idempotent.
   */
  dispose() {
    this._disposed = true;
  }

  /**
   * Internal: actually construct and show a Notification.
   * @returns {boolean}
   */
  _show({ type, title, body, meta, silent }) {
    if (this._disposed) {
      this._log('warn', 'notification.disposed', { type, title });
      return false;
    }
    // Always log the request — even when disabled or unsupported —
    // so the audit trail captures every attempted emission.
    this._log('info', `notification.${type}.request`, { ...meta, title, body });
    if (!this._enabled) {
      this._log('debug', `notification.${type}.skipped_disabled`, { title });
      return false;
    }
    if (!this.isSupported()) {
      this._log('debug', `notification.${type}.skipped_unsupported`, { title });
      return false;
    }
    let notification;
    try {
      notification = new this._NotificationCtor({
        title,
        body,
        silent: silent === true,
        icon: this._iconPath || undefined,
        timeoutType: 'default',
      });
      // Some platforms (notably Windows) respect a `timeoutType: 'never'`
      // we don't set by default; users can still dismiss the toast.
      try {
        if (DEFAULT_TIMEOUT_MS && typeof notification.show === 'function') {
          // The Electron API has no direct timeout setter; instead
          // we schedule a close. If the platform supports the
          // `close` event we use that, otherwise the OS default
          // takes over.
          setTimeout(() => {
            try {
              if (notification && typeof notification.close === 'function') {
                notification.close();
              }
            } catch {
              /* already closed */
            }
          }, DEFAULT_TIMEOUT_MS).unref?.();
        }
      } catch {
        /* ignore — notification may have been closed already */
      }
      if (typeof notification.on === 'function') {
        notification.on('click', () => {
          this._log('info', `notification.${type}.click`, { title });
          this._focusApp();
        });
        notification.on('close', () => {
          this._log('debug', `notification.${type}.close`, { title });
        });
        notification.on('failed', (_event, error) => {
          this._log('warn', `notification.${type}.failed`, {
            title,
            message: error && error.message ? error.message : String(error),
          });
        });
      }
      if (typeof notification.show === 'function') {
        notification.show();
      }
      this._log('info', `notification.${type}.shown`, { ...meta, title });
      return true;
    } catch (err) {
      this._log('error', `notification.${type}.error`, {
        title,
        message: err && err.message ? err.message : String(err),
      });
      return false;
    }
  }

  /**
   * Bring the main window to the foreground. Mirrors the tray icon's
   * click handler so notifications and the tray feel identical.
   */
  _focusApp() {
    const win = this._getMainWindow();
    if (!win) return;
    try {
      if (typeof win.show === 'function') win.show();
      if (
        typeof win.unminimize === 'function' &&
        typeof win.isMinimized === 'function' &&
        win.isMinimized()
      ) {
        win.unminimize();
      }
      if (typeof win.focus === 'function') win.focus();
    } catch (err) {
      this._log('warn', 'notification.focus_failed', {
        message: err && err.message ? err.message : String(err),
      });
    }
  }

  _log(level, message, meta) {
    const logger = this._logger;
    if (!logger || typeof logger[level] !== 'function') return;
    try {
      logger[level](message, meta);
    } catch {
      /* logger is best-effort */
    }
  }
}

/**
 * Default electron dependency bundle. Imports happen lazily so unit
 * tests can override the module before the constructor reads the
 * real `electron` package.
 */
const defaultElectronDeps = () => {
  try {
    // Use require to keep the syntax consistent with the rest of the
    // module (ESM). The conditional ensures we only pull from
    // `electron` when available.

    const electron = require('electron');
    return {
      Notification: electron && electron.Notification,
      isSupported:
        electron && electron.Notification ? () => electron.Notification.isSupported() : () => false,
    };
  } catch {
    return { Notification: null, isSupported: () => false };
  }
};

let _singleton = null;

/**
 * Initialise the global notification manager. Subsequent calls
 * return the same instance.
 */
export const initNotificationManager = (deps = {}) => {
  if (_singleton) return _singleton;
  _singleton = new NotificationManager(deps);
  return _singleton;
};

export const getNotificationManager = () => _singleton;

export const disposeNotificationManager = () => {
  if (_singleton) {
    _singleton.dispose();
    _singleton = null;
  }
};
