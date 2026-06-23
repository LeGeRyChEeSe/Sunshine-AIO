/**
 * Sunshine AIO — Shared main-window focus helper
 *
 * The tray icon and the notification manager both need the same
 * window-restore sequence when the user invokes them:
 *
 *   1. Show the window (in case it is hidden behind the tray).
 *   2. Unminimize if it was minimised.
 *   3. Focus it so it comes to the foreground.
 *
 * Centralising the sequence in a single helper prevents the two
 * call sites from drifting (e.g. one of them forgets to call
 * `unminimize()` and the user sees a window pop to the taskbar but
 * not actually appear).
 *
 * Behaviour contract:
 *
 *   * The helper NEVER throws. If any of the three calls raises, the
 *     error is captured and reported via the optional logger so the
 *     caller's handler (notification click / tray click) does not
 *     surface an uncaught exception in the main process.
 *
 *   * The helper is a no-op when the window reference is null
 *     (`getMainWindow()` returning null means the window has not been
 *     created yet, or has been destroyed).
 *
 *   * Each of `show` / `unminimize` / `focus` is feature-checked so a
 *     stub window from unit tests does not have to provide every
 *     method. `unminimize` is also gated by `isMinimized()` returning
 *     true to avoid spurious state changes on Windows.
 *
 * @param {() => (object | null)} getMainWindow
 *        Accessor returning the current main window (may be null).
 * @param {object} [options]
 * @param {object} [options.logger]
 *        Optional logger. Must expose `warn(message, meta)` if
 *        provided; missing methods are tolerated silently.
 * @param {string} [options.eventName]
 *        Optional logical name for the caller (e.g.
 *        'notification.focus' or 'tray.click'). Forwarded to the
 *        logger so the operator can tell which surface failed.
 */
export const restoreMainWindow = (getMainWindow, { logger, eventName } = {}) => {
  let win = null;
  try {
    win = typeof getMainWindow === 'function' ? getMainWindow() : null;
  } catch {
    // Accessor threw; treat as "no window" and skip.
    win = null;
  }
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
    if (logger && typeof logger.warn === 'function') {
      try {
        const name = typeof eventName === 'string' && eventName ? eventName : 'window.focus';
        logger.warn(`${name}_failed`, {
          message: err && err.message ? err.message : String(err),
        });
      } catch {
        // Logger itself failed; swallow.
      }
    }
  }
};
