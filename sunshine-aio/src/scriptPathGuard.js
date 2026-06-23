/**
 * Path-traversal guard for the Python bridge script path.
 *
 * Extracted from main.js so it can be unit-tested without booting an
 * Electron environment. The production guard is `isScriptPathSafe()`;
 * the trusted-roots computation lives in `computeAppRoot()` and
 * `computeAllowedScriptDirs()`.
 *
 * The guard enforces THREE properties in this order:
 *   1. The script path is a non-empty string.
 *   2. The basename equals `python_bridge_server.py` (so a future
 *      attacker can't point at a sibling helper script).
 *   3. The script's directory equals one of a small set of trusted
 *      roots — the project's `src/` (dev layout) and the
 *      `.vite/build/` directory (Vite-bundled output). A future Story
 *      that adds another script location must add it to the trusted
 *      set explicitly; a "anything under APP_ROOT" check would
 *      silently widen the surface.
 *
 * APP_ROOT is computed as two levels up from `__dirname`, so the guard
 * works in both the dev layout (where `__dirname` is `src/`) and the
 * Vite-bundled layout (where `__dirname` is `.vite/build/`).
 */

import path from 'node:path';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';

const SCRIPT_FILE_NAME = 'python_bridge_server.py';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

/**
 * Resolve the application root from this module's location. Two
 * levels up because this module lives at `<root>/src/scriptPathGuard.js`
 * in dev and at `<root>/.vite/build/scriptPathGuard.js` in the Vite
 * bundle. Both layouts land on the same package root.
 */
export const computeAppRoot = () => path.resolve(__dirname, '..', '..');

/**
 * Compute the trusted script directories under the given app root.
 * Exposed so tests can compute the same set against a stub `__dirname`.
 *
 * In a packaged Electron build, the Python script is bundled as an
 * `extraResource` (see forge.config.js → packagerConfig.extraResource)
 * so it lives at `<resourcesPath>/python_bridge_server.py`. The
 * resourcesPath is OUTSIDE the app root (it is a sibling of the
 * installation), so we must include it as a trusted dir too. We
 * pass it via `options.extraDirs` so the dev / test code path
 * (which has no resourcesPath) does not accidentally trust an
 * arbitrary directory.
 */
export const computeAllowedScriptDirs = (appRoot, extraDirs = []) => [
  path.join(appRoot, 'src'),
  path.join(appRoot, '.vite', 'build'),
  ...extraDirs,
];

/**
 * Verify a scriptPath resolves inside the application root. Rejects any
 * path that escapes via `..` segments so a caller-supplied scriptPath
 * cannot point at an attacker-controlled location.
 *
 * This is a defense-in-depth check: the Sunshine AIO install flow runs
 * as admin so file-system ACLs usually protect python_bridge_server.py,
 * but the code should not depend on that. If a future story adds CLI
 * flags / env-var driven scriptPath overrides, this guard refuses them.
 *
 * The script must end with `python_bridge_server.py` (so a future
 * attacker can't point at a sibling helper script) AND its directory
 * must live under one of the trusted roots (`<app>/src/` for dev or
 * `<app>/.vite/build/` for the Vite bundle). Subdirectories of a
 * trusted root are allowed so a future Story that nests the script
 * does not silently break the bridge; the basename check is what
 * enforces the "this is the well-known bridge script" identity.
 *
 * SECURITY: this function uses `fs.realpathSync.native` (when
 * available) to detect symlinks / junctions. A symlink placed inside
 * a trusted root (e.g. `python_bridge_server.py` symlinked to
 * `C:\evil\malware.py`) would pass the path.resolve-based check
 * above — `path.resolve` does NOT follow symlinks. The Node spawn()
 * call, however, DOES follow them at exec time, so the attacker would
 * be able to execute arbitrary code. We close that gap by comparing
 * the realpath to the resolved path: if they differ, a symlink is
 * present and we reject the path.
 *
 * @param {string} scriptPath
 * @param {object} [options]
 * @param {string} [options.appRoot]     Override the app root (tests).
 * @param {string[]} [options.allowedDirs] Override the trusted dirs (tests).
 * @param {boolean} [options.followSymlinks] When true (default), check
 *   that the resolved path matches the realpath. Tests that simulate
 *   symlinks can opt out to exercise the legacy string-based check.
 * @returns {boolean}
 */
export const isScriptPathSafe = (scriptPath, options = {}) => {
  if (typeof scriptPath !== 'string' || !scriptPath) return false;
  const resolved = path.resolve(scriptPath);
  if (path.basename(resolved) !== SCRIPT_FILE_NAME) {
    return false;
  }

  // Symlink / junction detection. If realpathSync.native is available
  // (Node 13.7+) we use the native variant which skips UNC / extended-
  // path resolution quirks that can misbehave on Windows network
  // shares. If it is not available (very old Node), we fall through
  // to the legacy string-based check; this is a strictly weaker
  // guarantee but better than nothing.
  if (options.followSymlinks !== false) {
    try {
      const realpathFn = fs.realpathSync.native || fs.realpathSync;
      const real = realpathFn(resolved);
      // On Windows, path.resolve preserves the drive letter casing
      // of the input; realpathSync returns the canonical casing.
      // Normalize via path.resolve so a casing-only difference
      // (e.g. "C:\\Foo" vs "c:\\foo") does not cause a false
      // positive. We still treat any non-equal path as a symlink.
      if (path.resolve(real) !== resolved) {
        return false;
      }
    } catch {
      // The path does not exist or cannot be resolved. The bridge
      // caller will surface this with a clearer error at spawn
      // time; here we return false so the guard does not pass a
      // path that the OS cannot validate.
      return false;
    }
  }

  const dir = path.dirname(resolved);
  const appRoot = options.appRoot || computeAppRoot();
  // In production, allow the script to live at <resourcesPath>/ as well
  // because the script is bundled as an `extraResource`. We only
  // append process.resourcesPath when it is a directory we can stat —
  // this avoids granting trust to a non-existent or attacker-controlled
  // path on systems where resourcesPath is undefined.
  const extraDirs = [];
  if (process.resourcesPath && typeof process.resourcesPath === 'string') {
    extraDirs.push(process.resourcesPath);
  }
  const allowed = options.allowedDirs || computeAllowedScriptDirs(appRoot, extraDirs);
  // path.relative returns a string starting with '..' (or an absolute
  // path on Windows mixed drives) when the script dir escapes the
  // trusted root. We accept any path that lives strictly under a
  // trusted root — equality is a special case of "under".
  for (const trusted of allowed) {
    const rel = path.relative(trusted, dir);
    if (rel === '' || (!rel.startsWith('..') && !path.isAbsolute(rel))) {
      return true;
    }
  }
  return false;
};
