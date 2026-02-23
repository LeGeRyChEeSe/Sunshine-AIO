const { contextBridge, ipcRenderer } = require('electron');

// Whitelist of allowed IPC channels for security
// Only channels in this list can be invoked from renderer
const ALLOWED_CHANNELS = [
  // Will be populated in Story 1.3 with actual Python backend IPC channels
  // Example: 'python:execute', 'python:get-status', etc.
];

// Validate that a channel is in the whitelist
const isChannelAllowed = (channel) => {
  return ALLOWED_CHANNELS.includes(channel);
};

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
    const subscription = (event, ...args) => {
      // Verify the event originates from the main process
      if (event.sender && !event.sender.isDestroyed()) {
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
});
