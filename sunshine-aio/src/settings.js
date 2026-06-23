import { app } from 'electron';
import path from 'node:path';
import fs from 'node:fs';

/**
 * Persisted application settings.
 *
 * Settings are stored as JSON under the Electron `userData` directory
 * so they survive app restarts without polluting the project root.
 * We avoid pulling in `electron-store` as a dependency for the small
 * surface area we need (a single boolean today) and to keep the
 * dependency graph lean for Story 1.4. If the schema grows in a
 * later story we should swap this for `electron-store` rather than
 * rolling our own.
 *
 * File format: `{ "minimizeToTray": boolean, ... }`. The file is
 * created on first write; missing files default to `minimizeToTray
 * = false` so the first launch behaves like a normal windowed app.
 *
 * Forward-compat: unknown keys in the on-disk file are PRESERVED on
 * disk (so a future binary can read its own keys without an older
 * binary wiping them out) but FILTERED OUT of the in-memory return
 * value (so callers in this binary cannot accidentally depend on
 * keys it does not know about).
 */

const DEFAULT_SETTINGS = Object.freeze({
  minimizeToTray: false,
});

const DEFAULTS_BY_KEY = {
  minimizeToTray: false,
};

const isPlainObject = (value) =>
  value !== null && typeof value === 'object' && !Array.isArray(value);

const coerceMinimizeToTray = (raw) => {
  if (typeof raw === 'boolean') return raw;
  if (typeof raw === 'number') {
    // 1 / any non-zero number -> true. 0 / NaN -> false.
    if (Number.isFinite(raw)) return raw !== 0;
    return DEFAULTS_BY_KEY.minimizeToTray;
  }
  if (typeof raw === 'string') {
    if (raw === 'true' || raw === '1') return true;
    if (raw === 'false' || raw === '0' || raw === '') return false;
  }
  return DEFAULTS_BY_KEY.minimizeToTray;
};

const COERCERS = {
  minimizeToTray: coerceMinimizeToTray,
};

/**
 * Normalize an arbitrary object into a known-shape settings record.
 * Unknown keys are dropped — this is the *return-value* filter so
 * callers never see fields they did not ask for.
 */
const normalize = (raw) => {
  if (!isPlainObject(raw)) return { ...DEFAULT_SETTINGS };
  const out = { ...DEFAULT_SETTINGS };
  for (const key of Object.keys(DEFAULTS_BY_KEY)) {
    if (key in raw) {
      out[key] = COERCERS[key](raw[key]);
    }
  }
  return out;
};

/**
 * Read the raw on-disk settings without normalization. Returns
 * `null` when the file does not exist or cannot be parsed. Used
 * internally for shallow-merge so unknown keys are preserved on
 * disk; never exposed to callers.
 */
const readRawSettings = (filePath) => {
  try {
    if (!fs.existsSync(filePath)) return null;
    const text = fs.readFileSync(filePath, 'utf8');
    const parsed = JSON.parse(text);
    return isPlainObject(parsed) ? parsed : null;
  } catch {
    return null;
  }
};

/**
 * Load settings synchronously. Returns the default record if no file
 * exists or the file is malformed. Logging is optional so the module
 * remains usable in unit-test contexts that have no logger.
 */
export const loadSettings = (deps = {}) => {
  const filePath = deps.filePath || defaultSettingsPath(deps.app || app);
  const logger = deps.logger;
  const raw = readRawSettings(filePath);
  const normalized = normalize(raw);
  if (logger && typeof logger.info === 'function') {
    logger.info('Settings loaded', { filePath, settings: normalized });
  }
  return normalized;
};

/**
 * Persist settings synchronously. The settings object is shallow-merged
 * onto the existing on-disk record (NOT onto the normalized view) so
 * unknown keys survive across writes — that is what makes the file
 * forward-compat. Unknown keys on disk are preserved as-is in the
 * written JSON; the in-memory return is normalized.
 *
 * Returns the persisted (normalized) record on success, `null` on
 * failure.
 */
export const saveSettings = (settings, deps = {}) => {
  if (!isPlainObject(settings)) {
    return null;
  }
  const filePath = deps.filePath || defaultSettingsPath(deps.app || app);
  const logger = deps.logger;
  // Merge onto the RAW on-disk record so we do not erase keys this
  // binary does not know about. If the file is missing or unreadable
  // we start from an empty object — defaults are filled in by the
  // normalize step.
  const rawCurrent = readRawSettings(filePath) || {};
  const rawNext = { ...rawCurrent, ...settings };
  const next = normalize(rawNext);
  try {
    const dir = path.dirname(filePath);
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }
    fs.writeFileSync(filePath, JSON.stringify(rawNext, null, 2), 'utf8');
    if (logger && typeof logger.info === 'function') {
      logger.info('Settings saved', { filePath, settings: next });
    }
    return next;
  } catch (err) {
    if (logger && typeof logger.error === 'function') {
      logger.error('Failed to save settings', {
        filePath,
        message: err && err.message ? err.message : String(err),
      });
    }
    return null;
  }
};

/**
 * Pure setter for `minimizeToTray`. Returns the new settings record
 * (or null on failure). Provided as a thin convenience for IPC handlers.
 */
export const setMinimizeToTray = (enabled, deps = {}) => {
  return saveSettings({ minimizeToTray: Boolean(enabled) }, deps);
};

/**
 * Compute the default settings file path under the Electron userData
 * directory. Falls back to a relative path in non-Electron test
 * contexts so the module is unit-testable without an `app` object.
 */
export const defaultSettingsPath = (appInstance) => {
  if (appInstance && typeof appInstance.getPath === 'function') {
    try {
      const userData = appInstance.getPath('userData');
      return path.join(userData, 'settings.json');
    } catch {
      // fall through
    }
  }
  return path.resolve(process.cwd(), 'settings.json');
};

export const DEFAULT_SETTINGS_RECORD = DEFAULT_SETTINGS;
