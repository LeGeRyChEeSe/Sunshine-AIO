/**
 * Renderer entry point.
 *
 * Story 2-1 wires the Three.js canvas into the existing Sunshine AIO
 * scaffold:
 *
 *   - creates a <canvas> element inside the #app container
 *   - boots the WebGL renderer via `createScene` from src/three/setup.js
 *   - subscribes to the FPS monitor and pushes values into the Zustand
 *     store (so the React-side overlay can render them)
 *   - exposes a small dev-only FPS overlay (no external deps) so the
 *     developer can verify the 30 FPS target without DevTools
 *   - tears everything down on `beforeunload` so closing the window
 *     releases the GL context and clears the resize listener
 *
 * Story 2-2 adds the Sun:
 *
 *   - imports `createSun` from src/three/sun.js
 *   - imports the real `three` module on the renderer side so we can
 *     build the sun mesh (the unit tests inject a stub via DI)
 *   - attaches the sun's root group to the scene via `scene.add`
 *   - wires the scene controller's `setSun(...)` so the per-frame
 *     updater runs inside the existing animation loop
 *   - subscribes to the Zustand store's `coreTools` slice and pushes
 *     it into the sun through `setInstalledTools`
 *
 * Story 2-3 adds the Planets:
 *
 *   - imports `createPlanetsForCategories` from src/three/planetFactory.js
 *   - builds one planet per category in the store's `categories` slice
 *   - calls `sceneController.setPlanets(factory)` so the factory's
 *     per-frame updater is registered with the loop and the root
 *     group is added to the scene
 *   - subscribes to the `categories` slice and pushes the installed
 *     flag for each entry into the scene via `setPlanetInstalled`
 */

import './styles.css';
import * as THREE from 'three';
import { createScene } from './three/setup.js';
import { createSun, CORE_TOOLS } from './three/sun.js';
import { createPlanetsForCategories } from './three/planetFactory.js';
import { useAppStore, APP_VIEW } from './state/store.js';

const appRoot = document.getElementById('app');
if (!appRoot) {
  // Surface early: if #app is missing the rest of the wiring is moot.
  throw new Error('[Renderer] Missing #app root element');
}

// Replace the story 1-1 placeholder content with a canvas host.
appRoot.innerHTML = '';

const canvasHost = document.createElement('div');
canvasHost.id = 'scene-host';
canvasHost.style.position = 'relative';
canvasHost.style.width = '100%';
canvasHost.style.height = '100vh';
canvasHost.style.minHeight = '480px';
appRoot.appendChild(canvasHost);

const canvas = document.createElement('canvas');
canvas.id = 'three-canvas';
canvas.style.display = 'block';
canvas.style.width = '100%';
canvas.style.height = '100%';
canvasHost.appendChild(canvas);

const fpsOverlay = document.createElement('div');
fpsOverlay.id = 'fps-overlay';
fpsOverlay.setAttribute('aria-live', 'polite');
fpsOverlay.textContent = 'FPS: --';
canvasHost.appendChild(fpsOverlay);

// Console-backed logger. The Story 1-2 logger module lives in the main
// process; the renderer process just gets a thin shim that prints to
// the Chromium devtools console (also picked up by electron-forge's
// terminal output during dev).
const logger = (message, meta) => {
  if (meta) {
    console.info(message, meta);
  } else {
    console.info(message);
  }
};

let sceneController = null;

try {
  sceneController = createScene({
    canvas,
    logger,
  });

  // Story 2-2: build the sun, attach it to the scene, and hand it to
  // the controller so the animation loop drives its `update(...)`.
  // The sun is owned by the controller: dispose() will release its
  // geometries/materials when the window closes.
  const sun = createSun({ THREE, logger });
  sceneController.scene.add(sun.group);
  sceneController.setSun(sun);

  // Story 2-3: build the planet factory from the store's categories
  // slice, attach it to the scene controller, and subscribe to slice
  // changes so the installed flag for each category is pushed into
  // the 3D scene through `setPlanetInstalled`. The factory is owned
  // by the controller: dispose() will release its geometries and
  // detach the root group when the window closes.
  const store = useAppStore;
  const planetsFactory = createPlanetsForCategories({
    THREE,
    categories: store.getState().categories,
    logger,
  });
  sceneController.setPlanets(planetsFactory);

  sceneController.start();

  store.getState().markSceneInitialized(true);

  // Push the initial core-tools state into the sun. Subscribing via
  // `subscribe` keeps the indicator colors in lockstep with the store
  // after every action — no manual sync required when an installer
  // finishes in story 3-x. We pass a selector so the subscription
  // fires only when `coreTools` actually changes; without it, every
  // store mutation (FPS ticks, navigation transitions, etc.) would
  // call into `setInstalledTools` and re-validate the slice for no
  // reason. The store is built with `subscribeWithSelector` so the
  // 2-arg form of `subscribe(selector, listener)` is supported.
  const pushCoreTools = (coreTools) => {
    sceneController.setInstalledTools(coreTools);
  };
  pushCoreTools(store.getState().coreTools);
  store.subscribe((state) => state.coreTools, pushCoreTools);

  // Push the initial categories state into the planet factory. The
  // factory's `setInstalled(id, flag)` is the only planet-side state
  // channel — orbital layout / colour come from the factory build
  // (which already happens above with `createPlanetsForCategories`).
  // We subscribe to the categories slice so a future action that flips
  // a category's installed flag is reflected on the planet within a
  // single tick. The selector-driven subscribe avoids waking the
  // listener for unrelated store mutations.
  const pushCategories = (categories) => {
    if (!Array.isArray(categories)) {
      return;
    }
    for (const entry of categories) {
      if (!entry || typeof entry.id !== 'string') {
        continue;
      }
      sceneController.setPlanetInstalled(entry.id, Boolean(entry.installed));
    }
  };
  pushCategories(store.getState().categories);
  store.subscribe((state) => state.categories, pushCategories);

  // Wire the FPS monitor's onFpsUpdate sink so the store and the
  // on-screen overlay both read from the same source of truth — the
  // rolling-average FPS computed inside the scene controller. The
  // monitor flushes every ~2s, which is a comfortable cadence for the
  // React subscribers and keeps the overlay value stable.
  sceneController.setFpsSink?.((fps) => {
    store.getState().setFps(fps);
    fpsOverlay.textContent = `FPS: ${fps.toFixed(1)}`;
  });

  // Pin the initial view to the solar system so a brand-new install
  // lands on the right screen. Defers to the post-hydration callback
  // when the persist API exposes it (so a saved SETTINGS view is not
  // clobbered), and runs synchronously as a safety net for the
  // already-hydrated case — setCurrentView is a no-op on the same
  // view, so the second invocation is harmless. A flag guards the
  // listener so rehydration does not re-fire it.
  const persistApi = store.persist;
  let pinApplied = false;
  const pinInitialView = () => {
    if (pinApplied) {
      return;
    }
    pinApplied = true;
    const persistedView = store.getState().navigationState.currentView;
    if (!Object.values(APP_VIEW).includes(persistedView)) {
      store.getState().setCurrentView(APP_VIEW.SOLAR_SYSTEM);
    }
  };
  if (persistApi && typeof persistApi.onFinishHydration === 'function') {
    persistApi.onFinishHydration(pinInitialView);
  }
  pinInitialView();

  // Reference CORE_TOOLS to keep the import live (and silence the
  // no-unused-vars warning in case the linter is strict about
  // module-scope constants that aren't read locally).
  void CORE_TOOLS;

  logger('[Renderer] Sunshine AIO renderer online (Story 2-2)');
} catch (err) {
  logger('[Renderer] Failed to bootstrap Three.js scene', err);
  if (sceneController) {
    sceneController.dispose();
    sceneController = null;
  }
  // Re-throw so the Chromium devtools console shows the stack; the
  // main process fatal-log handler (Story 1-1) will also catch this.
  throw err;
}

// Cleanly dispose the GL context and any listeners when the window
// is closed. Without this, the WebGLRenderer leaks GPU memory on
// hot reload.
window.addEventListener('beforeunload', () => {
  if (sceneController) {
    sceneController.dispose();
    sceneController = null;
  }
});
