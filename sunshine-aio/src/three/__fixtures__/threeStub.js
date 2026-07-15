/**
 * Shared THREE stub for the Story 2-2 sun + scene-controller tests.
 *
 * Vitest defaults to `environment: 'node'` for this project, which means
 * we cannot import the real `three` module (its WebGLRenderer needs a
 * real DOM canvas with a WebGL context). Both `sun.test.js` and the
 * "sun integration (Story 2-2)" block inside `setup.test.js` previously
 * carried near-verbatim copies of this stub, which had already drifted
 * (the setup test wrapped `Color` inside `vi.mock` instead of exporting
 * it from the factory, so a future test that needed to assert on color
 * state would have silently seen `undefined`).
 *
 * Centralising the stub here guarantees both suites share one source of
 * truth. The factory accepts the test's `vi` instance so `vi.fn()` spies
 * remain scoped to the calling suite rather than a shared module.
 */

export const createThreeStub = ({ vi }) => {
  class Color {
    constructor(value) {
      this.value = value;
    }
    // Mirrors the production Color surface that the sun's hot path
    // (`material.color.set(hex)`) relies on so the stub exercises the
    // real call site without needing a WebGL context.
    set(value) {
      this.value = value;
      return this;
    }
  }

  class Geometry {
    constructor() {
      this.dispose = vi.fn();
    }
  }

  class Material {
    constructor(opts = {}) {
      this.opts = opts;
      this.dispose = vi.fn();
      this.emissiveIntensity = opts.emissiveIntensity ?? 1;
      this.color = opts.color !== undefined ? new Color(opts.color) : undefined;
      this.emissive = opts.emissive !== undefined ? new Color(opts.emissive) : undefined;
    }
  }

  class Object3D {
    constructor() {
      this.name = '';
      this.children = [];
      this.position = {
        x: 0,
        y: 0,
        z: 0,
        set(x, y, z) {
          this.x = x;
          this.y = y;
          this.z = z;
        },
      };
      this.scale = {
        x: 1,
        y: 1,
        z: 1,
        set(x, y, z) {
          this.x = x;
          this.y = y;
          this.z = z;
        },
      };
    }
    add(child) {
      this.children.push(child);
    }
    remove(child) {
      const idx = this.children.indexOf(child);
      if (idx !== -1) this.children.splice(idx, 1);
    }
  }

  class Mesh extends Object3D {
    constructor(geometry, material) {
      super();
      this.geometry = geometry;
      this.material = material;
    }
  }

  class SphereGeometry extends Geometry {}
  class MeshStandardMaterial extends Material {}
  class MeshBasicMaterial extends Material {}

  return {
    Object3D,
    Mesh,
    SphereGeometry,
    MeshStandardMaterial,
    MeshBasicMaterial,
    Color,
    BackSide: Symbol('BackSide'),
  };
};
