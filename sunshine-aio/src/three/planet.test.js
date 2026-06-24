/**
 * Tests for src/three/planet.js (Story 2-3).
 *
 * The planet component imports Three.js geometry/material classes but
 * the WebGL renderer is never instantiated — these tests run in pure
 * Node (vitest default `environment: 'node'`) and use a lightweight
 * `THREE` stub via the shared fixture.
 *
 * Test focus (mirrors the contract documented in planet.js):
 *   - Construction: a group + sphere mesh + pivot, with a stable
 *     procedural noise seed derived from the category id.
 *   - `update(delta, elapsed)` advances the orbital position via
 *     `cos/sin(phase + elapsed * revolutionSpeed)` and rotates the
 *     mesh around its own axis.
 *   - `setInstalled(boolean)` flips the material color and emissive
 *     intensity between the "installed" and "uninstalled" palettes.
 *   - `dispose()` releases every geometry/material exactly once and
 *     turns subsequent calls into no-ops.
 *   - Updates after dispose are silently ignored (no throws).
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { createThreeStub } from './__fixtures__/threeStub.js';

const buildThreeStub = () => createThreeStub({ vi });

describe('three/planet.js (Story 2-3)', () => {
  let THREE;
  let planet;

  beforeEach(() => {
    THREE = buildThreeStub();
    return import('./planet.js').then((mod) => {
      planet = mod.createPlanet({
        THREE,
        category: { id: 'games', name: 'Games', color: 0x4fc3f7 },
      });
    });
  });

  describe('construction', () => {
    it('throws when THREE is missing', async () => {
      const mod = await import('./planet.js');
      expect(() => mod.createPlanet({ category: { id: 'x' } })).toThrow(/THREE module is required/);
    });

    it('throws when category is missing the id', async () => {
      const mod = await import('./planet.js');
      expect(() => mod.createPlanet({ THREE })).toThrow(/string `id` is required/);
    });

    it('creates a group, mesh, and pivot on the requested orbital slot', () => {
      expect(planet.group).toBeTruthy();
      expect(planet.mesh).toBeTruthy();
      expect(planet.pivot).toBeTruthy();
      // The pivot sits on its orbital slot from the first frame so
      // callers don't see a "everything at the origin" pop-in.
      const radius = planet.orbitRadius;
      expect(planet.pivot.position.x).toBeCloseTo(radius, 5);
      expect(planet.pivot.position.z).toBe(0);
    });

    it('starts in the uninstalled state with the gray default color', () => {
      expect(planet.isInstalled()).toBe(false);
      // Default uninstalledColor is 0x4a4a4a.
      expect(planet.mesh.material.color.value).toBe(0x4a4a4a);
      expect(planet.mesh.material.emissive.value).toBe(0x4a4a4a);
      expect(planet.mesh.material.emissiveIntensity).toBe(0.25);
    });

    it('exposes a stable procedural seed derived from the category id', () => {
      // Two planets built with the same id must get the same seed —
      // this is what makes a persisted layout round-trip without
      // shimmering textures on reload.
      return import('./planet.js').then((mod) => {
        const a = mod.createPlanet({ THREE, category: { id: 'games' } });
        const b = mod.createPlanet({ THREE, category: { id: 'games' } });
        expect(a.getSeed()).toBe(b.getSeed());
        const c = mod.createPlanet({ THREE, category: { id: 'utilities' } });
        expect(c.getSeed()).not.toBe(a.getSeed());
      });
    });
  });

  describe('animation', () => {
    it('advances the pivot along the orbit as elapsed time grows', () => {
      const radius = planet.orbitRadius;
      const speed = planet.revolutionSpeed;
      const elapsed = 1.0;
      planet.update(0.016, elapsed);
      const expectedAngle = planet.phase + elapsed * speed;
      expect(planet.pivot.position.x).toBeCloseTo(Math.cos(expectedAngle) * radius, 5);
      expect(planet.pivot.position.z).toBeCloseTo(Math.sin(expectedAngle) * radius, 5);
    });

    it('rotates the mesh around its own Y axis', () => {
      planet.update(0.5, 1.0);
      expect(planet.mesh.rotation.y).toBeCloseTo(1.0 * planet.spinSpeed, 5);
    });

    it('uses the running delta sum when no elapsed clock is supplied', () => {
      planet.update(0.5);
      // After 0.5s the spin should be 0.5 * spinSpeed (default 0.5 -> 0.25).
      expect(planet.mesh.rotation.y).toBeCloseTo(0.5 * planet.spinSpeed, 5);
    });

    it('does not throw on non-finite arguments', () => {
      expect(() => planet.update(NaN, NaN)).not.toThrow();
      expect(() => planet.update(-1)).not.toThrow();
      expect(() => planet.update(0, 0)).not.toThrow();
    });

    it('is a no-op after dispose', () => {
      planet.dispose();
      expect(() => planet.update(0.016, 1)).not.toThrow();
      // Mesh rotation should not change after dispose.
      const before = planet.mesh.rotation.y;
      planet.update(0.5, 2.0);
      expect(planet.mesh.rotation.y).toBe(before);
    });
  });

  describe('setInstalled', () => {
    it('flips to the installed color when true', () => {
      planet.setInstalled(true);
      expect(planet.isInstalled()).toBe(true);
      // installedColor default 0x4fc3f7.
      expect(planet.mesh.material.color.value).toBe(0x4fc3f7);
      expect(planet.mesh.material.emissive.value).toBe(0x4fc3f7);
      expect(planet.mesh.material.emissiveIntensity).toBe(0.5);
    });

    it('returns to the uninstalled color when false', () => {
      planet.setInstalled(true);
      planet.setInstalled(false);
      expect(planet.isInstalled()).toBe(false);
      expect(planet.mesh.material.color.value).toBe(0x4a4a4a);
      expect(planet.mesh.material.emissiveIntensity).toBe(0.25);
    });

    it('is a no-op when the value is unchanged', () => {
      planet.setInstalled(true);
      const before = planet.mesh.material.color.value;
      // Same value: no transition, no allocation on the hot path.
      planet.setInstalled(true);
      expect(planet.mesh.material.color.value).toBe(before);
    });

    it('coerces non-boolean inputs', () => {
      planet.setInstalled('truthy');
      expect(planet.isInstalled()).toBe(true);
      planet.setInstalled(0);
      expect(planet.isInstalled()).toBe(false);
    });

    it('does not throw after dispose', () => {
      planet.dispose();
      expect(() => planet.setInstalled(true)).not.toThrow();
    });
  });

  describe('dispose', () => {
    it('releases geometry and material exactly once', () => {
      planet.dispose();
      expect(planet.mesh.geometry.dispose).toHaveBeenCalledTimes(1);
      expect(planet.mesh.material.dispose).toHaveBeenCalledTimes(1);
    });

    it('is idempotent', () => {
      planet.dispose();
      planet.dispose();
      expect(planet.mesh.geometry.dispose).toHaveBeenCalledTimes(1);
      expect(planet.isDisposed()).toBe(true);
    });
  });
});

describe('three/planet.js — generateProceduralNoise', () => {
  it('returns a deterministic RGBA buffer for a given seed', async () => {
    const mod = await import('./planet.js');
    const a = mod.generateProceduralNoise({ size: 8, seed: 42, baseColor: 0xff0000 });
    const b = mod.generateProceduralNoise({ size: 8, seed: 42, baseColor: 0xff0000 });
    expect(a.pixels).toEqual(b.pixels);
    expect(a.width).toBe(8);
    expect(a.height).toBe(8);
    expect(a.pixels.length).toBe(8 * 8 * 4);
  });

  it('produces different buffers for different seeds', async () => {
    const mod = await import('./planet.js');
    const a = mod.generateProceduralNoise({ size: 8, seed: 1, baseColor: 0xff0000 });
    const b = mod.generateProceduralNoise({ size: 8, seed: 2, baseColor: 0xff0000 });
    // Almost certain to differ in at least one byte.
    let diffs = 0;
    for (let i = 0; i < a.pixels.length; i += 1) {
      if (a.pixels[i] !== b.pixels[i]) diffs += 1;
    }
    expect(diffs).toBeGreaterThan(0);
  });

  it('clamps each channel to [0, 255]', async () => {
    const mod = await import('./planet.js');
    const out = mod.generateProceduralNoise({ size: 16, seed: 7, baseColor: 0xffffff });
    for (let i = 0; i < out.pixels.length; i += 1) {
      expect(out.pixels[i]).toBeGreaterThanOrEqual(0);
      expect(out.pixels[i]).toBeLessThanOrEqual(255);
    }
  });
});
