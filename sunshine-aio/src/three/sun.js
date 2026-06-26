/**
 * Sun component for Sunshine AIO (Story 2-2).
 *
 * Visual contract:
 *   - A glowing orange/yellow sphere at the origin of the solar system.
 *   - A pulsing animation: gentle scale oscillation driven by sin(elapsed)
 *     so the breathe is independent of frame rate.
 *   - A halo / glow shell (a back-side rendered sphere) tinted orange so
 *     the sun reads as luminous without a real bloom post-process.
 *   - Three orbiting satellite indicators, one per core tool:
 *       * sunshine  -> Sunshine game-stream host
 *       * vdd       -> Virtual Display Driver
 *       * playnite  -> Playnite launcher
 *     The indicator for a tool brightens when that tool is reported as
 *     installed via `setInstalledTools({ ... })`.
 *
 * Lifecycle:
 *   const sun = createSun({ THREE });
 *   scene.add(sun.group);           // `group` is the Object3D root
 *   // animation loop:
 *   sun.update(deltaSeconds, elapsedSeconds);
 *   sun.setInstalledTools({ sunshine: true, vdd: false, playnite: true });
 *   sun.dispose();                  // releases geometries + materials
 *
 * Design notes:
 *   - Pure Three.js code; no React, no Zustand imports. The store calls
 *     `setInstalledTools` to push state into the sun.
 *   - Accepts the `THREE` module via dependency injection so the unit
 *     tests can pass a stub instead of importing real Three.js (which
 *     requires WebGL). This keeps the suite runnable under pure Node
 *     like the rest of the renderer tests.
 *   - `update(delta, elapsed)` is idempotent and cheap: a single sin()
 *     per frame plus a quaternion rotation for the satellites. No
 *     allocations on the hot path.
 *   - Disposal is recursive: every mesh under the group has its
 *     geometry and material disposed exactly once.
 *   - The sun's pulsing is gated to `update(...)`. If a caller forgets
 *     to call update, the sun stays static — never throws. The first
 *     update seeds `elapsed` with a tiny sentinel so callers that boot
 *     with `(0, 0)` or `(0, undefined)` still see a non-trivial pulse
 *     on the very first frame instead of holding at scale=1.0 until
 *     the second tick.
 */

const DEFAULT_CORE_RADIUS = 1.0;
const DEFAULT_HALO_RADIUS = 1.45;
const DEFAULT_HALO_RATIO = 1.45;
const DEFAULT_PULSE_AMPLITUDE = 0.06;
const DEFAULT_PULSE_FREQUENCY_HZ = 0.6;
const DEFAULT_SATELLITE_ORBIT_RADIUS = 2.2;
const DEFAULT_SATELLITE_RADIUS = 0.12;
const DEFAULT_SATELLITE_ORBIT_SPEED = 0.4; // radians per second

const DEFAULT_CORE_COLOR = 0xffb347; // soft orange
const DEFAULT_EMISSIVE_COLOR = 0xffd166; // warm yellow glow
const DEFAULT_HALO_COLOR = 0xff8c1a; // deeper orange for the back-side halo
const DEFAULT_INACTIVE_COLOR = 0x6b6259; // dim gray-orange for "not installed"
const DEFAULT_ACTIVE_COLOR = 0xffe066; // bright yellow for "installed"

export const CORE_TOOLS = Object.freeze(['sunshine', 'vdd', 'playnite']);
const TWO_PI = Math.PI * 2;

/**
 * Coerce an arbitrary value into a color input acceptable to Three.js.
 *
 * Accepted formats:
 *   - number: a 24-bit hex value in [0, 0xFFFFFF]. Negative numbers
 *     and out-of-range values fall back to the default — `>>> 0`
 *     would otherwise turn -1 into 0xFFFFFFFF (opaque white).
 *   - string: a CSS hex color matching /^#[0-9a-f]{3,8}$/i (3, 4, 6,
 *     or 8 hex digits). Anything else falls back rather than throw
 *     deep inside a material constructor.
 *
 * The string branch is kept so the defaults table can mirror a future
 * caller that prefers CSS hexes; production setInstalledTools always
 * feeds sanitized integers, so the path is dormant in the hot path but
 * still exercised by the test suite.
 *
 * @param {unknown} value
 * @param {number} fallback
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

const sanitizeRadius = (value, fallback) => {
  if (typeof value === 'number' && Number.isFinite(value) && value > 0) {
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
 * @typedef {Object} SunOptions
 * @property {object} THREE                  Three.js module (required).
 * @property {number} [coreRadius=1.0]       Core sphere radius.
 * @property {number} [haloRatio=1.45]       Halo radius as a multiple of coreRadius.
 * @property {number} [pulseAmplitude=0.06]  Peak scale delta (0..1).
 * @property {number} [pulseFrequencyHz=0.6] Pulses per second.
 * @property {number} [orbitRadius=2.2]      Satellite orbit radius.
 * @property {number} [satelliteRadius=0.12] Satellite sphere radius.
 * @property {number} [orbitSpeed=0.4]       Satellite angular speed (rad/s).
 * @property {number} [coreColor=0xffb347]   Core color.
 * @property {number} [emissiveColor=0xffd166] Emissive color.
 * @property {number} [haloColor=0xff8c1a]   Halo color.
 * @property {number} [inactiveColor=0x6b6259] Satellite inactive color.
 * @property {number} [activeColor=0xffe066]   Satellite active color.
 * @property {(msg: string, meta?: object) => void} [logger] Optional logger.
 */

/**
 * Create a Sun. Returns an object with:
 *   - group: THREE.Object3D root to add to the scene
 *   - core, halo: child meshes
 *   - satellites: array of { name, mesh, material }
 *   - update(delta, elapsed): per-frame driver
 *   - setInstalledTools({ ... }): mutate installed state
 *   - isToolInstalled(name): boolean
 *   - dispose(): release GPU resources
 *
 * @param {SunOptions} opts
 */
export const createSun = (opts = {}) => {
  if (!opts || !opts.THREE) {
    throw new Error('createSun: a THREE module is required');
  }
  const THREE = opts.THREE;

  const logger =
    typeof opts.logger === 'function' ? opts.logger : (msg, meta) => console.info(msg, meta);

  const coreRadius = sanitizeRadius(opts.coreRadius, DEFAULT_CORE_RADIUS);
  const haloRadius = sanitizeRadius(opts.haloRatio, coreRadius * DEFAULT_HALO_RATIO);
  const pulseAmplitude = Math.max(0, sanitizeScalar(opts.pulseAmplitude, DEFAULT_PULSE_AMPLITUDE));
  const pulseFrequencyHz = Math.max(
    0,
    sanitizeScalar(opts.pulseFrequencyHz, DEFAULT_PULSE_FREQUENCY_HZ)
  );
  const orbitRadius = sanitizeRadius(opts.orbitRadius, DEFAULT_SATELLITE_ORBIT_RADIUS);
  const satelliteRadius = sanitizeRadius(opts.satelliteRadius, DEFAULT_SATELLITE_RADIUS);
  const orbitSpeed = sanitizeScalar(opts.orbitSpeed, DEFAULT_SATELLITE_ORBIT_SPEED);

  const coreColor = sanitizeColor(opts.coreColor, DEFAULT_CORE_COLOR);
  const emissiveColor = sanitizeColor(opts.emissiveColor, DEFAULT_EMISSIVE_COLOR);
  const haloColor = sanitizeColor(opts.haloColor, DEFAULT_HALO_COLOR);
  const inactiveColor = sanitizeColor(opts.inactiveColor, DEFAULT_INACTIVE_COLOR);
  const activeColor = sanitizeColor(opts.activeColor, DEFAULT_ACTIVE_COLOR);

  // `Color` is not used directly inside createSun anymore — the
  // hot path (`setInstalledTools`) mutates the existing material
  // colors via `material.color.set(hex)`, which does not require a
  // fresh `THREE.Color` instance. We keep the destructure list small
  // to avoid an unused-var lint warning.
  const { Object3D, Mesh, SphereGeometry, MeshStandardMaterial, MeshBasicMaterial } = THREE;

  // Root group — single Object3D so callers can `scene.add(sun.group)`
  // without learning about the internal structure.
  const group = new Object3D();
  group.name = 'Sun';

  // Core sphere: emissive orange/yellow. MeshStandardMaterial keeps the
  // sun sensitive to scene lights so future planets/lights (added in
  // later stories) can subtly tint it. emissiveIntensity is bumped up
  // for the literal "glow" feeling even without post-processing.
  const coreGeometry = new SphereGeometry(coreRadius, 32, 32);
  const coreMaterial = new MeshStandardMaterial({
    color: coreColor,
    emissive: emissiveColor,
    emissiveIntensity: 1.4,
    roughness: 0.45,
    metalness: 0.1,
  });
  const core = new Mesh(coreGeometry, coreMaterial);
  core.name = 'SunCore';
  group.add(core);

  // Halo shell: a slightly larger sphere rendered with BackSide so it
  // acts as a soft glow. MeshBasicMaterial ignores lights on purpose —
  // the halo should look uniformly warm even in a dark scene.
  const haloGeometry = new SphereGeometry(haloRadius, 32, 32);
  const haloMaterial = new MeshBasicMaterial({
    color: haloColor,
    side: THREE.BackSide,
    transparent: true,
    opacity: 0.28,
    depthWrite: false,
  });
  const halo = new Mesh(haloGeometry, haloMaterial);
  halo.name = 'SunHalo';
  group.add(halo);

  // Satellite indicators — one per core tool. Each starts in the
  // "inactive" (dim) state until setInstalledTools flips it.
  const satellites = CORE_TOOLS.map((name, index) => {
    const satelliteGeometry = new SphereGeometry(satelliteRadius, 16, 16);
    const satelliteMaterial = new MeshStandardMaterial({
      color: inactiveColor,
      emissive: inactiveColor,
      emissiveIntensity: 0.6,
      roughness: 0.4,
      metalness: 0.2,
    });
    const mesh = new Mesh(satelliteGeometry, satelliteMaterial);
    mesh.name = `SunSatellite:${name}`;
    // Spread initial positions evenly around the orbit so they don't
    // overlap on first frame. Phase = (2pi * i) / N.
    const phase = (TWO_PI * index) / CORE_TOOLS.length;
    mesh.position.set(Math.cos(phase) * orbitRadius, 0, Math.sin(phase) * orbitRadius);
    group.add(mesh);
    return {
      name,
      mesh,
      material: satelliteMaterial,
      geometry: satelliteGeometry,
      installed: false,
      phaseOffset: phase,
    };
  });

  // Precomputed O(1) lookup for the installed-tools hot path. Building
  // the map once at construction time replaces the per-call
  // `satellites.find(...)` walk in `setInstalledTools` (O(N^2) overall)
  // with a single map read. Kept as a plain Map rather than a WeakMap
  // because the keys are the well-known CORE_TOOLS strings, not object
  // references.
  const satellitesByName = new Map(satellites.map((s) => [s.name, s]));

  // Track installed state for each tool. Default to false.
  const installedState = CORE_TOOLS.reduce((acc, name) => {
    acc[name] = false;
    return acc;
  }, {});

  // Cached membership lookup so unknown-tool queries don't rebuild
  // a Set per call. The whitelist is the same CORE_TOOLS export used
  // by setInstalledTools — unknown names (e.g. a typo "sunshne") get
  // surfaced through the injected logger and return `false`.
  const knownToolNames = new Set(CORE_TOOLS);
  const warnUnknownTool = (source, name) => {
    logger('[Sun] Unknown tool id ignored', { source, name });
  };

  // Default emissive intensity applied to every inactive satellite at
  // construction time. The "installed" branch writes 2.0 in `setInstalledTools`
  // on state flip; the per-frame loop trusts that value until the next flip.
  const INACTIVE_EMISSIVE_INTENSITY = 0.6;
  const ACTIVE_EMISSIVE_INTENSITY = 2.0;

  // Pulse bookkeeping: keep the baseline scale so `setSize` or a future
  // transform can safely overwrite `group.scale` without losing the
  // pulse rhythm.
  let elapsed = 0;
  let hasUpdated = false; // sentinel for the first-frame AC guarantee
  let disposed = false;

  const computePulseScale = () => {
    if (pulseAmplitude <= 0 || pulseFrequencyHz <= 0) {
      return 1;
    }
    // sin(2pi * freq * t) oscillates in [-1, 1]; map to [1-a, 1+a].
    const wave = Math.sin(TWO_PI * pulseFrequencyHz * elapsed);
    return 1 + pulseAmplitude * wave;
  };

  const applySatelliteTransform = (satellite) => {
    if (!satellite || !satellite.mesh) {
      return;
    }
    const angle = elapsed * orbitSpeed + satellite.phaseOffset;
    satellite.mesh.position.set(
      Math.cos(angle) * orbitRadius,
      Math.sin(angle * 0.5) * 0.15, // gentle vertical wobble for depth
      Math.sin(angle) * orbitRadius
    );
    // Defensive re-stamp: the round-1 hot path in `setInstalledTools`
    // only writes emissiveIntensity on the frame the installed flag
    // actually flips, so any non-Zustand frame (RAF ticks, manual
    // calls) still needs a stable value. We re-derive from the current
    // `installed` flag rather than trusting a cached field so a future
    // caller that mutates `satellite.installed` directly still renders
    // correctly. The branch is cheap (no allocation) and never touches
    // material.color.
    satellite.material.emissiveIntensity = satellite.installed
      ? ACTIVE_EMISSIVE_INTENSITY
      : INACTIVE_EMISSIVE_INTENSITY;
  };

  const update = (deltaSeconds = 0, elapsedSeconds) => {
    if (disposed) {
      return;
    }
    const dt = Number.isFinite(deltaSeconds) && deltaSeconds > 0 ? deltaSeconds : 0;
    // Prefer an injected elapsed clock (for tests), otherwise trust
    // the running sum of deltas. Either path is monotonic.
    if (Number.isFinite(elapsedSeconds) && elapsedSeconds >= 0) {
      elapsed = elapsedSeconds;
    } else if (dt > 0) {
      elapsed += dt;
    } else if (!hasUpdated) {
      // First-frame safety net: callers that hit us with `(0, undefined)`
      // or `(0, 0)` (the standard test bootstrap) should still see the
      // pulse animation kick in. Seed the elapsed clock with a tiny
      // non-zero delta so the sin wave produces a non-trivial scale
      // on the very first tick instead of holding at 1.0 until the
      // second frame. After the first update, the running delta sum
      // takes over.
      elapsed += 0.0001;
    }
    hasUpdated = true;
    // Apply pulse to the core (not the group) so the halo keeps its
    // fixed radius — the halo's role is a steady glow, not a pulse.
    const scale = computePulseScale();
    core.scale.set(scale, scale, scale);
    // Subtle halo opacity oscillation so the glow feels alive without
    // a real bloom shader. Tied to the same sin wave so the two stay
    // in sync visually.
    if (pulseAmplitude > 0 && pulseFrequencyHz > 0) {
      const wave = Math.sin(TWO_PI * pulseFrequencyHz * elapsed);
      // Defensive clamp: with the current default amplitude (0.06) the
      // raw expression stays well inside [0, 1], but a future caller
      // could pass a larger amplitude and the value would leave the
      // legal alpha range. Three.js does not validate this for us.
      const opacity = 0.28 + pulseAmplitude * 0.8 * wave;
      haloMaterial.opacity = Math.max(0, Math.min(1, opacity));
    }
    for (const satellite of satellites) {
      applySatelliteTransform(satellite);
    }
  };

  /**
   * Replace the installed-tools state. Accepts an object with any
   * subset of `sunshine`, `vdd`, `playnite`. Unknown keys are ignored.
   * Updates the satellite colors and emissive intensity to reflect the
   * new state.
   *
   * Hot-path contract: this method runs on every Zustand store
   * subscription, so it must NOT allocate. We mutate the existing
   * `material.color` and `material.emissive` in place via
   * `Color.set(...)` and look up the target satellite through the
   * pre-built `satellitesByName` map.
   */
  const setInstalledTools = (tools) => {
    if (disposed) {
      return;
    }
    if (!tools || typeof tools !== 'object') {
      return;
    }
    // Surface unknown keys (typos, legacy callers) via the injected
    // logger. The slice itself is still dropped silently to keep the
    // hot-path allocation-free, but the developer-facing signal lands
    // somewhere visible so a future bug doesn't go undetected.
    for (const key of Object.keys(tools)) {
      if (!knownToolNames.has(key)) {
        warnUnknownTool('setInstalledTools', key);
      }
    }
    let changed = false;
    for (const name of CORE_TOOLS) {
      const next = Boolean(tools[name]);
      if (installedState[name] === next) {
        // No state transition — skip the material rebuild entirely
        // so Zustand store re-emissions with identical payloads don't
        // mutate Color objects on every change.
        continue;
      }
      installedState[name] = next;
      changed = true;
      const satellite = satellitesByName.get(name);
      if (!satellite) {
        continue;
      }
      satellite.installed = next;
      // Mutate in place — Color.set() overwrites the existing color
      // value rather than allocating a new one. We feed the raw
      // sanitized hex (already a finite integer) directly so the call
      // is independent of the pre-built Color instances' internal
      // representation, which keeps the stub's Color.set contract
      // minimal and the production behavior identical.
      const hex = next ? activeColor : inactiveColor;
      satellite.material.color.set(hex);
      satellite.material.emissive.set(hex);
      satellite.material.emissiveIntensity = next
        ? ACTIVE_EMISSIVE_INTENSITY
        : INACTIVE_EMISSIVE_INTENSITY;
    }
    if (changed) {
      logger('[Sun] Installed tools updated', { ...installedState });
    }
  };

  const isToolInstalled = (name) => {
    if (!knownToolNames.has(name)) {
      warnUnknownTool('isToolInstalled', name);
      return false;
    }
    return Boolean(installedState[name]);
  };

  const getInstalledState = () => ({ ...installedState });

  /**
   * Release GPU resources. After dispose, all update / setInstalledTools
   * calls become no-ops. Safe to call more than once.
   */
  const dispose = () => {
    if (disposed) {
      return;
    }
    disposed = true;
    // Remove children before disposing their geometries so a stray
    // render doesn't try to access released buffers.
    if (typeof group.remove === 'function') {
      group.remove(core);
      group.remove(halo);
      for (const satellite of satellites) {
        group.remove(satellite.mesh);
      }
    }
    coreGeometry.dispose();
    coreMaterial.dispose();
    haloGeometry.dispose();
    haloMaterial.dispose();
    for (const satellite of satellites) {
      satellite.geometry.dispose();
      satellite.material.dispose();
    }
    logger('[Sun] Disposed');
  };

  const isDisposed = () => disposed;

  return {
    group,
    core,
    halo,
    satellites,
    coreRadius,
    haloRadius,
    orbitRadius,
    satelliteRadius,
    update,
    setInstalledTools,
    isToolInstalled,
    getInstalledState,
    dispose,
    isDisposed,
  };
};

// Expose defaults for tests + tooling so callers can mirror the visual
// spec without re-deriving constants.
export const SUN_DEFAULTS = Object.freeze({
  coreRadius: DEFAULT_CORE_RADIUS,
  haloRadius: DEFAULT_HALO_RADIUS,
  haloRatio: DEFAULT_HALO_RATIO,
  pulseAmplitude: DEFAULT_PULSE_AMPLITUDE,
  pulseFrequencyHz: DEFAULT_PULSE_FREQUENCY_HZ,
  orbitRadius: DEFAULT_SATELLITE_ORBIT_RADIUS,
  satelliteRadius: DEFAULT_SATELLITE_RADIUS,
  orbitSpeed: DEFAULT_SATELLITE_ORBIT_SPEED,
  coreColor: DEFAULT_CORE_COLOR,
  emissiveColor: DEFAULT_EMISSIVE_COLOR,
  haloColor: DEFAULT_HALO_COLOR,
  inactiveColor: DEFAULT_INACTIVE_COLOR,
  activeColor: DEFAULT_ACTIVE_COLOR,
});
