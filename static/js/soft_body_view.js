var powanSoftBodyView = {
  states: new Map(),
  rafId: null,
  last: 0,

  attach(element, layout = {}) {
    if (!element) {
      return null;
    }
    let state = this.states.get(element);
    if (!state) {
      state = this.createState(element, layout);
      this.states.set(element, state);
    } else {
      this.ensureSkin(state);
      this.resizeState(state, layout, performance.now() / 1000);
    }
    element.classList.add("softbody-visual");
    this.start();
    return state;
  },

  attachStatic(element, layout = {}) {
    if (!element) {
      return null;
    }
    const state = this.createState(element, layout);
    // 静止スキンはアニメしないので、脈動(breathing)で歪んだ1フレームを焼き込まない。
    // 歪みのない中央楕円で描き直す（雲が要素中心に揃い、文字が上にズレない）。
    state.isStatic = true;
    state.softBody = powanSoftBody.create(state.width, state.height);
    this.writePath(state);
    element.classList.add("softbody-visual");
    return state;
  },

  acquire(element, layout = {}) {
    const state = this.attach(element, layout);
    if (!state) {
      return null;
    }
    state.controlled = true;
    this.resizeState(state, layout, performance.now() / 1000);
    return state;
  },

  release(element) {
    const state = this.states.get(element);
    if (!state) {
      return;
    }
    state.controlled = false;
    state.last = performance.now();
    this.start();
  },

  createState(element, layout = {}) {
    const dimensions = this.dimensions(element, layout);
    const softBody = powanSoftBody.applyBreathing(
      powanSoftBody.create(dimensions.width, dimensions.height),
      performance.now() / 1000,
    );
    const state = {
      element,
      softBody,
      skin: null,
      path: null,
      context: null,
      pixelRatio: 1,
      drawPadding: 0,
      fillStyle: "#ffffff",
      strokeStyle: "#8ddcff",
      selectedStrokeStyle: "#8ddcff",
      selected: false,
      width: dimensions.width,
      height: dimensions.height,
      controlled: false,
      last: performance.now(),
    };
    this.ensureSkin(state);
    this.writePath(state);
    return state;
  },

  ensureSkin(state) {
    let skin = Array.from(state.element.children).find((child) => (
      child.classList?.contains("softbody-skin") &&
      child.classList?.contains("softbody-permanent-skin")
    ));
    if (skin && skin.tagName?.toLowerCase() !== "canvas") {
      skin.remove();
      skin = null;
    }
    if (!skin) {
      skin = document.createElement("canvas");
      skin.className = "softbody-skin softbody-permanent-skin";
      skin.style.position = "absolute";
      skin.style.left = "0";
      skin.style.top = "0";
      skin.style.overflow = "visible";
      skin.style.pointerEvents = "none";
      skin.style.zIndex = "0";
      state.element.insertBefore(skin, state.element.firstChild);
    }
    state.skin = skin;
    state.context = skin.getContext("2d");
    state.path = this.pathProxy(state);
    this.setSkinSize(state);
    this.refreshSkinStyle(state);
  },

  pathProxy(state) {
    return {
      setAttribute: (name) => {
        if (name === "d") {
          this.writePath(state);
        }
      },
    };
  },

  dimensions(element, layout = {}) {
    const width = Number(layout.width)
      || element.offsetWidth
      || Number.parseFloat(element.style.width)
      || 1;
    const height = Number(layout.height)
      || element.offsetHeight
      || Number.parseFloat(element.style.height)
      || 1;
    return {
      width: Math.max(1, width),
      height: Math.max(1, height),
    };
  },

  resizeElement(element, layout = {}) {
    const state = this.states.get(element);
    if (!state) {
      return this.attach(element, layout);
    }
    return this.resizeState(state, layout, performance.now() / 1000);
  },

  resizeState(state, layout = {}, time = 0) {
    const dimensions = this.dimensions(state.element, layout);
    if (
      Math.abs(dimensions.width - state.width) < 0.5 &&
      Math.abs(dimensions.height - state.height) < 0.5
    ) {
      return state;
    }
    state.width = dimensions.width;
    state.height = dimensions.height;
    // 静止スキンは脈動の歪みを焼き込まない（雲が要素中心に揃う）。
    state.softBody = state.isStatic
      ? powanSoftBody.create(dimensions.width, dimensions.height)
      : powanSoftBody.applyBreathing(
          powanSoftBody.create(dimensions.width, dimensions.height),
          time,
        );
    this.setSkinSize(state);
    this.writePath(state);
    return state;
  },

  setSkinSize(state) {
    if (!state.skin) {
      return false;
    }
    const padding = Math.max(16, Math.min(96, Math.max(state.width, state.height) * 0.12));
    const ratio = this.targetPixelRatio(state);
    const skinWidth = state.width + padding * 2;
    const skinHeight = state.height + padding * 2;
    const pixelWidth = Math.max(1, Math.round(skinWidth * ratio));
    const pixelHeight = Math.max(1, Math.round(skinHeight * ratio));
    let changed = Math.abs((state.pixelRatio || 1) - ratio) > 0.01;
    state.drawPadding = padding;
    state.pixelRatio = ratio;
    if (state.skin.width !== pixelWidth) {
      state.skin.width = pixelWidth;
      changed = true;
    }
    if (state.skin.height !== pixelHeight) {
      state.skin.height = pixelHeight;
      changed = true;
    }
    state.skin.style.left = `${-padding}px`;
    state.skin.style.top = `${-padding}px`;
    state.skin.style.width = `${skinWidth}px`;
    state.skin.style.height = `${skinHeight}px`;
    return changed;
  },

  targetPixelRatio(state) {
    const deviceRatio = Math.max(1, window.devicePixelRatio || 1);
    const viewScale = typeof viewport !== "undefined" ? Number(viewport.scale || 1) : 1;
    const screenRatio = this.visibleScreenPixelRatio(state, deviceRatio);
    let level = 1;
    if (state.element?.classList?.contains("nested-preview-meaning")) {
      const depth = Math.max(1, Number(state.element.dataset.previewDepth || 1));
      const first = 1.75 + (depth - 1) * 0.65;
      const second = 3 + (depth - 1) * 0.85;
      const third = 4.5 + (depth - 1) * 1.15;
      level = viewScale >= third ? 4 : viewScale >= second ? 3 : viewScale >= first ? 2 : 1;
    } else if (state.element?.classList?.contains("nested-meaning")) {
      level = viewScale >= 4 ? 4 : viewScale >= 2.4 ? 3 : viewScale >= 1.5 ? 2 : 1;
    } else {
      level = viewScale >= 4 ? 3 : viewScale >= 2 ? 2 : 1;
    }
    return Math.max(1, Math.min(8, Math.max(deviceRatio, level, screenRatio)));
  },

  visibleScreenScale(state) {
    const rect = state.element?.getBoundingClientRect?.();
    if (!rect || !Number.isFinite(rect.width) || !Number.isFinite(rect.height)) {
      return 1;
    }
    const margin = 96;
    const visible = (
      rect.right >= -margin &&
      rect.bottom >= -margin &&
      rect.left <= window.innerWidth + margin &&
      rect.top <= window.innerHeight + margin
    );
    if (!visible) {
      return 1;
    }
    const widthScale = rect.width / Math.max(1, state.width);
    const heightScale = rect.height / Math.max(1, state.height);
    return Math.max(widthScale, heightScale, 1);
  },

  visibleScreenPixelRatio(state, deviceRatio = Math.max(1, window.devicePixelRatio || 1)) {
    return Math.ceil(this.visibleScreenScale(state) * deviceRatio);
  },

  refreshViewportResolution() {
    let changed = 0;
    for (const state of this.states.values()) {
      if (!state.element?.isConnected) {
        continue;
      }
      if (this.setSkinSize(state)) {
        this.writePath(state);
        changed += 1;
      }
    }
    return changed;
  },

  refreshSkinStyle(state) {
    if (!state?.element) {
      return;
    }
    const element = state.element;
    // インライン値を優先して読む。要素がまだDOMに挿入されていない(detached)とき
    // getComputedStyleはカスタムプロパティを空で返すため、白に化けてしまう。
    const readVar = (name) => {
      const inline = element.style.getPropertyValue(name).trim();
      if (inline) {
        return inline;
      }
      return getComputedStyle(element).getPropertyValue(name).trim();
    };
    const accent = readVar("--accent") || "#8ddcff";
    state.fillStyle = readVar("--node-color") || "#ffffff";
    state.strokeStyle = accent;
    state.selectedStrokeStyle = accent;
    state.selected = element.classList.contains("selected");
  },

  writePath(state) {
    if (!state.context || !state.skin) {
      return;
    }
    const points = state.softBody?.points || [];
    const n = state.softBody?.count || points.length;
    if (n < 3) {
      return;
    }
    const context = state.context;
    const ratio = state.pixelRatio || 1;
    const padding = state.drawPadding || 0;
    context.setTransform(ratio, 0, 0, ratio, 0, 0);
    context.clearRect(0, 0, state.width + padding * 2, state.height + padding * 2);
    context.translate(padding, padding);

    const selected = state.element.classList.contains("selected");
    if (selected !== state.selected) {
      this.refreshSkinStyle(state);
    }
    const stroke = selected ? state.selectedStrokeStyle : state.strokeStyle;
    const viewScale = typeof viewport !== "undefined" ? viewport.scale : 1;
    const screenScale = Math.max(0.01, Number(viewScale || 1));
    const lineWidth = (selected ? 3.4 : 2) / screenScale;

    context.beginPath();
    for (let i = 0; i < n; i++) {
      const p0 = points[(i - 1 + n) % n];
      const p1 = points[i];
      const p2 = points[(i + 1) % n];
      const p3 = points[(i + 2) % n];
      if (i === 0) {
        context.moveTo(p1.x, p1.y);
      }
      const c1x = p1.x + (p2.x - p0.x) / 6;
      const c1y = p1.y + (p2.y - p0.y) / 6;
      const c2x = p2.x - (p3.x - p1.x) / 6;
      const c2y = p2.y - (p3.y - p1.y) / 6;
      context.bezierCurveTo(c1x, c1y, c2x, c2y, p2.x, p2.y);
    }
    context.closePath();
    context.fillStyle = state.fillStyle;
    context.strokeStyle = stroke;
    context.lineWidth = lineWidth;
    context.fill();
    context.stroke();
  },

  start() {
    if (this.rafId || !this.states.size) {
      return;
    }
    this.last = performance.now();
    this.rafId = requestAnimationFrame((timestamp) => this.step(timestamp));
  },

  step(timestamp) {
    this.rafId = null;
    const dt = Math.min(Math.max((timestamp - this.last) / 1000, 0.001), 0.032);
    this.last = timestamp;
    for (const [element, state] of this.states) {
      if (!element.isConnected) {
        this.states.delete(element);
        continue;
      }
      if (state.controlled) {
        continue;
      }
      this.resizeState(state, {}, timestamp / 1000);
      powanSoftBody.step(state.softBody, {
        dt,
        moveX: 0,
        moveY: 0,
        grabIndex: -1,
        released: true,
        time: timestamp / 1000,
      });
      this.writePath(state);
    }
    if (this.states.size) {
      this.rafId = requestAnimationFrame((next) => this.step(next));
    }
  },
};
