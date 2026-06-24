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

const MIN_ORBIT_RADIUS = 3.0;
const ORBIT_SPACING = 1.5;
const PHASE_SPREAD = Math.PI * 2;
const DEFAULT_INNER_RADIUS = 2.8;

/**
 * Derive an orbital slot (radius, phase, spin, revolution) from the
 * index. The formula is intentionally simple and deterministic: the
 * caller doesn't get to inject fancy layouts yet (the persistence layer
 * round-trips the whole planet descriptor anyway, including any future
 * manual overrides). When a category carries its own `orbitRadius` /
 * `phase` / `spinSpeed` / `revolutionSpeed`, those win.
 */
const computeSlot = (index, total, override = {}) => {
  const orbitRadius =
    typeof override.orbitRadius === 'number' && override.orbitRadius > 0
      ? override.orbitRadius
      : MIN_ORBIT_RADIUS + index * ORBIT_SPACING;
  const phase =
    typeof override.phase === 'number'
      ? override.phase
      : (index / Math.max(1, total)) * PHASE_SPREAD;
  const spinSpeed =
    typeof override.spinSpeed === 'number' ? override.spinSpeed : PLANET_DEFAULTS.spinSpeed;
  const revolutionSpeed =
    typeof override.revolutionSpeed === 'number'
      ? override.revolutionSpeed
      : PLANET_DEFAULTS.revolutionSpeed + index * 0.01;
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

  opts.categories.forEach((category, index) => {
    if (!category || typeof category !== 'object' || !category.id) {
      skipped.push({ index, reason: 'missing-id' });
      logger('[PlanetFactory] Skipping category with no id', { index });
      return;
    }
    const slot = computeSlot(index, opts.categories.length, category);
    // Don't draw orbits inside the sun's halo.
    const orbitRadius = Math.max(innerRadius, slot.orbitRadius);
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
  let sharedElapsed = 0;
  let hasUpdated = false;

  const update = (deltaSeconds = 0, elapsedSeconds) => {
    if (disposed) {
      return;
    }
    const dt = Number.isFinite(deltaSeconds) && deltaSeconds > 0 ? deltaSeconds : 0;
    if (Number.isFinite(elapsedSeconds) && elapsedSeconds >= 0) {
      sharedElapsed = elapsedSeconds;
    } else if (dt > 0) {
      sharedElapsed += dt;
    } else if (!hasUpdated) {
      sharedElapsed += 0.0001;
    }
    hasUpdated = true;
    for (const planet of planets) {
      planet.instance.update(deltaSeconds, sharedElapsed);
    }
    if (orbits) {
      orbits.update(sharedElapsed);
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

  return {
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
};

export { computeSlot };
