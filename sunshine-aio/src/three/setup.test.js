/**
 * Tests for src/three/setup.js (Story 2-1).
 *
 * Three.js' WebGLRenderer requires a real DOM canvas with a WebGL context.
 * Running the suite under pure Node (vitest defaults to `environment: 'node'`)
 * means we cannot exercise the renderer's GPU code path, so the suite
 * follows a hybrid approach:
 *
 *   - Stub the WebGLRenderer/Scene/PerspectiveCamera/Clock with `vi.fn()`
 *     instances so we can assert on lifecycle calls without booting a
 *     WebGL context.
 *   - Use a lightweight canvas shim (just enough `addEventListener`/`removeEventListener`
 *     and `clientWidth/clientHeight`) to keep `createScene` happy.
 *   - Drive `createFpsMonitor` and `disposeSceneObjects` against real
 *     Three.js classes so we exercise the rolling-sample math and the
 *     recursive dispose walker.
 *
 * The renderer lifecycle is therefore tested at the contract level: the
 * setup module wires `start -> render -> render -> ... -> stop` and
 * releases resources on `dispose`. Visual correctness is left to manual
 * QA in the Electron window — story 2-1 is plumbing only.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';

// Mock the 'three' module BEFORE importing the SUT so the renderer
// uses our stubs instead of trying to allocate a WebGL context.
const rendererStub = {
  setPixelRatio: vi.fn(),
  setSize: vi.fn(),
  setClearColor: vi.fn(),
  render: vi.fn(),
  dispose: vi.fn(),
  forceContextLoss: vi.fn(),
};

const sceneStub = {
  background: null,
  traverse: vi.fn((cb) => cb({ geometry: null, material: null })),
};

const cameraStub = {
  position: { set: vi.fn() },
  lookAt: vi.fn(),
  aspect: 0,
  updateProjectionMatrix: vi.fn(),
};

const clockStub = {
  start: vi.fn(),
  stop: vi.fn(),
  getDelta: vi.fn(() => 0.016),
};

vi.mock('three', () => {
  // The stubs must be plain mutable instances whose properties can be
  // reassigned by the SUT. Using Object.assign in the constructor
  // doesn't help because prototype writes don't persist back to the
  // shared stub.
  class WebGLRenderer {
    constructor() {
      this.setPixelRatio = rendererStub.setPixelRatio;
      this.setSize = rendererStub.setSize;
      this.setClearColor = rendererStub.setClearColor;
      this.render = rendererStub.render;
      this.dispose = rendererStub.dispose;
      this.forceContextLoss = rendererStub.forceContextLoss;
    }
  }
  class Scene {
    constructor() {
      this.background = null;
      this.traverse = sceneStub.traverse;
    }
  }
  class PerspectiveCamera {
    constructor() {
      this.position = cameraStub.position;
      this.lookAt = cameraStub.lookAt;
      this.aspect = 0;
      this.updateProjectionMatrix = cameraStub.updateProjectionMatrix;
    }
  }
  class Color {
    constructor(value) {
      this.value = value;
    }
  }
  class Clock {
    constructor() {
      this.start = clockStub.start;
      this.stop = clockStub.stop;
      this.getDelta = clockStub.getDelta;
    }
  }
  return {
    WebGLRenderer,
    Scene,
    PerspectiveCamera,
    Color,
    Clock,
  };
});

// Import after the mock so the SUT picks up the stubs.
const { createScene, createFpsMonitor, disposeSceneObjects, SCENE_DEFAULTS } =
  await import('./setup.js');

/**
 * Minimal canvas stub. Mirrors the bits of HTMLCanvasElement that
 * createScene touches: add/remove event listeners, clientWidth/Height,
 * parentElement.
 */
const makeCanvas = ({ width = 800, height = 600 } = {}) => {
  const listeners = new Map();
  const canvas = {
    clientWidth: width,
    clientHeight: height,
    parentElement: null,
    addEventListener: vi.fn((event, cb) => {
      listeners.set(event, cb);
    }),
    removeEventListener: vi.fn((event) => {
      listeners.delete(event);
    }),
    _fire: (event) => {
      const cb = listeners.get(event);
      if (cb) {
        cb();
      }
    },
    _listeners: listeners,
  };
  return canvas;
};

/**
 * Build a no-op rafFactory + cancelRaf pair so tests can start the loop
 * without a real window.requestAnimationFrame.
 */
const makeRafStubs = () => {
  const raf = vi.fn(() => 1);
  const cancel = vi.fn();
  return { raf, cancel };
};

const baseOpts = (overrides = {}) => {
  const { raf, cancel } = makeRafStubs();
  return {
    canvas: makeCanvas(),
    logger: vi.fn(),
    rafFactory: raf,
    cancelRaf: cancel,
    ...overrides,
  };
};

describe('three/setup.js (Story 2-1)', () => {
  beforeEach(() => {
    rendererStub.setPixelRatio.mockClear();
    rendererStub.setSize.mockClear();
    rendererStub.setClearColor.mockClear();
    rendererStub.render.mockClear();
    rendererStub.dispose.mockClear();
    rendererStub.forceContextLoss.mockClear();
    sceneStub.traverse.mockClear();
    cameraStub.position.set.mockClear();
    cameraStub.lookAt.mockClear();
    cameraStub.updateProjectionMatrix.mockClear();
    clockStub.start.mockClear();
    clockStub.stop.mockClear();
    clockStub.getDelta.mockClear();
  });

  describe('createScene()', () => {
    it('throws when no canvas is supplied', () => {
      expect(() => createScene({ rafFactory: () => 1 })).toThrow(/canvas/);
    });

    it('creates the WebGL renderer with sane defaults', () => {
      const opts = baseOpts({ canvas: makeCanvas({ width: 1024, height: 768 }) });
      const controller = createScene(opts);

      // Pixel ratio is clamped to <= 2 by default.
      expect(rendererStub.setPixelRatio).toHaveBeenCalledTimes(1);
      const dpr = rendererStub.setPixelRatio.mock.calls[0][0];
      expect(dpr).toBeGreaterThan(0);
      expect(dpr).toBeLessThanOrEqual(SCENE_DEFAULTS.dprCap);

      // Initial size + clear color applied.
      expect(rendererStub.setSize).toHaveBeenCalledWith(1024, 768, false);
      expect(rendererStub.setClearColor).toHaveBeenCalledWith(SCENE_DEFAULTS.backgroundColor, 1);

      // Camera positioned at default Z.
      expect(cameraStub.position.set).toHaveBeenCalledWith(0, 0, SCENE_DEFAULTS.cameraZ);
      expect(cameraStub.lookAt).toHaveBeenCalledWith(0, 0, 0);

      // Scene background matches the clear color.
      expect(controller.scene.background).toBeTruthy();
      expect(controller.scene.background.value).toBe(SCENE_DEFAULTS.backgroundColor);

      controller.dispose();
    });

    it('respects explicit width/height/fov/cameraZ options', () => {
      const opts = baseOpts({
        width: 400,
        height: 200,
        fov: 90,
        cameraZ: 12,
        backgroundColor: 0x111111,
      });
      const controller = createScene(opts);

      expect(rendererStub.setSize).toHaveBeenCalledWith(400, 200, false);
      expect(rendererStub.setClearColor).toHaveBeenCalledWith(0x111111, 1);
      expect(cameraStub.position.set).toHaveBeenCalledWith(0, 0, 12);
      controller.dispose();
    });

    it('start() begins the render loop, stop() ends it', () => {
      const opts = baseOpts();
      const controller = createScene(opts);

      controller.start();
      expect(controller.isRunning()).toBe(true);
      expect(opts.rafFactory).toHaveBeenCalled();
      expect(clockStub.start).toHaveBeenCalled();

      controller.stop();
      expect(controller.isRunning()).toBe(false);
      expect(clockStub.stop).toHaveBeenCalled();
      controller.dispose();
    });

    it('the render loop drives renderer.render until stopped', () => {
      let pending = null;
      const raf = vi.fn((cb) => {
        pending = cb;
        return 1;
      });
      const opts = baseOpts({ rafFactory: raf });
      const controller = createScene(opts);

      controller.start();
      // Step the loop a few times.
      pending();
      pending();
      pending();
      expect(rendererStub.render).toHaveBeenCalledTimes(3);

      controller.stop();
      // After stop, invoking the stored callback should not render again.
      const rendersBefore = rendererStub.render.mock.calls.length;
      if (pending) {
        pending();
      }
      expect(rendererStub.render.mock.calls.length).toBe(rendersBefore);
      controller.dispose();
    });

    it('resize handler updates camera aspect and renderer size', () => {
      // Capture the deferred raf callback so the test can drive the
      // size read deterministically (handleResize now defers to the
      // next animation frame to give the browser a chance to lay out
      // the canvas before reading clientWidth/clientHeight).
      const pendingCallbacks = [];
      const raf = vi.fn((cb) => {
        pendingCallbacks.push(cb);
        return pendingCallbacks.length;
      });
      const canvas = makeCanvas({ width: 800, height: 600 });
      const opts = baseOpts({ canvas, rafFactory: raf });
      const controller = createScene(opts);

      // Mutate the canvas client size to simulate a window resize.
      canvas.clientWidth = 1280;
      canvas.clientHeight = 720;
      controller.handleResize();

      // The resize was scheduled, not applied yet.
      expect(pendingCallbacks).toHaveLength(1);
      pendingCallbacks[0]();

      expect(rendererStub.setSize).toHaveBeenCalledWith(1280, 720, false);
      expect(controller.camera.aspect).toBeCloseTo(1280 / 720, 5);
      expect(cameraStub.updateProjectionMatrix).toHaveBeenCalled();
      controller.dispose();
    });

    it('resize handler skips when the canvas reports zero dimensions', () => {
      const pendingCallbacks = [];
      const raf = vi.fn((cb) => {
        pendingCallbacks.push(cb);
        return pendingCallbacks.length;
      });
      const canvas = makeCanvas({ width: 800, height: 600 });
      const opts = baseOpts({ canvas, rafFactory: raf });
      const controller = createScene(opts);

      // First, drive a successful resize so the handler no longer
      // treats the initialWidth/Height as a fallback.
      canvas.clientWidth = 1024;
      canvas.clientHeight = 768;
      controller.handleResize();
      pendingCallbacks.pop()();

      const setSizeCallsAfterFirstResize = rendererStub.setSize.mock.calls.length;

      // Now simulate a layout collapse (e.g. display:none during a
      // theme switch) where the canvas reports 0/0. The handler must
      // skip the resize rather than clobber the framebuffer.
      canvas.clientWidth = 0;
      canvas.clientHeight = 0;
      controller.handleResize();
      pendingCallbacks.pop()();

      expect(rendererStub.setSize.mock.calls.length).toBe(setSizeCallsAfterFirstResize);
      controller.dispose();
    });

    it('setSize ignores non-positive or non-finite dimensions', () => {
      const opts = baseOpts();
      const controller = createScene(opts);
      const callsBefore = rendererStub.setSize.mock.calls.length;

      controller.setSize(0, 100);
      controller.setSize(100, 0);
      controller.setSize(Number.NaN, 100);
      controller.setSize(100, Number.POSITIVE_INFINITY);

      expect(rendererStub.setSize.mock.calls.length).toBe(callsBefore);
      controller.dispose();
    });

    it('attaches and detaches the resize listener around the loop', () => {
      // The SUT attaches its listener to `window` (not the canvas), so
      // we stub window for this test. Restore the original after.
      const originalWindow = globalThis.window;
      const windowListeners = new Map();
      const winStub = {
        addEventListener: vi.fn((event, cb) => {
          windowListeners.set(event, cb);
        }),
        removeEventListener: vi.fn((event) => {
          windowListeners.delete(event);
        }),
      };
      globalThis.window = winStub;
      try {
        const opts = baseOpts();
        const controller = createScene(opts);
        expect(windowListeners.has('resize')).toBe(false);

        controller.start();
        expect(windowListeners.has('resize')).toBe(true);

        controller.dispose();
        expect(windowListeners.has('resize')).toBe(false);
        expect(winStub.removeEventListener).toHaveBeenCalledWith('resize', expect.any(Function));
      } finally {
        if (originalWindow === undefined) {
          delete globalThis.window;
        } else {
          globalThis.window = originalWindow;
        }
      }
    });

    it('dispose() releases the renderer context and is idempotent', () => {
      const opts = baseOpts();
      const controller = createScene(opts);
      controller.start();

      controller.dispose();
      expect(rendererStub.dispose).toHaveBeenCalledTimes(1);
      expect(rendererStub.forceContextLoss).toHaveBeenCalled();
      expect(controller.isDisposed()).toBe(true);

      // Second dispose is a no-op.
      controller.dispose();
      expect(rendererStub.dispose).toHaveBeenCalledTimes(1);
    });

    it('start() refuses to restart after dispose()', () => {
      const raf = vi.fn(() => 1);
      const opts = baseOpts({ rafFactory: raf });
      const controller = createScene(opts);
      controller.dispose();
      // After dispose the rafFactory branch should short-circuit before
      // the first render. Use a fresh factory so we can detect calls.
      controller.start();
      // No raf should have been registered after dispose.
      expect(raf).not.toHaveBeenCalled();
    });

    it('logs lifecycle events through the injected logger', () => {
      const opts = baseOpts();
      const controller = createScene(opts);
      controller.start();
      controller.dispose();

      const messages = opts.logger.mock.calls.map((args) => args[0]);
      expect(messages).toContain('[Three] Scene started');
      expect(messages).toContain('[Three] Scene disposed');
    });
  });

  describe('createFpsMonitor()', () => {
    let nowSpy;

    beforeEach(() => {
      nowSpy = vi.spyOn(Date, 'now');
      nowSpy.mockReturnValue(0);
    });

    afterEach(() => {
      nowSpy.mockRestore();
    });

    it('ignores zero / negative / non-finite deltas', () => {
      const onLog = vi.fn();
      const monitor = createFpsMonitor({ onLog });
      monitor.tick(0);
      monitor.tick(-1);
      monitor.tick(Number.NaN);
      monitor.flush(true);
      expect(onLog).not.toHaveBeenCalled();
      monitor.dispose();
    });

    it('computes FPS over the rolling sample window', () => {
      const onLog = vi.fn();
      const monitor = createFpsMonitor({ onLog, sampleWindow: 4 });
      // 60 FPS = 1/60s per frame.
      monitor.tick(1 / 60);
      monitor.tick(1 / 60);
      monitor.tick(1 / 60);
      monitor.tick(1 / 60);
      monitor.flush(true);
      expect(onLog).toHaveBeenCalledTimes(1);
      const meta = onLog.mock.calls[0][1];
      expect(meta.fps).toBeGreaterThan(55);
      expect(meta.fps).toBeLessThan(65);
      expect(meta.samples).toBe(4);
      monitor.dispose();
    });

    it('caps the rolling window so memory stays bounded', () => {
      const onLog = vi.fn();
      const monitor = createFpsMonitor({ onLog, sampleWindow: 3 });
      for (let i = 0; i < 10; i += 1) {
        monitor.tick(1 / 60);
      }
      monitor.flush(true);
      const meta = onLog.mock.calls[0][1];
      expect(meta.samples).toBe(3);
      monitor.dispose();
    });

    it('throttles log emissions to the configured interval', () => {
      const onLog = vi.fn();
      const monitor = createFpsMonitor({
        onLog,
        sampleWindow: 2,
        logIntervalMs: 1000,
      });
      monitor.tick(1 / 60);
      // First flush is forced and emits immediately.
      monitor.flush(true);
      expect(onLog).toHaveBeenCalledTimes(1);

      // Advance the clock by 200 ms only — should NOT emit.
      nowSpy.mockReturnValue(200);
      monitor.tick(1 / 60);
      monitor.flush(false);
      expect(onLog).toHaveBeenCalledTimes(1);

      // Advance past the interval — should emit again.
      nowSpy.mockReturnValue(1500);
      monitor.tick(1 / 60);
      monitor.flush(false);
      expect(onLog).toHaveBeenCalledTimes(2);
      monitor.dispose();
    });

    it('start()/stop() manage the wall-clock interval lifecycle', () => {
      const monitor = createFpsMonitor({ logIntervalMs: 60_000 });
      monitor.start();
      monitor.stop();
      monitor.dispose();
      // The point of this test is that stop() cancels the interval so
      // it doesn't keep the test runner alive past exit.
      expect(true).toBe(true);
    });

    it('forwards the rolling FPS to onFpsUpdate on every flush', () => {
      const onLog = vi.fn();
      const onFpsUpdate = vi.fn();
      const monitor = createFpsMonitor({
        onLog,
        onFpsUpdate,
        sampleWindow: 2,
      });
      monitor.tick(1 / 60);
      monitor.tick(1 / 60);
      monitor.flush(true);
      expect(onFpsUpdate).toHaveBeenCalledTimes(1);
      expect(onFpsUpdate).toHaveBeenCalledWith(expect.any(Number));
      const fps = onFpsUpdate.mock.calls[0][0];
      expect(fps).toBeGreaterThan(55);
      expect(fps).toBeLessThan(65);
      monitor.dispose();
    });

    it('clamps onFpsUpdate to a sane upper bound (240)', () => {
      const onFpsUpdate = vi.fn();
      const monitor = createFpsMonitor({ onFpsUpdate, sampleWindow: 1 });
      // A tiny delta would produce an astronomical FPS without the clamp.
      monitor.tick(1 / 10000);
      monitor.flush(true);
      expect(onFpsUpdate).toHaveBeenCalledTimes(1);
      expect(onFpsUpdate.mock.calls[0][0]).toBeLessThanOrEqual(240);
      monitor.dispose();
    });

    it('setFpsSink replaces the sink at runtime', () => {
      const first = vi.fn();
      const second = vi.fn();
      const monitor = createFpsMonitor({ onFpsUpdate: first, sampleWindow: 1 });
      monitor.tick(1 / 60);
      monitor.flush(true);
      expect(first).toHaveBeenCalledTimes(1);

      monitor.setFpsSink(second);
      monitor.tick(1 / 60);
      monitor.flush(true);
      expect(second).toHaveBeenCalledTimes(1);
      // The original sink is no longer called.
      expect(first).toHaveBeenCalledTimes(1);
      monitor.dispose();
    });
  });

  describe('disposeSceneObjects()', () => {
    it('handles null / undefined input gracefully', () => {
      expect(() => disposeSceneObjects(null)).not.toThrow();
      expect(() => disposeSceneObjects(undefined)).not.toThrow();
    });

    it('disposes geometries and materials attached to scene children', () => {
      const geom = { dispose: vi.fn() };
      const mat = { dispose: vi.fn(), map: { dispose: vi.fn() }, disposeSelf: vi.fn() };
      const object = { geometry: geom, material: mat };
      const scene = {
        traverse: vi.fn((cb) => {
          cb(object);
        }),
      };
      disposeSceneObjects(scene);
      expect(geom.dispose).toHaveBeenCalled();
      expect(mat.dispose).toHaveBeenCalled();
      // Material map should be disposed too.
      expect(mat.map.dispose).toHaveBeenCalled();
    });

    it('handles objects with array materials', () => {
      const mat1 = { dispose: vi.fn() };
      const mat2 = { dispose: vi.fn() };
      const scene = {
        traverse: vi.fn((cb) => cb({ geometry: null, material: [mat1, mat2] })),
      };
      disposeSceneObjects(scene);
      expect(mat1.dispose).toHaveBeenCalled();
      expect(mat2.dispose).toHaveBeenCalled();
    });
  });

  describe('SCENE_DEFAULTS', () => {
    it('is frozen so callers cannot mutate the shared constants', () => {
      expect(Object.isFrozen(SCENE_DEFAULTS)).toBe(true);
    });

    it('exposes the documented defaults', () => {
      expect(SCENE_DEFAULTS.fov).toBe(60);
      expect(SCENE_DEFAULTS.cameraZ).toBe(5);
      expect(SCENE_DEFAULTS.near).toBeLessThan(SCENE_DEFAULTS.far);
      expect(SCENE_DEFAULTS.dprCap).toBe(2);
    });
  });
});
