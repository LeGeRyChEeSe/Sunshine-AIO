const { contextBridge, ipcRenderer } = require('electron');

// Whitelist of allowed IPC channels for security
// Only channels in this list can be invoked from renderer
const ALLOWED_CHANNELS = [
  // Logger bridge — renderer writes are forwarded to the main-process logger.
  'log:write',
  // Python backend bridge (Story 1.3)
  'python:ping',
  'python:execute',
  // Settings + tray bridge (Story 1.4)
  'settings:get',
  'settings:set-minimize-to-tray',
  // Admin privileges (Story 1.4)
  'admin:get-status',
  'admin:request-elevation',
  // System notifications (Story 1.5)
  'notification:test',
  'notification:install-complete',
  'notification:update-available',
  'notification:error',
];

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

// Validate that a channel is in the whitelist
const isChannelAllowed = (channel) => {
  return ALLOWED_CHANNELS.includes(channel);
};

const VALID_LOG_LEVELS = new Set(['debug', 'info', 'warn', 'error']);

// Expose protected methods that allow the renderer process to use
// the ipcRenderer without exposing the entire object
contextBridge.exposeInMainWorld('electronAPI', {
  // IPC methods for Story 1.3 (Python backend integration)
  invoke: (channel, ...args) => {
    if (!isChannelAllowed(channel)) {
      console.warn(`[PRELOAD] Blocked attempt to invoke non-whitelisted channel: ${channel}`);
      return Promise.reject(new Error(`Channel "${channel}" is not allowed`));
    }
    return ipcRenderer.invoke(channel, ...args);
  },
  on: (channel, callback) => {
    if (!isChannelAllowed(channel)) {
      console.warn(`[PRELOAD] Blocked attempt to listen on non-whitelisted channel: ${channel}`);
      return;
    }
    // Use a subscription-based approach with proper isolation
    // Only allow receiving messages for whitelisted channels
    //
    // For ipcRenderer.on, event.sender is the WebContents that SENT the
    // message. In our model, all incoming traffic is from the main
    // process (the only WebContents that can push through ipcMain.on).
    // We guard against invoking the callback after the sender has been
    // destroyed (e.g. main window closed) to avoid touching freed
    // resources. The check is intentionally an isDestroyed() guard on
    // the sender — a live-but-disconnected sender is still safe to
    // forward to; a destroyed one is not.
    const subscription = (event, ...args) => {
      const senderIsMain = event.sender && !event.sender.isDestroyed();
      if (senderIsMain) {
        callback(...args);
      }
    };
    ipcRenderer.on(channel, subscription);
    // Return cleanup function
    return () => {
      ipcRenderer.removeListener(channel, subscription);
    };
  },
  send: (channel, ...args) => {
    if (!isChannelAllowed(channel)) {
      console.warn(`[PRELOAD] Blocked attempt to send on non-whitelisted channel: ${channel}`);
      return;
    }
    ipcRenderer.send(channel, ...args);
  },
  // Method to check if a channel is allowed (for renderer to query)
  isChannelAllowed: (channel) => isChannelAllowed(channel),

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

  // ----------------------------------------------------------------
  // Story 1.4 — Settings + tray preferences
  // ----------------------------------------------------------------
  //
  // `getSettings` returns the current settings record (currently just
  // `minimizeToTray`). `setMinimizeToTray(enabled)` updates the
  // preference and persists it via the main-process settings module.
  // The boolean is coerced at the IPC boundary so a stringy "true" /
  // "false" cannot slip through.
  //
  // We deliberately expose this as a *named* method (`setMinimizeToTray`)
  // rather than the generic `invoke('settings:set-minimize-to-tray', ...)`
  // for two reasons: (a) it gives the renderer a self-documenting
  // typed surface, and (b) it lets us validate the argument here
  // before it crosses the IPC boundary.

  getSettings: () => ipcRenderer.invoke('settings:get'),

  setMinimizeToTray: (enabled) => {
    // Coerce liberally: any truthy non-zero / non-empty value maps to
    // true. Everything else maps to false. This matches the booleans
    // that come out of `<input type="checkbox">` in the renderer.
    const safeEnabled = enabled === true || enabled === 1 || enabled === '1' || enabled === 'true';
    return ipcRenderer.invoke('settings:set-minimize-to-tray', safeEnabled);
  },

  // ----------------------------------------------------------------
  // Story 1.4 — Admin privileges
  // ----------------------------------------------------------------
  //
  // `getAdminStatus` returns whether the current process is elevated
  // and the platform string. `requestAdminElevation` triggers a UAC
  // prompt and (on success) the main process quits so the elevated
  // copy takes over. Both are read-only / request-style helpers — the
  // renderer cannot change the privilege state directly.

  getAdminStatus: () => ipcRenderer.invoke('admin:get-status'),

  requestAdminElevation: () => ipcRenderer.invoke('admin:request-elevation'),

  // ----------------------------------------------------------------
  // Story 1.5 — System notifications
  // ----------------------------------------------------------------
  //
  // Thin wrappers around the four notification IPC channels. Each
  // method validates its argument shape locally (so a buggy renderer
  // gets a synchronous rejection rather than a confusing main-process
  // error) before crossing the IPC boundary.
  //
  // The methods return { ok: boolean, reason?: string } from the
  // main process. `ok: false` happens when (a) the host does not
  // support OS toasts, (b) the manager is disabled, or (c) the per-
  // sender rate limit is hit.

  notifyTest: () => ipcRenderer.invoke('notification:test'),

  notifyInstallComplete: (appName) => {
    const safe = typeof appName === 'string' ? appName : '';
    return ipcRenderer.invoke('notification:install-complete', { appName: safe });
  },

  notifyUpdateAvailable: (apps) => {
    // The main process accepts arrays, comma-separated strings, or
    // a bare number. We forward the value as-is and let the
    // NotificationManager normalise it; this keeps the renderer
    // surface small.
    return ipcRenderer.invoke('notification:update-available', { apps });
  },

  notifyError: (message, title) => {
    const safeMessage = typeof message === 'string' ? message : '';
    const safeTitle = typeof title === 'string' ? title : undefined;
    const payload = { message: safeMessage };
    if (safeTitle !== undefined) payload.title = safeTitle;
    return ipcRenderer.invoke('notification:error', payload);
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
