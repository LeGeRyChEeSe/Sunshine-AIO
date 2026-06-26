/**
 * Shared THREE stub for the Story 2-2 / 2-3 sun + scene-controller + planet tests.
 *
 * Vitest defaults to `environment: 'node'` for this project, which means
 * we cannot import the real `three` module (its WebGLRenderer needs a
 * real DOM canvas with a WebGL context). Both `sun.test.js`,
 * `setup.test.js`, `planet.test.js`, and `planetFactory.test.js`
 * previously carried near-verbatim copies of this stub, which had
 * already drifted (the setup test wrapped `Color` inside `vi.mock`
 * instead of exporting it from the factory, so a future test that
 * needed to assert on color state would have silently seen `undefined`).
 *
 * Centralising the stub here guarantees all suites share one source
 * of truth. The factory accepts the test's `vi` instance so `vi.fn()`
 * spies remain scoped to the calling suite rather than a shared
 * module.
 *
 * Story 2-3 extends the stub with:
 *   - Line, LineDashedMaterial for orbit visualisation
 *   - BufferGeometry + BufferAttribute + computeLineDistances for orbit geometry
 *   - CanvasTexture (no-op stub) for procedural noise textures
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

  class BufferGeometry extends Geometry {
    constructor() {
      super();
      this.attributes = {};
      this.index = null;
    }
    setAttribute(name, attribute) {
      this.attributes[name] = attribute;
    }
    setIndex(index) {
      this.index = index;
    }
    // The real method walks the line segments to compute a per-vertex
    // distance value used by LineDashedMaterial. The stub records the
    // call without actually walking anything so the call site stays
    // exercised.
    computeLineDistances() {
      this.lineDistances = true;
    }
  }

  class BufferAttribute {
    constructor(array, itemSize) {
      this.array = array;
      this.itemSize = itemSize;
    }
  }

  class Material {
    constructor(opts = {}) {
      this.opts = opts;
      this.dispose = vi.fn();
      this.emissiveIntensity = opts.emissiveIntensity ?? 1;
      this.color = opts.color !== undefined ? new Color(opts.color) : undefined;
      this.emissive = opts.emissive !== undefined ? new Color(opts.emissive) : undefined;
      // Map is a slot we don't fully exercise but tests may assert on.
      this.map = opts.map ?? null;
      this.side = opts.side ?? null;
      this.opacity = opts.opacity ?? 1;
      this.transparent = opts.transparent ?? false;
      this.depthWrite = opts.depthWrite ?? true;
    }
  }

  class Object3D {
    constructor() {
      this.name = '';
      this.children = [];
      this.parent = null;
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
      this.rotation = {
        x: 0,
        y: 0,
        z: 0,
      };
    }
    add(child) {
      this.children.push(child);
      if (child && typeof child === 'object') {
        child.parent = this;
      }
    }
    remove(child) {
      const idx = this.children.indexOf(child);
      if (idx !== -1) {
        this.children.splice(idx, 1);
        if (child && typeof child === 'object') {
          child.parent = null;
        }
      }
    }
  }

  class Mesh extends Object3D {
    constructor(geometry, material) {
      super();
      this.geometry = geometry;
      this.material = material;
    }
  }

  // Story 2-3: minimal Line stub. The production surface (geometry +
  // material) is enough for our orbit code; we just need the
  // dispose() chain to be reachable from createOrbits.dispose().
  class Line extends Object3D {
    constructor(geometry, material) {
      super();
      this.geometry = geometry;
      this.material = material;
    }
  }

  class SphereGeometry extends Geometry {}
  class MeshStandardMaterial extends Material {}
  class MeshBasicMaterial extends Material {}
  class LineDashedMaterial extends Material {
    constructor(opts = {}) {
      super(opts);
      this.dashSize = opts.dashSize ?? 1;
      this.gapSize = opts.gapSize ?? 1;
    }
  }

  class CanvasTexture {
    constructor(canvas) {
      this.canvas = canvas;
      this.dispose = vi.fn();
    }
  }

  return {
    Object3D,
    Mesh,
    Line,
    SphereGeometry,
    MeshStandardMaterial,
    MeshBasicMaterial,
    LineDashedMaterial,
    BufferGeometry,
    BufferAttribute,
    CanvasTexture,
    Color,
    BackSide: Symbol('BackSide'),
  };
};
