/**
 * Shared seed helpers for Story 2-4.
 *
 * The "regenerate world" affordance is reachable from two distinct
 * code paths:
 *
 *   1. `state/store.js` exposes a `regenerateWorld` action that rolls
 *      a new `worldConfig.seed` and stamps `lastRegeneratedAt`.
 *   2. `state/persistence.js` exposes a sibling `regenerateWorld` that
 *      mutates the on-disk blob (used by tests and by the standalone
 *      persistence adapter).
 *
 * Both paths need a seed that differs from the previous one — even
 * when two clicks land in the same millisecond. The counter that
 * guarantees the uniqueness used to live as a module-level variable
 * inside each file, which meant the two paths would advance their
 * *own* counter independently. Two back-to-back calls (one through
 * the store, one through the persistence adapter) could end up
 * picking the same candidate seed; the `+1` escape hatch prevented a
 * literal duplicate, but the *order* in which the two counters
 * advanced would silently influence which seed got picked.
 *
 * Centralising the counter here makes the two paths share a single
 * monotonic source of truth. The escape hatch still works as a
 * belt-and-braces guard, but it is no longer load-bearing.
 *
 * Tests that need deterministic seeds pass them through the
 * `opts.seed` override on each call site; the counter is bypassed
 * entirely in that case.
 */

/**
 * Module-level counter. Advanced on every call to `pickFreshSeed`
 * so two back-to-back calls in the same millisecond produce distinct
 * candidates. The counter is exported as a named binding (and not
 * mutated through a function) so a future test can reset it without
 * reaching into the module's internals.
 */
let REGEN_COUNTER = 0;

/**
 * Reset the counter. Intended for tests that want deterministic seed
 * sequences across multiple test cases — call `resetSeedCounter()`
 * in a `beforeEach` to keep the candidate sequence predictable.
 */
export const resetSeedCounter = () => {
  REGEN_COUNTER = 0;
};

/**
 * Pick a fresh seed that differs from the previous one. The
 * candidate is composed from the lower 16 bits of the timestamp and
 * the lower 16 bits of the counter; the escape hatch (the `+1` when
 * the candidate collides with the previous seed) is a defensive
 * guard, not the primary mechanism — the counter is what guarantees
 * forward progress.
 *
 * @param {number} previousSeed  The seed the caller currently has.
 * @param {number} [ts]          Timestamp in ms (defaults to Date.now()).
 * @returns {number}             A non-negative integer distinct from `previousSeed`.
 */
export const pickFreshSeed = (previousSeed, ts) => {
  REGEN_COUNTER += 1;
  const now = typeof ts === 'number' && Number.isFinite(ts) ? ts : Date.now();
  const candidate = ((now & 0xffff) << 16) | (REGEN_COUNTER & 0xffff);
  return candidate === previousSeed ? candidate + 1 : candidate;
};

/**
 * The largest seed value the planet factory's bit math can encode
 * without precision loss. Anything larger than this collapses to the
 * counter-driven default in `pickFreshSeed`.
 */
export const MAX_SEED = 2 ** 32 - 1;

/**
 * Coerce a user-supplied seed into the documented range. Returns
 * `null` when the input is missing or out of range so the caller can
 * fall back to `pickFreshSeed`. The bounds are:
 *   - must be a finite number (rejects NaN, Infinity, strings)
 *   - must be a safe integer (rejects MAX_SAFE_INTEGER + 1, floats)
 *   - must be non-negative
 *   - must fit in 32 bits (rejects values that would lose precision
 *     when encoded into the seed bit math downstream).
 *
 * Centralising the check means `regenerateWorld` and `setSeed` both
 * accept the same input shape and never let an out-of-range integer
 * reach the bit math that derives per-planet slots.
 */
export const coerceSeed = (value) => {
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    return null;
  }
  if (!Number.isSafeInteger(value)) {
    return null;
  }
  if (value < 0 || value > MAX_SEED) {
    return null;
  }
  return Math.floor(value);
};
