const { FusesPlugin } = require('@electron-forge/plugin-fuses');
const { FuseV1Options, FuseVersion } = require('@electron/fuses');

module.exports = {
  packagerConfig: {
    asar: true,
    name: 'Sunshine AIO',
    executableName: 'sunshine-aio',
    appCopyright: 'Copyright 2026 LeGeRyChEeSe',
    win32metadata: {
      CompanyName: 'LeGeRyChEeSe',
      FileDescription: 'Sunshine AIO - Game Streaming Tool',
      ProductName: 'Sunshine AIO',
    },
  },
  rebuildConfig: {},
  makers: [
    {
      name: '@electron-forge/maker-squirrel',
      config: {
        name: 'SunshineAIO',
        authors: 'LeGeRyChEeSe',
        description: 'Windows tool for automating installation and configuration of game streaming components',
      },
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
        // `build` can specify multiple entry builds, which can be Main process, Preload scripts, Worker process, etc.
        // If you are familiar with Vite configuration, it will look really familiar.
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
    // Fuses are used to enable/disable various Electron functionality
    // at package time, before code signing the application
    new FusesPlugin({
      version: FuseVersion.V1,
      [FuseV1Options.RunAsNode]: false,
      [FuseV1Options.EnableCookieEncryption]: true,
      [FuseV1Options.EnableNodeOptionsEnvironmentVariable]: false,
      [FuseV1Options.EnableNodeCliInspectArguments]: false,
      [FuseV1Options.EnableEmbeddedAsarIntegrityValidation]: true,
      [FuseV1Options.OnlyLoadAppFromAsar]: false,
    }),
  ],
};
