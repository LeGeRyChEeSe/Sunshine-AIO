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
 * If the Error has a `cause` (ES2022 Error chaining), the cause chain is
 * appended recursively with a depth limit so post-mortem diagnosis can
 * trace the full causal chain.
 */
const MAX_CAUSE_DEPTH = 10;

/**
 * Serialize an Error (or any value) for inclusion in a log line. Recurses
 * into `cause` properties to preserve ES2022 error chains.
 *
 * Returns a newline-prefixed line describing `err`. If `err` has a `.cause`,
 * the chain continues recursively, each link prefixed with "Caused by:".
 */
export const formatErrorChain = (err, depth = 0) => {
  if (depth >= MAX_CAUSE_DEPTH) {
    return `\n[cause chain truncated at depth ${MAX_CAUSE_DEPTH}]`;
  }
  if (err === undefined || err === null) {
    return '';
  }
  let head;
  if (err instanceof Error) {
    const stack = err.stack || `${err.name}: ${err.message}`;
    head = stack;
  } else if (typeof err === 'object') {
    head = String(err);
  } else {
    head = String(err);
  }

  let line = `\nCaused by: ${head}`;
  if (err && typeof err === 'object' && err.cause) {
    line += formatErrorChain(err.cause, depth + 1);
  }
  return line;
};

/**
 * Try to serialize a value as JSON. Returns null on failure so the caller
 * can fall back gracefully. Uses a replacer that converts BigInt to a
 * string with a trailing 'n' (a common JSON convention) so a payload
 * containing BigInts does not drop the whole entry. As a last resort, a
 * manual enumerable-properties walk is attempted to preserve at least the
 * top-level shape of the meta.
 */
export const safeStringify = (value) => {
  // 1) Fast path: try the standard replacer that handles BigInt and most
  //    other non-serializable scalars.
  try {
    return JSON.stringify(value, (_k, v) => (typeof v === 'bigint' ? `${v.toString()}n` : v));
  } catch {
    // fall through
  }

  // 2) Fallback: enumerate own properties manually. Skip function values
  //    and circular references (tracked by a WeakSet). This is best-effort
  //    and may lose nested data, but it preserves the top-level shape so
  //    post-mortem diagnosis is still possible.
  if (!value || typeof value !== 'object') {
    return null;
  }
  try {
    const seen = new WeakSet();
    const walk = (v) => {
      if (v === null) return null;
      if (typeof v === 'bigint') return `${v.toString()}n`;
      if (typeof v === 'function') return '[Function]';
      if (typeof v === 'undefined') return '[undefined]';
      if (typeof v === 'symbol') return '[Symbol]';
      if (typeof v !== 'object') return v;
      if (seen.has(v)) return '[Circular]';
      seen.add(v);
      if (Array.isArray(v)) {
        return v.map((item) => walk(item));
      }
      const out = {};
      for (const key of Object.keys(v)) {
        try {
          out[key] = walk(v[key]);
        } catch {
          out[key] = '[Unserializable]';
        }
      }
      return out;
    };
    return JSON.stringify(walk(value));
  } catch {
    return null;
  }
};

export const formatLogLine = (level, message, meta, timestamp = new Date()) => {
  const ts = timestamp.toISOString();
  let line = `${ts} ${level.toUpperCase()} ${message}`;

  if (meta !== undefined && meta !== null) {
    if (meta instanceof Error) {
      const stack = meta.stack || `${meta.name}: ${meta.message}`;
      line += `\n${stack}`;
      // Preserve ES2022 Error.cause chain so the full causal context survives.
      if (meta.cause) {
        line += formatErrorChain(meta.cause);
      }
    } else if (typeof meta === 'object') {
      // Errors can also arrive wrapped in a plain object literal — preserve
      // any `cause` field that holds an Error or a serializable value.
      if (meta.cause !== undefined && meta.cause !== null) {
        const serialized = safeStringify(meta);
        if (serialized !== null) {
          line += ` ${serialized}`;
        } else {
          line += ` [unserializable meta]`;
        }
        line += formatErrorChain(meta.cause);
      } else {
        const serialized = safeStringify(meta);
        if (serialized !== null) {
          line += ` ${serialized}`;
        } else {
          line += ` [unserializable meta]`;
        }
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
 *
 * Uses UTC components so the file name matches the ISO 8601 timestamp
 * emitted on each line. Mixing local-time file names with UTC timestamps
 * would scatter late-evening entries into the "wrong" file around midnight.
 */
export const getLogFileName = (date = new Date()) => {
  const y = date.getUTCFullYear();
  const m = String(date.getUTCMonth() + 1).padStart(2, '0');
  const d = String(date.getUTCDate()).padStart(2, '0');
  return `sunshine-aio-${y}-${m}-${d}.log`;
};

/**
 * Rename a single file, swallowing transient errors. On Windows, antivirus
 * or file-locking can fail an individual rename; logging the failure lets
 * the caller continue rather than corrupting the rotation chain silently.
 */
const safeRename = (fileSystem, from, to) => {
  try {
    fileSystem.renameSync(from, to);
    return true;
  } catch (err) {
    try {
      process.stderr.write(
        `[LOGGER] Failed to rename ${from} -> ${to}: ${err && err.message ? err.message : String(err)}\n`
      );
    } catch {
      // stderr itself failed; nothing more we can do
    }
    return false;
  }
};

/**
 * Rotate existing log files. The current file becomes .1, .1 becomes .2, etc.
 * Files beyond MAX_FILES are deleted.
 *
 * Each rename is wrapped in its own try/catch so a single failure (e.g.
 * antivirus locking one file on Windows) does not leave the rotation chain
 * in a half-shifted state where the next rotation duplicates entries.
 *
 * Exposed for testing.
 */
export const rotateFiles = (logsDir, fileName, fileSystem = fs) => {
  const currentPath = path.join(logsDir, fileName);

  // Delete the oldest if it would exceed MAX_FILES rotated backups
  const oldestPath = path.join(logsDir, `${fileName}.${MAX_FILES}`);
  if (fileSystem.existsSync(oldestPath)) {
    try {
      fileSystem.unlinkSync(oldestPath);
    } catch (err) {
      try {
        process.stderr.write(
          `[LOGGER] Failed to delete oldest log ${oldestPath}: ${err && err.message ? err.message : String(err)}\n`
        );
      } catch {
        // nothing more we can do
      }
    }
  }

  // Shift .N -> .(N+1) from highest to lowest
  for (let i = MAX_FILES - 1; i >= 1; i -= 1) {
    const from = path.join(logsDir, `${fileName}.${i}`);
    const to = path.join(logsDir, `${fileName}.${i + 1}`);
    if (fileSystem.existsSync(from)) {
      safeRename(fileSystem, from, to);
    }
  }

  // Move current to .1
  if (fileSystem.existsSync(currentPath)) {
    const rotatedPath = path.join(logsDir, `${fileName}.1`);
    safeRename(fileSystem, currentPath, rotatedPath);
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

  // Detect concurrent Sunshine AIO instances. Two processes writing to the
  // same log file can interleave bytes and corrupt rotation. We try to
  // create a lock file with the 'wx' flag (fail if exists); if it already
  // exists we log a one-shot warning and continue (best-effort, not a hard
  // block — a stale lock from a crashed process would otherwise prevent
  // logging entirely). The lock file is best-effort and is intentionally
  // NOT deleted on process exit because Windows file-locking semantics make
  // the lock useful for the lifetime of the process.
  const lockPath = path.join(logsDir, '.sunshine-aio.lock');
  let concurrentInstanceWarned = false;
  try {
    if (typeof injectedFs.openSync === 'function') {
      const fd = injectedFs.openSync(lockPath, 'wx');
      try {
        if (typeof fd === 'number' && typeof injectedFs.writeSync === 'function') {
          injectedFs.writeSync(fd, String(process.pid));
        }
      } finally {
        if (typeof fd === 'number' && typeof injectedFs.closeSync === 'function') {
          try {
            injectedFs.closeSync(fd);
          } catch {
            // ignore
          }
        }
      }
    }
  } catch (err) {
    if (err && (err.code === 'EEXIST' || err.code === 'EACCES' || err.code === 'EBUSY')) {
      concurrentInstanceWarned = true;
    }
  }

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

    if (concurrentInstanceWarned) {
      // Reset the flag so the warning is emitted at most once per process
      // (per logger instance). This avoids flooding the log when a second
      // instance is running in parallel.
      concurrentInstanceWarned = false;
      try {
        process.stderr.write(
          '[LOGGER] Another Sunshine AIO instance appears to be writing to this logs directory. Concurrent writes can corrupt the log file.\n'
        );
      } catch {
        // ignore
      }
    }

    // Helper: try to read the file size. Returns null on failure so a
    // statSync error during rotation does not block the subsequent
    // appendFileSync. Rotation is best-effort: if we cannot determine
    // the size we still attempt the write and rely on the post-append
    // check to catch oversize files (best effort).
    const tryGetFileSize = (filePath) => {
      try {
        if (injectedFs.existsSync(filePath)) {
          return injectedFs.statSync(filePath).size;
        }
      } catch (err) {
        try {
          process.stderr.write(
            `[LOGGER] statSync failed for ${filePath}: ${err && err.message ? err.message : String(err)}\n`
          );
        } catch {
          // ignore
        }
      }
      return null;
    };

    pendingWrites = pendingWrites
      .then(
        () =>
          new Promise((resolve) => {
            try {
              // Check size and rotate if needed. We rotate before the append
              // when the existing file is already at or above the threshold,
              // and again AFTER the append if the single write pushed us
              // over the threshold on its own (e.g. a massive meta payload).
              // A failure in the size check is isolated: we still attempt
              // the append rather than dropping the log entry.
              const preSize = tryGetFileSize(filePath);
              if (preSize !== null && preSize >= MAX_FILE_SIZE_BYTES) {
                rotateFiles(logsDir, fileName, injectedFs);
              }
              injectedFs.appendFileSync(filePath, `${line}\n`);
              const postSize = tryGetFileSize(filePath);
              if (postSize !== null && postSize >= MAX_FILE_SIZE_BYTES) {
                rotateFiles(logsDir, fileName, injectedFs);
              }
            } catch (err) {
              // Last-resort: surface to stderr but never throw to caller
              process.stderr.write(`[LOGGER] Failed to write log: ${err.message}\n`);
            }
            resolve();
          })
      )
      .catch((chainErr) => {
        // The chain itself rejected (e.g. a bug in formatLogLine or in the
        // Promise constructor above). This is distinct from the per-write
        // try/catch above and signals a real defect. Surface the error and
        // a stack trace to stderr so an external tool (or the next run)
        // can pick it up, then reset the chain to a fresh resolved
        // promise so subsequent writes are not pinned to the poisoned
        // chain forever.
        try {
          const stack = chainErr && chainErr.stack ? chainErr.stack : String(chainErr);
          process.stderr.write(`[LOGGER] pendingWrites chain rejected: ${stack}\n`);
        } catch {
          // stderr itself failed; nothing more we can do
        }
        // Returning undefined here lets the next `.then` in the chain
        // continue. We deliberately do not rethrow so the user's writes
        // keep going.
        return undefined;
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
