/**
 * Persistence bridge for the Zustand store (Story 2-4).
 *
 * `installPersistenceBridge(store, adapter, opts)` is the single
 * source of truth for "wire a persistence adapter into a Zustand
 * store". Both `createAppStore({ persistence })` (used at construction
 * time) and `attachPersistence(store, adapter)` (used to upgrade the
 * singleton after import) delegate here so the two paths can never
 * drift.
 *
 * Behavior contract:
 *
 *   - If `adapter` is missing or does not expose `getWorldConfig`,
 *     the call is a no-op and the store is returned unchanged.
 *   - If the store already has a `persistenceCancel` teardown hook
 *     (from a previous bridge), the teardown runs first so a double
 *     attach never stacks listeners.
 *   - The adapter is read once to hydrate the `worldConfig` slice.
 *     Errors are surfaced through the logger but never thrown.
 *   - A throttled writer coalesces mutations so at most one disk
 *     write per `throttleMs` window leaves the process.
 *   - A dirty-checked subscription forwards changed slices to the
 *     throttled writer. Unchanged slices (FPS ticks, etc.) are
 *     short-circuited.
 *   - The store is augmented with `persistenceFlush` and
 *     `persistenceCancel` hooks. `persistenceFlush` runs any
 *     pending trailing write; `persistenceCancel` discards the
 *     pending write AND unsubscribes the store listener.
 *
 * The bridge mirrors ALL persistable slices (worldConfig,
 * installedApps, navigationHistory, coreTools, categories) so the
 * persistence adapter and the `persist` middleware cannot drift.
 * Without the broader mirror, a slice updated through the middleware
 * but never written to the adapter would only land on localStorage
 * — a regression that would surface as inconsistent `persistence.get*`
 * reads after a crash.
 */

import { coerceSeed } from './seed.js';
import { MAX_SEED } from './seed.js';

/**
 * Throttle helper. Coalesces a burst of `fn()` calls so the wrapped
 * function runs at most once per `waitMs` milliseconds. The trailing
 * call carries the most recent arguments, so the last update always
 * lands on disk. We use a leading-edge throttle (no leading call,
 * trailing only) so a write that races with a state mutation does
 * not overwrite a fresher value with a stale snapshot.
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
 * Shallow-compare two slice snapshots. Returns `true` when both
 * inputs are reference-equal OR when every key on `a` matches the
 * same key on `b` under `===` (with `a` keys used as the
 * authoritative set). New keys on `b` count as a change so an
 * evolving slice is not silently ignored.
 */
const shallowEqualSlice = (a, b) => {
  if (a === b) {
    return true;
  }
  if (!a || !b || typeof a !== 'object' || typeof b !== 'object') {
    return false;
  }
  const aKeys = Object.keys(a);
  const bKeys = Object.keys(b);
  if (aKeys.length !== bKeys.length) {
    return false;
  }
  for (const key of aKeys) {
    if (a[key] !== b[key]) {
      return false;
    }
  }
  return true;
};

/**
 * Shallow-compare two arrays. Length and per-index reference equality
 * are sufficient for our slice because every action replaces the
 * array rather than mutating it in place.
 */
const shallowEqualArray = (a, b) => {
  if (a === b) {
    return true;
  }
  if (!Array.isArray(a) || !Array.isArray(b)) {
    return false;
  }
  if (a.length !== b.length) {
    return false;
  }
  for (let i = 0; i < a.length; i += 1) {
    if (a[i] !== b[i]) {
      return false;
    }
  }
  return true;
};

/**
 * Sanitize the on-disk `worldConfig` blob before merging it into the
 * runtime state. Mirrors the validation used by `setWorldConfig` so a
 * forged or partially-written entry can never smuggle a NaN seed
 * into the renderer.
 */
const sanitizeWorldConfig = (next, fallback) => {
  const safe = fallback || { seed: 42, lastRegeneratedAt: null, regenerated: false };
  if (!next || typeof next !== 'object') {
    return { ...safe };
  }
  const coerced = coerceSeed(next.seed);
  const seed = coerced !== null ? coerced : safe.seed;
  const lastRegeneratedAt =
    next.lastRegeneratedAt === null
      ? null
      : typeof next.lastRegeneratedAt === 'number' && Number.isFinite(next.lastRegeneratedAt)
        ? next.lastRegeneratedAt
        : safe.lastRegeneratedAt;
  const regenerated = typeof next.regenerated === 'boolean' ? next.regenerated : !!safe.regenerated;
  return { seed, lastRegeneratedAt, regenerated };
};

/**
 * Install the persistence bridge on a store.
 *
 * @param {Object} store       The Zustand store to augment.
 * @param {Object} adapter     The persistence wrapper.
 * @param {Object} [opts]
 * @param {number} [opts.throttleMs=250]
 * @param {Function} [opts.logger]
 * @returns {Object}           The same `store` reference, for chaining.
 */
export const installPersistenceBridge = (store, adapter, opts = {}) => {
  if (!store || !adapter || typeof adapter.getWorldConfig !== 'function') {
    return store;
  }
  // Tear down a prior bridge before installing a new one. Without
  // this, a double attach would stack subscribers and the
  // persistenceFlush / persistenceCancel hooks would point at the
  // older (cancelled) writer.
  if (typeof store.persistenceCancel === 'function') {
    try {
      store.persistenceCancel();
    } catch {
      // Best-effort: a previous bridge's teardown failure must not
      // prevent the new bridge from being installed.
    }
  }
  const throttleMs = typeof opts.throttleMs === 'number' ? opts.throttleMs : 250;
  const persistenceLogger = typeof opts.logger === 'function' ? opts.logger : () => {};

  // Hydrate the worldConfig slice from disk so a renderer that
  // boots before the `persist` middleware finishes still observes
  // the on-disk seed. Errors are surfaced through the logger but
  // never thrown — a corrupt disk entry must not brick the boot.
  try {
    const onDisk = adapter.getWorldConfig();
    store.setState((state) => ({
      worldConfig: sanitizeWorldConfig({ ...state.worldConfig, ...onDisk }, state.worldConfig),
    }));
  } catch (err) {
    persistenceLogger('[Store] persistence hydration failed', {
      error: err && err.message ? err.message : String(err),
    });
  }

  const throttledWrite = throttleTrailing((snapshot) => {
    try {
      if (snapshot.worldConfig) {
        adapter.setWorldConfig(snapshot.worldConfig);
      }
      if (snapshot.installState && Array.isArray(snapshot.installState.installedApps)) {
        adapter.setInstalledApps(snapshot.installState.installedApps);
      }
      if (snapshot.navigationState && Array.isArray(snapshot.navigationState.history)) {
        adapter.setNavigationHistory(snapshot.navigationState.history);
      }
      // Story 2-4 follow-up: also mirror `coreTools` and `categories`
      // through the adapter. The persist middleware writes those
      // slices to localStorage, but a future consumer reading via
      // `persistence.get*` (or a future story that disables the
      // persist middleware for these slices) would otherwise see a
      // stale view. Mirroring every persistable slice keeps the two
      // storage layers in lockstep so a crash-recovery round trip
      // is always consistent.
      if (snapshot.coreTools && typeof adapter.setCoreTools === 'function') {
        adapter.setCoreTools(snapshot.coreTools);
      }
      if (snapshot.categories && typeof adapter.setCategories === 'function') {
        adapter.setCategories(snapshot.categories);
      }
    } catch (err) {
      persistenceLogger('[Store] persistence save failed', {
        error: err && err.message ? err.message : String(err),
      });
    }
  }, throttleMs);

  // Track the previous slice so we can detect actual changes. The
  // subscribe listener fires on every mutation; without this guard
  // we would write to disk on every FPS tick, every navigation
  // transition, and every frame update — the very spike the
  // throttle is meant to absorb.
  let previous = {
    worldConfig: null,
    installedApps: null,
    navigationHistory: null,
    coreTools: null,
    categories: null,
  };
  const unsubscribe = store.subscribe((state) => {
    const worldConfig = state.worldConfig;
    const installedApps = state.installState ? state.installState.installedApps : null;
    const navigationHistory = state.navigationState ? state.navigationState.history : null;
    const coreTools = state.coreTools;
    const categories = state.categories;
    const dirty =
      !shallowEqualSlice(previous.worldConfig, worldConfig) ||
      !shallowEqualArray(previous.installedApps, installedApps) ||
      !shallowEqualArray(previous.navigationHistory, navigationHistory) ||
      !shallowEqualSlice(previous.coreTools, coreTools) ||
      !shallowEqualArray(previous.categories, categories);
    if (!dirty) {
      return;
    }
    previous = {
      worldConfig: worldConfig ? { ...worldConfig } : null,
      installedApps: Array.isArray(installedApps) ? installedApps.slice() : null,
      navigationHistory: Array.isArray(navigationHistory) ? navigationHistory.slice() : null,
      coreTools: coreTools ? { ...coreTools } : null,
      categories: Array.isArray(categories) ? categories.slice() : null,
    };
    throttledWrite({
      worldConfig,
      installState: { installedApps },
      navigationState: { history: navigationHistory },
      coreTools,
      categories,
    });
  });

  // Expose flush/cancel so the renderer can flush pending writes
  // before the window closes. `cancel` also tears down the store
  // subscription so the bridge is fully reversible.
  store.persistenceFlush = () => throttledWrite.flush();
  store.persistenceCancel = () => {
    throttledWrite.cancel();
    if (typeof unsubscribe === 'function') {
      unsubscribe();
    }
  };
  return store;
};

export { MAX_SEED };
