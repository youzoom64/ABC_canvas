var powanWorkspace = {
  size: 10000,
  origin: {
    x: 5000,
    y: 5000,
  },
  defaultNodeSize: {
    width: 260,
    height: 150,
  },
  colorPairs: [
    { color: "#fff1b8", accent: "#d8b500" },
    { color: "#ffe1ef", accent: "#ef6ea8" },
    { color: "#dcf7ff", accent: "#34a6cf" },
    { color: "#e5f8c8", accent: "#7db83f" },
    { color: "#efe3ff", accent: "#9b72df" },
    { color: "#ffe7c7", accent: "#ef9a3c" },
    { color: "#dff7ec", accent: "#42b883" },
    { color: "#e2ecff", accent: "#5f8fe8" },
  ],

  number(value, fallback = 0) {
    const next = Number(value);
    return Number.isFinite(next) ? next : fallback;
  },

  clamp(value, min, max) {
    if (max < min) {
      return min;
    }
    return Math.min(max, Math.max(min, value));
  },

  randomChoice(items) {
    return items[Math.floor(Math.random() * items.length)];
  },

  defaultNodeStyle() {
    return {
      shape: "cloud",
      color: "#ffffff",
      accent: "#8ddcff",
      glow: true,
      blur: true,
      motion: "soft",
    };
  },

  randomNodeStyle() {
    const pair = this.randomChoice(this.colorPairs);
    return {
      shape: "cloud",
      color: pair.color,
      accent: pair.accent,
      glow: true,
      blur: true,
      motion: "soft",
    };
  },

  nodeStyle({ randomize = false } = {}) {
    return randomize ? this.randomNodeStyle() : this.defaultNodeStyle();
  },

  documentState() {
    return {
      version: 1,
      width: this.size,
      height: this.size,
      origin: {
        x: this.origin.x,
        y: this.origin.y,
      },
    };
  },

  hasCurrentDocumentState(workspace) {
    return (
      workspace &&
      Number(workspace.width) === this.size &&
      Number(workspace.height) === this.size &&
      Number(workspace.origin?.x) === this.origin.x &&
      Number(workspace.origin?.y) === this.origin.y
    );
  },

  ensureCanvas(nextDoc) {
    if (!nextDoc.canvas || typeof nextDoc.canvas !== "object" || Array.isArray(nextDoc.canvas)) {
      nextDoc.canvas = {};
    }
    return nextDoc.canvas;
  },

  ensureDocument(nextDoc) {
    const canvasState = this.ensureCanvas(nextDoc);
    const migrated = !this.hasCurrentDocumentState(canvasState.workspace);
    if (migrated) {
      this.migrateLegacyDocument(nextDoc);
    }
    canvasState.workspace = this.documentState();
    return {
      doc: nextDoc,
      migrated,
    };
  },

  migrateLegacyDocument(nextDoc) {
    for (const node of Array.isArray(nextDoc.nodes) ? nextDoc.nodes : []) {
      if (!node.layout || typeof node.layout !== "object") {
        continue;
      }
      if (Number.isFinite(Number(node.layout.x))) {
        node.layout.x = Math.round(Number(node.layout.x) + this.origin.x);
      }
      if (Number.isFinite(Number(node.layout.y))) {
        node.layout.y = Math.round(Number(node.layout.y) + this.origin.y);
      }
      node.layout = this.clampLayout(node.layout);
    }
    const viewportState = nextDoc.canvas?.viewport;
    if (viewportState && typeof viewportState === "object" && !Array.isArray(viewportState)) {
      const scale = this.number(viewportState.scale, 1);
      viewportState.x = Math.round(this.number(viewportState.x, 0) - this.origin.x * scale);
      viewportState.y = Math.round(this.number(viewportState.y, 0) - this.origin.y * scale);
    }
  },

  topLeftForCenter(center, width = this.defaultNodeSize.width, height = this.defaultNodeSize.height) {
    return {
      x: Math.round(this.number(center?.x, this.origin.x) - width / 2),
      y: Math.round(this.number(center?.y, this.origin.y) - height / 2),
    };
  },

  clampPoint(point) {
    return {
      x: Math.round(this.clamp(this.number(point?.x, this.origin.x), 0, this.size)),
      y: Math.round(this.clamp(this.number(point?.y, this.origin.y), 0, this.size)),
    };
  },

  clampLayout(layout) {
    const width = Math.max(1, this.number(layout?.width, this.defaultNodeSize.width));
    const height = Math.max(1, this.number(layout?.height, this.defaultNodeSize.height));
    return {
      ...layout,
      x: Math.round(this.clamp(this.number(layout?.x, this.origin.x - width / 2), 0, Math.max(0, this.size - width))),
      y: Math.round(this.clamp(this.number(layout?.y, this.origin.y - height / 2), 0, Math.max(0, this.size - height))),
      width: Math.round(width),
      height: Math.round(height),
    };
  },

  displayBounds(currentOrigin) {
    const origin = currentOrigin || { x: 0, y: 0 };
    return {
      x: -this.number(origin.x),
      y: -this.number(origin.y),
      width: this.size,
      height: this.size,
      zeroX: this.origin.x - this.number(origin.x),
      zeroY: this.origin.y - this.number(origin.y),
    };
  },

  logicalCenterForLayout(layout) {
    const next = this.clampLayout(layout || {});
    return {
      x: Math.round(next.x + next.width / 2 - this.origin.x),
      y: Math.round(next.y + next.height / 2 - this.origin.y),
    };
  },
};
