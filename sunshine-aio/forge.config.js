const { FusesPlugin } = require('@electron-forge/plugin-fuses');
const { FuseV1Options, FuseVersion } = require('@electron/fuses');

// Shared metadata for all makers in this single-bundle Windows distribution.
const BASE_METADATA = {
  name: 'SunshineAIO',
  authors: 'LeGeRyChEeSe',
  description: 'Windows tool for automating installation and configuration of game streaming components',
};

module.exports = {
  packagerConfig: {
    asar: true,
    // When the Python backend is bundled (Story 1.3+), add:
    //   asarUnpack: ['**/*.exe', '**/*.py', '**/python/**']
    // so the sidecar scripts and binaries can be spawned directly on Windows.
    // Native modules are auto-unpacked by @electron-forge/plugin-auto-unpack-natives.
    name: 'Sunshine AIO',
    executableName: 'sunshine-aio',
    appCopyright: 'Copyright 2026 LeGeRyChEeSe',
    win32metadata: {
      CompanyName: 'LeGeRyChEeSe',
      FileDescription: 'Sunshine AIO - Game Streaming Tool',
      ProductName: 'Sunshine AIO',
    },
  },
  makers: [
    {
      name: '@electron-forge/maker-squirrel',
      config: BASE_METADATA,
    },
    {
      name: '@electron-forge/maker-zip',
      platforms: ['win32'],
    },
  ],
  plugins: [
    {
      name: '@electron-forge/plugin-vite',
      config: {
        // `build` can specify multiple entry builds (main, preload, workers, ...).
        build: [
          {
            entry: 'src/main.js',
            target: 'main',
          },
          {
            entry: 'src/preload.js',
            target: 'preload',
          },
        ],
        renderer: [
          {
            name: 'main_window',
          },
        ],
      },
    },
    // Fuses are applied at package time, before code signing.
    // OnlyLoadAppFromAsar is intentionally true: this is a single-bundle
    // Windows distribution without auto-update, so we forbid loading the app
    // from outside the asar (prevents entry-point hijack by a dropped file
    // next to sunshine-aio.exe). EnableEmbeddedAsarIntegrityValidation adds
    // a complementary integrity check.
    new FusesPlugin({
      version: FuseVersion.V1,
      [FuseV1Options.RunAsNode]: false,
      [FuseV1Options.EnableCookieEncryption]: true,
      [FuseV1Options.EnableNodeOptionsEnvironmentVariable]: false,
      [FuseV1Options.EnableNodeCliInspectArguments]: false,
      [FuseV1Options.EnableEmbeddedAsarIntegrityValidation]: true,
      [FuseV1Options.OnlyLoadAppFromAsar]: true,
    }),
  ],
};