const { contextBridge, ipcRenderer } = require('electron');

/**
 * Security invariants for this preload bridge — DO NOT weaken without PR review.
 *
 *  - WHITELIST-ONLY: every IPC entry point (`invoke`, `on`, `send`) must check
 *    `isChannelAllowed(channel)` against `ALLOWED_CHANNELS` BEFORE forwarding to
 *    `ipcRenderer`. Adding a new channel requires adding it here AND ensuring
 *    `ipcMain.handle` is registered in `src/main.js`.
 *  - SENDER ORIGIN: the `on()` listener must verify both `event.sender` (not
 *    destroyed) AND `event.senderFrame.url` matches an expected origin before
 *    invoking the renderer callback. A compromised renderer or future
 *    `<webview>` must not be able to deliver spoofed events.
 *  - NO RAW EVENT: callbacks must receive the IPC payload, not the raw
 *    `IpcRendererEvent`. Never expose `event.sender`, `event.senderFrame`, or
 *    `event.senderId` to renderer code.
 *  - ASAR INTEGRITY: this preload runs in a sandboxed, contextIsolated
 *    renderer. `electronAPI` is the ONLY supported surface for IPC.
 *
 * Story 1-1 ships this bridge with an EMPTY `ALLOWED_CHANNELS` whitelist by
 * design — IPC is intentionally inert until Story 1.3 introduces the Python
 * backend. See `README.md` for the public-facing note.
 */

// Whitelist of allowed IPC channels for security.
// ONLY channels in this list can be invoked from the renderer.
const ALLOWED_CHANNELS = [
  // Populated in Story 1.3 with Python backend IPC channels.
];

// Allowed origins for incoming IPC events. In dev, the renderer is served
// from the Vite dev server; in production, from the asar file:// bundle.
const getExpectedOrigins = () => {
  const origins = [];
  if (process.env.MAIN_WINDOW_VITE_DEV_SERVER_URL) {
    try {
      const u = new URL(process.env.MAIN_WINDOW_VITE_DEV_SERVER_URL);
      origins.push(`${u.protocol}//${u.host}`);
    } catch {
      // ignore malformed env var
    }
  }
  origins.push('file://');
  return origins;
};

// Validate that a channel is in the whitelist (internal helper only).
const isChannelAllowed = (channel) => ALLOWED_CHANNELS.includes(channel);

// Validate that an inbound event originates from a trusted frame.
const isEventFromTrustedOrigin = (event) => {
  if (!event || !event.sender || event.sender.isDestroyed()) {
    return false;
  }
  const frameUrl = event.senderFrame && event.senderFrame.url;
  if (!frameUrl) {
    return false;
  }
  return getExpectedOrigins().some((origin) => frameUrl.startsWith(origin));
};

// Expose protected methods that allow the renderer process to use
// ipcRenderer without exposing the entire object. The whitelist is empty for
// story 1-1, so every call rejects — this is intentional YAGNI scaffolding.
contextBridge.exposeInMainWorld('electronAPI', {
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
      return () => {};
    }
    // Subscription-based approach: filter by origin in addition to channel.
    const subscription = (event, ...args) => {
      if (isEventFromTrustedOrigin(event)) {
        callback(...args);
      } else {
        console.warn(`[PRELOAD] Dropped event from untrusted origin on channel: ${channel}`);
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
});
