/**
 * Zustand store for Sunshine AIO (Story 2-1 + Story 2-2 + Story 2-3).
 *
 * Centralizes five slices of application state:
 *   - worldState       : the 3D solar-system view (planets, statuses, FPS).
 *   - installState     : which apps are installed, in-progress, or failed.
 *   - navigationState  : current view, focus, history stack for back nav.
 *   - coreTools        : the three core tools wired into the sun's
 *                        satellite indicators (sunshine / vdd / playnite).
 *   - categories       : the app-category descriptors that drive the
 *                        planet factory (one planet per category).
 *
 * Story 2-2 adds the `coreTools` slice. The sun component subscribes
 * via `sceneController.setInstalledTools(coreTools)` so the satellite
 * indicators brighten when a tool is reported as installed. The slice
 * is *derived* from `installState.installedApps` — the store keeps the
 * map in sync through actions rather than asking callers to mutate
 * two slices.
 *
 * Story 2-3 adds the `categories` slice. Each category carries the
 * data the planet factory needs to lay out a planet (orbit radius,
 * phase, color, installed flag). The factory subscribes to this slice
 * via `useAppStore.subscribe` and applies updates through
 * `sceneController.setPlanetInstalled`. The sun's `coreTools` slice
 * stays the source of truth for the satellites; the categories slice
 * is the source of truth for the planets. The two never overlap.
 *
 * `worldState.fps` semantics: this value is the **rolling-average**
 * FPS emitted by the scene controller's FPS monitor (a 60-frame
 * rolling window, refreshed every ~2s). It is NOT an instantaneous
 * 1/frame-delta reading. Consumers (story 2-2 / 2-3 overlays,
 * diagnostics, etc.) should treat the value as a smoothed
 * representation of renderer throughput rather than a per-frame
 * measurement. The value is also clamped to [0, 240] so a long tab
 * pause does not produce a 1e10 reading when the monitor finally
 * flushes.
 *
 * Persistence:
 *   The store is wrapped with the `persist` middleware. State survives a
 *   renderer reload (F5 during development) and an app restart (window
 *   close + reopen). Only the slices marked persistable are written to
 *   localStorage; ephemeral fields (FPS samples, transient errors) are
 *   excluded via the `partialize` callback.
 *
 *   `version` is bumped whenever the persisted shape changes; the
 *   migration table returns the old state forward-compatible so a user
 *   upgrading the app never loses their saved world layout.
 *
 * The store accepts an injected `storage` so unit tests can drive the
 * middleware with an in-memory shim rather than touching `window.localStorage`.
 */

import { createStore } from 'zustand/vanilla';
import { persist, createJSONStorage, subscribeWithSelector } from 'zustand/middleware';

import { pickFreshSeed, coerceSeed } from './seed.js';
import { DEFAULT_WORLD_CONFIG } from './defaults.js';
import { installPersistenceBridge } from './persistenceBridge.js';

export const STORE_NAME = 'sunshine-aio-app-state';
export const STORE_VERSION = 2;

export const PLANET_STATUS = Object.freeze({
  UNINSTALLED: 'uninstalled',
  INSTALLING: 'installing',
  INSTALLED: 'installed',
  FAILED: 'failed',
  UPDATING: 'updating',
});

export const APP_VIEW = Object.freeze({
  SOLAR_SYSTEM: 'solar-system',
  PLANET_DETAIL: 'planet-detail',
  APP_DETAIL: 'app-detail',
  SETTINGS: 'settings',
});

export const CORE_TOOL_IDS = Object.freeze(['sunshine', 'vdd', 'playnite']);

const initialWorldState = () => ({
  planets: [],
  fps: 0,
  sceneInitialized: false,
});

/**
 * Re-exported so existing test code and consumers that imported
 * `DEFAULT_WORLD_CONFIG` from `store.js` keep working. The actual
 * definition lives in `./defaults.js` so `store.js` and
 * `persistence.js` share a single source of truth.
 */
export { DEFAULT_WORLD_CONFIG };

const initialWorldConfig = () => ({
  seed: DEFAULT_WORLD_CONFIG.seed,
  lastRegeneratedAt: DEFAULT_WORLD_CONFIG.lastRegeneratedAt,
  regenerated: DEFAULT_WORLD_CONFIG.regenerated,
});

const initialInstallState = () => ({
  installedApps: [],
  inProgressApps: [],
  failedApps: [],
  lastUpdatedAt: null,
});

const initialNavigationState = () => ({
  currentView: APP_VIEW.SOLAR_SYSTEM,
  focusedPlanetId: null,
  focusedAppId: null,
  // Seed the history with the initial view so `goBack` can restore it
  // after the first navigation away.
  history: [APP_VIEW.SOLAR_SYSTEM],
});

/**
 * Core-tools map. Story 2-2 keys off the canonical `CORE_TOOL_IDS`
 * list (Sunshine, Virtual Display Driver, Playnite). Every core tool
 * starts in the `false` (not installed) state. The literal shape is
 * identical in semantics to a `reduce` build but is faster, easier to
 * read, and lines up with the frozen `CORE_TOOL_IDS` whitelist — the
 * keys cannot drift between the source list and the default state.
 */
const initialCoreTools = () => ({
  sunshine: false,
  vdd: false,
  playnite: false,
});

/**
 * Default category descriptors. Story 2-3 ships a small, stable list
 * of planets that map to common Sunshine-AIO install categories:
 *   - games      : the launchers (Steam, Epic, etc.) that produce games
 *   - streaming  : streaming helpers (audio, virtual camera, etc.)
 *   - utilities  : utility tools (Playnite, VDD, etc.)
 *   - emulators  : emulator frontends
 *
 * The list is intentionally short and seedable: a developer can grow
 * it via `setCategories(...)` without re-wiring the renderer. The
 * default `installed` flags are `false` so the freshly-booted solar
 * system renders every planet in its gray "uninstalled" state.
 */
export const DEFAULT_CATEGORIES = Object.freeze([
  Object.freeze({ id: 'games', name: 'Games', color: 0x4fc3f7 }),
  Object.freeze({ id: 'streaming', name: 'Streaming', color: 0x81c784 }),
  Object.freeze({ id: 'utilities', name: 'Utilities', color: 0xffb74d }),
  Object.freeze({ id: 'emulators', name: 'Emulators', color: 0xba68c8 }),
]);

/**
 * Build the initial categories slice from the DEFAULT_CATEGORIES list.
 * Every category starts in the `false` (not installed) state so a
 * freshly-booted solar system renders every planet in its gray form.
 * The returned array is a fresh shallow copy — callers are free to
 * mutate the slice without affecting the default export.
 */
const initialCategories = () =>
  DEFAULT_CATEGORIES.map((category) => ({
    id: category.id,
    name: category.name,
    color: category.color,
    installed: false,
  }));

const initialState = () => ({
  worldState: initialWorldState(),
  worldConfig: initialWorldConfig(),
  installState: initialInstallState(),
  navigationState: initialNavigationState(),
  coreTools: initialCoreTools(),
  categories: initialCategories(),
});

/**
 * Only persist slices that are safe to round-trip across reloads:
 *   - worldState.planets (planet layout)
 *   - worldConfig (seed driving the planet factory's layout)
 *   - installState (installed apps list)
 *   - navigationState (current view, history)
 *   - coreTools (so the sun's satellite indicators survive a restart)
 *   - categories (so a user's per-category overrides survive)
 * Ephemeral fields (fps, sceneInitialized, inProgressApps, lastUpdatedAt)
 * are excluded so we don't persist transient runtime metrics.
 */
const partialize = (state) => ({
  worldState: {
    planets: state.worldState.planets,
  },
  worldConfig: { ...state.worldConfig },
  installState: {
    installedApps: state.installState.installedApps,
    failedApps: state.installState.failedApps,
    lastUpdatedAt: state.installState.lastUpdatedAt,
  },
  navigationState: {
    currentView: state.navigationState.currentView,
    focusedPlanetId: state.navigationState.focusedPlanetId,
    focusedAppId: state.navigationState.focusedAppId,
    history: state.navigationState.history,
  },
  coreTools: { ...state.coreTools },
  categories: state.categories.map((category) => ({ ...category })),
});

/**
 * In-memory storage adapter. Matches the `StateStorage` interface so the
 * persist middleware can use it in test environments without `window.localStorage`.
 */
export const createMemoryStorage = () => {
  const map = new Map();
  return {
    getItem: (name) => (map.has(name) ? map.get(name) : null),
    setItem: (name, value) => {
      map.set(name, value);
    },
    removeItem: (name) => {
      map.delete(name);
    },
  };
};

/**
 * Default factory used in production. Resolves `window.localStorage` lazily
 * so importing this module on the server side (or in unit tests with jsdom
 * shims missing localStorage) does not throw.
 */
const defaultStorage = () => {
  if (typeof window !== 'undefined' && window.localStorage) {
    return createJSONStorage(() => window.localStorage);
  }
  // Fall back to in-memory storage when no DOM is available.
  return createJSONStorage(() => createMemoryStorage());
};

/**
 * Throttle helper. The persistence bridge owns its own copy of this
 * helper inside `persistenceBridge.js`; it is duplicated here as a
 * stub so this module keeps a stable module surface for any caller
 * that imported `throttleTrailing` directly. New code should import
 * from `persistenceBridge.js` instead.
 *
 * @deprecated Import from `./persistenceBridge.js` instead.
 */
const throttleTrailing = (fn, waitMs) => {
  if (typeof fn !== 'function') {
    return () => {};
  }
  const wait = Math.max(0, Number(waitMs) || 0);
  let pending = null;
  let timer = null;
  const flush = () => {
    timer = null;
    if (pending) {
      const args = pending;
      pending = null;
      try {
        fn(...args);
      } catch {
        // Swallow: throttled writers must never throw into a
        // subscriber. Errors are surfaced through the logger passed
        // to the writer (if any) or the global console.
      }
    }
  };
  const throttled = (...args) => {
    pending = args;
    if (timer === null) {
      timer = setTimeout(flush, wait);
    }
  };
  throttled.flush = flush;
  throttled.cancel = () => {
    pending = null;
    if (timer !== null) {
      clearTimeout(timer);
      timer = null;
    }
  };
  return throttled;
};

/**
 * Migration table. Each entry receives `(persistedState, version)` and
 * returns a state compatible with the new version.
 *
 * Resolution contract: when the persisted version has no registered
 * migrator, the persisted blob is treated as untrusted and discarded.
 * `runMigration` returns `undefined` in that case, which Zustand's
 * `persist` middleware interprets as "no persisted state — use
 * `initialState`". This prevents a corrupt or stale shape from being
 * merged with the new defaults via `mergeSlices` and silently producing
 * a hybrid object that satisfies none of the new invariants.
 *
 * Version history:
 *   1 -> 2: Story 2-4. The new `worldConfig` slice is hydrated from
 *           the persistence layer on boot. There is no on-disk
 *           representation of `worldConfig` in v1 blobs, so the
 *           migrator seeds it with the default (seed = 42). The
 *           install/navigation/categories/coreTools slices round-trip
 *           unchanged — they were already persisted in v1.
 */
const migrations = {
  1: (persistedState) => {
    if (!persistedState || typeof persistedState !== 'object') {
      return persistedState;
    }
    return {
      ...persistedState,
      worldConfig: { ...DEFAULT_WORLD_CONFIG },
    };
  },
};

/**
 * Surface "bumped STORE_VERSION but no migrators" at module load.
 * Without this, the API is unstable: a developer can update the
 * version constant and forget to add a migration entry, and the only
 * symptom is silent data loss in the field. The assertion turns that
 * omission into a hard error in the same tick that the mismatch is
 * introduced — but ONLY in development/test environments. In a
 * production renderer (Electron Forge packaged build) we downgrade
 * the failure to a console warning so a stale module never bricks
 * the renderer window for end users mid-upgrade (the previous
 * throw-eagerly behavior surfaced as a blank window with a Vite
 * overlay, which is hostile to users who cannot read the error).
 */
const IS_DEV =
  typeof process !== 'undefined' && process.env && process.env.NODE_ENV !== 'production';

const assertMigrationsConsistent = () => {
  const message =
    STORE_VERSION > 1 && Object.keys(migrations).length === 0
      ? `[Store] STORE_VERSION is ${STORE_VERSION} but the migrations table is empty. ` +
        'Add a migrator entry for the previous version before bumping STORE_VERSION.'
      : null;
  // Forward direction: every version below STORE_VERSION must have a
  // migrator, otherwise older persisted blobs will be discarded and
  // the user loses their state silently.
  let forwardMessage = null;
  for (let v = 1; v < STORE_VERSION; v += 1) {
    if (typeof migrations[v] !== 'function') {
      forwardMessage =
        `[Store] Missing migrator for version ${v} -> ${STORE_VERSION}. ` +
        'Add a migrator entry to the migrations table.';
      break;
    }
  }
  if (!message && !forwardMessage) {
    return;
  }
  if (IS_DEV) {
    throw new Error(message || forwardMessage);
  } else {
    console.warn(`[Store] Migration table out of sync: ${message || forwardMessage}`);
  }
};
assertMigrationsConsistent();

const runMigration = (persistedState, version) => {
  if (!persistedState) {
    return persistedState;
  }
  const migrator = migrations[version];
  if (typeof migrator === 'function') {
    return migrator(persistedState, version);
  }
  // Unknown older version with no migrator: hard reset.
  // Returning undefined tells persist to fall back to initialState().
  return undefined;
};

/**
 * Whitelist of recognized top-level slices. `mergeSlices` builds the
 * rehydrated state exclusively from this list — any extra key present
 * in the persisted blob is dropped and surfaced via a warn-level log
 * line. This is a defensive measure against forged or accidentally
 * mutated storage entries: the spread-based merge used to accept any
 * `Object.keys(persistedState)` and could surface arbitrary
 * undocumented keys to selectors.
 */
const KNOWN_SLICES = Object.freeze([
  'worldState',
  'worldConfig',
  'installState',
  'navigationState',
  'coreTools',
  'categories',
]);

/**
 * Shallow-merge each top-level slice individually rather than
 * replacing whole slices. This preserves runtime-only fields like
 * `worldState.fps` and `worldState.sceneInitialized` across rehydrate
 * even when those keys are intentionally excluded from the persisted
 * blob via `partialize`.
 *
 * The merged root is built explicitly from `KNOWN_SLICES`; any
 * additional key present in the persisted blob is logged and
 * dropped. The previous implementation used a root-level
 * `{ ...currentState, ...persistedState }` spread, which would have
 * silently injected arbitrary keys (e.g. a forged `toString`
 * override or a custom `__extra__` field) into the runtime state.
 */
const mergeSlices = (persistedState, currentState) => {
  if (!persistedState) {
    return currentState;
  }
  const merged = {};
  for (const key of KNOWN_SLICES) {
    merged[key] = currentState[key];
  }
  for (const key of Object.keys(persistedState)) {
    if (!KNOWN_SLICES.includes(key)) {
      console.warn(
        `[Store] mergeSlices: ignoring unknown persisted key "${key}". ` +
          'Whitelisted slices are: ' +
          KNOWN_SLICES.join(', ')
      );
      continue;
    }
    const persistedSlice = persistedState[key];
    const currentSlice = currentState[key];
    if (
      persistedSlice &&
      typeof persistedSlice === 'object' &&
      !Array.isArray(persistedSlice) &&
      currentSlice &&
      typeof currentSlice === 'object' &&
      !Array.isArray(currentSlice)
    ) {
      merged[key] = { ...currentSlice, ...persistedSlice };
    } else {
      merged[key] = persistedSlice;
    }
  }
  return merged;
};

/**
 * Sanitize the user-supplied core-tools map. Only accepts keys from
 * CORE_TOOL_IDS; coerces every value to a boolean so a stray string
 * like `"true"` cannot poison the slice. Keys absent from the input
 * stay at their default `false` so a partial payload cannot accidentally
 * mark a tool as installed.
 */
const normalizeCoreTools = (tools) => {
  const result = { sunshine: false, vdd: false, playnite: false };
  if (!tools || typeof tools !== 'object') {
    return result;
  }
  for (const id of CORE_TOOL_IDS) {
    result[id] = Boolean(tools[id]);
  }
  return result;
};

/**
 * Sanitize a partial worldConfig update. Accepts any subset of the
 * documented fields and returns a fully-populated object. Numeric
 * seeds must be non-negative finite integers; timestamps must be
 * finite numbers (or `null`); the boolean must be coerced. Any
 * unknown field is silently dropped so a caller cannot extend the
 * slice shape.
 */
const sanitizeWorldConfig = (next) => {
  const fallback = initialWorldConfig();
  if (!next || typeof next !== 'object') {
    return fallback;
  }
  // `coerceSeed` rejects anything outside the 32-bit safe-integer
  // range. Out-of-range inputs collapse to `null` so we fall back
  // to the default — a `Number.MAX_SAFE_INTEGER + 1` (or a NaN)
  // can never reach the planet factory's bit math.
  const coerced = coerceSeed(next.seed);
  const seed = coerced !== null ? coerced : fallback.seed;
  const lastRegeneratedAt =
    next.lastRegeneratedAt === null
      ? null
      : typeof next.lastRegeneratedAt === 'number' && Number.isFinite(next.lastRegeneratedAt)
        ? next.lastRegeneratedAt
        : fallback.lastRegeneratedAt;
  const regenerated =
    typeof next.regenerated === 'boolean' ? next.regenerated : fallback.regenerated;
  return { seed, lastRegeneratedAt, regenerated };
};

/**
 * Sanitize a single category descriptor. Drops entries without a
 * string `id`, normalises `name` to a string (falls back to the id),
 * coerces `color` to a finite non-negative integer (falls back to the
 * default cyan 0x4fc3f7), and coerces `installed` to a boolean.
 * Extra keys are dropped so a caller cannot inject arbitrary fields
 * into the slice.
 */
const sanitizeCategory = (entry) => {
  if (!entry || typeof entry !== 'object' || typeof entry.id !== 'string' || !entry.id) {
    return null;
  }
  let color = 0x4fc3f7;
  if (typeof entry.color === 'number' && Number.isFinite(entry.color) && entry.color >= 0) {
    color = entry.color | 0;
  } else if (typeof entry.color === 'string' && /^#[0-9a-f]{3,8}$/i.test(entry.color)) {
    // Accept CSS hex strings so a UI layer can pass through colours
    // without forcing a numeric conversion. The hex is left as-is and
    // resolved by the planet factory's color sanitizer downstream.
    color = entry.color;
  }
  return {
    id: entry.id,
    name: typeof entry.name === 'string' && entry.name ? entry.name : entry.id,
    color,
    installed: Boolean(entry.installed),
  };
};

/**
 * Normalise a full categories array. Drops invalid entries, preserves
 * order, and deduplicates by id (first occurrence wins). Returns a
 * fresh array so the caller can safely spread or replace the slice.
 */
const normalizeCategories = (entries) => {
  if (!Array.isArray(entries)) {
    return initialCategories();
  }
  const seen = new Set();
  const result = [];
  for (const entry of entries) {
    const safe = sanitizeCategory(entry);
    if (!safe || seen.has(safe.id)) {
      continue;
    }
    seen.add(safe.id);
    result.push(safe);
  }
  return result;
};

/**
 * Build the Zustand store. Accepts an optional `storage` override (mainly
 * for tests). The returned store has the documented actions attached.
 *
 * @param {Object} [opts]
 * @param {import('zustand/middleware').PersistStorage<any>} [opts.storage]
 * @param {string} [opts.name]      Override the storage key (tests).
 * @param {boolean} [opts.skipHydration]  Defer hydration to the caller.
 * @param {Object} [opts.persistence]    Optional persistence adapter
 *   (the wrapper from `state/persistence.js`). When supplied, the
 *   store will:
 *     1. Hydrate the `worldConfig`, `installedApps`, and
 *        `navigationHistory` slices from disk on boot.
 *     2. Mirror every state mutation back to disk through a
 *        trailing-edge throttle (default 250 ms) so a burst of
 *        store updates collapses into a single disk write.
 */
export const createAppStore = (opts = {}) => {
  const storage = opts.storage || defaultStorage();
  const name = opts.name || STORE_NAME;
  const skipHydration = Boolean(opts.skipHydration);
  const persistence = opts.persistence || null;
  const throttleMs = typeof opts.throttleMs === 'number' ? opts.throttleMs : 250;
  const persistenceLogger =
    typeof opts.persistenceLogger === 'function' ? opts.persistenceLogger : () => {};

  const store = createStore(
    // `subscribeWithSelector` lets callers pass a selector to
    // `subscribe(selector, listener)`. Without this middleware, the
    // vanilla store fires on every state change — including FPS
    // updates, navigation transitions, and any other slice mutation
    // — which is wasteful for selectors that only care about a single
    // slice (e.g. the sun's `coreTools` watcher in renderer.js).
    subscribeWithSelector(
      persist(
        // `set` is required by Zustand's state creator signature; `get` is kept
        // for symmetry with future actions that will need cross-slice reads.
        // eslint-disable-next-line no-unused-vars
        (set, get) => ({
          ...initialState(),

          // ---------- worldState actions ----------
          setPlanetStatus: (planetId, status) =>
            set((state) => {
              const next = state.worldState.planets.map((planet) =>
                planet.id === planetId ? { ...planet, status } : planet
              );
              return {
                worldState: { ...state.worldState, planets: next },
              };
            }),

          upsertPlanet: (planet) =>
            set((state) => {
              const existingIndex = state.worldState.planets.findIndex((p) => p.id === planet.id);
              const planets =
                existingIndex === -1
                  ? [...state.worldState.planets, planet]
                  : state.worldState.planets.map((p, i) =>
                      i === existingIndex ? { ...p, ...planet } : p
                    );
              return { worldState: { ...state.worldState, planets } };
            }),

          setFps: (fps) =>
            set((state) => ({
              worldState: {
                ...state.worldState,
                fps: Number.isFinite(fps) ? fps : 0,
              },
            })),

          markSceneInitialized: (initialized = true) =>
            set((state) => ({
              worldState: { ...state.worldState, sceneInitialized: !!initialized },
            })),

          // ---------- worldConfig actions (Story 2-4) ----------
          /**
           * Replace the worldConfig slice. The new value is sanitized
           * so a caller cannot poison the slice with a NaN seed or a
           * string `lastRegeneratedAt`. This is the only path that
           * mutates `worldConfig` from the renderer's perspective —
           * the persistence layer writes the same shape.
           */
          setWorldConfig: (next) =>
            set((state) => ({
              worldConfig: sanitizeWorldConfig({ ...state.worldConfig, ...next }),
            })),

          /**
           * Pick a fresh seed and stamp `lastRegeneratedAt`. Returns
           * the new config so the caller can react (e.g. re-build
           * the planet factory). Does NOT touch the installState
           * slice — installed apps survive a regenerate.
           *
           * @param {Object} [opts]
           * @param {number} [opts.seed]   Force a specific seed (tests).
           * @param {number} [opts.now]    Override the clock source.
           */
          regenerateWorld: (opts = {}) => {
            const ts =
              typeof opts.now === 'number' && Number.isFinite(opts.now) ? opts.now : Date.now();
            // `coerceSeed` validates the forced seed against the
            // 32-bit safe-integer range. Anything outside the range
            // (MAX_SAFE_INTEGER + 1, NaN, strings) collapses to
            // `null` so we fall through to the counter-driven
            // `pickFreshSeed`. The previous slice's seed is read
            // inside the `set` callback so the new seed is guaranteed
            // to differ from whatever is currently stored.
            const forcedSeed = coerceSeed(opts.seed);
            let chosenSeed = null;
            set((state) => {
              const sanitized = sanitizeWorldConfig({
                ...state.worldConfig,
                seed: forcedSeed !== null ? forcedSeed : pickFreshSeed(state.worldConfig.seed, ts),
                lastRegeneratedAt: ts,
                regenerated: true,
              });
              chosenSeed = sanitized.seed;
              return { worldConfig: sanitized };
            });
            return {
              seed: chosenSeed,
              lastRegeneratedAt: ts,
              regenerated: true,
            };
          },

          /**
           * Replace the seed (without bumping the regenerate
           * timestamp). Useful for tests and for a future "import a
           * layout from a seed" feature. Out-of-range seeds are
           * silently coerced to the default so a caller cannot
           * poison the slice with a NaN or an integer that would
           * lose precision in the planet factory's bit math.
           */
          setSeed: (seed) => {
            const coerced = coerceSeed(seed);
            set((state) => ({
              worldConfig: sanitizeWorldConfig({
                ...state.worldConfig,
                seed: coerced !== null ? coerced : DEFAULT_WORLD_CONFIG.seed,
              }),
            }));
          },

          // ---------- installState actions ----------
          addInstalledApp: (app) =>
            set((state) => {
              const exists = state.installState.installedApps.some((entry) => entry.id === app.id);
              if (exists) {
                return {
                  installState: {
                    ...state.installState,
                    installedApps: state.installState.installedApps.map((entry) =>
                      entry.id === app.id ? { ...entry, ...app } : entry
                    ),
                    lastUpdatedAt: Date.now(),
                  },
                };
              }
              return {
                installState: {
                  ...state.installState,
                  installedApps: [
                    ...state.installState.installedApps,
                    { ...app, installedAt: app.installedAt || Date.now() },
                  ],
                  lastUpdatedAt: Date.now(),
                },
              };
            }),

          removeInstalledApp: (appId) =>
            set((state) => ({
              installState: {
                ...state.installState,
                installedApps: state.installState.installedApps.filter(
                  (entry) => entry.id !== appId
                ),
                lastUpdatedAt: Date.now(),
              },
            })),

          startInstallProgress: (appId) =>
            set((state) => {
              if (state.installState.inProgressApps.includes(appId)) {
                return state;
              }
              return {
                installState: {
                  ...state.installState,
                  inProgressApps: [...state.installState.inProgressApps, appId],
                  failedApps: state.installState.failedApps.filter((id) => id !== appId),
                },
              };
            }),

          finishInstallProgress: (appId, outcome) =>
            set((state) => {
              const inProgressApps = state.installState.inProgressApps.filter((id) => id !== appId);
              const failedApps =
                outcome === 'failed' && !state.installState.failedApps.includes(appId)
                  ? [...state.installState.failedApps, appId]
                  : state.installState.failedApps.filter((id) => id !== appId);
              return {
                installState: {
                  ...state.installState,
                  inProgressApps,
                  failedApps,
                  lastUpdatedAt: Date.now(),
                },
              };
            }),

          // ---------- navigationState actions ----------
          setCurrentView: (view) =>
            set((state) => {
              if (!Object.values(APP_VIEW).includes(view)) {
                return state;
              }
              // Skip pushing the same view we're already on to avoid
              // cluttering the history stack with no-op transitions.
              if (state.navigationState.currentView === view) {
                return state;
              }
              return {
                navigationState: {
                  ...state.navigationState,
                  currentView: view,
                  history: [...state.navigationState.history, view].slice(-20),
                },
              };
            }),

          setFocusedPlanet: (planetId) =>
            set((state) => ({
              navigationState: {
                ...state.navigationState,
                focusedPlanetId: planetId,
              },
            })),

          setFocusedApp: (appId) =>
            set((state) => ({
              navigationState: {
                ...state.navigationState,
                focusedAppId: appId,
              },
            })),

          goBack: () =>
            set((state) => {
              const history = [...state.navigationState.history];
              // The history stack includes the current view as its last
              // entry. Discard it, then promote the entry below to the
              // current view. If we are already at the bottom, leave the
              // state untouched so the UI doesn't fall off the start of
              // the timeline.
              history.pop();
              const previous = history[history.length - 1];
              if (!previous || previous === state.navigationState.currentView) {
                return state;
              }
              return {
                navigationState: {
                  ...state.navigationState,
                  currentView: previous,
                  history,
                },
              };
            }),

          resetNavigation: () =>
            set(() => ({
              navigationState: initialNavigationState(),
            })),

          // ---------- coreTools actions ----------
          /**
           * Replace the entire core-tools map. Unknown keys are dropped,
           * missing keys default to `false`. The new state is shallow-
           * cloned to keep the persist middleware happy.
           */
          setCoreTools: (tools) =>
            set(() => ({
              coreTools: normalizeCoreTools(tools),
            })),

          /**
           * Set a single core tool's installed state. Ignores unknown ids
           * (returns the unchanged state) so a typo in a caller doesn't
           * silently expand the slice.
           */
          setCoreToolInstalled: (toolId, installed) => {
            if (!CORE_TOOL_IDS.includes(toolId)) {
              return;
            }
            set((state) => ({
              coreTools: { ...state.coreTools, [toolId]: Boolean(installed) },
            }));
          },

          /**
           * Convenience: derive the core-tools map from the installed
           * apps list. Recognizes the canonical core tool ids and
           * marks a tool as installed when an app with the same id is
           * present in `installedApps`. Apps without a recognized id
           * (e.g. "playnite-extension") do not affect the sun.
           */
          syncCoreToolsFromInstalls: () =>
            set((state) => {
              const next = { ...state.coreTools };
              const installedIds = new Set(
                state.installState.installedApps.map((entry) => entry.id)
              );
              for (const id of CORE_TOOL_IDS) {
                next[id] = installedIds.has(id);
              }
              return { coreTools: next };
            }),

          // ---------- categories actions (Story 2-3) ----------
          /**
           * Replace the entire categories slice. Accepts an array of
           * `{ id, name, color, installed }` objects. Drops entries
           * without a string `id` and coerces every other field into
           * the documented shape so a caller cannot poison the slice
           * with arbitrary keys.
           */
          setCategories: (next) => set(() => ({ categories: normalizeCategories(next) })),

          /**
           * Upsert a single category. If a category with the same `id`
           * already exists, the existing entry is replaced; otherwise
           * a new entry is appended at the end of the array. Returns
           * the new array so callers can react if they need to.
           */
          upsertCategory: (category) =>
            set((state) => {
              if (!category || typeof category !== 'object' || !category.id) {
                return state;
              }
              const safe = sanitizeCategory(category);
              const idx = state.categories.findIndex((entry) => entry.id === safe.id);
              const next =
                idx === -1
                  ? [...state.categories, safe]
                  : state.categories.map((entry, i) => (i === idx ? safe : entry));
              return { categories: next };
            }),

          /**
           * Remove a category by id. No-op when the id is unknown so
           * a stale subscription cannot crash the store.
           */
          removeCategory: (categoryId) =>
            set((state) => {
              if (!categoryId || typeof categoryId !== 'string') {
                return state;
              }
              const next = state.categories.filter((entry) => entry.id !== categoryId);
              if (next.length === state.categories.length) {
                return state;
              }
              return { categories: next };
            }),

          /**
           * Flip a category's installed flag. The planet factory
           * subscribes to this slice and pushes the change into the
           * 3D scene via `sceneController.setPlanetInstalled(id, ...)`.
           * No-op when the id is unknown.
           */
          setCategoryInstalled: (categoryId, installed) =>
            set((state) => {
              if (!categoryId || typeof categoryId !== 'string') {
                return state;
              }
              let mutated = false;
              const next = state.categories.map((entry) => {
                if (entry.id !== categoryId) {
                  return entry;
                }
                const flag = Boolean(installed);
                if (entry.installed === flag) {
                  return entry;
                }
                mutated = true;
                return { ...entry, installed: flag };
              });
              if (!mutated) {
                return state;
              }
              return { categories: next };
            }),

          /**
           * Recompute each category's installed flag from the current
           * `installState.installedApps`. A category is marked
           * installed when at least one installed app carries the
           * category id (either as its `id` or its `categoryId`).
           * This keeps the planet colours in sync with the install
           * state without forcing every installer to know about
           * categories.
           *
           * Defensive validation: `categoryId` strings carried by
           * installed apps are intersected with the set of known
           * category ids before they participate in the sync. A typo
           * or stale `categoryId` (e.g. "game" instead of "games")
           * would otherwise silently mark a non-existent category as
           * installed — and because the planet factory only knows
           * about the categories passed at construction time, the
           * mismatch is invisible to the renderer. We log a warning
           * for each unmatched id so a developer can spot the drift
           * without it ever affecting the 3D scene.
           */
          syncCategoriesFromInstalls: () =>
            set((state) => {
              const knownCategoryIds = new Set(state.categories.map((entry) => entry.id));
              const installedIds = new Set(
                state.installState.installedApps.map((entry) => entry.id)
              );
              const installedCategoryIds = new Set(
                state.installState.installedApps
                  .map((entry) => entry.categoryId)
                  .filter((id) => typeof id === 'string')
              );
              // Surface unmatched `categoryId` values so stale or
              // mistyped entries don't silently mark a non-existent
              // category as installed. `installedIds` is a set of app
              // ids, which lives in a disjoint id space from category
              // ids — intersecting the two would never be true, so the
              // check is solely against `knownCategoryIds`.
              const unmatchedCategoryIds = new Set();
              for (const id of installedCategoryIds) {
                if (!knownCategoryIds.has(id)) {
                  unmatchedCategoryIds.add(id);
                }
              }
              if (unmatchedCategoryIds.size > 0) {
                console.warn(
                  '[Store] syncCategoriesFromInstalls: installed apps reference ' +
                    'unknown categoryId(s): ' +
                    Array.from(unmatchedCategoryIds).join(', ') +
                    '. They will be ignored. Known category ids: ' +
                    Array.from(knownCategoryIds).join(', ')
                );
              }
              let mutated = false;
              const next = state.categories.map((entry) => {
                const flag = installedIds.has(entry.id) || installedCategoryIds.has(entry.id);
                if (entry.installed === flag) {
                  return entry;
                }
                mutated = true;
                return { ...entry, installed: flag };
              });
              if (!mutated) {
                return state;
              }
              return { categories: next };
            }),

          // ---------- bulk helpers ----------
          reset: () => set(initialState()),
        }),
        {
          name,
          version: STORE_VERSION,
          storage,
          partialize,
          merge: mergeSlices,
          migrate: runMigration,
          skipHydration,
        }
      )
    )
  );

  /**
   * Persistence integration. When the caller supplies a `persistence`
   * adapter, the bridge installs a hydration + throttled save path
   * that mirrors the persistable slices (worldConfig, installedApps,
   * navigationHistory, coreTools, categories) to the on-disk adapter.
   *
   * See `./persistenceBridge.js` for the full behavior contract.
   */
  installPersistenceBridge(store, persistence, { throttleMs, logger: persistenceLogger });

  return store;
};

/**
 * The default singleton. Used by the renderer entry. Tests should call
 * `createAppStore()` directly to get a fresh instance.
 *
 * The singleton is built WITHOUT a persistence adapter so importing
 * this module from a Vitest spec does not crash on Electron-specific
 * APIs. The renderer wires the persistence adapter after import via
 * `attachPersistence(useAppStore, adapter)` once the renderer-side
 * adapter is constructed.
 */
export const useAppStore = createAppStore();

/**
 * Attach a persistence adapter to an existing store. Thin re-export
 * of the shared bridge so callers that imported `attachPersistence`
 * from `store.js` keep working unchanged. The behavior contract lives
 * in `./persistenceBridge.js`.
 *
 * @param {Object} store
 * @param {Object} adapter
 * @param {Object} [opts]
 * @param {number} [opts.throttleMs=250]
 * @param {Function} [opts.logger]
 */
export const attachPersistence = (store, adapter, opts = {}) => {
  if (!store || !adapter) {
    return store;
  }
  return installPersistenceBridge(store, adapter, opts);
};

// Re-export the factory + helpers so callers (renderer.js, future stories)
// can import only what they need.
export { initialState };
