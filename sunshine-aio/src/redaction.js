/**
 * Shared redaction + sanitization helpers.
 *
 * Centralised here (rather than re-exported from main.js) so any
 * module — including `notifications.js`, which is imported BY
 * `main.js` and therefore cannot safely import from it — can apply
 * the same defenses before user-supplied text reaches the file
 * logger or the OS toast surface.
 */

/**
 * Known secret-bearing keys. Any meta / params key matching one of these
 * is redacted before being written to the file logger. Keys are matched
 * case-insensitively because secrets / passwords are commonly
 * mis-capitalized by accident.
 */
export const SECRET_KEYS = new Set([
  'password',
  'passwd',
  'pwd',
  'token',
  'secret',
  'apikey',
  'api_key',
  'authorization',
  'auth',
  'cookie',
  'session',
  'sessionid',
  'session_id',
  'privatekey',
  'private_key',
  'access_token',
  'refresh_token',
]);

const isSecretKey = (key) => {
  if (typeof key !== 'string') return false;
  return SECRET_KEYS.has(key.toLowerCase());
};

/**
 * Recursively redact secret-looking keys and string values that match
 * common credential patterns (JWT, long base64 blobs, bearer tokens).
 * The original object is NOT mutated; a redacted shallow copy is
 * returned. Arrays are walked. Functions / symbols / undefined are
 * preserved as their safeStringify equivalents.
 *
 * Depth is capped to prevent a malicious caller from constructing a
 * payload that pins the CPU for arbitrarily long.
 */
const REDACT_MAX_DEPTH = 8;

/**
 * Credential patterns matched against string VALUES (independent of
 * the surrounding key). Order matters: the longer, more specific
 * patterns run first so the generic "Bearer" doesn't shadow a more
 * informative match. Each pattern is anchored loosely so a token
 * embedded inside a longer URL or log line still trips the regex.
 */
const VALUE_PATTERNS = [
  // JWT three-segment base64url. The standard form starts with eyJ
  // (base64url of '{"') but the matcher below is more permissive so
  // a JWT-shaped envelope without the standard prefix is still
  // caught (e.g. truncated tests, alternate header bytes).
  /\b[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}\b/,
  // JWT two-segment base64url (used by some legacy test fixtures
  // and refresh tokens).
  /\b[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\b/,
  // AWS access key ID (AKIA / ASIA prefix + 16 chars)
  /\b(?:AKIA|ASIA)[0-9A-Z]{16}\b/,
  // GitHub personal access token (ghp_, gho_, ghu_, ghs_, ghr_)
  /\bgh[pousr]_[A-Za-z0-9]{30,}\b/,
  // Slack tokens (xox[bpars]-…)
  /\bxox[bpars]-[A-Za-z0-9-]{10,}\b/,
  // Generic Bearer token (NOT anchored to start so a token buried
  // inside a longer string is still caught). Require the value to be
  // at least 8 base64url-ish chars so a stray "Bearer N" in a URL
  // fragment does not false-positive.
  /\bBearer\s+[A-Za-z0-9_\-.=]{8,}/i,
  // Generic api_key=… / password=… in query strings / form data
  /\b(?:api[_-]?key|password|passwd|pwd|secret|token)\s*[=:]\s*["']?([A-Za-z0-9_\-.+/=]{6,})/i,
  // Long base64url blob (40+ chars, no dots) — catches many random
  // shared secrets that do not match any specific provider format.
  /\b[A-Za-z0-9_\-]{40,}\b/,
];

export const redactSecrets = (value, depth = 0) => {
  if (depth > REDACT_MAX_DEPTH) return '[redacted: too deep]';
  if (value === null || value === undefined) return value;
  if (typeof value === 'string') {
    for (const pattern of VALUE_PATTERNS) {
      if (pattern.test(value)) {
        return '[redacted]';
      }
    }
    return value;
  }
  if (typeof value !== 'object') return value;
  if (Array.isArray(value)) {
    return value.map((item) => redactSecrets(item, depth + 1));
  }
  const out = {};
  for (const key of Object.keys(value)) {
    if (isSecretKey(key)) {
      out[key] = '[redacted]';
    } else {
      try {
        out[key] = redactSecrets(value[key], depth + 1);
      } catch {
        out[key] = '[unserializable]';
      }
    }
  }
  return out;
};

/**
 * Strip control / ANSI escape sequences from a string. Used by the
 * notification IPC handler to keep renderer-supplied titles and
 * messages from injecting CRLF or escape sequences into either the
 * Windows toast surface or the file logger.
 */
export const stripControlChars = (value) => {
  if (typeof value !== 'string') return '';

  return value.replace(/[\x00-\x1f\x7f]/g, '');
};

/**
 * Cap a string to a maximum length (in characters). Returns the
 * trimmed value, with no ellipsis added — callers that want an
 * ellipsis should append their own. Used to bound the size of
 * renderer-supplied notification bodies before they reach the OS
 * toast surface or the file logger.
 */
export const capStringLength = (value, maxLen) => {
  if (typeof value !== 'string') return '';
  return value.length > maxLen ? value.slice(0, maxLen) : value;
};

/**
 * Sanitize a renderer-supplied string before it reaches a Windows
 * toast or the file logger. Strips control characters and caps
 * length. Centralised here so the same shape is applied to title,
 * body, and the meta-preview snapshot.
 */
export const sanitizeUserString = (value, maxLen = 200) => {
  const stripped = stripControlChars(typeof value === 'string' ? value : '');
  return capStringLength(stripped, maxLen);
};
