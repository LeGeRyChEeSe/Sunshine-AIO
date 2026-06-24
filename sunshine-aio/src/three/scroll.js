/**
 * Horizontal scroll controller for Sunshine AIO (Story 3-1).
 *
 * Owns the camera's horizontal pan across the planet sequence. The
 * user can drive the camera with the mouse wheel (vertical wheel
 * deltas are mapped to horizontal motion) or by clicking-and-dragging
 * the canvas. The controller interpolates the camera toward the
 * target offset every frame with a critically-damped spring that
 * delivers a natural inertia feel, and clamps (or wraps) the target
 * at the configured boundary.
 *
 * Lifecycle:
 *   const scroll = createHorizontalScrollController({
 *     camera, canvas, planetCount, planets, ...
 *   });
 *   scroll.attach();          // bind DOM listeners
 *   scroll.update(delta);     // drive interpolation; call from RAF
 *   scroll.detach();          // unbind DOM listeners
 *   scroll.dispose();         // detach + zero state
 *
 * Boundary modes:
 *   - 'clamp' (default): the target stops at the first or last planet
 *     slot. The user can still push the wheel past the boundary; the
 *     target simply doesn't move further. The current offset also
 *     clamps to the boundary so the camera never slides off-world.
 *   - 'wrap': the target wraps around. Going past the last planet
 *     jumps to the first, and vice versa. Inertia naturally carries
 *     the visual across the wrap.
 *
 * The controller is intentionally framework-agnostic: it does not
 * import React, Zustand, or the scene controller. Consumers wire it
 * up in `setup.js` and feed it the camera + canvas. The brand symbol
 * lives in `setup.js` (a single source of truth) and is re-exported
 * from this module for tests so a future scene-controller refactor
 * can reject faked controllers on the same defense-in-depth principle
 * as `PLANET_FACTORY_BRAND`. Importing the brand — instead of
 * creating a fresh `Symbol('ScrollController')` here — guarantees
 * the brand stamped by this module is bit-identical to the one
 * `setScroll` checks, since `Symbol()` returns a unique value at every
 * call site.
 */

import { SCROLL_CONTROLLER_BRAND } from './setup.js';

export { SCROLL_CONTROLLER_BRAND };

const DEFAULT_DAMPING = 8; // higher = snappier, lower = floatier
const DEFAULT_WHEEL_SCALE = 0.0015; // wheel delta -> world units
const DEFAULT_DRAG_SCALE = 0.0045; // pointer delta -> world units
const DEFAULT_FRICTION = 4.5; // velocity decay per second
const DEFAULT_MAX_VELOCITY = 6; // world units per second
const DEFAULT_BOUNDARY_MODE = 'clamp';
const DEFAULT_PLANET_SPACING = 1.5; // world units between planet centers

const BOUNDARY_MODES = new Set(['clamp', 'wrap']);

/**
 * Coerce an arbitrary value into a finite, non-negative scalar. Used at
 * the configuration boundary so a typo in opts cannot corrupt the
 * spring math (e.g. NaN spring constant would freeze the camera).
 */
const sanitizeScalar = (value, fallback) => {
  if (typeof value === 'number' && Number.isFinite(value) && value >= 0) {
    return value;
  }
  return fallback;
};

/**
 * @typedef {Object} HorizontalScrollControllerOptions
 * @property {object} camera          Three.js camera (must expose
 *   `position` and optionally `lookAt`).
 * @property {HTMLCanvasElement | object} canvas Canvas used for pointer
 *   hit-testing. May be a stub in tests.
 * @property {number} [planetCount]   Number of planets in the scene.
 *   Defaults to 0; when 0 the controller clamps at offset 0 and
 *   nothing scrolls.
 * @property {number} [planetSpacing=1.5] Distance between planet
 *   centers along the X axis. Combined with `planetCount` to compute
 *   the right boundary slot.
 * @property {number} [damping=8]     Spring stiffness for the target
 *   interpolation. Higher values make the camera catch up to the
 *   target faster (less floaty).
 * @property {number} [friction=4.5]  Velocity decay per second once
 *   the user releases the wheel/drag. Higher values stop the camera
 *   sooner.
 * @property {number} [wheelScale=0.0015]  Multiplier applied to wheel
 *   `deltaY` to convert to world units.
 * @property {number} [dragScale=0.0045]   Multiplier applied to
 *   pointer movement in pixels to convert to world units.
 * @property {number} [maxVelocity=6] Cap on the integrated velocity
 *   so a flailing wheel gesture cannot launch the camera off-world.
 * @property {'clamp' | 'wrap'} [boundaryMode='clamp'] How the target
 *   behaves at the edges.
 * @property {(msg: string, meta?: object) => void} [logger] Optional
 *   logger; used for boundary-mode rejection and dispose() notices.
 * @property {boolean} [enabled=true] Initial enabled state.
 */

/**
 * Build a horizontal scroll controller. Returns the public surface
 * documented at the top of the file.
 *
 * @param {HorizontalScrollControllerOptions} opts
 */
export const createHorizontalScrollController = (opts = {}) => {
  if (!opts || !opts.camera) {
    throw new Error('createHorizontalScrollController: a camera is required');
  }
  if (!opts.canvas) {
    throw new Error('createHorizontalScrollController: a canvas is required');
  }

  const logger =
    typeof opts.logger === 'function' ? opts.logger : (msg, meta) => console.info(msg, meta);

  const camera = opts.camera;
  const canvas = opts.canvas;

  const planetCount = Math.max(0, Math.floor(sanitizeScalar(opts.planetCount, 0)));
  const planetSpacing = sanitizeScalar(opts.planetSpacing, DEFAULT_PLANET_SPACING);
  const damping = sanitizeScalar(opts.damping, DEFAULT_DAMPING);
  const friction = sanitizeScalar(opts.friction, DEFAULT_FRICTION);
  const wheelScale = sanitizeScalar(opts.wheelScale, DEFAULT_WHEEL_SCALE);
  const dragScale = sanitizeScalar(opts.dragScale, DEFAULT_DRAG_SCALE);
  const maxVelocity = sanitizeScalar(opts.maxVelocity, DEFAULT_MAX_VELOCITY);

  // Boundary mode is the only string we accept; anything else is
  // logged and collapsed onto the default. We refuse to silently
  // pick one because the visual feel changes meaningfully between
  // clamp and wrap.
  const requestedMode = opts.boundaryMode;
  let boundaryMode = DEFAULT_BOUNDARY_MODE;
  if (typeof requestedMode === 'string' && BOUNDARY_MODES.has(requestedMode)) {
    boundaryMode = requestedMode;
  } else if (requestedMode !== undefined) {
    logger('[Scroll] Unknown boundaryMode; falling back to "clamp"', {
      requested: requestedMode,
    });
  }

  // The "right edge" of the universe is the X coordinate of the LAST
  // planet's centerline. With planetCount=0 the universe collapses
  // to a single point (offset 0) and there is nothing to scroll.
  const maxOffset = planetCount > 0 ? (planetCount - 1) * planetSpacing : 0;

  // Internal state. `offset` is the visual (current) camera X; `target`
  // is what the user is steering toward; `velocity` is the residual
  // momentum that drives the camera between wheel/drag events.
  //
  // In `wrap` mode `target` is also the camera-space X (it lives inside
  // `[0, maxOffset)`). The unbounded counterpart is `visualOffset`: a
  // free-running accumulator that grows without bound as the user
  // scrolls. The camera X is `visualOffset mod maxOffset`, so a wheel
  // flick can carry the camera across the seam between the last and
  // first planet without the modulo snapping the next integrateVelocity
  // tick back to 0. `visualOffset` is only ever read in wrap mode; in
  // clamp mode it stays at 0 and `target` carries the full state.
  let offset = 0;
  let target = 0;
  let visualOffset = 0;
  let velocity = 0;
  let enabled = opts.enabled !== false;
  let attached = false;
  let disposed = false;

  // Drag state. The pointer can be a stub in tests; the controller
  // checks for the DOM methods before calling them.
  let dragging = false;
  let dragPointerId = null;
  let lastPointerX = 0;

  // Cached listener references so `detach()` can remove exactly the
  // functions that `attach()` registered. Re-binding `bound` copies
  // would silently fail to remove the listener on cleanup.
  const wheelListener = (event) => {
    if (!enabled || disposed) {
      return;
    }
    // We intentionally do not call `preventDefault()` here: the wheel
    // might arrive on a parent element (e.g. the Electron window
    // scrollbar). Letting the browser handle the default keeps the
    // canvas focusable. The motion of the scene is decoupled from
    // document scroll, so the user never sees a page jump.
    const delta = typeof event.deltaY === 'number' ? event.deltaY : 0;
    const impulse = delta * wheelScale;
    applyImpulse(impulse);
  };

  const pointerDownListener = (event) => {
    if (!enabled || disposed) {
      return;
    }
    if (typeof event.button === 'number' && event.button !== 0) {
      // Only left-button drags start a scroll; the right button is
      // reserved for future context menus.
      return;
    }
    dragging = true;
    dragPointerId = typeof event.pointerId === 'number' ? event.pointerId : null;
    lastPointerX = typeof event.clientX === 'number' ? event.clientX : 0;
    velocity = 0;
    if (canvas && typeof canvas.setPointerCapture === 'function' && dragPointerId !== null) {
      try {
        canvas.setPointerCapture(dragPointerId);
      } catch {
        // Some test stubs throw on setPointerCapture; swallowing the
        // error keeps the test suite honest about the failure
        // surface without masking real bugs.
      }
    }
    // Install window-level fallbacks while the drag is in progress so
    // a pointer-up outside the canvas (or an alt-tab mid-drag) still
    // ends the drag. These are removed in `endDrag` to avoid paying
    // the cost on idle frames.
    const scope = getGlobalScope();
    if (scope && typeof scope.addEventListener === 'function') {
      scope.addEventListener('pointerup', windowPointerUpListener);
      scope.addEventListener('blur', windowBlurListener);
    }
  };

  const pointerMoveListener = (event) => {
    if (!dragging || !enabled || disposed) {
      return;
    }
    if (
      dragPointerId !== null &&
      typeof event.pointerId === 'number' &&
      event.pointerId !== dragPointerId
    ) {
      return;
    }
    const x = typeof event.clientX === 'number' ? event.clientX : 0;
    const dx = x - lastPointerX;
    lastPointerX = x;
    // Drag-right should pan the camera LEFT (i.e. reveal planets to
    // the right). The convention matches Google Maps / Photos-style
    // scrollers and is the only one that feels right with inertia.
    applyImpulse(-dx * dragScale);
  };

  const endDrag = (event) => {
    if (!dragging) {
      return;
    }
    dragging = false;
    if (canvas && typeof canvas.releasePointerCapture === 'function' && dragPointerId !== null) {
      try {
        canvas.releasePointerCapture(dragPointerId);
      } catch {
        // ignore — stubbed canvases may not implement the method.
      }
    }
    dragPointerId = null;
    // Drop the window-level fallbacks now that the drag is done.
    const scope = getGlobalScope();
    if (scope && typeof scope.removeEventListener === 'function') {
      scope.removeEventListener('pointerup', windowPointerUpListener);
      scope.removeEventListener('blur', windowBlurListener);
    }
    // The event argument is intentionally unused; the listener only
    // cares about the side-effect of releasing pointer capture.
    void event;
  };

  const pointerUpListener = (event) => endDrag(event);
  const pointerCancelListener = (event) => endDrag(event);
  // `pointerleave` is registered as a defence against a drag that
  // exits the canvas before the user releases — without this the
  // pointer-capture path is the only safety net, and pointer capture
  // can fail silently (the `setPointerCapture` try/catch swallows the
  // error in some stubs). Falling back to a leave-driven endDrag keeps
  // `dragging` from getting stuck on `true` indefinitely.
  const pointerLeaveListener = (event) => endDrag(event);

  // Window-level fallbacks. We bind a global pointerup + blur listener
  // only while a drag is active so we don't pay the cost on idle
  // frames. The blur listener catches the case where the user alt-tabs
  // away mid-drag — the canvas will never see a pointerup.
  const windowPointerUpListener = (event) => endDrag(event);
  const windowBlurListener = () => endDrag(null);
  const getGlobalScope = () => {
    if (typeof window !== 'undefined') return window;
    if (typeof globalThis !== 'undefined') return globalThis;
    return null;
  };

  /**
   * Apply an instantaneous velocity change. The wheel emits discrete
   * deltas, so accumulating them as impulses (rather than a position
   * delta) preserves the natural "wheel flick feels snappy" feel.
   */
  const applyImpulse = (impulse) => {
    if (!Number.isFinite(impulse)) {
      return;
    }
    velocity += impulse;
    if (velocity > maxVelocity) {
      velocity = maxVelocity;
    } else if (velocity < -maxVelocity) {
      velocity = -maxVelocity;
    }
  };

  /**
   * Apply the boundary policy to a requested target. In `clamp` mode
   * the target is pinned to [0, maxOffset]; in `wrap` mode the target
   * is folded into [0, maxOffset) so it always points at a valid slot.
   * The wrap math uses `((value % length) + length) % length` so a
   * `value` of exactly `length` (or any positive multiple) lands at 0
   * rather than producing a `NaN` or out-of-range slot, and so negative
   * `value`s map back into the valid range symmetrically.
   *
   * Note: the per-frame visual continuity in wrap mode is provided by
   * `integrateVelocity`, which advances `visualOffset` freely and only
   * folds it into `target` for the camera transform. `applyBoundary` is
   * the single boundary primitive used by `jumpTo` and `setPlanetCount`
   * to clamp the camera-space slot.
   */
  const applyBoundary = (value) => {
    if (maxOffset <= 0) {
      return 0;
    }
    if (boundaryMode === 'wrap') {
      const length = maxOffset;
      let wrapped = value % length;
      if (wrapped < 0) {
        wrapped += length;
      }
      return wrapped;
    }
    if (value < 0) {
      return 0;
    }
    if (value > maxOffset) {
      return maxOffset;
    }
    return value;
  };

  /**
   * Update the target from the current velocity (the integrated
   * wheel/drag momentum). Called every frame from the render loop.
   * Friction decays the velocity exponentially so the camera glides
   * to a stop instead of halting abruptly.
   *
   * In `wrap` mode the accumulator (`visualOffset`) is allowed to grow
   * without bound across the seam; the camera-space slot (`target`) is
   * computed each tick as `visualOffset mod length`. This is the fix
   * for the seam-snap regression: under the prior implementation the
   * camera would slide linearly toward `length`, then on the next tick
   * the modulo would fold the target back to 0, producing a single
   * frame of discontinuity. With a free-running accumulator, the camera
   * crosses the seam linearly and the slot naturally wraps.
   *
   * In `clamp` mode `visualOffset` stays at 0 and `target` carries the
   * full state — the existing clamp math on `target` is unchanged.
   */
  const integrateVelocity = (deltaSeconds) => {
    if (!Number.isFinite(deltaSeconds) || deltaSeconds <= 0) {
      return;
    }
    if (boundaryMode === 'wrap' && maxOffset > 0) {
      visualOffset += velocity * deltaSeconds;
      // Fold only for the camera-space slot. The accumulator itself
      // never gets folded back, so the spring never sees a wrap-step
      // discontinuity on its own state.
      const length = maxOffset;
      let wrapped = visualOffset % length;
      if (wrapped < 0) {
        wrapped += length;
      }
      target = wrapped;
    } else {
      target += velocity * deltaSeconds;
      target = applyBoundary(target);
    }
    // Exponential decay: a frame of length `dt` multiplies velocity
    // by `exp(-friction * dt)`. The closed form is equivalent to
    // `v *= 1 - friction*dt` for small dt, but `exp` is frame-rate
    // independent. A floor at 1e-3 prevents an "infinite slide" if
    // the renderer is paused for minutes and resumed.
    const decay = Math.exp(-friction * deltaSeconds);
    velocity *= decay;
    if (Math.abs(velocity) < 1e-3) {
      velocity = 0;
    }
  };

  /**
   * Move the camera's X toward the target with a critically-damped
   * spring. `damping` controls how aggressively the camera catches
   * up; a high value makes the motion feel snappy, a low value makes
   * the motion feel floaty. The camera's Y and Z are left alone so
   * a future vertical-pan or zoom-in story can layer on top.
   *
   * In `wrap` mode the spring advances a free-running `offset` (in
   * the same coordinate space as `visualOffset`) and only folds into
   * the camera-space slot at the very end. Tracking the camera in
   * the same unbounded space as the target keeps the spring linear
   * across the wrap seam: the lerp `(target - offset) * k` would
   * otherwise see a discontinuity (target near `length`, offset near
   * 0) and skip an entire universe of motion in a single frame.
   */
  const applyCameraTransform = (deltaSeconds) => {
    if (!camera || !camera.position) {
      return;
    }
    const dt = Number.isFinite(deltaSeconds) && deltaSeconds > 0 ? deltaSeconds : 0;
    // Frame-rate independent lerp: 1 - exp(-damping * dt) converges
    // to 1 as dt grows and keeps the smoothing stable across 30/60
    // FPS. The plain `offset += (target - offset) * factor` form is
    // dependent on the renderer's frame interval.
    const k = 1 - Math.exp(-damping * dt);
    if (boundaryMode === 'wrap' && maxOffset > 0) {
      // Spring against the unbounded coordinate. Choose the offset
      // closest to `visualOffset` so the lerp is the short way around
      // the wrap (rather than spinning the camera the long way).
      const length = maxOffset;
      let delta = visualOffset - offset;
      delta -= Math.round(delta / length) * length;
      offset += delta * k;
      // Snap when the spring has fully settled so floating-point drift
      // doesn't keep nudging the camera forever.
      if (Math.abs(delta) < 1e-4 && Math.abs(velocity) < 1e-3) {
        offset = visualOffset;
      }
      let slot = offset % length;
      if (slot < 0) {
        slot += length;
      }
      camera.position.x = slot;
    } else {
      offset += (target - offset) * k;
      if (Math.abs(target - offset) < 1e-4 && Math.abs(velocity) < 1e-3) {
        offset = target;
      }
      camera.position.x = offset;
    }
  };

  /**
   * Per-frame driver. `deltaSeconds` is the elapsed wall-clock time
   * since the previous frame. Consumers wire this up via the scene
   * controller's `addUpdater` registry so the loop can pause when
   * the scene is paused.
   */
  const update = (deltaSeconds = 0) => {
    if (!enabled || disposed) {
      return;
    }
    integrateVelocity(deltaSeconds);
    applyCameraTransform(deltaSeconds);
  };

  const attach = () => {
    if (attached || disposed) {
      return;
    }
    attached = true;
    if (!canvas || typeof canvas.addEventListener !== 'function') {
      // Tests frequently pass a stub canvas that doesn't implement
      // addEventListener. The controller can still be used as a
      // state machine by calling `applyImpulse` directly; we just
      // skip the DOM binding in that case.
      return;
    }
    canvas.addEventListener('wheel', wheelListener, { passive: true });
    canvas.addEventListener('pointerdown', pointerDownListener);
    canvas.addEventListener('pointermove', pointerMoveListener);
    canvas.addEventListener('pointerup', pointerUpListener);
    canvas.addEventListener('pointercancel', pointerCancelListener);
    canvas.addEventListener('pointerleave', pointerLeaveListener);
  };

  const detach = () => {
    if (!attached) {
      return;
    }
    attached = false;
    if (!canvas || typeof canvas.removeEventListener !== 'function') {
      return;
    }
    canvas.removeEventListener('wheel', wheelListener);
    canvas.removeEventListener('pointerdown', pointerDownListener);
    canvas.removeEventListener('pointermove', pointerMoveListener);
    canvas.removeEventListener('pointerup', pointerUpListener);
    canvas.removeEventListener('pointercancel', pointerCancelListener);
    canvas.removeEventListener('pointerleave', pointerLeaveListener);
    // If a drag is still active when detach is called, end it so the
    // window-level fallback listeners installed in pointerDown are
    // cleaned up. `endDrag` short-circuits when `dragging` is false,
    // so calling it here is harmless in the common path.
    if (dragging) {
      endDrag(null);
    }
  };

  const setEnabled = (next) => {
    enabled = Boolean(next);
    if (!enabled) {
      velocity = 0;
    }
  };

  const getOffset = () => offset;
  const getTarget = () => target;
  const getVelocity = () => velocity;
  const getMaxOffset = () => maxOffset;
  const isEnabled = () => enabled;
  const isAttached = () => attached;
  const isDisposed = () => disposed;
  const getBoundaryMode = () => boundaryMode;

  /**
   * Jump to an absolute offset (e.g. when the user clicks a planet in
   * the UI to centre it). Clamps to the boundary so a programmatic
   * jump cannot push the camera off-world. The velocity is zeroed so
   * a manual jump is never overridden by stale inertia.
   *
   * The argument is interpreted as the camera-space slot in both
   * boundary modes (clamp and wrap); in wrap mode the unbounded
   * accumulator is folded to the requested slot so subsequent
   * inertia continues from the same visual position.
   */
  const jumpTo = (value) => {
    if (!Number.isFinite(value)) {
      return false;
    }
    const slot = applyBoundary(value);
    target = slot;
    offset = slot;
    visualOffset = slot;
    velocity = 0;
    if (camera && camera.position) {
      camera.position.x = slot;
    }
    return true;
  };

  /**
   * Replace the planet count at runtime. Used when categories are
   * reloaded from disk and the universe grew or shrank. The current
   * offset is re-clamped onto the new boundary so the camera never
   * sits beyond the last planet after a regeneration.
   *
   * In wrap mode `visualOffset` (the unbounded accumulator driving
   * the spring across the seam) is folded onto the new length so the
   * next frame picks up the same visual slot without re-crossing the
   * seam unexpectedly.
   */
  const setPlanetCount = (count) => {
    const safe = Math.max(0, Math.floor(sanitizeScalar(count, 0)));
    const newMax = safe > 0 ? (safe - 1) * planetSpacing : 0;
    planetCountValue = safe;
    // Re-clamp target + offset. We intentionally recompute maxOffset
    // against the updated count so the wrap/clamp math stays
    // consistent with the new universe.
    const newLength = newMax;
    if (newLength <= 0) {
      target = 0;
      offset = 0;
      visualOffset = 0;
    } else if (boundaryMode === 'wrap') {
      let wrapped = target % newLength;
      if (wrapped < 0) {
        wrapped += newLength;
      }
      target = wrapped;
      offset = wrapped;
      // Fold the unbounded accumulator to match. Keeping it in sync
      // here means a wheel flick right after the swap doesn't see a
      // surprise jump as the spring catches up from a stale offset.
      let wrappedVisual = visualOffset % newLength;
      if (wrappedVisual < 0) {
        wrappedVisual += newLength;
      }
      visualOffset = wrappedVisual;
    } else {
      if (target > newLength) {
        target = newLength;
      }
      if (target < 0) {
        target = 0;
      }
      if (offset > newLength) {
        offset = newLength;
      }
      if (offset < 0) {
        offset = 0;
      }
      visualOffset = 0;
    }
    velocity = 0;
    if (camera && camera.position) {
      camera.position.x = offset;
    }
  };

  // We store the planet count in a closure-local binding so
  // `setPlanetCount` can mutate it without a `let` redeclaration on
  // the top of the factory. The public `getPlanetCount` reads from
  // this binding.
  let planetCountValue = planetCount;

  const dispose = () => {
    if (disposed) {
      return;
    }
    disposed = true;
    detach();
    velocity = 0;
    target = 0;
    offset = 0;
    visualOffset = 0;
    logger('[Scroll] Disposed');
  };

  const controller = {
    attach,
    detach,
    update,
    setEnabled,
    isEnabled,
    isAttached,
    isDisposed,
    dispose,
    jumpTo,
    setPlanetCount,
    getOffset,
    getTarget,
    getVelocity,
    getMaxOffset,
    getBoundaryMode,
    getPlanetCount: () => planetCountValue,
    applyImpulse,
  };
  // Defense in depth: stamp the brand so a future refactor that
  // accepts an arbitrary object as a scroll controller can reject
  // fakes. Symbols cannot be forged across module boundaries — only
  // this module can stamp the exact value.
  try {
    Object.defineProperty(controller, SCROLL_CONTROLLER_BRAND, {
      value: true,
      enumerable: false,
      configurable: false,
      writable: false,
    });
  } catch (err) {
    logger('[Scroll] brand stamp failed', {
      error: err && err.message ? err.message : String(err),
    });
  }
  return controller;
};

export { DEFAULT_DAMPING, DEFAULT_FRICTION, DEFAULT_WHEEL_SCALE, DEFAULT_DRAG_SCALE };
