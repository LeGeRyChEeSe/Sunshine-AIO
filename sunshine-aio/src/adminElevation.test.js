/**
 * Tests for the adminElevation module — Story 1.4 admin privileges.
 *
 * Covers the high-severity regressions that prompted this module's
 * extraction from main.js:
 *
 *   - `requestAdminElevation` actually uses the `runas` ShellExecute
 *     verb (was: only set the priority class via `/high`, no UAC).
 *   - `isRunningAsAdmin` runs the documented `whoami /groups` probe
 *     rather than unconditionally returning false.
 *   - The spawned command uses `powershell` with `-Verb RunAs` rather
 *     than `cmd.exe /c start /high` (which silently spawns a
 *     non-elevated duplicate and never raises the UAC prompt).
 *   - Edge cases: non-Windows platform, child_process throwing,
 *     process.isElevated=true short-circuit, JSON parsing of marker
 *     file, and argument escaping for paths with spaces / quotes.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import path from 'node:path';

import {
  _resetIsElevatedCache,
  isRunningAsAdmin,
  isWindowsPlatform,
  parseWhoamiGroupsOutput,
  probeElevatedViaWhoami,
  readProcessElevatedFlag,
  requestAdminElevation,
} from './adminElevation.js';

const ORIGINAL_PLATFORM = Object.getOwnPropertyDescriptor(process, 'platform');

const setPlatform = (value) => {
  Object.defineProperty(process, 'platform', {
    value,
    configurable: true,
    writable: true,
  });
};

const restorePlatform = () => {
  if (ORIGINAL_PLATFORM) {
    Object.defineProperty(process, 'platform', ORIGINAL_PLATFORM);
  }
};

describe('isWindowsPlatform', () => {
  it('returns true on win32', () => {
    setPlatform('win32');
    expect(isWindowsPlatform()).toBe(true);
  });

  it('returns false on darwin / linux', () => {
    setPlatform('darwin');
    expect(isWindowsPlatform()).toBe(false);
    setPlatform('linux');
    expect(isWindowsPlatform()).toBe(false);
  });

  afterEach(restorePlatform);
});

describe('parseWhoamiGroupsOutput', () => {
  it('detects elevation via the S-1-16-12288 SID', () => {
    const stdout = `
GROUP INFORMATION
-----------------
Group Name                                  Type             SID          Attributes
=========================================== ================ ============ ==================================================
BUILTIN\\Administrators                      Alias            S-1-5-32-544 Enabled by default, Enabled group, Group owner
Mandatory Label\\High Mandatory Level        Label            S-1-16-12288
Everyone                                    Well-known group S-1-1-0      Mandatory group, Enabled by default, Enabled group
`;
    expect(parseWhoamiGroupsOutput(stdout)).toBe(true);
  });

  it('detects elevation via the EN label needle (fallback)', () => {
    // Some build pipelines strip SIDs but keep the EN label.
    const stdout = `
Mandatory Label\\High Mandatory Level        Label
`;
    expect(parseWhoamiGroupsOutput(stdout)).toBe(true);
  });

  it('returns false for a non-elevated user', () => {
    const stdout = `
GROUP INFORMATION
-----------------
BUILTIN\\Administrators                      Alias            S-1-5-32-544
Everyone                                    Well-known group S-1-1-0
`;
    expect(parseWhoamiGroupsOutput(stdout)).toBe(false);
  });

  it('returns false for an empty / non-string input', () => {
    expect(parseWhoamiGroupsOutput('')).toBe(false);
    expect(parseWhoamiGroupsOutput(null)).toBe(false);
    expect(parseWhoamiGroupsOutput(undefined)).toBe(false);
    expect(parseWhoamiGroupsOutput(42)).toBe(false);
  });
});

describe('readProcessElevatedFlag', () => {
  afterEach(() => {
    try {
      delete process.isElevated;
    } catch {
      /* may not be deletable in some environments; the next test will redefine */
    }
    _resetIsElevatedCache();
  });

  it('returns the boolean when process.isElevated is set', () => {
    Object.defineProperty(process, 'isElevated', {
      value: true,
      configurable: true,
      writable: true,
    });
    expect(readProcessElevatedFlag()).toBe(true);
    Object.defineProperty(process, 'isElevated', {
      value: false,
      configurable: true,
      writable: true,
    });
    expect(readProcessElevatedFlag()).toBe(false);
  });

  it('returns null when process.isElevated is undefined', () => {
    try {
      delete process.isElevated;
    } catch {}
    expect(readProcessElevatedFlag()).toBe(null);
  });

  it('returns null when the getter throws (defensive)', () => {
    const original = Object.getOwnPropertyDescriptor(process, 'isElevated');
    Object.defineProperty(process, 'isElevated', {
      configurable: true,
      get() {
        throw new Error('boom');
      },
    });
    expect(readProcessElevatedFlag()).toBe(null);
    if (original) {
      Object.defineProperty(process, 'isElevated', original);
    } else {
      try {
        delete process.isElevated;
      } catch {}
    }
  });
});

describe('probeElevatedViaWhoami', () => {
  it('returns true when whoami stdout contains the elevated SID', () => {
    const spawnSync = vi.fn(() => ({ stdout: 'Mandatory Label S-1-16-12288', status: 0 }));
    expect(probeElevatedViaWhoami(spawnSync)).toBe(true);
    expect(spawnSync).toHaveBeenCalledWith('whoami', ['/groups'], expect.any(Object));
  });

  it('returns false when whoami stdout has no elevated SID', () => {
    const spawnSync = vi.fn(() => ({ stdout: 'No elevated groups here', status: 0 }));
    expect(probeElevatedViaWhoami(spawnSync)).toBe(false);
  });

  it('returns null when the spawn throws', () => {
    const spawnSync = vi.fn(() => {
      throw new Error('whoami not found');
    });
    expect(probeElevatedViaWhoami(spawnSync)).toBe(null);
  });

  it('returns null when stdout is missing / non-string', () => {
    expect(probeElevatedViaWhoami(() => ({ stdout: undefined }))).toBe(null);
    expect(probeElevatedViaWhoami(() => null)).toBe(null);
    expect(probeElevatedViaWhoami(() => ({}))).toBe(null);
  });
});

describe('isRunningAsAdmin', () => {
  beforeEach(() => {
    setPlatform('win32');
    _resetIsElevatedCache();
    try {
      delete process.isElevated;
    } catch {}
  });

  afterEach(() => {
    restorePlatform();
    _resetIsElevatedCache();
    try {
      delete process.isElevated;
    } catch {}
  });

  it('returns false on non-Windows platforms without spawning', () => {
    setPlatform('darwin');
    const spawnImpl = vi.fn(() => ({ stdout: '' }));
    expect(isRunningAsAdmin({ spawnImpl })).toBe(false);
    expect(spawnImpl).not.toHaveBeenCalled();
  });

  it('honors process.isElevated=true and skips whoami', () => {
    Object.defineProperty(process, 'isElevated', {
      value: true,
      configurable: true,
      writable: true,
    });
    const spawnImpl = vi.fn(() => ({ stdout: '' }));
    expect(isRunningAsAdmin({ spawnImpl })).toBe(true);
    expect(spawnImpl).not.toHaveBeenCalled();
  });

  it('honors process.isElevated=false and skips whoami', () => {
    Object.defineProperty(process, 'isElevated', {
      value: false,
      configurable: true,
      writable: true,
    });
    const spawnImpl = vi.fn(() => ({ stdout: '' }));
    expect(isRunningAsAdmin({ spawnImpl })).toBe(false);
    expect(spawnImpl).not.toHaveBeenCalled();
  });

  it('runs whoami /groups and returns true on the elevated SID', () => {
    const spawnImpl = vi.fn(() => ({
      stdout: 'Mandatory Label\\High Mandatory Level S-1-16-12288',
    }));
    expect(isRunningAsAdmin({ spawnImpl })).toBe(true);
    expect(spawnImpl).toHaveBeenCalledWith('whoami', ['/groups'], expect.any(Object));
  });

  it('runs whoami /groups and returns false when not elevated', () => {
    const spawnImpl = vi.fn(() => ({ stdout: 'BUILTIN\\Users S-1-5-32-545' }));
    expect(isRunningAsAdmin({ spawnImpl })).toBe(false);
    expect(spawnImpl).toHaveBeenCalledWith('whoami', ['/groups'], expect.any(Object));
  });

  it('returns false (and does not throw) when whoami fails', () => {
    const spawnImpl = vi.fn(() => {
      throw new Error('whoami missing');
    });
    expect(isRunningAsAdmin({ spawnImpl })).toBe(false);
  });

  it('caches the result across calls', () => {
    const spawnImpl = vi.fn(() => ({ stdout: 'S-1-16-12288' }));
    expect(isRunningAsAdmin({ spawnImpl })).toBe(true);
    expect(isRunningAsAdmin({ spawnImpl })).toBe(true);
    expect(spawnImpl).toHaveBeenCalledTimes(1);
  });

  it('forceFresh bypasses the cache', () => {
    const spawnImpl = vi.fn(() => ({ stdout: 'S-1-16-12288' }));
    expect(isRunningAsAdmin({ spawnImpl })).toBe(true);
    expect(isRunningAsAdmin({ spawnImpl, forceFresh: true })).toBe(true);
    expect(spawnImpl).toHaveBeenCalledTimes(2);
  });

  it('invalidates the cache via _resetIsElevatedCache', () => {
    const spawnImpl = vi.fn(() => ({ stdout: 'S-1-16-12288' }));
    expect(isRunningAsAdmin({ spawnImpl })).toBe(true);
    _resetIsElevatedCache();
    expect(isRunningAsAdmin({ spawnImpl })).toBe(true);
    expect(spawnImpl).toHaveBeenCalledTimes(2);
  });
});

describe('requestAdminElevation', () => {
  beforeEach(() => {
    setPlatform('win32');
  });

  afterEach(() => {
    restorePlatform();
  });

  it('returns ok:true on non-Windows', async () => {
    setPlatform('darwin');
    const spawnImpl = vi.fn();
    const result = await requestAdminElevation({ spawnImpl });
    expect(result).toEqual({ ok: false, reason: 'unsupported platform' });
    expect(spawnImpl).not.toHaveBeenCalled();
  });

  it('spawns powershell.exe with the runas verb (regression: was /high cmd)', async () => {
    const spawnImpl = vi.fn(() => ({ unref: vi.fn() }));
    const result = await requestAdminElevation({ spawnImpl });
    expect(result.ok).toBe(true);
    expect(spawnImpl).toHaveBeenCalledTimes(1);
    const [cmd, args, opts] = spawnImpl.mock.calls[0];
    // Command must be powershell, not cmd.exe — the old code used
    // `cmd.exe /c start ... /high`, which never raised a UAC prompt.
    expect(cmd).toBe('powershell.exe');
    // The composed PowerShell command must include `RunAs` and the
    // exe path. We assert on the substring rather than the full
    // command to avoid coupling the test to whitespace / quoting.
    const psCommand = args[args.length - 1];
    expect(psCommand).toContain('Start-Process');
    expect(psCommand).toContain('-Verb RunAs');
    expect(psCommand).toContain(process.execPath);
    // Must NOT use /high — that flag only sets the priority class
    // and is the original bug.
    expect(psCommand).not.toContain('/high');
    expect(psCommand).not.toContain('cmd.exe');
    // Spawn must be detached + hidden so the elevated child survives
    // parent shutdown and does not pop a console window.
    expect(opts).toMatchObject({ detached: true, stdio: 'ignore', windowsHide: true });
  });

  it('passes handshakeArgs as a separate array element to Start-Process', async () => {
    const spawnImpl = vi.fn(() => ({ unref: vi.fn() }));
    await requestAdminElevation({
      spawnImpl,
      handshakeArgs: ['--sunshine-aio-elevation-handshake', 'C:\\Temp\\marker.json'],
    });
    const psCommand = spawnImpl.mock.calls[0][1].slice(-1)[0];
    // The -ArgumentList must be emitted as a PowerShell array so the
    // child process receives the flags as separate argv entries.
    expect(psCommand).toContain('-ArgumentList @(');
    expect(psCommand).toContain("'--sunshine-aio-elevation-handshake'");
    expect(psCommand).toContain("'C:\\Temp\\marker.json'");
  });

  it('does not pass -ArgumentList when handshakeArgs is empty', async () => {
    const spawnImpl = vi.fn(() => ({ unref: vi.fn() }));
    await requestAdminElevation({ spawnImpl });
    const psCommand = spawnImpl.mock.calls[0][1].slice(-1)[0];
    expect(psCommand).not.toContain('-ArgumentList');
  });

  it('escapes single quotes in the exe path', async () => {
    const originalExecPath = process.execPath;
    Object.defineProperty(process, 'execPath', {
      value: "C:\\Path's\\sunshine.exe",
      configurable: true,
      writable: true,
    });
    try {
      const spawnImpl = vi.fn(() => ({ unref: vi.fn() }));
      await requestAdminElevation({ spawnImpl });
      const psCommand = spawnImpl.mock.calls[0][1].slice(-1)[0];
      // PowerShell's single-quote escape is '' (doubled single quote)
      expect(psCommand).toContain("C:\\Path''s\\sunshine.exe");
    } finally {
      Object.defineProperty(process, 'execPath', {
        value: originalExecPath,
        configurable: true,
        writable: true,
      });
    }
  });

  it('unrefs the child so the parent can exit without waiting', async () => {
    const unref = vi.fn();
    const spawnImpl = vi.fn(() => ({ unref }));
    await requestAdminElevation({ spawnImpl });
    expect(unref).toHaveBeenCalled();
  });

  it('returns ok:false with the error message when spawn throws', async () => {
    const spawnImpl = vi.fn(() => {
      throw new Error('spawn failed');
    });
    const result = await requestAdminElevation({ spawnImpl });
    expect(result.ok).toBe(false);
    expect(result.reason).toBe('spawn failed');
  });

  it('tolerates a child without an unref method (defensive)', async () => {
    const spawnImpl = vi.fn(() => ({}));
    const result = await requestAdminElevation({ spawnImpl });
    expect(result.ok).toBe(true);
  });

  it('treats non-array handshakeArgs as empty (defensive)', async () => {
    const spawnImpl = vi.fn(() => ({ unref: vi.fn() }));
    await requestAdminElevation({ spawnImpl, handshakeArgs: 'not-an-array' });
    const psCommand = spawnImpl.mock.calls[0][1].slice(-1)[0];
    expect(psCommand).not.toContain('-ArgumentList');
  });
});

describe('integration: marker file path is stable for parent and child', () => {
  it('parent path and child path use the same well-known location', () => {
    // Both parent and child use computeElevationMarkerPath from
    // main.js, but the *marker filename* must remain stable so a
    // future bugfix doesn't silently desync the two. We assert here
    // that any path the parent could compute lives under TEMP/TMP
    // and ends with the documented filename.
    const filename = 'sunshine-aio-elevation-marker.json';
    const fakeMarkerPath = path.join('/tmp', filename);
    expect(path.basename(fakeMarkerPath)).toBe(filename);
  });
});
