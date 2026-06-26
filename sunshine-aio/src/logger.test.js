/**
 * Tests for the logger module.
 *
 * These tests cover the Acceptance Criteria for Story 1.2:
 *   - AC1: A log file is created in logs/ at start-up
 *   - AC2: Log entries include ISO timestamp + level + message
 *   - AC3: Error logs capture the stack trace
 *   - AC4: Rotation kicks in when the file exceeds 5MB
 *   - AC5: Levels (info/warn/error/debug) work correctly
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

import {
  createLogger,
  defaultLogsDir,
  formatErrorChain,
  formatLogLine,
  getLogFileName,
  LOG_LEVELS,
  MAX_FILE_SIZE_BYTES,
  MAX_FILES,
  rotateFiles,
  safeLog,
} from './logger.js';

const makeTempDir = () => fs.mkdtempSync(path.join(os.tmpdir(), 'sunshine-logger-'));

const cleanupTempDir = (dir) => {
  if (fs.existsSync(dir)) {
    fs.rmSync(dir, { recursive: true, force: true });
  }
};

const readFile = (filePath) => fs.readFileSync(filePath, 'utf8');

describe('formatLogLine', () => {
  it('produces a line with ISO timestamp, level and message', () => {
    const fixed = new Date('2026-06-23T10:30:45.123Z');
    const line = formatLogLine('info', 'App started', undefined, fixed);
    expect(line).toBe('2026-06-23T10:30:45.123Z INFO App started');
  });

  it('uppercases the level', () => {
    const line = formatLogLine('error', 'boom', undefined, new Date('2026-01-01T00:00:00.000Z'));
    expect(line.startsWith('2026-01-01T00:00:00.000Z ERROR ')).toBe(true);
  });

  it('serializes plain objects as JSON metadata', () => {
    const line = formatLogLine('info', 'evt', { userId: 42 }, new Date('2026-01-01T00:00:00.000Z'));
    expect(line).toContain(' INFO evt {"userId":42}');
  });

  it('appends the Error stack when an Error is passed', () => {
    const err = new Error('something failed');
    const line = formatLogLine('error', 'crash', err, new Date('2026-01-01T00:00:00.000Z'));
    expect(line).toContain('ERROR crash');
    expect(line).toContain(err.stack);
  });

  it('falls back gracefully when metadata cannot be serialized', () => {
    // Circular references are recovered with a '[Circular]' marker so the
    // surrounding shape survives. The classic '[unserializable meta]'
    // fallback is only used as a last resort.
    const cyclic = {};
    cyclic.self = cyclic;
    const line = formatLogLine('warn', 'cyclic', cyclic, new Date('2026-01-01T00:00:00.000Z'));
    expect(line).toContain('[Circular]');
  });

  it('serializes BigInt values rather than dropping the whole entry', () => {
    const meta = { count: 42n, label: 'big' };
    const line = formatLogLine('info', 'big', meta, new Date('2026-01-01T00:00:00.000Z'));
    // BigInt is rendered with a trailing 'n' (common JSON convention) so
    // it is clearly distinguishable from a regular number in the log.
    expect(line).toContain('42n');
    expect(line).not.toContain('[unserializable meta]');
  });

  it('preserves ES2022 Error.cause chain on an Error meta', () => {
    const root = new Error('root');
    const wrapped = new Error('wrapped', { cause: root });
    const line = formatLogLine('error', 'crash', wrapped, new Date('2026-01-01T00:00:00.000Z'));
    expect(line).toContain('Caused by:');
    expect(line).toContain('root');
  });

  it('recurses into nested Error.cause chains', () => {
    const root = new Error('level-3');
    const mid = new Error('level-2', { cause: root });
    const top = new Error('level-1', { cause: mid });
    const line = formatLogLine('error', 'crash', top, new Date('2026-01-01T00:00:00.000Z'));
    expect(line).toContain('level-1');
    expect(line).toContain('level-2');
    expect(line).toContain('level-3');
  });

  it('truncates very deep Error.cause chains safely', () => {
    let err = new Error('leaf');
    for (let i = 0; i < 25; i += 1) {
      err = new Error(`wrap-${i}`, { cause: err });
    }
    const line = formatLogLine('error', 'crash', err, new Date('2026-01-01T00:00:00.000Z'));
    expect(line).toContain('[cause chain truncated at depth');
  });

  it('preserves a cause on a plain-object meta', () => {
    const inner = new Error('inner cause');
    const meta = { reason: 'explosion', cause: inner };
    const line = formatLogLine('error', 'crash', meta, new Date('2026-01-01T00:00:00.000Z'));
    expect(line).toContain('"reason":"explosion"');
    expect(line).toContain('Caused by:');
    expect(line).toContain('inner cause');
  });
});

describe('formatErrorChain', () => {
  it('returns an empty string for nullish input', () => {
    expect(formatErrorChain(null)).toBe('');
    expect(formatErrorChain(undefined)).toBe('');
  });

  it('serializes non-Error values as a Caused by: line', () => {
    expect(formatErrorChain('disk gone')).toContain('Caused by: disk gone');
    expect(formatErrorChain(42)).toContain('Caused by: 42');
  });
});

describe('getLogFileName', () => {
  it('uses YYYY-MM-DD pattern', () => {
    expect(getLogFileName(new Date('2026-06-23T15:00:00Z'))).toBe('sunshine-aio-2026-06-23.log');
    expect(getLogFileName(new Date('2026-01-01T00:00:00Z'))).toBe('sunshine-aio-2026-01-01.log');
  });
});

describe('LOG_LEVELS', () => {
  it('orders levels so error is highest', () => {
    expect(LOG_LEVELS.debug).toBeLessThan(LOG_LEVELS.info);
    expect(LOG_LEVELS.info).toBeLessThan(LOG_LEVELS.warn);
    expect(LOG_LEVELS.warn).toBeLessThan(LOG_LEVELS.error);
  });
});

describe('createLogger', () => {
  let tempDir;
  let originalCwd;

  beforeEach(() => {
    tempDir = makeTempDir();
    originalCwd = process.cwd();
    // Suppress console output during tests
    vi.spyOn(process.stdout, 'write').mockImplementation(() => true);
    vi.spyOn(process.stderr, 'write').mockImplementation(() => true);
  });

  afterEach(() => {
    cleanupTempDir(tempDir);
    process.chdir(originalCwd);
    vi.restoreAllMocks();
  });

  it('throws when logsDir is missing', () => {
    expect(() => createLogger({ logsDir: '' })).toThrow(/logsDir is required/);
  });

  it('creates the logs directory if it does not exist (AC: log file created at startup)', async () => {
    const nested = path.join(tempDir, 'nested', 'logs');
    createLogger({ logsDir: nested, consoleLevel: 'error' });
    expect(fs.existsSync(nested)).toBe(true);
  });

  it('writes info/warn/error entries to the dated log file', async () => {
    const logger = createLogger({
      logsDir: tempDir,
      consoleLevel: 'error',
      now: () => new Date('2026-06-23T10:00:00.000Z'),
    });

    logger.info('App started');
    logger.warn('Heads up');
    logger.error('Something broke');
    await logger.flush();

    const filePath = path.join(tempDir, 'sunshine-aio-2026-06-23.log');
    expect(fs.existsSync(filePath)).toBe(true);

    const content = readFile(filePath);
    expect(content).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z INFO App started$/m);
    expect(content).toMatch(/WARN Heads up/);
    expect(content).toMatch(/ERROR Something broke/);
  });

  it('writes the line with the exact ISO timestamp provided', async () => {
    const logger = createLogger({
      logsDir: tempDir,
      consoleLevel: 'error',
      now: () => new Date('2026-06-23T10:30:45.123Z'),
    });
    logger.info('ping');
    await logger.flush();

    const content = readFile(path.join(tempDir, 'sunshine-aio-2026-06-23.log'));
    expect(content).toContain('2026-06-23T10:30:45.123Z INFO ping');
  });

  it('captures Error stack traces in error logs (AC: error includes stack)', async () => {
    const logger = createLogger({
      logsDir: tempDir,
      consoleLevel: 'error',
      now: () => new Date('2026-06-23T10:00:00.000Z'),
    });
    const err = new Error('boom!');
    err.stack = 'Error: boom!\n    at Object.<anonymous> (test.js:1:1)';
    logger.error('Operation failed', err);
    await logger.flush();

    const content = readFile(path.join(tempDir, 'sunshine-aio-2026-06-23.log'));
    expect(content).toContain('ERROR Operation failed');
    expect(content).toContain('Error: boom!');
    expect(content).toContain('at Object.<anonymous> (test.js:1:1)');
  });

  it('does not write to console for levels below consoleLevel', async () => {
    const stdoutSpy = vi.spyOn(process.stdout, 'write');
    const stderrSpy = vi.spyOn(process.stderr, 'write');

    const logger = createLogger({ logsDir: tempDir, consoleLevel: 'warn' });
    logger.debug('d');
    logger.info('i');
    logger.warn('w');
    logger.error('e');

    // debug+info suppressed, warn+error emitted
    const allCalls = [...stdoutSpy.mock.calls, ...stderrSpy.mock.calls]
      .map((c) => String(c[0]))
      .join('');
    expect(allCalls).not.toContain('DEBUG d');
    expect(allCalls).not.toContain('INFO i');
    expect(allCalls).toContain('WARN w');
    expect(allCalls).toContain('ERROR e');
    await logger.flush();
  });

  it('rotates the file when MAX_FILE_SIZE_BYTES is exceeded (AC: rotation)', async () => {
    // Custom fs that reports a huge file size to trigger rotation on first
    // write. The existsSync is true for the current log file AND for all
    // the rotation slots (.1 .. .MAX_FILES) so the full shift chain
    // executes: .4 -> .5, .3 -> .4, ..., current -> .1, and the oldest
    // (.5) is unlinked. A narrower stub would only exercise the
    // current->.1 step and silently miss a regression in the shift loop.
    let writeCount = 0;
    const fileBase = 'sunshine-aio-2026-06-23.log';
    const fakeFs = {
      existsSync: vi.fn((p) => {
        const base = path.basename(p);
        if (base === fileBase) return true;
        for (let i = 1; i <= MAX_FILES; i += 1) {
          if (base === `${fileBase}.${i}`) return true;
        }
        return false;
      }),
      statSync: vi.fn(() => ({ size: MAX_FILE_SIZE_BYTES })),
      appendFileSync: vi.fn(() => {
        writeCount += 1;
      }),
      renameSync: vi.fn(),
      unlinkSync: vi.fn(),
      mkdirSync: vi.fn(),
      rmSync: vi.fn(),
      readFileSync: vi.fn(),
      writeFileSync: vi.fn(),
      openSync: vi.fn(() => {
        throw Object.assign(new Error('exists'), { code: 'EEXIST' });
      }),
      writeSync: vi.fn(),
      closeSync: vi.fn(),
    };

    const logger = createLogger({
      logsDir: tempDir,
      consoleLevel: 'error',
      fs: fakeFs,
      now: () => new Date('2026-06-23T10:00:00.000Z'),
    });

    logger.info('trigger rotation');
    await logger.flush();

    expect(fakeFs.renameSync).toHaveBeenCalled();
    expect(writeCount).toBeGreaterThanOrEqual(1);

    // Verify the full shift chain executed in the right order: .4 -> .5,
    // .3 -> .4, .2 -> .3, .1 -> .2, current -> .1. The .4->.5 step
    // would not happen if the loop order is wrong, so we check it
    // explicitly.
    const renameCalls = fakeFs.renameSync.mock.calls.map((c) => [
      path.basename(c[0]),
      path.basename(c[1]),
    ]);
    const currentToOne = renameCalls.find(
      ([from, to]) => from === fileBase && to === `${fileBase}.1`
    );
    expect(currentToOne).toBeDefined();
    const fourToFive = renameCalls.find(
      ([from, to]) => from === `${fileBase}.4` && to === `${fileBase}.5`
    );
    expect(fourToFive).toBeDefined();

    // Oldest backup (.5) must be unlinked before the shift so it does
    // not get overwritten by the .4 -> .5 rename.
    const unlinkCalls = fakeFs.unlinkSync.mock.calls.map((c) => path.basename(c[0]));
    expect(unlinkCalls).toContain(`${fileBase}.${MAX_FILES}`);
  });

  it('rotates again if a single append pushed the file over MAX_FILE_SIZE_BYTES', async () => {
    // Track file size across appends: start under threshold, jump over it on
    // the first append. The second statSync (post-append) should trigger a
    // rotation that the pre-append check missed.
    const sizes = [0, MAX_FILE_SIZE_BYTES + 10];
    let statIndex = 0;
    const fakeFs = {
      existsSync: vi.fn((p) => {
        if (p.endsWith('sunshine-aio-2026-06-23.log')) return true;
        return false;
      }),
      statSync: vi.fn(() => ({ size: sizes[Math.min(statIndex++, sizes.length - 1)] })),
      appendFileSync: vi.fn(),
      renameSync: vi.fn(),
      unlinkSync: vi.fn(),
      mkdirSync: vi.fn(),
      rmSync: vi.fn(),
      readFileSync: vi.fn(),
      writeFileSync: vi.fn(),
    };

    const logger = createLogger({
      logsDir: tempDir,
      consoleLevel: 'error',
      fs: fakeFs,
      now: () => new Date('2026-06-23T10:00:00.000Z'),
    });

    logger.info('massive single write');
    await logger.flush();

    // The append alone pushed the file over the threshold, so a rotation
    // had to happen even though the pre-append check saw size === 0.
    expect(fakeFs.renameSync).toHaveBeenCalled();
    // statSync was invoked at least twice (pre- and post-append check).
    expect(fakeFs.statSync.mock.calls.length).toBeGreaterThanOrEqual(2);
  });

  it('rotateFiles deletes the oldest backup once MAX_FILES is exceeded', () => {
    const fakeFs = {
      existsSync: vi.fn(() => true),
      renameSync: vi.fn(),
      unlinkSync: vi.fn(),
    };

    rotateFiles(tempDir, 'sunshine-aio-2026-06-23.log', fakeFs);

    // Oldest (.MAX_FILES) is removed
    const unlinkCalls = fakeFs.unlinkSync.mock.calls.map((c) => path.basename(c[0]));
    expect(unlinkCalls).toContain(`sunshine-aio-2026-06-23.log.${MAX_FILES}`);
    // .4 gets renamed to .5, .3 to .4, ..., current to .1
    expect(fakeFs.renameSync).toHaveBeenCalled();
  });

  it('creates the logs directory synchronously in constructor (not lazily)', async () => {
    // The directory must exist after createLogger returns, before any
    // write() call. This is the documented behavior — not lazy creation.
    const fresh = path.join(tempDir, 'fresh');
    expect(fs.existsSync(fresh)).toBe(false);
    createLogger({ logsDir: fresh, consoleLevel: 'error' });
    expect(fs.existsSync(fresh)).toBe(true);
  });

  it('returns the formatted line from the logger methods', async () => {
    const logger = createLogger({
      logsDir: tempDir,
      consoleLevel: 'error',
      now: () => new Date('2026-06-23T10:00:00.000Z'),
    });
    const line = logger.info('returned');
    expect(line).toContain('INFO returned');
    await logger.flush();
  });
  it('exposes getLogsDir() pointing at the configured directory', async () => {
    const logger = createLogger({ logsDir: tempDir, consoleLevel: 'error' });
    expect(logger.getLogsDir()).toBe(tempDir);
    await logger.flush();
  });

  it('survives filesystem write failures without throwing to the caller', async () => {
    // Two distinct failure modes to cover:
    //   (a) existsSync false -> no statSync, appendFileSync throws.
    //   (b) existsSync true, statSync throws during the size check.
    // In both, logger.error() must not throw to the caller, and the
    // pendingWrites chain must RESOLVE (not reject) so subsequent
    // writes are not pinned to a poisoned chain.
    const failingFsA = {
      existsSync: () => false,
      statSync: () => {
        throw new Error('disk gone');
      },
      appendFileSync: () => {
        throw new Error('disk gone');
      },
      mkdirSync: () => {},
      renameSync: () => {},
      unlinkSync: () => {},
    };

    const loggerA = createLogger({
      logsDir: tempDir,
      consoleLevel: 'error',
      fs: failingFsA,
      now: () => new Date('2026-06-23T10:00:00.000Z'),
    });

    expect(() => loggerA.error('boom')).not.toThrow();
    // The flush() promise must resolve, not reject — that is the
    // guarantee that the chain has not been poisoned.
    await expect(loggerA.flush()).resolves.not.toThrow();

    // (b) existsSync true, statSync throws during the rotation size-check.
    // The try/catch around the rotation block must absorb the error AND
    // the subsequent appendFileSync must still execute. This guards
    // against a regression where a statSync failure would short-circuit
    // the write entirely.
    const failingFsB = {
      existsSync: () => true,
      statSync: () => {
        throw new Error('disk gone');
      },
      appendFileSync: vi.fn(),
      renameSync: vi.fn(),
      unlinkSync: vi.fn(),
      mkdirSync: () => {},
    };

    const loggerB = createLogger({
      logsDir: tempDir,
      consoleLevel: 'error',
      fs: failingFsB,
      now: () => new Date('2026-06-23T10:00:00.000Z'),
    });

    expect(() => loggerB.error('boom-2')).not.toThrow();
    await loggerB.flush();
    // Despite the failing statSync, appendFileSync must still be called —
    // the per-write try/catch absorbs the statSync error and the code
    // falls through to the append.
    expect(failingFsB.appendFileSync).toHaveBeenCalled();
  });

  it('recovers from a stale lock by overwriting when the recorded PID is dead', () => {
    // Regression: the previous lock-acquisition strategy could leave
    // a stale lock file on disk after a hard crash. The new strategy
    // reads the recorded PID inside the lock file and overwrites it
    // when the process is no longer alive (so a fresh instance can
    // boot without seeing a phantom "Another instance is running"
    // warning).
    const lockPath = path.join(tempDir, '.sunshine-aio.lock');
    // Pre-populate the lock file with a PID that cannot possibly be
    // alive (PID 0 / negative). The fake fs reports it as existing.
    const deadPid = '999999';
    let openCalls = 0;
    const fakeFs = {
      existsSync: vi.fn((p) => p === lockPath || p.endsWith('.log')),
      statSync: vi.fn(() => ({ size: 0 })),
      appendFileSync: vi.fn(),
      renameSync: vi.fn(),
      unlinkSync: vi.fn(),
      mkdirSync: vi.fn(),
      rmSync: vi.fn(),
      readFileSync: vi.fn((p) => (p === lockPath ? deadPid : '')),
      writeFileSync: vi.fn(),
      openSync: vi.fn(() => {
        openCalls += 1;
        // First call (initial 'wx' on the existing lock) throws
        // EEXIST. Second call (after stale-PID recovery) succeeds
        // and returns a numeric fd.
        if (openCalls === 1) {
          throw Object.assign(new Error('exists'), { code: 'EEXIST' });
        }
        return 42;
      }),
      writeSync: vi.fn(),
      closeSync: vi.fn(),
    };

    createLogger({
      logsDir: tempDir,
      consoleLevel: 'error',
      fs: fakeFs,
      now: () => new Date('2026-06-23T10:00:00.000Z'),
    });

    // The stale lock must have been unlinked...
    expect(fakeFs.unlinkSync).toHaveBeenCalledWith(lockPath);
    // ...and the lock then re-acquired via a fresh 'wx' open.
    expect(openCalls).toBeGreaterThanOrEqual(2);
  });

  it('does NOT overwrite the lock when the recorded PID is alive', () => {
    // If the recorded PID is still alive, the lock must be left in
    // place so the two processes do not both log to the same file.
    // We use a PID we know is alive on every platform: the current
    // process's own PID. process.kill(pid, 0) returns true for self.
    const lockPath = path.join(tempDir, '.sunshine-aio.lock');
    const livePid = String(process.pid);
    const fakeFs = {
      existsSync: vi.fn((p) => p === lockPath || p.endsWith('.log')),
      statSync: vi.fn(() => ({ size: 0 })),
      appendFileSync: vi.fn(),
      renameSync: vi.fn(),
      unlinkSync: vi.fn(),
      mkdirSync: vi.fn(),
      rmSync: vi.fn(),
      readFileSync: vi.fn((p) => (p === lockPath ? livePid : '')),
      writeFileSync: vi.fn(),
      openSync: vi.fn(() => {
        throw Object.assign(new Error('exists'), { code: 'EEXIST' });
      }),
      writeSync: vi.fn(),
      closeSync: vi.fn(),
    };

    createLogger({
      logsDir: tempDir,
      consoleLevel: 'error',
      fs: fakeFs,
      now: () => new Date('2026-06-23T10:00:00.000Z'),
    });

    // The lock must NOT have been unlinked because the recorded PID
    // is the current process (which is obviously alive).
    const unlinkCalls = fakeFs.unlinkSync.mock.calls.map((c) => c[0]);
    expect(unlinkCalls).not.toContain(lockPath);
  });
});

describe('defaultLogsDir', () => {
  it('returns a logs path under the current working directory', () => {
    const dir = defaultLogsDir();
    expect(dir).toMatch(/[\\/]logs$/);
  });
});

describe('integration: console output streams', () => {
  beforeEach(() => {
    vi.spyOn(process.stdout, 'write').mockImplementation(() => true);
    vi.spyOn(process.stderr, 'write').mockImplementation(() => true);
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('writes error and warn to stderr, info and debug to stdout', async () => {
    const tempDir = makeTempDir();
    try {
      const logger = createLogger({ logsDir: tempDir, consoleLevel: 'debug' });
      const stdoutSpy = vi.spyOn(process.stdout, 'write');
      const stderrSpy = vi.spyOn(process.stderr, 'write');

      logger.debug('d');
      logger.info('i');
      logger.warn('w');
      logger.error('e');

      const stdoutText = stdoutSpy.mock.calls.map((c) => String(c[0])).join('');
      const stderrText = stderrSpy.mock.calls.map((c) => String(c[0])).join('');

      expect(stdoutText).toContain('INFO i');
      expect(stdoutText).toContain('DEBUG d');
      expect(stderrText).toContain('WARN w');
      expect(stderrText).toContain('ERROR e');
      await logger.flush();
    } finally {
      cleanupTempDir(tempDir);
    }
  });
});

describe('safeLog', () => {
  it('is a no-op when logger is falsy', () => {
    expect(() => safeLog(null, 'info', 'msg')).not.toThrow();
    expect(() => safeLog(undefined, 'warn', 'msg', { a: 1 })).not.toThrow();
  });

  it('is a no-op when the requested level is missing', () => {
    const logger = { info: () => {} };
    expect(() => safeLog(logger, 'warn', 'msg')).not.toThrow();
    // logger.warn was never invoked, so the test cannot directly
    // assert on it — but if safeLog had thrown the test would fail.
  });

  it('forwards message and meta when the level exists', () => {
    const fn = vi.fn();
    const logger = { info: fn };
    safeLog(logger, 'info', 'evt', { foo: 'bar' });
    expect(fn).toHaveBeenCalledWith('evt', { foo: 'bar' });
  });

  it('swallows exceptions thrown by the logger', () => {
    const logger = {
      info: () => {
        throw new Error('boom');
      },
    };
    expect(() => safeLog(logger, 'info', 'evt')).not.toThrow();
  });
});
