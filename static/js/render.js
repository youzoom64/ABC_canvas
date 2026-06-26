function updateWorldStatus() {
  const worldParent = currentWorldParent();
  if (!worldParent) {
    worldName.textContent = "外側の世界";
    worldPath.textContent = "外側";
    return;
  }
  worldName.textContent = `${meaningName(worldParent)} の世界`;
  worldPath.textContent = ["外側", ...worldPathNodes(worldParent).map(meaningName)].join(" / ");
}

function selectNode(id) {
  const node = nodeById(id);
  powanFocus.applySelected(id);
  updateCoordinateBadge(node);
  if (!node) {
    return;
  }
  if (codePanelNodeId && codePanelNodeId !== id) {
    powanExplorer.setCodeNode(null, "selection-closes-code");
  }
  titleInput.value = node.title || "";
  bodyInput.value = node.body || "";
  powanKindInput.value = node.powanKind === "organ" ? "organ" : "nerve";
  if (codePanelNodeId && !nodeById(codePanelNodeId)) {
    powanExplorer.setCodeNode(null, "selection-clears-missing-code");
  }
  syncCodePanel();
  shapeInput.value = node.style?.shape || "cloud";
  colorInput.value = node.style?.color || "#ffffff";
  accentInput.value = node.style?.accent || "#8ddcff";
  glowInput.checked = Boolean(node.style?.glow);
  blurInput.checked = Boolean(node.style?.blur);
  motionInput.checked = node.style?.motion === "soft";
  refreshSelectionVisuals();
}

function updateCoordinateBadge(node = nodeById(selectedId)) {
  if (!coordinateBadge) {
    return;
  }
  if (!node) {
    coordinateBadge.hidden = true;
    coordinateBadge.textContent = "";
    return;
  }
  const layout = displayLayoutForNode(node);
  const logicalCenter = powanWorkspace.logicalCenterForLayout(node.layout || {});
  coordinateBadge.hidden = false;
  coordinateBadge.textContent = `x ${logicalCenter.x}  y ${logicalCenter.y}`;
  coordinateBadge.title = `${meaningName(node)} / top-left ${Math.round(layout.x)}, ${Math.round(layout.y)} / width ${Math.round(layout.width)} / height ${Math.round(layout.height)}`;
}

function render() {
  const layer = getWorldLayer();
  layer.innerHTML = "";
  renderWorldBoundary(layer);
  const worldParent = currentWorldParent();
  const canvasColor = worldParent?.style?.color || doc.canvas?.background || "#e8f8ff";
  const canvasAccent = worldParent?.style?.accent || "#8ddcff";
  canvas.style.backgroundColor = canvasColor;
  canvas.style.setProperty("--canvas-world-color", canvasColor);
  canvas.style.setProperty("--canvas-accent-color", canvasAccent);
  canvas.classList.toggle("inside-meaning", Boolean(openParentId));
  canvas.classList.toggle("editing-children", Boolean(childEditParentId));
  backButton.disabled = !openParentId;
  updateWorldStatus();
  const nodes = currentWorldNodes();
  for (const node of nodes) {
    layer.appendChild(renderNode(node));
  }
  requestAnimationFrame(() => {
    for (const node of nodes) {
      const element = nodeElementById(node.id);
      if (element) {
        if (!openParentId && node.parent && node.parent === childEditParentId) {
          fitCompactChildFrame(node, element);
          continue;
        }
        fitFrameToText(node, element, { persist: true, instant: true });
      }
    }
    displayMeaningsInsideMeanings();
    restoreSpeakingPowanVisuals();
    powanFocus.applySelected(selectedId);
    updateCoordinateBadge();
  });
  selectNode(powanExplorer.ensureSelected(nodes));
  renderTreePanel();
  if (typeof renderConversationTabs === "function") {
    renderConversationTabs();
  }
}

function renderWorldBoundary(layer) {
  const bounds = powanWorkspace.displayBounds(currentWorldOrigin());
  const boundary = document.createElement("div");
  boundary.className = "world-boundary";
  boundary.setAttribute("aria-hidden", "true");
  boundary.style.left = `${bounds.x}px`;
  boundary.style.top = `${bounds.y}px`;
  boundary.style.width = `${bounds.width}px`;
  boundary.style.height = `${bounds.height}px`;
  boundary.style.setProperty("--world-zero-x", `${bounds.zeroX}px`);
  boundary.style.setProperty("--world-zero-y", `${bounds.zeroY}px`);
  boundary.innerHTML = `
    <div class="world-boundary-grid"></div>
    <div class="world-boundary-frame"></div>
    <div class="world-boundary-axis world-boundary-axis-x"></div>
    <div class="world-boundary-axis world-boundary-axis-y"></div>
    <div class="world-boundary-corner"></div>
  `;
  layer.appendChild(boundary);
}

function powanFaceMetrics(layout) {
  const width = Number(layout?.width || 240);
  const height = Number(layout?.height || 140);
  const base = Math.max(5, Math.min(48, Math.min(width, height) * 0.08125));
  const bodyBase = Math.max(6, Math.min(34, Math.min(width, height) * 0.092));
  return {
    faceSize: Math.round(base),
    bodySize: Math.round(bodyBase),
    codeSize: Math.round(Math.max(4, Math.min(28, base * 0.76))),
  };
}

function applyPowanVisualMetrics(element, layout, { kind = "node", depth = 0, softBody = true, staticSkin = false } = {}) {
  const metrics = powanFaceMetrics(layout);
  const isNested = kind === "nested";
  const isPreview = kind === "preview";
  const shortSide = Math.min(Number(layout?.width || 240), Number(layout?.height || 140));
  const faceSize = isPreview
    ? Math.max(3, Math.min(16, shortSide * 0.16))
    : isNested
      ? Math.max(4, Math.min(28, shortSide * 0.16))
      : metrics.faceSize;
  const bodySize = isPreview
    ? Math.max(2, Math.min(18, Number(layout?.width || 0) * 0.16))
    : metrics.bodySize;
  element.style.setProperty("--powan-face-size", `${Math.round(faceSize)}px`);
  element.style.setProperty("--powan-body-size", `${Math.round(bodySize)}px`);
  element.style.setProperty("--powan-code-label-size", `${metrics.codeSize}px`);
  element.style.setProperty("--powan-morph-duration", `${isPreview ? 8.4 + depth * 0.35 : isNested ? 7.8 : 7}s`);
  element.style.setProperty("--powan-breathe-duration", `${isPreview ? 5.2 + depth * 0.24 : isNested ? 4.8 : 4.5}s`);
  element.style.setProperty("--powan-breathe-scale-start", "1 1");
  element.style.setProperty("--powan-breathe-scale-mid", isNested || isPreview ? "1.03 0.97" : "1 1");
  element.style.setProperty("--powan-breathe-filter-start", isNested || isPreview ? "none" : "drop-shadow(0 6px 10px rgba(62, 129, 158, 0.1))");
  element.style.setProperty("--powan-breathe-filter-mid", isNested || isPreview ? "none" : "drop-shadow(0 12px 18px rgba(62, 129, 158, 0.18))");
  if (softBody && typeof powanSoftBodyView !== "undefined") {
    powanSoftBodyView.attach(element, layout);
  } else if (staticSkin && typeof powanSoftBodyView !== "undefined") {
    powanSoftBodyView.attachStatic(element, layout);
  }
}

function basePowanFaceEmoji(node) {
  if ((node?.code || "").trim()) {
    return "😊";
  }
  if (hasMeaningText(node)) {
    return "🙂";
  }
  return "😐";
}

function powanFaceElapsedMs(nodeId, now = Date.now()) {
  if (!powanFaceTouchedAtById.has(nodeId)) {
    powanFaceTouchedAtById.set(nodeId, now);
  }
  return now - powanFaceTouchedAtById.get(nodeId);
}

function sleepyPowanFaceEmoji(baseEmoji, elapsedMs) {
  const minute = POWAN_FACE_MINUTE_MS;
  const cycle = POWAN_FACE_CYCLE_MS;
  const phase = elapsedMs % cycle;
  if (elapsedMs > 60 * minute) {
    return "😪";
  }
  if (elapsedMs >= 30 * minute) {
    const progress = Math.min(1, Math.max(0, (elapsedMs - 30 * minute) / (30 * minute)));
    const sleepMs = (5 + progress * 25) * 1000;
    if (phase < sleepMs) {
      return "😴";
    }
    if (sleepMs < 20 * 1000 && phase < sleepMs + 1000) {
      return "😦";
    }
    return "😌";
  }
  if (elapsedMs >= 20 * minute) {
    return phase < 3000 ? "🥱" : "😌";
  }
  if (elapsedMs >= 10 * minute) {
    return phase < 5000 ? "😌" : baseEmoji;
  }
  return baseEmoji;
}

function powanFaceEmoji(node, element = null) {
  if (element?.classList?.contains("speaking")) {
    return element.classList.contains("mouth-closed") ? "🙂" : "😀";
  }
  const baseEmoji = basePowanFaceEmoji(node);
  if (!node?.id) {
    return baseEmoji;
  }
  return sleepyPowanFaceEmoji(baseEmoji, powanFaceElapsedMs(node.id));
}

function powanVisualElements(nodeId) {
  const elements = [];
  const direct = nodeElementById(nodeId);
  if (direct) {
    elements.push(direct);
  }
  const selector = `.nested-meaning[data-id="${CSS.escape(nodeId)}"], .nested-preview-meaning[data-id="${CSS.escape(nodeId)}"]`;
  getWorldLayer().querySelectorAll(selector).forEach((element) => {
    if (!elements.includes(element)) {
      elements.push(element);
    }
  });
  return elements;
}

function updatePowanFaceButton(element, node = nodeById(element?.dataset?.id)) {
  const button = element?.querySelector?.(".powan-face-button");
  if (!button || !node) {
    return;
  }
  button.textContent = powanFaceEmoji(node, element);
  button.setAttribute("aria-label", `${meaningName(node)} と会話`);
}

function updatePowanFaceForNode(nodeId) {
  const node = nodeById(nodeId);
  if (!node) {
    return;
  }
  for (const element of powanVisualElements(node.id)) {
    updatePowanFaceButton(element, node);
  }
}

function updateAllPowanFaces() {
  if (!doc?.nodes) {
    return;
  }
  for (const node of doc.nodes) {
    updatePowanFaceForNode(node.id);
  }
}

function restoreSpeakingPowanVisuals() {
  if (!conversationTypingNodeId) {
    return;
  }
  for (const element of powanVisualElements(conversationTypingNodeId)) {
    element.classList.add("speaking");
    element.classList.toggle("mouth-open", Boolean(conversationTypingMouthOpen));
    element.classList.toggle("mouth-closed", !conversationTypingMouthOpen);
    updatePowanFaceButton(element);
  }
}

function startPowanFaceClock() {
  if (powanFaceClockTimer) {
    return;
  }
  powanFaceClockTimer = window.setInterval(updateAllPowanFaces, POWAN_FACE_CLOCK_INTERVAL_MS);
}

function resetPowanFaceClock(nodeId, reason = "powan-touch") {
  const node = nodeById(nodeId);
  if (!node) {
    return;
  }
  powanFaceTouchedAtById.set(node.id, Date.now());
  updatePowanFaceForNode(node.id);
  logEvent("trace", "powan-face-reset", { nodeId: node.id, reason });
}

function resetPowanFaceClocks(nodeIds, reason = "powan-touch-many") {
  for (const nodeId of [...new Set((nodeIds || []).filter(Boolean))]) {
    resetPowanFaceClock(nodeId, reason);
  }
}

function createPowanFaceButton(node, element) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "powan-face-button";
  button.textContent = powanFaceEmoji(node, element);
  button.setAttribute("aria-label", `${meaningName(node)} と会話`);
  button.addEventListener("pointerdown", (event) => {
    event.preventDefault();
    event.stopPropagation();
  });
  button.addEventListener("click", (event) => {
    event.preventDefault();
    event.stopPropagation();
    resetPowanFaceClock(node.id, "face-button-click");
    powanExplorer.toggleConversation(node.id);
  });
  return button;
}

function createPowanDragHitFrame() {
  const frame = document.createElement("div");
  frame.className = "powan-drag-hit-frame";
  for (const side of ["top", "right", "bottom", "left"]) {
    const strip = document.createElement("span");
    strip.className = `powan-drag-hit powan-drag-hit-${side}`;
    frame.append(strip);
  }
  return frame;
}

function createPowanSurface(node, layout, { mode = "world", depth = 0, softBody = true, staticSkin = false } = {}) {
  const element = document.createElement("article");
  const style = node.style || {};
  const baseClass = mode === "world" ? "node" : mode === "preview" ? "nested-preview-meaning" : "nested-meaning";
  const kind = mode === "world" ? "node" : mode;
  element.className = `${baseClass} shape-${style.shape || "cloud"}`;
  element.dataset.id = node.id;
  element.style.left = `${layout.x}px`;
  element.style.top = `${layout.y}px`;
  element.style.width = `${layout.width}px`;
  element.style.height = `${layout.height}px`;
  element.style.setProperty("--node-color", style.color || "#ffffff");
  element.style.setProperty("--accent", style.accent || "#8ddcff");
  if (mode === "preview") {
    element.style.setProperty("--preview-depth", String(depth));
  }
  applyPowanVisualMetrics(element, layout, { kind, depth, softBody, staticSkin });
  element.classList.toggle("glow", Boolean(style.glow));
  element.classList.toggle("blur", Boolean(style.blur));
  element.classList.toggle("motion", style.motion === "soft");
  element.classList.toggle("has-name", hasMeaningText(node));
  element.classList.toggle("has-code", Boolean((node.code || "").trim()));
  element.classList.toggle("has-attachment", Boolean(node.attachment));
  powanFocus.markSelected(element);
  element.append(createPowanDragHitFrame());
  element.append(createPowanFaceButton(node, element));
  const attachmentView = powanAttachments.createView(node, { mode });
  if (attachmentView) {
    element.append(attachmentView);
  }
  return element;
}

function createPowanSurfaceWithoutSoftBody(node, layout, options = {}) {
  return createPowanSurface(node, layout, {
    ...options,
    softBody: false,
    staticSkin: true,
  });
}

function createPowanBody(node, { mode = "world" } = {}) {
  const body = document.createElement("textarea");
  body.className = "node-body";
  body.placeholder = EMPTY_MEANING_PLACEHOLDER;
  body.value = meaningSurfaceText(node);
  body.spellcheck = false;
  body.tabIndex = -1;
  if (mode !== "world") {
    body.rows = 1;
  }
  if (mode === "preview") {
    body.readOnly = true;
    body.tabIndex = -1;
  }
  body.addEventListener("focus", () => {
    resetPowanFaceClock(node.id, "node-body-focus");
    if (!body.value) {
      body.placeholder = "";
    }
  });
  body.addEventListener("blur", () => {
    if (!body.value) {
      body.placeholder = EMPTY_MEANING_PLACEHOLDER;
    }
  });
  body.addEventListener("keydown", (event) => event.stopPropagation());
  return body;
}

function renderNode(node) {
  const layout = displayLayoutForNode(node);
  const element = createPowanSurface(node, layout, { mode: "world" });
  element.classList.toggle("nested", Boolean(node.parent));
  element.classList.toggle("open-parent", node.id === openParentId || node.id === childEditParentId);
  element.classList.toggle("visible-child", Boolean(!openParentId && node.parent && node.parent === childEditParentId));
  element.classList.toggle("interior-node", Boolean(openParentId));

  const body = createPowanBody(node, { mode: "world" });
  body.addEventListener("input", () => {
    powanExplorer.updateMeaning(node.id, { title: body.value }, {
      reason: "node-body-input",
    });
    element.classList.toggle("has-name", hasMeaningText(node));
    updatePowanFaceButton(element, node);
    titleInput.value = node.title;
    fitFrameToText(node, element);
  });
  body.addEventListener("blur", () => {
    element.classList.remove("meaning-editing");
    powanExplorer.endHistoryGroup();
    logEvent("debug", "meaning-editor-close-node", { nodeId: node.id });
  });

  element.append(body);
  const nestedLayer = document.createElement("div");
  nestedLayer.className = "nested-layer";
  element.append(nestedLayer);
  element.addEventListener("pointerdown", (event) => {
    if (event.target?.closest?.(".powan-face-button")) {
      return;
    }
    if (powanHitTest.isNestedTarget(event.target)) {
      return;
    }
    if (element.classList.contains("meaning-editing") && event.target?.closest?.(".node-body")) {
      return;
    }
    resetPowanFaceClock(node.id, "node-pointerdown");
    const decision = powanExplorer.nodeDragDecision(event, element);
    if (!decision.canDrag) {
      if (powanExplorer.canBeginWorldPanFromNode(event, decision)) {
        beginPanIntent(event, {
          nodeId: node.id,
          reason: decision.reason,
          distance: decision.distance,
        });
      }
      return;
    }
    beginPointerIntent(event, node, element);
  }, true);
  element.addEventListener("pointermove", (event) => {
    if (powanHitTest.isNestedTarget(event.target)) {
      powanHitTest.clearNodeCursor(element);
      return;
    }
    powanHitTest.syncNodeCursor(event, element);
  });
  element.addEventListener("pointerleave", () => powanHitTest.clearNodeCursor(element));
  element.addEventListener("contextmenu", (event) => openPowanContextMenu(event, node));
  element.addEventListener("auxclick", (event) => {
    if (event.button === 1) {
      event.preventDefault();
    }
  });
  element.addEventListener("dblclick", () => powanExplorer.enterWorld(node.id, element));
  return element;
}

function openPowanContextMenu(event, node) {
  event.preventDefault();
  event.stopPropagation();
  powanExplorer.openNodeMenu(node.id, event.clientX, event.clientY);
}

function hideMeaningDisplay(nodeId) {
  const element = nodeElementById(nodeId);
  if (element) {
    element.classList.add("hidden-meaning");
  }
}

function visualElementById(nodeId) {
  const escapedId = CSS.escape(nodeId);
  const visibleCandidate = (selector) => (
    [...getWorldLayer().querySelectorAll(selector)]
      .find((element) => {
        const rect = element.getBoundingClientRect();
        return rect.width > 0 && rect.height > 0 && !element.classList.contains("hidden-meaning");
      }) || null
  );
  return visibleCandidate(`.nested-meaning[data-id="${escapedId}"]`) ||
    visibleCandidate(`.nested-preview-meaning[data-id="${escapedId}"]`) ||
    visibleCandidate(`.node[data-id="${escapedId}"]`);
}

function rectSnapshot(rect) {
  if (!rect) {
    return null;
  }
  return {
    left: rect.left,
    top: rect.top,
    width: rect.width,
    height: rect.height,
  };
}

function visualRectForMeaning(nodeId) {
  return rectSnapshot(visualElementById(nodeId)?.getBoundingClientRect());
}

function attachSoftBodyToTransitionSurface(element, layout, { kind = "node" } = {}) {
  if (!element || typeof powanSoftBodyView === "undefined") {
    return;
  }
  element.classList.add("softbody-visual");
  applyPowanVisualMetrics(element, layout, { kind });
}

function clampPopScale(value) {
  if (!Number.isFinite(value)) {
    return 1;
  }
  return Math.max(0.15, Math.min(4, value));
}

function applyMeaningPop(element, className, fromRect, toRect) {
  if (!element || !fromRect || !toRect || !toRect.width || !toRect.height) {
    logEvent("debug", "meaning-pop-skipped", {
      nodeId: element?.dataset?.id || null,
      className,
      hasElement: Boolean(element),
      hasFromRect: Boolean(fromRect),
      hasToRect: Boolean(toRect),
    });
    return false;
  }
  const fromCenterX = fromRect.left + fromRect.width / 2;
  const fromCenterY = fromRect.top + fromRect.height / 2;
  const toCenterX = toRect.left + toRect.width / 2;
  const toCenterY = toRect.top + toRect.height / 2;
  element.style.setProperty("--meaning-pop-x-start", String(clampPopScale(fromRect.width / toRect.width)));
  element.style.setProperty("--meaning-pop-y-start", String(clampPopScale(fromRect.height / toRect.height)));
  element.style.setProperty("--meaning-pop-translate-x", `${Math.round(fromCenterX - toCenterX)}px`);
  element.style.setProperty("--meaning-pop-translate-y", `${Math.round(fromCenterY - toCenterY)}px`);
  logEvent("trace", "meaning-pop-start", {
    nodeId: element.dataset.id || null,
    className,
    fromRect: {
      left: Math.round(fromRect.left),
      top: Math.round(fromRect.top),
      width: Math.round(fromRect.width),
      height: Math.round(fromRect.height),
    },
    toRect: {
      left: Math.round(toRect.left),
      top: Math.round(toRect.top),
      width: Math.round(toRect.width),
      height: Math.round(toRect.height),
    },
    translate: {
      x: Math.round(fromCenterX - toCenterX),
      y: Math.round(fromCenterY - toCenterY),
    },
  });
  element.classList.remove("meaning-enter-pop", "meaning-release-pop");
  void element.offsetWidth;
  element.classList.add(className);
  window.setTimeout(() => {
    element.classList.remove(className);
    element.style.removeProperty("--meaning-pop-x-start");
    element.style.removeProperty("--meaning-pop-y-start");
    element.style.removeProperty("--meaning-pop-translate-x");
    element.style.removeProperty("--meaning-pop-translate-y");
  }, 520);
  return true;
}

function animateMeaningEntering(childId, parentId, { fromRect = null } = {}) {
  const parentElement = visualElementById(parentId);
  const targetElement = visualElementById(childId);
  const targetRect = visualRectForMeaning(childId);
  applyMeaningPop(targetElement, "meaning-enter-pop", fromRect, targetRect);
  if (parentElement) {
    parentElement.classList.add("holding-meaning");
    window.setTimeout(() => parentElement.classList.remove("holding-meaning"), 320);
  }
}

function animateMeaningRelease(childId, parentId, { fromRect = null } = {}) {
  const targetElement = visualElementById(childId);
  const targetRect = visualRectForMeaning(childId);
  applyMeaningPop(targetElement, "meaning-release-pop", fromRect, targetRect);
  const parentElement = parentId ? visualElementById(parentId) : null;
  if (parentElement) {
    parentElement.classList.add("releasing-meaning");
    window.setTimeout(() => parentElement.classList.remove("releasing-meaning"), 320);
  }
}

function holdMeaningInsideMeaning(parent, child) {
  resetPowanFaceClocks([parent?.id, child?.id], "hold-meaning-touch");
  powanExplorer.attach(child.id, parent.id);
}

function displayMeaningsInsideMeanings() {
  const nodes = currentWorldNodes();
  for (const node of nodes) {
    const element = nodeElementById(node.id);
    if (!element) {
      continue;
    }
    const layer = element.querySelector(".nested-layer");
    if (layer) {
      layer.innerHTML = "";
    }
    element.classList.remove("has-nested-meanings");
  }
  for (const parent of nodes) {
    const children = meaningChildren(parent);
    if (!children.length) {
      continue;
    }
    const parentElement = nodeElementById(parent.id);
    const layer = parentElement?.querySelector(".nested-layer");
    if (!parentElement || !layer) {
      continue;
    }
    parentElement.classList.add("has-nested-meanings");
    if (parent.id === childEditParentId) {
      continue;
    }
    const scale = divideMeaningDisplaySizeByMeaningCount(children.length);
    for (const placement of arrangeHeldMeaningsEvenly(parent, children, scale)) {
      const chip = renderNestedMeaning(placement.node, placement);
      makeMeaningTranslucent(chip);
      layer.appendChild(chip);
    }
  }
}

function makeMeaningTranslucent(element) {
  element.classList.add("translucent-meaning");
}

function pointerDebugElement(element) {
  if (!element) {
    return null;
  }
  const style = getComputedStyle(element);
  return {
    tag: element.tagName?.toLowerCase() || "",
    className: String(element.className || ""),
    nodeId: element.dataset?.id || null,
    pointerEvents: style.pointerEvents,
    zIndex: style.zIndex,
  };
}

function pointerDebugSnapshot(event, element) {
  const target = event.target;
  const fromPoint = document.elementsFromPoint(event.clientX, event.clientY).slice(0, 6);
  const path = typeof event.composedPath === "function" ? event.composedPath().slice(0, 8) : [];
  const elementRect = element?.getBoundingClientRect?.();
  return {
    pointerId: event.pointerId,
    button: event.button,
    buttons: event.buttons,
    clientX: Math.round(event.clientX),
    clientY: Math.round(event.clientY),
    target: pointerDebugElement(target),
    currentTarget: pointerDebugElement(event.currentTarget),
    nestedTarget: pointerDebugElement(target?.closest?.(".nested-meaning, .nested-preview-meaning")),
    nodeTarget: pointerDebugElement(target?.closest?.(".node")),
    layerTarget: pointerDebugElement(target?.closest?.(".nested-layer, .nested-preview-layer")),
    fromPoint: fromPoint.map(pointerDebugElement),
    path: path.map(pointerDebugElement),
    element: pointerDebugElement(element),
    elementRect: elementRect ? {
      left: Math.round(elementRect.left),
      top: Math.round(elementRect.top),
      width: Math.round(elementRect.width),
      height: Math.round(elementRect.height),
    } : null,
  };
}

function logNestedPointerDebug(action, event, node, element, details = {}) {
  logEvent("debug", action, {
    nodeId: node?.id || null,
    parentId: node?.parent || null,
    snapshot: pointerDebugSnapshot(event, element),
    ...details,
  });
}

function holdMeaningCount(node) {
  return powanExplorer.setHoldingCount(node);
}

function divideMeaningDisplaySizeByMeaningCount(count) {
  if (count <= 1) {
    return 0.72;
  }
  if (count <= 2) {
    return 0.58;
  }
  if (count <= 4) {
    return 0.48;
  }
  if (count <= 9) {
    return 0.34;
  }
  return 0.26;
}

function arrangeHeldMeaningsEvenly(parent, children, scale, { expanded = false } = {}) {
  return children.map((child) => {
    if (expanded) {
      return {
        node: child,
        ...powanPlacement.worldRectToInteriorRect(parent, powanPlacement.nodeLayout(child)),
      };
    }
    return nestedPlacementFromLayout(parent, child);
  });
}

function nestedPlacementFromLayout(parent, child) {
  const parentLayout = parent.layout || {};
  const parentWidth = Number(parentLayout.width || NODE_LIMITS.minWidth);
  const parentHeight = Number(parentLayout.height || NODE_LIMITS.minHeight);
  const layerInset = 14;
  const layerSize = {
    width: Math.max(1, parentWidth - layerInset * 2),
    height: Math.max(1, parentHeight - layerInset * 2),
  };
  const rect = powanPlacement.nestedViewRect(parent, child, layerSize);
  return {
    node: child,
    ...rect,
  };
}

function meaningInteriorDisplayArea(parent) {
  const layout = parent.layout || {};
  const inset = 28;
  return {
    x: inset,
    y: inset,
    width: Math.max(56, Number(layout.width || 180) - inset * 2),
    height: Math.max(40, Number(layout.height || 104) - inset * 2),
  };
}

function childPreviewSize(cellWidth, cellHeight, scale) {
  const width = Math.max(72, Math.min(150, cellWidth * scale));
  const height = Math.max(28, Math.min(58, width * 0.38, cellHeight * 0.72));
  return {
    width: Math.min(width, Math.max(58, cellWidth - 12)),
    height: Math.min(height, Math.max(24, cellHeight - 12)),
  };
}

function expandedChildSize(cellWidth, cellHeight, scale) {
  const width = Math.max(NODE_LIMITS.minWidth, Math.min(300, cellWidth * scale));
  const height = Math.max(NODE_LIMITS.minHeight, Math.min(180, cellHeight * scale));
  return {
    width: Math.min(width, Math.max(NODE_LIMITS.minWidth, cellWidth - 18)),
    height: Math.min(height, Math.max(NODE_LIMITS.minHeight, cellHeight - 18)),
  };
}

function expandedMeaningInteriorArea() {
  return { ...INTERIOR_STAGE };
}

function toggleMeaningInterior(parentId) {
  const parent = nodeById(parentId);
  if (!parent || !meaningChildren(parent).length || openParentId) {
    return;
  }
  powanExplorer.setChildEditParent(childEditParentId === parentId ? null : parentId, "toggle-child-edit");
  if (childEditParentId) {
    enterMeaningInterior(parent);
    powanExplorer.setSelected(meaningChildren(parent)[0]?.id || parentId, "toggle-child-edit-select-child");
  } else {
    powanExplorer.setSelected(parentId, "toggle-child-edit-select-parent");
  }
  render();
}

function enterMeaningInterior(parent) {
  const children = meaningChildren(parent);
  const shouldPack = children.some((child) => !powanPlacement.hasNestedLayout(child, parent.id));
  powanExplorer.syncParentCoordinates(parent.id, {
    force: shouldPack,
    reason: "enter-interior-coordinates",
  });
}

function interiorChildScale(count) {
  if (count <= 1) {
    return 0.92;
  }
  if (count <= 4) {
    return 0.74;
  }
  if (count <= 9) {
    return 0.58;
  }
  return 0.46;
}

function fitCompactChildFrame(node, element) {
  const layout = node.layout || {};
  const width = Math.max(36, Number(layout.width || 54));
  const height = Math.max(28, Number(layout.height || 38));
  element.style.width = `${width}px`;
  element.style.height = `${height}px`;
  if (typeof powanSoftBodyView !== "undefined") {
    powanSoftBodyView.resizeElement(element, { width, height });
  }
  preventTextOvertake(node, element, { width, height });
}

function releaseMeaningFromParent(child) {
  powanExplorer.detach(child.id);
}

function isMeaningOutsideParent(child) {
  if (!child.parent) {
    return false;
  }
  const parent = nodeById(child.parent);
  if (!parent) {
    return false;
  }
  const childLayout = child.layout || {};
  const worldArea = powanPlacement.parentWorldArea(parent);
  const childCenterX = Number(childLayout.x || 0) + Number(childLayout.width || 0) / 2;
  const childCenterY = Number(childLayout.y || 0) + Number(childLayout.height || 0) / 2;
  return (
    childCenterX < worldArea.x ||
    childCenterY < worldArea.y ||
    childCenterX > worldArea.x + worldArea.width ||
    childCenterY > worldArea.y + worldArea.height
  );
}

function renderNestedMeaning(node, placement) {
  const chip = createPowanSurface(node, placement, { mode: "nested" });
  chip.classList.toggle("name-editing", nestedNameEditNodeId === node.id);
  chip.addEventListener("pointerdown", (event) => {
    logNestedPointerDebug("nested-chip-pointerdown-capture", event, node, chip);
  }, true);
  chip.addEventListener("pointerdown", (event) => {
    resetPowanFaceClock(node.id, "nested-chip-pointerdown");
    beginNestedPointer(event, node, chip);
  });
  chip.addEventListener("pointermove", (event) => powanHitTest.syncNodeCursor(event, chip));
  chip.addEventListener("pointerleave", () => powanHitTest.clearNodeCursor(chip));
  chip.addEventListener("contextmenu", (event) => openPowanContextMenu(event, node));
  chip.addEventListener("dblclick", (event) => {
    event.stopPropagation();
    powanExplorer.enterWorld(node.id, chip);
  });
  const body = document.createElement("div");
  body.className = "node-body nested-body-label";
  body.textContent = meaningSurfaceText(node) || EMPTY_MEANING_PLACEHOLDER;
  body.addEventListener("pointerdown", (event) => {
    resetPowanFaceClock(node.id, "nested-body-pointerdown");
    logNestedPointerDebug("nested-body-pointerdown-stop", event, node, chip, {
      reason: "nested-body-display-only",
    });
    event.preventDefault();
    event.stopPropagation();
  });
  body.addEventListener("dblclick", (event) => {
    event.preventDefault();
    event.stopPropagation();
  });
  chip.append(body);
  appendNestedMeaningPreview(chip, node, placement);
  return chip;
}

function beginNestedNameEdit(nodeId, chip, body) {
  nestedNameEditNodeId = nodeId;
  powanExplorer.select(nodeId);
  chip.classList.add("name-editing");
  body.readOnly = false;
  logEvent("debug", "nested-name-edit-start", { nodeId });
  window.requestAnimationFrame(() => {
    body.focus();
    body.select();
  });
}

function finishNestedNameEdit(nodeId, chip) {
  if (nestedNameEditNodeId !== nodeId) {
    return;
  }
  nestedNameEditNodeId = null;
  powanExplorer.endHistoryGroup();
  chip.classList.remove("name-editing");
  const body = chip.querySelector(":scope > .node-body");
  if (body) {
    body.readOnly = true;
  }
  logEvent("debug", "nested-name-edit-finish", { nodeId });
}

function meaningChildren(parent) {
  return powanExplorer.childrenOf(parent);
}
