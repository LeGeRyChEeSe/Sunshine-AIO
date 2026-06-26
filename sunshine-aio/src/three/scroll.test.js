/**
 * Tests for src/three/scroll.js (Story 3-1).
 *
 * The scroll controller owns the camera's horizontal pan across the
 * planet sequence. It drives the camera via wheel/pointer events and
 * a critically-damped spring, and clamps/wraps the target at the
 * configured boundary.
 *
 * Test focus:
 *   - Construction: rejects missing camera/canvas; stamps the brand.
 *   - Wheel input: applies an impulse, integrates into the target.
 *   - Drag input: pointerdown/move emits impulses; pointerup stops drag.
 *   - Inertia: update(dt) integrates the velocity, decays friction,
 *     and the camera position converges toward the target.
 *   - Boundary: clamp mode stops at the edges; wrap mode cycles.
 *   - setPlanetCount: re-clamps the current offset to the new edge.
 *   - Lifecycle: attach/detach bind/unbind DOM listeners; dispose
 *     zeros state and prevents further updates.
 *
 * The controller does NOT import Three.js. We pass a plain
 * `camera` object with a `position` slot — exactly what
 * `setup.js` hands to the controller in production. The `canvas`
 * argument is a stub with the few DOM methods the controller calls
 * (`addEventListener`, `removeEventListener`, `setPointerCapture`,
 * `releasePointerCapture`).
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { createHorizontalScrollController, SCROLL_CONTROLLER_BRAND } from './scroll.js';

/**
 * Build a fresh canvas stub for each test. The stub records every
 * DOM call so a test can assert the controller bound/unbound
 * listeners correctly. The pointer-capture methods are no-ops; some
 * tests do not care about them.
 */
const buildCanvasStub = () => {
  const listeners = new Map();
  return {
    listeners,
    addEventListener: vi.fn((name, fn) => {
      listeners.set(name, fn);
    }),
    removeEventListener: vi.fn((name) => {
      listeners.delete(name);
    }),
    setPointerCapture: vi.fn(),
    releasePointerCapture: vi.fn(),
    // emit() is a test-only convenience: drive the listener the way
    // the browser would, without going through real PointerEvent.
    emit(name, payload = {}) {
      const fn = listeners.get(name);
      if (typeof fn === 'function') {
        fn(payload);
      }
    },
  };
};

const buildCameraStub = () => ({
  position: { x: 0, y: 0, z: 5 },
  lookAt: vi.fn(),
});

describe('three/scroll.js (Story 3-1)', () => {
  let camera;
  let canvas;

  beforeEach(() => {
    camera = buildCameraStub();
    canvas = buildCanvasStub();
  });

  describe('construction', () => {
    it('throws when camera is missing', () => {
      expect(() => createHorizontalScrollController({ canvas })).toThrow(/camera is required/);
    });

    it('throws when canvas is missing', () => {
      expect(() => createHorizontalScrollController({ camera })).toThrow(/canvas is required/);
    });

    it('stamps the SCROLL_CONTROLLER_BRAND on the returned object', () => {
      const scroll = createHorizontalScrollController({ camera, canvas, planetCount: 3 });
      expect(scroll[SCROLL_CONTROLLER_BRAND]).toBe(true);
    });

    it('exposes the configured planet count and spacing-derived max offset', () => {
      const scroll = createHorizontalScrollController({
        camera,
        canvas,
        planetCount: 4,
        planetSpacing: 2,
      });
      // 4 planets with spacing 2 → first at 0, last at 6 → maxOffset 6.
      expect(scroll.getPlanetCount()).toBe(4);
      expect(scroll.getMaxOffset()).toBe(6);
    });

    it('collapses to maxOffset=0 when planetCount is 0', () => {
      const scroll = createHorizontalScrollController({ camera, canvas, planetCount: 0 });
      expect(scroll.getMaxOffset()).toBe(0);
      expect(scroll.getPlanetCount()).toBe(0);
    });

    it('falls back to clamp mode when boundaryMode is unknown', () => {
      const logger = vi.fn();
      const scroll = createHorizontalScrollController({
        camera,
        canvas,
        planetCount: 3,
        boundaryMode: 'bogus',
        logger,
      });
      expect(scroll.getBoundaryMode()).toBe('clamp');
      expect(logger).toHaveBeenCalledWith(
        expect.stringContaining('Unknown boundaryMode'),
        expect.objectContaining({ requested: 'bogus' })
      );
    });

    it('accepts boundaryMode="wrap"', () => {
      const scroll = createHorizontalScrollController({
        camera,
        canvas,
        planetCount: 3,
        boundaryMode: 'wrap',
      });
      expect(scroll.getBoundaryMode()).toBe('wrap');
    });
  });

  describe('wheel input', () => {
    it('attaches a wheel listener when attach() is called', () => {
      const scroll = createHorizontalScrollController({ camera, canvas, planetCount: 4 });
      scroll.attach();
      expect(canvas.addEventListener).toHaveBeenCalledWith('wheel', expect.any(Function), {
        passive: true,
      });
      scroll.dispose();
    });

    it('does not call addEventListener twice on double-attach', () => {
      const scroll = createHorizontalScrollController({ camera, canvas, planetCount: 4 });
      scroll.attach();
      scroll.attach();
      // One wheel listener registration is the contract; a second
      // attach must be a no-op so a re-entrant caller doesn't double
      // the wheel traffic.
      const wheelCalls = canvas.addEventListener.mock.calls.filter(([n]) => n === 'wheel');
      expect(wheelCalls).toHaveLength(1);
      scroll.dispose();
    });

    it('applies a wheel impulse that pushes the target', () => {
      const scroll = createHorizontalScrollController({
        camera,
        canvas,
        planetCount: 4,
        wheelScale: 1, // 1:1 to make assertions easy
      });
      scroll.attach();
      // 200 px of wheel motion = 200 world units of target advance.
      canvas.emit('wheel', { deltaY: 200 });
      // The impulse is integrated into velocity; the target only
      // moves when `update()` runs. The impulse lands in velocity.
      expect(scroll.getVelocity()).toBeGreaterThan(0);
      scroll.dispose();
    });

    it('ignores wheel events when disabled', () => {
      const scroll = createHorizontalScrollController({ camera, canvas, planetCount: 4 });
      scroll.attach();
      scroll.setEnabled(false);
      canvas.emit('wheel', { deltaY: 200 });
      expect(scroll.getVelocity()).toBe(0);
      scroll.dispose();
    });
  });

  describe('drag input', () => {
    it('attaches pointer listeners on attach()', () => {
      const scroll = createHorizontalScrollController({ camera, canvas, planetCount: 4 });
      scroll.attach();
      const names = canvas.addEventListener.mock.calls.map(([n]) => n);
      expect(names).toEqual(
        expect.arrayContaining(['pointerdown', 'pointermove', 'pointerup', 'pointercancel'])
      );
      scroll.dispose();
    });

    it('starts a drag on pointerdown and applies a positive impulse on move', () => {
      const scroll = createHorizontalScrollController({
        camera,
        canvas,
        planetCount: 4,
        dragScale: 1,
      });
      scroll.attach();
      canvas.emit('pointerdown', { button: 0, pointerId: 1, clientX: 0 });
      canvas.emit('pointermove', { pointerId: 1, clientX: -50 });
      // Drag right (clientX: -50 → 0): convention is to push the
      // camera LEFT (negative offset), so a drag-right should
      // produce negative velocity.
      canvas.emit('pointermove', { pointerId: 1, clientX: 0 });
      expect(scroll.getVelocity()).toBeLessThan(0);
      scroll.dispose();
    });

    it('ignores right-button clicks', () => {
      const scroll = createHorizontalScrollController({ camera, canvas, planetCount: 4 });
      scroll.attach();
      canvas.emit('pointerdown', { button: 2, pointerId: 1, clientX: 0 });
      canvas.emit('pointermove', { pointerId: 1, clientX: -100 });
      expect(scroll.getVelocity()).toBe(0);
      scroll.dispose();
    });

    it('stops dragging on pointerup and releases pointer capture', () => {
      const scroll = createHorizontalScrollController({ camera, canvas, planetCount: 4 });
      scroll.attach();
      canvas.emit('pointerdown', { button: 0, pointerId: 7, clientX: 0 });
      canvas.emit('pointerup', { pointerId: 7, clientX: 0 });
      expect(canvas.releasePointerCapture).toHaveBeenCalledWith(7);
      scroll.dispose();
    });

    it('stops dragging on pointercancel', () => {
      const scroll = createHorizontalScrollController({ camera, canvas, planetCount: 4 });
      scroll.attach();
      canvas.emit('pointerdown', { button: 0, pointerId: 9, clientX: 0 });
      canvas.emit('pointercancel', { pointerId: 9 });
      // After cancel, pointermove must NOT accumulate more impulse.
      canvas.emit('pointermove', { pointerId: 9, clientX: 100 });
      expect(scroll.getVelocity()).toBe(0);
      scroll.dispose();
    });
  });

  describe('inertia + spring', () => {
    it('update(dt) advances the target from velocity', () => {
      const scroll = createHorizontalScrollController({
        camera,
        canvas,
        planetCount: 4,
        wheelScale: 1,
      });
      scroll.attach();
      canvas.emit('wheel', { deltaY: 100 });
      const targetBefore = scroll.getTarget();
      scroll.update(0.1);
      expect(scroll.getTarget()).toBeGreaterThan(targetBefore);
      scroll.dispose();
    });

    it('friction decays the velocity over time', () => {
      const scroll = createHorizontalScrollController({
        camera,
        canvas,
        planetCount: 4,
        wheelScale: 1,
        friction: 5,
      });
      scroll.attach();
      canvas.emit('wheel', { deltaY: 100 });
      const v0 = scroll.getVelocity();
      // 1 second of updates should reduce the velocity to ~0 (the
      // closed-form decay is `v0 * exp(-friction * dt)` summed over
      // frames; with dt=0.1 and friction=5 we expect less than 1% of
      // the original velocity).
      for (let i = 0; i < 20; i += 1) {
        scroll.update(0.1);
      }
      expect(Math.abs(scroll.getVelocity())).toBeLessThan(Math.abs(v0) * 0.01);
      scroll.dispose();
    });

    it('the camera position converges to the target after many frames', () => {
      const scroll = createHorizontalScrollController({
        camera,
        canvas,
        planetCount: 4,
        wheelScale: 1,
        damping: 12,
      });
      scroll.attach();
      canvas.emit('wheel', { deltaY: 50 });
      for (let i = 0; i < 200; i += 1) {
        scroll.update(0.05);
      }
      // After enough time the camera's X must equal the target.
      expect(camera.position.x).toBeCloseTo(scroll.getTarget(), 4);
      scroll.dispose();
    });

    it('clamps the velocity to maxVelocity', () => {
      const scroll = createHorizontalScrollController({
        camera,
        canvas,
        planetCount: 4,
        wheelScale: 1,
        maxVelocity: 2,
      });
      scroll.attach();
      // A huge wheel event should not push the velocity past the cap.
      canvas.emit('wheel', { deltaY: 1e9 });
      expect(scroll.getVelocity()).toBeLessThanOrEqual(2);
      canvas.emit('wheel', { deltaY: -1e9 });
      // The negative wheel reverses direction; the absolute cap
      // should hold.
      expect(scroll.getVelocity()).toBeGreaterThanOrEqual(-2);
      scroll.dispose();
    });
  });

  describe('boundary modes', () => {
    it('clamp mode stops the target at the right edge', () => {
      const scroll = createHorizontalScrollController({
        camera,
        canvas,
        planetCount: 3,
        planetSpacing: 1,
        wheelScale: 1,
      });
      scroll.attach();
      // Push the target past the right edge (maxOffset = 2).
      for (let i = 0; i < 100; i += 1) {
        scroll.update(0.5);
        canvas.emit('wheel', { deltaY: 100 });
      }
      expect(scroll.getTarget()).toBe(2);
      expect(scroll.getOffset()).toBeLessThanOrEqual(2);
      scroll.dispose();
    });

    it('clamp mode stops the target at the left edge', () => {
      const scroll = createHorizontalScrollController({
        camera,
        canvas,
        planetCount: 3,
        planetSpacing: 1,
        wheelScale: 1,
      });
      scroll.attach();
      for (let i = 0; i < 100; i += 1) {
        scroll.update(0.5);
        canvas.emit('wheel', { deltaY: -100 });
      }
      expect(scroll.getTarget()).toBe(0);
      expect(scroll.getOffset()).toBeGreaterThanOrEqual(0);
      scroll.dispose();
    });

    it('wrap mode cycles the target across the boundary', () => {
      const scroll = createHorizontalScrollController({
        camera,
        canvas,
        planetCount: 3,
        planetSpacing: 1,
        wheelScale: 1,
        boundaryMode: 'wrap',
      });
      scroll.attach();
      // Push well past the right edge (maxOffset = 2) and let the
      // wrap kick in. After a few frames the target should land in
      // [0, maxOffset).
      for (let i = 0; i < 60; i += 1) {
        scroll.update(0.05);
        canvas.emit('wheel', { deltaY: 100 });
      }
      const target = scroll.getTarget();
      expect(target).toBeGreaterThanOrEqual(0);
      expect(target).toBeLessThan(2);
      scroll.dispose();
    });
  });

  describe('jumpTo', () => {
    it('moves both target and offset to the requested value', () => {
      const scroll = createHorizontalScrollController({
        camera,
        canvas,
        planetCount: 4,
        planetSpacing: 1,
      });
      expect(scroll.jumpTo(2)).toBe(true);
      expect(scroll.getTarget()).toBe(2);
      expect(scroll.getOffset()).toBe(2);
      expect(camera.position.x).toBe(2);
    });

    it('rejects non-finite values', () => {
      const scroll = createHorizontalScrollController({ camera, canvas, planetCount: 4 });
      expect(scroll.jumpTo(NaN)).toBe(false);
      expect(scroll.jumpTo(Infinity)).toBe(false);
    });

    it('clamps to the boundary in clamp mode', () => {
      const scroll = createHorizontalScrollController({
        camera,
        canvas,
        planetCount: 3,
        planetSpacing: 1,
      });
      scroll.jumpTo(100);
      expect(scroll.getOffset()).toBe(2);
    });

    it('wraps in wrap mode', () => {
      const scroll = createHorizontalScrollController({
        camera,
        canvas,
        planetCount: 3,
        planetSpacing: 1,
        boundaryMode: 'wrap',
      });
      scroll.jumpTo(5); // 5 mod 2 = 1
      expect(scroll.getOffset()).toBe(1);
    });
  });

  describe('setPlanetCount', () => {
    it('re-clamps the current offset when the universe shrinks', () => {
      const scroll = createHorizontalScrollController({
        camera,
        canvas,
        planetCount: 5,
        planetSpacing: 1,
      });
      scroll.jumpTo(4);
      // Shrink to 2 planets → maxOffset = 1.
      scroll.setPlanetCount(2);
      expect(scroll.getOffset()).toBe(1);
      expect(scroll.getPlanetCount()).toBe(2);
    });

    it('re-wraps the current offset when the universe shrinks under wrap mode', () => {
      const scroll = createHorizontalScrollController({
        camera,
        canvas,
        planetCount: 5,
        planetSpacing: 1,
        boundaryMode: 'wrap',
      });
      scroll.jumpTo(4);
      // Shrink to 3 planets → length = 2. 4 mod 2 = 0.
      scroll.setPlanetCount(3);
      expect(scroll.getOffset()).toBe(0);
    });

    it('zeroes the offset when the universe collapses to 0', () => {
      const scroll = createHorizontalScrollController({
        camera,
        canvas,
        planetCount: 3,
        planetSpacing: 1,
      });
      scroll.jumpTo(2);
      scroll.setPlanetCount(0);
      expect(scroll.getOffset()).toBe(0);
    });
  });

  describe('lifecycle', () => {
    it('detach removes every listener that attach registered', () => {
      const scroll = createHorizontalScrollController({ camera, canvas, planetCount: 4 });
      scroll.attach();
      const names = ['wheel', 'pointerdown', 'pointermove', 'pointerup', 'pointercancel'];
      for (const name of names) {
        expect(canvas.listeners.has(name)).toBe(true);
      }
      scroll.detach();
      for (const name of names) {
        expect(canvas.listeners.has(name)).toBe(false);
      }
      scroll.dispose();
    });

    it('dispose prevents further updates', () => {
      const scroll = createHorizontalScrollController({ camera, canvas, planetCount: 4 });
      scroll.attach();
      canvas.emit('wheel', { deltaY: 50 });
      const v0 = scroll.getVelocity();
      scroll.dispose();
      scroll.update(1);
      expect(scroll.getVelocity()).toBe(0);
      expect(scroll.getOffset()).toBe(0);
      expect(scroll.getTarget()).toBe(0);
      expect(v0).toBeGreaterThan(0); // sanity: pre-dispose had momentum
    });

    it('dispose detaches listeners', () => {
      const scroll = createHorizontalScrollController({ camera, canvas, planetCount: 4 });
      scroll.attach();
      scroll.dispose();
      expect(canvas.listeners.has('wheel')).toBe(false);
    });

    it('setEnabled(false) zeros the velocity', () => {
      const scroll = createHorizontalScrollController({ camera, canvas, planetCount: 4 });
      scroll.attach();
      canvas.emit('wheel', { deltaY: 50 });
      expect(scroll.getVelocity()).toBeGreaterThan(0);
      scroll.setEnabled(false);
      expect(scroll.getVelocity()).toBe(0);
      scroll.dispose();
    });
  });
});
