/**
 * Tests for the shared redaction + sanitization helpers.
 *
 * The `redaction.js` module is shared by `main.js` (which uses it
 * for `log:write` meta) and `notifications.js` (which uses it for
 * toast title / body logging). These tests pin down the behavior so
 * a future refactor cannot accidentally widen the redaction surface.
 */

import { describe, expect, it } from 'vitest';

import {
  capStringLength,
  redactSecrets,
  sanitizeUserString,
  SECRET_KEYS,
  stripControlChars,
} from './redaction.js';

describe('SECRET_KEYS', () => {
  it('includes common credential keys', () => {
    for (const key of ['password', 'token', 'secret', 'apikey', 'authorization']) {
      expect(SECRET_KEYS.has(key)).toBe(true);
    }
  });

  it('is lowercased for case-insensitive matching', () => {
    // The set itself contains lowercased entries; matching happens
    // by lowercasing the input key in the implementation.
    expect(SECRET_KEYS.has('Password')).toBe(false);
  });
});

describe('redactSecrets', () => {
  it('redacts well-known keys', () => {
    const out = redactSecrets({ password: 'hunter2', token: 'abc', visible: 'ok' });
    expect(out.password).toBe('[redacted]');
    expect(out.token).toBe('[redacted]');
    expect(out.visible).toBe('ok');
  });

  it('redacts Bearer tokens in strings', () => {
    expect(redactSecrets('Bearer abcdefghijklmnopqrstuvwxyz0123456789')).toBe('[redacted]');
  });

  it('redacts JWT-shaped strings', () => {
    // The matcher requires two `.`-separated 20+ char segments.
    // A real JWT is `header.payload.signature`; we use a
    // header.payload here since the signature is the third segment
    // and would push us past the test intent.
    const jwt =
      'aaaabbbbccccddddeeeeffffgggghhhhh.iiiijjjjkkkkllllmmmmnnnnooooppppqqqqrrrrssssttttuuuuvvvv';
    expect(redactSecrets(jwt)).toBe('[redacted]');
  });

  it('walks arrays', () => {
    const out = redactSecrets([{ token: 'x' }, { visible: 'y' }]);
    expect(out[0].token).toBe('[redacted]');
    expect(out[1].visible).toBe('y');
  });

  it('preserves non-secret strings', () => {
    expect(redactSecrets('just a friendly message')).toBe('just a friendly message');
  });

  it('caps recursion depth to REDACT_MAX_DEPTH', () => {
    // Build a chain longer than REDACT_MAX_DEPTH (8). We rely on
    // the marker `[redacted: too deep]` appearing in the output to
    // confirm the cap is enforced.
    let nested = { leaf: 'visible' };
    for (let i = 0; i < 20; i += 1) {
      nested = { inner: nested };
    }
    const out = redactSecrets(nested);
    expect(JSON.stringify(out)).toContain('[redacted: too deep]');
  });
});

describe('stripControlChars', () => {
  it('removes NUL and other control bytes', () => {
    expect(stripControlChars('hello\x00world')).toBe('helloworld');
  });

  it('removes CR and LF', () => {
    expect(stripControlChars('line1\r\nline2')).toBe('line1line2');
  });

  it('removes DEL (0x7F)', () => {
    expect(stripControlChars('hithere')).toBe('hithere');
  });

  it('returns empty string for non-string input', () => {
    expect(stripControlChars(null)).toBe('');
    expect(stripControlChars(undefined)).toBe('');
    expect(stripControlChars(123)).toBe('');
  });

  it('preserves normal printable characters', () => {
    expect(stripControlChars('Hello, world! 123')).toBe('Hello, world! 123');
  });
});

describe('capStringLength', () => {
  it('caps long strings to maxLen', () => {
    expect(capStringLength('x'.repeat(500), 100)).toHaveLength(100);
  });

  it('passes through short strings unchanged', () => {
    expect(capStringLength('hi', 100)).toBe('hi');
  });

  it('returns empty string for non-strings', () => {
    expect(capStringLength(null, 100)).toBe('');
    expect(capStringLength(undefined, 100)).toBe('');
  });
});

describe('sanitizeUserString', () => {
  it('strips control characters AND caps length', () => {
    const dirty = 'hello\x00world'.repeat(100); // ~1200 chars
    const result = sanitizeUserString(dirty, 200);
    expect(result).toHaveLength(200);
    expect(result).not.toContain('\x00');
  });

  it('uses 200 as the default cap', () => {
    expect(sanitizeUserString('a'.repeat(500))).toHaveLength(200);
  });
});
