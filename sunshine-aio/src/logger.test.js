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
    const cyclic = {};
    cyclic.self = cyclic;
    const line = formatLogLine('warn', 'cyclic', cyclic, new Date('2026-01-01T00:00:00.000Z'));
    expect(line).toContain('[unserializable meta]');
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
    // Custom fs that reports a huge file size to trigger rotation on first write
    let writeCount = 0;
    const fakeFs = {
      existsSync: vi.fn((p) => {
        if (p.endsWith('sunshine-aio-2026-06-23.log')) return true;
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

  it('handles missing logs directory by creating it lazily (no throw)', async () => {
    const fresh = path.join(tempDir, 'fresh');
    const logger = createLogger({ logsDir: fresh, consoleLevel: 'error' });
    logger.info('hello');
    await logger.flush();
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
    const failingFs = {
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

    const logger = createLogger({
      logsDir: tempDir,
      consoleLevel: 'error',
      fs: failingFs,
      now: () => new Date('2026-06-23T10:00:00.000Z'),
    });

    expect(() => logger.error('boom')).not.toThrow();
    await logger.flush();
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
