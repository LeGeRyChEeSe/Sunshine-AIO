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
    // Bundle the Python bridge script as an extra resource so it is
    // available at <resources>/python_bridge_server.py in the packaged
    // app. Without this, the script is packed into the ASAR (which
    // cannot be `exec`d / spawned from) and the bridge fails to start
    // in production. The `extraResource` directive places the file
    // outside the ASAR so `spawn(python, [scriptPath])` works.
    extraResource: [
      {
        from: 'src/python_bridge_server.py',
        to: 'python_bridge_server.py',
      },
    ],
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
