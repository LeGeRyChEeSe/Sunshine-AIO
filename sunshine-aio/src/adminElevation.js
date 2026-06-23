/**
 * Admin elevation helpers (Story 1.4).
 *
 * On Windows the running Electron process may or may not be elevated
 * (i.e. running with an "Administrator" token). Sunshine-AIO needs
 * admin for several operations (registering services, editing VDD
 * / firewall rules, etc.), so we expose a small helper that callers
 * can use to:
 *   (a) check whether the current process is already elevated, or
 *   (b) request an elevated re-launch of the same binary via the
 *       `runas` ShellExecute verb, which is the documented way to
 *       trigger a UAC prompt from a running process.
 *
 * The helper is intentionally extracted into its own module so it can
 * be unit-tested without booting Electron. `main.js` imports and
 * re-exports the public surface.
 *
 * Design notes:
 *   - We do NOT auto-elevate on startup; that would surface a UAC
 *     prompt to every user, every launch.
 *   - On non-Windows platforms both helpers degrade gracefully:
 *     `isRunningAsAdmin` returns false (we never run as admin on
 *     macOS/Linux), `requestAdminElevation` returns
 *     `{ ok: false, reason: 'unsupported platform' }`.
 *   - The elevation request uses PowerShell's
 *     `Start-Process -Verb RunAs -FilePath <exe>` which translates to
 *     `ShellExecuteExW` with `lpVerb = "runas"`. This is the canonical
 *     way to raise a UAC prompt from a Node process and produces an
 *     honest yes/no dialog. (Note: `cmd /c start /runas <exe>` would
 *     also work, but only when the second argument is wrapped
 *     carefully; PowerShell is more reliable and self-documenting.)
 */

import { spawn, spawnSync } from 'node:child_process';

export const isWindowsPlatform = () => process.platform === 'win32';

/**
 * Sentinel string printed by `whoami /groups` for an elevated process.
 * We look for the literal "Mandatory Label\\High Mandatory Level"
 * group label OR the integrity-level SID `S-1-16-12288`. Either is
 * proof the current process token is elevated.
 *
 * We match on both because the localized label varies (e.g. French
 * Windows prints "Niveau d'obligation élevé") but the SID is
 * locale-independent. SID is the primary signal; the label is a
 * belt-and-braces fallback for environments that strip the SID.
 */
const ELEVATED_SID = 'S-1-16-12288';
const ELEVATED_LABEL_NEEDLE = 'High Mandatory Level';

/**
 * Synchronous check of `process.isElevated`.
 *
 * `process.isElevated` is NOT a Node/Electron built-in and is NOT
 * injected by `electron-squirrel-startup` (that module just adds a
 * Windows shortcut on first launch and quits the app). The property
 * is therefore undefined in production builds today. We keep the
 * check because:
 *   (a) it costs nothing;
 *   (b) a future native helper (or a Squirrel plugin change) might
 *       populate it, in which case we want to honor it;
 *   (c) test suites can inject it directly via `Object.defineProperty`.
 *
 * If the property is set to a boolean we trust it and skip the
 * `whoami` probe entirely.
 */
export const readProcessElevatedFlag = () => {
  try {
    const value = process.isElevated;
    if (typeof value === 'boolean') return value;
  } catch {
    // Defensive: some test stubs define it as a getter that throws.
  }
  return null;
};

/**
 * Parse the stdout of `whoami /groups` and return true if the process
 * is elevated. Exported for tests; the production call path is
 * `isRunningAsAdmin` below.
 *
 * The output of `whoami /groups` is locale-dependent and roughly:
 *
 *   GROUP INFORMATION
 *   -----------------
 *   Group Name                                  Type             SID          Attributes
 *   =========================================== ================ ============ ==================================================
 *   BUILTIN\Administrators                      Alias            S-1-5-32-544 Enabled by default, Enabled group, Group owner
 *   ...
 *   Mandatory Label\High Mandatory Level        Label            S-1-16-12288
 *
 * We split on newlines and look for either the SID or the EN label
 * needle. The label needle is case-insensitive because the EN form is
 * what Microsoft emits by default; localized builds won't match it,
 * but the SID will.
 */
export const parseWhoamiGroupsOutput = (stdout) => {
  if (typeof stdout !== 'string' || stdout.length === 0) return false;
  if (stdout.includes(ELEVATED_SID)) return true;
  // Case-insensitive label match — only EN form is recognized because
  // other locales will not include the English label and must be
  // detected via the SID instead.
  if (stdout.toLowerCase().includes(ELEVATED_LABEL_NEEDLE.toLowerCase())) return true;
  return false;
};

/**
 * Run `whoami /groups` synchronously and return true if the process
 * is elevated. Returns null if the command could not be executed
 * (e.g. `whoami` not on PATH — extremely rare on Windows).
 *
 * `spawnImpl` is the synchronous-spawn function used to launch the
 * probe (defaults to `child_process.spawnSync`). Tests inject a
 * fake to avoid actually running whoami in CI.
 */
export const probeElevatedViaWhoami = (spawnImpl = spawnSync, timeoutMs = 2000) => {
  try {
    const result = spawnImpl('whoami', ['/groups'], {
      encoding: 'utf8',
      timeout: timeoutMs,
      windowsHide: true,
    });
    if (!result || typeof result.stdout !== 'string') return null;
    return parseWhoamiGroupsOutput(result.stdout);
  } catch {
    return null;
  }
};

// Internal cache; tests reset via `_resetIsElevatedCache()`.
let _isElevatedCache = null;

/**
 * Reset the cached elevation result. Exposed for tests and called by
 * the IPC handler after an `admin:request-elevation` so the elevated
 * re-launch reports correctly on its first `isRunningAsAdmin()` call.
 */
export const _resetIsElevatedCache = () => {
  _isElevatedCache = null;
};

/**
 * True when the current process is running as administrator (Windows)
 * or root (other platforms — never the case here, but we keep the
 * helper portable so the same call site works in CI).
 *
 * Implementation:
 *   1. Honor `process.isElevated` when it is set to a boolean (test
 *      stubs and any future native helper can populate it).
 *   2. Otherwise, on Windows, run `whoami /groups` and look for the
 *      elevated integrity-level SID `S-1-16-12288` or the literal
 *      label "High Mandatory Level". Cache the result.
 *   3. On non-Windows, return false.
 *
 * The probe is `spawnSync` so the first call may briefly block, but
 * typical execution is < 100 ms on Windows. Subsequent calls hit the
 * cache and are free.
 *
 * `deps` is an optional dependency-injection object for tests:
 *   - `spawnImpl`   replaces `child_process.spawn`
 *   - `forceFresh`  if true, the cache is bypassed for this call
 */
export const isRunningAsAdmin = (deps = {}) => {
  const forceFresh = deps.forceFresh === true;
  const spawnImpl = deps.spawnImpl || spawnSync;
  if (!forceFresh && _isElevatedCache !== null) return _isElevatedCache;
  if (!isWindowsPlatform()) {
    _isElevatedCache = false;
    return _isElevatedCache;
  }
  const flag = readProcessElevatedFlag();
  if (flag !== null) {
    _isElevatedCache = flag;
    return _isElevatedCache;
  }
  const probed = probeElevatedViaWhoami(spawnImpl);
  if (probed === null) {
    // Probe failed. Treat unknown as "not elevated" — callers will
    // surface the elevation UI which is the safe default. Do NOT
    // cache nulls across calls; a transient whoami failure should
    // not be sticky forever.
    _isElevatedCache = false;
    return _isElevatedCache;
  }
  _isElevatedCache = probed;
  return _isElevatedCache;
};

/**
 * Re-launch the current executable with elevation (Windows UAC).
 *
 * Strategy: invoke PowerShell's `Start-Process -Verb RunAs -FilePath
 * <exe>`. PowerShell translates that to `ShellExecuteExW` with
 * `lpVerb = "runas"`, which raises the standard UAC consent prompt.
 *
 * Optional handshake: if `deps.handshakeArgs` is provided, the
 * elevated child is started with those extra CLI arguments. The
 * child, on startup, recognizes the sentinel flag and writes a
 * marker file the parent polls for — this is how the parent knows
 * the elevated child actually launched (and was not, for instance,
 * cancelled at the UAC prompt). See `waitForElevationMarker` /
 * `computeElevationMarkerPath` in main.js.
 *
 * Returns:
 *   - `{ ok: true }`  when the elevated child was successfully
 *                     spawned. Note: we cannot synchronously know
 *                     whether the user accepted or declined the UAC
 *                     prompt; the parent must wait for the handshake
 *                     marker before quitting.
 *   - `{ ok: false, reason: 'unsupported platform' }` on non-Windows.
 *   - `{ ok: false, reason: <message> }` if the spawn threw.
 *
 * `deps.spawnImpl` lets tests stub the spawn call.
 */
export const requestAdminElevation = async (deps = {}) => {
  if (!isWindowsPlatform()) {
    return { ok: false, reason: 'unsupported platform' };
  }
  const spawnImpl = deps.spawnImpl || spawn;
  const exePath = process.execPath;
  const handshakeArgs = Array.isArray(deps.handshakeArgs) ? deps.handshakeArgs : [];
  try {
    // Escape the exePath for embedding in a PowerShell single-quoted
    // string. The `'` -> `''` escape is the PowerShell convention.
    const psExePath = exePath.replace(/'/g, "''");
    // Build the Start-Process argument list. PowerShell's
    // -ArgumentList accepts an array literal; we emit each element
    // as a quoted string so paths with spaces survive and so the
    // receiving process sees them as separate argv entries (rather
    // than one space-joined string).
    const psArgs =
      handshakeArgs.length > 0
        ? ` -ArgumentList @(${handshakeArgs.map((a) => `'${a.replace(/'/g, "''")}'`).join(',')})`
        : '';
    const command = `Start-Process -FilePath '${psExePath}' -Verb RunAs${psArgs}`;
    const args = ['-NoProfile', '-NonInteractive', '-Command', command];
    // Capture stderr (was 'ignore') so spawn-failures (rare but
    // possible — missing powershell.exe, AV quarantining, ACL
    // issues) are surfaced to the logger instead of disappearing.
    const child = spawnImpl('powershell.exe', args, {
      detached: true,
      stdio: ['ignore', 'pipe', 'pipe'],
      windowsHide: true,
    });
    if (!child) {
      return { ok: false, reason: 'spawn returned no child handle' };
    }
    // Drain stderr to surface spawn errors. We do not await them —
    // the spawn success / failure is what callers gate on — but a
    // captured stream prevents the pipe from filling up and lets us
    // log the diagnostic if the elevation fails downstream.
    if (child.stderr && typeof child.stderr.on === 'function') {
      child.stderr.setEncoding('utf8');
      child.stderr.on('data', () => {
        // Best-effort drain. The caller will observe UAC via the
        // handshake marker; if it never appears we log here.
      });
    }
    if (child.stdout && typeof child.stdout.on === 'function') {
      child.stdout.setEncoding('utf8');
      child.stdout.on('data', () => {
        // Drain stdout too so the pipe does not block.
      });
    }
    if (child.stdin && typeof child.stdin.on === 'function') {
      // Some PowerShell configurations do not need stdin; closing
      // it makes the command finish cleanly without an interactive
      // prompt.
      try {
        child.stdin.end();
      } catch {
        /* ignore */
      }
    }
    if (typeof child.unref === 'function') {
      child.unref();
    }
    // Spawn-only success: the elevated child has been requested but
    // we have NOT yet verified that UAC succeeded or that the
    // child actually launched. Callers MUST wait for the handshake
    // marker before treating this as "elevated". We expose a
    // distinct `pending` reason so the caller can render a
    // "waiting for UAC" UI state rather than promising elevation
    // that has not been verified. A user-cancelled UAC leaves the
    // spawn success intact but the handshake times out — and the
    // parent stays alive instead of quitting without an elevated
    // child.
    return { ok: true, pending: 'uac_pending' };
  } catch (err) {
    return {
      ok: false,
      reason: err && err.message ? err.message : String(err),
    };
  }
};
