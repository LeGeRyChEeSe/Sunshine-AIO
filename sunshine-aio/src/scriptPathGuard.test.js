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
import fs from 'node:fs';
import os from 'node:os';

import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import { computeAllowedScriptDirs, computeAppRoot, isScriptPathSafe } from './scriptPathGuard.js';

const FAKE_APP_ROOT = path.resolve('/fake', 'app');

/**
 * The current isScriptPathSafe implementation uses fs.realpathSync to
 * detect symlinks. Tests need to pass real on-disk paths for the
 * "accepts" cases; the "rejects" cases can use synthetic strings
 * (realpathSync will throw on a non-existent path and the guard
 * returns false). To support both styles, the helper below creates a
 * throwaway directory tree under os.tmpdir() and yields a pair of
 * {appRoot, allowedDirs} for use with the "accepts" tests.
 */
const makeTempAppRoot = () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'saio-scriptguard-'));
  fs.mkdirSync(path.join(root, 'src'), { recursive: true });
  fs.mkdirSync(path.join(root, '.vite', 'build'), { recursive: true });
  // Create the well-known bridge script in both layouts so the
  // realpathSync check has a real file to resolve.
  fs.writeFileSync(path.join(root, 'src', 'python_bridge_server.py'), '');
  fs.writeFileSync(path.join(root, '.vite', 'build', 'python_bridge_server.py'), '');
  return root;
};

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

  it('appends extraDirs when provided (production extraResource path)', () => {
    // The packaged build bundles the script at
    // <resourcesPath>/python_bridge_server.py. The computeAllowed
    // helper must include any caller-supplied extraDirs so the guard
    // accepts the production layout.
    const extra = '/resources';
    const dirs = computeAllowedScriptDirs(FAKE_APP_ROOT, [extra]);
    expect(dirs).toContain(extra);
  });
});

describe('isScriptPathSafe', () => {
  let tempRoot;
  beforeEach(() => {
    tempRoot = makeTempAppRoot();
  });
  afterEach(() => {
    if (tempRoot && fs.existsSync(tempRoot)) {
      fs.rmSync(tempRoot, { recursive: true, force: true });
    }
  });

  it('rejects empty / non-string inputs', () => {
    const allowed = computeAllowedScriptDirs(tempRoot);
    expect(isScriptPathSafe('', { appRoot: tempRoot, allowedDirs: allowed })).toBe(false);
    expect(isScriptPathSafe(null, { appRoot: tempRoot, allowedDirs: allowed })).toBe(false);
    expect(isScriptPathSafe(undefined, { appRoot: tempRoot, allowedDirs: allowed })).toBe(false);
    expect(isScriptPathSafe(42, { appRoot: tempRoot, allowedDirs: allowed })).toBe(false);
  });

  it('accepts the dev layout: <app>/src/python_bridge_server.py', () => {
    const allowed = computeAllowedScriptDirs(tempRoot);
    const devPath = path.join(tempRoot, 'src', 'python_bridge_server.py');
    expect(isScriptPathSafe(devPath, { appRoot: tempRoot, allowedDirs: allowed })).toBe(true);
  });

  it('accepts the Vite-bundled layout: <app>/.vite/build/python_bridge_server.py', () => {
    // This is the regression test for the production-layout bug: the
    // previous single-level APP_ROOT put the trusted root inside
    // `.vite/`, so the Vite-bundled main process could not find its
    // own script. The new guard must accept both layouts.
    const allowed = computeAllowedScriptDirs(tempRoot);
    const vitePath = path.join(tempRoot, '.vite', 'build', 'python_bridge_server.py');
    expect(isScriptPathSafe(vitePath, { appRoot: tempRoot, allowedDirs: allowed })).toBe(true);
  });

  it('rejects a path that escapes the app root via ..', () => {
    const allowed = computeAllowedScriptDirs(tempRoot);
    const evil = path.join(tempRoot, 'src', '..', '..', 'evil', 'python_bridge_server.py');
    expect(isScriptPathSafe(evil, { appRoot: tempRoot, allowedDirs: allowed })).toBe(false);
  });

  it('rejects a script whose basename is not python_bridge_server.py', () => {
    // Defense against a future attacker that points the guard at a
    // sibling helper script inside a trusted directory.
    const allowed = computeAllowedScriptDirs(tempRoot);
    const wrongName = path.join(tempRoot, 'src', 'evil.py');
    // Create the file so the realpathSync check has something to
    // resolve, then assert the basename check rejects it.
    fs.writeFileSync(wrongName, '');
    expect(isScriptPathSafe(wrongName, { appRoot: tempRoot, allowedDirs: allowed })).toBe(false);
  });

  it('rejects a path inside an untrusted sibling directory', () => {
    const allowed = computeAllowedScriptDirs(tempRoot);
    const otherDir = path.join(tempRoot, 'random');
    fs.mkdirSync(otherDir, { recursive: true });
    const other = path.join(otherDir, 'python_bridge_server.py');
    fs.writeFileSync(other, '');
    expect(isScriptPathSafe(other, { appRoot: tempRoot, allowedDirs: allowed })).toBe(false);
  });

  it('rejects a path that lives under src/ but with a different filename', () => {
    // Defense in depth: a subdirectory of a trusted root is allowed
    // (per the issue's recommendation) BUT only if the basename
    // matches the well-known bridge script name. So a sibling helper
    // script inside src/ is rejected.
    const allowed = computeAllowedScriptDirs(tempRoot);
    const sub = path.join(tempRoot, 'src', 'sub');
    fs.mkdirSync(sub, { recursive: true });
    const wrongNameInSubdir = path.join(sub, 'evil.py');
    fs.writeFileSync(wrongNameInSubdir, '');
    expect(isScriptPathSafe(wrongNameInSubdir, { appRoot: tempRoot, allowedDirs: allowed })).toBe(
      false
    );
  });

  it('rejects a path that escapes the trusted root via ..', () => {
    const allowed = computeAllowedScriptDirs(tempRoot);
    const sneaky = path.join(tempRoot, 'src', '..', 'evil', 'python_bridge_server.py');
    // Resolve so the .. is normalized away; the result is
    // <app>/evil/python_bridge_server.py which is not under either
    // trusted root.
    const resolved = path.resolve(sneaky);
    expect(isScriptPathSafe(resolved, { appRoot: tempRoot, allowedDirs: allowed })).toBe(false);
  });

  it('accepts a Vite-bundled layout relative to a fake .vite/build __dirname', () => {
    // End-to-end test of the production layout: simulate a Vite bundle
    // by computing APP_ROOT from a fake `.vite/build/scriptPathGuard.js`
    // location and checking that the resolved PYTHON_SCRIPT_PATH
    // (sibling to main.js) passes the guard.
    const fakeBundleDir = path.join(tempRoot, '.vite', 'build');
    const fakeAppRoot = path.resolve(fakeBundleDir, '..', '..');
    expect(fakeAppRoot).toBe(tempRoot);
    const allowed = computeAllowedScriptDirs(fakeAppRoot);
    const bundledScript = path.join(fakeBundleDir, 'python_bridge_server.py');
    expect(isScriptPathSafe(bundledScript, { appRoot: fakeAppRoot, allowedDirs: allowed })).toBe(
      true
    );
  });

  it('rejects a symlink whose target escapes the trusted root', () => {
    // SECURITY: the symlink-following attack from the high-severity
    // review. A `python_bridge_server.py` symlink placed inside
    // <app>/src/ but pointing at /tmp/evil.py would pass the legacy
    // string-based guard (path.resolve does not follow symlinks) but
    // fail the realpathSync check. We assert the symlink case is
    // rejected.
    const target = path.join(os.tmpdir(), `evil-${Date.now()}.py`);
    fs.writeFileSync(target, 'malicious');
    const linkPath = path.join(tempRoot, 'src', 'python_bridge_server.py');
    // The real file is in src/ from makeTempAppRoot; overwrite it
    // with a symlink to /tmp/evil.py. Skip on Windows if symlink
    // creation fails (developer-policy may disallow it) — the
    // symlink check is then untested in this environment, which we
    // surface in the assertion message.
    try {
      fs.unlinkSync(linkPath);
      fs.symlinkSync(target, linkPath, 'file');
    } catch (err) {
      // Best-effort cleanup; rethrow as a soft skip via assertion.
      try {
        fs.unlinkSync(target);
      } catch {}
      // Re-create the real file so subsequent tests don't see a
      // broken fixture.
      fs.writeFileSync(linkPath, '');
      // Skip the assertion on platforms where symlinks are not
      // available to the test runner. The symlink path is still
      // exercised in environments that allow it.
      if (err && /EPERM|ENOTSUP|EACCES/.test(err.code || '')) {
        return;
      }
      throw err;
    }
    const allowed = computeAllowedScriptDirs(tempRoot);
    const isSafe = isScriptPathSafe(linkPath, { appRoot: tempRoot, allowedDirs: allowed });
    // Cleanup the symlink + target before asserting.
    try {
      fs.unlinkSync(linkPath);
      fs.unlinkSync(target);
    } catch {}
    expect(isSafe).toBe(false);
  });

  it('rejects a non-existent path', () => {
    // The realpathSync check throws on a non-existent path; the guard
    // catches that and returns false rather than passing a path the
    // OS cannot validate.
    const allowed = computeAllowedScriptDirs(tempRoot);
    const ghost = path.join(tempRoot, 'src', 'python_bridge_server.py');
    fs.unlinkSync(ghost);
    expect(isScriptPathSafe(ghost, { appRoot: tempRoot, allowedDirs: allowed })).toBe(false);
  });
});
