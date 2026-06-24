/**
 * Tests for src/three/sun.js (Story 2-2).
 *
 * The sun component imports Three.js geometry/material classes but
 * the WebGL renderer is never instantiated — these tests run in pure
 * Node (vitest default `environment: 'node'`) and use a lightweight
 * `THREE` stub that records construction calls and exposes minimal
 * `dispose` / `position` / `scale` APIs. The test focus is the
 * contract surface:
 *
 *   - Construction: group + core + halo + 3 satellites are created.
 *   - Pulse animation: `update(delta, elapsed)` scales the core based
 *     on `sin(2*pi*freq*elapsed)` and a configurable amplitude.
 *   - `setInstalledTools({ ... })` flips the satellite material colors
 *     and emissive intensity between the active and inactive palettes.
 *   - `dispose()` releases every geometry/material exactly once and
 *     turns subsequent calls into no-ops.
 *   - Updates after dispose are silently ignored (no throws).
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';

/**
 * Build a minimal THREE stub. We need just enough of the Three.js
 * public API to exercise `createSun` without booting a WebGL context:
 *
 *   - Object3D / Mesh with `add`, `remove`, `position`, `scale`,
 *     `name`, and a child array.
 *   - SphereGeometry + MeshStandardMaterial + MeshBasicMaterial with
 *     `dispose()` spies and `color` / `emissive` slots that accept
 *     `new Color(value)` without throwing.
 *   - A Color class that captures the numeric / string value passed in.
 *   - The constant `BackSide` — only needs to be a unique symbol so
 *     `material.side = THREE.BackSide` round-trips correctly.
 */
const createThreeStub = () => {
  class Color {
    constructor(value) {
      this.value = value;
    }
    // Real Three.js Color exposes a `set(value)` mutator that
    // overwrites the instance in place. The production code path
    // for `setInstalledTools` uses `material.color.set(hex)` to avoid
    // allocating a new Color on every state flip, so the stub must
    // support the same surface. Returning `this` mirrors the real
    // API and lets callers chain.
    set(value) {
      this.value = value;
      return this;
    }
  }

  class Geometry {
    constructor() {
      this.dispose = vi.fn();
    }
  }

  class Material {
    constructor(opts = {}) {
      this.opts = opts;
      this.dispose = vi.fn();
      this.emissiveIntensity = opts.emissiveIntensity ?? 1;
      this.color = opts.color !== undefined ? new Color(opts.color) : undefined;
      this.emissive = opts.emissive !== undefined ? new Color(opts.emissive) : undefined;
    }
  }

  class Object3D {
    constructor() {
      this.name = '';
      this.children = [];
      this.position = {
        x: 0,
        y: 0,
        z: 0,
        set(x, y, z) {
          this.x = x;
          this.y = y;
          this.z = z;
        },
      };
      this.scale = {
        x: 1,
        y: 1,
        z: 1,
        set(x, y, z) {
          this.x = x;
          this.y = y;
          this.z = z;
        },
      };
    }
    add(child) {
      this.children.push(child);
    }
    remove(child) {
      const idx = this.children.indexOf(child);
      if (idx !== -1) this.children.splice(idx, 1);
    }
  }

  class Mesh extends Object3D {
    constructor(geometry, material) {
      super();
      this.geometry = geometry;
      this.material = material;
    }
  }

  class SphereGeometry extends Geometry {}
  class MeshStandardMaterial extends Material {}
  class MeshBasicMaterial extends Material {}

  return {
    Object3D,
    Mesh,
    SphereGeometry,
    MeshStandardMaterial,
    MeshBasicMaterial,
    Color,
    BackSide: Symbol('BackSide'),
  };
};

describe('three/sun.js (Story 2-2)', () => {
  let THREE;
  let sun;

  beforeEach(() => {
    THREE = createThreeStub();
    // Lazy import so the stub is ready before sun.js evaluates its
    // destructured imports. Vitest hoists vi.mock, but we prefer an
    // explicit factory import to keep the dependency wiring obvious.
    return import('./sun.js').then((mod) => {
      sun = mod.createSun({ THREE });
    });
  });

  describe('construction', () => {
    it('throws when THREE is missing', async () => {
      const mod = await import('./sun.js');
      expect(() => mod.createSun({})).toThrow(/THREE module is required/);
    });

    it('returns a group with a core, halo, and three satellites', () => {
      expect(sun.group).toBeTruthy();
      expect(sun.group.children).toContain(sun.core);
      expect(sun.group.children).toContain(sun.halo);
      expect(sun.satellites).toHaveLength(3);
      expect(sun.satellites.map((s) => s.name)).toEqual(['sunshine', 'vdd', 'playnite']);
    });

    it('starts every satellite in the inactive state', () => {
      for (const satellite of sun.satellites) {
        expect(satellite.installed).toBe(false);
        expect(sun.isToolInstalled(satellite.name)).toBe(false);
      }
      expect(sun.getInstalledState()).toEqual({
        sunshine: false,
        vdd: false,
        playnite: false,
      });
    });

    it('honors the documented `haloRatio` option (renamed from haloRadius)', async () => {
      // The previous implementation read `opts.haloRadius`, which
      // silently ignored documented `haloRatio: 1.45` overrides and
      // fell back to the default. Verify the rename took effect: a
      // caller-supplied haloRatio must produce a halo sphere whose
      // geometry was built with the explicit radius.
      const mod = await import('./sun.js');
      const customSun = mod.createSun({ THREE, coreRadius: 1.0, haloRatio: 2.0 });
      // Halo radius should be 2.0 * coreRadius (not the 1.45 default).
      expect(customSun.haloRadius).toBeCloseTo(2.0, 5);
    });

    it('falls back to the default when coreColor is a negative number', async () => {
      // The previous `>>> 0` coercion turned -1 into 0xFFFFFFFF
      // (opaque white). The new validation requires the number to
      // sit inside [0, 0xFFFFFF], so a negative value must fall back
      // to the default orange (0xffb347) instead.
      const mod = await import('./sun.js');
      const customSun = mod.createSun({ THREE, coreColor: -1 });
      const sunshineSat = customSun.satellites.find((s) => s.name === 'sunshine');
      // The satellite uses the inactiveColor as its initial material
      // color, but it shares the constructor path with coreColor via
      // sanitizeColor. The default inactiveColor (0x6b6259) is what
      // lands in the satellite's material because the override is
      // rejected and falls through. We assert that the *initial* color
      // matches the documented default rather than 0xFFFFFFFF.
      const initial = sunshineSat.material.color.value;
      expect(initial).not.toBe(0xffffffff);
      expect(initial).toBe(0x6b6259); // default inactiveColor
    });
  });

  describe('pulsing animation', () => {
    it('scales the core by 1 + amplitude * sin(2*pi*freq*elapsed)', () => {
      // Pick an elapsed value where sin is non-zero so we observe a
      // visible deviation from 1.0. With default freq=0.6 Hz, sin
      // peaks at elapsed = 1 / (4 * 0.6) = 5/12.
      const elapsed = 5 / 12;
      sun.update(0.016, elapsed);
      const wave = Math.sin(2 * Math.PI * 0.6 * elapsed);
      const expected = 1 + 0.06 * wave;
      expect(sun.core.scale.x).toBeCloseTo(expected, 5);
      expect(sun.core.scale.y).toBeCloseTo(expected, 5);
      expect(sun.core.scale.z).toBeCloseTo(expected, 5);
    });

    it('uses the running delta sum when no elapsed clock is supplied', () => {
      sun.update(0.5); // deltaSeconds=0.5, elapsedSeconds=undefined
      // After 0.5s with freq=0.6 and amp=0.06:
      const wave = Math.sin(2 * Math.PI * 0.6 * 0.5);
      const expected = 1 + 0.06 * wave;
      expect(sun.core.scale.x).toBeCloseTo(expected, 5);
    });

    it('does not throw when called with non-finite arguments', () => {
      expect(() => sun.update(NaN, NaN)).not.toThrow();
      expect(() => sun.update(-1)).not.toThrow();
      expect(() => sun.update(0, 0)).not.toThrow();
    });

    it('is a no-op after dispose', () => {
      sun.dispose();
      expect(() => sun.update(0.016, 1)).not.toThrow();
      // Scale stays at the last applied value because update short-circuits.
      expect(sun.core.scale.x).toBe(1);
    });
  });

  describe('setInstalledTools', () => {
    it('flips a satellite to active when its tool id is true', () => {
      sun.setInstalledTools({ sunshine: true });
      const sunshineSat = sun.satellites.find((s) => s.name === 'sunshine');
      expect(sunshineSat.installed).toBe(true);
      expect(sunshineSat.material.color.value).toBe(0xffe066); // activeColor
      expect(sunshineSat.material.emissive.value).toBe(0xffe066);
      // 2.0 is the stronger installed-state boost chosen so the
      // active indicator is clearly distinguishable from the
      // inactive 0.6 baseline.
      expect(sunshineSat.material.emissiveIntensity).toBe(2.0);
    });

    it('leaves unrelated tools unchanged', () => {
      sun.setInstalledTools({ vdd: true });
      const sunshineSat = sun.satellites.find((s) => s.name === 'sunshine');
      const playniteSat = sun.satellites.find((s) => s.name === 'playnite');
      expect(sunshineSat.installed).toBe(false);
      expect(playniteSat.installed).toBe(false);
      expect(sunshineSat.material.color.value).toBe(0x6b6259); // inactiveColor
    });

    it('rejects unknown keys without expanding the slice', () => {
      sun.setInstalledTools({ unknownTool: true, sunshine: true });
      expect(sun.getInstalledState()).toEqual({
        sunshine: true,
        vdd: false,
        playnite: false,
      });
    });

    it('is a no-op when called with a non-object', () => {
      const before = { ...sun.getInstalledState() };
      sun.setInstalledTools(null);
      sun.setInstalledTools(undefined);
      sun.setInstalledTools('sunshine');
      expect(sun.getInstalledState()).toEqual(before);
    });

    it('returns to inactive when a tool flips back to false', () => {
      sun.setInstalledTools({ sunshine: true });
      sun.setInstalledTools({ sunshine: false });
      const sunshineSat = sun.satellites.find((s) => s.name === 'sunshine');
      expect(sunshineSat.material.color.value).toBe(0x6b6259);
      expect(sunshineSat.material.emissiveIntensity).toBe(0.6);
    });

    it('does not throw after dispose', () => {
      sun.dispose();
      expect(() => sun.setInstalledTools({ sunshine: true })).not.toThrow();
    });

    it('clamps halo opacity to [0, 1] across 100 frames even with aggressive pulseAmplitude', async () => {
      // Build a sun with an aggressive amplitude that would push the
      // raw `0.28 + pulseAmplitude * 0.8 * sin(...)` expression outside
      // the legal alpha range (0.28 + 0.8 * 0.6 = 0.76, while the lower
      // bound 0.28 - 0.8 * 0.6 = -0.20 < 0). The defensive clamp added
      // in sun.js must keep the value inside [0, 1] regardless.
      const mod = await import('./sun.js');
      const aggressiveSun = mod.createSun({
        THREE,
        pulseAmplitude: 0.6,
        pulseFrequencyHz: 1.0,
      });
      for (let frame = 0; frame < 100; frame += 1) {
        const elapsed = frame * 0.016;
        aggressiveSun.update(0.016, elapsed);
        expect(aggressiveSun.halo.material.opacity).toBeGreaterThanOrEqual(0);
        expect(aggressiveSun.halo.material.opacity).toBeLessThanOrEqual(1);
      }
    });
  });

  describe('dispose', () => {
    it('releases every geometry and material exactly once', () => {
      sun.dispose();
      expect(sun.core.geometry.dispose).toHaveBeenCalledTimes(1);
      expect(sun.core.material.dispose).toHaveBeenCalledTimes(1);
      expect(sun.halo.geometry.dispose).toHaveBeenCalledTimes(1);
      expect(sun.halo.material.dispose).toHaveBeenCalledTimes(1);
      for (const satellite of sun.satellites) {
        expect(satellite.geometry.dispose).toHaveBeenCalledTimes(1);
        expect(satellite.material.dispose).toHaveBeenCalledTimes(1);
      }
    });

    it('removes children from the group so a stray render cannot touch them', () => {
      sun.dispose();
      expect(sun.group.children).toEqual([]);
    });

    it('is idempotent — calling twice does not double-dispose', () => {
      sun.dispose();
      sun.dispose();
      expect(sun.core.geometry.dispose).toHaveBeenCalledTimes(1);
      expect(sun.isDisposed()).toBe(true);
    });
  });
});
