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
 * No planet meshes are added in this story — that work lands in 2-2 and
 * 2-3. Story 2-1 only proves the plumbing: canvas + renderer + state +
 * FPS pipeline all compose correctly.
 */

import './styles.css';
import { createScene } from './three/setup.js';
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
  sceneController.start();

  const store = useAppStore;
  store.getState().markSceneInitialized(true);

  // Reflect FPS into the Zustand store and the on-screen overlay. The
  // overlay is updated from a small polling loop so the user-visible
  // value stays fresh even though the FPS monitor only logs every
  // ~2s. The store update is throttled to ~2 Hz to avoid hammering
  // React subscribers with transient frame data.
  let lastPushedAt = 0;
  let lastFrameTime = performance.now();
  const fpsProbe = () => {
    const now = performance.now();
    const delta = (now - lastFrameTime) / 1000;
    lastFrameTime = now;
    if (delta > 0) {
      const instantFps = 1 / delta;
      if (now - lastPushedAt >= 500) {
        lastPushedAt = now;
        store.getState().setFps(instantFps);
        fpsOverlay.textContent = `FPS: ${instantFps.toFixed(1)}`;
      }
    }
    if (sceneController && sceneController.isRunning()) {
      requestAnimationFrame(fpsProbe);
    }
  };
  requestAnimationFrame(fpsProbe);

  // Pin the initial view to the solar system so a brand-new install
  // lands on the right screen instead of waiting for the first user
  // interaction.
  if (store.getState().navigationState.currentView !== APP_VIEW.SOLAR_SYSTEM) {
    store.getState().setCurrentView(APP_VIEW.SOLAR_SYSTEM);
  }

  logger('[Renderer] Sunshine AIO renderer online (Story 2-1)');
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
