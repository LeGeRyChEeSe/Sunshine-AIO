/**
 * Sunshine AIO Logger
 *
 * Simple dependency-free logger that:
 * - Writes timestamped log entries (ISO 8601) to a daily log file in logs/
 * - Mirrors entries to the console for development visibility
 * - Supports log levels: debug, info, warn, error
 * - Rotates log files when they exceed MAX_FILE_SIZE_BYTES
 *   and keeps at most MAX_FILES rotated files
 *
 * Public API:
 *   const logger = createLogger({ logsDir, consoleLevel })
 *   logger.debug(msg, meta?)
 *   logger.info(msg, meta?)
 *   logger.warn(msg, meta?)
 *   logger.error(msg, errOrMeta?)
 *   logger.flush()  -> Promise that resolves when pending writes are flushed
 *
 * The factory accepts options so tests can inject a temporary logsDir
 * and stub the file-system layer via the `fs` option.
 */

import fs from 'node:fs';
import path from 'node:path';

export const LOG_LEVELS = {
  debug: 10,
  info: 20,
  warn: 30,
  error: 40,
};

export const MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024; // 5 MB
export const MAX_FILES = 5; // keep up to 5 rotated backup files

/**
 * Format a log line.
 * Format: "YYYY-MM-DDTHH:mm:ss.sssZ LEVEL message" with optional metadata.
 * If an Error is passed as meta, the stack is appended on subsequent lines.
 */
export const formatLogLine = (level, message, meta, timestamp = new Date()) => {
  const ts = timestamp.toISOString();
  let line = `${ts} ${level.toUpperCase()} ${message}`;

  if (meta !== undefined && meta !== null) {
    if (meta instanceof Error) {
      const stack = meta.stack || `${meta.name}: ${meta.message}`;
      line += `\n${stack}`;
    } else if (typeof meta === 'object') {
      try {
        line += ` ${JSON.stringify(meta)}`;
      } catch {
        line += ` [unserializable meta]`;
      }
    } else {
      line += ` ${String(meta)}`;
    }
  }

  return line;
};

/**
 * Pick the active log file name based on the current date.
 * Returns a file name like "sunshine-aio-2026-06-23.log".
 */
export const getLogFileName = (date = new Date()) => {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  return `sunshine-aio-${y}-${m}-${d}.log`;
};

/**
 * Rotate existing log files. The current file becomes .1, .1 becomes .2, etc.
 * Files beyond MAX_FILES are deleted.
 *
 * Exposed for testing.
 */
export const rotateFiles = (logsDir, fileName, fileSystem = fs) => {
  const currentPath = path.join(logsDir, fileName);

  // Delete the oldest if it would exceed MAX_FILES rotated backups
  const oldestPath = path.join(logsDir, `${fileName}.${MAX_FILES}`);
  if (fileSystem.existsSync(oldestPath)) {
    fileSystem.unlinkSync(oldestPath);
  }

  // Shift .N -> .(N+1) from highest to lowest
  for (let i = MAX_FILES - 1; i >= 1; i -= 1) {
    const from = path.join(logsDir, `${fileName}.${i}`);
    const to = path.join(logsDir, `${fileName}.${i + 1}`);
    if (fileSystem.existsSync(from)) {
      fileSystem.renameSync(from, to);
    }
  }

  // Move current to .1
  if (fileSystem.existsSync(currentPath)) {
    const rotatedPath = path.join(logsDir, `${fileName}.1`);
    fileSystem.renameSync(currentPath, rotatedPath);
  }
};

const ensureLogsDir = (logsDir, fileSystem = fs) => {
  if (!fileSystem.existsSync(logsDir)) {
    fileSystem.mkdirSync(logsDir, { recursive: true });
  }
};

const consoleColorFor = (level) => {
  switch (level) {
    case 'debug':
      return '[90m'; // bright black
    case 'info':
      return '[36m'; // cyan
    case 'warn':
      return '[33m'; // yellow
    case 'error':
      return '[31m'; // red
    default:
      return '';
  }
};

const RESET_COLOR = '[0m';

/**
 * Build a logger instance.
 *
 * @param {object} options
 * @param {string} options.logsDir          Directory where log files are stored.
 * @param {string} [options.consoleLevel]   Minimum level echoed to console (default 'info').
 * @param {object} [options.fs]             Filesystem module (overridable for tests).
 * @param {Function} [options.now]          Clock function returning Date (overridable for tests).
 */
export const createLogger = ({
  logsDir,
  consoleLevel = 'info',
  fs: injectedFs = fs,
  now = () => new Date(),
} = {}) => {
  if (!logsDir) {
    throw new Error('createLogger: logsDir is required');
  }

  ensureLogsDir(logsDir, injectedFs);

  let pendingWrites = Promise.resolve();

  const consoleMinLevel = LOG_LEVELS[consoleLevel] ?? LOG_LEVELS.info;

  /**
   * Write a log entry. Returns the formatted line and persists it asynchronously.
   */
  const write = (level, message, meta) => {
    const timestamp = now();
    const line = formatLogLine(level, message, meta, timestamp);

    // Console output (synchronous)
    if (LOG_LEVELS[level] >= consoleMinLevel) {
      const color = consoleColorFor(level);
      const stream = level === 'error' || level === 'warn' ? process.stderr : process.stdout;
      stream.write(`${color}${line}${RESET_COLOR}\n`);
    }

    // File output (asynchronous, sequential via pendingWrites)
    const fileName = getLogFileName(timestamp);
    const filePath = path.join(logsDir, fileName);

    pendingWrites = pendingWrites
      .then(
        () =>
          new Promise((resolve) => {
            try {
              // Check size and rotate if needed
              if (
                injectedFs.existsSync(filePath) &&
                injectedFs.statSync(filePath).size >= MAX_FILE_SIZE_BYTES
              ) {
                rotateFiles(logsDir, fileName, injectedFs);
              }
              injectedFs.appendFileSync(filePath, `${line}\n`);
            } catch (err) {
              // Last-resort: surface to stderr but never throw to caller
              process.stderr.write(`[LOGGER] Failed to write log: ${err.message}\n`);
            }
            resolve();
          })
      )
      .catch(() => {
        // Swallow errors from the chain itself
      });

    return line;
  };

  return {
    debug: (message, meta) => write('debug', message, meta),
    info: (message, meta) => write('info', message, meta),
    warn: (message, meta) => write('warn', message, meta),
    error: (message, meta) => write('error', message, meta),
    flush: () => pendingWrites,
    getLogsDir: () => logsDir,
  };
};

/**
 * Resolve a sensible default logs directory relative to the application.
 * Uses process.cwd() so the location matches the project root at runtime.
 */
export const defaultLogsDir = () => path.join(process.cwd(), 'logs');

/**
 * Convenience: create a logger pointing at the project's logs/ directory.
 */
export const createDefaultLogger = (overrides = {}) =>
  createLogger({ logsDir: defaultLogsDir(), ...overrides });
