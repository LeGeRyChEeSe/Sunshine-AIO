# Sunshine AIO

Windows tool for automating installation and configuration of game streaming
components (Sunshine, Virtual Display Driver, Playnite).

## Story 1-1 Scope

This commit ships **only** the project scaffold:

- Electron Forge + Vite build setup
- Main process (`src/main.js`) with hardened `BrowserWindow` defaults
- Preload bridge (`src/preload.js`) — IPC is intentionally inert (empty
  channel whitelist); it will be populated in Story 1.3 when the Python
  backend is introduced
- Minimal renderer entry (`src/renderer.js`) importing `styles.css`
- Vitest test framework with smoke tests for the scaffold
- ESLint + Prettier configuration

The full Python backend, system tray, and Windows notifications are introduced
in later stories — see the roadmap below.

## Planned Features (not yet shipped)

- Python backend integration (Story 1.3)
- System tray support (Story 1.4)
- Windows notifications (Story 1.5)

## Prerequisites

- Windows 10/11
- Node.js v20.20.0 (tested)
- npm 10.8.2 (tested)

## Development

```bash
# Install dependencies
npm install

# Start the Electron app in dev mode (Vite HMR enabled)
npm run start

# Lint the source tree
npm run lint

# Run unit tests (Vitest)
npm test

# Build a Windows distributable (Squirrel installer + zip)
npm run make
```

The Python backend will be introduced in Story 1.3 as a sidecar process
spawned by the main process.

## Tech Stack

- Electron Forge (build + packaging)
- Vite (dev server + bundling)
- JavaScript (ESM) — TypeScript was deliberately not adopted
- Vitest (unit tests)
- ESLint + Prettier (lint/format)

## License

MIT