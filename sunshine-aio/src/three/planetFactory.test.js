/**
 * Tests for src/three/planetFactory.js (Story 2-3).
 *
 * The factory orchestrates one planet per category, plus optional
 * orbit lines, and exposes a single `update` and `setInstalled`
 * surface. The tests run in pure Node with the shared THREE stub.
 *
 * Test focus:
 *   - Construction builds one planet per valid category and skips
 *     entries missing the required `id`.
 *   - `setInstalled(id, flag)` flips the planet's installed state and
 *     is reflected by `getInstalledMap()`.
 *   - `update(delta, elapsed)` advances every planet.
 *   - `dispose()` releases every planet + orbit resources exactly
 *     once and turns subsequent calls into no-ops.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { createThreeStub } from './__fixtures__/threeStub.js';

const buildThreeStub = () => createThreeStub({ vi });

describe('three/planetFactory.js (Story 2-3)', () => {
  let THREE;
  let factory;
  let categories;

  beforeEach(() => {
    THREE = buildThreeStub();
    categories = [
      { id: 'games', name: 'Games', color: 0x4fc3f7 },
      { id: 'streaming', name: 'Streaming', color: 0x81c784 },
      { id: 'utilities', name: 'Utilities', color: 0xffb74d },
    ];
    return import('./planetFactory.js').then((mod) => {
      factory = mod.createPlanetsForCategories({ THREE, categories });
    });
  });

  describe('construction', () => {
    it('throws when THREE is missing', async () => {
      const mod = await import('./planetFactory.js');
      expect(() => mod.createPlanetsForCategories({ categories: [{ id: 'x' }] })).toThrow(
        /THREE module is required/
      );
    });

    it('throws when categories is not an array', async () => {
      const mod = await import('./planetFactory.js');
      expect(() => mod.createPlanetsForCategories({ THREE, categories: 'nope' })).toThrow(
        /must be an array/
      );
    });

    it('builds one planet per valid category', () => {
      expect(factory.planets).toHaveLength(3);
      expect(factory.planets.map((p) => p.id)).toEqual(['games', 'streaming', 'utilities']);
    });

    it('skips entries missing an id and surfaces them via `skipped`', () => {
      return import('./planetFactory.js').then((mod) => {
        const f = mod.createPlanetsForCategories({
          THREE,
          categories: [{ id: 'games' }, { name: 'no-id' }, null, { id: 'utilities' }],
        });
        expect(f.planets).toHaveLength(2);
        expect(f.planets.map((p) => p.id)).toEqual(['games', 'utilities']);
        expect(f.skipped.length).toBe(2);
      });
    });

    it('assigns deterministic orbit slots so layout is stable', () => {
      return import('./planetFactory.js').then((mod) => {
        const f1 = mod.createPlanetsForCategories({ THREE, categories });
        const f2 = mod.createPlanetsForCategories({ THREE, categories });
        for (let i = 0; i < f1.planets.length; i += 1) {
          expect(f1.planets[i].orbitRadius).toBe(f2.planets[i].orbitRadius);
          expect(f1.planets[i].phase).toBe(f2.planets[i].phase);
        }
      });
    });

    it('honors per-category orbitRadius and phase overrides', () => {
      return import('./planetFactory.js').then((mod) => {
        const f = mod.createPlanetsForCategories({
          THREE,
          categories: [{ id: 'games', orbitRadius: 7.5, phase: 1.23 }, { id: 'streaming' }],
        });
        expect(f.planets[0].orbitRadius).toBe(7.5);
        expect(f.planets[0].phase).toBe(1.23);
      });
    });

    it('creates orbit lines by default and can be turned off', () => {
      return import('./planetFactory.js').then((mod) => {
        const withOrbits = mod.createPlanetsForCategories({ THREE, categories });
        expect(withOrbits.orbits).toBeTruthy();
        expect(withOrbits.orbits.lines).toHaveLength(3);

        const noOrbits = mod.createPlanetsForCategories({
          THREE,
          categories,
          withOrbits: false,
        });
        expect(noOrbits.orbits).toBeNull();
      });
    });

    it('applies the installed flag from the category descriptor', () => {
      return import('./planetFactory.js').then((mod) => {
        const f = mod.createPlanetsForCategories({
          THREE,
          categories: [{ id: 'games', installed: true }, { id: 'streaming' }],
        });
        expect(f.planets[0].installed).toBe(true);
        expect(f.planets[0].instance.isInstalled()).toBe(true);
        expect(f.planets[1].installed).toBe(false);
      });
    });
  });

  describe('update', () => {
    it('advances every planet', () => {
      // Capture initial mesh rotations and pivot positions.
      const before = factory.planets.map((p) => ({
        y: p.instance.mesh.rotation.y,
        x: p.instance.pivot.position.x,
      }));
      factory.update(0.5, 1.0);
      factory.planets.forEach((descriptor, idx) => {
        expect(descriptor.instance.mesh.rotation.y).not.toBe(before[idx].y);
        expect(descriptor.instance.pivot.position.x).not.toBeCloseTo(before[idx].x, 5);
      });
    });

    it('does not throw on non-finite arguments', () => {
      expect(() => factory.update(NaN, NaN)).not.toThrow();
      expect(() => factory.update(0, 0)).not.toThrow();
    });

    it('is a no-op after dispose', () => {
      factory.dispose();
      expect(() => factory.update(0.016, 1)).not.toThrow();
    });
  });

  describe('setInstalled', () => {
    it('flips a planet and reflects in getInstalledMap()', () => {
      expect(factory.getInstalledMap()).toEqual({
        games: false,
        streaming: false,
        utilities: false,
      });
      factory.setInstalled('games', true);
      expect(factory.getInstalledMap().games).toBe(true);
      expect(factory.planets[0].instance.isInstalled()).toBe(true);
    });

    it('is a no-op when the value is unchanged', () => {
      const before = factory.planets[0].instance.mesh.material.color.value;
      factory.setInstalled('games', false);
      expect(factory.planets[0].instance.mesh.material.color.value).toBe(before);
    });

    it('returns false for unknown ids and does not throw', () => {
      expect(factory.setInstalled('unknown', true)).toBe(false);
      // Map is still well-formed.
      expect(Object.keys(factory.getInstalledMap()).sort()).toEqual(
        ['games', 'streaming', 'utilities'].sort()
      );
    });

    it('does not throw after dispose', () => {
      factory.dispose();
      expect(() => factory.setInstalled('games', true)).not.toThrow();
    });
  });

  describe('dispose', () => {
    it('releases every planet and the orbits exactly once', () => {
      factory.dispose();
      for (const descriptor of factory.planets) {
        expect(descriptor.instance.mesh.geometry.dispose).toHaveBeenCalledTimes(1);
        expect(descriptor.instance.mesh.material.dispose).toHaveBeenCalledTimes(1);
      }
      for (const entry of factory.orbits.lines) {
        expect(entry.geometry.dispose).toHaveBeenCalledTimes(1);
        expect(entry.material.dispose).toHaveBeenCalledTimes(1);
      }
    });

    it('is idempotent', () => {
      factory.dispose();
      factory.dispose();
      expect(factory.isDisposed()).toBe(true);
      // Geometry dispose still called exactly once.
      expect(factory.planets[0].instance.mesh.geometry.dispose).toHaveBeenCalledTimes(1);
    });

    it('removes children from the root group', () => {
      factory.dispose();
      expect(factory.group.children).toEqual([]);
    });
  });
});

describe('three/planetFactory.js — computeSlot', () => {
  it('returns the override values when supplied', async () => {
    const mod = await import('./planetFactory.js');
    const slot = mod.computeSlot(2, 5, {
      orbitRadius: 9,
      phase: 1.5,
      spinSpeed: 0.3,
      revolutionSpeed: 0.2,
    });
    expect(slot).toEqual({
      orbitRadius: 9,
      phase: 1.5,
      spinSpeed: 0.3,
      revolutionSpeed: 0.2,
    });
  });

  it('derives a deterministic slot from the index when no overrides are given', async () => {
    const mod = await import('./planetFactory.js');
    const a = mod.computeSlot(1, 5);
    const b = mod.computeSlot(1, 5);
    expect(a).toEqual(b);
    expect(a.orbitRadius).toBeGreaterThan(0);
    expect(a.phase).toBeGreaterThanOrEqual(0);
    expect(a.phase).toBeLessThan(Math.PI * 2);
  });
});
