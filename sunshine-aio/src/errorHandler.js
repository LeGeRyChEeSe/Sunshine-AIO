/**
 * Error handling helpers for the renderer.
 *
 * These helpers are deliberately kept free of DOM access so they can be
 * unit-tested in the node environment. The DOM glue (window listeners,
 * toast element creation) lives in renderer.js which wires these helpers
 * to the global window/document.
 *
 * The renderer cannot write to disk directly. It forwards errors to the
 * main process via the preload `window.electronAPI.log` bridge; that
 * bridge is the single entry point that puts renderer errors into the
 * shared log file.
 */

/**
 * Build a user-friendly error message from a raw error.
 *
 * The goal is to give the user enough info to act, but not to drown them
 * in stack traces — those go to the log file instead.
 */
// Match network-related error messages. Kept narrow on purpose: a broad
// /network|fetch/ would catch benign phrases like "fetched the user
// preferences" or "refetch on focus" and misclassify them as network
// errors. The patterns below correspond to the actual error text that
// Node, the DOM fetch API, and common HTTP libraries emit.
const NETWORK_ERROR_PATTERN =
  /\b(network error|network request failed|failed to fetch|fetch failed|networkerror|net::err_)/i;

export const buildFriendlyMessage = (err) => {
  if (err instanceof Error) {
    if (err.name === 'TypeError') {
      return 'Something went wrong while processing data. Please try again.';
    }
    if (err.name === 'NetworkError' || NETWORK_ERROR_PATTERN.test(err.message)) {
      return 'A network problem was detected. Please check your connection and try again.';
    }
    return 'An unexpected error occurred. The technical details have been saved to the log file.';
  }
  if (typeof err === 'string') {
    return 'An unexpected error occurred. Please try again.';
  }
  return 'An unexpected error occurred. The technical details have been saved to the log file.';
};

const VALID_LEVELS = new Set(['debug', 'info', 'warn', 'error']);

/**
 * Validate and normalise a log level to one of the supported values.
 * Falls back to 'info' for anything unknown so the caller cannot crash
 * the logger with an arbitrary string.
 */
export const normalizeLogLevel = (level) => (VALID_LEVELS.has(level) ? level : 'info');

/**
 * Wrap a raw error into a serializable payload suitable for the
 * `window.electronAPI.log` IPC call. Strips the stack to the message
 * field so the renderer never sends massive strings.
 */
export const toLogPayload = (level, message, err) => {
  const safeLevel = normalizeLogLevel(level);
  const safeMessage = typeof message === 'string' ? message : String(message ?? '');

  let detail;
  if (err instanceof Error) {
    detail = { name: err.name, message: err.message };
  } else if (err && typeof err === 'object') {
    detail = err;
  } else if (err !== undefined && err !== null) {
    detail = { value: String(err) };
  }

  return { level: safeLevel, message: safeMessage, meta: detail };
};

/**
 * Format the payload into a single-line description useful in tests
 * and for the console fallback.
 */
export const formatReportedError = (payload) => {
  if (!payload) return '';
  const { level, message, meta } = payload;
  const metaPart =
    meta && typeof meta === 'object' && meta.message
      ? ` (${meta.name || 'Error'}: ${meta.message})`
      : '';
  return `[${level}] ${message}${metaPart}`;
};
