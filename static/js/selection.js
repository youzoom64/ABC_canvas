var selectionMarqueeElement = null;

function uniqueActiveNodeIds(ids) {
  const result = [];
  const seen = new Set();
  for (const id of ids || []) {
    const nodeId = String(id || "");
    if (!nodeId || seen.has(nodeId) || !nodeById(nodeId)) {
      continue;
    }
    seen.add(nodeId);
    result.push(nodeId);
  }
  return result;
}

function selectedNodeIds() {
  const ids = uniqueActiveNodeIds([...selectedIds]);
  if (selectedId && nodeById(selectedId) && !ids.includes(selectedId)) {
    ids.unshift(selectedId);
  }
  return ids;
}

function selectionCount() {
  return selectedNodeIds().length;
}

function isNodeSelected(nodeId) {
  return Boolean(nodeId && selectedIds.has(nodeId));
}

function syncSelectionControls() {
  const count = selectionCount();
  for (const button of [treeCopyButton, treeDeleteButton, copySelectionMenuButton, deleteSelectionMenuButton]) {
    if (button) {
      button.disabled = count <= 0;
    }
  }
}

function refreshSelectionVisuals() {
  if (typeof powanFocus !== "undefined") {
    powanFocus.applySelected(selectedId);
  }
  if (treeList) {
    treeList.querySelectorAll(".tree-item").forEach((item) => {
      item.classList.toggle("selected", isNodeSelected(item.dataset.id));
    });
  }
  updateCoordinateBadge(nodeById(selectedId));
  syncSelectionControls();
}

function applySelection(
  ids,
  {
    primaryId = null,
    anchorId = null,
    reason = "set-selection",
    renderTree = false,
    updatePanel = true,
    log = true,
  } = {},
) {
  const normalized = uniqueActiveNodeIds(ids);
  const primary = primaryId && normalized.includes(primaryId) ? primaryId : (normalized[0] || null);
  selectedIds = new Set(normalized);
  selectedId = primary;
  selectionAnchorId = anchorId !== null ? anchorId : (primary || selectionAnchorId);
  if (!selectedId) {
    selectionAnchorId = null;
  }
  if (updatePanel && selectedId && typeof selectNode === "function") {
    selectNode(selectedId);
  } else {
    refreshSelectionVisuals();
  }
  if (renderTree && typeof renderTreePanel === "function") {
    renderTreePanel();
  } else {
    syncSelectionControls();
  }
  if (log) {
    logEvent("debug", reason, { selectedIds: normalized, selectedId, count: normalized.length });
  }
  return normalized;
}

function selectableOrderIds(scope = "canvas") {
  if (scope === "tree" && treeList) {
    return [...treeList.querySelectorAll(".tree-item")]
      .map((item) => item.dataset.id)
      .filter((id) => nodeById(id));
  }
  return currentWorldNodes().map((node) => node.id).filter((id) => nodeById(id));
}

function rangeSelectionIds(targetId, scope = "canvas") {
  const order = selectableOrderIds(scope);
  const targetIndex = order.indexOf(targetId);
  if (targetIndex < 0) {
    return [targetId];
  }
  const anchor = selectionAnchorId && order.includes(selectionAnchorId)
    ? selectionAnchorId
    : selectedId && order.includes(selectedId)
      ? selectedId
      : targetId;
  const anchorIndex = order.indexOf(anchor);
  const start = Math.min(anchorIndex, targetIndex);
  const end = Math.max(anchorIndex, targetIndex);
  return order.slice(start, end + 1);
}

function applySelectionFromEvent(nodeId, event, { scope = "canvas" } = {}) {
  if (!nodeById(nodeId)) {
    return [];
  }
  if (event?.shiftKey) {
    return applySelection(rangeSelectionIds(nodeId, scope), {
      primaryId: nodeId,
      anchorId: selectionAnchorId || selectedId || nodeId,
      reason: `${scope}-range-select`,
    });
  }
  if (event?.ctrlKey || event?.metaKey) {
    const next = new Set(selectedNodeIds());
    if (next.has(nodeId) && next.size > 1) {
      next.delete(nodeId);
    } else {
      next.add(nodeId);
    }
    return applySelection([...next], {
      primaryId: nodeId,
      anchorId: nodeId,
      reason: `${scope}-toggle-select`,
    });
  }
  return applySelection([nodeId], {
    primaryId: nodeId,
    anchorId: nodeId,
    reason: `${scope}-single-select`,
  });
}

function selectionClientRect(startX, startY, endX, endY) {
  const left = Math.min(startX, endX);
  const top = Math.min(startY, endY);
  const right = Math.max(startX, endX);
  const bottom = Math.max(startY, endY);
  return {
    left,
    top,
    right,
    bottom,
    width: right - left,
    height: bottom - top,
  };
}

function rectsIntersect(a, b) {
  return a.left <= b.right && a.right >= b.left && a.top <= b.bottom && a.bottom >= b.top;
}

function ensureSelectionMarqueeElement() {
  if (selectionMarqueeElement) {
    return selectionMarqueeElement;
  }
  selectionMarqueeElement = document.createElement("div");
  selectionMarqueeElement.className = "selection-marquee";
  document.body.appendChild(selectionMarqueeElement);
  return selectionMarqueeElement;
}

function selectionIdsInClientRect(scope, rect) {
  const selector = scope === "tree" ? ".tree-item" : ".node";
  const root = scope === "tree" ? treeList : getWorldLayer();
  if (!root) {
    return [];
  }
  return [...root.querySelectorAll(selector)]
    .filter((element) => nodeById(element.dataset.id) && rectsIntersect(rect, element.getBoundingClientRect()))
    .map((element) => element.dataset.id);
}

function updateSelectionMarquee(event) {
  if (!marqueeSelection) {
    return;
  }
  event.preventDefault();
  const rect = selectionClientRect(
    marqueeSelection.startX,
    marqueeSelection.startY,
    event.clientX,
    event.clientY,
  );
  const element = ensureSelectionMarqueeElement();
  element.style.left = `${rect.left}px`;
  element.style.top = `${rect.top}px`;
  element.style.width = `${rect.width}px`;
  element.style.height = `${rect.height}px`;
  const hitIds = selectionIdsInClientRect(marqueeSelection.scope, rect);
  const next = marqueeSelection.additive
    ? uniqueActiveNodeIds([...marqueeSelection.baseIds, ...hitIds])
    : hitIds;
  applySelection(next, {
    primaryId: hitIds[hitIds.length - 1] || next[next.length - 1] || null,
    anchorId: hitIds[0] || marqueeSelection.anchorId || null,
    reason: `${marqueeSelection.scope}-marquee-preview`,
    updatePanel: false,
    log: false,
  });
}

function beginMarqueeSelection(event, scope = "canvas") {
  event.preventDefault();
  event.stopPropagation();
  window.getSelection()?.removeAllRanges();
  marqueeSelection = {
    scope,
    pointerId: event.pointerId,
    startX: event.clientX,
    startY: event.clientY,
    additive: Boolean(event.ctrlKey || event.metaKey),
    baseIds: selectedNodeIds(),
    anchorId: selectionAnchorId || selectedId || null,
  };
  const element = ensureSelectionMarqueeElement();
  element.style.left = `${event.clientX}px`;
  element.style.top = `${event.clientY}px`;
  element.style.width = "0px";
  element.style.height = "0px";
  element.classList.add("active");
  logEvent("debug", `${scope}-marquee-start`, {
    startX: Math.round(event.clientX),
    startY: Math.round(event.clientY),
    additive: marqueeSelection.additive,
  });
}

function finishMarqueeSelection(event) {
  if (!marqueeSelection) {
    return;
  }
  updateSelectionMarquee(event);
  const scope = marqueeSelection.scope;
  const count = selectionCount();
  marqueeSelection = null;
  if (selectionMarqueeElement) {
    selectionMarqueeElement.classList.remove("active");
  }
  if (selectedId && typeof selectNode === "function") {
    selectNode(selectedId);
  } else {
    refreshSelectionVisuals();
  }
  logEvent("debug", `${scope}-marquee-end`, { count, selectedIds: selectedNodeIds() });
}

window.addEventListener("pointermove", (event) => {
  if (marqueeSelection) {
    updateSelectionMarquee(event);
  }
});

window.addEventListener("pointerup", (event) => {
  if (marqueeSelection) {
    finishMarqueeSelection(event);
  }
});

window.addEventListener("pointercancel", () => {
  if (!marqueeSelection) {
    return;
  }
  const scope = marqueeSelection.scope;
  marqueeSelection = null;
  if (selectionMarqueeElement) {
    selectionMarqueeElement.classList.remove("active");
  }
  refreshSelectionVisuals();
  logEvent("debug", `${scope}-marquee-cancel`);
});
