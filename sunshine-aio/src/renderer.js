import './styles.css';
import { buildFriendlyMessage, formatReportedError, toLogPayload } from './errorHandler.js';

/**
 * Sunshine AIO Renderer Process
 *
 * This file handles the UI rendering for the desktop application.
 * Current implementation: Basic HTML rendering with stylesheet, plus a
 * global error trap that surfaces uncaught errors to the main-process
 * logger via window.electronAPI.log and shows a friendly toast in the DOM.
 *
 * For Story 1.3+ (Python backend integration):
 * - Use IPC via window.electronAPI to communicate with main process
 * - IPC channels (will be defined in Story 1.3):
 *   - 'app:get-installed-apps' - Get list of installed applications
 *   - 'app:install-app' - Install an application
 *   - 'app:uninstall-app' - Uninstall an application
 *   - 'app:get-catalog' - Get application catalog
 *
 * Example IPC usage (to be implemented in Story 1.3+):
 *   const apps = await window.electronAPI.invoke('app:get-installed-apps');
 *
 * Error handling example:
 *   try {
 *     const apps = await window.electronAPI.invoke('app:get-installed-apps');
 *     console.log('Installed apps:', apps);
 *   } catch (error) {
 *     console.error('Failed to get apps:', error.message);
 *     // Show user-friendly error message
 *   }
 *
 * UI Framework: Plain JavaScript for now, consider React for complex UI later
 * State Management: Will use Zustand in Story 2.1
 */

/**
 * Send the error to the main-process logger. Falls back to console.error
 * when the bridge is unavailable (e.g. running unit tests in node).
 *
 * Returns a promise that resolves once the main process has acknowledged
 * the log (or after falling back to console). Callers can chain UI
 * actions — such as showing a toast — on this promise so the user is
 * not told "we logged it" if logging silently failed.
 */
const reportError = (level, message, err) => {
  const payload = toLogPayload(level, message, err);
  if (window.electronAPI && typeof window.electronAPI.log === 'function') {
    try {
      const result = window.electronAPI.log(payload.level, payload.message, payload.meta);
      // The bridge returns a promise (or a sync value). Normalize to a
      // promise so we can attach a .catch fallback for IPC failures.
      if (result && typeof result.then === 'function') {
        return result.catch((ipcErr) => {
          console[level === 'error' ? 'error' : 'warn'](formatReportedError(payload), ipcErr);
        });
      }
      return Promise.resolve(result);
    } catch (bridgeErr) {
      // Synchronous throw from the bridge (e.g. preload crashed). Fall
      // through to the console fallback.
      console[level === 'error' ? 'error' : 'warn'](formatReportedError(payload), bridgeErr);
      return Promise.resolve();
    }
  }

  console[level === 'error' ? 'error' : 'warn'](formatReportedError(payload));
  return Promise.resolve();
};

/**
 * Show a transient toast at the bottom-right of the screen.
 * Multiple toasts stack. Each auto-dismisses after `durationMs`.
 */
const showErrorToast = (message, durationMs = 5000) => {
  const root = document.body || document.documentElement;
  if (!root) {
    return;
  }

  const toast = document.createElement('div');
  toast.className = 'saio-error-toast';
  toast.setAttribute('role', 'alert');
  toast.textContent = message;

  const dismiss = () => {
    if (toast.parentNode) {
      toast.parentNode.removeChild(toast);
    }
  };

  toast.addEventListener('click', dismiss);
  root.appendChild(toast);

  // Trigger CSS transition on next tick
  requestAnimationFrame(() => {
    toast.classList.add('saio-error-toast--visible');
  });

  setTimeout(dismiss, durationMs);
};

/**
 * The single integration point that wires a thrown/rejected error into both
 * the main-process logger and a user-visible toast. Used by the window
 * `error` and `unhandledrejection` listeners below.
 *
 * The toast is shown only after the main-process logger has acknowledged
 * the entry. Otherwise a transient IPC failure would leave the user
 * staring at a "logged to file" message that was never actually logged.
 */
const handleRendererError = (err, sourceLabel) => {
  reportError('error', sourceLabel, err).then(() => {
    showErrorToast(buildFriendlyMessage(err));
  });
};

// ---- Global error traps ----------------------------------------------------

if (typeof window !== 'undefined') {
  window.addEventListener('error', (event) => {
    const err = event.error || new Error(event.message || 'Unknown error');
    handleRendererError(err, 'Unhandled renderer error');
  });

  window.addEventListener('unhandledrejection', (event) => {
    const reason = event.reason;
    const err = reason instanceof Error ? reason : new Error(String(reason));
    handleRendererError(err, 'Unhandled promise rejection in renderer');
  });
}

// ---- Python backend integration (Story 1.3) -------------------------------
//
// On bootstrap we send a single ping to the Python backend via the
// preload-exposed window.electronAPI.pythonPing() and write the result
// into a status element in the DOM. The DOM is touched defensively so
// the renderer does not crash in test contexts where document is absent.

const PYTHON_STATUS_ID = 'python-status';

const setPythonStatus = (status, message) => {
  if (typeof document === 'undefined') return;
  const node = document.getElementById(PYTHON_STATUS_ID);
  if (!node) return;
  // Reset all modifier classes so we always reflect the latest state.
  node.classList.remove(
    'saio-python-status--ok',
    'saio-python-status--error',
    'saio-python-status--pending'
  );
  node.classList.add(`saio-python-status--${status}`);
  node.dataset.status = status;
  node.textContent = message;
};

const pingPythonBackend = async () => {
  if (!window.electronAPI || typeof window.electronAPI.pythonPing !== 'function') {
    // Running in a context without the bridge (unit tests, SSR). The
    // user should still see an actionable status — otherwise the
    // "Initializing…" pending state would persist forever and they
    // would have no way to tell whether the bridge was missing vs
    // merely slow.
    setPythonStatus('error', 'Python backend bridge unavailable');
    reportError('warn', 'Python backend bridge unavailable on electronAPI', null);
    return;
  }
  setPythonStatus('pending', 'Contacting Python backend…');
  try {
    const response = await window.electronAPI.pythonPing();
    if (response && response.ok && response.result && response.result.result === 'pong') {
      setPythonStatus('ok', `Python backend OK — ${response.result.result}`);
      reportError('info', 'Python backend ping succeeded', { result: response.result });
    } else {
      const reason = (response && response.error) || 'unknown error';
      setPythonStatus('error', `Python backend error: ${reason}`);
      reportError('warn', 'Python backend ping returned a non-success response', { reason });
    }
  } catch (err) {
    // IPC-level failure (preload crashed, channel rejected, etc.).
    setPythonStatus('error', 'Python backend unavailable');
    reportError('warn', 'Python backend ping failed at IPC layer', err);
  }
};

// ---- Settings UI (Story 1.4) -----------------------------------------------
//
// A small "minimize to tray" toggle + admin-status indicator. The
// toggle is wired to `electronAPI.setMinimizeToTray` and reads from
// `electronAPI.getSettings` on bootstrap. The admin section reads
// `getAdminStatus` and exposes a button that calls
// `requestAdminElevation` when the process is not already elevated.

const MINIMIZE_TOGGLE_ID = 'minimize-to-tray-toggle';
const MINIMIZE_TOGGLE_STATUS_ID = 'minimize-to-tray-status';
const ADMIN_STATUS_ID = 'admin-status';
const ADMIN_ELEVATE_BTN_ID = 'admin-elevate-btn';

const setMinimizeStatus = (message, kind = 'info') => {
  if (typeof document === 'undefined') return;
  const node = document.getElementById(MINIMIZE_TOGGLE_STATUS_ID);
  if (!node) return;
  node.dataset.kind = kind;
  node.textContent = message;
};

const setAdminStatus = (message, kind = 'info') => {
  if (typeof document === 'undefined') return;
  const node = document.getElementById(ADMIN_STATUS_ID);
  if (!node) return;
  node.dataset.kind = kind;
  node.textContent = message;
};

const initSettingsUI = async () => {
  if (typeof document === 'undefined') return;
  const api = window.electronAPI;
  if (!api) return;

  const toggle = document.getElementById(MINIMIZE_TOGGLE_ID);
  if (toggle) {
    // Render initial state from the persisted settings record so the
    // toggle survives across launches.
    try {
      const res = await api.getSettings();
      if (res && res.ok && res.settings && typeof res.settings.minimizeToTray === 'boolean') {
        toggle.checked = res.settings.minimizeToTray;
        setMinimizeStatus(
          res.settings.minimizeToTray
            ? 'Closing the window will hide Sunshine AIO in the system tray.'
            : 'Closing the window will quit Sunshine AIO.',
          res.settings.minimizeToTray ? 'ok' : 'info'
        );
      }
    } catch (err) {
      reportError('warn', 'Failed to load settings for UI', err);
    }

    // Persist on change. We do NOT optimistically update the toggle's
    // checked state — we wait for the IPC response so the user sees
    // the persisted value (avoids a flash of "on" if the write fails).
    //
    // We capture the pre-click value at the moment of the event so
    // that any rollback (failure path) restores the user's earlier
    // intent rather than the logical inverse of whatever we last
    // observed. The previous implementation rolled back to `!enabled`,
    // which corrupted UI state if the user double-clicked the
    // checkbox before the first IPC returned: the second click would
    // flip the checkbox to a third state, then the first IPC's
    // failure would roll back to the inverse of the second click —
    // which is NOT the user's original value.
    toggle.addEventListener('change', async (event) => {
      // Disable the checkbox while the IPC is in flight so a
      // rapid second click cannot race the rollback path. The
      // disabled state is restored in the `finally` block.
      const previousValue = !event.target.checked;
      toggle.disabled = true;
      const enabled = Boolean(event.target.checked);
      try {
        const res = await api.setMinimizeToTray(enabled);
        if (res && res.ok) {
          setMinimizeStatus(
            enabled
              ? 'Closing the window will hide Sunshine AIO in the system tray.'
              : 'Closing the window will quit Sunshine AIO.',
            enabled ? 'ok' : 'info'
          );
          reportError('info', 'Minimize-to-tray preference saved', { enabled });
        } else {
          // Roll back to the pre-click value, not the inverse of
          // the latest click — the user might have toggled multiple
          // times while the IPC was in flight.
          event.target.checked = previousValue;
          setMinimizeStatus(
            `Failed to save preference: ${(res && res.error) || 'unknown error'}`,
            'error'
          );
        }
      } catch (err) {
        event.target.checked = previousValue;
        reportError('error', 'Failed to save minimize-to-tray preference', err);
        setMinimizeStatus('Failed to save preference (see toast).', 'error');
      } finally {
        toggle.disabled = false;
      }
    });
  }
};

const initAdminUI = async () => {
  if (typeof document === 'undefined') return;
  const api = window.electronAPI;
  if (!api) return;

  const btn = document.getElementById(ADMIN_ELEVATE_BTN_ID);
  try {
    const res = await api.getAdminStatus();
    if (res && res.ok) {
      if (res.isAdmin) {
        setAdminStatus('Running as administrator.', 'ok');
        if (btn) {
          btn.disabled = true;
          btn.textContent = 'Already elevated';
        }
      } else {
        setAdminStatus('Running as standard user. Some operations require elevation.', 'warn');
        if (btn) btn.disabled = false;
      }
    } else {
      setAdminStatus('Could not determine privilege state.', 'error');
      if (btn) btn.disabled = true;
    }
  } catch (err) {
    reportError('warn', 'Failed to query admin status', err);
    setAdminStatus('Could not determine privilege state.', 'error');
    if (btn) btn.disabled = true;
    return;
  }

  if (btn) {
    btn.addEventListener('click', async () => {
      // Disable the button BEFORE updating the status text so a
      // second click cannot observe a half-updated state. The
      // single-state-update helper is the local `updateState`
      // closure — it sets BOTH the status and the button in
      // lockstep so the user never sees a flash of stale text.
      const updateState = (message, kind, opts = {}) => {
        setAdminStatus(message, kind);
        if (opts.enableButton === true) {
          btn.disabled = false;
        } else if (opts.enableButton === false) {
          btn.disabled = true;
        }
      };
      updateState('Requesting administrator privileges…', 'pending', { enableButton: false });
      try {
        const res = await api.requestAdminElevation();
        if (res && res.ok) {
          if (res.alreadyElevated) {
            updateState('Already running as administrator.', 'ok', { enableButton: false });
          } else {
            updateState('Elevation requested. The app will restart shortly.', 'ok', {
              enableButton: false,
            });
          }
        } else {
          updateState(
            `Failed to request elevation: ${(res && res.reason) || 'unknown error'}`,
            'error',
            { enableButton: true }
          );
        }
      } catch (err) {
        reportError('error', 'Failed to request admin elevation', err);
        updateState('Failed to request elevation (see toast).', 'error', { enableButton: true });
      }
    });
  }
};

// ---- Notifications UI (Story 1.5) -----------------------------------------
//
// A small "Test Notification" button wires to the notification
// channels exposed by `electronAPI.notifyTest`. The button is also a
// live echo surface: the most recent notification result is written
// to a status element so a developer can see, at a glance, whether
// the host supports toasts and whether the manager accepted the
// request.

const NOTIFY_TEST_BTN_ID = 'notify-test-btn';
const NOTIFY_TEST_STATUS_ID = 'notify-test-status';

const setNotifyTestStatus = (message, kind = 'info') => {
  if (typeof document === 'undefined') return;
  const node = document.getElementById(NOTIFY_TEST_STATUS_ID);
  if (!node) return;
  node.dataset.kind = kind;
  node.textContent = message;
};

const initNotificationsUI = () => {
  if (typeof document === 'undefined') return;
  const api = window.electronAPI;
  if (!api) return;

  const btn = document.getElementById(NOTIFY_TEST_BTN_ID);
  if (!btn) return;

  btn.addEventListener('click', async () => {
    btn.disabled = true;
    setNotifyTestStatus('Sending test notification…', 'pending');
    try {
      if (typeof api.notifyTest !== 'function') {
        setNotifyTestStatus('Notification bridge is not available.', 'error');
        reportError('warn', 'Notification bridge missing on electronAPI', null);
        return;
      }
      const res = await api.notifyTest();
      if (res && res.ok) {
        setNotifyTestStatus('Test notification sent. Check the Windows notification area.', 'ok');
      } else {
        const reason = (res && res.reason) || 'unknown error';
        setNotifyTestStatus(`Test notification failed: ${reason}`, 'error');
        reportError('warn', 'Test notification failed', { reason });
      }
    } catch (err) {
      setNotifyTestStatus('Test notification failed (see toast).', 'error');
      reportError('error', 'Test notification threw', err);
    } finally {
      btn.disabled = false;
    }
  });
};

// ---- Bootstrap -------------------------------------------------------------

const bootstrap = () => {
  try {
    const api = typeof window !== 'undefined' ? window.electronAPI : undefined;
    if (api && typeof api.log === 'function') {
      api
        .log(
          'info',
          'Renderer bootstrapped',
          typeof window !== 'undefined' ? { url: window.location.href } : {}
        )
        .catch(() => {
          /* logging is best-effort */
        });
    }
  } catch (err) {
    reportError('warn', 'Renderer bootstrap logging failed', err);
  }

  // Fire-and-forget: the DOM updates asynchronously as the IPC call resolves.
  pingPythonBackend();
  initSettingsUI();
  initAdminUI();
  initNotificationsUI();
};

if (typeof document !== 'undefined') {
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bootstrap, { once: true });
  } else {
    bootstrap();
  }
}

// Expose for tests so they can exercise the DOM update path without
// reaching into module-private state. Kept tiny on purpose.
if (typeof window !== 'undefined') {
  window.__sunshineRenderer = {
    pingPythonBackend,
    setPythonStatus,
    initSettingsUI,
    initAdminUI,
    initNotificationsUI,
    setMinimizeStatus,
    setAdminStatus,
    setNotifyTestStatus,
  };
}
