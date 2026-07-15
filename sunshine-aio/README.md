# Sunshine AIO

Windows tool for automating installation and configuration of game streaming components.

## Features

- Automated installation of Sunshine streaming server
- Virtual Display Driver configuration
- Playnite integration
- System tray support (minimize-to-tray, Open / Quit context menu)
- Windows notifications
- On-demand admin elevation for operations that require it

## Prerequisites

- Windows 10/11
- Node.js v20.20.0 (tested)
- npm 10.8.2 (tested)

## Development

```bash
# Install dependencies
npm install

# Start development server
npm run start

# Run unit tests
npm test

# Run linter
npm run lint

# Build for production
npm run make
```

## Admin Privileges

Sunshine-AIO needs administrator privileges for some operations
(service registration, Virtual Display Driver configuration, firewall
rules). The privilege model is split in two:

1. **Install-time** — `forge.config.js` sets `requireAdmin: true` on
   the Squirrel maker, so the installer itself runs elevated and can
   place files under `Program Files` and register Windows services.

2. **Runtime** — the launched app starts as the standard user. When
   the user attempts an operation that requires admin, the renderer
   can call `electronAPI.requestAdminElevation()` (or the user clicks
   the "Restart as administrator" button in Settings). The main
   process spawns `powershell.exe -Command "Start-Process -Verb RunAs
   -FilePath <exe>"` to trigger a UAC prompt and re-launches the app
   elevated. The elevated child writes a handshake marker file at
   startup so the parent only quits once it has evidence the new
   process actually launched (and was not, for instance, cancelled at
   the UAC prompt).

The `AppUserModelID` is set to `com.legerycheese.sunshine-aio` early
in `main.js` so Windows groups taskbar / toast notifications under a
stable identity.

## Tech Stack

- Electron Forge
- Vite
- JavaScript
- Vitest

## License

MIT
