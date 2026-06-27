var SVG_NS = "http://www.w3.org/2000/svg";

// ドラッグ中のポワン変形を一括管理するコントローラ。top-level / nested 問わず
// powanExplorer から begin/release され、同時に1つだけ有効。輪郭は soft-body で水風船変形する。
var powanDragDeform = {
  active: null,

  begin(element, offsetX, offsetY, rule = {}) {
    this.stop();
    const startTime = performance.now();
    const visual = this.createDragVisualState(element, startTime / 1000);
    const softBody = visual.softBody;
    const visualCenter = this.visualCenter(softBody);
    const childEls = Array.isArray(rule.childEls) ? rule.childEls : [];
    const startPosition = this.leftTop(element);
    this.active = {
      element,
      softBody,
      skin: visual.skin,
      path: visual.path,
      permanentSkin: visual.permanent,
      grabIndex: powanSoftBody.grabIndex(softBody, offsetX, offsetY),
      grabOffsetX: offsetX,
      grabOffsetY: offsetY,
      pointerX: startPosition.left + offsetX,
      pointerY: startPosition.top + offsetY,
      hasPointer: true,
      released: false,
      bodyLeft: startPosition.left,
      bodyTop: startPosition.top,
      bodyVX: 0,
      bodyVY: 0,
      lastLeft: startPosition.left,
      lastTop: startPosition.top,
      last: startTime,
      // 中の子ポワン(nestedレイヤー)を親の動きに対して遅れて揺らすための慣性ラグ
      contentLayer: rule.contentLayer || null,
      lagX: 0,
      lagY: 0,
      lagVX: 0,
      lagVY: 0,
      // 親からはみ出ないようラグの上限。子要素は変形(揺れ)もさせる
      maxLagX: element.offsetWidth * 0.13,
      maxLagY: element.offsetHeight * 0.13,
      childEls,
      childStates: [],
      childVX: 0,
      childVY: 0,
      contentFollowsVisualCenter: rule.contentFollowsVisualCenter !== false,
      childrenDeformAtWall: rule.childrenDeformAtWall !== false && childEls.length > 0,
      visualCenter,
      previousVisualCenter: visualCenter,
      visualCenterDelta: { x: 0, y: 0 },
      visualCenterOffset: this.visualCenterOffset(softBody, visualCenter),
      releaseStartedAt: null,
      traceFrame: 0,
    };
    if (this.active.childrenDeformAtWall) {
      this.active.childStates = this.active.childEls.map((child) => this.createChildWaterState(child));
    }
    this.syncSoftBodyVisualStates(this.active);
    element.classList.add("drag-softbody");
    this.trace("drag-deform-text-layer-start", {
      nodeId: element?.dataset?.id || null,
      className: String(element?.className || ""),
      textLayer: this.textLayerSnapshot(element),
    });
    this.trace("drag-deform-begin", {
      offsetX,
      offsetY,
      startPosition,
      childCount: childEls.length,
      snapshot: this.snapshot(this.active),
    });
    const self = this;
    this.active.rafId = requestAnimationFrame((timestamp) => self.step(timestamp));
  },

  release() {
    const active = this.active;
    if (!active) {
      return;
    }
    this.trace("drag-deform-release", {
      snapshot: this.snapshot(active),
    });
    active.hasPointer = false;
    active.released = true;
    active.releaseStartedAt = performance.now();
  },

  stop() {
    const active = this.active;
    if (!active) {
      return;
    }
    this.trace("drag-deform-stop", {
      snapshot: this.snapshot(active),
    });
    if (active.rafId) {
      cancelAnimationFrame(active.rafId);
    }
    this.active = null;
    this.clearVisualContentOffset(active);
    this.clearChildWaterDeform(active);
    // 箱の発光(0.2s transition)が戻るのと重なるよう、輪郭は即消さず短くフェードアウトしてポップを防ぐ
    active.element.classList.remove("drag-softbody");
    if (active.permanentSkin && typeof powanSoftBodyView !== "undefined") {
      powanSoftBodyView.release(active.element);
      return;
    }
    const skin = active.skin;
    if (skin) {
      skin.style.transition = "opacity 0.18s ease-out";
      skin.style.opacity = "0";
      window.setTimeout(() => {
        if (skin.parentNode) {
          skin.parentNode.removeChild(skin);
        }
      }, 200);
    }
  },

  leftTop(element) {
    return {
      left: Number.parseFloat(element.style.left || "0"),
      top: Number.parseFloat(element.style.top || "0"),
    };
  },

  createSoftBody(element, time = 0) {
    return powanSoftBody.applyBreathing(
      powanSoftBody.create(element.offsetWidth, element.offsetHeight),
      time,
    );
  },

  createDragVisualState(element, time = 0) {
    if (typeof powanSoftBodyView !== "undefined") {
      const state = powanSoftBodyView.acquire(element, {
        width: element.offsetWidth,
        height: element.offsetHeight,
      });
      if (state) {
        return {
          softBody: state.softBody,
          skin: state.skin,
          path: state.path,
          permanent: true,
        };
      }
    }
    const softBody = this.createSoftBody(element, time);
    const skin = this.createSkin(element, softBody);
    return {
      softBody,
      skin: skin.skin,
      path: skin.path,
      permanent: false,
    };
  },

  visualCenter(softBody) {
    const points = softBody?.points || [];
    if (!points.length) {
      return { x: softBody?.cx || 0, y: softBody?.cy || 0 };
    }

    let area2 = 0;
    let centerX = 0;
    let centerY = 0;
    for (let i = 0; i < points.length; i++) {
      const current = points[i];
      const next = points[(i + 1) % points.length];
      const cross = current.x * next.y - next.x * current.y;
      area2 += cross;
      centerX += (current.x + next.x) * cross;
      centerY += (current.y + next.y) * cross;
    }

    if (Math.abs(area2) < 0.001) {
      const total = points.reduce(
        (sum, point) => ({
          x: sum.x + point.x,
          y: sum.y + point.y,
        }),
        { x: 0, y: 0 },
      );
      return {
        x: total.x / points.length,
        y: total.y / points.length,
      };
    }

    return {
      x: centerX / (3 * area2),
      y: centerY / (3 * area2),
    };
  },

  visualCenterOffset(softBody, center = this.visualCenter(softBody)) {
    return {
      x: center.x - softBody.cx,
      y: center.y - softBody.cy,
    };
  },

  currentVisualCenter({ absolute = false } = {}) {
    const active = this.active;
    if (!active) {
      return null;
    }
    const center = active.visualCenter || this.visualCenter(active.softBody);
    if (!absolute) {
      return {
        x: center.x,
        y: center.y,
        offsetX: center.x - active.softBody.cx,
        offsetY: center.y - active.softBody.cy,
      };
    }
    const position = this.leftTop(active.element);
    return {
      x: position.left + center.x,
      y: position.top + center.y,
      offsetX: center.x - active.softBody.cx,
      offsetY: center.y - active.softBody.cy,
    };
  },

  moveToPointer(pointerX, pointerY) {
    const active = this.active;
    if (!active) {
      return null;
    }
    active.pointerX = pointerX;
    active.pointerY = pointerY;
    active.hasPointer = true;
    active.released = false;
    return this.currentLocalRect(active);
  },

  currentLocalRect(active = this.active) {
    if (!active) {
      return null;
    }
    const position = this.leftTop(active.element);
    return {
      x: position.left,
      y: position.top,
      width: active.element.offsetWidth,
      height: active.element.offsetHeight,
    };
  },

  roundNumber(value) {
    return Number.isFinite(value) ? Number(value.toFixed(2)) : value;
  },

  roundPoint(point) {
    if (!point) {
      return null;
    }
    return {
      x: this.roundNumber(point.x),
      y: this.roundNumber(point.y),
      offsetX: this.roundNumber(point.offsetX),
      offsetY: this.roundNumber(point.offsetY),
    };
  },

  snapshot(active = this.active, extra = {}) {
    if (!active) {
      return null;
    }
    const center = active.visualCenter || this.visualCenter(active.softBody);
    const position = this.leftTop(active.element);
    const localCenter = {
      x: center.x,
      y: center.y,
      offsetX: center.x - active.softBody.cx,
      offsetY: center.y - active.softBody.cy,
    };
    const absoluteCenter = {
      x: position.left + center.x,
      y: position.top + center.y,
      offsetX: center.x - active.softBody.cx,
      offsetY: center.y - active.softBody.cy,
    };
    return {
      nodeId: active.element?.dataset?.id || null,
      hasPointer: active.hasPointer,
      released: active.released,
      pointer: {
        x: this.roundNumber(active.pointerX),
        y: this.roundNumber(active.pointerY),
      },
      grabOffset: {
        x: this.roundNumber(active.grabOffsetX),
        y: this.roundNumber(active.grabOffsetY),
      },
      body: {
        left: this.roundNumber(active.bodyLeft),
        top: this.roundNumber(active.bodyTop),
        vx: this.roundNumber(active.bodyVX),
        vy: this.roundNumber(active.bodyVY),
      },
      visualCenter: this.roundPoint(localCenter),
      absoluteVisualCenter: this.roundPoint(absoluteCenter),
      visualCenterDelta: {
        x: this.roundNumber(active.visualCenterDelta?.x || 0),
        y: this.roundNumber(active.visualCenterDelta?.y || 0),
      },
      lag: {
        x: this.roundNumber(active.lagX),
        y: this.roundNumber(active.lagY),
        vx: this.roundNumber(active.lagVX),
        vy: this.roundNumber(active.lagVY),
      },
      childCount: active.childEls?.length || 0,
      ...extra,
    };
  },

  trace(action, details = {}) {
    if (typeof logEvent === "function") {
      logEvent("trace", action, details);
    }
  },

  textLayerSnapshot(element) {
    const layers = Array.from(
      element?.querySelectorAll?.(":scope > .node-body") || [],
    );
    if (!layers.length) {
      return null;
    }
    return layers.map((layer) => {
      const style = getComputedStyle(layer);
      return {
        className: String(layer.className || ""),
        position: style.position,
        display: style.display,
        left: style.left,
        top: style.top,
        right: style.right,
        bottom: style.bottom,
        transform: style.transform,
        opacity: style.opacity,
      };
    });
  },

  advanceBodyPosition(active, dt) {
    if (!active.hasPointer) {
      active.bodyVX *= Math.exp(-9 * dt);
      active.bodyVY *= Math.exp(-9 * dt);
    } else {
      const localGrabX = active.pointerX - active.bodyLeft;
      const localGrabY = active.pointerY - active.bodyTop;
      const pullX = localGrabX - active.grabOffsetX;
      const pullY = localGrabY - active.grabOffsetY;
      const spring = 170;
      const damping = 22;
      active.bodyVX += (pullX * spring - active.bodyVX * damping) * dt;
      active.bodyVY += (pullY * spring - active.bodyVY * damping) * dt;
    }
    active.bodyLeft += active.bodyVX * dt;
    active.bodyTop += active.bodyVY * dt;
    active.element.style.left = `${active.bodyLeft}px`;
    active.element.style.top = `${active.bodyTop}px`;
  },

  grabTargetLocal(active) {
    if (!active.hasPointer) {
      return { x: null, y: null };
    }
    const overshoot = 0.55;
    const minX = -active.element.offsetWidth * overshoot;
    const maxX = active.element.offsetWidth * (1 + overshoot);
    const minY = -active.element.offsetHeight * overshoot;
    const maxY = active.element.offsetHeight * (1 + overshoot);
    return {
      x: Math.max(minX, Math.min(maxX, active.pointerX - active.bodyLeft)),
      y: Math.max(minY, Math.min(maxY, active.pointerY - active.bodyTop)),
    };
  },

  visualContentOffset(active) {
    return this.nestedLayerOffset(active);
  },

  softBodySelfOffset(target) {
    return this.visualCenterOffset(target.softBody, target.visualCenter || this.visualCenter(target.softBody));
  },

  nestedLayerOffset(active) {
    return { x: 0, y: 0 };
  },

  applyNestedLayerOffset(active, offset) {
    if (active.contentLayer) {
      active.contentLayer.style.removeProperty("transform");
    }
  },

  clearVisualContentOffset(active) {
    this.clearElementVisualContentOffset(active.element);
    this.clearNestedLayerOffset(active);
  },

  clearNestedLayerOffset(active) {
    if (active.contentLayer) {
      active.contentLayer.style.transform = "";
    }
  },

  applyElementVisualContentOffset(element, offset) {
    element.style.setProperty("--powan-visual-content-x", `${offset.x.toFixed(2)}px`);
    element.style.setProperty("--powan-visual-content-y", `${offset.y.toFixed(2)}px`);
  },

  clearElementVisualContentOffset(element) {
    element.style.removeProperty("--powan-visual-content-x");
    element.style.removeProperty("--powan-visual-content-y");
  },

  syncSoftBodyVisualStates(active) {
    this.applyElementVisualContentOffset(active.element, this.softBodySelfOffset(active));
    for (const state of active.childStates || []) {
      this.applyElementVisualContentOffset(state.element, this.softBodySelfOffset(state));
    }
  },

  clearChildWaterDeform(active) {
    for (const state of active.childStates || []) {
      this.trace("drag-deform-child-water-clear", {
        parentId: active.element?.dataset?.id || null,
        childId: state.element?.dataset?.id || null,
        hadDragSoftbodyClass: state.element.classList.contains("drag-softbody"),
        permanentSkin: Boolean(state.permanentSkin),
        push: {
          x: this.roundNumber(state.pushX || 0),
          y: this.roundNumber(state.pushY || 0),
        },
      });
      state.element.style.transform = "";
      state.element.style.transformOrigin = "";
      this.clearElementVisualContentOffset(state.element);
      state.element.style.removeProperty("--powan-child-push-x");
      state.element.style.removeProperty("--powan-child-push-y");
      if (state.permanentSkin && typeof powanSoftBodyView !== "undefined") {
        powanSoftBodyView.release(state.element);
        continue;
      }
      if (state.skin?.parentNode) {
        state.skin.parentNode.removeChild(state.skin);
      }
    }
    active.childStates = [];
  },

  createChildWaterState(element) {
    const visual = this.createDragVisualState(element, performance.now() / 1000);
    const state = {
      element,
      softBody: visual.softBody,
      skin: visual.skin,
      path: visual.path,
      permanentSkin: visual.permanent,
      pressure: 0,
      pushX: 0,
      pushY: 0,
      pushVX: 0,
      pushVY: 0,
    };
    this.trace("drag-deform-child-water-create", {
      childId: element?.dataset?.id || null,
      hadDragSoftbodyClass: element.classList.contains("drag-softbody"),
      permanentSkin: Boolean(state.permanentSkin),
      width: element.offsetWidth,
      height: element.offsetHeight,
    });
    return state;
  },

  createSkin(element, softBody) {
    const style = getComputedStyle(element);
    const selected = element.classList.contains("selected");
    const accent = style.getPropertyValue("--accent").trim() || "#8ddcff";
    const bg = style.backgroundColor;
    const fill = bg && bg !== "transparent" && !bg.startsWith("rgba(0, 0, 0, 0")
      ? bg
      : (style.getPropertyValue("--node-color").trim() || "#ffffff");
    const skin = document.createElementNS(SVG_NS, "svg");
    const nestedSkin = element.classList.contains("nested-meaning") || element.classList.contains("nested-preview-meaning");
    skin.setAttribute("class", "softbody-skin");
    skin.style.position = "absolute";
    skin.style.left = "0";
    skin.style.top = "0";
    skin.style.overflow = "visible";
    skin.style.pointerEvents = "auto";
    skin.style.zIndex = nestedSkin ? "0" : "-1";
    skin.setAttribute("width", String(element.offsetWidth));
    skin.setAttribute("height", String(element.offsetHeight));
    const path = document.createElementNS(SVG_NS, "path");
    path.setAttribute("class", "softbody-path");
    path.setAttribute("fill", fill);
    path.setAttribute("stroke", accent);
    path.setAttribute("stroke-width", selected ? "3.4" : "2");
    path.setAttribute("d", powanSoftBody.toPathData(softBody));
    skin.appendChild(path);
    element.insertBefore(skin, element.firstChild);
    return { skin, path };
  },

  step(timestamp) {
    const active = this.active;
    if (!active) {
      return;
    }
    if (!active.element.isConnected) {
      this.stop();
      return;
    }
    const dt = Math.min(Math.max((timestamp - active.last) / 1000, 0.001), 0.032);
    active.last = timestamp;
    this.advanceBodyPosition(active, dt);
    const now = this.leftTop(active.element);
    const moveX = now.left - active.lastLeft;
    const moveY = now.top - active.lastTop;
    active.lastLeft = now.left;
    active.lastTop = now.top;
    const grabTarget = this.grabTargetLocal(active);
    const softBodyState = powanSoftBody.step(active.softBody, {
      dt,
      moveX,
      moveY,
      grabIndex: active.grabIndex,
      released: active.released,
      time: timestamp / 1000,
      grabTargetX: grabTarget.x,
      grabTargetY: grabTarget.y,
    });
    active.previousVisualCenter = active.visualCenter;
    active.visualCenter = this.visualCenter(active.softBody);
    active.visualCenterDelta = {
      x: active.visualCenter.x - active.previousVisualCenter.x,
      y: active.visualCenter.y - active.previousVisualCenter.y,
    };
    active.visualCenterOffset = this.visualCenterOffset(active.softBody, active.visualCenter);
    active.path.setAttribute("d", powanSoftBody.toPathData(active.softBody));
    this.stepContentLag(active, moveX, moveY, dt, timestamp / 1000);
    if (this.shouldStopReleasedMotion(active, softBodyState, timestamp)) {
      this.trace("drag-deform-settled", {
        snapshot: this.snapshot(active),
      });
      this.stop();
      return;
    }
    active.traceFrame += 1;
    if (active.traceFrame % 6 === 0) {
      this.trace("drag-deform-step", {
        snapshot: this.snapshot(active, {
          dt: this.roundNumber(dt),
          moveX: this.roundNumber(moveX),
          moveY: this.roundNumber(moveY),
          grabTarget: this.roundPoint(grabTarget),
        }),
      });
    }
    const self = this;
    active.rafId = requestAnimationFrame((next) => self.step(next));
  },

  shouldStopReleasedMotion(active, softBodyState, timestamp) {
    if (!active.released) {
      return false;
    }
    const elapsed = timestamp - (active.releaseStartedAt || timestamp);
    if (elapsed > 320) {
      return true;
    }
    if (elapsed < 120 || !softBodyState?.settled) {
      return false;
    }
    const bodySpeed = Math.hypot(active.bodyVX, active.bodyVY);
    const lagDistance = Math.hypot(active.lagX, active.lagY);
    const lagSpeed = Math.hypot(active.lagVX, active.lagVY);
    const childSettled = (active.childStates || []).every((state) => (
      Math.hypot(state.pushX, state.pushY) < 0.8 &&
      Math.hypot(state.pushVX, state.pushVY) < 12
    ));
    return bodySpeed < 8 && lagDistance < 0.8 && lagSpeed < 12 && childSettled;
  },

  // 親が動いた分だけ中身を後方へ取り残し、バネで0へ戻す（中で物理的にくっついて揺れる感じ）。
  // ラグは親からはみ出ないようクランプし、各子も取り残し方向に伸び縮みさせる。
  stepContentLag(active, moveX, moveY, dt, time) {
    const stiffness = 200;
    const damp = 19;
    const follow = 0.55;
    const visualMoveX = moveX + active.visualCenterDelta.x;
    const visualMoveY = moveY + active.visualCenterDelta.y;
    active.lagX -= visualMoveX * follow;
    active.lagY -= visualMoveY * follow;
    active.lagVX += (-stiffness * active.lagX - damp * active.lagVX) * dt;
    active.lagVY += (-stiffness * active.lagY - damp * active.lagVY) * dt;
    active.lagX += active.lagVX * dt;
    active.lagY += active.lagVY * dt;
    active.lagX = Math.max(-active.maxLagX, Math.min(active.maxLagX, active.lagX));
    active.lagY = Math.max(-active.maxLagY, Math.min(active.maxLagY, active.lagY));
    const contentOffset = this.visualContentOffset(active);
    this.applyNestedLayerOffset(active, contentOffset);
    const velX = visualMoveX / dt;
    const velY = visualMoveY / dt;
    active.childVX += (velX - active.childVX) * 0.35;
    active.childVY += (velY - active.childVY) * 0.35;
    this.applyChildWaterDeform(active, contentOffset, dt, time);
    this.syncSoftBodyVisualStates(active);
  },

  applyChildWaterDeform(active, contentOffset, dt, time) {
    if (!active.childrenDeformAtWall) {
      this.clearChildWaterDeform(active);
      return;
    }
    const speed = Math.hypot(active.childVX, active.childVY);
    const motion = {
      amount: Math.min(0.08, speed / 3600),
      ux: speed > 5 ? active.childVX / speed : 0,
      uy: speed > 5 ? active.childVY / speed : 0,
    };

    for (const state of active.childStates) {
      const pressure = this.childWallPressure(active, state.element, contentOffset, state);
      this.stepChildWallPush(state, pressure, dt);
      this.applyChildPushOffset(state);
      this.stepChildWaterBody(active, state, contentOffset, pressure, motion, dt, time);
    }
  },

  stepChildWallPush(state, pressure, dt) {
    const step = Math.min(Math.max(dt, 0.001), 0.032);
    const minSize = Math.max(1, Math.min(state.element.offsetWidth, state.element.offsetHeight));
    const maxPush = Math.min(34, Math.max(10, minSize * 0.32));
    const targetX = -pressure.ux * pressure.amount * maxPush;
    const targetY = -pressure.uy * pressure.amount * maxPush;
    const stiffness = 260;
    const damping = 30;

    state.pushVX += ((targetX - state.pushX) * stiffness - state.pushVX * damping) * step;
    state.pushVY += ((targetY - state.pushY) * stiffness - state.pushVY * damping) * step;
    state.pushX += state.pushVX * step;
    state.pushY += state.pushVY * step;

    const length = Math.hypot(state.pushX, state.pushY);
    if (length > maxPush) {
      const scale = maxPush / length;
      state.pushX *= scale;
      state.pushY *= scale;
      state.pushVX *= 0.45;
      state.pushVY *= 0.45;
    }
  },

  applyChildPushOffset(state) {
    if (Math.hypot(state.pushX, state.pushY) < 0.05) {
      state.element.style.removeProperty("--powan-child-push-x");
      state.element.style.removeProperty("--powan-child-push-y");
      state.element.style.transform = "";
      return;
    }
    state.element.style.setProperty("--powan-child-push-x", `${state.pushX.toFixed(2)}px`);
    state.element.style.setProperty("--powan-child-push-y", `${state.pushY.toFixed(2)}px`);
    state.element.style.transform = `translate(${state.pushX.toFixed(2)}px, ${state.pushY.toFixed(2)}px)`;
  },

  stepChildWaterBody(active, state, contentOffset, pressure, motion, dt, time) {
    const step = Math.min(Math.max(dt, 0.001), 0.032);
    const follow = 1 - Math.exp(-26 * step);
    state.pressure += (pressure.amount - state.pressure) * follow;
    const amount = state.pressure;
    const rx = state.softBody.cx;
    const ry = state.softBody.cy;
    const localRect = this.childLocalRect(active, state.element, contentOffset, state);
    const parentCenter = active.visualCenter || { x: active.softBody.cx, y: active.softBody.cy };
    const stiffness = 190;
    const damping = 20;

    for (const [index, point] of state.softBody.points.entries()) {
      const nx = (point.restX - state.softBody.cx) / rx;
      const ny = (point.restY - state.softBody.cy) / ry;
      const rest = powanSoftBody.breathedRest(state.softBody, index, time);
      const pointPressure = this.childPointWallPressure(active, localRect, parentCenter, point);
      const wallAlong = nx * pressure.ux + ny * pressure.uy;
      const wallFace = Math.max(0, wallAlong);
      const backFace = Math.max(0, -wallAlong);
      const side = Math.sqrt(Math.max(0, 1 - wallAlong * wallAlong));
      const motionAlong = nx * motion.ux + ny * motion.uy;
      const motionFace = Math.max(0, motionAlong);
      const deformation = Math.max(amount * wallFace, pointPressure.amount);
      const pointSide = Math.sqrt(Math.max(0, 1 - pointPressure.amount));

      let targetX = rest.x;
      let targetY = rest.y;
      targetX -= pointPressure.ux * rx * pointPressure.amount * 0.62;
      targetY -= pointPressure.uy * ry * pointPressure.amount * 0.62;
      targetX -= pressure.ux * rx * amount * wallFace * 0.28;
      targetY -= pressure.uy * ry * amount * wallFace * 0.28;
      targetX += pressure.ux * rx * amount * backFace * 0.09;
      targetY += pressure.uy * ry * amount * backFace * 0.09;
      targetX += nx * rx * deformation * side * 0.20;
      targetY += ny * ry * deformation * side * 0.20;
      targetX += nx * rx * pointPressure.amount * pointSide * 0.12;
      targetY += ny * ry * pointPressure.amount * pointSide * 0.12;
      targetX -= motion.ux * rx * motion.amount * motionFace * 0.24;
      targetY -= motion.uy * ry * motion.amount * motionFace * 0.24;

      const ax = (targetX - point.x) * stiffness - point.vx * damping;
      const ay = (targetY - point.y) * stiffness - point.vy * damping;
      point.vx += ax * step;
      point.vy += ay * step;
      point.x += point.vx * step;
      point.y += point.vy * step;
    }
    state.path.setAttribute("d", powanSoftBody.toPathData(state.softBody));
  },

  childPointWallPressure(active, childRect, center, point) {
    const pointX = childRect.x + point.restX;
    const pointY = childRect.y + point.restY;
    const dx = pointX - center.x;
    const dy = pointY - center.y;
    const distance = Math.max(0.001, Math.hypot(dx, dy));
    const ux = dx / distance;
    const uy = dy / distance;
    const boundary = this.parentBoundaryRadius(active, center, ux, uy);
    const contactBand = Math.max(8, Math.min(childRect.width, childRect.height) * 0.32);
    const distanceToWall = boundary - distance;
    const amount = Math.max(0, Math.min(1, (contactBand - distanceToWall) / contactBand));
    return { amount, ux, uy };
  },

  childWallPressure(active, child, contentOffset, state = null) {
    const localRect = this.childLocalRect(active, child, contentOffset, state);
    const center = active.visualCenter || { x: active.softBody.cx, y: active.softBody.cy };
    const childCenterX = localRect.x + localRect.width / 2;
    const childCenterY = localRect.y + localRect.height / 2;
    const dx = childCenterX - center.x;
    const dy = childCenterY - center.y;
    const distance = Math.max(0.001, Math.hypot(dx, dy));
    const ux = dx / distance;
    const uy = dy / distance;
    const boundary = this.parentBoundaryRadius(active, center, ux, uy);
    const childRadius = this.childRadiusAlong(localRect, ux, uy);
    const padding = Math.max(4, Math.min(localRect.width, localRect.height) * 0.1);
    const distanceToWall = boundary - (distance + childRadius + padding);
    const contactBand = Math.max(16, childRadius * 0.78);
    const amount = Math.max(0, Math.min(1, (contactBand - distanceToWall) / contactBand));
    return { amount, ux, uy };
  },

  childLocalRect(active, child, contentOffset, state = null) {
    const layer = active.contentLayer;
    const layerX = layer ? layer.offsetLeft : 0;
    const layerY = layer ? layer.offsetTop : 0;
    return {
      x: layerX + Number.parseFloat(child.style.left || child.offsetLeft || "0") + contentOffset.x + (state?.pushX || 0),
      y: layerY + Number.parseFloat(child.style.top || child.offsetTop || "0") + contentOffset.y + (state?.pushY || 0),
      width: child.offsetWidth,
      height: child.offsetHeight,
    };
  },

  parentBoundaryRadius(active, center, ux, uy) {
    let radius = 1;
    for (const point of active.softBody.points) {
      radius = Math.max(radius, (point.x - center.x) * ux + (point.y - center.y) * uy);
    }
    return radius;
  },

  childRadiusAlong(rect, ux, uy) {
    const rx = rect.width / 2;
    const ry = rect.height / 2;
    return Math.sqrt((rx * ux) ** 2 + (ry * uy) ** 2);
  },
};
