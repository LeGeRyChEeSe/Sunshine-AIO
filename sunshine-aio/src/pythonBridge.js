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

const DEFAULT_TIMEOUT_MS = 10_000;
const DEFAULT_EXIT_GRACE_MS = 2_000;
const DEFAULT_READY_TIMEOUT_MS = 5_000;

// Prefer 'py' (Windows launcher) → 'python3' → 'python'. The bridge tries
// them in order; the first one that exists wins. We probe by checking PATH
// via 'where' (Windows) / 'which' (POSIX) so we do not have to import the
// file-system just to pick an interpreter.
const PYTHON_CANDIDATES =
  process.platform === 'win32' ? ['py', 'python', 'python3'] : ['python3', 'python'];

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// The Python script lives two directories up: src/python_bridge_server.py.
// We resolve from this file so the bridge works regardless of cwd (which
// changes when packaged vs. dev vs. tested).
const DEFAULT_SCRIPT_PATH = path.resolve(__dirname, '..', '..', 'src', 'python_bridge_server.py');

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
 * Pick a Python interpreter. Tries each candidate in order and returns the
 * first one that spawns successfully (i.e. does not ENOENT).
 *
 * Accepts an optional `spawnFn` for testing. When omitted, uses the real
 * node:child_process.spawn. The injected function should throw on ENOENT
 * to mimic the real behavior across platforms.
 *
 * Exported for tests; production code should rely on PythonBridge auto-start.
 */
export const resolvePythonCommand = async (options = {}) => {
  const spawnFn = options.spawnFn || spawn;
  for (const candidate of PYTHON_CANDIDATES) {
    let probe;
    try {
      probe = spawnFn(candidate, ['--version'], { stdio: 'ignore' });
    } catch {
      // ENOENT or other synchronous spawn failure — try the next candidate.
      continue;
    }
    if (!probe) {
      continue;
    }
    const ok = await new Promise((resolve) => {
      probe.once('error', () => resolve(false));
      probe.once('exit', (code) => resolve(code === 0 || code === null));
    });
    // Reap the probe if still alive.
    if (probe.exitCode === null && probe.signalCode === null) {
      try {
        probe.kill();
      } catch {
        /* ignore */
      }
    }
    if (ok) {
      return candidate;
    }
  }
  throw new Error('No Python interpreter found. Tried: ' + PYTHON_CANDIDATES.join(', '));
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
      proc = this.spawnFn(command, [this.scriptPath], {
        stdio: ['pipe', 'pipe', 'pipe'],
        windowsHide: true,
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
      }
    });

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
    if (this._stderrBuffer.length > 16 * 1024) {
      this._stderrBuffer = this._stderrBuffer.slice(-16 * 1024);
    }
    this.logger.warn('Python stderr', { chunk: chunk.trim() });
  }

  /**
   * Parse one response line from Python. Lines without an id are control
   * events (e.g. the initial 'ready' envelope); lines with an id are
   * responses to a pending request.
   */
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

    // Control event (no id): the server announces 'ready' once at startup.
    if (parsed.id === undefined || parsed.id === null) {
      if (parsed.event === 'ready') {
        this._markReady(parsed);
      } else {
        this.emit('event', parsed);
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

    if (parsed.ok === false) {
      const err = new Error(parsed.error || 'Python bridge returned an error');
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

    const id = newRequestId();
    const envelope = JSON.stringify({ id, cmd: command, params });
    const timeoutMs = options.timeoutMs ?? this.timeoutMs;

    return new Promise((resolve, reject) => {
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
        this._proc.stdin.write(`${envelope}\n`);
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
   */
  async quit() {
    if (!this._proc) {
      return;
    }
    this._intentionallyClosed = true;

    const proc = this._proc;
    const killTimer = setTimeout(() => {
      try {
        proc.kill('SIGKILL');
      } catch {
        /* ignore */
      }
    }, this.exitGraceMs);
    if (typeof killTimer.unref === 'function') {
      killTimer.unref();
    }

    try {
      if (proc.stdin && !proc.stdin.destroyed) {
        try {
          proc.stdin.end();
        } catch {
          /* ignore */
        }
      }
      // On Windows, SIGTERM is mapped to terminating the process; on POSIX
      // it allows the child to flush before exiting.
      try {
        proc.kill('SIGTERM');
      } catch {
        /* ignore */
      }
    } finally {
      // Wait for the exit event so callers can chain cleanup deterministically.
      await new Promise((resolve) => {
        if (!this._proc) {
          resolve();
          return;
        }
        this.once('exit', resolve);
        // If the child never emits 'exit' (shouldn't happen, but...), bail
        // out after the SIGKILL grace period plus a small OS-delivery buffer
        // so we don't leak the await. The buffer is intentionally tiny so
        // callers can chain cleanup quickly even when the child is wedged.
        const safety = setTimeout(resolve, this.exitGraceMs + 50);
        if (typeof safety.unref === 'function') {
          safety.unref();
        }
      });
      clearTimeout(killTimer);
    }
  }
}
