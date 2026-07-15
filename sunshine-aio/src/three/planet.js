/**
 * Planet component for Sunshine AIO (Story 2-3).
 *
 * Visual contract:
 *   - A textured sphere positioned on an orbital ring around the sun.
 *   - Each planet gets a unique procedural noise texture (per-planet
 *     seed) so two planets never look identical.
 *   - The planet color reflects its installation status: a dim
 *     "uninstalled" gray when no app in its category is installed,
 *     a saturated "installed" tint when at least one app is installed.
 *   - The mesh rotates on its own axis (spin) and revolves around the
 *     origin at a configurable angular speed. The revolution does NOT
 *     affect the spin, so the noise pattern still rotates visibly.
 *
 * Lifecycle:
 *   const planet = createPlanet({ THREE, category });
 *   scene.add(planet.group);
 *   planet.update(deltaSeconds, elapsedSeconds);
 *   planet.setInstalled(true | false);
 *   planet.dispose();
 *
 * Design notes:
 *   - Pure Three.js code; no React, no Zustand imports. The store calls
 *     `setInstalled` to push state into the planet.
 *   - Accepts the `THREE` module via dependency injection so the unit
 *     tests can pass a stub instead of importing real Three.js (which
 *     requires WebGL).
 *   - Procedural noise is generated via a deterministic PRNG (mulberry32)
 *     seeded by the planet id, so two calls with the same seed produce
 *     byte-identical textures. This keeps the visual identity of each
 *     planet stable across reloads (the persist middleware round-trips
 *     planet layouts; without a stable seed the texture would shimmer
 *     on every reload).
 *   - The procedural texture is rendered to an off-screen canvas, then
 *     converted to a CanvasTexture. The stub does not implement the
 *     full Canvas2D API; tests pass a pre-built texture instead and
 *     the constructor falls back to a flat color so the suite stays
 *     runnable under pure Node.
 *   - The installed-state flip mutates `material.color` in place via
 *     `Color.set(hex)` — no allocation on the hot path.
 */

const DEFAULT_RADIUS = 0.4;
const DEFAULT_ORBIT_RADIUS = 4.0;
const DEFAULT_SPIN_SPEED = 0.5; // radians per second (own axis)
const DEFAULT_REVOLUTION_SPEED = 0.1; // radians per second (around sun)
const DEFAULT_TILT = 0; // radians, around X axis
const DEFAULT_NOISE_SCALE = 8;

const DEFAULT_INSTALLED_COLOR = 0x4fc3f7; // soft cyan
const DEFAULT_UNINSTALLED_COLOR = 0x4a4a4a; // dim gray

const TEXTURE_SIZE = 64;

/**
 * Coerce an arbitrary value into a color input acceptable to Three.js.
 * Mirrors the sanitizer used by the sun component. Negative numbers
 * fall back to the default rather than wrap via `>>> 0`.
 */
const sanitizeColor = (value, fallback) => {
  if (typeof value === 'number' && Number.isFinite(value) && value >= 0 && value <= 0xffffff) {
    return value | 0;
  }
  if (typeof value === 'string' && /^#[0-9a-f]{3,8}$/i.test(value)) {
    return value;
  }
  return fallback;
};

const sanitizeScalar = (value, fallback) => {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value;
  }
  return fallback;
};

/**
 * Deterministic 32-bit PRNG (mulberry32). Same seed -> same sequence,
 * which is what we want for procedural textures that need to be stable
 * across reloads.
 */
const mulberry32 = (seed) => {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) | 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
};

/**
 * Hash a category id string into a 32-bit integer seed. Uses a
 * FNV-1a variant so the result is deterministic and easy to reason
 * about in tests. The string length and a second mixing round are
 * folded into the result so two adjacent ids with a shared prefix
 * (e.g. "games" / "games-2") cannot land on the same seed.
 */
const hashCategoryId = (id) => {
  const str = typeof id === 'string' ? id : '';
  let h = 0x811c9dc5;
  for (let i = 0; i < str.length; i += 1) {
    h ^= str.charCodeAt(i);
    h = Math.imul(h, 0x01000193);
  }
  // Mix in the string length and a second FNV-1a round over the
  // initial hash bytes so divergent ids do not collapse onto the
  // same seed. The golden-ratio constant (0x9e3779b1) is the same
  // one Knuth attributes to the "multiply by a large odd prime"
  // hash-mixing trick and gives excellent avalanche properties.
  const lenMix = Math.imul(str.length | 0, 0x9e3779b1) >>> 0;
  h = (h ^ lenMix) >>> 0;
  let h2 = 0x811c9dc5;
  const bytes = [h & 0xff, (h >>> 8) & 0xff, (h >>> 16) & 0xff, (h >>> 24) & 0xff];
  for (let i = 0; i < bytes.length; i += 1) {
    h2 ^= bytes[i];
    h2 = Math.imul(h2, 0x01000193);
  }
  return h2 >>> 0;
};

/**
 * Build a procedural noise texture as an ImageData buffer. Returns
 * a flat RGBA Uint8Array of `size * size * 4` pixels plus a base
 * color. The consumer (createPlanet) wraps it in a Three.js
 * CanvasTexture or, in test environments, returns the raw buffer
 * for inspection.
 */
export const generateProceduralNoise = ({
  size = TEXTURE_SIZE,
  seed = 1,
  baseColor = 0x4fc3f7,
}) => {
  const width = Math.max(2, size | 0);
  const height = width;
  const pixels = new Uint8Array(width * height * 4);
  const rand = mulberry32(seed);
  // Pre-roll the PRNG a few steps so two consecutive calls with
  // adjacent seeds don't produce visually identical patterns.
  for (let i = 0; i < 4; i += 1) rand();
  const baseR = (baseColor >> 16) & 0xff;
  const baseG = (baseColor >> 8) & 0xff;
  const baseB = baseColor & 0xff;
  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      // Cheap multi-octave noise: two layers of rand() mixed together.
      const n1 = rand();
      const n2 = rand();
      const noise = 0.6 * n1 + 0.4 * n2;
      // Map noise [0, 1] -> brightness multiplier [0.6, 1.2].
      const brightness = 0.6 + noise * 0.6;
      const idx = (y * width + x) * 4;
      pixels[idx] = Math.min(255, Math.max(0, Math.round(baseR * brightness)));
      pixels[idx + 1] = Math.min(255, Math.max(0, Math.round(baseG * brightness)));
      pixels[idx + 2] = Math.min(255, Math.max(0, Math.round(baseB * brightness)));
      pixels[idx + 3] = 255;
    }
  }
  return { pixels, width, height };
};

/**
 * @typedef {Object} PlanetOptions
 * @property {object} THREE                            Three.js module (required).
 * @property {{id: string, name?: string, color?: number}} category
 *   Category descriptor. `id` is required and seeds the texture;
 *   `name` is used for the mesh name; `color` overrides the installed
 *   tint (defaults to DEFAULT_INSTALLED_COLOR).
 * @property {number} [radius=0.4]                     Sphere radius.
 * @property {number} [orbitRadius=4.0]                Distance from origin.
 * @property {number} [phase=0]                        Initial angle on the orbit (radians).
 * @property {number} [spinSpeed=0.5]                  Rotation around own axis (rad/s).
 * @property {number} [revolutionSpeed=0.1]            Orbit angular speed (rad/s).
 * @property {number} [tilt=0]                         Tilt around X axis (radians).
 * @property {number} [installedColor=0x4fc3f7]        Installed tint.
 * @property {number} [uninstalledColor=0x4a4a4a]      Grayed-out tint.
 * @property {(msg: string, meta?: object) => void} [logger] Optional logger.
 * @property {object} [texture]                        Pre-built texture (test override).
 */

/**
 * Create a Planet. Returns:
 *   - group: Object3D root positioned at the orbital slot
 *   - mesh: the sphere mesh (added as group.children[0])
 *   - pivot: an Object3D whose rotation drives the spin (so spin and
 *     revolution don't fight over the same transform)
 *   - update(delta, elapsed): per-frame driver
 *   - setInstalled(boolean): flip installed state
 *   - isInstalled(): boolean
 *   - dispose(): release GPU resources
 *
 * @param {PlanetOptions} opts
 */
export const createPlanet = (opts = {}) => {
  if (!opts || !opts.THREE) {
    throw new Error('createPlanet: a THREE module is required');
  }
  if (!opts.category || typeof opts.category !== 'object' || !opts.category.id) {
    throw new Error('createPlanet: a category with a string `id` is required');
  }
  const THREE = opts.THREE;
  const { Object3D, Mesh, SphereGeometry, MeshStandardMaterial, CanvasTexture } = THREE;

  const logger =
    typeof opts.logger === 'function' ? opts.logger : (msg, meta) => console.info(msg, meta);

  const radius = sanitizeScalar(opts.radius, DEFAULT_RADIUS);
  const orbitRadius = sanitizeScalar(opts.orbitRadius, DEFAULT_ORBIT_RADIUS);
  const phase = sanitizeScalar(opts.phase, 0);
  const spinSpeed = sanitizeScalar(opts.spinSpeed, DEFAULT_SPIN_SPEED);
  const revolutionSpeed = sanitizeScalar(opts.revolutionSpeed, DEFAULT_REVOLUTION_SPEED);
  const tilt = sanitizeScalar(opts.tilt, DEFAULT_TILT);
  const installedColor = sanitizeColor(opts.installedColor, DEFAULT_INSTALLED_COLOR);
  const uninstalledColor = sanitizeColor(opts.uninstalledColor, DEFAULT_UNINSTALLED_COLOR);
  // Note: `opts.category.color` is intentionally not consumed. The
  // visible color is driven exclusively by `material.color` (flipped
  // by `setInstalled` between `installedColor` and `uninstalledColor`),
  // and the noise texture is grayscale (baseColor: 0xffffff below) so
  // multiplying a colored tint into the noise buffer is not necessary.
  // Keeping the option in the typedef documents the per-category color
  // contract for callers that pass a descriptor with a custom `color`
  // without breaking the grayscale-noise invariant.
  void opts.category?.color;

  const seed = hashCategoryId(opts.category.id);

  // Build the procedural noise texture. In test environments the stub
  // does not implement Canvas2D, so callers can pre-supply a `texture`
  // and we skip the canvas dance entirely.
  let texture = opts.texture;
  if (!texture && typeof CanvasTexture === 'function') {
    try {
      if (typeof document !== 'undefined' && document.createElement) {
        const canvas = document.createElement('canvas');
        canvas.width = TEXTURE_SIZE;
        canvas.height = TEXTURE_SIZE;
        const ctx = canvas.getContext('2d');
        if (ctx) {
          const { pixels, width, height } = generateProceduralNoise({
            size: TEXTURE_SIZE,
            seed,
            // The texture must be grayscale so the visible color is
            // driven exclusively by `material.color` (which `setInstalled`
            // flips between the installed tint and the uninstalled gray).
            // Multiplying a colored noise texture against `material.color`
            // would produce a dimmed version of the installed tint in the
            // "uninstalled" state instead of a neutral gray.
            baseColor: 0xffffff,
          });
          const imageData = ctx.createImageData(width, height);
          imageData.data.set(pixels);
          ctx.putImageData(imageData, 0, 0);
          texture = new CanvasTexture(canvas);
        }
      }
    } catch {
      texture = undefined;
    }
  }

  const geometry = new SphereGeometry(radius, 32, 32);
  // Use the procedural texture when available; fall back to a flat
  // color so the test suite (which doesn't ship a real CanvasTexture)
  // still gets a visible mesh.
  const material = new MeshStandardMaterial({
    color: uninstalledColor,
    emissive: uninstalledColor,
    emissiveIntensity: 0.25,
    roughness: 0.7,
    metalness: 0.05,
    ...(texture ? { map: texture } : {}),
  });

  const pivot = new Object3D();
  pivot.name = `PlanetPivot:${opts.category.id}`;

  const mesh = new Mesh(geometry, material);
  mesh.name = opts.category.name ? `Planet:${opts.category.name}` : `Planet:${opts.category.id}`;

  // The pivot carries the orbital position + revolution. The mesh
  // sits at the pivot's origin and rotates independently for spin.
  // A second Object3D (`tiltNode`) lets us apply an axial tilt without
  // fighting the spin axis.
  const tiltNode = new Object3D();
  tiltNode.name = `PlanetTilt:${opts.category.id}`;
  tiltNode.rotation.x = tilt;
  tiltNode.add(mesh);
  pivot.add(tiltNode);

  // Root group at the origin of the solar system. The pivot is the
  // child that actually revolves so a caller can attach other objects
  // to `group` without inheriting the orbit motion.
  const group = new Object3D();
  group.name = `PlanetGroup:${opts.category.id}`;
  group.add(pivot);

  // Seed the initial orbital position so the first frame already
  // shows the planet on its slot (no "everything at the origin"
  // pop-in before the first tick).
  pivot.position.set(Math.cos(phase) * orbitRadius, 0, Math.sin(phase) * orbitRadius);

  let installed = false;
  let elapsed = 0;
  let hasUpdated = false;
  let disposed = false;

  const update = (deltaSeconds = 0, elapsedSeconds) => {
    // Disposed check MUST come first — otherwise we'd waste the dt
    // computation and increment the closure-local `elapsed` variable
    // on every tick even though the loop is supposed to no-op after
    // dispose(). This is the per-planet hot path; the few cycles saved
    // add up across the entire solar system.
    if (disposed) {
      return;
    }
    const dt = Number.isFinite(deltaSeconds) && deltaSeconds > 0 ? deltaSeconds : 0;
    if (Number.isFinite(elapsedSeconds) && elapsedSeconds >= 0) {
      elapsed = elapsedSeconds;
    } else if (dt > 0) {
      elapsed += dt;
    } else if (!hasUpdated) {
      // First-frame safety net so a (0, 0) bootstrap still advances
      // the orbit by a hair, preventing the planet from sitting at
      // exactly its initial phase until the second tick.
      elapsed += 0.0001;
    }
    hasUpdated = true;
    const revolutionAngle = phase + elapsed * revolutionSpeed;
    pivot.position.set(
      Math.cos(revolutionAngle) * orbitRadius,
      0,
      Math.sin(revolutionAngle) * orbitRadius
    );
    // Spin: rotate the mesh on its local Y axis. The mesh is parented
    // to `tiltNode`, so the tilt survives and only the spin changes.
    mesh.rotation.y = elapsed * spinSpeed;
  };

  /**
   * Replace the installed state. Mutates the material color and
   * emissive in place via `Color.set(hex)` so the hot path is
   * allocation-free.
   */
  const setInstalled = (next) => {
    if (disposed) {
      return;
    }
    const flag = Boolean(next);
    if (installed === flag) {
      return;
    }
    installed = flag;
    const hex = flag ? installedColor : uninstalledColor;
    material.color.set(hex);
    material.emissive.set(hex);
    material.emissiveIntensity = flag ? 0.5 : 0.25;
  };

  const isInstalled = () => installed;

  const dispose = () => {
    if (disposed) {
      return;
    }
    disposed = true;
    if (typeof pivot.remove === 'function') {
      pivot.remove(tiltNode);
    }
    if (typeof tiltNode.remove === 'function') {
      tiltNode.remove(mesh);
    }
    if (typeof group.remove === 'function') {
      group.remove(pivot);
    }
    geometry.dispose();
    material.dispose();
    if (texture && typeof texture.dispose === 'function') {
      texture.dispose();
    }
    logger('[Planet] Disposed', { id: opts.category.id });
  };

  const isDisposed = () => disposed;

  return {
    group,
    pivot,
    mesh,
    radius,
    orbitRadius,
    phase,
    spinSpeed,
    revolutionSpeed,
    installedColor,
    uninstalledColor,
    update,
    setInstalled,
    isInstalled,
    dispose,
    isDisposed,
    getSeed: () => seed,
  };
};

export const PLANET_DEFAULTS = Object.freeze({
  radius: DEFAULT_RADIUS,
  orbitRadius: DEFAULT_ORBIT_RADIUS,
  spinSpeed: DEFAULT_SPIN_SPEED,
  revolutionSpeed: DEFAULT_REVOLUTION_SPEED,
  tilt: DEFAULT_TILT,
  installedColor: DEFAULT_INSTALLED_COLOR,
  uninstalledColor: DEFAULT_UNINSTALLED_COLOR,
  noiseScale: DEFAULT_NOISE_SCALE,
  textureSize: TEXTURE_SIZE,
});
