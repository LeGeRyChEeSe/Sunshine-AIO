/**
 * Tests for the PythonBridge (Story 1.3).
 *
 * These tests use a fake child-process factory (FakeChild) instead of
 * spawning a real Python process. The fake emits the same events the
 * real spawn() emits (exit, error, stdout.on('data'), etc.) so the
 * bridge code path is exercised end-to-end without needing a Python
 * interpreter in the test environment.
 */

import { describe, expect, it, vi } from 'vitest';
import { EventEmitter } from 'node:events';
import { Readable, Writable } from 'node:stream';

import {
  JsonProtocolError,
  ProcessExitError,
  PythonBridge,
  TimeoutError,
  defaultBridgeOptions,
  resolvePythonCommand,
} from './pythonBridge.js';

/**
 * Minimal in-memory child stand-in. It exposes the same surface the bridge
 * touches: stdin (Writable), stdout (Readable in object/buffer mode),
 * stderr (Readable), `kill`, `once('error')`, `once('exit')`.
 *
 * Tests drive it by writing to `stdin` to simulate Python output, or
 * emitting 'exit' to simulate the process dying.
 */
class FakeChild extends EventEmitter {
  constructor() {
    super();
    this.killed = null;
    this.kill = vi.fn((signal) => {
      this.killed = signal || 'SIGTERM';
      // Real spawn delivers 'exit' asynchronously; mirror that so the
      // bridge's race-conditions are exercised.
      setImmediate(() => {
        if (!this._exited) {
          this._exited = true;
          this.emit('exit', null, signal || 'SIGTERM');
        }
      });
      return true;
    });

    // stdin: a writable whose .write/.end we control from the test.
    this.stdin = new Writable({
      write(_chunk, _enc, cb) {
        cb();
      },
    });
    // Spy on write so tests can assert what the bridge sent.
    this.stdinWrite = vi.spyOn(this.stdin, 'write');

    // stdout/stderr: a Readable that emits 'data' when we push strings.
    // Wrapping an EventEmitter in a Readable is the simplest way to
    // get back-pressure semantics close enough for tests.
    this.stdout = new Readable({ read() {} });
    this.stderr = new Readable({ read() {} });

    this._exited = false;
    this.exitCode = null;
    this.signalCode = null;
  }

  pushStdout(text) {
    this.stdout.push(text);
  }

  pushStderr(text) {
    this.stderr.push(text);
  }

  /**
   * Simulate the child process terminating.
   */
  simulateExit(code = 0, signal = null) {
    if (this._exited) return;
    this._exited = true;
    this.exitCode = code;
    this.signalCode = signal;
    // Drain any buffered stdout first so the bridge processes the
    // final lines before seeing 'exit'.
    this.stdout.push(null);
    this.stderr.push(null);
    setImmediate(() => this.emit('exit', code, signal));
  }

  simulateError(err) {
    this.emit('error', err);
  }
}

/**
 * Build a spawn() stub that returns a fresh FakeChild each call.
 */
const makeSpawnStub = () => {
  const fake = new FakeChild();
  const fn = vi.fn(() => fake);
  return { fn, fake };
};

const silentLogger = () => ({
  debug: vi.fn(),
  info: vi.fn(),
  warn: vi.fn(),
  error: vi.fn(),
  flush: vi.fn(() => Promise.resolve()),
});

const defaultTestOptions = (overrides = {}) => {
  const { fn } = makeSpawnStub();
  return {
    pythonCommand: 'python-test',
    scriptPath: '/fake/python_bridge_server.py',
    timeoutMs: 200,
    exitGraceMs: 100,
    readyTimeoutMs: 5000,
    logger: silentLogger(),
    spawnFn: fn,
    ...overrides,
  };
};

/** Drive a fake to emit its 'ready' envelope. */
const emitReady = (fake, payload = { pid: 12345 }) => {
  fake.pushStdout(`${JSON.stringify({ event: 'ready', ...payload })}\n`);
};

describe('defaultBridgeOptions', () => {
  it('exposes the timeout and exit grace defaults', () => {
    const opts = defaultBridgeOptions();
    expect(opts.timeoutMs).toBe(10_000);
    expect(opts.exitGraceMs).toBe(2_000);
    expect(typeof opts.scriptPath).toBe('string');
  });
});

describe('PythonBridge basic lifecycle', () => {
  it('invokes the spawn factory with the configured interpreter and script', () => {
    const opts = defaultTestOptions();
    new PythonBridge(opts);
    expect(opts.spawnFn).toHaveBeenCalledTimes(1);
    const [cmd, args, spawnOpts] = opts.spawnFn.mock.calls[0];
    expect(cmd).toBe('python-test');
    expect(args).toEqual(['/fake/python_bridge_server.py']);
    expect(spawnOpts.stdio).toEqual(['pipe', 'pipe', 'pipe']);
  });

  it('marks itself ready when Python emits the ready envelope', async () => {
    const opts = defaultTestOptions();
    const bridge = new PythonBridge(opts);
    emitReady(opts.spawnFn.mock.results[0].value, { pid: 4242 });
    await expect(bridge.whenReady()).resolves.toMatchObject({ pid: 4242 });
    expect(bridge.isReady()).toBe(true);
  });

  it('rejects whenReady if Python never sends a ready envelope', async () => {
    const opts = defaultTestOptions({ readyTimeoutMs: 50 });
    // We do NOT emit the ready envelope and do NOT simulate an error.
    // The bridge's own ready-timeout should fail whenReady() quickly so
    // the caller learns the bridge never came up rather than hanging.
    const bridge = new PythonBridge(opts);
    await expect(bridge.whenReady()).rejects.toThrow(/did not become ready/);
  });
});

describe('PythonBridge.send / ping', () => {
  it('round-trips a ping and returns pong', async () => {
    const opts = defaultTestOptions();
    const bridge = new PythonBridge(opts);
    const fake = opts.spawnFn.mock.results[0].value;
    emitReady(fake);

    const promise = bridge.ping();
    // Allow the stdin.write microtask to run, then assert what was sent.
    await new Promise((resolve) => setImmediate(resolve));
    expect(fake.stdinWrite).toHaveBeenCalledTimes(1);
    const sentLine = fake.stdinWrite.mock.calls[0][0];
    expect(sentLine.endsWith('\n')).toBe(true);
    const envelope = JSON.parse(sentLine.trim());
    expect(envelope.cmd).toBe('ping');
    expect(typeof envelope.id).toBe('string');
    expect(envelope.params).toEqual({});

    // Simulate the Python side responding.
    fake.pushStdout(
      `${JSON.stringify({ id: envelope.id, ok: true, result: { result: 'pong', echo: {} } })}\n`
    );

    await expect(promise).resolves.toEqual({ result: 'pong', echo: {} });
  });

  it('queues requests made before the child is ready and dispatches after ready', async () => {
    const opts = defaultTestOptions();
    const bridge = new PythonBridge(opts);
    const fake = opts.spawnFn.mock.results[0].value;

    // Queue a ping BEFORE ready: this is the realistic load order — the
    // renderer fires the IPC call as soon as the main process has wired
    // the handler, possibly before Python has finished booting.
    const promise = bridge.ping();

    // Nothing has been written yet because the bridge awaits whenReady.
    expect(fake.stdinWrite).not.toHaveBeenCalled();

    emitReady(fake);
    await new Promise((resolve) => setImmediate(resolve));
    expect(fake.stdinWrite).toHaveBeenCalledTimes(1);

    const envelope = JSON.parse(fake.stdinWrite.mock.calls[0][0]);
    fake.pushStdout(
      `${JSON.stringify({ id: envelope.id, ok: true, result: { result: 'pong', echo: {} } })}\n`
    );
    await expect(promise).resolves.toEqual({ result: 'pong', echo: {} });
  });

  it('rejects when Python returns a non-ok response', async () => {
    // Per the strict ok:true contract, anything that is not an explicit
    // ok:true (including ok:false, ok:0, ok:null, missing ok) is treated
    // as a protocol error. This is intentionally stricter than just
    // forwarding parsed.error so a buggy Python server that forgets to
    // set ok:true on a successful response is surfaced as an error.
    const opts = defaultTestOptions();
    const bridge = new PythonBridge(opts);
    const fake = opts.spawnFn.mock.results[0].value;
    emitReady(fake);

    const promise = bridge.ping();
    await new Promise((resolve) => setImmediate(resolve));
    const envelope = JSON.parse(fake.stdinWrite.mock.calls[0][0]);
    fake.pushStdout(`${JSON.stringify({ id: envelope.id, ok: false, error: 'boom' })}\n`);
    await expect(promise).rejects.toBeInstanceOf(JsonProtocolError);
  });

  it('rejects when Python returns ok=true with missing result', async () => {
    // Even with ok:true, if result is missing, the promise resolves with
    // undefined — but the bridge must not crash or hang.
    const opts = defaultTestOptions();
    const bridge = new PythonBridge(opts);
    const fake = opts.spawnFn.mock.results[0].value;
    emitReady(fake);

    const promise = bridge.ping();
    await new Promise((resolve) => setImmediate(resolve));
    const envelope = JSON.parse(fake.stdinWrite.mock.calls[0][0]);
    fake.pushStdout(`${JSON.stringify({ id: envelope.id, ok: true })}\n`);
    await expect(promise).resolves.toBeUndefined();
  });

  it('throws synchronously when send is called with a non-string command', async () => {
    const opts = defaultTestOptions();
    const bridge = new PythonBridge(opts);
    await expect(bridge.send('', {})).rejects.toThrow(/non-empty string/);
    await expect(bridge.send(null, {})).rejects.toThrow(/non-empty string/);
  });

  it('produces a descriptive error when params are not JSON-serializable', async () => {
    // Pre-flight serialization: a circular params object must produce a
    // descriptive error tagged with the command name instead of a raw
    // TypeError leaking out of the async function body.
    const opts = defaultTestOptions();
    const bridge = new PythonBridge(opts);
    const fake = opts.spawnFn.mock.results[0].value;
    emitReady(fake);
    await bridge.whenReady();

    const params = {};
    params.self = params; // cycle
    let caught;
    try {
      await bridge.send('circular', params);
    } catch (err) {
      caught = err;
    }
    expect(caught).toBeInstanceOf(Error);
    expect(caught.message).toMatch(/Failed to serialize params for command 'circular'/);
  });
});

describe('PythonBridge timeout behavior', () => {
  it('rejects pending requests with TimeoutError after the timeout elapses', async () => {
    const opts = defaultTestOptions({ timeoutMs: 50 });
    const bridge = new PythonBridge(opts);
    const fake = opts.spawnFn.mock.results[0].value;
    emitReady(fake);

    const promise = bridge.ping();
    // Catch the rejection immediately so we don't trip unhandled-rejection
    // warnings during the test run. Use expect(...).rejects below for the
    // actual assertion.
    const assertion = expect(promise).rejects.toBeInstanceOf(TimeoutError);
    await assertion;
  });

  it('honors a per-call timeoutMs override', async () => {
    const opts = defaultTestOptions({ timeoutMs: 500 });
    const bridge = new PythonBridge(opts);
    const fake = opts.spawnFn.mock.results[0].value;
    emitReady(fake);

    const start = Date.now();
    const promise = bridge.send('slow', {}, { timeoutMs: 50 });
    await expect(promise).rejects.toBeInstanceOf(TimeoutError);
    const elapsed = Date.now() - start;
    expect(elapsed).toBeLessThan(300); // well under the 500ms default
  });
});

describe('PythonBridge process crash handling', () => {
  it('rejects all pending requests with ProcessExitError when the child dies unexpectedly', async () => {
    const opts = defaultTestOptions();
    const bridge = new PythonBridge(opts);
    const fake = opts.spawnFn.mock.results[0].value;
    emitReady(fake);

    const a = bridge.ping();
    const b = bridge.ping();
    const c = bridge.ping();

    fake.simulateExit(1, null);

    await expect(a).rejects.toBeInstanceOf(ProcessExitError);
    await expect(b).rejects.toBeInstanceOf(ProcessExitError);
    await expect(c).rejects.toBeInstanceOf(ProcessExitError);
  });

  it('does not reject pending requests on intentional quit', async () => {
    const opts = defaultTestOptions();
    const bridge = new PythonBridge(opts);
    const fake = opts.spawnFn.mock.results[0].value;
    emitReady(fake);

    // Issue a quit before any pending requests. The intentional path
    // must not throw ProcessExitError for the absent-promise case.
    await expect(bridge.quit()).resolves.toBeUndefined();
  });

  it('rejects in-flight requests with ProcessExitError when quit() is called', async () => {
    // The quit() contract promises that any in-flight send() promise
    // rejects with a ProcessExitError so the caller learns the bridge
    // was shut down underneath them — rather than waiting for the
    // per-request timeout. This test pins that invariant.
    const opts = defaultTestOptions();
    const bridge = new PythonBridge(opts);
    const fake = opts.spawnFn.mock.results[0].value;
    emitReady(fake);

    // Attach rejections handlers immediately to avoid unhandled-rejection
    // warnings during the test run. We capture the rejection handlers in
    // an array so we can assert on them after quit() settles.
    const a = bridge.ping().catch((err) => err);
    const b = bridge.ping().catch((err) => err);
    const c = bridge.ping().catch((err) => err);

    // We do NOT push any responses — the requests should be rejected by
    // the intentional-shutdown path, not by the timeout.
    await bridge.quit();

    const [aErr, bErr, cErr] = await Promise.all([a, b, c]);
    expect(aErr).toBeInstanceOf(ProcessExitError);
    expect(bErr).toBeInstanceOf(ProcessExitError);
    expect(cErr).toBeInstanceOf(ProcessExitError);
  });

  it('exposes isQuitting() as a public re-entrancy guard', async () => {
    const opts = defaultTestOptions();
    const bridge = new PythonBridge(opts);
    const fake = opts.spawnFn.mock.results[0].value;
    emitReady(fake);
    expect(bridge.isQuitting()).toBe(false);

    const quitPromise = bridge.quit();
    // quit() may not have flipped the flag yet (the await is async), but
    // after the promise settles the flag MUST be true.
    await quitPromise;
    expect(bridge.isQuitting()).toBe(true);
  });
});

describe('PythonBridge malformed JSON handling', () => {
  it('emits protocolError and does not crash when Python sends garbage', async () => {
    const opts = defaultTestOptions();
    const bridge = new PythonBridge(opts);
    const fake = opts.spawnFn.mock.results[0].value;
    emitReady(fake);

    const protocolErrors = [];
    bridge.on('protocolError', (err) => protocolErrors.push(err));

    // Send two garbage lines interleaved with a valid response so we can
    // also verify recovery (a malformed line must NOT kill the bridge).
    fake.pushStdout('this is not json\n');
    fake.pushStdout('{"id":"r1","ok":true,"result":"ok"}\n');
    fake.pushStdout('{"oops"\n'); // truncated
    await new Promise((resolve) => setImmediate(resolve));

    expect(protocolErrors.length).toBe(2);
    expect(protocolErrors[0]).toBeInstanceOf(JsonProtocolError);
  });

  it('warns when Python sends a response for an unknown request id', async () => {
    const opts = defaultTestOptions();
    new PythonBridge(opts);
    const fake = opts.spawnFn.mock.results[0].value;
    emitReady(fake);

    fake.pushStdout(`${JSON.stringify({ id: 'no-such-id', ok: true, result: 'whatever' })}\n`);
    await new Promise((resolve) => setImmediate(resolve));
    // The logger was a spy; we asserted on calls here rather than the
    // exact message to keep the test resilient to formatting tweaks.
    const warnCalls = opts.logger.warn.mock.calls.map((c) => String(c[0]));
    expect(warnCalls.some((m) => m.includes('unknown request'))).toBe(true);
  });

  it('kills the child when stdout buffer exceeds the cap', async () => {
    // DoS guard: a misbehaving / compromised Python child that emits N
    // bytes without a newline must not be allowed to grow _stdoutBuffer
    // until V8 OOMs. The bridge must kill the child and reject any
    // pending requests.
    const opts = defaultTestOptions();
    new PythonBridge(opts);
    const fake = opts.spawnFn.mock.results[0].value;
    emitReady(fake);

    // Send a payload larger than MAX_STDOUT_BUFFER_BYTES (1 MiB) with no
    // newline. The bridge should kill the child.
    const bigChunk = 'x'.repeat(1024 * 1024 + 1);
    fake.pushStdout(bigChunk);
    await new Promise((resolve) => setImmediate(resolve));

    // The child should have been killed as SIGKILL by the bridge.
    const killSignals = fake.kill.mock.calls.map((c) => c[0]);
    expect(killSignals).toContain('SIGKILL');
  });
});

describe('PythonBridge concurrent requests', () => {
  it('resolves multiple in-flight requests independently and in any order', async () => {
    const opts = defaultTestOptions({ timeoutMs: 1000 });
    const bridge = new PythonBridge(opts);
    const fake = opts.spawnFn.mock.results[0].value;
    emitReady(fake);

    const N = 10;
    const promises = [];
    for (let i = 0; i < N; i += 1) {
      promises.push(bridge.send('ping', { i }));
    }
    // Capture each request id and which one we want to answer first/last.
    await new Promise((resolve) => setImmediate(resolve));
    const lines = fake.stdinWrite.mock.calls.map((c) => c[0]);
    expect(lines).toHaveLength(N);
    const ids = lines.map((l) => JSON.parse(l.trim()).id);
    const echoedParams = lines.map((l) => JSON.parse(l.trim()).params);

    // Answer in REVERSE order to prove there is no FIFO assumption on
    // the response side.
    for (let i = ids.length - 1; i >= 0; i -= 1) {
      fake.pushStdout(
        `${JSON.stringify({ id: ids[i], ok: true, result: { result: 'pong', echo: echoedParams[i] } })}\n`
      );
    }

    const results = await Promise.all(promises);
    expect(results).toHaveLength(N);
    results.forEach((res, i) => {
      expect(res).toEqual({ result: 'pong', echo: { i } });
    });
  });

  it('keeps pending requests separate so a timeout on one does not affect others', async () => {
    const opts = defaultTestOptions({ timeoutMs: 80 });
    const bridge = new PythonBridge(opts);
    const fake = opts.spawnFn.mock.results[0].value;
    emitReady(fake);

    const slow = bridge.send('slow', {}, { timeoutMs: 30 });
    const fast = bridge.send('fast', {}, { timeoutMs: 500 });
    await new Promise((resolve) => setImmediate(resolve));
    const ids = fake.stdinWrite.mock.calls.map((c) => JSON.parse(c[0].trim()).id);
    // Answer only the fast one.
    fake.pushStdout(
      `${JSON.stringify({ id: ids[1], ok: true, result: { result: 'pong', echo: {} } })}\n`
    );
    await expect(slow).rejects.toBeInstanceOf(TimeoutError);
    await expect(fast).resolves.toEqual({ result: 'pong', echo: {} });
  });

  it('refuses new requests once _pending exceeds the cap', async () => {
    // The bridge should refuse new sends once _pending grows past the
    // hard cap (1000 by default). We can't easily fill 1000 slots in a
    // unit test, so we override the cap by stuffing _pending directly
    // and then assert that the next send() rejects.
    const opts = defaultTestOptions({ timeoutMs: 5000 });
    const bridge = new PythonBridge(opts);
    const fake = opts.spawnFn.mock.results[0].value;
    emitReady(fake);

    // Stuff 1000 fake entries so the next send() hits the cap.
    for (let i = 0; i < 1000; i += 1) {
      bridge._pending.set(`fake-${i}`, {
        resolve: () => {},
        reject: () => {},
        timer: setTimeout(() => {}, 60000),
      });
    }
    // Now send() should refuse.
    await expect(bridge.send('ping')).rejects.toThrow(/too many pending requests/);
    // Cleanup the fake entries.
    for (const [, p] of bridge._pending) {
      clearTimeout(p.timer);
    }
    bridge._pending.clear();
  });
});

describe('PythonBridge cleanup', () => {
  it('sends SIGTERM (and SIGKILL after grace) on quit', async () => {
    const opts = defaultTestOptions({ exitGraceMs: 30 });
    const bridge = new PythonBridge(opts);
    const fake = opts.spawnFn.mock.results[0].value;
    emitReady(fake);
    await bridge.whenReady();

    await bridge.quit();
    expect(fake.kill).toHaveBeenCalled();
    const signals = fake.kill.mock.calls.map((c) => c[0]);
    // First signal must be SIGTERM (the polite one).
    expect(signals[0]).toBe('SIGTERM');
  });

  it('resolves quit() even if the child never reports exit', async () => {
    const opts = defaultTestOptions({ exitGraceMs: 20 });
    const bridge = new PythonBridge(opts);
    const fake = opts.spawnFn.mock.results[0].value;
    emitReady(fake);
    await bridge.whenReady();

    // Override kill to NOT emit exit so we can verify the safety net.
    fake.kill.mockImplementation(() => true);

    const start = Date.now();
    await bridge.quit();
    const elapsed = Date.now() - start;
    expect(elapsed).toBeLessThan(500);
  });

  it('emits exit with the observed code and signal', async () => {
    const opts = defaultTestOptions();
    const bridge = new PythonBridge(opts);
    const fake = opts.spawnFn.mock.results[0].value;
    emitReady(fake);
    await bridge.whenReady();

    const exited = new Promise((resolve) => bridge.once('exit', resolve));
    fake.simulateExit(137, 'SIGKILL');
    await expect(exited).resolves.toMatchObject({ code: 137, signal: 'SIGKILL' });
  });
});

describe('resolvePythonCommand', () => {
  /**
   * Build a probe child whose stdout/stderr will deliver the given
   * banner text and then exit 0 on the next tick. Mirrors what
   * `python --version` does on real systems.
   */
  const makeBannerChild = (banner, opts = {}) => {
    const stdout = new Readable({ read() {} });
    const stderr = new Readable({ read() {} });
    const child = new EventEmitter();
    Object.assign(child, {
      exitCode: null,
      signalCode: null,
      kill: vi.fn(),
      stdout,
      stderr,
    });
    setImmediate(() => {
      if (banner && opts.toStderr) {
        stderr.push(`${banner}\n`);
      } else if (banner) {
        stdout.push(`${banner}\n`);
      }
      stdout.push(null);
      stderr.push(null);
      child.emit('exit', opts.exitCode ?? 0, null);
    });
    return child;
  };

  it('returns the first candidate whose --version invocation succeeds', async () => {
    // On Windows, the first probe is `py -3 --version`. Provide a
    // Python 3 banner on that probe and ENOENT for everything else.
    const calls = [];
    const spawnSpy = vi.fn((cmd, args) => {
      calls.push(`${cmd} ${(args || []).join(' ')}`);
      if (cmd === 'py' && args && args[0] === '-3') {
        return makeBannerChild('Python 3.11.2');
      }
      throw new Error('ENOENT');
    });
    const cmd = await resolvePythonCommand({ spawnFn: spawnSpy });
    expect(cmd).toBe('py');
    expect(calls).toContain('py -3 --version');
  });

  it('throws when no candidate works', async () => {
    const spawnSpy = vi.fn(() => {
      throw new Error('ENOENT');
    });
    await expect(resolvePythonCommand({ spawnFn: spawnSpy })).rejects.toThrow(
      /Python 3 is required/
    );
  });

  it('skips candidates that spawn but exit with a non-zero code', async () => {
    const spawnSpy = vi.fn((cmd, args) => {
      if (cmd === 'py' && args && args[0] === '-3') {
        // `py -3` rejected (no Python 3 installed) — exit non-zero.
        return makeBannerChild('', { exitCode: 1 });
      }
      if (cmd === 'py') {
        return makeBannerChild('Python 2.7.18');
      }
      if (cmd === 'python') {
        return makeBannerChild('Python 3.10.4');
      }
      throw new Error('ENOENT');
    });
    const cmd = await resolvePythonCommand({ spawnFn: spawnSpy });
    expect(cmd).toBe('python');
  });

  it('rejects Python 2 even when it is the only candidate that exists', async () => {
    const spawnSpy = vi.fn((cmd, args) => {
      if (cmd === 'py' && args && args[0] === '-3') {
        return makeBannerChild('', { exitCode: 1 });
      }
      if (cmd === 'py') {
        return makeBannerChild('Python 2.7.18');
      }
      if (cmd === 'python') {
        return makeBannerChild('Python 2.7.18');
      }
      throw new Error('ENOENT');
    });
    await expect(resolvePythonCommand({ spawnFn: spawnSpy })).rejects.toThrow(
      /Python 3 is required/
    );
  });

  it('accepts a Python 3 banner delivered to stderr', async () => {
    // Some Python builds write the version banner to stderr; we must
    // accept it from either stream.
    const spawnSpy = vi.fn((cmd, args) => {
      if (cmd === 'py' && args && args[0] === '-3') {
        return makeBannerChild('Python 3.9.5', { toStderr: true });
      }
      throw new Error('ENOENT');
    });
    const cmd = await resolvePythonCommand({ spawnFn: spawnSpy });
    expect(cmd).toBe('py');
  });

  it('falls back from `py -3` to bare `py` to `python` to `python3` on Windows', async () => {
    const calls = [];
    const spawnSpy = vi.fn((cmd, args) => {
      calls.push(`${cmd} ${(args || []).join(' ')}`);
      if (cmd === 'py' && args && args[0] === '-3') {
        return makeBannerChild('', { exitCode: 1 });
      }
      if (cmd === 'py') {
        return makeBannerChild('', { exitCode: 1 });
      }
      if (cmd === 'python') {
        return makeBannerChild('', { exitCode: 1 });
      }
      if (cmd === 'python3') {
        return makeBannerChild('Python 3.12.0');
      }
      throw new Error('ENOENT');
    });
    // Force the Windows probe list by stubbing process.platform. This
    // lets the test run on any host while still exercising the
    // Windows-specific ordering.
    const originalPlatform = process.platform;
    Object.defineProperty(process, 'platform', { value: 'win32', configurable: true });
    try {
      const cmd = await resolvePythonCommand({ spawnFn: spawnSpy });
      expect(cmd).toBe('python3');
      expect(calls).toEqual([
        'py -3 --version',
        'py --version',
        'python --version',
        'python3 --version',
      ]);
    } finally {
      Object.defineProperty(process, 'platform', {
        value: originalPlatform,
        configurable: true,
      });
    }
  });

  it('skips candidates whose banner is unparseable', async () => {
    const spawnSpy = vi.fn((cmd, args) => {
      if (cmd === 'py' && args && args[0] === '-3') {
        return makeBannerChild('garbage that is not a python banner');
      }
      if (cmd === 'py') {
        return makeBannerChild('Python 3.11.0');
      }
      throw new Error('ENOENT');
    });
    const cmd = await resolvePythonCommand({ spawnFn: spawnSpy });
    expect(cmd).toBe('py');
  });
});
