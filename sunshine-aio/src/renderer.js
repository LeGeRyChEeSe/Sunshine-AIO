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
 */

import './styles.css';
import * as THREE from 'three';
import { createScene } from './three/setup.js';
import { createSun, CORE_TOOLS } from './three/sun.js';
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

  sceneController.start();

  const store = useAppStore;
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
  // lands on the right screen instead of waiting for the first user
  // interaction. We must wait for the persist middleware to rehydrate
  // before reading navigationState.currentView, otherwise the snapshot
  // above reflects the in-memory defaults (always SOLAR_SYSTEM) and we
  // would clobber a saved view like SETTINGS or PLANET_DETAIL on every
  // relaunch. We only force SOLAR_SYSTEM when the persisted view is
  // missing or unrecognised — never when the user has explicitly chosen
  // another view.
  const persistApi = store.persist;
  const pinInitialView = () => {
    const persistedView = store.getState().navigationState.currentView;
    if (!Object.values(APP_VIEW).includes(persistedView)) {
      store.getState().setCurrentView(APP_VIEW.SOLAR_SYSTEM);
    }
  };
  if (persistApi && typeof persistApi.onFinishHydration === 'function') {
    persistApi.onFinishHydration(pinInitialView);
    if (typeof persistApi.hasHydrated === 'function' && persistApi.hasHydrated()) {
      pinInitialView();
    }
  } else {
    // No persist API exposed (shouldn't happen for our store, but be
    // defensive): fall back to the old behavior.
    pinInitialView();
  }
  // Safety net for the sync-hydration case: zustand's `persist` middleware
  // only invokes `onFinishHydration` listeners on the hydrating -> hydrated
  // transition. For a singleton store whose storage is already a sync API
  // (the createJSONStorage(() => createMemoryStorage()) path used in tests
  // and the defaultStorage() path here), hydration may complete synchronously
  // before the registration above runs — in which case the listener never
  // fires. Also, if hydration is in flight when this code runs, the early
  // `setCurrentView` would be overwritten once hydration lands. An
  // unconditional `pinInitialView()` call is harmless for the in-progress
  // case (it reads the post-hydration value once hydration settles, and the
  // default `currentView` is SOLAR_SYSTEM so it is a no-op for the happy
  // path) and it guarantees the synchronous case still pins correctly.
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
