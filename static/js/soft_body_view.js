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
    let path = skin?.querySelector(".softbody-path") || null;
    if (!skin) {
      skin = document.createElementNS(SVG_NS, "svg");
      skin.setAttribute("class", "softbody-skin softbody-permanent-skin");
      skin.style.position = "absolute";
      skin.style.left = "0";
      skin.style.top = "0";
      skin.style.overflow = "visible";
      skin.style.pointerEvents = "auto";
      skin.style.zIndex = "0";
      state.element.insertBefore(skin, state.element.firstChild);
    }
    if (!path) {
      path = document.createElementNS(SVG_NS, "path");
      path.setAttribute("class", "softbody-path");
      skin.appendChild(path);
    }
    state.skin = skin;
    state.path = path;
    this.setSkinSize(state);
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
      this.setSkinSize(state);
      return state;
    }
    state.width = dimensions.width;
    state.height = dimensions.height;
    state.softBody = powanSoftBody.applyBreathing(
      powanSoftBody.create(dimensions.width, dimensions.height),
      time,
    );
    this.setSkinSize(state);
    this.writePath(state);
    return state;
  },

  setSkinSize(state) {
    if (!state.skin) {
      return;
    }
    state.skin.setAttribute("width", String(state.width));
    state.skin.setAttribute("height", String(state.height));
    state.skin.setAttribute("viewBox", `0 0 ${state.width} ${state.height}`);
  },

  writePath(state) {
    if (state.path) {
      state.path.setAttribute("d", powanSoftBody.toPathData(state.softBody));
    }
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
