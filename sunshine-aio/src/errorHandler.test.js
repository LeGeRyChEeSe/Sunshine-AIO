/**
 * Tests for the renderer's error-handling helpers (Story 1.2).
 *
 * These cover the parts of the error pipeline that are testable without
 * a DOM: the friendly message mapper, the log payload normalizer, and the
 * format helper. The DOM glue (window listeners, toast rendering) lives
 * in renderer.js and is covered by manual smoke tests.
 */

import { describe, expect, it } from 'vitest';

import {
  buildFriendlyMessage,
  formatReportedError,
  normalizeLogLevel,
  toLogPayload,
} from './errorHandler.js';

describe('buildFriendlyMessage', () => {
  it('returns a generic, non-technical message for a plain Error', () => {
    const msg = buildFriendlyMessage(new Error('cannot read property foo of undefined'));
    expect(msg).toBe(
      'An unexpected error occurred. The technical details have been saved to the log file.'
    );
    // Critically: the raw error message is NOT leaked to the user.
    expect(msg).not.toContain('cannot read property foo');
  });

  it('returns a TypeError-specific friendly message', () => {
    expect(buildFriendlyMessage(new TypeError('x is not a function'))).toBe(
      'Something went wrong while processing data. Please try again.'
    );
  });

  it('returns a network-specific friendly message when the error mentions network', () => {
    expect(buildFriendlyMessage(new Error('Network request failed'))).toBe(
      'A network problem was detected. Please check your connection and try again.'
    );
    expect(buildFriendlyMessage(new Error('failed to fetch resource'))).toBe(
      'A network problem was detected. Please check your connection and try again.'
    );
  });

  it('handles string and non-Error inputs gracefully', () => {
    expect(buildFriendlyMessage('boom')).toBe('An unexpected error occurred. Please try again.');
    expect(buildFriendlyMessage(null)).toBe(
      'An unexpected error occurred. The technical details have been saved to the log file.'
    );
    expect(buildFriendlyMessage(undefined)).toBe(
      'An unexpected error occurred. The technical details have been saved to the log file.'
    );
    expect(buildFriendlyMessage(42)).toBe(
      'An unexpected error occurred. The technical details have been saved to the log file.'
    );
  });
});

describe('normalizeLogLevel', () => {
  it('passes through valid levels', () => {
    expect(normalizeLogLevel('debug')).toBe('debug');
    expect(normalizeLogLevel('info')).toBe('info');
    expect(normalizeLogLevel('warn')).toBe('warn');
    expect(normalizeLogLevel('error')).toBe('error');
  });

  it('falls back to "info" for unknown levels', () => {
    expect(normalizeLogLevel('fatal')).toBe('info');
    expect(normalizeLogLevel('')).toBe('info');
    expect(normalizeLogLevel(undefined)).toBe('info');
    expect(normalizeLogLevel(null)).toBe('info');
    expect(normalizeLogLevel(42)).toBe('info');
  });
});

describe('toLogPayload', () => {
  it('serialises an Error to a safe payload (no full stack)', () => {
    const err = new Error('boom');
    const payload = toLogPayload('error', 'something failed', err);
    expect(payload.level).toBe('error');
    expect(payload.message).toBe('something failed');
    expect(payload.meta).toEqual({ name: 'Error', message: 'boom' });
    // The full stack is intentionally not sent over IPC.
    expect(payload.meta.stack).toBeUndefined();
  });

  it('serialises non-Error values into a `value` field', () => {
    expect(toLogPayload('warn', 'weird', 'a string').meta).toEqual({ value: 'a string' });
    expect(toLogPayload('warn', 'weird', 42).meta).toEqual({ value: '42' });
  });

  it('passes plain objects through unchanged', () => {
    const obj = { code: 'E_FAIL', retryable: true };
    expect(toLogPayload('error', 'op failed', obj).meta).toBe(obj);
  });

  it('omits meta when no error is provided', () => {
    const payload = toLogPayload('info', 'just info', undefined);
    expect(payload.meta).toBeUndefined();
  });

  it('coerces non-string messages to strings', () => {
    expect(toLogPayload('info', 42, undefined).message).toBe('42');
    expect(toLogPayload('info', null, undefined).message).toBe('');
    expect(toLogPayload('info', undefined, undefined).message).toBe('');
  });

  it('normalises an unknown log level to "info"', () => {
    expect(toLogPayload('fatal', 'x', undefined).level).toBe('info');
  });
});

describe('formatReportedError', () => {
  it('produces a single-line summary including level and message', () => {
    const text = formatReportedError(toLogPayload('error', 'crash', new Error('boom')));
    expect(text).toBe('[error] crash (Error: boom)');
  });

  it('omits the error suffix when there is no meta', () => {
    expect(formatReportedError(toLogPayload('info', 'hello', undefined))).toBe('[info] hello');
  });

  it('returns an empty string for a missing payload', () => {
    expect(formatReportedError(undefined)).toBe('');
    expect(formatReportedError(null)).toBe('');
  });
});
