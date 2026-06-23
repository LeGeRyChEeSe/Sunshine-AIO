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
    // Running in a context without the bridge (unit tests, SSR). Skip
    // silently rather than logging an error that the user cannot act on.
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
  window.__sunshineRenderer = { pingPythonBackend, setPythonStatus };
}
