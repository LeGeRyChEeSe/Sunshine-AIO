/**
 * Planet factory for Sunshine AIO (Story 2-3).
 *
 * Generates one planet per category in the supplied list, with
 * deterministic spacing so a fresh install renders the same orbital
 * layout every time. The factory owns the list of planet instances
 * and exposes a single `update(dt, elapsed)` that delegates to each
 * planet, plus a `setInstalled(planetId, installed)` to flip a single
 * planet's state.
 *
 * Lifecycle:
 *   const planets = createPlanetsForCategories({ THREE, categories });
 *   scene.add(planets.group);
 *   planets.update(deltaSeconds, elapsedSeconds);
 *   planets.setInstalled(planetId, true);
 *   planets.dispose();
 *
 * Design notes:
 *   - Pure Three.js code; no React, no Zustand imports. The store
 *     subscribes to `worldState.planets[*].installed` and pushes the
 *     value through `setInstalled`.
 *   - Orbit radius and phase are derived from the category index via
 *     a stable formula so two calls with the same input list produce
 *     the same layout (the persist middleware relies on this).
 *   - The factory also creates the matching orbit lines so the caller
 *     only needs to add one group to the scene. The orbits are hidden
 *     when the factory was constructed with `withOrbits: false`.
 *   - The factory never throws on unknown planet ids in `setInstalled`;
 *     it logs through the injected logger and returns `false` so a
 *     stale subscription cannot crash the render loop.
 */

import { createPlanet, PLANET_DEFAULTS } from './planet.js';
import { createOrbits } from './orbits.js';
import { PLANET_FACTORY_BRAND } from './setup.js';

const MIN_ORBIT_RADIUS = 3.0;
const ORBIT_SPACING = 1.5;
const PHASE_SPREAD = Math.PI * 2;
const DEFAULT_INNER_RADIUS = 2.8;

/**
 * Coerce an arbitrary value into a finite scalar. Mirrors the sanitizer
 * used by the planet constructor — without it, an override like
 * `{ phase: NaN }` would silently propagate to `Math.cos(NaN) = NaN`
 * and the pivot's position would corrupt on the very first tick.
 */
const sanitizeScalar = (value, fallback) => {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value;
  }
  return fallback;
};

/**
 * Derive an orbital slot (radius, phase, spin, revolution) from the
 * index. The formula is intentionally simple and deterministic: the
 * caller doesn't get to inject fancy layouts yet (the persistence layer
 * round-trips the whole planet descriptor anyway, including any future
 * manual overrides). When a category carries its own `orbitRadius` /
 * `phase` / `spinSpeed` / `revolutionSpeed`, those win.
 *
 * All numeric overrides flow through `sanitizeScalar` so non-finite
 * inputs (NaN, Infinity, strings, objects) collapse onto the
 * deterministic default instead of corrupting the orbital maths.
 */
const computeSlot = (index, total, override = {}) => {
  const orbitRadius = sanitizeScalar(
    typeof override.orbitRadius === 'number' && override.orbitRadius > 0
      ? override.orbitRadius
      : NaN,
    MIN_ORBIT_RADIUS + index * ORBIT_SPACING
  );
  const phase = sanitizeScalar(override.phase, (index / Math.max(1, total)) * PHASE_SPREAD);
  const spinSpeed = sanitizeScalar(override.spinSpeed, PLANET_DEFAULTS.spinSpeed);
  const revolutionSpeed = sanitizeScalar(
    override.revolutionSpeed,
    PLANET_DEFAULTS.revolutionSpeed + index * 0.01
  );
  return { orbitRadius, phase, spinSpeed, revolutionSpeed };
};

/**
 * @typedef {Object} Category
 * @property {string}  id
 * @property {string}  [name]
 * @property {number}  [color]
 * @property {boolean} [installed]
 * @property {number}  [orbitRadius]
 * @property {number}  [phase]
 * @property {number}  [spinSpeed]
 * @property {number}  [revolutionSpeed]
 * @property {number}  [radius]
 * @property {number}  [tilt]
 */

/**
 * @typedef {Object} PlanetFactoryOptions
 * @property {object} THREE                 Three.js module (required).
 * @property {Category[]} categories        Category descriptors.
 * @property {boolean} [withOrbits=true]    Generate the dashed orbit lines.
 * @property {number}  [innerRadius=2.8]    Minimum orbit radius (kept
 *   clear of the sun's halo at 1.45).
 * @property {(msg: string, meta?: object) => void} [logger] Optional logger.
 */

/**
 * Build a planet per category and (optionally) the matching orbit
 * lines. Returns:
 *   - group: Object3D root containing all planets + orbits
 *   - planets: array of planet descriptors (public surface)
 *   - orbits: the orbits controller (null when withOrbits is false)
 *   - update(delta, elapsed): per-frame driver
 *   - setInstalled(planetId, installed): flip a planet's installed flag
 *   - getInstalledMap(): { [planetId]: boolean }
 *   - dispose(): release GPU resources
 *
 * @param {PlanetFactoryOptions} opts
 */
export const createPlanetsForCategories = (opts = {}) => {
  if (!opts || !opts.THREE) {
    throw new Error('createPlanetsForCategories: a THREE module is required');
  }
  if (!Array.isArray(opts.categories)) {
    throw new Error('createPlanetsForCategories: `categories` must be an array');
  }
  const THREE = opts.THREE;

  const logger =
    typeof opts.logger === 'function' ? opts.logger : (msg, meta) => console.info(msg, meta);

  const withOrbits = opts.withOrbits !== false;
  const innerRadius =
    typeof opts.innerRadius === 'number' && opts.innerRadius > 0
      ? opts.innerRadius
      : DEFAULT_INNER_RADIUS;

  const rootGroup = new THREE.Object3D();
  rootGroup.name = 'PlanetFactoryRoot';

  const planets = [];
  const planetById = new Map();
  const skipped = [];

  // Detect innerRadius clamps BEFORE we start placing planets. The
  // default config (innerRadius=2.8, MIN_ORBIT_RADIUS=3.0) leaves room
  // for every category at (3.0, 4.5, 6.0, ...). Only warn when there
  // is genuinely NO room — i.e. `innerRadius` exceeds the LAST computed
  // slot, in which case `Math.max(innerRadius, slot)` will collapse
  // planets onto the same orbit. A single orbit at the clamp (the first
  // slot equals innerRadius) is fine and not a regression.
  const totalCategories = opts.categories.length;
  const firstSlotRadius = MIN_ORBIT_RADIUS;
  const lastDefaultSlotRadius = firstSlotRadius + Math.max(0, totalCategories - 1) * ORBIT_SPACING;
  if (innerRadius > lastDefaultSlotRadius) {
    logger(
      '[PlanetFactory] innerRadius is larger than the last default orbit; ' +
        'planets will be clamped up to innerRadius and may share orbits. ' +
        'Pass a smaller innerRadius (default 2.8) or larger ORBIT_SPACING.',
      {
        innerRadius,
        firstDefaultRadius: firstSlotRadius,
        lastDefaultRadius: lastDefaultSlotRadius,
        categoryCount: totalCategories,
      }
    );
  }

  opts.categories.forEach((category, index) => {
    if (!category || typeof category !== 'object' || !category.id) {
      skipped.push({ index, reason: 'missing-id' });
      logger('[PlanetFactory] Skipping category with no id', { index });
      return;
    }
    const slot = computeSlot(index, totalCategories, category);
    // Don't draw orbits inside the sun's halo.
    const orbitRadius = Math.max(innerRadius, slot.orbitRadius);
    if (
      typeof category.orbitRadius === 'number' &&
      Number.isFinite(category.orbitRadius) &&
      category.orbitRadius > 0 &&
      category.orbitRadius < innerRadius
    ) {
      logger('[PlanetFactory] Category orbitRadius is below innerRadius; clamped up.', {
        id: category.id,
        requested: category.orbitRadius,
        innerRadius,
      });
    }
    const planet = createPlanet({
      THREE,
      category,
      radius:
        typeof category.radius === 'number' && category.radius > 0 ? category.radius : undefined,
      orbitRadius,
      phase: slot.phase,
      spinSpeed: slot.spinSpeed,
      revolutionSpeed: slot.revolutionSpeed,
      tilt: typeof category.tilt === 'number' ? category.tilt : 0,
      logger,
    });
    if (category.installed) {
      planet.setInstalled(true);
    }
    rootGroup.add(planet.group);
    planets.push({
      id: category.id,
      name: category.name || category.id,
      installed: Boolean(category.installed),
      orbitRadius: planet.orbitRadius,
      phase: planet.phase,
      spinSpeed: planet.spinSpeed,
      revolutionSpeed: planet.revolutionSpeed,
      radius: planet.radius,
      instance: planet,
    });
    planetById.set(category.id, planet);
  });

  let orbits = null;
  if (withOrbits && planets.length > 0) {
    orbits = createOrbits({
      THREE,
      planets: planets.map((p) => ({
        id: p.id,
        orbitRadius: p.orbitRadius,
        phase: p.phase,
      })),
      logger,
    });
    rootGroup.add(orbits.group);
  }

  let disposed = false;

  const update = (deltaSeconds = 0, elapsedSeconds) => {
    if (disposed) {
      return;
    }
    // Each planet owns its own `elapsed` clock (per-planet
    // `update(deltaSeconds, elapsedSeconds)`); the factory just fans
    // the inputs out. We pass `elapsedSeconds` through so a caller
    // that supplies a shared clock still drives every planet in
    // sync; when `elapsedSeconds` is undefined each planet falls
    // back to accumulating its own `deltaSeconds`.
    for (const planet of planets) {
      planet.instance.update(deltaSeconds, elapsedSeconds);
    }
    if (orbits) {
      orbits.update(elapsedSeconds);
    }
  };

  const setInstalled = (planetId, installed) => {
    if (disposed) {
      return false;
    }
    const planet = planetById.get(planetId);
    if (!planet) {
      logger('[PlanetFactory] Unknown planet id', { planetId });
      return false;
    }
    const next = Boolean(installed);
    if (planet.isInstalled() === next) {
      return true;
    }
    planet.setInstalled(next);
    const descriptor = planets.find((p) => p.id === planetId);
    if (descriptor) {
      descriptor.installed = next;
    }
    return true;
  };

  const getInstalledMap = () => {
    const result = {};
    for (const descriptor of planets) {
      result[descriptor.id] = descriptor.installed;
    }
    return result;
  };

  const dispose = () => {
    if (disposed) {
      return;
    }
    disposed = true;
    for (const descriptor of planets) {
      if (typeof rootGroup.remove === 'function') {
        rootGroup.remove(descriptor.instance.group);
      }
      descriptor.instance.dispose();
    }
    if (orbits) {
      rootGroup.remove(orbits.group);
      orbits.dispose();
      orbits = null;
    }
    logger('[PlanetFactory] Disposed', {
      planetCount: planets.length,
      skipped: skipped.length,
    });
  };

  const isDisposed = () => disposed;

  const factory = {
    group: rootGroup,
    planets,
    orbits,
    update,
    setInstalled,
    getInstalledMap,
    dispose,
    isDisposed,
    skipped,
  };
  // Stamp the PLANET_FACTORY_BRAND so the scene controller's
  // `setPlanets(factory)` can verify the object originated from this
  // module. Symbols cannot be reproduced across module boundaries, so
  // a faked factory cannot impersonate us — see the SECURITY note in
  // setup.js for the threat model.
  try {
    Object.defineProperty(factory, PLANET_FACTORY_BRAND, {
      value: true,
      enumerable: false,
      configurable: false,
      writable: false,
    });
  } catch (err) {
    // Some environments (very old engines, frozen objects) refuse
    // defineProperty after the literal is created. The brand is a
    // defense-in-depth check; the brand is a defense-in-depth check
    // and a failure here almost certainly indicates a Proxy / accessor
    // collision. Forward to the logger so the regression is diagnosable
    // — `setPlanets` will reject this factory as a result, but the
    // developer should know WHY.
    logger('[PlanetFactory] brand stamp failed', {
      error: err && err.message ? err.message : String(err),
    });
  }
  return factory;
};

export { computeSlot };
