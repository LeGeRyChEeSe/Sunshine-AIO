/**
 * Tests for src/state/persistence.js (Story 2-4).
 *
 * Coverage:
 *   - Save / load round-trip for the three persisted slices.
 *   - `regenerateWorld()` rolls a new seed and stamps
 *     `lastRegeneratedAt` without touching `installedApps`.
 *   - Corruption recovery: a store that throws on read falls back to
 *     defaults, a partially-written payload is sanitized into the
 *     documented shape.
 *   - Integration with the Zustand store: the `worldConfig` slice
 *     hydrates from disk on boot and mutations are mirrored back
 *     through the throttled save middleware.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { createJSONStorage } from 'zustand/middleware';
import {
  createPersistence,
  createMemoryStore,
  DEFAULT_WORLD_CONFIG,
  PERSIST_NAMESPACE,
} from './persistence.js';
import { createAppStore, createMemoryStorage } from './store.js';

const jsonMemoryStorage = () => createJSONStorage(() => createMemoryStorage());

/**
 * Build a fresh persistence adapter backed by an in-memory shim so
 * the suite never touches `electron-store` (which requires the
 * Electron runtime). The shim mirrors the `conf` surface enough to
 * exercise every code path.
 */
const buildMemoryPersistence = (overrides = {}) =>
  createPersistence({
    useMemory: true,
    now: overrides.now || (() => 1234567890),
    logger: overrides.logger || (() => {}),
  });

describe('state/persistence.js (Story 2-4)', () => {
  describe('save / load round-trip', () => {
    it('returns the documented defaults when the store is empty', () => {
      const p = buildMemoryPersistence();
      expect(p.getWorldConfig()).toEqual(DEFAULT_WORLD_CONFIG);
      expect(p.getInstalledApps()).toEqual([]);
      expect(p.getNavigationHistory()).toEqual([]);
    });

    it('persists and reads back the worldConfig slice', () => {
      const p = buildMemoryPersistence();
      p.setWorldConfig({ seed: 999, lastRegeneratedAt: 42, regenerated: true });
      expect(p.getWorldConfig()).toEqual({
        seed: 999,
        lastRegeneratedAt: 42,
        regenerated: true,
      });
    });

    it('persists and reads back the installedApps slice', () => {
      const p = buildMemoryPersistence();
      p.setInstalledApps([
        { id: 'sunshine', name: 'Sunshine', version: '0.20.0' },
        { id: 'vdd', name: 'Virtual Display Driver' },
      ]);
      const apps = p.getInstalledApps();
      expect(apps).toHaveLength(2);
      expect(apps[0]).toMatchObject({ id: 'sunshine', version: '0.20.0' });
      expect(apps[1]).toMatchObject({ id: 'vdd' });
    });

    it('persists and reads back the navigationHistory slice', () => {
      const p = buildMemoryPersistence();
      p.setNavigationHistory(['solar-system', 'planet-detail']);
      expect(p.getNavigationHistory()).toEqual(['solar-system', 'planet-detail']);
    });

    it('round-trips through a fresh persistence adapter (simulates reboot)', () => {
      const now = () => 7777;
      const p1 = buildMemoryPersistence({ now });
      p1.setWorldConfig({ seed: 123, lastRegeneratedAt: 555, regenerated: true });
      p1.setInstalledApps([{ id: 'sunshine' }]);
      p1.setNavigationHistory(['solar-system', 'app-detail']);
      // Read the raw shim so we can hydrate a second adapter with the
      // same bytes — emulates the renderer closing and reopening.
      const raw = p1.raw().raw();
      const p2 = createPersistence({
        store: createMemoryStore(raw),
        now,
        logger: () => {},
      });
      expect(p2.getWorldConfig()).toEqual({
        seed: 123,
        lastRegeneratedAt: 555,
        regenerated: true,
      });
      expect(p2.getInstalledApps().map((entry) => entry.id)).toEqual(['sunshine']);
      expect(p2.getNavigationHistory()).toEqual(['solar-system', 'app-detail']);
    });
  });

  describe('regenerateWorld', () => {
    it('picks a fresh seed and stamps lastRegeneratedAt', () => {
      const p = buildMemoryPersistence({ now: () => 1000 });
      const before = p.getWorldConfig().seed;
      const next = p.regenerateWorld();
      expect(next.seed).not.toBe(before);
      expect(next.lastRegeneratedAt).toBe(1000);
      expect(next.regenerated).toBe(true);
      expect(p.getWorldConfig()).toEqual(next);
    });

    it('accepts a forced seed for tests', () => {
      const p = buildMemoryPersistence();
      const next = p.regenerateWorld({ seed: 314 });
      expect(next.seed).toBe(314);
      expect(p.getWorldConfig().seed).toBe(314);
    });

    it('preserves installedApps across a regenerate', () => {
      const p = buildMemoryPersistence();
      p.setInstalledApps([
        { id: 'sunshine', name: 'Sunshine' },
        { id: 'playnite', name: 'Playnite' },
      ]);
      const beforeApps = p.getInstalledApps();
      p.regenerateWorld({ seed: 2024 });
      const afterApps = p.getInstalledApps();
      expect(afterApps).toEqual(beforeApps);
      // The worldConfig slice is the only one that changed.
      expect(p.getWorldConfig().seed).toBe(2024);
    });

    it('produces a different seed on two back-to-back calls', () => {
      const p = buildMemoryPersistence({ now: () => 0 });
      // Use the counter: two calls in the same millisecond with the
      // same timestamp still produce distinct seeds.
      const a = p.regenerateWorld();
      const b = p.regenerateWorld();
      expect(a.seed).not.toBe(b.seed);
    });

    it('coerces a non-finite forced seed to the default', () => {
      const p = buildMemoryPersistence();
      const next = p.regenerateWorld({ seed: Number.NaN });
      expect(Number.isFinite(next.seed)).toBe(true);
      expect(next.seed).toBeGreaterThanOrEqual(0);
    });
  });

  describe('corruption recovery', () => {
    it('falls back to defaults when the underlying store throws on read', () => {
      const broken = {
        get: () => {
          throw new Error('disk on fire');
        },
        set: () => {
          throw new Error('disk on fire');
        },
        delete: () => {},
        clear: () => {},
        raw: () => ({}),
      };
      const logger = vi.fn();
      const p = createPersistence({ store: broken, logger });
      expect(p.getWorldConfig()).toEqual(DEFAULT_WORLD_CONFIG);
      expect(p.getInstalledApps()).toEqual([]);
      expect(p.getNavigationHistory()).toEqual([]);
      // Logger was called at least once (one per slice we read).
      expect(logger).toHaveBeenCalled();
    });

    it('sanitizes a partially-written worldConfig blob', () => {
      const p = buildMemoryPersistence();
      // Directly seed a corrupted blob via the underlying shim. We
      // bypass the wrapper's setWorldConfig because that path would
      // sanitize the input itself.
      const shim = p.raw();
      shim.set('worldConfig', {
        seed: Number.NaN, // coerce to default
        lastRegeneratedAt: 'not-a-number', // coerce to null
        regenerated: 'yes', // coerce to false
        // extra keys are silently dropped:
        __forged__: { danger: true },
      });
      const sanitized = p.getWorldConfig();
      expect(sanitized.seed).toBe(DEFAULT_WORLD_CONFIG.seed);
      expect(sanitized.lastRegeneratedAt).toBeNull();
      expect(sanitized.regenerated).toBe(false);
      expect(sanitized).not.toHaveProperty('__forged__');
    });

    it('sanitizes a partially-written installedApps blob', () => {
      const p = buildMemoryPersistence();
      const shim = p.raw();
      shim.set('installedApps', [
        { id: 'sunshine' },
        { id: 42 }, // dropped: id is not a string
        null, // dropped: not an object
        { name: 'no-id' }, // dropped: no string id
        { id: 'sunshine', version: '0.2.0' }, // dropped: duplicate id
        { id: 'vdd' },
      ]);
      const apps = p.getInstalledApps();
      expect(apps.map((entry) => entry.id)).toEqual(['sunshine', 'vdd']);
    });

    it('sanitizes a navigation history blob to strings only', () => {
      const p = buildMemoryPersistence();
      const shim = p.raw();
      shim.set('navigationHistory', ['solar-system', null, 42, 'app-detail']);
      expect(p.getNavigationHistory()).toEqual(['solar-system', 'app-detail']);
    });

    it('clear() restores every slice to its documented default', () => {
      const p = buildMemoryPersistence();
      p.setWorldConfig({ seed: 999, lastRegeneratedAt: 1, regenerated: true });
      p.setInstalledApps([{ id: 'sunshine' }]);
      p.setNavigationHistory(['planet-detail']);
      p.clear();
      expect(p.getWorldConfig()).toEqual(DEFAULT_WORLD_CONFIG);
      expect(p.getInstalledApps()).toEqual([]);
      expect(p.getNavigationHistory()).toEqual([]);
    });
  });

  describe('Zustand store integration', () => {
    let persistence;
    let store;

    beforeEach(() => {
      persistence = buildMemoryPersistence();
      store = createAppStore({
        storage: jsonMemoryStorage(),
        persistence,
        throttleMs: 0, // immediate flush for the test environment
        logger: () => {},
      });
    });

    it('hydrates the worldConfig slice from the persistence adapter on boot', () => {
      persistence.setWorldConfig({ seed: 7, lastRegeneratedAt: 1, regenerated: true });
      const fresh = createAppStore({
        storage: jsonMemoryStorage(),
        persistence,
        throttleMs: 0,
        logger: () => {},
      });
      expect(fresh.getState().worldConfig.seed).toBe(7);
      expect(fresh.getState().worldConfig.regenerated).toBe(true);
    });

    it('mirrors store mutations back to disk through the throttle', async () => {
      store.getState().setSeed(2025);
      // The throttle is configured with throttleMs=0 — the trailing
      // call still runs through setTimeout, so we yield once.
      await new Promise((resolve) => setTimeout(resolve, 10));
      store.persistenceFlush?.();
      expect(persistence.getWorldConfig().seed).toBe(2025);
    });

    it('regenerateWorld preserves installedApps on both sides of the round trip', async () => {
      store.getState().addInstalledApp({ id: 'sunshine', name: 'Sunshine' });
      store.getState().addInstalledApp({ id: 'vdd', name: 'Virtual Display Driver' });
      await new Promise((resolve) => setTimeout(resolve, 10));
      store.persistenceFlush?.();
      expect(persistence.getInstalledApps().map((entry) => entry.id)).toEqual(['sunshine', 'vdd']);
      const beforeApps = persistence.getInstalledApps();
      store.getState().regenerateWorld({ seed: 9001 });
      await new Promise((resolve) => setTimeout(resolve, 10));
      store.persistenceFlush?.();
      const afterApps = persistence.getInstalledApps();
      expect(afterApps).toEqual(beforeApps);
      expect(persistence.getWorldConfig().seed).toBe(9001);
      expect(persistence.getWorldConfig().regenerated).toBe(true);
    });

    it('exposes a persistenceFlush hook on the store', () => {
      expect(typeof store.persistenceFlush).toBe('function');
      expect(() => store.persistenceFlush()).not.toThrow();
    });
  });

  describe('module exports', () => {
    it('exposes the documented PERSIST_NAMESPACE', () => {
      expect(PERSIST_NAMESPACE).toBe('sunshine-aio');
    });

    it('exposes the documented KEYS via the wrapper instance', () => {
      const p = buildMemoryPersistence();
      expect(p.KEYS).toEqual({
        WORLD_CONFIG: 'worldConfig',
        INSTALLED_APPS: 'installedApps',
        NAVIGATION_HISTORY: 'navigationHistory',
      });
    });
  });

  describe('memory shim', () => {
    it('createMemoryStore returns a working shim with defaults', () => {
      const shim = createMemoryStore();
      expect(shim.get('worldConfig', null)).toBeNull();
      shim.set('worldConfig', { seed: 1 });
      expect(shim.get('worldConfig', null)).toEqual({ seed: 1 });
      shim.delete('worldConfig');
      expect(shim.get('worldConfig', null)).toBeNull();
    });

    it('shim.clear() drops the documented keys', () => {
      const shim = createMemoryStore({
        worldConfig: { seed: 1 },
        installedApps: [{ id: 'a' }],
        navigationHistory: ['solar-system'],
      });
      shim.clear();
      expect(shim.get('worldConfig', 'gone')).toBe('gone');
      expect(shim.get('installedApps', 'gone')).toBe('gone');
      expect(shim.get('navigationHistory', 'gone')).toBe('gone');
    });
  });
});
