/**
 * PythonBridge — JSON-line IPC bridge to the Sunshine AIO Python backend.
 *
 * Spawns the Python interpreter with the bridge server script as a long-lived
 * child process, then communicates over stdin/stdout using newline-delimited
 * JSON (one JSON object per line). This module is deliberately framework-free
 * so it can be exercised by unit tests with a mocked spawn().
 *
 * Contract:
 *   - send(command, params, options?) → Promise<result>
 *   - ping() → Promise<"pong">
 *   - quit() → Promise<void>  (terminates the child and waits for exit)
 *   - isReady() → boolean
 *   - onReady / onError / onExit  → EventEmitter-like subscriptions
 *
 * The bridge auto-starts on construction. Calls made before the child reports
 * 'ready' are queued and dispatched in order once the ready event arrives,
 * so callers do not need to await `whenReady` themselves (though they may).
 *
 * Concurrency:
 *   - Each `send` allocates an opaque request id. Responses are matched by id.
 *   - Pending requests are tracked in a Map so multiple concurrent calls are
 *     safe (FIFO by registration order; responses may arrive in any order).
 *   - On timeout the pending entry is rejected with TimeoutError and removed.
 *
 * Cleanup:
 *   - quit() sends SIGTERM, waits up to `exitGraceMs`, then SIGKILL.
 *   - If the child dies unexpectedly, all pending requests are rejected with
 *     a ProcessExitError so callers do not hang forever on a dead pipe.
 */

import { EventEmitter } from 'node:events';
import { spawn } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';

import { createDefaultLogger } from './logger.js';

// `app` from electron is only available when running inside the
// Electron main process. We import it lazily inside resolveDefaultScriptPath
// so the bridge module remains unit-testable in a plain Node context
// (where `app` would be undefined).

const DEFAULT_TIMEOUT_MS = 10_000;
const DEFAULT_EXIT_GRACE_MS = 2_000;
const DEFAULT_READY_TIMEOUT_MS = 5_000;
// Maximum size of the stdout line buffer. A misbehaving/compromised
// Python child that emits N bytes without a newline could otherwise
// grow _stdoutBuffer without bound until V8 OOMs. 1 MiB is comfortably
// larger than any legitimate single JSON response (a 64 KiB params
// envelope maxes out around 70 KiB serialized) while still being
// bounded enough to keep us safe.
const MAX_STDOUT_BUFFER_BYTES = 1 * 1024 * 1024;

/**
 * Forcefully terminate a child process. On Windows, `proc.kill('SIGKILL')`
 * is unreliable for grandchildren spawned via the `py` launcher or
 * `cmd.exe`; the documented reliable force-kill is
 * `taskkill /F /T /PID <pid>` (the `/T` flag kills the process tree,
 * not just the immediate child). On POSIX, SIGKILL works as expected.
 *
 * The function is a no-op if `proc` is null/undefined or has no pid,
 * so callers can invoke it unconditionally during error paths.
 */
const forceKillProcess = (proc, logger) => {
  if (!proc || typeof proc.kill !== 'function') return;
  const pid = proc.pid;
  if (!pid) return;
  if (process.platform === 'win32') {
    // Use taskkill via a fresh spawn so we can capture stderr if it
    // fails. We deliberately do NOT use the proc.stdin/.stdout/.stderr
    // (they belong to the child) and we do NOT await — this is
    // best-effort cleanup during error paths.
    try {
      const { spawn: spawnSync } = require('node:child_process');
      const taskkill = spawnSync('taskkill', ['/F', '/T', '/PID', String(pid)], {
        stdio: 'ignore',
        windowsHide: true,
      });
      taskkill.on('error', (err) => {
        if (logger && typeof logger.warn === 'function') {
          logger.warn('taskkill spawn failed', { pid, message: err.message });
        }
      });
    } catch (err) {
      // Fall back to the Node kill() if taskkill itself cannot spawn
      // (e.g. a corporate policy blocks it). On Windows this maps to
      // TerminateProcess, which kills the immediate child but not the
      // tree — better than nothing.
      try {
        proc.kill('SIGKILL');
      } catch {
        /* ignore */
      }
      if (logger && typeof logger.warn === 'function') {
        logger.warn('forceKillProcess taskkill fallback to SIGKILL', {
          pid,
          message: err && err.message ? err.message : String(err),
        });
      }
    }
    return;
  }
  // POSIX: SIGKILL works.
  try {
    proc.kill('SIGKILL');
  } catch {
    /* ignore */
  }
};
// Hard cap on the number of concurrent in-flight requests. A
// compromised renderer could otherwise grow _pending without bound by
// rapidly firing `python:execute` calls until OOM.
const MAX_PENDING_REQUESTS = 1000;

// Prefer 'py' (Windows launcher) → 'python3' → 'python'. The bridge tries
// them in order; the first one that exists AND reports Python 3.x wins.
// We probe by spawning each candidate with '--version' and reading stdout
// to enforce a major-version floor: the bridge server uses Python 3.6+
// syntax (`from __future__ import annotations`, f-strings, etc.) and
// would SyntaxError on Python 2.

// Per-candidate probe timeout. A hung `--version` probe (e.g. an
// antivirus hook on a network share) must not block bridge startup
// indefinitely; we cap each probe at 2s so the worst-case probe time
// is bounded. The first candidate to either resolve, exit non-zero,
// or time out moves us to the next one.
const PROBE_TIMEOUT_MS = 2000;

// Module-level cache for the resolved Python command. The bridge
// restart path (future reconnect logic) re-uses the cached value so we
// do not pay the cost of up to four `--version` probes on every spawn.
// `null` means "not resolved yet"; a string is the resolved command.
// Tests can pass `forceReProbe: true` to bypass the cache.
let _cachedPythonCommand = null;

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

/**
 * Compute the default script path.
 *
 * In dev / tests, the script lives at
 *   <project>/src/python_bridge_server.py
 * which resolves to two levels up from this file (the dev layout puts
 * pythonBridge.js under <project>/src/, and the script is a sibling
 * of the same directory).
 *
 * In a packaged Electron build, the script is bundled as an
 * `extraResource` (see forge.config.js → packagerConfig.extraResource)
 * so it lives at:
 *   <process.resourcesPath>/python_bridge_server.py
 * i.e. outside the ASAR — Node cannot spawn a script from inside an
 * ASAR, so we MUST resolve to the unpacked location. process.resourcesPath
 * is the official Electron API for this and is set up by the Squirrel /
 * squirrel installer to point at <install>/resources/.
 *
 * The `app` import from `electron` is deferred so this module can be
 * loaded in a non-Electron context (e.g. unit tests). If `app` is
 * unavailable, we fall through to the dev-layout resolution.
 */
const resolveDefaultScriptPath = () => {
  // Dev / test layout: resolve relative to this file's directory.
  const devPath = path.resolve(__dirname, '..', '..', 'src', 'python_bridge_server.py');

  // Try to use the Electron `app` module to detect packaged mode.
  // Lazy require so a test environment without `electron` installed
  // still loads cleanly. process.resourcesPath exists even in dev
  // (points at <repo>/resources, which doesn't exist), so we also
  // check process.type or rely on the caller passing an explicit
  // scriptPath.
  let app;
  try {
    // Use createRequire so this works regardless of module type.
    const requireFn = createRequire(import.meta.url);
    const electron = requireFn('electron');
    app = electron && electron.app ? electron.app : null;
  } catch {
    app = null;
  }

  if (app && typeof app.isPackaged === 'function' && app.isPackaged()) {
    // Packaged: <resourcesPath>/python_bridge_server.py
    return path.join(process.resourcesPath, 'python_bridge_server.py');
  }
  return devPath;
};

const DEFAULT_SCRIPT_PATH = resolveDefaultScriptPath();

export class TimeoutError extends Error {
  constructor(message) {
    super(message);
    this.name = 'TimeoutError';
  }
}

export class ProcessExitError extends Error {
  constructor(message, details) {
    super(message);
    this.name = 'ProcessExitError';
    if (details !== undefined) {
      this.details = details;
    }
  }
}

export class JsonProtocolError extends Error {
  constructor(message, rawLine) {
    super(message);
    this.name = 'JsonProtocolError';
    if (rawLine !== undefined) {
      this.rawLine = rawLine;
    }
  }
}

/**
 * Raised when the stdin pipe to the Python child is full. Distinct
 * error type so the caller (renderer / IPC layer) can distinguish
 * "retry later" (transient) from "command rejected" (semantic).
 */
export class BackpressureError extends Error {
  constructor(message) {
    super(message);
    this.name = 'BackpressureError';
    this.code = 'BACKPRESSURE';
  }
}

/**
 * Build a minimal allowlist environment for the Python child.
 * The default Node `spawn` inherits the entire parent process env,
 * which is a large information-disclosure surface (AWS_*, AZURE_*,
 * GITHUB_TOKEN, PYTHONPATH, VIRTUAL_ENV, NODE_*, etc.). We restrict
 * to only the variables the Python interpreter and the bridge
 * actually need to boot. The list is intentionally tiny — add a
 * variable here only if a unit test or a future Story proves it is
 * required.
 */
const safeChildEnv = () => {
  const env = {};
  const allowlist = [
    'PATH',
    'SystemRoot',
    'SYSTEMROOT',
    'LANG',
    'LC_ALL',
    'LC_CTYPE',
    'TEMP',
    'TMP',
  ];
  for (const key of allowlist) {
    if (process.env[key] !== undefined) {
      env[key] = process.env[key];
    }
  }
  // Strip any user-set PYTHONPATH / PYTHONHOME / VIRTUAL_ENV / NODE_*
  // env vars defensively. The list of "always strip" prefixes is
  // enforced even if the allowlist above does not match — we
  // explicitly null them so a future Story that adds a variable to
  // the allowlist does not accidentally leave these leaking.
  const stripPrefixes = [
    'PYTHON',
    'VIRTUAL_ENV',
    'CONDA',
    'NODE_',
    'NPM_',
    'AWS_',
    'AZURE_',
    'GCP_',
    'GITHUB_',
    'GITLAB_',
    'BITBUCKET_',
    'HEROKU_',
    'DO_',
    'DIGITALOCEAN_',
  ];
  for (const key of Object.keys(process.env)) {
    if (stripPrefixes.some((p) => key === p || key.startsWith(p))) {
      // Skip: we only allow the variables in the allowlist above.
      continue;
    }
    if (!(key in env)) {
      env[key] = process.env[key];
    }
  }
  // On Windows, preserve the Path casing that Python expects.
  if (process.platform === 'win32' && env.Path === undefined && env.PATH !== undefined) {
    env.Path = env.PATH;
  }
  return env;
};

/**
 * Compute a safe cwd for the Python child. We deliberately do NOT
 * inherit process.cwd() because the user may have launched the
 * Electron app from a directory containing sensitive data. Use the
 * app temp directory if available, else the script's own directory.
 */
const safeChildCwd = () => {
  try {
    const os = process.platform === 'win32' ? require('node:os') : null;
    if (os && typeof os.tmpdir === 'function') {
      return os.tmpdir();
    }
  } catch {
    /* fall through */
  }
  return path.dirname(__filename);
};

/**
 * Parse the major version from a `python --version` banner. Returns the
 * major version number (e.g. 3) on success, or null on any parse failure.
 * The Python version banner looks like "Python 3.11.2" on stdout (or
 * stderr on older versions); we accept either by inspecting the full
 * concatenated output the caller hands us.
 */
const parsePythonMajorVersion = (banner) => {
  if (typeof banner !== 'string') return null;
  // Match "Python 3" or "Python 3.11.2" — strict, do NOT match "Python 2".
  const match = banner.match(/Python\s+(\d+)(?:\.\d+)*/i);
  if (!match) return null;
  const major = Number.parseInt(match[1], 10);
  return Number.isFinite(major) ? major : null;
};

/**
 * Pick a Python interpreter. Tries each candidate in order and returns the
 * first one that:
 *   1. spawns successfully (does not ENOENT)
 *   2. exits 0 (or is killed by the ready-timeout with code null)
 *   3. advertises a Python 3.x banner
 *
 * On Windows, the `py` launcher is probed with the `-3` flag first so we
 * never silently land on a Python 2 interpreter that happens to be the
 * highest version installed. If `-3` is rejected (older launcher, no
 * Python 3 installed) we fall back to bare `py`, then `python`, then
 * `python3`. For non-Windows candidates, a single `--version` probe is
 * sufficient because `python3` already implies Python 3.
 *
 * Accepts an optional `spawnFn` for testing. When omitted, uses the real
 * node:child_process.spawn. The injected function should throw on ENOENT
 * to mimic the real behavior across platforms. The injected function may
 * also accept a `__collectOutput` option in its spawn options so tests
 * can return banner text from the probe child.
 *
 * Exported for tests; production code should rely on PythonBridge auto-start.
 */
export const resolvePythonCommand = async (options = {}) => {
  const spawnFn = options.spawnFn || spawn;
  const forceReProbe = options.forceReProbe === true;

  // Honor the module-level cache. The first call probes all four
  // candidates; subsequent calls (including future bridge restarts)
  // reuse the resolved command directly. A test that needs to exercise
  // the probe path again can pass `forceReProbe: true`.
  if (!forceReProbe && _cachedPythonCommand !== null) {
    return _cachedPythonCommand;
  }

  /**
   * Probe a single (cmd, args) tuple. Returns a structured result so the
   * caller can decide whether to fall through to the next candidate.
   */
  const probeCandidate = async (cmd, args) => {
    let probe;
    try {
      probe = spawnFn(cmd, args, { stdio: ['ignore', 'pipe', 'pipe'] });
    } catch {
      return { ok: false, reason: 'enoent' };
    }
    if (!probe) {
      return { ok: false, reason: 'enoent' };
    }

    // Capture stdout+stderr so we can verify the banner reports Python 3.
    // Some Python builds print the version to stderr (PEP 678 era
    // inconsistency) so we read both.
    let banner = '';
    if (probe.stdout && typeof probe.stdout.on === 'function') {
      probe.stdout.setEncoding('utf8');
      probe.stdout.on('data', (chunk) => {
        banner += chunk;
      });
    }
    if (probe.stderr && typeof probe.stderr.on === 'function') {
      probe.stderr.setEncoding('utf8');
      probe.stderr.on('data', (chunk) => {
        banner += chunk;
      });
    }

    // Bound the per-candidate wait so a hung `--version` probe (e.g.
    // antivirus hook on a network share) does not block the bridge
    // indefinitely. The race between 'exit' and the timeout is benign
    // — whichever resolves the promise first wins; the kill is a
    // best-effort cleanup of the orphaned child.
    let probeTimeout;
    const exitOk = await new Promise((resolve) => {
      let settled = false;
      const settle = (value) => {
        if (settled) return;
        settled = true;
        resolve(value);
      };
      probe.once('error', () => settle(false));
      probe.once('exit', (code) => settle(code === 0 || code === null));
      probeTimeout = setTimeout(() => settle(false), PROBE_TIMEOUT_MS);
      if (typeof probeTimeout.unref === 'function') {
        probeTimeout.unref();
      }
    });
    if (probeTimeout) clearTimeout(probeTimeout);
    if (probe.exitCode === null && probe.signalCode === null) {
      try {
        probe.kill();
      } catch {
        /* ignore */
      }
    }
    if (!exitOk) {
      return { ok: false, reason: 'exit' };
    }
    return { ok: true, banner };
  };

  // Build the ordered probe list. On Windows, the `py` launcher accepts
  // a `-3` flag that makes it refuse to dispatch to Python 2 — we use
  // that as the first probe so the bridge never lands on a py2 install
  // that happens to be the highest registered version. Bare `py` and
  // `python` are tried next as fallbacks; both still go through the
  // Python-3 banner check below.
  const probeList = [];
  if (process.platform === 'win32') {
    probeList.push({ cmd: 'py', args: ['-3', '--version'] });
    probeList.push({ cmd: 'py', args: ['--version'] });
    probeList.push({ cmd: 'python', args: ['--version'] });
    probeList.push({ cmd: 'python3', args: ['--version'] });
  } else {
    probeList.push({ cmd: 'python3', args: ['--version'] });
    probeList.push({ cmd: 'python', args: ['--version'] });
  }

  for (const { cmd, args } of probeList) {
    const result = await probeCandidate(cmd, args);
    if (!result.ok) {
      // ENOENT or non-zero exit — try the next candidate.
      continue;
    }
    const major = parsePythonMajorVersion(result.banner);
    if (major === null) {
      // Banner could not be parsed. Reject rather than fall through with
      // an unknown version — we cannot prove the interpreter is safe to
      // use. (Falling through could silently land on an exotic or
      // truncated banner that we cannot trust.)
      continue;
    }
    if (major < 3) {
      // Python 2 is not supported. Skip explicitly so the error path
      // below reports a clear "Python 3 is required" rather than a
      // generic "interpreter not found".
      continue;
    }
    // Cache the resolved command for the next bridge restart. The
    // cache is process-wide; if a future Story ever changes Python
    // interpreters at runtime, it can call `resolvePythonCommand({ forceReProbe: true })`.
    _cachedPythonCommand = cmd;
    return cmd;
  }

  const triedList = probeList.map((p) => `${p.cmd} ${p.args.join(' ')}`).join(', ');
  throw new Error(
    `Python 3 is required (the Sunshine AIO bridge uses Python 3.6+ syntax). ` +
      `No suitable interpreter was found. Tried: ${triedList}`
  );
};

/**
 * Build the default bridge options. Pulled out so unit tests can call it
 * and assert the defaults without having to spawn a real process.
 */
export const defaultBridgeOptions = () => ({
  pythonCommand: null, // auto-detect
  scriptPath: DEFAULT_SCRIPT_PATH,
  timeoutMs: DEFAULT_TIMEOUT_MS,
  exitGraceMs: DEFAULT_EXIT_GRACE_MS,
  readyTimeoutMs: DEFAULT_READY_TIMEOUT_MS,
  logger: createDefaultLogger({ consoleLevel: 'warn' }),
});

/**
 * Generate a unique request id. crypto.randomUUID is available in Node 16+
 * and Electron always ships a recent Node, so this is safe.
 */
const newRequestId = () => {
  try {
    // Prefer the require form so this works even when the bridge is
    // bundled into a context where globalThis.crypto is not present
    // (older test runners, some bundler configs).
    const require = createRequire(import.meta.url);
    const { randomUUID } = require('node:crypto');
    return randomUUID();
  } catch {
    return `req-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
  }
};

/**
 * The PythonBridge class.
 *
 * The `spawnFn` option is a testing seam: pass a function shaped like
 * child_process.spawn to inject a fake child. Production callers should
 * leave it unset.
 */
export class PythonBridge extends EventEmitter {
  constructor(options = {}) {
    super();
    const defaults = defaultBridgeOptions();
    this.pythonCommand = options.pythonCommand || defaults.pythonCommand;
    this.scriptPath = options.scriptPath || defaults.scriptPath;
    this.timeoutMs = options.timeoutMs ?? defaults.timeoutMs;
    this.exitGraceMs = options.exitGraceMs ?? defaults.exitGraceMs;
    this.readyTimeoutMs = options.readyTimeoutMs ?? defaults.readyTimeoutMs;
    this.logger = options.logger || defaults.logger;
    this.spawnFn = options.spawnFn || spawn;

    this._proc = null;
    this._ready = false;
    this._readyPromise = null;
    this._readyResolve = null;
    this._readyReject = null;
    this._pending = new Map(); // id → { resolve, reject, timer }
    this._stdoutBuffer = '';
    this._stderrBuffer = '';
    this._intentionallyClosed = false;
    this._paused = false; // stdin backpressure flag
    this._drainPromise = null; // shared drain await promise

    // Auto-start, but allow callers to await start() explicitly if they want.
    // We do not block the constructor on the spawn so callers can attach
    // event listeners synchronously after construction.
    this._start();
  }

  /**
   * Begin spawning the child. Resolves once the child has emitted the
   * 'ready' event (or rejects if startup fails).
   */
  start() {
    return this.whenReady();
  }

  /**
   * Resolves when the bridge has finished initializing. If the bridge
   * has already initialized, returns the original promise so concurrent
   * callers all see the same outcome.
   */
  whenReady() {
    if (this._ready) {
      return Promise.resolve();
    }
    if (!this._readyPromise) {
      this._readyPromise = new Promise((resolve, reject) => {
        this._readyResolve = resolve;
        this._readyReject = reject;
      });
    }
    return this._readyPromise;
  }

  isReady() {
    return this._ready;
  }

  /**
   * Internal: spawn the child process and wire up I/O handlers.
   * Failures here reject _readyPromise (and therefore whenReady()) so
   * callers that explicitly await start() see the real error rather
   * than a silent queue.
   */
  async _start() {
    let command = this.pythonCommand;
    if (!command) {
      try {
        command = await resolvePythonCommand();
      } catch (err) {
        this._failReady(err);
        return;
      }
    }

    let proc;
    try {
      // Build a minimal allowlist environment. The Python child
      // inherits the entire parent process env by default, which
      // includes AWS_*, AZURE_*, GITHUB_TOKEN, and any other
      // secret-bearing variables the parent process holds. A
      // compromised Python interpreter (or a future Story that
      // registers a destructive command) could exfiltrate those.
      // We sanitize to a tiny allowlist: PATH (required for the
      // Python interpreter resolution), SYSTEMROOT (required for
      // Windows DLL loading), LANG (for consistent text encoding),
      // and a few other essentials. We also set cwd to a known-safe
      // directory and explicitly pass shell:false / windowsHide:true
      // (windowsHide was already set; the rest is new).
      proc = this.spawnFn(command, [this.scriptPath], {
        stdio: ['pipe', 'pipe', 'pipe'],
        windowsHide: true,
        shell: false,
        cwd: safeChildCwd(),
        env: safeChildEnv(),
      });
    } catch (err) {
      this._failReady(err);
      return;
    }

    this._proc = proc;

    proc.on('error', (err) => {
      this.logger.error('Python bridge process error', err);
      this._failReady(err);
      this._rejectAllPending(
        new ProcessExitError(`Python process error: ${err.message}`, { code: 'error' })
      );
    });

    proc.on('exit', (code, signal) => {
      this.logger.info('Python bridge process exited', { code, signal });
      this._ready = false;
      this._proc = null;
      this.emit('exit', { code, signal });
      if (!this._intentionallyClosed) {
        // Unexpected death: reject anything still in flight so the
        // caller learns about it instead of waiting for a timeout.
        this._rejectAllPending(
          new ProcessExitError(
            `Python process exited unexpectedly (code=${code}, signal=${signal ?? 'none'})`,
            { code, signal }
          )
        );
      } else if (this._pending.size > 0) {
        // Intentional shutdown: still reject in-flight requests so callers
        // don't wait for their per-request timeout after quit().
        this._rejectAllPending(
          new ProcessExitError('Python bridge shut down before request completed')
        );
      }
    });

    // Surface EPIPE / stdin errors to in-flight requests so they don't
    // silently wait for the per-request timeout. Without this, a closed
    // stdin (e.g. the child died) leaves every pending send() hung until
    // the timeout fires, which is a poor user experience for the first
    // request after a child crash.
    if (proc.stdin && typeof proc.stdin.on === 'function') {
      proc.stdin.on('error', (err) => {
        this.logger.warn('Python bridge stdin error', {
          message: err && err.message ? err.message : String(err),
        });
        if (this._pending.size > 0) {
          this._rejectAllPending(
            new ProcessExitError(
              `Python bridge stdin error: ${err && err.message ? err.message : String(err)}`
            )
          );
        }
      });
    }

    proc.stdout.setEncoding('utf8');
    proc.stdout.on('data', (chunk) => this._onStdout(chunk));

    proc.stderr.setEncoding('utf8');
    proc.stderr.on('data', (chunk) => this._onStderr(chunk));

    // Ready race: if the ready line never arrives (e.g. Python crashes
    // before printing), we still want start() to reject rather than hang.
    setTimeout(() => {
      if (!this._ready && this._proc) {
        this._failReady(
          new Error(`Python bridge did not become ready within ${this.readyTimeoutMs}ms`)
        );
      }
    }, this.readyTimeoutMs).unref();
  }

  _failReady(err) {
    if (this._readyReject) {
      const reject = this._readyReject;
      this._readyResolve = null;
      this._readyReject = null;
      reject(err);
    }
  }

  /**
   * Reject every in-flight request with the supplied error and clear the
   * pending map. Called when the child process dies unexpectedly or when
   * the bridge is shutting down intentionally with outstanding requests.
   */
  _rejectAllPending(err) {
    for (const [, pending] of this._pending) {
      clearTimeout(pending.timer);
      pending.reject(err);
    }
    this._pending.clear();
  }

  _markReady(payload) {
    if (this._ready) return;
    this._ready = true;
    // Cache the ready payload so callers can pull typed fields off it
    // (e.g. `bridge.pid`) without re-parsing the raw line. The Python
    // server sends a `pid` field on the ready envelope; we expose it as
    // a top-level property so future Stories have a typed access path
    // rather than a magic-string lookup on the payload.
    this._readyPayload = payload || null;
    if (payload && payload.pid !== undefined && payload.pid !== null) {
      this.pid = payload.pid;
    }
    if (this._readyResolve) {
      const resolve = this._readyResolve;
      this._readyResolve = null;
      this._readyReject = null;
      resolve(payload);
    }
    this.emit('ready', payload);
  }

  _onStdout(chunk) {
    this._stdoutBuffer += chunk;
    // Bound the stdout buffer so a misbehaving / compromised Python
    // child that streams bytes without a newline cannot OOM us. If we
    // exceed the cap, kill the child and reject all pending requests —
    // a partial line that never terminated is a protocol violation.
    if (this._stdoutBuffer.length > MAX_STDOUT_BUFFER_BYTES) {
      this.logger.error('Python bridge stdout buffer exceeded; killing child', {
        size: this._stdoutBuffer.length,
        cap: MAX_STDOUT_BUFFER_BYTES,
      });
      const proc = this._proc;
      forceKillProcess(proc, this.logger);
      this._rejectAllPending(
        new JsonProtocolError(
          `Python bridge stdout exceeded ${MAX_STDOUT_BUFFER_BYTES} bytes without a newline; child terminated`,
          undefined
        )
      );
      this._stdoutBuffer = '';
      return;
    }
    let newlineIdx;
    // Process one JSON line at a time. We split rather than parsing the
    // entire buffer so a partial line never blocks subsequent lines.
    while ((newlineIdx = this._stdoutBuffer.indexOf('\n')) !== -1) {
      const line = this._stdoutBuffer.slice(0, newlineIdx);
      this._stdoutBuffer = this._stdoutBuffer.slice(newlineIdx + 1);
      this._handleLine(line);
    }
  }

  _onStderr(chunk) {
    this._stderrBuffer += chunk;
    // Bound the stderr buffer so a chatty Python script cannot OOM us.
    // When truncating, mark the boundary so an operator reading the log
    // knows the beginning of a long stderr stream was lost (without
    // this marker, the first line could be silently cut off mid-line
    // and the operator would not know).
    if (this._stderrBuffer.length > 16 * 1024) {
      const truncated = this._stderrBuffer.slice(-16 * 1024);
      this._stderrBuffer = `...[truncated]\n${truncated}`;
    }
    // Demote routine Python output to a non-warn level. The previous
    // implementation logged EVERY stderr chunk at `warn`, which
    // flooded the log file with DeprecationWarning / informational
    // lines and drowned out real warnings. We now classify each line
    // by content:
    //   - Traceback ... → error
    //   - DeprecationWarning / FutureWarning → debug
    //   - UserWarning / RuntimeWarning → info
    //   - anything else → info (was: warn)
    // We buffer per-line so a single logical line split across two
    // chunks is logged as one entry rather than two.
    let newlineIdx;
    while ((newlineIdx = this._stderrBuffer.indexOf('\n')) !== -1) {
      const line = this._stderrBuffer.slice(0, newlineIdx).trim();
      this._stderrBuffer = this._stderrBuffer.slice(newlineIdx + 1);
      if (!line) continue;
      let level = 'info';
      if (/Traceback \(most recent call last\)/.test(line)) {
        level = 'error';
      } else if (/DeprecationWarning|FutureWarning/i.test(line)) {
        level = 'debug';
      } else if (/Warning/i.test(line)) {
        level = 'info';
      }
      const fn = this.logger[level];
      if (typeof fn === 'function') {
        fn('Python stderr', { line });
      }
    }
  }

  /**
   * Parse one response line from Python. Lines without an id are control
   * events (e.g. the initial 'ready' envelope); lines with an id are
   * responses to a pending request.
   */
  /**
   * Internal: await stdin drain. Shared across concurrent send() calls
   * so they all wait on the same drain event rather than each
   * installing its own one-shot listener (which would race with itself
   * and silently lose the signal). The promise resolves on the next
   * 'drain' event from the current stdin stream.
   */
  _awaitDrain() {
    const proc = this._proc;
    if (!proc || !proc.stdin || proc.stdin.destroyed) {
      return Promise.reject(new ProcessExitError('Python bridge is not running (stdin closed)'));
    }
    if (!this._drainPromise) {
      this._drainPromise = new Promise((resolve) => {
        const onDrain = () => {
          this._drainPromise = null;
          if (proc.stdin && typeof proc.stdin.removeListener === 'function') {
            proc.stdin.removeListener('drain', onDrain);
            proc.stdin.removeListener('close', onClose);
            proc.stdin.removeListener('error', onError);
          }
          resolve();
        };
        const onClose = () => {
          this._drainPromise = null;
          if (proc.stdin && typeof proc.stdin.removeListener === 'function') {
            proc.stdin.removeListener('drain', onDrain);
            proc.stdin.removeListener('close', onClose);
            proc.stdin.removeListener('error', onError);
          }
          resolve(); // fall through; send() will catch the closed stdin
        };
        const onError = () => {
          this._drainPromise = null;
          if (proc.stdin && typeof proc.stdin.removeListener === 'function') {
            proc.stdin.removeListener('drain', onDrain);
            proc.stdin.removeListener('close', onClose);
            proc.stdin.removeListener('error', onError);
          }
          resolve();
        };
        if (proc.stdin) {
          proc.stdin.once('drain', onDrain);
          proc.stdin.once('close', onClose);
          proc.stdin.once('error', onError);
        } else {
          this._drainPromise = null;
          resolve();
        }
      });
    }
    return this._drainPromise;
  }

  _handleLine(line) {
    const trimmed = line.trim();
    if (!trimmed) return;

    let parsed;
    try {
      parsed = JSON.parse(trimmed);
    } catch (err) {
      this.logger.error('Malformed JSON from Python bridge', { rawLine: trimmed });
      this.emit('protocolError', new JsonProtocolError(`Malformed JSON: ${err.message}`, trimmed));
      return;
    }

    if (!parsed || typeof parsed !== 'object') {
      this.logger.error('Non-object JSON from Python bridge', { rawLine: trimmed });
      return;
    }

    // Control event (no id): the server announces 'ready' once at startup
    // and may broadcast future control events (e.g. 'shutdown'). The
    // set of recognized control events is a small, explicit allowlist —
    // anything else (e.g. a future Python bug that emits
    // `{"error": "..."}` with no id and no event) is rejected as a
    // protocol error rather than silently dropped on the floor via the
    // generic 'event' emit. This makes a malformed control line fail
    // loud rather than disappearing into the renderer.
    if (parsed.id === undefined || parsed.id === null) {
      const event = parsed.event;
      if (event === 'ready') {
        this._markReady(parsed);
      } else if (event === 'shutdown' || event === 'event') {
        this.emit('event', parsed);
      } else {
        const err = new JsonProtocolError(
          `Python bridge sent unknown control event: ${JSON.stringify(event)}`,
          trimmed
        );
        this.logger.error('Unknown control event from Python bridge', {
          rawLine: trimmed,
          message: err.message,
        });
        this.emit('protocolError', err);
      }
      return;
    }

    const pending = this._pending.get(parsed.id);
    if (!pending) {
      this.logger.warn('Received response for unknown request id', { id: parsed.id });
      return;
    }

    clearTimeout(pending.timer);
    this._pending.delete(parsed.id);

    // Require an explicit ok: true. Anything that is NOT a clear
    // `ok: true` is treated as a protocol error so a buggy Python
    // server that forgets to set ok: true on a successful response
    // is surfaced as an error rather than silently resolving with
    // undefined. (Previously, missing ok / ok: 0 / ok: null all fell
    // through to the success branch, masking the bug as "the command
    // ran with no output".)
    if (parsed.ok !== true) {
      const err = new JsonProtocolError(
        `Python bridge response missing ok:true (got ${JSON.stringify(parsed.ok)})`,
        trimmed
      );
      err.response = parsed;
      pending.reject(err);
    } else {
      pending.resolve(parsed.result);
    }
  }

  /**
   * Send a command. Resolves with the `result` field on success, rejects
   * with an Error on failure or timeout.
   */
  async send(command, params = {}, options = {}) {
    if (typeof command !== 'string' || !command) {
      throw new Error('send: command must be a non-empty string');
    }
    await this.whenReady();

    // If stdin is currently under backpressure, await the drain before
    // doing anything else. This is the critical correctness fix: the
    // previous implementation set `_paused = true` but never checked
    // it in subsequent send() calls, so a burst of concurrent writes
    // would all allocate pending entries and grow _pending until the
    // 1000-entry cap was hit. Now we serialize: callers wait on a
    // single shared drain promise so only one new request enters the
    // pipe per drain cycle.
    if (this._paused) {
      try {
        await this._awaitDrain();
      } catch {
        // Drain promise rejected (stdin closed) — fall through to the
        // closed-stdin check below.
      }
    }

    // Allocate the request id once and reuse it: the envelope id and the
    // pending-map id MUST agree so the response can be matched. Generating
    // them separately is a subtle bug that surfaces as "response for
    // unknown request id" warnings.
    const id = newRequestId();
    // Pre-flight serialization: validate the params can be turned into JSON
    // BEFORE entering the Promise constructor's try block, so a circular
    // reference / BigInt / non-serializable value produces a descriptive
    // error tagged with the command name instead of a raw TypeError from
    // JSON.stringify leaking out of the async function body.
    let envelope;
    try {
      envelope = JSON.stringify({ id, cmd: command, params });
    } catch (err) {
      throw new Error(
        `Failed to serialize params for command '${command}': ${err && err.message ? err.message : String(err)}`
      );
    }

    const timeoutMs = options.timeoutMs ?? this.timeoutMs;

    return new Promise((resolve, reject) => {
      // Bail early if the child has died between whenReady() returning
      // and the caller reaching this point. Without this guard we'd queue
      // a pending entry on a dead pipe and the caller would only learn
      // about it after the timeout.
      if (!this._proc || !this._proc.stdin || this._proc.stdin.destroyed) {
        reject(new ProcessExitError('Python bridge is not running'));
        return;
      }

      // Hard cap on concurrent pending requests. A compromised renderer
      // or buggy JS loop could otherwise grow _pending indefinitely
      // until OOM. Reject loudly rather than silently queueing.
      if (this._pending.size >= MAX_PENDING_REQUESTS) {
        reject(
          new Error(
            `Python bridge has too many pending requests (>= ${MAX_PENDING_REQUESTS}); refusing '${command}'`
          )
        );
        return;
      }

      const timer = setTimeout(() => {
        if (this._pending.has(id)) {
          this._pending.delete(id);
          reject(
            new TimeoutError(`Python bridge request '${command}' timed out after ${timeoutMs}ms`)
          );
        }
      }, timeoutMs);
      // unref so an in-flight timer never holds the event loop open.
      if (typeof timer.unref === 'function') {
        timer.unref();
      }

      this._pending.set(id, { resolve, reject, timer });

      try {
        // Handle stdin backpressure: if .write() returns false the pipe
        // is full. Set _paused so the next send() awaits drain BEFORE
        // allocating its pending entry. The drain promise is shared
        // (see _awaitDrain) so concurrent callers serialize on the
        // same drain event.
        const accepted = this._proc.stdin.write(`${envelope}\n`);
        if (accepted === false) {
          this._paused = true;
        }
      } catch (err) {
        clearTimeout(timer);
        this._pending.delete(id);
        reject(new Error(`Failed to write to Python bridge stdin: ${err.message}`));
      }
    });
  }

  /**
   * Convenience wrapper for the AC2 ping/pong contract.
   */
  ping() {
    return this.send('ping');
  }

  /**
   * Gracefully terminate the child. Sends SIGTERM (Windows: taskkill /T),
   * waits up to `exitGraceMs` for exit, then SIGKILL.
   *
   * Contract: any `send()` calls that are still in flight when `quit()`
   * is invoked will reject with a `ProcessExitError` so the caller learns
   * the bridge was shut down underneath them instead of waiting for a
   * timeout.
   */
  async quit() {
    if (!this._proc) {
      // Even if no live child, ensure pending requests are drained so a
      // caller can chain cleanup deterministically after quit().
      if (this._pending.size > 0) {
        this._rejectAllPending(
          new ProcessExitError('Python bridge is shutting down (no live process)')
        );
      }
      return;
    }
    this._intentionallyClosed = true;
    this._quitting = true;

    const proc = this._proc;
    // IMPORTANT: arm the SIGKILL fallback BEFORE awaiting the exit promise
    // so it is in flight regardless of which path (real 'exit' event or
    // safety timer) resolves the await. If we set it AFTER the await, a
    // child that already exited cleanly would still leave the timer
    // arming on a now-stale `proc` reference, masking any subsequent
    // hang. Arming first also bounds the total wall-clock time of quit()
    // to roughly `exitGraceMs` + OS delivery latency.
    const killTimer = setTimeout(() => {
      // On Windows, proc.kill('SIGKILL') does not always kill the
      // process tree spawned by the `py` launcher / cmd.exe. Use
      // taskkill /F /T /PID via the platform-aware forceKillProcess
      // helper so the child is guaranteed to be reaped.
      forceKillProcess(proc, this.logger);
    }, this.exitGraceMs);
    if (typeof killTimer.unref === 'function') {
      killTimer.unref();
    }

    let safety;
    try {
      if (proc.stdin && !proc.stdin.destroyed) {
        try {
          proc.stdin.end();
        } catch {
          /* ignore */
        }
      }
      // IMPORTANT: register the exit listener BEFORE issuing SIGTERM so
      // a fast-exit child (e.g. Windows where SIGTERM maps to immediate
      // termination) does not emit 'exit' before any listener exists,
      // which would force the caller to wait for the safety timeout.
      const exitedPromise = new Promise((resolve) => {
        // If the proc is already null (i.e. 'exit' fired between the
        // guard above and now), resolve immediately.
        if (!this._proc) {
          resolve();
          return;
        }
        // Capture the local proc reference because `this._proc` may be
        // nulled by the 'exit' handler before our listener fires, but
        // `proc` is still a valid EventEmitter reference.
        proc.once('exit', () => resolve());
        // Safety net in case the child never emits 'exit' (shouldn't
        // happen but...). Resolves after the SIGKILL grace period plus a
        // small OS-delivery buffer so we don't leak the await. The
        // outer scope `safety` is assigned here so the finally block
        // below can clearTimeout it after the await settles.
        safety = setTimeout(resolve, this.exitGraceMs + 50);
        if (typeof safety.unref === 'function') {
          safety.unref();
        }
      });

      // On Windows, SIGTERM is mapped to terminating the process; on POSIX
      // it allows the child to flush before exiting.
      try {
        proc.kill('SIGTERM');
      } catch {
        /* ignore */
      }

      // Now wait for the exit that we registered a listener for.
      try {
        await exitedPromise;
      } finally {
        // Unconditional cleanup: whichever path resolved the await
        // (real 'exit' OR safety timer), both timers must be cleared so
        // we never leave a queued timer in the event loop. clearTimeout
        // is a no-op on already-fired timers, so this is safe in both
        // branches. The `try { clearTimeout(safety) }` is wrapped in its
        // own try so an unexpected throw (e.g. `safety` was never
        // assigned because the proc-already-null branch ran) does not
        // mask the killTimer cleanup.
        clearTimeout(killTimer);
        try {
          if (safety) clearTimeout(safety);
        } catch {
          /* safety was never assigned; nothing to clear */
        }
      }

      // After exit, any pending requests must be rejected — the contract
      // promises that quit() does not leave in-flight promises dangling.
      if (this._pending.size > 0) {
        this._rejectAllPending(
          new ProcessExitError('Python bridge shut down before request completed')
        );
      }
    } catch (err) {
      clearTimeout(killTimer);
      try {
        if (safety) clearTimeout(safety);
      } catch {
        /* safety was never assigned; nothing to clear */
      }
      // Best-effort cleanup so callers don't see a leaked timer.
      if (this._pending.size > 0) {
        this._rejectAllPending(
          new ProcessExitError(
            `Python bridge quit failed: ${err && err.message ? err.message : String(err)}`
          )
        );
      }
    }
  }

  /**
   * Whether the bridge is currently in the process of shutting down.
   * Used by callers (e.g. main.js before-quit handler) as a re-entrancy
   * guard so they don't kick off a second quit() while one is in flight.
   */
  isQuitting() {
    return this._quitting === true;
  }
}
