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
 */
const reportError = (level, message, err) => {
  const payload = toLogPayload(level, message, err);
  try {
    if (window.electronAPI && typeof window.electronAPI.log === 'function') {
      window.electronAPI.log(payload.level, payload.message, payload.meta);
      return;
    }
  } catch {
    // bridge failed; fall through to console fallback
  }

  console[level === 'error' ? 'error' : 'warn'](formatReportedError(payload));
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
 */
const handleRendererError = (err, sourceLabel) => {
  reportError('error', sourceLabel, err);
  showErrorToast(buildFriendlyMessage(err));
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
};

if (typeof document !== 'undefined') {
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bootstrap, { once: true });
  } else {
    bootstrap();
  }
}
