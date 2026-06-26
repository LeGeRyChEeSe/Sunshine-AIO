/**
 * Tests for the scriptPathGuard module — the path-traversal guard used
 * by main.js to ensure the Python bridge spawns a script inside one of
 * the trusted roots (`<app>/src/` for dev, `<app>/.vite/build/` for the
 * Vite bundle).
 *
 * These tests do not boot Electron; the guard is intentionally
 * extracted into its own module so it can be exercised in isolation.
 */

import path from 'node:path';

import { describe, expect, it } from 'vitest';

import { computeAllowedScriptDirs, computeAppRoot, isScriptPathSafe } from './scriptPathGuard.js';

const FAKE_APP_ROOT = path.resolve('/fake', 'app');

describe('computeAppRoot', () => {
  it('returns an absolute path two levels up from the guard module', () => {
    // The guard module lives at <root>/src/scriptPathGuard.js in dev
    // and <root>/.vite/build/scriptPathGuard.js in the Vite bundle.
    // Both layouts must resolve to the same package root, so we
    // assert the path is absolute and ends at the package root, not
    // at the src/ or .vite/build/ directory itself.
    const root = computeAppRoot();
    expect(path.isAbsolute(root)).toBe(true);
    // Compute the guard's directory via the same path-from-URL logic
    // the module uses internally, then verify `root` is two levels up.
    // We deliberately avoid importing the module's private __dirname
    // to keep the test resilient to the helper file's own path
    // structure (it may live under .vite/build/ in production).
    const guardModulePath = new URL(import.meta.url).pathname.replace(/^\//, '');
    const guardDir = path.dirname(guardModulePath);
    expect(path.resolve(root)).toBe(path.resolve(guardDir, '..', '..'));
  });
});

describe('computeAllowedScriptDirs', () => {
  it('returns the dev src/ directory and the Vite .vite/build/ directory', () => {
    const dirs = computeAllowedScriptDirs(FAKE_APP_ROOT);
    expect(dirs).toEqual([
      path.join(FAKE_APP_ROOT, 'src'),
      path.join(FAKE_APP_ROOT, '.vite', 'build'),
    ]);
  });
});

describe('isScriptPathSafe', () => {
  it('rejects empty / non-string inputs', () => {
    expect(
      isScriptPathSafe('', {
        appRoot: FAKE_APP_ROOT,
        allowedDirs: computeAllowedScriptDirs(FAKE_APP_ROOT),
      })
    ).toBe(false);
    expect(
      isScriptPathSafe(null, {
        appRoot: FAKE_APP_ROOT,
        allowedDirs: computeAllowedScriptDirs(FAKE_APP_ROOT),
      })
    ).toBe(false);
    expect(
      isScriptPathSafe(undefined, {
        appRoot: FAKE_APP_ROOT,
        allowedDirs: computeAllowedScriptDirs(FAKE_APP_ROOT),
      })
    ).toBe(false);
    expect(
      isScriptPathSafe(42, {
        appRoot: FAKE_APP_ROOT,
        allowedDirs: computeAllowedScriptDirs(FAKE_APP_ROOT),
      })
    ).toBe(false);
  });

  it('accepts the dev layout: <app>/src/python_bridge_server.py', () => {
    const allowed = computeAllowedScriptDirs(FAKE_APP_ROOT);
    const devPath = path.join(FAKE_APP_ROOT, 'src', 'python_bridge_server.py');
    expect(isScriptPathSafe(devPath, { appRoot: FAKE_APP_ROOT, allowedDirs: allowed })).toBe(true);
  });

  it('accepts the Vite-bundled layout: <app>/.vite/build/python_bridge_server.py', () => {
    // This is the regression test for the production-layout bug: the
    // previous single-level APP_ROOT put the trusted root inside
    // `.vite/`, so the Vite-bundled main process could not find its
    // own script. The new guard must accept both layouts.
    const allowed = computeAllowedScriptDirs(FAKE_APP_ROOT);
    const vitePath = path.join(FAKE_APP_ROOT, '.vite', 'build', 'python_bridge_server.py');
    expect(isScriptPathSafe(vitePath, { appRoot: FAKE_APP_ROOT, allowedDirs: allowed })).toBe(true);
  });

  it('rejects a path that escapes the app root via ..', () => {
    const allowed = computeAllowedScriptDirs(FAKE_APP_ROOT);
    const evil = path.join(FAKE_APP_ROOT, 'src', '..', '..', 'evil', 'python_bridge_server.py');
    expect(isScriptPathSafe(evil, { appRoot: FAKE_APP_ROOT, allowedDirs: allowed })).toBe(false);
  });

  it('rejects a script whose basename is not python_bridge_server.py', () => {
    // Defense against a future attacker that points the guard at a
    // sibling helper script inside a trusted directory.
    const allowed = computeAllowedScriptDirs(FAKE_APP_ROOT);
    const wrongName = path.join(FAKE_APP_ROOT, 'src', 'evil.py');
    expect(isScriptPathSafe(wrongName, { appRoot: FAKE_APP_ROOT, allowedDirs: allowed })).toBe(
      false
    );
  });

  it('rejects a path inside an untrusted sibling directory', () => {
    const allowed = computeAllowedScriptDirs(FAKE_APP_ROOT);
    const other = path.join(FAKE_APP_ROOT, 'random', 'python_bridge_server.py');
    expect(isScriptPathSafe(other, { appRoot: FAKE_APP_ROOT, allowedDirs: allowed })).toBe(false);
  });

  it('rejects a path that lives under src/ but with a different filename', () => {
    // Defense in depth: a subdirectory of a trusted root is allowed
    // (per the issue's recommendation) BUT only if the basename
    // matches the well-known bridge script name. So a sibling helper
    // script inside src/ is rejected.
    const allowed = computeAllowedScriptDirs(FAKE_APP_ROOT);
    const wrongNameInSubdir = path.join(FAKE_APP_ROOT, 'src', 'sub', 'evil.py');
    expect(
      isScriptPathSafe(wrongNameInSubdir, { appRoot: FAKE_APP_ROOT, allowedDirs: allowed })
    ).toBe(false);
  });

  it('rejects a path that escapes the trusted root via ..', () => {
    const allowed = computeAllowedScriptDirs(FAKE_APP_ROOT);
    const sneaky = path.join(FAKE_APP_ROOT, 'src', '..', 'evil', 'python_bridge_server.py');
    // Resolve so the .. is normalized away; the result is
    // <app>/evil/python_bridge_server.py which is not under either
    // trusted root.
    const resolved = path.resolve(sneaky);
    expect(isScriptPathSafe(resolved, { appRoot: FAKE_APP_ROOT, allowedDirs: allowed })).toBe(
      false
    );
  });

  it('accepts a Vite-bundled layout relative to a fake .vite/build __dirname', () => {
    // End-to-end test of the production layout: simulate a Vite bundle
    // by computing APP_ROOT from a fake `.vite/build/scriptPathGuard.js`
    // location and checking that the resolved PYTHON_SCRIPT_PATH
    // (sibling to main.js) passes the guard.
    const fakeBundleDir = path.join(FAKE_APP_ROOT, '.vite', 'build');
    const fakeAppRoot = path.resolve(fakeBundleDir, '..', '..');
    expect(fakeAppRoot).toBe(FAKE_APP_ROOT);
    const allowed = computeAllowedScriptDirs(fakeAppRoot);
    const bundledScript = path.join(fakeBundleDir, 'python_bridge_server.py');
    expect(isScriptPathSafe(bundledScript, { appRoot: fakeAppRoot, allowedDirs: allowed })).toBe(
      true
    );
  });
});
