/**
 * Tests for the NotificationManager (Story 1.5).
 *
 * The manager imports `electron` lazily (so it can be unit-tested
 * without booting an Electron environment). The pattern:
 *   - Inject `electronDeps` with a fake `Notification` class that
 *     records the options it was constructed with and exposes a
 *     mocked `show` / `on` / `close` surface.
 *   - Re-import the module via `vi.resetModules()` so each
 *     `describe` block can swap the electron mock without leaking
 *     state into siblings.
 *
 * Tests cover:
 *   - Constructor validation (getMainWindow required).
 *   - `isSupported()` reflects the injected `isSupported()` probe.
 *   - `notifyInstallComplete` constructs a Notification with the
 *     expected title / body / icon / silent.
 *   - `notifyUpdateAvailable` handles arrays of strings, arrays of
 *     objects with `name`, comma-separated strings, and counts.
 *   - `notifyError` caps long messages, supports custom titles,
 *     and tolerates non-string inputs.
 *   - `setEnabled(false)` suppresses toasts but still logs.
 *   - Click handler focuses the main window (show + focus +
 *     unminimize).
 *   - `failed` and `close` events are surfaced to the logger.
 *   - Fallback: when `Notification.isSupported()` returns false
 *     we do not attempt to construct a Notification.
 *   - Singleton accessors round-trip correctly.
 *   - `dispose()` is idempotent and prevents further shows.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const makeElectronDeps = ({ supported = true } = {}) => {
  const constructors = [];
  const fakeNotification = function Notification(opts) {
    this.opts = opts;
    this._handlers = new Map();
    constructors.push(this);
  };
  fakeNotification.isSupported = vi.fn(() => supported);
  fakeNotification.prototype.show = vi.fn();
  fakeNotification.prototype.close = vi.fn();
  fakeNotification.prototype.on = vi.fn(function (event, handler) {
    this._handlers.set(event, handler);
  });
  return {
    deps: {
      Notification: fakeNotification,
      isSupported: () => supported,
    },
    constructors,
    fakeNotification,
  };
};

describe('NotificationManager', () => {
  beforeEach(() => {
    vi.resetModules();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('throws when getMainWindow is missing', async () => {
    const { NotificationManager } = await import('./notifications.js');
    expect(() => new NotificationManager({})).toThrow(TypeError);
    expect(() => new NotificationManager({ getMainWindow: 'not-a-fn' })).toThrow(TypeError);
  });

  it('reports isSupported() based on the injected probe', async () => {
    const { NotificationManager } = await import('./notifications.js');
    const electronMock = makeElectronDeps({ supported: true });
    const win = {};
    const mgr = new NotificationManager({
      getMainWindow: () => win,
      electronDeps: electronMock.deps,
    });
    expect(mgr.isSupported()).toBe(true);

    vi.resetModules();
    const unsupported = makeElectronDeps({ supported: false });
    const { NotificationManager: NotificationManager2 } = await import('./notifications.js');
    const mgr2 = new NotificationManager2({
      getMainWindow: () => win,
      electronDeps: unsupported.deps,
    });
    expect(mgr2.isSupported()).toBe(false);
  });

  it('builds an install-complete notification with title/body/icon/silent', async () => {
    const { NotificationManager } = await import('./notifications.js');
    const electronMock = makeElectronDeps();
    const logger = { info: vi.fn(), warn: vi.fn(), error: vi.fn(), debug: vi.fn() };
    const win = {};
    const mgr = new NotificationManager({
      getMainWindow: () => win,
      electronDeps: electronMock.deps,
      logger,
      iconPath: '/tmp/icon.png',
    });
    const ok = mgr.notifyInstallComplete('Sunshine');
    expect(ok).toBe(true);
    expect(electronMock.constructors).toHaveLength(1);
    const opts = electronMock.constructors[0].opts;
    expect(opts.title).toContain('Installation Complete');
    expect(opts.body).toBe('Sunshine has been installed successfully.');
    expect(opts.icon).toBe('/tmp/icon.png');
    expect(opts.silent).toBe(false);
    expect(electronMock.constructors[0].show).toHaveBeenCalledTimes(1);
    // Logger captures both the request and the show.
    expect(logger.info).toHaveBeenCalled();
  });

  it('falls back to a generic name when install name is empty', async () => {
    const { NotificationManager } = await import('./notifications.js');
    const electronMock = makeElectronDeps();
    const mgr = new NotificationManager({
      getMainWindow: () => {},
      electronDeps: electronMock.deps,
    });
    mgr.notifyInstallComplete('   ');
    const opts = electronMock.constructors[0].opts;
    expect(opts.body).toBe('The application has been installed successfully.');
  });

  it('counts updates from an array of strings', async () => {
    const { NotificationManager } = await import('./notifications.js');
    const electronMock = makeElectronDeps();
    const mgr = new NotificationManager({
      getMainWindow: () => {},
      electronDeps: electronMock.deps,
    });
    mgr.notifyUpdateAvailable(['Sunshine', 'VDD', 'Playnite']);
    const opts = electronMock.constructors[0].opts;
    expect(opts.title).toContain('Updates Available');
    expect(opts.body).toBe('3 updates are available for installed applications.');
  });

  it('uses the first name in the title for a single update', async () => {
    const { NotificationManager } = await import('./notifications.js');
    const electronMock = makeElectronDeps();
    const mgr = new NotificationManager({
      getMainWindow: () => {},
      electronDeps: electronMock.deps,
    });
    mgr.notifyUpdateAvailable([{ name: 'Sunshine' }]);
    const opts = electronMock.constructors[0].opts;
    expect(opts.title).toContain('(Sunshine)');
    expect(opts.body).toBe('1 update is available for an installed application.');
  });

  it('accepts a comma-separated string as the update list', async () => {
    const { NotificationManager } = await import('./notifications.js');
    const electronMock = makeElectronDeps();
    const mgr = new NotificationManager({
      getMainWindow: () => {},
      electronDeps: electronMock.deps,
    });
    mgr.notifyUpdateAvailable('Sunshine, VDD');
    const opts = electronMock.constructors[0].opts;
    expect(opts.body).toBe('2 updates are available for installed applications.');
  });

  it('accepts a bare count as the update list', async () => {
    const { NotificationManager } = await import('./notifications.js');
    const electronMock = makeElectronDeps();
    const mgr = new NotificationManager({
      getMainWindow: () => {},
      electronDeps: electronMock.deps,
    });
    mgr.notifyUpdateAvailable(7);
    const opts = electronMock.constructors[0].opts;
    expect(opts.body).toBe('7 updates are available for installed applications.');
  });

  it('truncates long error messages', async () => {
    const { NotificationManager } = await import('./notifications.js');
    const electronMock = makeElectronDeps();
    const mgr = new NotificationManager({
      getMainWindow: () => {},
      electronDeps: electronMock.deps,
    });
    const longMsg = 'x'.repeat(500);
    mgr.notifyError(longMsg);
    const opts = electronMock.constructors[0].opts;
    expect(opts.body.length).toBeLessThanOrEqual(200);
    expect(opts.body.endsWith('...')).toBe(true);
  });

  it('supports a custom title for error notifications', async () => {
    const { NotificationManager } = await import('./notifications.js');
    const electronMock = makeElectronDeps();
    const mgr = new NotificationManager({
      getMainWindow: () => {},
      electronDeps: electronMock.deps,
    });
    mgr.notifyError('boom', { title: 'Custom Title' });
    const opts = electronMock.constructors[0].opts;
    expect(opts.title).toBe('Custom Title');
  });

  it('tolerates non-string error messages', async () => {
    const { NotificationManager } = await import('./notifications.js');
    const electronMock = makeElectronDeps();
    const mgr = new NotificationManager({
      getMainWindow: () => {},
      electronDeps: electronMock.deps,
    });
    mgr.notifyError(null);
    const opts = electronMock.constructors[0].opts;
    expect(typeof opts.body).toBe('string');
    expect(opts.body.length).toBeGreaterThan(0);
  });

  it('does not construct a Notification when isSupported() returns false', async () => {
    const { NotificationManager } = await import('./notifications.js');
    const electronMock = makeElectronDeps({ supported: false });
    const mgr = new NotificationManager({
      getMainWindow: () => {},
      electronDeps: electronMock.deps,
    });
    const ok = mgr.notifyInstallComplete('Sunshine');
    expect(ok).toBe(false);
    expect(electronMock.constructors).toHaveLength(0);
  });

  it('does not construct a Notification when disabled via setEnabled(false)', async () => {
    const { NotificationManager } = await import('./notifications.js');
    const electronMock = makeElectronDeps();
    const logger = { info: vi.fn(), warn: vi.fn(), error: vi.fn(), debug: vi.fn() };
    const mgr = new NotificationManager({
      getMainWindow: () => {},
      electronDeps: electronMock.deps,
      logger,
    });
    mgr.setEnabled(false);
    expect(mgr.isEnabled()).toBe(false);
    const ok = mgr.notifyError('boom');
    expect(ok).toBe(false);
    expect(electronMock.constructors).toHaveLength(0);
    // The audit trail is preserved.
    expect(logger.info).toHaveBeenCalled();
    expect(logger.debug).toHaveBeenCalled();
  });

  it('re-enabling allows subsequent toasts', async () => {
    const { NotificationManager } = await import('./notifications.js');
    const electronMock = makeElectronDeps();
    const mgr = new NotificationManager({
      getMainWindow: () => {},
      electronDeps: electronMock.deps,
    });
    mgr.setEnabled(false);
    expect(mgr.notifyInstallComplete('X')).toBe(false);
    mgr.setEnabled(true);
    expect(mgr.notifyInstallComplete('X')).toBe(true);
    expect(electronMock.constructors).toHaveLength(1);
  });

  it('focuses the main window when the user clicks the notification', async () => {
    const { NotificationManager } = await import('./notifications.js');
    const electronMock = makeElectronDeps();
    const logger = { info: vi.fn(), warn: vi.fn(), error: vi.fn(), debug: vi.fn() };
    const win = {
      show: vi.fn(),
      focus: vi.fn(),
      unminimize: vi.fn(),
      isMinimized: () => true,
    };
    const mgr = new NotificationManager({
      getMainWindow: () => win,
      electronDeps: electronMock.deps,
      logger,
    });
    mgr.notifyInstallComplete('Sunshine');
    const handlers = electronMock.constructors[0]._handlers;
    expect(handlers.has('click')).toBe(true);
    handlers.get('click')();
    expect(win.show).toHaveBeenCalledTimes(1);
    expect(win.unminimize).toHaveBeenCalledTimes(1);
    expect(win.focus).toHaveBeenCalledTimes(1);
    expect(logger.info).toHaveBeenCalledWith(
      'notification.install-complete.click',
      expect.objectContaining({ title: expect.any(String) })
    );
  });

  it('click handler is a no-op when the main window is unavailable', async () => {
    const { NotificationManager } = await import('./notifications.js');
    const electronMock = makeElectronDeps();
    const mgr = new NotificationManager({
      getMainWindow: () => null,
      electronDeps: electronMock.deps,
    });
    mgr.notifyInstallComplete('Sunshine');
    const handlers = electronMock.constructors[0]._handlers;
    expect(() => handlers.get('click')()).not.toThrow();
  });

  it('surfaces failed events to the logger', async () => {
    const { NotificationManager } = await import('./notifications.js');
    const electronMock = makeElectronDeps();
    const logger = { info: vi.fn(), warn: vi.fn(), error: vi.fn(), debug: vi.fn() };
    const mgr = new NotificationManager({
      getMainWindow: () => {},
      electronDeps: electronMock.deps,
      logger,
    });
    mgr.notifyInstallComplete('Sunshine');
    const handlers = electronMock.constructors[0]._handlers;
    handlers.get('failed')(null, new Error('boom'));
    expect(logger.warn).toHaveBeenCalledWith(
      'notification.install-complete.failed',
      expect.objectContaining({ message: 'boom' })
    );
  });

  it('surfaces close events to the logger', async () => {
    const { NotificationManager } = await import('./notifications.js');
    const electronMock = makeElectronDeps();
    const logger = { info: vi.fn(), warn: vi.fn(), error: vi.fn(), debug: vi.fn() };
    const mgr = new NotificationManager({
      getMainWindow: () => {},
      electronDeps: electronMock.deps,
      logger,
    });
    mgr.notifyError('boom');
    const handlers = electronMock.constructors[0]._handlers;
    handlers.get('close')();
    expect(logger.debug).toHaveBeenCalledWith('notification.error.close', expect.any(Object));
  });

  it('logs and returns false when the constructor throws', async () => {
    const { NotificationManager } = await import('./notifications.js');
    const electronMock = makeElectronDeps();
    // Replace the constructor with one that throws.
    electronMock.deps.Notification = function ThrowingNotification() {
      throw new Error('not allowed');
    };
    const logger = { info: vi.fn(), warn: vi.fn(), error: vi.fn(), debug: vi.fn() };
    const mgr = new NotificationManager({
      getMainWindow: () => {},
      electronDeps: electronMock.deps,
      logger,
    });
    const ok = mgr.notifyError('boom');
    expect(ok).toBe(false);
    expect(logger.error).toHaveBeenCalledWith(
      'notification.error.error',
      expect.objectContaining({ message: 'not allowed' })
    );
  });

  it('dispose() is idempotent and prevents further shows', async () => {
    const { NotificationManager } = await import('./notifications.js');
    const electronMock = makeElectronDeps();
    const logger = { info: vi.fn(), warn: vi.fn(), error: vi.fn(), debug: vi.fn() };
    const mgr = new NotificationManager({
      getMainWindow: () => {},
      electronDeps: electronMock.deps,
      logger,
    });
    mgr.dispose();
    mgr.dispose();
    const ok = mgr.notifyInstallComplete('Sunshine');
    expect(ok).toBe(false);
    expect(electronMock.constructors).toHaveLength(0);
    expect(logger.warn).toHaveBeenCalledWith('notification.disposed', expect.any(Object));
  });
});

describe('NotificationManager singleton', () => {
  beforeEach(() => {
    vi.resetModules();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('initNotificationManager returns the same instance on repeat calls', async () => {
    const electronMock = makeElectronDeps();
    const { initNotificationManager, getNotificationManager } = await import('./notifications.js');
    const a = initNotificationManager({
      getMainWindow: () => null,
      electronDeps: electronMock.deps,
    });
    const b = initNotificationManager({
      getMainWindow: () => null,
      electronDeps: electronMock.deps,
    });
    expect(a).toBe(b);
    expect(getNotificationManager()).toBe(a);
  });

  it('disposeNotificationManager clears the singleton', async () => {
    const electronMock = makeElectronDeps();
    const { initNotificationManager, getNotificationManager, disposeNotificationManager } =
      await import('./notifications.js');
    initNotificationManager({
      getMainWindow: () => null,
      electronDeps: electronMock.deps,
    });
    expect(getNotificationManager()).not.toBeNull();
    disposeNotificationManager();
    expect(getNotificationManager()).toBeNull();
  });
});
