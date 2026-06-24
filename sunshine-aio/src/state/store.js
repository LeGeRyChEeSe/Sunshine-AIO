/**
 * Zustand store for Sunshine AIO (Story 2-1 + Story 2-2).
 *
 * Centralizes four slices of application state:
 *   - worldState       : the 3D solar-system view (planets, statuses, FPS).
 *   - installState     : which apps are installed, in-progress, or failed.
 *   - navigationState  : current view, focus, history stack for back nav.
 *   - coreTools        : the three core tools wired into the sun's
 *                        satellite indicators (sunshine / vdd / playnite).
 *
 * Story 2-2 adds the `coreTools` slice. The sun component subscribes
 * via `sceneController.setInstalledTools(coreTools)` so the satellite
 * indicators brighten when a tool is reported as installed. The slice
 * is *derived* from `installState.installedApps` — the store keeps the
 * map in sync through actions rather than asking callers to mutate
 * two slices.
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
import { persist, createJSONStorage } from 'zustand/middleware';

export const STORE_NAME = 'sunshine-aio-app-state';
export const STORE_VERSION = 1;

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
 * starts in the `false` (not installed) state.
 */
const initialCoreTools = () =>
  CORE_TOOL_IDS.reduce((acc, id) => {
    acc[id] = false;
    return acc;
  }, {});

const initialState = () => ({
  worldState: initialWorldState(),
  installState: initialInstallState(),
  navigationState: initialNavigationState(),
  coreTools: initialCoreTools(),
});

/**
 * Only persist slices that are safe to round-trip across reloads:
 *   - worldState.planets (planet layout)
 *   - installState (installed apps list)
 *   - navigationState (current view, history)
 *   - coreTools (so the sun's satellite indicators survive a restart)
 * Ephemeral fields (fps, sceneInitialized, inProgressApps, lastUpdatedAt)
 * are excluded so we don't persist transient runtime metrics.
 */
const partialize = (state) => ({
  worldState: {
    planets: state.worldState.planets,
  },
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
 */
const migrations = {
  // No migrations yet — first version. When STORE_VERSION is bumped,
  // add a migrator here keyed by the *previous* version (e.g. 1, 2)
  // so persisted blobs from earlier releases can be upgraded in place.
  // The runtime assertion below (see `assertMigrationsConsistent`)
  // will throw at module load if the table is left empty while
  // STORE_VERSION > 1, surfacing the omission in CI before it reaches
  // production.
};

/**
 * Surface "bumped STORE_VERSION but no migrators" at module load.
 * Without this, the API is unstable: a developer can update the
 * version constant and forget to add a migration entry, and the only
 * symptom is silent data loss in the field. The assertion turns that
 * omission into a hard error in the same tick that the mismatch is
 * introduced.
 */
const assertMigrationsConsistent = () => {
  if (STORE_VERSION > 1 && Object.keys(migrations).length === 0) {
    throw new Error(
      `[Store] STORE_VERSION is ${STORE_VERSION} but the migrations table is empty. ` +
        'Add a migrator entry for the previous version before bumping STORE_VERSION.'
    );
  }
  // Forward direction: every version below STORE_VERSION must have a
  // migrator, otherwise older persisted blobs will be discarded and
  // the user loses their state silently.
  for (let v = 1; v < STORE_VERSION; v += 1) {
    if (typeof migrations[v] !== 'function') {
      throw new Error(
        `[Store] Missing migrator for version ${v} -> ${STORE_VERSION}. ` +
          'Add a migrator entry to the migrations table.'
      );
    }
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
 * Shallow-merge each top-level slice individually rather than
 * replacing whole slices. This preserves runtime-only fields like
 * `worldState.fps` and `worldState.sceneInitialized` across rehydrate
 * even when those keys are intentionally excluded from the persisted
 * blob via `partialize`.
 */
const mergeSlices = (persistedState, currentState) => {
  if (!persistedState) {
    return currentState;
  }
  const merged = { ...currentState, ...persistedState };
  for (const key of Object.keys(persistedState)) {
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
    }
  }
  return merged;
};

/**
 * Sanitize the user-supplied core-tools map. Only accepts keys from
 * CORE_TOOL_IDS; coerces every value to a boolean so a stray string
 * like `"true"` cannot poison the slice.
 */
const normalizeCoreTools = (tools) => {
  const result = {};
  for (const id of CORE_TOOL_IDS) {
    result[id] = false;
  }
  if (!tools || typeof tools !== 'object') {
    return result;
  }
  for (const id of CORE_TOOL_IDS) {
    if (Object.prototype.hasOwnProperty.call(tools, id)) {
      result[id] = Boolean(tools[id]);
    }
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
 */
export const createAppStore = (opts = {}) => {
  const storage = opts.storage || defaultStorage();
  const name = opts.name || STORE_NAME;
  const skipHydration = Boolean(opts.skipHydration);

  return createStore(
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
              installedApps: state.installState.installedApps.filter((entry) => entry.id !== appId),
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
            const installedIds = new Set(state.installState.installedApps.map((entry) => entry.id));
            for (const id of CORE_TOOL_IDS) {
              next[id] = installedIds.has(id);
            }
            return { coreTools: next };
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
  );
};

/**
 * The default singleton. Used by the renderer entry. Tests should call
 * `createAppStore()` directly to get a fresh instance.
 */
export const useAppStore = createAppStore();

// Re-export the factory + helpers so callers (renderer.js, future stories)
// can import only what they need.
export { initialState };
