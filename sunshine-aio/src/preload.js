const { contextBridge, ipcRenderer } = require('electron');

// Strict allowlist of Python commands the renderer can ask the bridge
// to dispatch. This MUST stay in sync with the COMMANDS dict in
// python_bridge_server.py: every command name on the Python side must
// appear here, and only those names may be sent through `python:execute`.
// Treat this as a security boundary — adding a destructive command to
// the Python side without also adding it here would silently widen the
// IPC attack surface, so keep both changes in the same code review.
const ALLOWED_PYTHON_CMDS = new Set(['ping']);

// Maximum nesting depth for `params`. Mirrors the log:write meta cap so
// a renderer cannot pin the main process with a deeply nested object.
// The main process enforces a 64 KiB size cap; this cap is in addition,
// not a replacement.
const MAX_PARAMS_DEPTH = 5;

const VALID_LOG_LEVELS = new Set(['debug', 'info', 'warn', 'error']);

// Expose protected methods that allow the renderer process to use
// the ipcRenderer without exposing the entire object.
//
// SECURITY: we deliberately do NOT expose a generic `invoke` /
// `send` / `on` / `isChannelAllowed` pass-through on
// `window.electronAPI`. The previous implementation did, which gave
// the renderer a generic IPC pass-through surface — even with a
// channel allowlist, a future Story that adds a new channel and
// forgets to update the allowlist would silently drop calls, AND
// an XSS payload or a compromised npm dependency in the renderer
// could enumerate the bridge and probe arbitrary channel names.
//
// Instead, every IPC channel is exposed as a dedicated, typed method
// (`log`, `pythonPing`, `pythonExecute`). If a future Story needs
// another channel, add a typed method here — DO NOT add a generic
// pass-through.
contextBridge.exposeInMainWorld('electronAPI', {
  // Logger bridge (Story 1.2). Forwards renderer log messages to the main
  // process so they end up in the same log file as main-process entries.
  // - level: 'debug' | 'info' | 'warn' | 'error' (invalid → 'info')
  // - message: string
  // - meta: optional structured detail (string or plain object)
  log: (level, message, meta) => {
    const safeLevel = VALID_LOG_LEVELS.has(level) ? level : 'info';
    const safeMessage = typeof message === 'string' ? message : String(message ?? '');
    return ipcRenderer.invoke('log:write', { level: safeLevel, message: safeMessage, meta });
  },

  // Logger bridge (Story 1.2). Forwards renderer log messages to the main
  // process so they end up in the same log file as main-process entries.
  // - level: 'debug' | 'info' | 'warn' | 'error' (invalid → 'info')
  // - message: string
  // - meta: optional structured detail (string or plain object)
  log: (level, message, meta) => {
    const safeLevel = VALID_LOG_LEVELS.has(level) ? level : 'info';
    const safeMessage = typeof message === 'string' ? message : String(message ?? '');
    return ipcRenderer.invoke('log:write', { level: safeLevel, message: safeMessage, meta });
  },

  // Python backend bridge (Story 1.3). Narrow, typed surface — never
  // expose a raw channel-based invoke because that would re-introduce
  // every channel in ALLOWED_CHANNELS to the renderer.
  //
  // pythonPing: round-trip a ping to the Python bridge. Takes no
  //   parameters. Resolves with { ok: true, result: { result: 'pong' } }
  //   on success, or { ok: false, error } if the bridge is unavailable
  //   / Python is down. The result payload contains ONLY the
  //   `result: 'pong'` field — params are intentionally not echoed
  //   back so a future caller cannot accidentally route sensitive data
  //   through the no-op params slot.
  pythonPing: () => ipcRenderer.invoke('python:ping'),

  // pythonExecute: forward a typed command to the Python bridge.
  //   - cmd: command name (string, required, must be in ALLOWED_PYTHON_CMDS)
  //   - params: optional command-specific parameters (must be a plain
  //            JSON value with nesting depth <= MAX_PARAMS_DEPTH)
  // The main process enforces a 64KiB cap on params and rejects non-serializable
  // payloads so a misbehaving renderer cannot crash the bridge. The cmd
  // allowlist is enforced HERE and AGAIN in the main process so a
  // compromised preload (or a future bug that bypasses this check) still
  // cannot dispatch arbitrary commands to the Python script.
  pythonExecute: (cmd, params) => {
    const safeCmd = typeof cmd === 'string' ? cmd : '';
    if (!safeCmd) {
      return Promise.reject(new Error('pythonExecute: cmd must be a non-empty string'));
    }
    if (!ALLOWED_PYTHON_CMDS.has(safeCmd)) {
      return Promise.reject(new Error(`pythonExecute: cmd "${safeCmd}" is not in the allowlist`));
    }
    // Validate params shape BEFORE forwarding to the main process. A
    // cyclic reference would only be caught by the main process's
    // JSON.stringify size check, which throws a generic error. A depth
    // / shape check here gives a much clearer "params too deep" or
    // "params must be a plain JSON value" rejection. We intentionally
    // do NOT cap size here — the main process is the source of truth
    // for the 64 KiB envelope limit.
    if (params !== undefined && params !== null) {
      if (typeof params !== 'object') {
        // primitives are fine
      } else {
        const depth = paramsDepth(params);
        if (depth > MAX_PARAMS_DEPTH) {
          return Promise.reject(
            new Error(`pythonExecute: params nesting depth ${depth} exceeds ${MAX_PARAMS_DEPTH}`)
          );
        }
        // Reject if serialization would fail (catches cycles, BigInt, etc.)
        try {
          JSON.stringify(params);
        } catch (err) {
          return Promise.reject(
            new Error(
              `pythonExecute: params are not JSON-serializable: ${err && err.message ? err.message : String(err)}`
            )
          );
        }
      }
    }
    return ipcRenderer.invoke('python:execute', { cmd: safeCmd, params });
  },
});

/**
 * Compute the maximum nesting depth of an arbitrary JSON value.
 * Objects and arrays increment the depth; primitives do not.
 * Cyclic references are bounded by a small internal cycle tracker so a
 * pathological input cannot hang the renderer.
 */
const paramsDepth = (value, current = 0, seen) => {
  if (current > MAX_PARAMS_DEPTH) return current;
  if (value === null || typeof value !== 'object') return current;
  const tracker = seen || new WeakSet();
  if (tracker.has(value)) return current; // cycle — return current depth
  tracker.add(value);
  if (Array.isArray(value)) {
    let max = current + 1;
    for (const item of value) {
      const d = paramsDepth(item, current + 1, tracker);
      if (d > max) max = d;
    }
    return max;
  }
  let max = current + 1;
  for (const key of Object.keys(value)) {
    const d = paramsDepth(value[key], current + 1, tracker);
    if (d > max) max = d;
  }
  return max;
};
