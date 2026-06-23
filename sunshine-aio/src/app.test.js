/**
 * Smoke tests for Sunshine AIO scaffold.
 *
 * Story 1-1 ships only the project scaffold (main, preload, renderer, forge
 * config). IPC channels are intentionally inert in this story — the
 * `ALLOWED_CHANNELS` whitelist is empty by design and will be populated in
 * Story 1.3 when the Python backend is introduced.
 *
 * The tests below verify what story 1-1 actually delivers:
 *   - forge.config.js loads and exposes the expected Electron Forge shape
 *   - package.json scripts referenced by the docs resolve
 *   - preload.js source declares the expected electronAPI surface and the
 *     channel whitelist guards every IPC entry point
 *   - CSP in index.html blocks remote script sources
 *
 * @see https://vitest.dev/guide/
 * @see https://www.electronjs.org/docs/latest/api/ipc-main
 */

import { describe, it, expect } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';

const repoRoot = path.resolve(__dirname, '..');
const readFile = (rel) => fs.readFileSync(path.join(repoRoot, rel), 'utf8');

describe('Sunshine AIO scaffold (story 1-1)', () => {
  describe('Project metadata', () => {
    it('package.json declares the expected scripts', () => {
      const pkg = JSON.parse(readFile('package.json'));
      expect(pkg.scripts.start).toBe('electron-forge start');
      expect(pkg.scripts.make).toBe('electron-forge make');
      expect(pkg.scripts.test).toBe('vitest run');
      expect(pkg.scripts.lint).toBeDefined();
    });

    it('forge.config.js loads and configures Vite + FusesPlugin', () => {
      const require = createRequire(path.join(repoRoot, 'package.json'));
      // Stub the electron-forge CLI plugins at require time so the config
      // can be loaded in a plain Node test environment.
      const stubNames = [
        '@electron-forge/plugin-fuses',
        '@electron-forge/plugin-vite',
        '@electron/fuses',
      ];
      const Module = require('node:module');
      const originalResolve = Module._resolveFilename;
      Module._resolveFilename = function patchedResolve(request, parent, ...rest) {
        if (stubNames.includes(request)) {
          return request;
        }
        return originalResolve.call(this, request, parent, ...rest);
      };
      const originalLoad = Module._load;
      Module._load = function patchedLoad(request, parent, ...rest) {
        if (request === '@electron-forge/plugin-fuses') {
          return {
            FusesPlugin: class FusesPlugin {
              constructor(cfg) {
                this.name = '@electron-forge/plugin-fuses';
                this.cfg = cfg;
              }
            },
          };
        }
        if (request === '@electron-forge/plugin-vite') {
          return { name: '@electron-forge/plugin-vite' };
        }
        if (request === '@electron/fuses') {
          return {
            FuseVersion: { V1: 1 },
            FuseV1Options: new Proxy({}, { get: (_t, prop) => prop }),
          };
        }
        return originalLoad.call(this, request, parent, ...rest);
      };
      try {
        const config = require(path.join(repoRoot, 'forge.config.js'));
        expect(config.packagerConfig.asar).toBe(true);
        const pluginNames = config.plugins.map((p) => (typeof p === 'string' ? p : p.name));
        expect(pluginNames).toContain('@electron-forge/plugin-vite');
        expect(pluginNames).toContain('@electron-forge/plugin-fuses');
        const fuses = config.plugins.find((p) => p && p.name === '@electron-forge/plugin-fuses');
        // Either explicit object FusesPlugin or constructed class instance.
        const fusesCfg =
          fuses && (fuses.cfg || fuses.cfg || fuses.constructor?.name ? fuses.cfg : null);
        expect(fuses).toBeTruthy();
        expect(typeof fusesCfg === 'object' && fusesCfg !== null).toBe(true);
      } finally {
        Module._resolveFilename = originalResolve;
        Module._load = originalLoad;
      }
    });
  });

  describe('preload.js IPC surface', () => {
    const source = readFile('src/preload.js');

    it('uses contextBridge.exposeInMainWorld with name "electronAPI"', () => {
      expect(source).toMatch(/contextBridge\.exposeInMainWorld\(\s*['"]electronAPI['"]/);
    });

    it('declares invoke, on and send (no isChannelAllowed leak)', () => {
      for (const method of ['invoke', 'on', 'send']) {
        const re = new RegExp(`\\b${method}\\s*:`);
        expect(source, `preload.js must expose ${method}`).toMatch(re);
      }
      // isChannelAllowed must be referenced internally for whitelist checks
      // but must NOT be exposed via contextBridge.
      expect(source).toMatch(/isChannelAllowed/);
      const exposedBlock = source.match(/contextBridge\.exposeInMainWorld\([\s\S]*?\)\s*;?/);
      expect(exposedBlock).toBeTruthy();
      expect(exposedBlock[0]).not.toMatch(/isChannelAllowed/);
    });

    it('gates every IPC entry point on the ALLOWED_CHANNELS whitelist', () => {
      // The whitelist is empty by design for story 1-1; verify the guards exist.
      // Use multiline-tolerant regex because the array literal may span lines
      // and include a comment-only entry.
      expect(source).toMatch(/const\s+ALLOWED_CHANNELS\s*=\s*\[\s*[\s\S]*?\s*\]/);
      // Each of invoke/on/send must check isChannelAllowed before forwarding.
      const gates = source.match(/isChannelAllowed\(channel\)/g) || [];
      expect(gates.length).toBeGreaterThanOrEqual(3);
    });

    it('verifies senderFrame in the on() subscription handler', () => {
      expect(source).toMatch(/senderFrame/);
      // Verify the listener filters by both sender and senderFrame to avoid
      // spoofed events from arbitrary webContents.
      expect(source).toMatch(/event\.senderFrame/);
    });

    it('does not expose raw ipcRenderer to the renderer', () => {
      // Only contextBridge.exposeInMainWorld should be the exposure path.
      const exposeMatches = source.match(/contextBridge\.exposeInMainWorld/g) || [];
      expect(exposeMatches.length).toBe(1);
      expect(source).not.toMatch(/window\.ipcRenderer\s*=/);
    });
  });

  describe('renderer.js entry point', () => {
    it('imports styles.css and has no inline roadmap', () => {
      const src = readFile('src/renderer.js');
      expect(src).toMatch(/import\s+['"]\.\/styles\.css['"]/);
      // Architectural commentary belongs in docs/, not the source file.
      expect(src).not.toMatch(/UI Framework:/);
      expect(src).not.toMatch(/State Management:/);
    });
  });

  describe('index.html security headers', () => {
    it('declares a Content-Security-Policy that blocks remote scripts', () => {
      const html = readFile('index.html');
      expect(html).toMatch(/Content-Security-Policy/);
      const csp = html.match(/Content-Security-Policy[^>]*content="([^"]+)"/);
      expect(csp).toBeTruthy();
      const directives = csp[1].split(';').map((s) => s.trim());
      const scriptSrc = directives.find((d) => d.startsWith('script-src'));
      expect(scriptSrc).toBeDefined();
      expect(scriptSrc).toMatch(/'self'/);
      expect(scriptSrc).not.toMatch(/'unsafe-inline'/);
      expect(scriptSrc).not.toMatch(/'unsafe-eval'/);
    });
  });
});
