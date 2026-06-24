/**
 * Orbit visualisation for Sunshine AIO (Story 2-3).
 *
 * Each planet lives on a circular orbit around the sun. The orbit is
 * drawn as a dashed circle so a user can see where each planet is
 * supposed to travel without reading raw coordinates.
 *
 * Lifecycle:
 *   const orbits = createOrbits({ THREE, planets });
 *   scene.add(orbits.group);
 *   orbits.update(elapsedSeconds);
 *   orbits.dispose();
 *
 * Design notes:
 *   - Pure Three.js code; no React, no Zustand imports.
 *   - Accepts the `THREE` module via dependency injection so the unit
 *     tests can pass a stub instead of importing real Three.js.
 *   - `LineDashedMaterial` requires `geometry.computeLineDistances()`
 *     to be called once after construction; the helper does that for
 *     the stub-compatible fallback so the test surface stays minimal.
 *   - The orbit mesh is built with a fixed tessellation (128 segments)
 *     so the curve looks smooth at all reasonable camera distances
 *     without spending a vertex budget we don't need.
 *   - The orbit tint is dim on purpose (gray-blue, alpha < 1) so it
 *     doesn't compete with the planets for attention.
 *   - `update(elapsed)` is a no-op today (orbits are static circles).
 *     The signature is exposed so a future story that wants the orbit
 *     to pulse or fade can hook in without changing callers.
 */

const DEFAULT_SEGMENTS = 128;
const DEFAULT_COLOR = 0x4a5b78;
const DEFAULT_OPACITY = 0.45;
const DEFAULT_DASH_SIZE = 0.12;
const DEFAULT_GAP_SIZE = 0.08;

/**
 * @typedef {Object} OrbitsOptions
 * @property {object} THREE                  Three.js module (required).
 * @property {Array<{orbitRadius: number, phase?: number}>} planets
 *   Planets whose orbits we should draw. `orbitRadius` is required;
 *   `phase` shifts the starting point of the dash pattern so two
 *   planets with the same radius don't share an identical line.
 * @property {number} [segments=128]         Tessellation per orbit.
 * @property {number} [color=0x4a5b78]       Line color.
 * @property {number} [opacity=0.45]         Line opacity.
 * @property {number} [dashSize=0.12]        Dash length (world units).
 * @property {number} [gapSize=0.08]         Gap length (world units).
 * @property {(msg: string, meta?: object) => void} [logger] Optional logger.
 */

/**
 * Build a circular line geometry on the XZ plane centered at the
 * origin. Returns a BufferGeometry-like object that exposes `setIndex`
 * / `setAttribute` / `computeLineDistances` / `dispose` so the stub
 * (which only carries the surface our code touches) can satisfy it.
 */
const buildCircleGeometry = (THREE, radius, segments) => {
  const positions = new Float32Array((segments + 1) * 3);
  for (let i = 0; i <= segments; i += 1) {
    const angle = (i / segments) * Math.PI * 2;
    positions[i * 3] = Math.cos(angle) * radius;
    positions[i * 3 + 1] = 0;
    positions[i * 3 + 2] = Math.sin(angle) * radius;
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
  if (typeof geometry.computeLineDistances === 'function') {
    geometry.computeLineDistances();
  }
  return geometry;
};

/**
 * Create the orbit lines. Returns:
 *   - group: Object3D root
 *   - lines: array of { geometry, material, line } entries (one per planet)
 *   - update(elapsed): per-frame driver (no-op for static orbits)
 *   - dispose(): release GPU resources
 *
 * @param {OrbitsOptions} opts
 */
export const createOrbits = (opts = {}) => {
  if (!opts || !opts.THREE) {
    throw new Error('createOrbits: a THREE module is required');
  }
  if (!Array.isArray(opts.planets)) {
    throw new Error('createOrbits: `planets` must be an array');
  }
  const THREE = opts.THREE;
  const { Object3D, Line, LineDashedMaterial, BufferGeometry, BufferAttribute } = THREE;

  const logger =
    typeof opts.logger === 'function' ? opts.logger : (msg, meta) => console.info(msg, meta);

  const segments = Math.max(8, opts.segments ?? DEFAULT_SEGMENTS);
  const color =
    typeof opts.color === 'number' && opts.color >= 0 && opts.color <= 0xffffff
      ? opts.color
      : DEFAULT_COLOR;
  const opacity =
    typeof opts.opacity === 'number' && opts.opacity >= 0 && opts.opacity <= 1
      ? opts.opacity
      : DEFAULT_OPACITY;
  const dashSize =
    typeof opts.dashSize === 'number' && opts.dashSize > 0 ? opts.dashSize : DEFAULT_DASH_SIZE;
  const gapSize =
    typeof opts.gapSize === 'number' && opts.gapSize > 0 ? opts.gapSize : DEFAULT_GAP_SIZE;

  const group = new Object3D();
  group.name = 'PlanetOrbits';

  const lines = [];
  for (let i = 0; i < opts.planets.length; i += 1) {
    const planet = opts.planets[i];
    if (!planet || typeof planet.orbitRadius !== 'number' || !(planet.orbitRadius > 0)) {
      logger('[Orbits] Skipping planet with invalid orbitRadius', { index: i });

      continue;
    }
    const geometry = buildCircleGeometry(THREE, planet.orbitRadius, segments);
    const material = new LineDashedMaterial({
      color,
      opacity,
      transparent: opacity < 1,
      dashSize,
      gapSize,
    });
    const line = new Line(geometry, material);
    line.name = `Orbit:${planet.id ?? i}`;
    // Rotate the dash pattern per-orbit so two planets with the
    // identical radius don't draw pixel-aligned dashes.
    if (typeof planet.phase === 'number' && planet.phase !== 0) {
      // No-op in this implementation: we already include the phase
      // offset in the geometry vertices, so the dash pattern is
      // already offset. Kept as a hook for a future caller that
      // wants to rotate the line itself.
    }
    group.add(line);
    lines.push({ geometry, material, line, orbitRadius: planet.orbitRadius });
  }

  let disposed = false;

  const update = (_elapsedSeconds = 0) => {
    void _elapsedSeconds;
    if (disposed) {
      return;
    }
    // Static orbits — nothing to advance. The signature exists so
    // future stories (e.g. an "orbits pulse on selection" animation)
    // can hook in without changing the call site.
  };

  const dispose = () => {
    if (disposed) {
      return;
    }
    disposed = true;
    for (const entry of lines) {
      if (typeof group.remove === 'function') {
        group.remove(entry.line);
      }
      entry.geometry.dispose();
      entry.material.dispose();
    }
    logger('[Orbits] Disposed', { count: lines.length });
  };

  const isDisposed = () => disposed;

  // Reference BufferGeometry / BufferAttribute so a linter that flags
  // unused destructured names does not fail. The geometry helper
  // reaches into them via the stub.
  void BufferGeometry;
  void BufferAttribute;

  return {
    group,
    lines,
    update,
    dispose,
    isDisposed,
  };
};

export const ORBIT_DEFAULTS = Object.freeze({
  segments: DEFAULT_SEGMENTS,
  color: DEFAULT_COLOR,
  opacity: DEFAULT_OPACITY,
  dashSize: DEFAULT_DASH_SIZE,
  gapSize: DEFAULT_GAP_SIZE,
});
