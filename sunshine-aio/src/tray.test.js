/**
 * Tests for the TrayManager (Story 1.4).
 *
 * The manager imports `electron` at module load, which is unavailable
 * under vitest's node environment. We side-step that by:
 *   - Passing a fake `electronDeps` bundle into the constructor with
 *     minimal `Tray`, `Menu`, and `nativeImage` mocks.
 *   - Re-importing the module via `vi.resetModules()` so each
 *     `describe` block can swap the electron mock without leaking
 *     state into siblings.
 *
 * Tests cover:
 *   - Construction validation (getMainWindow required).
 *   - Tray icon creation (init returns true, sets active).
 *   - Menu structure (Open / separator / Quit).
 *   - Click handler restores the main window (show + focus + unminimize).
 *   - dispose() is idempotent and clears the tray.
 *   - Minimize behavior: re-init after dispose is a no-op.
 *   - Quit menu item invokes the supplied onQuit callback.
 *   - Singleton accessors (initTrayManager / getTrayManager /
 *     disposeTrayManager) round-trip correctly.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

// Per-test electron mock factory. We build a fresh object each test so
// handler bookkeeping from one test never leaks into the next.
const makeElectronDeps = () => {
  const handlers = new Map();
  const fakeTrayInstance = {
    setToolTip: vi.fn(),
    setContextMenu: vi.fn(),
    on: vi.fn((event, cb) => {
      handlers.set(event, cb);
    }),
    destroy: vi.fn(),
  };
  const TrayCtor = vi.fn(() => fakeTrayInstance);
  const MenuCtor = {
    buildFromTemplate: vi.fn((template) => ({ __template: template })),
  };
  const fakeIcon = { isEmpty: () => false };
  const nativeImage = {
    createFromPath: vi.fn(() => fakeIcon),
    createEmpty: vi.fn(() => fakeIcon),
  };
  const fakeApp = { quit: vi.fn() };
  return {
    deps: { Tray: TrayCtor, Menu: MenuCtor, nativeImage, app: fakeApp },
    handlers,
    fakeTrayInstance,
    MenuCtor,
    fakeIcon,
    fakeApp,
  };
};

describe('TrayManager', () => {
  let electronMock;

  beforeEach(() => {
    electronMock = makeElectronDeps();
    // Reset module-level singleton state between tests so the
    // top-level accessors don't carry state across cases.
    vi.resetModules();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('throws when getMainWindow is missing', async () => {
    const { TrayManager } = await import('./tray.js');
    expect(() => new TrayManager({})).toThrow(TypeError);
    expect(() => new TrayManager({ getMainWindow: 'not-a-fn' })).toThrow(TypeError);
  });

  it('creates a tray icon on init and reports active', async () => {
    const { TrayManager } = await import('./tray.js');
    const win = { show: vi.fn(), focus: vi.fn(), unminimize: vi.fn() };
    const tm = new TrayManager({
      getMainWindow: () => win,
      electronDeps: electronMock.deps,
      logger: { info: vi.fn(), warn: vi.fn(), error: vi.fn() },
    });
    expect(tm.isActive()).toBe(false);
    const ok = tm.init();
    expect(ok).toBe(true);
    expect(tm.isActive()).toBe(true);
    expect(electronMock.deps.Tray).toHaveBeenCalledTimes(1);
    expect(electronMock.fakeTrayInstance.setToolTip).toHaveBeenCalledWith('Sunshine AIO');
    expect(electronMock.fakeTrayInstance.setContextMenu).toHaveBeenCalledTimes(1);
  });

  it('builds a context menu with Open, separator, and Quit', async () => {
    const { TrayManager } = await import('./tray.js');
    const win = { show: vi.fn(), focus: vi.fn() };
    const tm = new TrayManager({
      getMainWindow: () => win,
      electronDeps: electronMock.deps,
    });
    tm.init();
    expect(electronMock.MenuCtor.buildFromTemplate).toHaveBeenCalledTimes(1);
    const template = electronMock.MenuCtor.buildFromTemplate.mock.calls[0][0];
    expect(template).toHaveLength(3);
    expect(template[0].label).toBe('Open');
    expect(template[1]).toEqual({ type: 'separator' });
    expect(template[2].label).toBe('Quit');
  });

  it('restores the window on left-click and double-click', async () => {
    const { TrayManager } = await import('./tray.js');
    const win = {
      show: vi.fn(),
      focus: vi.fn(),
      unminimize: vi.fn(),
      isMinimized: () => true,
    };
    const tm = new TrayManager({
      getMainWindow: () => win,
      electronDeps: electronMock.deps,
    });
    tm.init();
    // The 'click' and 'double-click' handlers should restore the window.
    expect(electronMock.handlers.has('click')).toBe(true);
    expect(electronMock.handlers.has('double-click')).toBe(true);
    const clickHandler = electronMock.handlers.get('click');
    clickHandler();
    expect(win.show).toHaveBeenCalledTimes(1);
    expect(win.unminimize).toHaveBeenCalledTimes(1);
    expect(win.focus).toHaveBeenCalledTimes(1);
  });

  it('is a no-op when the main window is unavailable', async () => {
    const { TrayManager } = await import('./tray.js');
    const tm = new TrayManager({
      getMainWindow: () => null,
      electronDeps: electronMock.deps,
    });
    tm.init();
    const clickHandler = electronMock.handlers.get('click');
    expect(() => clickHandler()).not.toThrow();
  });

  it('invokes the supplied onQuit when Quit is picked', async () => {
    const { TrayManager } = await import('./tray.js');
    const onQuit = vi.fn();
    const tm = new TrayManager({
      getMainWindow: () => null,
      electronDeps: electronMock.deps,
      onQuit,
    });
    tm.init();
    const template = electronMock.MenuCtor.buildFromTemplate.mock.calls[0][0];
    template[2].click();
    expect(onQuit).toHaveBeenCalledTimes(1);
    expect(electronMock.fakeApp.quit).not.toHaveBeenCalled();
  });

  it('falls back to app.quit when onQuit is not provided', async () => {
    const { TrayManager } = await import('./tray.js');
    const tm = new TrayManager({
      getMainWindow: () => null,
      electronDeps: electronMock.deps,
    });
    tm.init();
    const template = electronMock.MenuCtor.buildFromTemplate.mock.calls[0][0];
    template[2].click();
    expect(electronMock.fakeApp.quit).toHaveBeenCalledTimes(1);
  });

  it('dispose() destroys the tray and clears active state', async () => {
    const { TrayManager } = await import('./tray.js');
    const tm = new TrayManager({
      getMainWindow: () => null,
      electronDeps: electronMock.deps,
    });
    tm.init();
    tm.dispose();
    expect(electronMock.fakeTrayInstance.destroy).toHaveBeenCalledTimes(1);
    expect(tm.isActive()).toBe(false);
    // Idempotent: a second dispose does not throw nor re-call destroy.
    tm.dispose();
    expect(electronMock.fakeTrayInstance.destroy).toHaveBeenCalledTimes(1);
  });

  it('re-init after dispose is a no-op (does not create a second tray)', async () => {
    const { TrayManager } = await import('./tray.js');
    const tm = new TrayManager({
      getMainWindow: () => null,
      electronDeps: electronMock.deps,
    });
    tm.init();
    tm.dispose();
    const ok = tm.init();
    expect(ok).toBe(false);
    expect(electronMock.deps.Tray).toHaveBeenCalledTimes(1);
  });

  it('init() is idempotent (a second call is a no-op while active)', async () => {
    const { TrayManager } = await import('./tray.js');
    const tm = new TrayManager({
      getMainWindow: () => null,
      electronDeps: electronMock.deps,
    });
    expect(tm.init()).toBe(true);
    expect(tm.init()).toBe(false);
    expect(electronMock.deps.Tray).toHaveBeenCalledTimes(1);
  });

  it('uses the empty icon when createFromPath returns empty', async () => {
    // Override the icon factory for this test only.
    electronMock.deps.nativeImage.createFromPath = vi.fn(() => ({ isEmpty: () => true }));
    const { TrayManager } = await import('./tray.js');
    const tm = new TrayManager({
      getMainWindow: () => null,
      electronDeps: electronMock.deps,
    });
    tm.init();
    expect(electronMock.deps.nativeImage.createEmpty).toHaveBeenCalled();
  });

  it('swallows destroy errors so dispose() stays idempotent', async () => {
    const { TrayManager } = await import('./tray.js');
    electronMock.fakeTrayInstance.destroy = vi.fn(() => {
      throw new Error('already destroyed');
    });
    const tm = new TrayManager({
      getMainWindow: () => null,
      electronDeps: electronMock.deps,
    });
    tm.init();
    expect(() => tm.dispose()).not.toThrow();
    expect(tm.isActive()).toBe(false);
  });
});

describe('TrayManager singletons', () => {
  beforeEach(() => {
    vi.resetModules();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('initTrayManager returns the same instance on repeat calls', async () => {
    const electronMock = makeElectronDeps();
    const { initTrayManager, getTrayManager } = await import('./tray.js');
    const a = initTrayManager({
      getMainWindow: () => null,
      electronDeps: electronMock.deps,
    });
    const b = initTrayManager({
      getMainWindow: () => null,
      electronDeps: electronMock.deps,
    });
    expect(a).toBe(b);
    expect(getTrayManager()).toBe(a);
  });

  it('disposeTrayManager clears the singleton', async () => {
    const electronMock = makeElectronDeps();
    const { initTrayManager, getTrayManager, disposeTrayManager } = await import('./tray.js');
    initTrayManager({
      getMainWindow: () => null,
      electronDeps: electronMock.deps,
    });
    expect(getTrayManager()).not.toBeNull();
    disposeTrayManager();
    expect(getTrayManager()).toBeNull();
  });
});
