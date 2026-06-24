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
 *
 * Story 2-4 adds persistence + world regeneration:
 *
 *   - wires `createPersistence` from src/state/persistence.js so the
 *     store hydrates from disk on boot and mirrors every mutation
 *     back through a throttled save middleware
 *   - rebuilds the planet factory whenever the worldConfig seed
 *     changes (a regenerate, a manual `setSeed`, or a rehydrate
 *     from disk)
 *   - exposes a "Regenerate World" affordance in the on-screen HUD
 *     that asks for confirmation before rolling a new seed
 */

import './styles.css';
import * as THREE from 'three';
import { createScene } from './three/setup.js';
import { createSun, CORE_TOOLS } from './three/sun.js';
import { createPlanetsForCategories } from './three/planetFactory.js';
import { useAppStore, APP_VIEW, attachPersistence } from './state/store.js';
import { createPersistence, PERSIST_NAMESPACE } from './state/persistence.js';

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

// Story 2-4: a "Regenerate World" affordance. The button rolls a
// fresh seed in the persistence layer and rebuilds the planet
// factory. A confirmation dialog gates the action because rolling a
// new seed visibly changes the layout — we want a deliberate click
// rather than an accidental one.
const regenButton = document.createElement('button');
regenButton.id = 'regenerate-world-button';
regenButton.type = 'button';
regenButton.setAttribute('aria-label', 'Regenerate World');
regenButton.textContent = 'Regenerate World';
regenButton.style.position = 'absolute';
regenButton.style.top = '12px';
regenButton.style.right = '12px';
regenButton.style.padding = '8px 14px';
regenButton.style.border = '1px solid rgba(255,255,255,0.25)';
regenButton.style.borderRadius = '6px';
regenButton.style.background = 'rgba(20, 20, 30, 0.65)';
regenButton.style.color = '#f0f0f0';
regenButton.style.fontFamily = 'system-ui, sans-serif';
regenButton.style.fontSize = '13px';
regenButton.style.cursor = 'pointer';
regenButton.style.zIndex = '5';
canvasHost.appendChild(regenButton);

const regenStatus = document.createElement('div');
regenStatus.id = 'regenerate-world-status';
regenStatus.setAttribute('aria-live', 'polite');
regenStatus.style.position = 'absolute';
regenStatus.style.top = '48px';
regenStatus.style.right = '12px';
regenStatus.style.padding = '4px 10px';
regenStatus.style.borderRadius = '4px';
regenStatus.style.background = 'rgba(20, 20, 30, 0.55)';
regenStatus.style.color = '#cdd9e5';
regenStatus.style.fontFamily = 'system-ui, sans-serif';
regenStatus.style.fontSize = '11px';
regenStatus.style.zIndex = '5';
regenStatus.style.pointerEvents = 'none';
canvasHost.appendChild(regenStatus);

let regenStatusTimer = null;
const showRegenStatus = (text) => {
  regenStatus.textContent = text;
  if (regenStatusTimer !== null) {
    clearTimeout(regenStatusTimer);
  }
  regenStatusTimer = setTimeout(() => {
    regenStatus.textContent = '';
    regenStatusTimer = null;
  }, 3000);
};

// Bound at runtime by the try block below. Declared up here so the
// early-wired regen button handler can reach it via closure without
// leaking the rebuild function onto the global `window` object
// (which would expose a force-rebuild entry point to any future
// renderer-side script injection).
let rebuildPlanetsRef = null;

/**
 * Ask the user to confirm a regenerate. Returns true when confirmed.
 * We use a small stack of fallbacks so the affordance keeps working
 * even when `window.confirm` is unavailable (e.g. in some test
 * harnesses or sandboxed Electron configurations):
 *
 *   1. window.confirm (browser built-in dialog).
 *   2. Inline DOM confirmation overlay (rendered in the canvas host).
 *
 * The DOM overlay is appended lazily on first use so the boot path
 * stays lean when the user never clicks the button.
 */
const confirmRegenerate = (installedCount) => {
  const message =
    installedCount > 0
      ? `Regenerate the world? ${installedCount} installed app${
          installedCount === 1 ? '' : 's'
        } will be preserved.`
      : 'Regenerate the world?';
  if (typeof window !== 'undefined' && typeof window.confirm === 'function') {
    return window.confirm(message);
  }
  return new Promise((resolve) => {
    const overlay = document.createElement('div');
    overlay.style.position = 'absolute';
    overlay.style.inset = '0';
    overlay.style.display = 'flex';
    overlay.style.alignItems = 'center';
    overlay.style.justifyContent = 'center';
    overlay.style.background = 'rgba(0, 0, 0, 0.55)';
    overlay.style.zIndex = '10';
    const panel = document.createElement('div');
    panel.style.padding = '20px 24px';
    panel.style.borderRadius = '8px';
    panel.style.background = '#1f2933';
    panel.style.color = '#f0f0f0';
    panel.style.maxWidth = '320px';
    panel.style.fontFamily = 'system-ui, sans-serif';
    const text = document.createElement('p');
    text.textContent = message;
    text.style.margin = '0 0 12px 0';
    panel.appendChild(text);
    const buttons = document.createElement('div');
    buttons.style.display = 'flex';
    buttons.style.gap = '8px';
    buttons.style.justifyContent = 'flex-end';
    const cancelBtn = document.createElement('button');
    cancelBtn.type = 'button';
    cancelBtn.textContent = 'Cancel';
    const confirmBtn = document.createElement('button');
    confirmBtn.type = 'button';
    confirmBtn.textContent = 'Regenerate';
    buttons.appendChild(cancelBtn);
    buttons.appendChild(confirmBtn);
    panel.appendChild(buttons);
    overlay.appendChild(panel);
    canvasHost.appendChild(overlay);
    const cleanup = (result) => {
      if (overlay.parentNode) {
        overlay.parentNode.removeChild(overlay);
      }
      resolve(result);
    };
    cancelBtn.addEventListener('click', () => cleanup(false));
    confirmBtn.addEventListener('click', () => cleanup(true));
  });
};

regenButton.addEventListener('click', async () => {
  // The handler is wired early so the button is responsive on the
  // first paint, but it defers all reads/writes to the closures
  // `useAppStore` / `rebuildPlanetsRef` which are populated inside
  // the try block below. Until then the handler captures the current
  // snapshot via `useAppStore.getState()`.
  const installedCount = useAppStore.getState().installState.installedApps.length;
  let confirmed;
  try {
    confirmed = await confirmRegenerate(installedCount);
  } catch {
    confirmed = false;
  }
  if (!confirmed) {
    showRegenStatus('Regenerate cancelled');
    return;
  }
  const next = useAppStore.getState().regenerateWorld();
  // The factory rebuild is hooked up once the scene finishes
  // initializing; if the user clicked before that, the seed
  // subscription installed below will rebuild the factory on the
  // next tick.
  if (typeof rebuildPlanetsRef === 'function') {
    rebuildPlanetsRef(true);
  }
  showRegenStatus(`New seed: ${next.seed}`);
  logger('[Renderer] World regenerated', next);
});

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

  // Story 2-4: build the persistence adapter that hydrates the
  // store from disk on boot and mirrors every mutation back through
  // a throttled save middleware. The adapter is constructed once at
  // startup; every renderer-driven action goes through it.
  //
  // The on-disk file is namespaced via `PERSIST_NAMESPACE` so the
  // application does not collide with other Electron apps sharing
  // the same `userData` directory.
  //
  // Boot order matters: the persistence adapter is constructed and
  // attached BEFORE the planet factory is built so the
  // `installPersistenceBridge` hydration runs synchronously and
  // mutates `worldConfig.seed` before `createPlanetsForCategories`
  // reads it. Building the factory in a single pass with the
  // rehydrated seed avoids the "one-frame flash of the default-seed
  // layout" regression — the user sees exactly one consistent first
  // paint.
  const store = useAppStore;
  const persistence = createPersistence({ logger, name: PERSIST_NAMESPACE });
  attachPersistence(store, persistence, { logger });

  // After the persistence adapter has rehydrated `installState.installedApps`
  // from disk, the `categories` and `coreTools` slices still carry the
  // factory-default `installed: false` flags. The two derivations below
  // repaint the planet factory + the sun's satellite indicators from
  // the freshly-rehydrated install list so a user with persisted
  // installs sees the correct colors on the first paint — and not in
  // a confusing "everything is uninstalled" flash.
  store.getState().syncCategoriesFromInstalls();
  store.getState().syncCoreToolsFromInstalls();

  // Story 2-3: build the planet factory from the store's categories
  // slice, attach it to the scene controller, and subscribe to slice
  // changes so the installed flag for each category is pushed into
  // the 3D scene through `setPlanetInstalled`. The factory is owned
  // by the controller: dispose() will release its geometries and
  // detach the root group when the window closes.
  //
  // Story 2-4: we now also rebuild the factory when the worldConfig
  // seed changes (regenerateWorld, setSeed, or a rehydrate from
  // disk). `rebuildPlanets(force=false)` is idempotent: when the
  // seed matches the factory's current seed, the call is a no-op so
  // a no-op regenerateWorld() does not waste GPU resources.
  let planetsFactory = createPlanetsForCategories({
    THREE,
    categories: store.getState().categories,
    seed: store.getState().worldConfig.seed,
    logger,
  });
  sceneController.setPlanets(planetsFactory);

  const rebuildPlanets = (force = false) => {
    const nextSeed = store.getState().worldConfig.seed;
    if (!force && planetsFactory && planetsFactory.getSeed() === nextSeed) {
      return;
    }
    if (planetsFactory) {
      sceneController.setPlanets(null);
      planetsFactory.dispose();
      planetsFactory = null;
    }
    planetsFactory = createPlanetsForCategories({
      THREE,
      categories: store.getState().categories,
      seed: nextSeed,
      logger,
    });
    sceneController.setPlanets(planetsFactory);
    // Re-push the installed flags so the freshly-built factory
    // reflects the persisted install state on day one.
    for (const entry of store.getState().categories) {
      if (!entry || typeof entry.id !== 'string') {
        continue;
      }
      sceneController.setPlanetInstalled(entry.id, Boolean(entry.installed));
    }
    logger('[Renderer] Planet factory rebuilt', { seed: nextSeed });
  };

  // Bind the rebuild closure to the early-wired regen button handler.
  // The button is responsive on first paint so we cannot await the
  // try block to assign a closure variable. Using a let-bound
  // reference (instead of a `window.*` global) keeps the rebuild
  // function scoped to the renderer module so a future script
  // injection cannot reach in and force an unbounded rebuild.
  rebuildPlanetsRef = rebuildPlanets;

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

  // AC3 wiring: `addInstalledApp` / `removeInstalledApp` mutate
  // `installState.installedApps` but never touch `categories` directly.
  // The planet factory however subscribes to the `categories` slice
  // (see above). Without this listener, installing or uninstalling an
  // app would have zero visual effect on the planet colors until
  // something else happened to flip a category flag.
  //
  // We subscribe to the installedApps slice and re-derive both
  // `categories` and `coreTools` from it. The store actions are pure
  // and idempotent — when the derived state is identical, the slice
  // is left untouched (no spurious subscriber wake-ups).
  const pushInstalls = (installedApps) => {
    if (!Array.isArray(installedApps)) {
      return;
    }
    store.getState().syncCategoriesFromInstalls();
    store.getState().syncCoreToolsFromInstalls();
  };
  pushInstalls(store.getState().installState.installedApps);
  store.subscribe((state) => state.installState.installedApps, pushInstalls);

  // Story 2-4: rebuild the planet factory whenever the worldConfig
  // seed changes (regenerate, manual setSeed, rehydrate from disk).
  // The factory exposes its current seed via `getSeed()` so we can
  // skip the rebuild when the new seed matches the existing one —
  // important because `regenerateWorld` is a no-op when the slice is
  // unchanged, but the listener fires once per call.
  store.subscribe(
    (state) => state.worldConfig.seed,
    () => {
      rebuildPlanets(false);
    }
  );

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
  // Story 2-4: flush any pending throttled writes before the window
  // closes so a fast F5 / window close does not lose the last batch
  // of state mutations.
  try {
    if (typeof useAppStore?.persistenceFlush === 'function') {
      useAppStore.persistenceFlush();
    }
  } catch {
    // Best-effort: never let the cleanup path throw.
  }
  if (sceneController) {
    sceneController.dispose();
    sceneController = null;
  }
});
