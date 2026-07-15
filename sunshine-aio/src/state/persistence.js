/**
 * Persistence layer for Sunshine AIO (Story 2-4).
 *
 * Wraps `electron-store` (a thin abstraction over `conf`) so the rest
 * of the renderer can read and write three persisted slices without
 * knowing about the underlying store API:
 *
 *   - worldConfig        : layout-level configuration for the 3D scene
 *                          (the seed driving planet placement, plus the
 *                          timestamp of the last "Regenerate World"
 *                          click).
 *   - installedApps      : mirror of the installState slice so an
 *                          installer that crashes can be recovered on
 *                          next launch without re-downloading the
 *                          installer payload.
 *   - navigationHistory  : the back-stack so an offline user lands on
 *                          the view they last used.
 *
 * Why an indirection around `electron-store`?
 *
 *   1. The renderer process runs in the context of an Electron
 *      renderer. `electron-store` ships as an ESM module that the
 *      renderer can import directly under `contextIsolation: true`,
 *      but the import itself touches `electron.app.getPath(...)` at
 *      construction time. Vitest runs under Node with no Electron
 *      globals, so the raw import would crash the test environment.
 *      Wrapping the import behind a factory function lets us inject
 *      a shim for tests and use the real store for production.
 *
 *   2. The rest of the renderer (renderer.js, planetFactory.js) only
 *      needs three operations: `get`, `set`, `clear`. We expose those
 *      narrow methods instead of leaking the entire `electron-store`
 *      surface so the API stays small and testable.
 *
 *   3. Corruption recovery. `electron-store` writes atomically, but a
 *      partially-written payload from an old or buggy release is
 *      possible. The wrapper catches the underlying Conf corruption
 *      error and falls back to defaults so a corrupt store never bricks
 *      the renderer on boot.
 *
 * Regenerating the world:
 *   `regenerateWorld()` rebuilds the deterministic `worldConfig.seed`
 *   and stamps the new seed with a fresh `lastRegeneratedAt`. It is
 *   the *only* path that mutates the world seed — every other write
 *   preserves it. The seeded layout is consumed by planetFactory.js
 *   (story 2-3) so changing the seed produces a new visible layout.
 *
 *   Crucially, `regenerateWorld` preserves the persisted `installedApps`
 *   list. A user who installed three apps and then asked for a new
 *   layout does not expect their installs to be forgotten — the planet
 *   colors must continue to reflect what is installed. The wrapper
 *   only writes the worldConfig and never touches installedApps, so
 *   the installState slice in the Zustand store is unaffected.
 */

import Store from 'electron-store';

import { DEFAULT_CATEGORIES } from './store.js';
import {
  DEFAULT_WORLD_CONFIG,
  DEFAULT_INSTALLED_APPS,
  DEFAULT_NAVIGATION_HISTORY,
} from './defaults.js';
import { pickFreshSeed, coerceSeed } from './seed.js';

/**
 * Stable storage key prefix. Used by both the wrapper and tests so a
 * future rename does not silently orphan user data.
 */
export const PERSIST_NAMESPACE = 'sunshine-aio';

const KEYS = Object.freeze({
  WORLD_CONFIG: 'worldConfig',
  INSTALLED_APPS: 'installedApps',
  NAVIGATION_HISTORY: 'navigationHistory',
  CORE_TOOLS: 'coreTools',
  CATEGORIES: 'categories',
});

/**
 * Default core-tools map. Mirrors the canonical `CORE_TOOL_IDS`
 * whitelist from `store.js`. Every value starts as `false`; the
 * renderer's "Regenerate World" affordance and the future
 * "reset to defaults" affordance rely on this snapshot to rebuild
 * the slice after a corruption event.
 */
const DEFAULT_CORE_TOOLS = Object.freeze({
  sunshine: false,
  vdd: false,
  playnite: false,
});

/**
 * Default categories snapshot. Mirrors the descriptors from
 * `DEFAULT_CATEGORIES` in `store.js` so the persistence wrapper can
 * rebuild the slice after a corruption event without an import cycle.
 */
const DEFAULT_CATEGORIES_PERSISTED = Object.freeze(
  DEFAULT_CATEGORIES.map((entry) => ({
    id: entry.id,
    name: entry.name,
    color: entry.color,
    installed: false,
  }))
);

/**
 * Default categories snapshot. Story 2-3 ships a small, stable list
 * of category descriptors — we mirror it here so the persistence
 * wrapper can rebuild the slice after a corruption event without
 * having to import the store module.
 */
export const DEFAULT_CATEGORIES_SNAPSHOT = Object.freeze(
  DEFAULT_CATEGORIES.map((entry) => ({
    id: entry.id,
    name: entry.name,
    color: entry.color,
    installed: false,
  }))
);

/**
 * Resolve the schema passed to electron-store. The schema is an
 * object describing each persisted key — electron-store uses it to
 * provide defaults when a key is missing and to validate types on
 * write. We export the schema so tests can build a parallel in-memory
 * shim without re-implementing the defaults.
 */
export const buildSchema = () => ({
  [KEYS.WORLD_CONFIG]: {
    type: 'object',
    properties: {
      seed: { type: 'number' },
      lastRegeneratedAt: { type: ['number', 'null'] },
      regenerated: { type: 'boolean' },
    },
    default: { ...DEFAULT_WORLD_CONFIG },
  },
  [KEYS.INSTALLED_APPS]: {
    type: 'array',
    default: [...DEFAULT_INSTALLED_APPS],
  },
  [KEYS.NAVIGATION_HISTORY]: {
    type: 'array',
    default: [...DEFAULT_NAVIGATION_HISTORY],
  },
});

/**
 * Sanitize the worldConfig persisted blob. Defensive against a
 * partially-written or tampered entry: every field is coerced into the
 * documented shape so the renderer never observes NaN seeds or a
 * non-boolean `regenerated` flag.
 */
const sanitizeWorldConfig = (raw) => {
  if (!raw || typeof raw !== 'object') {
    return { ...DEFAULT_WORLD_CONFIG };
  }
  // `coerceSeed` enforces the 32-bit safe-integer range. Anything
  // outside that range (MAX_SAFE_INTEGER + 1, NaN, floats) collapses
  // to the default so the bit math downstream always receives a
  // value it can encode without precision loss.
  const coerced = coerceSeed(raw.seed);
  const seed = coerced !== null ? coerced : DEFAULT_WORLD_CONFIG.seed;
  const lastRegeneratedAt =
    typeof raw.lastRegeneratedAt === 'number' && Number.isFinite(raw.lastRegeneratedAt)
      ? raw.lastRegeneratedAt
      : null;
  const regenerated = typeof raw.regenerated === 'boolean' ? raw.regenerated : false;
  return { seed, lastRegeneratedAt, regenerated };
};

/**
 * Sanitize the installedApps persisted blob. Drops non-object entries
 * and entries without a string id; preserves order so the order of
 * installs is stable across reloads.
 */
const sanitizeInstalledApps = (raw) => {
  if (!Array.isArray(raw)) {
    return [];
  }
  const seen = new Set();
  const result = [];
  for (const entry of raw) {
    if (!entry || typeof entry !== 'object') {
      continue;
    }
    if (typeof entry.id !== 'string' || !entry.id) {
      continue;
    }
    if (seen.has(entry.id)) {
      continue;
    }
    seen.add(entry.id);
    result.push({ ...entry });
  }
  return result;
};

/**
 * Sanitize the navigation history. We accept any array of strings —
 * validation against the `APP_VIEW` enum lives in the store, not the
 * persistence layer.
 */
const sanitizeNavigationHistory = (raw) => {
  if (!Array.isArray(raw)) {
    return [];
  }
  return raw.filter((entry) => typeof entry === 'string');
};

/**
 * The canonical core-tool ids, mirrored from `store.js`. Used to
 * validate persisted payloads so a forged entry cannot smuggle an
 * arbitrary key (e.g. `"__proto__"`) into the adapter's read path.
 */
const PERSISTED_CORE_TOOL_IDS = Object.freeze(['sunshine', 'vdd', 'playnite']);

/**
 * Sanitize the coreTools persisted blob. Only the canonical tool ids
 * are accepted; every value is coerced to a boolean so a stringy
 * `"true"` cannot poison the slice. Missing keys fall back to
 * `false` so a partial payload cannot accidentally mark a tool as
 * installed.
 */
const sanitizeCoreTools = (raw) => {
  const result = { ...DEFAULT_CORE_TOOLS };
  if (!raw || typeof raw !== 'object') {
    return result;
  }
  for (const id of PERSISTED_CORE_TOOL_IDS) {
    result[id] = Boolean(raw[id]);
  }
  return result;
};

/**
 * Sanitize the categories persisted blob. Drops entries without a
 * string id, normalises `name` to a string (falls back to the id),
 * accepts a numeric or CSS hex `color`, and coerces `installed` to
 * a boolean. Order is preserved and duplicates are dropped (first
 * occurrence wins). Extra keys are silently dropped so a caller
 * cannot inject arbitrary fields into the slice.
 */
const sanitizeCategories = (raw) => {
  if (!Array.isArray(raw)) {
    return DEFAULT_CATEGORIES_PERSISTED.map((entry) => ({ ...entry }));
  }
  const seen = new Set();
  const result = [];
  for (const entry of raw) {
    if (!entry || typeof entry !== 'object' || typeof entry.id !== 'string' || !entry.id) {
      continue;
    }
    if (seen.has(entry.id)) {
      continue;
    }
    seen.add(entry.id);
    let color = entry.color;
    if (typeof color === 'number') {
      color = Number.isFinite(color) && color >= 0 ? color | 0 : null;
    } else if (typeof color !== 'string') {
      color = null;
    }
    result.push({
      id: entry.id,
      name: typeof entry.name === 'string' && entry.name ? entry.name : entry.id,
      color,
      installed: Boolean(entry.installed),
    });
  }
  return result;
};

/**
 * Default factory: lazy-import electron-store so the unit tests can
 * run with a shim. The factory returns a fresh `Store` instance on
 * every call so each call to `createPersistence({ useMemory: false })`
 * gets an isolated store — handy for parallel test cases.
 *
 * The `Store` constructor accepts a `name` for the file under
 * `app.getPath('userData')`. We expose the name through the options
 * so the production wiring can pick a stable file name while the
 * tests can pick a per-test one.
 */
const defaultStoreFactory = (opts = {}) => {
  const name = typeof opts.name === 'string' && opts.name ? opts.name : PERSIST_NAMESPACE;
  // electron-store v11 is ESM-only and accepts a `defaults` object.
  // We pass our schema via `defaults` so the first read returns a
  // well-formed object even if the file does not yet exist on disk.
  return new Store({
    name,
    defaults: {
      [KEYS.WORLD_CONFIG]: { ...DEFAULT_WORLD_CONFIG },
      [KEYS.INSTALLED_APPS]: [...DEFAULT_INSTALLED_APPS],
      [KEYS.NAVIGATION_HISTORY]: [...DEFAULT_NAVIGATION_HISTORY],
      [KEYS.CORE_TOOLS]: { ...DEFAULT_CORE_TOOLS },
      [KEYS.CATEGORIES]: DEFAULT_CATEGORIES_PERSISTED.map((entry) => ({ ...entry })),
    },
  });
};

/**
 * Build the in-memory shim used by tests. Implements just enough of
 * the electron-store surface (`get`, `set`, `delete`, `clear`,
 * `store`) for the wrapper to exercise every code path without
 * touching the disk.
 *
 * The shim stores values under the same `store` namespace used by
 * `conf`, mirroring the production layout so a future migration
 * between the two only needs to swap the factory.
 */
export const createMemoryStore = (initial = {}) => {
  const data = { store: { ...initial } };
  return {
    get: (key, fallback) => {
      if (key in data.store) {
        return data.store[key];
      }
      return fallback;
    },
    set: (key, value) => {
      data.store[key] = value;
    },
    delete: (key) => {
      delete data.store[key];
    },
    clear: () => {
      // Preserve keys that are *not* in our namespace — defensive
      // against a future Conf version that stashes its own metadata
      // under non-namespaced keys. In practice the shim has no such
      // keys, but the guard makes the test surface harder to misuse.
      for (const key of Object.keys(data.store)) {
        if (
          key in initial ||
          key === KEYS.WORLD_CONFIG ||
          key === KEYS.INSTALLED_APPS ||
          key === KEYS.NAVIGATION_HISTORY ||
          key === KEYS.CORE_TOOLS ||
          key === KEYS.CATEGORIES
        ) {
          delete data.store[key];
        }
      }
    },
    raw: () => ({ ...data.store }),
  };
};

/**
 * Build the wrapper. Accepts a `store` instance directly OR a
 * `storeFactory` that returns one. The factory form lets the caller
 * control when (and how many times) the underlying store is created.
 *
 * Options:
 *   - store        : pre-built store instance (skips the factory)
 *   - storeFactory : () => Store — called lazily on first read
 *   - useMemory    : boolean — build an in-memory shim (tests)
 *   - name         : string — name passed to electron-store
 *   - now          : () => number — clock source (defaults to Date.now)
 *   - logger       : (msg, meta) => void — diagnostic sink
 *
 * @param {Object} [opts]
 */
export const createPersistence = (opts = {}) => {
  const logger = typeof opts.logger === 'function' ? opts.logger : () => {};
  const now = typeof opts.now === 'function' ? opts.now : () => Date.now();
  // Resolve the on-disk filename *once* at the entry point so every
  // code path (default factory, custom storeFactory, the renderer's
  // call site) sees the same namespaced value. Without this, a caller
  // that omits `name` would see `undefined` flow through to a
  // `storeFactory` it injected — and the on-disk file would land
  // under electron-store's default name (`config`), which is the
  // collision we are trying to prevent.
  const effectiveName = typeof opts.name === 'string' && opts.name ? opts.name : PERSIST_NAMESPACE;

  let store;
  if (opts.store) {
    store = opts.store;
  } else if (opts.useMemory) {
    store = createMemoryStore({
      [KEYS.WORLD_CONFIG]: { ...DEFAULT_WORLD_CONFIG },
      [KEYS.INSTALLED_APPS]: [...DEFAULT_INSTALLED_APPS],
      [KEYS.NAVIGATION_HISTORY]: [...DEFAULT_NAVIGATION_HISTORY],
      [KEYS.CORE_TOOLS]: { ...DEFAULT_CORE_TOOLS },
      [KEYS.CATEGORIES]: DEFAULT_CATEGORIES_PERSISTED.map((entry) => ({ ...entry })),
    });
  } else if (typeof opts.storeFactory === 'function') {
    store = opts.storeFactory({ name: effectiveName });
  } else {
    store = defaultStoreFactory({ name: effectiveName });
  }

  /**
   * Wrap every store call in a try/catch so a corrupt payload never
   * bricks the renderer on boot. The catch falls back to the
   * documented default for the requested key. The recovery is logged
   * through the injected logger so a developer can spot the
   * regression in dev tools without crashing the renderer.
   */
  const safeGet = (key, fallback) => {
    try {
      const value = store.get(key, fallback);
      return value === undefined ? fallback : value;
    } catch (err) {
      logger('[Persistence] corrupt entry detected, falling back to default', {
        key,
        error: err && err.message ? err.message : String(err),
      });
      return fallback;
    }
  };

  const safeSet = (key, value) => {
    try {
      store.set(key, value);
      return true;
    } catch (err) {
      logger('[Persistence] failed to write entry', {
        key,
        error: err && err.message ? err.message : String(err),
      });
      return false;
    }
  };

  return {
    /** The underlying store instance. Exposed for advanced callers. */
    raw: () => store,

    KEYS,

    /**
     * Read the worldConfig slice. Always returns a sanitized object
     * so the caller never has to defend against partial writes.
     */
    getWorldConfig: () => {
      const raw = safeGet(KEYS.WORLD_CONFIG, { ...DEFAULT_WORLD_CONFIG });
      return sanitizeWorldConfig(raw);
    },

    /**
     * Replace the worldConfig slice. The new value is sanitized so a
     * caller cannot poison the persisted blob with a NaN seed or a
     * string `lastRegeneratedAt`.
     */
    setWorldConfig: (next) => {
      const sanitized = sanitizeWorldConfig(next);
      return safeSet(KEYS.WORLD_CONFIG, sanitized);
    },

    /**
     * Read the installedApps slice. Always returns a sanitized array.
     */
    getInstalledApps: () => {
      const raw = safeGet(KEYS.INSTALLED_APPS, [...DEFAULT_INSTALLED_APPS]);
      return sanitizeInstalledApps(raw);
    },

    /**
     * Replace the installedApps slice. The new value is sanitized
     * (non-object entries and entries without a string id are
     * dropped) so a caller cannot inject malformed data.
     */
    setInstalledApps: (next) => {
      const sanitized = sanitizeInstalledApps(next);
      return safeSet(KEYS.INSTALLED_APPS, sanitized);
    },

    /**
     * Read the navigation history. Always returns a sanitized array
     * of strings.
     */
    getNavigationHistory: () => {
      const raw = safeGet(KEYS.NAVIGATION_HISTORY, [...DEFAULT_NAVIGATION_HISTORY]);
      return sanitizeNavigationHistory(raw);
    },

    /**
     * Replace the navigation history. Non-string entries are
     * silently dropped.
     */
    setNavigationHistory: (next) => {
      const sanitized = sanitizeNavigationHistory(next);
      return safeSet(KEYS.NAVIGATION_HISTORY, sanitized);
    },

    /**
     * Read the coreTools slice. Always returns a sanitized object
     * restricted to the canonical tool ids so a forged payload
     * cannot smuggle arbitrary keys into the read path.
     */
    getCoreTools: () => {
      const raw = safeGet(KEYS.CORE_TOOLS, { ...DEFAULT_CORE_TOOLS });
      return sanitizeCoreTools(raw);
    },

    /**
     * Replace the coreTools slice. The new value is sanitized
     * (unknown keys dropped, every value coerced to a boolean) so a
     * caller cannot inject malformed data.
     */
    setCoreTools: (next) => {
      const sanitized = sanitizeCoreTools(next);
      return safeSet(KEYS.CORE_TOOLS, sanitized);
    },

    /**
     * Read the categories slice. Always returns a sanitized array of
     * `{ id, name, color, installed }` objects; duplicates are
     * dropped, missing ids fall back to the documented defaults.
     */
    getCategories: () => {
      const raw = safeGet(
        KEYS.CATEGORIES,
        DEFAULT_CATEGORIES_PERSISTED.map((entry) => ({ ...entry }))
      );
      return sanitizeCategories(raw);
    },

    /**
     * Replace the categories slice. The new value is sanitized so a
     * caller cannot inject malformed data.
     */
    setCategories: (next) => {
      const sanitized = sanitizeCategories(next);
      return safeSet(KEYS.CATEGORIES, sanitized);
    },

    /**
     * Regenerate the world. Picks a new non-negative integer seed
     * using the injected clock + a counter so two rapid clicks in
     * the same millisecond still produce different seeds. The new
     * `lastRegeneratedAt` is stamped from the clock.
     *
     * Critically: this method only writes the `worldConfig` slice.
     * `installedApps` is NEVER touched — the user's installed apps
     * are preserved across a regenerate, so the planet colors
     * continue to reflect what is installed under the new layout.
     *
     * @param {Object} [opts]
     * @param {number} [opts.seed]  Force a specific seed (tests only).
     * @returns {{ seed: number, lastRegeneratedAt: number, regenerated: true }}
     */
    regenerateWorld: (opts = {}) => {
      const current = sanitizeWorldConfig(safeGet(KEYS.WORLD_CONFIG, { ...DEFAULT_WORLD_CONFIG }));
      // The forced seed must be a non-negative integer in the safe
      // range. Anything outside that range (MAX_SAFE_INTEGER + 1,
      // negatives, NaN, non-numbers) collapses to a fresh pick from
      // the shared counter so the bit math in `pickFreshSeed` always
      // operates on a value it can safely encode.
      const forcedSeed = coerceSeed(opts.seed);
      const seed = forcedSeed !== null ? forcedSeed : pickFreshSeed(current.seed, now());
      const next = {
        seed,
        lastRegeneratedAt: now(),
        regenerated: true,
      };
      safeSet(KEYS.WORLD_CONFIG, next);
      return next;
    },

    /**
     * Drop every persisted slice. Used by tests and by the future
     * "Reset to factory defaults" affordance. Does NOT clear the
     * underlying store's internal metadata — only the three
     * documented slices.
     */
    clear: () => {
      safeSet(KEYS.WORLD_CONFIG, { ...DEFAULT_WORLD_CONFIG });
      safeSet(KEYS.INSTALLED_APPS, [...DEFAULT_INSTALLED_APPS]);
      safeSet(KEYS.NAVIGATION_HISTORY, [...DEFAULT_NAVIGATION_HISTORY]);
      safeSet(KEYS.CORE_TOOLS, { ...DEFAULT_CORE_TOOLS });
      safeSet(
        KEYS.CATEGORIES,
        DEFAULT_CATEGORIES_PERSISTED.map((entry) => ({ ...entry }))
      );
    },
  };
};

export default createPersistence;
