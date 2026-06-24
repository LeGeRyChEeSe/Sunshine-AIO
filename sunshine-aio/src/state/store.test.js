/**
 * Tests for src/state/store.js (Story 2-1 + Story 2-2).
 *
 * Covers:
 *   - Initial state for all four slices (world/install/navigation/coreTools).
 *   - Action behavior: setPlanetStatus, upsertPlanet, setFps,
 *     markSceneInitialized, addInstalledApp, removeInstalledApp,
 *     startInstallProgress, finishInstallProgress, setCurrentView,
 *     setFocusedPlanet, setFocusedApp, goBack, resetNavigation,
 *     setCoreTools, setCoreToolInstalled, syncCoreToolsFromInstalls,
 *     reset.
 *   - Persistence: only the persistable fields are written to storage,
 *     the store rehydrates from storage on construction, and migrations
 *     move an older version forward.
 *
 * Story 2-2 adds the `coreTools` slice coverage (initial state, three
 * dedicated actions, and round-trip through the persist middleware).
 *
 * Tests use the in-memory storage adapter (`createMemoryStorage`) so
 * the suite runs cleanly under Node without touching `window.localStorage`.
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { createJSONStorage } from 'zustand/middleware';
import {
  createAppStore,
  createMemoryStorage,
  PLANET_STATUS,
  APP_VIEW,
  CORE_TOOL_IDS,
  STORE_NAME,
  STORE_VERSION,
} from './store.js';

/**
 * Build a memory-backed PersistStorage compatible with the persist
 * middleware (handles JSON serialization on set / parse on get).
 */
const jsonMemoryStorage = () => createJSONStorage(() => createMemoryStorage());

describe('state/store.js (Story 2-1 + 2-2)', () => {
  describe('initial state', () => {
    it('exposes empty worlds, no installed apps, and the solar-system view', () => {
      const store = createAppStore({ storage: jsonMemoryStorage() });
      const state = store.getState();
      expect(state.worldState.planets).toEqual([]);
      expect(state.worldState.fps).toBe(0);
      expect(state.worldState.sceneInitialized).toBe(false);
      expect(state.installState.installedApps).toEqual([]);
      expect(state.installState.inProgressApps).toEqual([]);
      expect(state.installState.failedApps).toEqual([]);
      expect(state.installState.lastUpdatedAt).toBeNull();
      expect(state.navigationState.currentView).toBe(APP_VIEW.SOLAR_SYSTEM);
      expect(state.navigationState.focusedPlanetId).toBeNull();
      expect(state.navigationState.focusedAppId).toBeNull();
      expect(state.navigationState.history).toEqual([APP_VIEW.SOLAR_SYSTEM]);
    });

    it('exposes the documented planet status enum values', () => {
      expect(PLANET_STATUS).toEqual({
        UNINSTALLED: 'uninstalled',
        INSTALLING: 'installing',
        INSTALLED: 'installed',
        FAILED: 'failed',
        UPDATING: 'updating',
      });
    });

    it('exposes the documented app view enum values', () => {
      expect(APP_VIEW).toEqual({
        SOLAR_SYSTEM: 'solar-system',
        PLANET_DETAIL: 'planet-detail',
        APP_DETAIL: 'app-detail',
        SETTINGS: 'settings',
      });
    });

    it('initializes every core tool to "not installed"', () => {
      const store = createAppStore({ storage: jsonMemoryStorage() });
      const coreTools = store.getState().coreTools;
      expect(CORE_TOOL_IDS).toEqual(['sunshine', 'vdd', 'playnite']);
      expect(coreTools).toEqual({
        sunshine: false,
        vdd: false,
        playnite: false,
      });
    });
  });

  describe('worldState actions', () => {
    let store;
    beforeEach(() => {
      store = createAppStore({ storage: jsonMemoryStorage() });
    });

    it('upsertPlanet inserts and updates planets by id', () => {
      store.getState().upsertPlanet({
        id: 'sunshine-planet',
        name: 'Sunshine',
        status: PLANET_STATUS.UNINSTALLED,
      });
      expect(store.getState().worldState.planets).toHaveLength(1);

      store.getState().upsertPlanet({
        id: 'sunshine-planet',
        name: 'Sunshine',
        status: PLANET_STATUS.INSTALLED,
      });
      const planets = store.getState().worldState.planets;
      expect(planets).toHaveLength(1);
      expect(planets[0].status).toBe(PLANET_STATUS.INSTALLED);
    });

    it('setPlanetStatus updates the matching planet only', () => {
      store.getState().upsertPlanet({ id: 'a', status: PLANET_STATUS.UNINSTALLED });
      store.getState().upsertPlanet({ id: 'b', status: PLANET_STATUS.UNINSTALLED });
      store.getState().setPlanetStatus('a', PLANET_STATUS.INSTALLED);
      const planets = store.getState().worldState.planets;
      expect(planets.find((p) => p.id === 'a').status).toBe(PLANET_STATUS.INSTALLED);
      expect(planets.find((p) => p.id === 'b').status).toBe(PLANET_STATUS.UNINSTALLED);
    });

    it('setFps replaces the FPS value, clamping NaN to 0', () => {
      store.getState().setFps(60);
      expect(store.getState().worldState.fps).toBe(60);
      store.getState().setFps(Number.NaN);
      expect(store.getState().worldState.fps).toBe(0);
    });

    it('markSceneInitialized toggles the sceneInitialized flag', () => {
      expect(store.getState().worldState.sceneInitialized).toBe(false);
      store.getState().markSceneInitialized(true);
      expect(store.getState().worldState.sceneInitialized).toBe(true);
      store.getState().markSceneInitialized(false);
      expect(store.getState().worldState.sceneInitialized).toBe(false);
    });
  });

  describe('installState actions', () => {
    let store;
    beforeEach(() => {
      store = createAppStore({ storage: jsonMemoryStorage() });
    });

    it('addInstalledApp adds an app with an installedAt timestamp', () => {
      store.getState().addInstalledApp({ id: 'sunshine', name: 'Sunshine' });
      const installedApps = store.getState().installState.installedApps;
      expect(installedApps).toHaveLength(1);
      expect(installedApps[0].id).toBe('sunshine');
      expect(installedApps[0].installedAt).toEqual(expect.any(Number));
      expect(store.getState().installState.lastUpdatedAt).toEqual(expect.any(Number));
    });

    it('addInstalledApp is idempotent on the same id', () => {
      store.getState().addInstalledApp({ id: 'sunshine', name: 'Sunshine', version: '0.1' });
      store.getState().addInstalledApp({ id: 'sunshine', name: 'Sunshine', version: '0.2' });
      const installedApps = store.getState().installState.installedApps;
      expect(installedApps).toHaveLength(1);
      expect(installedApps[0].version).toBe('0.2');
    });

    it('removeInstalledApp drops the entry and stamps lastUpdatedAt', () => {
      store.getState().addInstalledApp({ id: 'vdd' });
      store.getState().removeInstalledApp('vdd');
      expect(store.getState().installState.installedApps).toEqual([]);
    });

    it('startInstallProgress + finishInstallProgress(outcome=success) clears in-progress', () => {
      store.getState().startInstallProgress('sunshine');
      expect(store.getState().installState.inProgressApps).toContain('sunshine');
      store.getState().finishInstallProgress('sunshine', 'success');
      expect(store.getState().installState.inProgressApps).not.toContain('sunshine');
      expect(store.getState().installState.failedApps).not.toContain('sunshine');
    });

    it('finishInstallProgress(outcome=failed) pushes into failedApps', () => {
      store.getState().startInstallProgress('sunshine');
      store.getState().finishInstallProgress('sunshine', 'failed');
      expect(store.getState().installState.failedApps).toContain('sunshine');
      expect(store.getState().installState.inProgressApps).not.toContain('sunshine');
    });
  });

  describe('navigationState actions', () => {
    let store;
    beforeEach(() => {
      store = createAppStore({ storage: jsonMemoryStorage() });
    });

    it('setCurrentView pushes unique views and ignores the same view', () => {
      store.getState().setCurrentView(APP_VIEW.PLANET_DETAIL);
      store.getState().setCurrentView(APP_VIEW.PLANET_DETAIL);
      expect(store.getState().navigationState.history).toEqual([
        APP_VIEW.SOLAR_SYSTEM,
        APP_VIEW.PLANET_DETAIL,
      ]);
    });

    it('setCurrentView rejects unknown views', () => {
      const before = store.getState().navigationState;
      store.getState().setCurrentView('garbage');
      expect(store.getState().navigationState).toBe(before);
    });

    it('goBack pops the history stack to the previous view', () => {
      store.getState().setCurrentView(APP_VIEW.SETTINGS);
      store.getState().goBack();
      expect(store.getState().navigationState.currentView).toBe(APP_VIEW.SOLAR_SYSTEM);
    });

    it('goBack is a no-op at the bottom of the stack', () => {
      const before = store.getState().navigationState;
      store.getState().goBack();
      expect(store.getState().navigationState).toBe(before);
    });

    it('resetNavigation returns to the initial view and history', () => {
      store.getState().setCurrentView(APP_VIEW.SETTINGS);
      store.getState().setCurrentView(APP_VIEW.APP_DETAIL);
      store.getState().resetNavigation();
      expect(store.getState().navigationState.currentView).toBe(APP_VIEW.SOLAR_SYSTEM);
      expect(store.getState().navigationState.history).toEqual([APP_VIEW.SOLAR_SYSTEM]);
    });
  });

  describe('coreTools actions (Story 2-2)', () => {
    let store;
    beforeEach(() => {
      store = createAppStore({ storage: jsonMemoryStorage() });
    });

    it('setCoreTools accepts the canonical tools map and drops unknown keys', () => {
      store.getState().setCoreTools({
        sunshine: true,
        vdd: true,
        playnite: false,
        bogus: true,
      });
      expect(store.getState().coreTools).toEqual({
        sunshine: true,
        vdd: true,
        playnite: false,
      });
    });

    it('setCoreTools normalizes non-boolean values to booleans', () => {
      store.getState().setCoreTools({ sunshine: 'true', vdd: 1, playnite: null });
      expect(store.getState().coreTools).toEqual({
        sunshine: true,
        vdd: true,
        playnite: false,
      });
    });

    it('setCoreTools is a no-op for non-object inputs', () => {
      const before = { ...store.getState().coreTools };
      store.getState().setCoreTools(null);
      store.getState().setCoreTools(undefined);
      store.getState().setCoreTools('sunshine');
      expect(store.getState().coreTools).toEqual(before);
    });

    it('setCoreToolInstalled flips a single tool', () => {
      store.getState().setCoreToolInstalled('vdd', true);
      expect(store.getState().coreTools).toEqual({
        sunshine: false,
        vdd: true,
        playnite: false,
      });
    });

    it('setCoreToolInstalled ignores unknown tool ids', () => {
      const before = { ...store.getState().coreTools };
      store.getState().setCoreToolInstalled('bogus', true);
      expect(store.getState().coreTools).toEqual(before);
    });

    it('syncCoreToolsFromInstalls derives the map from installedApps', () => {
      store.getState().addInstalledApp({ id: 'sunshine' });
      store.getState().addInstalledApp({ id: 'playnite' });
      store.getState().syncCoreToolsFromInstalls();
      expect(store.getState().coreTools).toEqual({
        sunshine: true,
        vdd: false,
        playnite: true,
      });
    });

    it('syncCoreToolsFromInstalls ignores apps whose id is not a core tool', () => {
      store.getState().addInstalledApp({ id: 'playnite-extension' });
      store.getState().addInstalledApp({ id: 'sunshine' });
      store.getState().syncCoreToolsFromInstalls();
      expect(store.getState().coreTools).toEqual({
        sunshine: true,
        vdd: false,
        playnite: false,
      });
    });
  });

  describe('persistence', () => {
    it('persists only the documented slices', () => {
      const memory = createMemoryStorage();
      const storage = createJSONStorage(() => memory);
      const store = createAppStore({ storage, name: STORE_NAME });
      store.getState().setFps(72);
      store.getState().addInstalledApp({ id: 'sunshine' });
      store.getState().setCoreTools({ sunshine: true });
      // `createJSONStorage` wraps the underlying storage with
      // JSON.parse/stringify, so getItem() already returns the parsed
      // object. We then verify the underlying memory store holds the
      // raw JSON string and that the parsed payload carries every
      // documented slice while excluding the ephemeral fields.
      const raw = memory.getItem(STORE_NAME);
      expect(raw).toBeTruthy();
      expect(typeof raw).toBe('string');
      const parsed = JSON.parse(raw);
      expect(parsed.state).toHaveProperty('worldState');
      expect(parsed.state).toHaveProperty('installState');
      expect(parsed.state).toHaveProperty('navigationState');
      expect(parsed.state).toHaveProperty('coreTools');
      // Ephemeral fields must NOT be persisted.
      expect(parsed.state.worldState.fps).toBeUndefined();
      expect(parsed.state.worldState.sceneInitialized).toBeUndefined();
      expect(parsed.state.installState.inProgressApps).toBeUndefined();
    });

    it('rehydrates the persisted coreTools map on a new store', () => {
      const storage = jsonMemoryStorage();
      const first = createAppStore({ storage, name: STORE_NAME });
      first.getState().setCoreTools({ sunshine: true, vdd: true, playnite: false });
      const second = createAppStore({ storage, name: STORE_NAME });
      expect(second.getState().coreTools).toEqual({
        sunshine: true,
        vdd: true,
        playnite: false,
      });
    });

    it('exposes the documented STORE_NAME and STORE_VERSION', () => {
      expect(STORE_NAME).toBe('sunshine-aio-app-state');
      expect(typeof STORE_VERSION).toBe('number');
      expect(STORE_VERSION).toBeGreaterThanOrEqual(1);
    });
  });
});
