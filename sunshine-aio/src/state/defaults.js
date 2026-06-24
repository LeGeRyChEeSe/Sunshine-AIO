/**
 * Shared defaults for Sunshine AIO state slices (Story 2-4).
 *
 * This module is intentionally dependency-free: it does not import the
 * Zustand store, the persistence adapter, or any UI code. That keeps
 * the import graph acyclic and lets both `store.js` and
 * `persistence.js` reach for a single source of truth without dragging
 * in the other's transitive dependencies.
 *
 * Why a separate module?
 *
 *   The `worldConfig` defaults used to live in *both* `persistence.js`
 *   and `store.js`. The two definitions drifted apart silently — a
 *   developer bumping the seed in one file would not see the change
 *   in the other, and the runtime + persisted blobs would disagree.
 *   Centralising the constants here closes that gap and turns the
 *   "duplicated here so the store can build its initial state without
 *   an import cycle" comment in `store.js` from a code smell into a
 *   solved problem.
 */

/**
 * The default world configuration. A fresh install ships with a
 * deterministic seed (`42`) so the solar system renders the same way
 * on every machine. The seed is a non-negative integer; the planet
 * factory multiplies it by a stable formula to derive per-planet
 * orbital slots.
 *
 * Kept frozen so a careless caller cannot mutate the module-level
 * default and silently corrupt subsequent reads.
 */
export const DEFAULT_WORLD_CONFIG = Object.freeze({
  seed: 42,
  lastRegeneratedAt: null,
  // Whether the user has explicitly regenerated at least once. Used
  // by the renderer's "Regenerate World" affordance to decide whether
  // the button should pulse / announce itself.
  regenerated: false,
});

/**
 * Default installed-apps list. The empty array is intentional — a
 * brand-new install has nothing to migrate.
 */
export const DEFAULT_INSTALLED_APPS = Object.freeze([]);

/**
 * Default navigation history. The history is a list of view ids
 * (matching the `APP_VIEW` enum in store.js). The wrapper keeps the
 * value as an opaque string array; the store handles validation on
 * its side via `setCurrentView`.
 */
export const DEFAULT_NAVIGATION_HISTORY = Object.freeze([]);