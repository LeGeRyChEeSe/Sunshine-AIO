/**
 * Three.js renderer setup for Sunshine AIO (Story 2-1 + Story 2-2).
 *
 * Owns the WebGL renderer, the Three.js Scene, a PerspectiveCamera, the
 * requestAnimationFrame loop, the resize handler, the FPS monitor, and the
 * dispose/cleanup path.
 *
 * Lifecycle:
 *   const scene = createScene({ canvas, logger });
 *   scene.start();      // begin the animation loop
 *   scene.setSize(w, h); // imperative resize from outside the loop
 *   scene.dispose();    // stop loop + release GPU resources
 *
 * Story 2-2 additions:
 *   - The scene holds an optional `sunGroup` (Object3D) created by
 *     `createSun` from `./sun.js`. The animation loop delegates per-frame
 *     updates to registered scene objects via `update(dt, elapsed)`.
 *   - `setInstalledTools(tools)` pushes the installed-tool set into the
 *     sun so it can recolor / highlight its satellite indicators.
 *   - `getSun()` exposes the sun instance (read-only surface for tests).
 *
 * Design notes:
 * - The renderer is created with `antialias: true` and a sensible device
 *   pixel ratio cap (2) so high-DPI screens don't tank the framerate.
 * - The FPS monitor samples the delta-time over a rolling window of
 *   samples and emits `info` log lines at a configurable interval
 *   (default: 2 seconds) so a developer or QA can verify the 30 FPS
 *   target from the log stream without DevTools.
 * - The `dispose()` path releases the renderer context, geometries,
 *   materials, and textures currently attached to the scene so the
 *   window can be closed without leaking GPU memory. It also
 *   removes the resize listener.
 * - The module accepts an optional `logger` and `raf` so tests can
 *   inject a stub logger and a manual clock without touching globals.
 * - The module is intentionally framework-agnostic (no React, no
 *   Zustand imports). Story 2-2 only adds the sun mesh and
 *   update-loop hooks; React/UI subscribers wire up later.
 */

import { WebGLRenderer, Scene, PerspectiveCamera, Color, Clock } from 'three';

const DEFAULT_FOV = 60;
const DEFAULT_NEAR = 0.1;
const DEFAULT_FAR = 1000;
const DEFAULT_CAMERA_Z = 5;
const DEFAULT_BACKGROUND_COLOR = 0x000000;
const DEFAULT_DPR_CAP = 2;
const DEFAULT_FPS_SAMPLE_WINDOW = 60;
const DEFAULT_FPS_LOG_INTERVAL_MS = 2000;

/**
 * @typedef {Object} FpsMonitorOptions
 * @property {number} [sampleWindow=60]   Number of frames to average over.
 * @property {number} [logIntervalMs=2000] How often to emit a log line.
 * @property {(msg: string, meta?: object) => void} [onLog]  Sink for FPS logs.
 */

/**
 * Lightweight FPS counter. Holds a rolling sum of frame deltas and reports
 * the average FPS over `sampleWindow` frames. Exposes a tick(delta) method
 * and a stop() method to cancel pending timers.
 *
 * @param {FpsMonitorOptions} [opts]
 */
export const createFpsMonitor = (opts = {}) => {
  const sampleWindow = Math.max(1, opts.sampleWindow || DEFAULT_FPS_SAMPLE_WINDOW);
  const logIntervalMs = Math.max(100, opts.logIntervalMs || DEFAULT_FPS_LOG_INTERVAL_MS);
  const onLog = typeof opts.onLog === 'function' ? opts.onLog : () => {};
  let onFpsUpdate = typeof opts.onFpsUpdate === 'function' ? opts.onFpsUpdate : null;

  const samples = [];
  let lastEmitAt = 0;
  let intervalId = null;

  const tick = (deltaSeconds) => {
    // Guard against the first frame where delta can be 0 or huge.
    if (!Number.isFinite(deltaSeconds) || deltaSeconds <= 0) {
      return;
    }
    samples.push(deltaSeconds);
    if (samples.length > sampleWindow) {
      samples.shift();
    }
  };

  const flush = (force = false) => {
    if (samples.length === 0) {
      return;
    }
    const totalDelta = samples.reduce((acc, v) => acc + v, 0);
    const avgDelta = totalDelta / samples.length;
    const fps = avgDelta > 0 ? 1 / avgDelta : 0;
    const now = Date.now();
    if (force || now - lastEmitAt >= logIntervalMs) {
      lastEmitAt = now;
      onLog('[Three] FPS sample', {
        fps: Number(fps.toFixed(2)),
        samples: samples.length,
      });
      if (typeof onFpsUpdate === 'function') {
        // Clamp to a sane upper bound so a long tab pause doesn't
        // produce a 1e10 instantaneous reading when the monitor
        // finally flushes after the user returns.
        const clamped = Math.min(Math.max(fps, 0), 240);
        onFpsUpdate(clamped);
      }
    }
  };

  /**
   * Drive the periodic flush on a wall-clock interval so the log line
   * fires even when the renderer is paused (the loop is the wrong place
   * to schedule reporting — it's tied to render activity).
   */
  const start = () => {
    if (intervalId !== null) {
      return;
    }
    intervalId = setInterval(() => flush(false), logIntervalMs);
    // Allow Node to exit cleanly when this monitor is used in a test.
    if (typeof intervalId === 'object' && intervalId && 'unref' in intervalId) {
      intervalId.unref();
    }
  };

  const stop = () => {
    if (intervalId !== null) {
      clearInterval(intervalId);
      intervalId = null;
    }
  };

  const dispose = () => {
    flush(true);
    stop();
    samples.length = 0;
  };

  /**
   * Replace the onFpsUpdate sink. Useful when a higher-level
   * controller (e.g. the renderer) wants to attach a store writer
   * after the monitor is constructed.
   */
  const setFpsSink = (sink) => {
    onFpsUpdate = typeof sink === 'function' ? sink : null;
  };

  return { tick, start, stop, dispose, flush, setFpsSink };
};

/**
 * Dispose every geometry, material, and texture attached to the scene.
 * Walks recursively because Three.js scenes commonly nest groups.
 *
 * @param {import('three').Scene} scene
 */
export const disposeSceneObjects = (scene) => {
  if (!scene) {
    return;
  }
  scene.traverse((object) => {
    if (object.geometry && typeof object.geometry.dispose === 'function') {
      object.geometry.dispose();
    }
    if (object.material) {
      const materials = Array.isArray(object.material) ? object.material : [object.material];
      for (const material of materials) {
        // Dispose textures on the material first, then the material itself.
        for (const key of Object.keys(material)) {
          const value = material[key];
          if (value && typeof value === 'object' && typeof value.dispose === 'function') {
            value.dispose();
          }
        }
        if (typeof material.dispose === 'function') {
          material.dispose();
        }
      }
    }
  });
};

/**
 * @typedef {Object} SceneControllerOptions
 * @property {HTMLCanvasElement} canvas       Canvas to render into (required).
 * @property {(msg: string, meta?: object) => void} [logger]   Optional log sink.
 * @property {number} [width]                Initial width (defaults to canvas.clientWidth).
 * @property {number} [height]               Initial height (defaults to canvas.clientHeight).
 * @property {number} [fov=60]               Perspective camera FOV in degrees.
 * @property {number} [near=0.1]             Near clipping plane.
 * @property {number} [far=1000]             Far clipping plane.
 * @property {number} [cameraZ=5]            Initial camera distance from origin.
 * @property {number} [backgroundColor=0x000000] Scene background color.
 * @property {number} [dprCap=2]             Maximum device pixel ratio.
 * @property {number} [fpsSampleWindow=60]   Frames averaged per FPS reading.
 * @property {number} [fpsLogIntervalMs=2000] FPS log cadence.
 * @property {(cb: (t: number) => void) => number} [rafFactory]   RAF override (tests).
 * @property {(handle: number) => void} [cancelRaf]            Cancel override.
 * @property {(fps: number) => void} [onFpsUpdate]   Sink for the
 *   rolling-window FPS value. Fires every time the monitor flushes, so
 *   consumers (e.g. the Zustand store) can read the same averaged value
 *   that gets logged. This is the single source of truth for FPS.
 */

/**
 * Create the WebGL renderer, scene, camera, animation loop, resize handler,
 * FPS monitor, and dispose() entry point. Returns a controller object.
 *
 * @param {SceneControllerOptions} opts
 */
export const createScene = (opts) => {
  if (!opts || !opts.canvas) {
    throw new Error('createScene: a canvas element is required');
  }

  const logger =
    typeof opts.logger === 'function' ? opts.logger : (msg, meta) => console.info(msg, meta);

  const canvas = opts.canvas;
  const fov = opts.fov ?? DEFAULT_FOV;
  const near = opts.near ?? DEFAULT_NEAR;
  const far = opts.far ?? DEFAULT_FAR;
  const cameraZ = opts.cameraZ ?? DEFAULT_CAMERA_Z;
  const backgroundColor = opts.backgroundColor ?? DEFAULT_BACKGROUND_COLOR;

  const initialWidth = opts.width ?? canvas.clientWidth ?? canvas.parentElement?.clientWidth ?? 800;
  const initialHeight =
    opts.height ?? canvas.clientHeight ?? canvas.parentElement?.clientHeight ?? 600;

  const renderer = new WebGLRenderer({
    canvas,
    antialias: true,
    alpha: false,
  });
  const dprSource =
    typeof window !== 'undefined' && window.devicePixelRatio ? window.devicePixelRatio : 1;
  renderer.setPixelRatio(Math.min(dprSource, opts.dprCap ?? DEFAULT_DPR_CAP));
  renderer.setSize(initialWidth, initialHeight, false);
  renderer.setClearColor(backgroundColor, 1);
  // The constructor-time setSize above is the only legitimate use of
  // initialWidth/Height — the resize handler must not fall back to
  // them once the canvas is in play. Track the initial apply so the
  // handler knows when to skip the fallback.
  let initialSizeApplied = true;

  const scene = new Scene();
  scene.background = new Color(backgroundColor);

  const camera = new PerspectiveCamera(fov, initialWidth / initialHeight, near, far);
  camera.position.set(0, 0, cameraZ);
  camera.lookAt(0, 0, 0);

  const clock = new Clock();

  const fpsMonitor = createFpsMonitor({
    sampleWindow: opts.fpsSampleWindow,
    logIntervalMs: opts.fpsLogIntervalMs,
    onLog: (msg, meta) => logger(msg, meta),
    onFpsUpdate: typeof opts.onFpsUpdate === 'function' ? opts.onFpsUpdate : null,
  });

  // Default RAF factories fall back to globalThis so the module works in
  // both browser and Electron renderer contexts without monkey-patching.
  // If neither globalThis nor opts provide one, we throw a descriptive
  // error rather than silently swallowing the render loop — startup is
  // the moment a developer most needs feedback.
  const fallbackRaf = (cb) => {
    if (typeof globalThis.requestAnimationFrame === 'function') {
      return globalThis.requestAnimationFrame(cb);
    }
    throw new Error(
      'createScene: no requestAnimationFrame is available. Pass opts.rafFactory when running outside a browser.'
    );
  };
  const fallbackCancelRaf = (h) => {
    if (typeof globalThis.cancelAnimationFrame === 'function') {
      globalThis.cancelAnimationFrame(h);
    }
  };
  const rafFactory = opts.rafFactory || fallbackRaf;
  const cancelRaf = opts.cancelRaf || fallbackCancelRaf;

  // Story 2-2: registry of per-frame updaters. Each updater is a plain
  // function `(delta, elapsedSeconds) => void`. Updaters are owned by
  // meshes (the sun, future planets) and registered via `addUpdater`.
  // `removeUpdater` is used by `dispose()` to ensure the loop cannot
  // call into a disposed mesh. The registry is intentionally simple —
  // no priority / sort order is needed at this scale.
  const updaters = new Set();

  // Story 2-2: optional sun instance. Held so `setInstalledTools` and
  // `getSun` can route through the scene controller without exposing
  // the mesh to callers. Set via `setSun` and disposed on `dispose()`.
  let sunInstance = null;
  // Local registry of per-sun unregister handles. The sun is created
  // by an external factory (`createSun`) which returns a clean,
  // JSDoc-defined public surface — we must NOT mutate that surface
  // with internal double-underscore properties. Storing the unregister
  // function in a WeakMap keyed by the sun instance keeps the bridge
  // encapsulated inside the scene controller and lets GC reclaim both
  // entries together when the sun is collected.
  const sunUnregisterByInstance = new WeakMap();

  let rafHandle = null;
  let running = false;
  let disposed = false;
  let resizeListener = null;

  const applySize = (width, height) => {
    if (!Number.isFinite(width) || !Number.isFinite(height) || width <= 0 || height <= 0) {
      return false;
    }
    renderer.setSize(width, height, false);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    return true;
  };

  const handleResize = () => {
    // Defer the actual size read to the next animation frame so the
    // browser has a chance to lay out the canvas. A freshly-created
    // canvas reports clientWidth/clientHeight === 0 before the first
    // paint, so reading them synchronously here would silently use the
    // stale initialWidth/Height. Scheduling the read on the next RAF
    // (or via the provided rafFactory for tests) keeps the listener
    // tracking the real window size. Reuse the already-configured
    // `rafFactory` (declared above) rather than re-implementing the
    // fallback inline — that keeps the resize path on the same RAF
    // channel as the render loop, so test mocks via `opts.rafFactory`
    // and the production fallback behave consistently.
    rafFactory(() => {
      if (disposed) {
        return;
      }
      const rawW = canvas.clientWidth;
      const rawH = canvas.clientHeight;
      // Only use initialWidth/Height as a last-resort fallback for the
      // *very first* call (when no explicit width/height was provided
      // and the canvas hasn't been laid out yet). After the initial
      // size has been applied at construction, if the canvas reports
      // zero dimensions, we skip the resize rather than silently
      // clobbering the WebGL framebuffer. The browser will emit
      // another resize event as soon as the canvas is laid out.
      const useFallback = initialSizeApplied && rawW <= 0 && rawH <= 0;
      const w = rawW > 0 ? rawW : useFallback ? initialWidth : null;
      const h = rawH > 0 ? rawH : useFallback ? initialHeight : null;
      if (w === null || h === null) {
        logger('[Three] Resize skipped: invalid canvas dimensions', {
          clientWidth: rawW,
          clientHeight: rawH,
        });
        return;
      }
      if (!applySize(w, h)) {
        logger('[Three] Resize skipped: applySize rejected dimensions', {
          width: w,
          height: h,
        });
        return;
      }
      // The first valid resize (whether the canvas was already laid
      // out or we used the fallback) means subsequent calls should
      // never fall back to the stale initialWidth/Height again.
      initialSizeApplied = false;
      logger('[Three] Resize', { width: w, height: h });
    });
  };

  const attachResizeListener = () => {
    if (resizeListener) {
      return;
    }
    resizeListener = () => handleResize();
    if (typeof window !== 'undefined' && typeof window.addEventListener === 'function') {
      window.addEventListener('resize', resizeListener);
    }
  };

  const detachResizeListener = () => {
    if (resizeListener) {
      if (typeof window !== 'undefined' && typeof window.removeEventListener === 'function') {
        window.removeEventListener('resize', resizeListener);
      }
      resizeListener = null;
    }
  };

  const tick = () => {
    if (!running || disposed) {
      return;
    }
    const delta = clock.getDelta();
    const elapsed = clock.elapsedTime;
    fpsMonitor.tick(delta);
    // Drive registered updaters (sun pulse, future planet spin).
    // Wrap each call in a try/catch so a single buggy updater cannot
    // take down the render loop — we want a clear log line and a
    // continuing animation, not a frozen window.
    for (const updater of updaters) {
      try {
        updater(delta, elapsed);
      } catch (err) {
        logger('[Three] Updater threw', { error: err?.message || String(err) });
        updaters.delete(updater);
      }
    }
    renderer.render(scene, camera);
    rafHandle = rafFactory(tick);
  };

  const start = () => {
    if (running || disposed) {
      return;
    }
    running = true;
    clock.start();
    fpsMonitor.start();
    attachResizeListener();
    rafHandle = rafFactory(tick);
    logger('[Three] Scene started', {
      width: initialWidth,
      height: initialHeight,
      fov,
    });
  };

  const stop = () => {
    if (!running) {
      return;
    }
    running = false;
    if (rafHandle !== null) {
      cancelRaf(rafHandle);
      rafHandle = null;
    }
    fpsMonitor.stop();
    clock.stop();
    logger('[Three] Scene stopped');
  };

  /**
   * Imperative resize (e.g. when the window is dragged across monitors
   * with different DPI). Mirrors the resize handler but takes explicit
   * dimensions so callers can force a sync resize. Returns true on
   * success, false when the dimensions were rejected.
   */
  const setSize = (width, height) => applySize(width, height);

  /**
   * Register a per-frame updater. Returns an unregister function.
   * The updater receives `(delta, elapsedSeconds)`.
   */
  const addUpdater = (updater) => {
    if (typeof updater !== 'function') {
      return () => {};
    }
    updaters.add(updater);
    return () => updaters.delete(updater);
  };

  /**
   * Story 2-2: attach the sun instance to the scene controller and
   * register its update function with the loop. Replaces any prior sun.
   * Returns the disposed/unregistered prior sun if there was one.
   */
  const setSun = (sun) => {
    const previous = sunInstance;
    if (previous && typeof previous.dispose === 'function') {
      previous.dispose();
    }
    // Drop the unregister for the prior sun (if any) so a leaked
    // reference in the loop does not hold the old sun alive.
    if (previous) {
      const prevUnregister = sunUnregisterByInstance.get(previous);
      if (typeof prevUnregister === 'function') {
        prevUnregister();
      }
      sunUnregisterByInstance.delete(previous);
    }
    sunInstance = sun || null;
    if (sunInstance) {
      // Register the sun's per-frame driver with the loop. The returned
      // unregister is stashed in a controller-local WeakMap keyed by
      // the sun instance — NOT on the sun itself. Mutating the public
      // surface of an external factory's return value would be a leaky
      // contract; the WeakMap keeps the bridge private to this
      // controller and lets GC reclaim both entries together.
      const unregister = addUpdater((delta, elapsed) => {
        if (typeof sunInstance.update === 'function') {
          sunInstance.update(delta, elapsed);
        }
      });
      sunUnregisterByInstance.set(sunInstance, unregister);
    }
    return previous;
  };

  const getSun = () => sunInstance;

  /**
   * Story 2-2: push the installed-core-tools set into the sun so its
   * satellite indicators can reflect Sunshine / VDD / Playnite state.
   * No-op when no sun is attached.
   */
  const setInstalledTools = (tools) => {
    if (!sunInstance || typeof sunInstance.setInstalledTools !== 'function') {
      return;
    }
    sunInstance.setInstalledTools(tools);
  };

  const dispose = () => {
    if (disposed) {
      return;
    }
    disposed = true;
    stop();
    detachResizeListener();
    fpsMonitor.dispose();
    // Dispose the sun first so it can detach its updater before the
    // updater registry is cleared. The unregister handle is read
    // from the controller-local WeakMap (NOT from a property on the
    // sun), so the public surface of the sun is left untouched.
    if (sunInstance) {
      const unregister = sunUnregisterByInstance.get(sunInstance);
      if (typeof unregister === 'function') {
        unregister();
      }
      sunUnregisterByInstance.delete(sunInstance);
      if (typeof sunInstance.dispose === 'function') {
        sunInstance.dispose();
      }
      sunInstance = null;
    }
    updaters.clear();
    disposeSceneObjects(scene);
    if (typeof renderer.dispose === 'function') {
      renderer.dispose();
    }
    if (typeof renderer.forceContextLoss === 'function') {
      // Three.js' WebGLRenderer exposes forceContextLoss() to release
      // the GL context back to the browser immediately. Calling it is
      // safe in any browser; in test (jsdom) environments it's a no-op.
      try {
        renderer.forceContextLoss();
      } catch {
        // ignore — some environments don't expose forceContextLoss.
      }
    }
    logger('[Three] Scene disposed');
  };

  /**
   * Replace the FPS sink at runtime. Used by the renderer to push
   * rolling-average FPS values into the Zustand store without
   * requiring the sink to be configured at construction time.
   */
  const setFpsSink = (sink) => {
    fpsMonitor.setFpsSink(typeof sink === 'function' ? sink : null);
  };

  return {
    renderer,
    scene,
    camera,
    start,
    stop,
    setSize,
    handleResize,
    addUpdater,
    setSun,
    getSun,
    setInstalledTools,
    dispose,
    setFpsSink,
    isRunning: () => running,
    isDisposed: () => disposed,
  };
};

// Expose the constructor-time constants for tests and tooling.
export const SCENE_DEFAULTS = Object.freeze({
  fov: DEFAULT_FOV,
  near: DEFAULT_NEAR,
  far: DEFAULT_FAR,
  cameraZ: DEFAULT_CAMERA_Z,
  backgroundColor: DEFAULT_BACKGROUND_COLOR,
  dprCap: DEFAULT_DPR_CAP,
  fpsSampleWindow: DEFAULT_FPS_SAMPLE_WINDOW,
  fpsLogIntervalMs: DEFAULT_FPS_LOG_INTERVAL_MS,
});
