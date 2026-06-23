const { contextBridge, ipcRenderer } = require('electron');

// Whitelist of allowed IPC channels for security
// Only channels in this list can be invoked from renderer
const ALLOWED_CHANNELS = [
  // Logger bridge — renderer writes are forwarded to the main-process logger.
  'log:write',
  // Python backend bridge (Story 1.3)
  'python:ping',
  'python:execute',
];

// Validate that a channel is in the whitelist
const isChannelAllowed = (channel) => {
  return ALLOWED_CHANNELS.includes(channel);
};

const VALID_LOG_LEVELS = new Set(['debug', 'info', 'warn', 'error']);

// Expose protected methods that allow the renderer process to use
// the ipcRenderer without exposing the entire object
contextBridge.exposeInMainWorld('electronAPI', {
  // IPC methods for Story 1.3 (Python backend integration)
  // TODO: Add actual channel names to ALLOWED_CHANNELS when implementing IPC
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
  // pythonPing: round-trip a ping to the Python bridge.
  //   Resolves with { ok: true, result: { result: 'pong', echo } } on success,
  //   or { ok: false, error } if the bridge is unavailable / Python is down.
  pythonPing: () => ipcRenderer.invoke('python:ping'),

  // pythonExecute: forward a typed command to the Python bridge.
  //   - cmd: command name (string, required)
  //   - params: optional command-specific parameters (must be JSON-serializable)
  // The main process enforces a 64KiB cap on params and rejects non-serializable
  // payloads so a misbehaving renderer cannot crash the bridge.
  pythonExecute: (cmd, params) => {
    const safeCmd = typeof cmd === 'string' ? cmd : '';
    if (!safeCmd) {
      return Promise.reject(new Error('pythonExecute: cmd must be a non-empty string'));
    }
    return ipcRenderer.invoke('python:execute', { cmd: safeCmd, params });
  },
});
