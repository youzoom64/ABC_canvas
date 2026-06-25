function preserveLocalNodeLayouts(nextDoc, previousDoc) {
  if (!Array.isArray(nextDoc?.nodes) || !Array.isArray(previousDoc?.nodes)) {
    return { doc: nextDoc, preservedCount: 0 };
  }
  const previousById = new Map(previousDoc.nodes.map((node) => [node.id, node]));
  let preservedCount = 0;
  const merged = {
    ...nextDoc,
    nodes: nextDoc.nodes.map((node) => {
      const previous = previousById.get(node.id);
      if (!previous) {
        return node;
      }
      const nextNode = { ...node };
      if (previous.layout) {
        nextNode.layout = clonePlain(previous.layout);
      }
      if (previous.nestedLayoutByParent) {
        nextNode.nestedLayoutByParent = clonePlain(previous.nestedLayoutByParent);
      }
      if (Object.prototype.hasOwnProperty.call(previous, "userSized")) {
        nextNode.userSized = previous.userSized;
      }
      preservedCount += 1;
      return nextNode;
    }),
  };
  return { doc: merged, preservedCount };
}

var powanExplorer = {
  setProjectName(name, reason = "set-project-name") {
    projectName = name;
    if (projectBadge) {
      projectBadge.textContent = name;
      projectBadge.title = `powan_work/${name}`;
    }
    logEvent("debug", reason, { projectName: name });
  },
  setDocumentName(name, reason = "set-document-name") {
    documentName = name;
    logEvent("debug", reason, { name });
  },
  setRandomPowanColor(enabled, reason = "set-random-powan-color") {
    setRandomPowanColor(enabled, reason);
  },
  recordHistory(reason = "history", { groupKey = null } = {}) {
    if (!doc) {
      return false;
    }
    if (groupKey && historyGroupKey === groupKey) {
      return false;
    }
    const snapshot = historyStateSnapshot();
    if (!snapshot) {
      return false;
    }
    const signature = historyStateSignature(snapshot);
    const previous = undoStack[undoStack.length - 1];
    if (previous?.signature === signature) {
      historyGroupKey = groupKey || null;
      return false;
    }
    undoStack.push({ snapshot, signature, reason });
    if (undoStack.length > HISTORY_LIMIT) {
      undoStack.shift();
    }
    redoStack = [];
    historyGroupKey = groupKey || null;
    updateHistoryButtons();
    logEvent("trace", "history-record", {
      reason,
      groupKey,
      undoCount: undoStack.length,
      redoCount: redoStack.length,
    });
    return true;
  },
  endHistoryGroup(groupKey = null) {
    if (!groupKey || historyGroupKey === groupKey) {
      historyGroupKey = null;
    }
  },
  clearHistory(reason = "clear-history") {
    clearDocumentHistory(reason);
  },
  undo() {
    if (!undoStack.length) {
      logEvent("debug", "undo-empty");
      return false;
    }
    const current = historyStateSnapshot();
    const entry = undoStack.pop();
    if (current) {
      redoStack.push({ snapshot: current, signature: historyStateSignature(current), reason: "redo-point" });
    }
    historyGroupKey = null;
    return applyHistoryState(entry.snapshot, "undo-history");
  },
  redo() {
    if (!redoStack.length) {
      logEvent("debug", "redo-empty");
      return false;
    }
    const current = historyStateSnapshot();
    const entry = redoStack.pop();
    if (current) {
      undoStack.push({ snapshot: current, signature: historyStateSignature(current), reason: "undo-point" });
    }
    historyGroupKey = null;
    return applyHistoryState(entry.snapshot, "redo-history");
  },
  setDocument(
    nextDoc,
    {
      name = documentName,
      status = "loaded",
      resetWorld = true,
      preserveView = false,
      restoreViewport = resetWorld,
      restoreWorld = resetWorld,
      resetHistory = true,
      preserveLocalLayouts = false,
      reason = "set-document",
    } = {},
  ) {
    const previousDoc = doc;
    const previousSelectedId = selectedId;
    const previousSelectedIds = new Set(selectedIds);
    const previousOpenParentId = openParentId;
    const previousChildEditParentId = childEditParentId;
    const previousCodePanelNodeId = codePanelNodeId;
    const previousConversationNodeId = conversationNodeId;
    const previousCollapsedIds = new Set(collapsedTreeNodeIds);
    const preserved = preserveLocalLayouts
      ? preserveLocalNodeLayouts(nextDoc, previousDoc)
      : { doc: nextDoc, preservedCount: 0 };
    documentName = name;
    doc = normalizeDocumentWorkspace(preserved.doc, `${reason}-workspace`);
    if (preserveLocalLayouts) {
      logEvent("debug", `${reason}-preserve-local-layouts`, {
        preservedCount: preserved.preservedCount,
        incomingNodeCount: Array.isArray(nextDoc?.nodes) ? nextDoc.nodes.length : 0,
      });
    }
    if (resetWorld) {
      powanFaceTouchedAtById.clear();
    } else {
      const nodeIds = new Set((doc.nodes || []).map((node) => node.id));
      for (const nodeId of powanFaceTouchedAtById.keys()) {
        if (!nodeIds.has(nodeId)) {
          powanFaceTouchedAtById.delete(nodeId);
        }
      }
    }
    collapsedTreeNodeIds.clear();
    if (resetWorld) {
      openParentId = null;
      childEditParentId = null;
      codePanelNodeId = null;
      conversationNodeId = null;
      conversationTabs = [];
      conversationTabStates.clear();
      activeConversationTabId = null;
      viewportBeforeInterior = null;
    } else if (preserveView) {
      openParentId = nodeById(previousOpenParentId) ? previousOpenParentId : null;
      childEditParentId = nodeById(previousChildEditParentId) ? previousChildEditParentId : null;
      codePanelNodeId = nodeById(previousCodePanelNodeId) ? previousCodePanelNodeId : null;
      conversationNodeId = nodeById(previousConversationNodeId) ? previousConversationNodeId : null;
      conversationTabs = conversationTabs.filter((tab) => !tab.nodeId || nodeById(tab.nodeId));
      const tabIds = new Set(conversationTabs.map((tab) => tab.id));
      for (const tabId of [...conversationTabStates.keys()]) {
        if (!tabIds.has(tabId)) {
          conversationTabStates.delete(tabId);
        }
      }
      if (activeConversationTabId && !tabIds.has(activeConversationTabId)) {
        activeConversationTabId = conversationTabs[0]?.id || null;
      }
      previousCollapsedIds.forEach((id) => {
        if (nodeById(id)) {
          collapsedTreeNodeIds.add(id);
        }
      });
    }
    if (restoreViewport) {
      restoreViewportFromDocument(doc, {
        resetMissing: resetWorld,
        restoreWorld,
        reason: `${reason}-viewport`,
      });
    }
    selectedId = preserveView && nodeById(previousSelectedId) ? previousSelectedId : (firstActiveNode()?.id || null);
    const nextSelectedIds = preserveView
      ? uniqueActiveNodeIds([...previousSelectedIds])
      : uniqueActiveNodeIds(selectedId ? [selectedId] : []);
    if (selectedId && !nextSelectedIds.includes(selectedId)) {
      nextSelectedIds.unshift(selectedId);
    }
    selectedIds = new Set(nextSelectedIds);
    selectionAnchorId = selectedId;
    if (resetHistory) {
      clearDocumentHistory(`${reason}-history`);
    }
    saveState.textContent = status;
    logEvent("debug", reason, { name, nodeCount: doc.nodes.length });
  },
  setSelected(nodeId, reason = "set-selected") {
    applySelection(nodeId ? [nodeId] : [], {
      primaryId: nodeId,
      anchorId: nodeId,
      reason,
      updatePanel: false,
    });
  },
  touchPowan(nodeId, reason = "touch-powan") {
    resetPowanFaceClock(nodeId, reason);
  },
  touchPowans(nodeIds, reason = "touch-powans") {
    resetPowanFaceClocks(nodeIds, reason);
  },
  meaningDisplayText(node, { emptyText = "名前のないポワン", maxLength = 32 } = {}) {
    const text = meaningSurfaceText(node);
    return text ? text.split("\n")[0].slice(0, maxLength) : emptyText;
  },
  nestedMeaningDisplayText(node) {
    return this.meaningDisplayText(node, { emptyText: EMPTY_MEANING_PLACEHOLDER });
  },
  nodeDragDecision(event, element) {
    const decision = powanHitTest.dragDecision(event, element);
    logEvent("trace", "drag-hit-test", {
      nodeId: element.dataset.id || null,
      pointerId: event.pointerId,
      clientX: Math.round(event.clientX),
      clientY: Math.round(event.clientY),
      ...decision,
    });
    if (!decision.canDrag || decision.nestedTarget || decision.textTarget || decision.nestedLayerTarget) {
      logEvent("debug", "drag-hit-test-blocking-surface", {
        nodeId: element.dataset.id || null,
        pointerId: event.pointerId,
        clientX: Math.round(event.clientX),
        clientY: Math.round(event.clientY),
        ...decision,
      });
    }
    return decision;
  },
  canBeginNodeDrag(event, element) {
    return this.nodeDragDecision(event, element).canDrag;
  },
  canBeginWorldPanFromNode(event, decision) {
    return (
      event.button === 0 &&
      decision?.insideEllipse &&
      !decision?.canDrag &&
      !decision?.nestedTarget
    );
  },
  ensureSelected(nodes) {
    if (!selectedId || (openParentId && !nodes.some((node) => node.id === selectedId))) {
      selectedId = nodes[0]?.id || openParentId || firstActiveNode()?.id || null;
      selectedIds = new Set(uniqueActiveNodeIds(selectedId ? [selectedId] : []));
      selectionAnchorId = selectedId;
      logEvent("debug", "ensure-selected", { nodeId: selectedId });
    } else if (selectedId && !selectedIds.has(selectedId)) {
      selectedIds.add(selectedId);
    }
    return selectedId;
  },
  setCodeNode(nodeId, reason = "set-code-node") {
    codePanelNodeId = nodeId;
    logEvent("debug", reason, { nodeId });
  },
  updateCode(nodeId, code, { renderAfter = true, reason = "update-code" } = {}) {
    const node = nodeById(nodeId);
    if (!node) {
      logEvent("warn", "update-code-missing-node", { nodeId, reason });
      return null;
    }
    this.recordHistory(reason, { groupKey: `code:${node.id}` });
    node.code = code;
    this.touchPowan(node.id, reason);
    setDirty();
    logEvent("debug", reason, { nodeId, length: code.length });
    if (renderAfter) {
      render();
    }
    return node;
  },
  setCodeLanguage(nodeId, language, reason = "set-code-language") {
    const node = nodeById(nodeId);
    if (!node) {
      logEvent("warn", "set-code-language-missing-node", { nodeId, language, reason });
      return null;
    }
    this.recordHistory(reason, { groupKey: `code-language:${node.id}` });
    node.codeLanguage = language;
    this.touchPowan(node.id, reason);
    setDirty();
    logEvent("debug", reason, { nodeId, language });
    return node;
  },
  updateMeaning(nodeId, patch, { renderAfter = false, refreshTree = true, reason = "update-meaning" } = {}) {
    const node = nodeById(nodeId);
    if (!node) {
      logEvent("warn", "update-meaning-missing-node", { nodeId, reason });
      return null;
    }
    const groupKey = Object.prototype.hasOwnProperty.call(patch, "powanKind")
      ? `meaning-kind:${node.id}`
      : Object.prototype.hasOwnProperty.call(patch, "body")
        ? `meaning-body:${node.id}`
        : `meaning-title:${node.id}`;
    this.recordHistory(reason, { groupKey });
    if (Object.prototype.hasOwnProperty.call(patch, "title")) {
      node.title = patch.title || "";
    }
    if (Object.prototype.hasOwnProperty.call(patch, "body")) {
      node.body = patch.body || "";
    }
    if (Object.prototype.hasOwnProperty.call(patch, "powanKind")) {
      node.powanKind = patch.powanKind === "organ" ? "organ" : "nerve";
    }
    this.touchPowan(node.id, reason);
    setDirty();
    logEvent("debug", reason, {
      nodeId,
      titleLength: (node.title || "").length,
      bodyLength: (node.body || "").length,
      powanKind: node.powanKind || "nerve",
    });
    if (renderAfter) {
      render();
    } else {
      updateWorldStatus();
      if (refreshTree) {
        renderTreePanel();
      }
      updateCoordinateBadge(node);
    }
    return node;
  },
  openNodeMenu(nodeId, clientX, clientY) {
    const node = nodeById(nodeId);
    if (!node) {
      logEvent("warn", "open-node-menu-missing-node", { nodeId });
      return;
    }
    this.closeWorldMenu("open-node-menu-close-world-menu");
    nodeContextMenuNodeId = node.id;
    this.touchPowan(node.id, "open-node-menu-touch");
    if (!isNodeSelected(node.id)) {
      this.select(node.id);
    } else {
      selectedId = node.id;
      selectNode(node.id);
      refreshSelectionVisuals();
    }
    showNodeContextMenu(clientX, clientY);
    logEvent("debug", "open-node-menu", { nodeId, clientX, clientY });
  },
  closeNodeMenu(reason = "close-node-menu") {
    hideNodeContextMenu();
    logEvent("debug", reason, { nodeId: nodeContextMenuNodeId });
    nodeContextMenuNodeId = null;
  },
  openWorldMenu(clientX, clientY) {
    this.closeNodeMenu("open-world-menu-close-node-menu");
    showWorldContextMenu(clientX, clientY);
    logEvent("debug", "open-world-menu", {
      clientX,
      clientY,
      openParentId: openParentId || null,
    });
  },
  closeWorldMenu(reason = "close-world-menu") {
    hideWorldContextMenu();
    logEvent("debug", reason, { openParentId: openParentId || null });
  },
  talkToPowan(nodeId) {
    const node = nodeById(nodeId);
    if (!node) {
      logEvent("warn", "talk-powan-missing-node", { nodeId });
      return;
    }
    this.select(node.id);
    openConversationPanel(node.id);
    logEvent("debug", "talk-powan-requested", { nodeId: node.id, name: meaningName(node) });
  },
  talkToPowanInNewTab(nodeId) {
    const node = nodeById(nodeId);
    if (!node) {
      logEvent("warn", "talk-powan-new-tab-missing-node", { nodeId });
      return;
    }
    this.select(node.id);
    openConversationPanel(node.id, { tabMode: "new", reason: "talk-powan-new-tab-requested" });
    logEvent("debug", "talk-powan-new-tab-requested", { nodeId: node.id, name: meaningName(node) });
  },
  toggleConversation(nodeId) {
    const node = nodeById(nodeId);
    if (!node) {
      logEvent("warn", "toggle-conversation-missing-node", { nodeId });
      return;
    }
    if (conversationNodeId === node.id && conversationPanel && !conversationPanel.hidden && !conversationPanelCollapsed) {
      this.touchPowan(node.id, "face-toggle-close-touch");
      closeConversationPanel("face-toggle-close-conversation");
      logEvent("debug", "face-toggle-conversation-closed", { nodeId: node.id });
      return;
    }
    this.talkToPowan(node.id);
    logEvent("debug", "face-toggle-conversation-opened", { nodeId: node.id });
  },
  closeConversation(reason = "close-conversation") {
    closeConversationPanel(reason);
  },
  closeCode(reason = "close-code") {
    logEvent("debug", reason, { nodeId: codePanelNodeId });
    if (codePanelNodeId) {
      this.endHistoryGroup(`code:${codePanelNodeId}`);
      this.endHistoryGroup(`code-language:${codePanelNodeId}`);
    }
    codePanelNodeId = null;
    syncCodePanel();
  },
  setWorld(parentId, reason = "set-world") {
    openParentId = parentId;
    logEvent("debug", reason, { parentId });
  },
  setChildEditParent(parentId, reason = "set-child-edit-parent") {
    childEditParentId = parentId;
    logEvent("debug", reason, { parentId });
  },
  clearChildEditParent(reason = "clear-child-edit-parent") {
    if (!childEditParentId) {
      return;
    }
    logEvent("debug", reason, { parentId: childEditParentId });
    childEditParentId = null;
  },
  resetWorldState(reason = "reset-world-state") {
    logEvent("debug", reason, { parentId: openParentId, childEditParentId, codePanelNodeId });
    openParentId = null;
    childEditParentId = null;
    codePanelNodeId = null;
  },
  setNodeLayout(nodeId, patch, reason = "set-node-layout") {
    const node = nodeById(nodeId);
    if (!node) {
      logEvent("warn", "set-node-layout-missing-node", { nodeId, reason });
      return null;
    }
    node.layout = powanWorkspace.clampLayout({
      ...(node.layout || {}),
      ...patch,
    });
    logEvent("debug", reason, { nodeId, layout: node.layout });
    return node;
  },
  setNestedLayout(nodeId, parentId, patch, reason = "set-nested-layout") {
    const node = nodeById(nodeId);
    if (!node) {
      logEvent("warn", "set-nested-layout-missing-node", { nodeId, parentId, reason });
      return null;
    }
    node.nestedLayoutByParent = {
      ...(node.nestedLayoutByParent || {}),
      [parentId]: {
        ...((node.nestedLayoutByParent || {})[parentId] || {}),
        ...patch,
      },
    };
    logEvent("debug", reason, { nodeId, parentId, layout: node.nestedLayoutByParent[parentId] });
    return node;
  },
  syncParentCoordinates(parentId, { force = false, reason = "sync-parent-coordinates" } = {}) {
    const parent = nodeById(parentId);
    if (!parent) {
      logEvent("warn", "sync-parent-coordinates-missing-parent", { parentId, reason });
      return [];
    }
    const plans = powanPlacement.planParentChildren(parent, this.childrenOf(parent));
    for (const plan of plans) {
      const child = plan.node;
      if (force || !powanPlacement.hasWorldLayout(child)) {
        this.setNodeLayout(child.id, plan.worldLayout, `${reason}-world`);
      }
      if (force || !powanPlacement.hasNestedLayout(child, parent.id)) {
        this.setNestedLayout(child.id, parent.id, plan.nestedLayout, `${reason}-nested`);
      }
    }
    logEvent("debug", reason, { parentId, childCount: plans.length, force });
    return plans;
  },
  ensureParentSizeForArrangedChildren(parent, childCount, reason = "arrange-parent-size") {
    if (!parent || childCount <= 0) {
      return parent;
    }
    const layout = powanPlacement.nodeLayout(parent);
    const minimum = powanPlacement.minimumParentSizeForChildren(childCount, appSettings.arrangeSize);
    const nextWidth = Math.min(NODE_LIMITS.maxWidth, Math.max(layout.width, minimum.width, NODE_LIMITS.minWidth));
    const nextHeight = Math.min(NODE_LIMITS.maxHeight, Math.max(layout.height, minimum.height, NODE_LIMITS.minHeight));
    if (Math.round(nextWidth) === Math.round(layout.width) && Math.round(nextHeight) === Math.round(layout.height)) {
      return parent;
    }
    const center = powanPlacement.rectCenter(layout);
    parent.userSized = true;
    const nextLayout = {
      x: Math.round(center.x - nextWidth / 2),
      y: Math.round(center.y - nextHeight / 2),
      width: Math.round(nextWidth),
      height: Math.round(nextHeight),
    };
    this.syncChildCoordinatesFromWorld(parent.id, parent.parent || null, nextLayout, `${reason}-layout`);
    logEvent("debug", reason, {
      parentId: parent.id,
      childCount,
      previous: layout,
      next: parent.layout,
      minimum,
    });
    return parent;
  },
  arrangeParentChildren(parent, reason = "arrange-parent-children") {
    const children = this.childrenOf(parent);
    if (!children.length) {
      return [];
    }
    this.ensureParentSizeForArrangedChildren(parent, children.length, `${reason}-parent-size`);
    const plans = powanPlacement.planParentChildren(parent, children, {
      spacing: appSettings.arrangeSpacing,
      sizeScale: appSettings.arrangeSize,
    });
    const changedIds = [];
    for (const plan of plans) {
      const child = plan.node;
      child.userSized = true;
      this.setNodeLayout(child.id, plan.worldLayout, `${reason}-world`);
      this.setNestedLayout(child.id, parent.id, plan.nestedLayout, `${reason}-nested`);
      changedIds.push(child.id);
    }
    logEvent("debug", reason, {
      parentId: parent.id,
      childCount: children.length,
      changedCount: changedIds.length,
    });
    return changedIds;
  },
  arrangeRootChildren(reason = "arrange-root-children") {
    const roots = rootNodes();
    if (!roots.length) {
      logEvent("debug", "arrange-root-children-empty");
      return [];
    }
    const plans = powanPlacement.planRootChildren(roots, {
      spacing: appSettings.arrangeSpacing,
      sizeScale: appSettings.arrangeSize,
    });
    const changedIds = [];
    for (const plan of plans) {
      const child = plan.node;
      child.userSized = true;
      this.setNodeLayout(child.id, plan.worldLayout, `${reason}-world`);
      changedIds.push(child.id);
    }
    logEvent("debug", reason, {
      childCount: roots.length,
      changedCount: changedIds.length,
    });
    return changedIds;
  },
  arrangeSubtree(nodeIdOrIds, reason = "arrange-subtree") {
    const requestedIds = Array.isArray(nodeIdOrIds) ? nodeIdOrIds : [nodeIdOrIds];
    const ids = uniqueActiveNodeIds(requestedIds);
    const rootIds = ids.filter((id) => !ids.some((otherId) => otherId !== id && isDescendant(id, otherId)));
    const roots = rootIds.map(nodeById).filter(Boolean);
    if (!roots.length) {
      logEvent("warn", "arrange-subtree-missing-node", { nodeIds: requestedIds });
      return false;
    }
    if (!roots.some((root) => this.childrenOf(root).length)) {
      logEvent("debug", "arrange-subtree-empty", { nodeIds: rootIds });
      return false;
    }
    this.recordHistory(reason);
    const parents = [];
    const changedIds = [];
    const visit = (parent) => {
      const children = this.childrenOf(parent);
      if (!children.length) {
        return;
      }
      parents.push(parent.id);
      changedIds.push(...this.arrangeParentChildren(parent, reason));
      for (const child of children) {
        visit(child);
      }
    };
    for (const root of roots) {
      visit(root);
    }
    this.touchPowans([...rootIds, ...changedIds], `${reason}-touch`);
    setDirty();
    render();
    logEvent("info", reason, {
      nodeId: rootIds.length === 1 ? rootIds[0] : null,
      nodeIds: rootIds,
      parentCount: parents.length,
      arrangedCount: changedIds.length,
    });
    return true;
  },
  arrangeCurrentWorld(reason = "arrange-current-world") {
    const parent = currentWorldParent();
    if (parent) {
      return this.arrangeSubtree(parent.id, reason);
    }
    const roots = rootNodes();
    if (!roots.length) {
      logEvent("debug", "arrange-current-world-empty");
      return false;
    }
    this.recordHistory(reason);
    const changedIds = [];
    const parents = [];
    changedIds.push(...this.arrangeRootChildren(reason));
    const visit = (parentNode) => {
      const children = this.childrenOf(parentNode);
      if (!children.length) {
        return;
      }
      parents.push(parentNode.id);
      changedIds.push(...this.arrangeParentChildren(parentNode, reason));
      for (const child of children) {
        visit(child);
      }
    };
    for (const root of roots) {
      visit(root);
    }
    this.touchPowans(changedIds, `${reason}-touch`);
    setDirty();
    render();
    logEvent("info", reason, {
      worldParentId: null,
      rootCount: roots.length,
      parentCount: parents.length,
      arrangedCount: changedIds.length,
    });
    return true;
  },
  syncChildCoordinatesFromWorld(childId, parentId, worldPatch, reason = "sync-child-from-world") {
    const child = this.setNodeLayout(childId, worldPatch, `${reason}-world`);
    const parent = nodeById(parentId);
    if (!child || !parent || child.parent !== parent.id) {
      return child;
    }
    const movesPosition = Object.prototype.hasOwnProperty.call(worldPatch || {}, "x")
      || Object.prototype.hasOwnProperty.call(worldPatch || {}, "y");
    if (!movesPosition && powanPlacement.hasNestedLayout(child, parent.id)) {
      logEvent("trace", `${reason}-nested-preserved`, { nodeId: child.id, parentId: parent.id });
      return child;
    }
    const nestedLayout = powanPlacement.nestedLayoutFromWorld(parent, child);
    this.setNestedLayout(child.id, parent.id, nestedLayout, `${reason}-nested`);
    return child;
  },
  syncChildCoordinatesFromNested(childId, parentId, nestedPatch, reason = "sync-child-from-nested") {
    const child = nodeById(childId);
    const parent = nodeById(parentId);
    if (!child || !parent) {
      logEvent("warn", "sync-child-from-nested-missing-node", { childId, parentId, reason });
      return null;
    }
    const previous = child.nestedLayoutByParent?.[parent.id] || {};
    const nestedLayout = {
      ...previous,
      ...nestedPatch,
    };
    this.setNestedLayout(child.id, parent.id, nestedLayout, `${reason}-nested`);
    this.setNodeLayout(child.id, powanPlacement.worldLayoutFromNested(parent, child, nestedLayout), `${reason}-world`);
    return child;
  },
  focusViewportOnNode(nodeId, reason = "focus-node") {
    const node = nodeById(nodeId);
    if (!node) {
      logEvent("warn", "focus-node-missing-node", { nodeId, reason });
      return false;
    }
    focusViewportOnRect(powanPlacement.displayRectForNode(node), 96);
    logEvent("debug", reason, { nodeId });
    return true;
  },
  resizeSelectedByWheel(factor) {
    const ids = selectedNodeIds();
    if (!ids.length) {
      logEvent("debug", "resize-selected-missing-node", { selectedId, selectedIds: ids });
      return false;
    }
    this.touchPowans(ids, "resize-selected-touch");
    this.recordHistory(ids.length > 1 ? "resize-selected-nodes" : "resize-selected", {
      groupKey: `resize:${ids.join("|")}`,
    });
    let resizedCount = 0;
    const missingIds = [];
    for (const nodeId of ids) {
      const node = nodeById(nodeId);
      const element = node ? visualElementById(node.id) : null;
      if (!node || !element) {
        missingIds.push(nodeId);
        continue;
      }
      const resized = (element.classList.contains("nested-meaning") || element.classList.contains("nested-preview-meaning")) && node.parent
        ? this.resizeNestedMeaningByFactor(node, element, factor, { renderAfter: false })
        : this.resizeMeaningByFactor(node, element, factor, { renderAfter: false });
      if (resized) {
        resizedCount += 1;
      }
    }
    if (resizedCount > 0) {
      setDirty();
      render();
    }
    logEvent(resizedCount > 0 ? "debug" : "warn", "resize-selected-complete", {
      selectedIds: ids,
      resizedCount,
      missingIds,
      factor,
    });
    return resizedCount > 0;
  },
  spreadSelectedFromOriginByWheel(factor) {
    const ids = selectedNodeIds();
    if (!ids.length) {
      logEvent("debug", "spread-selected-missing-node", { selectedId, selectedIds: ids });
      return false;
    }
    const origin = powanWorkspace.origin;
    this.touchPowans(ids, "spread-selected-touch");
    this.recordHistory(ids.length > 1 ? "spread-selected-nodes" : "spread-selected", {
      groupKey: `spread:${ids.join("|")}`,
    });
    let movedCount = 0;
    const missingIds = [];
    for (const nodeId of ids) {
      const node = nodeById(nodeId);
      if (!node) {
        missingIds.push(nodeId);
        continue;
      }
      const layout = powanPlacement.nodeLayout(node);
      const center = powanPlacement.rectCenter(layout);
      const nextCenterX = origin.x + (center.x - origin.x) * factor;
      const nextCenterY = origin.y + (center.y - origin.y) * factor;
      const nextLayout = {
        x: Math.round(nextCenterX - layout.width / 2),
        y: Math.round(nextCenterY - layout.height / 2),
        width: Math.round(layout.width),
        height: Math.round(layout.height),
      };
      this.syncChildCoordinatesFromWorld(
        node.id,
        node.parent || null,
        nextLayout,
        "spread-selected-from-origin",
      );
      movedCount += 1;
    }
    if (movedCount > 0) {
      setDirty();
      render();
    }
    logEvent(movedCount > 0 ? "debug" : "warn", "spread-selected-complete", {
      selectedIds: ids,
      movedCount,
      missingIds,
      factor,
      origin: {
        x: origin.x,
        y: origin.y,
      },
    });
    return movedCount > 0;
  },
  resizeMeaningByFactor(node, element, factor, { renderAfter = true } = {}) {
    const layout = node.layout || {};
    const width = Number(layout.width || 260);
    const height = Number(layout.height || 150);
    const nextWidth = Math.max(NODE_LIMITS.minWidth, Math.min(NODE_LIMITS.maxWidth, width * factor));
    const nextHeight = Math.max(NODE_LIMITS.minHeight, Math.min(NODE_LIMITS.maxHeight, height * factor));
    const visualRect = element?.getBoundingClientRect?.();
    const visualCenter = visualRect?.width && visualRect?.height
      ? screenToWorld(visualRect.left + visualRect.width / 2, visualRect.top + visualRect.height / 2)
      : null;
    const origin = currentWorldOrigin();
    const centerX = visualCenter ? origin.x + visualCenter.x : Number(layout.x || 0) + width / 2;
    const centerY = visualCenter ? origin.y + visualCenter.y : Number(layout.y || 0) + height / 2;
    const previousLayout = {
      ...(node.layout || {}),
      x: Number(layout.x || 0),
      y: Number(layout.y || 0),
      width,
      height,
    };
    const nextLayout = {
      x: Math.round(centerX - nextWidth / 2),
      y: Math.round(centerY - nextHeight / 2),
      width: Math.round(nextWidth),
      height: Math.round(nextHeight),
    };
    node.userSized = true;
    this.syncChildCoordinatesFromWorld(
      node.id,
      node.parent || null,
      nextLayout,
      "resize-focused-node",
    );
    this.preserveChildrenInsideResizedParent(node, previousLayout, nextLayout, "resize-focused-node-children");
    if (renderAfter) {
      setDirty();
      render();
    }
    return true;
  },
  resizeNestedMeaningByFactor(node, element, factor, { renderAfter = true } = {}) {
    const parent = nodeById(node.parent);
    if (!parent) {
      return false;
    }
    const parentLayout = parent.layout || {};
    const current = node.nestedLayoutByParent?.[parent.id] || {};
    const width = Number(current.width || element.offsetWidth || 54);
    const height = Number(current.height || element.offsetHeight || 38);
    const maxWidth = Math.max(NESTED_NODE_LIMITS.minWidth, Math.min(NESTED_NODE_LIMITS.maxWidth, Number(parentLayout.width || 260) - 28));
    const maxHeight = Math.max(NESTED_NODE_LIMITS.minHeight, Math.min(NESTED_NODE_LIMITS.maxHeight, Number(parentLayout.height || 150) - 28));
    const nextWidth = Math.max(NESTED_NODE_LIMITS.minWidth, Math.min(maxWidth, width * factor));
    const nextHeight = Math.max(NESTED_NODE_LIMITS.minHeight, Math.min(maxHeight, height * factor));
    const previousHostLayout = { width, height };
    const nextHostLayout = { width: Math.round(nextWidth), height: Math.round(nextHeight) };
    const x = Number.isFinite(Number(current.x)) ? Number(current.x) : Number.parseFloat(element.style.left || "0");
    const y = Number.isFinite(Number(current.y)) ? Number(current.y) : Number.parseFloat(element.style.top || "0");
    const elementRect = element?.getBoundingClientRect?.();
    const layer = element?.closest?.(".nested-preview-layer") || element?.closest?.(".nested-layer");
    const layerRect = layer?.getBoundingClientRect?.();
    const scaleX = layerRect?.width ? layerRect.width / Math.max(1, layer.offsetWidth || layerRect.width) : 1;
    const scaleY = layerRect?.height ? layerRect.height / Math.max(1, layer.offsetHeight || layerRect.height) : 1;
    const centerX = elementRect?.width && layerRect?.width
      ? (elementRect.left + elementRect.width / 2 - layerRect.left) / Math.max(0.01, scaleX)
      : x + width / 2;
    const centerY = elementRect?.height && layerRect?.height
      ? (elementRect.top + elementRect.height / 2 - layerRect.top) / Math.max(0.01, scaleY)
      : y + height / 2;
    const maxX = Math.max(0, Number(parentLayout.width || 260) - 28 - nextWidth);
    const maxY = Math.max(0, Number(parentLayout.height || 150) - 28 - nextHeight);
    this.syncChildCoordinatesFromNested(
      node.id,
      parent.id,
      {
        x: Math.round(Math.min(maxX, Math.max(0, centerX - nextWidth / 2))),
        y: Math.round(Math.min(maxY, Math.max(0, centerY - nextHeight / 2))),
        width: Math.round(nextWidth),
        height: Math.round(nextHeight),
      },
      "resize-focused-nested-node",
    );
    this.preserveChildrenInsideResizedParent(node, previousHostLayout, nextHostLayout, "resize-focused-nested-node-children");
    if (renderAfter) {
      setDirty();
      render();
    }
    return true;
  },
  nestedLocalAreaForLayout(layout) {
    const width = Number(layout?.width || NODE_LIMITS.minWidth);
    const height = Number(layout?.height || NODE_LIMITS.minHeight);
    const inset = powanPlacement.nestedLayerInset;
    return {
      x: 0,
      y: 0,
      width: Math.max(1, width - inset * 2),
      height: Math.max(1, height - inset * 2),
    };
  },
  nestedSizeWithinArea(layout, area, fallback = {}) {
    const maxWidth = Math.max(NESTED_NODE_LIMITS.minWidth, Math.min(NESTED_NODE_LIMITS.maxWidth, area.width));
    const maxHeight = Math.max(NESTED_NODE_LIMITS.minHeight, Math.min(NESTED_NODE_LIMITS.maxHeight, area.height));
    return {
      width: Math.max(NESTED_NODE_LIMITS.minWidth, Math.min(maxWidth, Number(layout?.width || fallback.width || NESTED_NODE_LIMITS.minWidth))),
      height: Math.max(NESTED_NODE_LIMITS.minHeight, Math.min(maxHeight, Number(layout?.height || fallback.height || NESTED_NODE_LIMITS.minHeight))),
    };
  },
  preserveChildrenInsideResizedParent(parent, previousLayout, nextLayout, reason = "preserve-children-inside-resized-parent") {
    const children = this.childrenOf(parent);
    if (!children.length) {
      return;
    }
    const previousArea = this.nestedLocalAreaForLayout(previousLayout);
    const nextArea = this.nestedLocalAreaForLayout(nextLayout);
    const previousParent = { ...parent, layout: previousLayout };
    for (const child of children) {
      const fallback = powanPlacement.nestedLayoutFromWorld(previousParent, child);
      const current = child.nestedLayoutByParent?.[parent.id] || fallback;
      const size = this.nestedSizeWithinArea(current, nextArea, fallback);
      const previousSize = this.nestedSizeWithinArea(current, previousArea, fallback);
      const currentX = Number.isFinite(Number(current.x)) ? Number(current.x) : Number(fallback.x || 0);
      const currentY = Number.isFinite(Number(current.y)) ? Number(current.y) : Number(fallback.y || 0);
      const centerX = currentX + previousSize.width / 2;
      const centerY = currentY + previousSize.height / 2;
      const anchor = {
        x: powanPlacement.clamp((centerX - previousArea.x) / Math.max(1, previousArea.width), 0, 1),
        y: powanPlacement.clamp((centerY - previousArea.y) / Math.max(1, previousArea.height), 0, 1),
      };
      const nextNested = powanPlacement.rectAtAnchor(nextArea, size, anchor);
      this.syncChildCoordinatesFromNested(child.id, parent.id, nextNested, reason);
      logEvent("trace", "resize-parent-child-position-preserved", {
        parentId: parent.id,
        childId: child.id,
        anchor,
        previous: current,
        next: nextNested,
      });
    }
    logEvent("debug", reason, { parentId: parent.id, childCount: children.length });
  },
  setHoldingCount(node) {
    if (!node) {
      return 0;
    }
    node.holdingCount = this.childrenOf(node).length;
    return node.holdingCount;
  },
  childrenOf(parent) {
    if (!parent) {
      return [];
    }
    const childIds = new Set(Array.isArray(parent.children) ? parent.children : []);
    for (const node of doc.nodes) {
      if (!isArchivedNode(node) && node.parent === parent.id) {
        childIds.add(node.id);
      }
    }
    const children = [...childIds].map(nodeById).filter(Boolean);
    parent.children = children.map((node) => node.id);
    return children;
  },
  attach(childId, parentId, { animation = "enter", placement = "current", fromRect = null, recordHistory = true } = {}) {
    if (recordHistory) {
      this.recordHistory("attach-powan");
    }
    this.touchPowans([childId, parentId], "attach-touch");
    return powanStateTransition.run({
      type: "attach",
      explorer: this,
      childId,
      parentId,
      animation,
      placement,
      fromRect,
    });
  },
  nestedLayoutFromScreenRect(parent, child, screenRect) {
    const parentElement = visualElementById(parent.id);
    const layer = parentElement?.querySelector(".nested-layer, .nested-preview-layer");
    const layerRect = rectSnapshot(layer?.getBoundingClientRect());
    const current = child.nestedLayoutByParent?.[parent.id] || {};
    const width = Math.round(Number(current.width || Math.max(NESTED_NODE_LIMITS.minWidth, Math.min(NESTED_NODE_LIMITS.maxWidth, screenRect.width / Math.max(0.01, viewport.scale)))));
    const height = Math.round(Number(current.height || Math.max(NESTED_NODE_LIMITS.minHeight, Math.min(NESTED_NODE_LIMITS.maxHeight, screenRect.height / Math.max(0.01, viewport.scale)))));
    if (!layerRect || !layerRect.width || !layerRect.height) {
      return powanPlacement.nestedLayoutFromWorld(parent, child, { width, height });
    }
    const scaleX = layerRect.width / Math.max(1, layer.offsetWidth || layerRect.width);
    const scaleY = layerRect.height / Math.max(1, layer.offsetHeight || layerRect.height);
    const centerX = screenRect.left + screenRect.width / 2;
    const centerY = screenRect.top + screenRect.height / 2;
    const x = (centerX - layerRect.left) / Math.max(0.01, scaleX) - width / 2;
    const y = (centerY - layerRect.top) / Math.max(0.01, scaleY) - height / 2;
    const maxX = Math.max(0, (layer.offsetWidth || layerRect.width) - width);
    const maxY = Math.max(0, (layer.offsetHeight || layerRect.height) - height);
    const layout = {
      x: Math.round(Math.min(maxX, Math.max(0, x))),
      y: Math.round(Math.min(maxY, Math.max(0, y))),
      width,
      height,
    };
    logEvent("trace", "nested-layout-from-screen-rect", {
      parentId: parent.id,
      childId: child.id,
      screenRect: {
        left: Math.round(screenRect.left),
        top: Math.round(screenRect.top),
        width: Math.round(screenRect.width),
        height: Math.round(screenRect.height),
      },
      layerRect: {
        left: Math.round(layerRect.left),
        top: Math.round(layerRect.top),
        width: Math.round(layerRect.width),
        height: Math.round(layerRect.height),
      },
      layout,
    });
    return layout;
  },
  detach(childId, { animation = "release", fromRect = null, recordHistory = true } = {}) {
    const child = nodeById(childId);
    if (recordHistory) {
      this.recordHistory("detach-powan");
    }
    this.touchPowans([childId, child?.parent || null], "detach-touch");
    return powanStateTransition.run({
      type: "detach",
      explorer: this,
      childId,
      animation,
      fromRect,
    });
  },
  deleteSelected() {
    const ids = selectedNodeIds();
    const nodesToDelete = ids.map((id) => nodeById(id)).filter(Boolean);
    const activeCount = activeNodes().length;
    if (!nodesToDelete.length || activeCount <= nodesToDelete.length) {
      logEvent("warn", "delete-node-rejected", {
        nodeIds: ids,
        nodeCount: activeCount,
      });
      return;
    }
    this.recordHistory(nodesToDelete.length > 1 ? "delete-nodes" : "delete-node");
    const deleteIds = new Set(nodesToDelete.map((node) => node.id));
    const touchedIds = new Set();
    for (const node of nodesToDelete) {
      if (node.parent) {
        touchedIds.add(node.parent);
      }
      const childIds = this.childrenOf(node).map((child) => child.id);
      for (const childId of childIds) {
        if (deleteIds.has(childId)) {
          continue;
        }
        const child = nodeById(childId);
        if (child) {
          child.parent = null;
          touchedIds.add(child.id);
        }
      }
    }
    for (const node of activeNodes()) {
      if (deleteIds.has(node.id)) {
        continue;
      }
      const before = node.children || [];
      const after = before.filter((childId) => !deleteIds.has(childId));
      if (after.length !== before.length) {
        node.children = after;
        this.setHoldingCount(node);
        touchedIds.add(node.id);
      }
    }
    this.touchPowans([...touchedIds], "delete-node-touch");
    doc.nodes = doc.nodes.filter((item) => !deleteIds.has(item.id));
    this.setSelected(firstActiveNode()?.id || null, "delete-node-select-next");
    setDirty();
    render();
    logEvent("debug", "delete-node", {
      nodeIds: [...deleteIds],
      releasedIds: [...touchedIds].filter((id) => !deleteIds.has(id)),
    });
  },
  beginPowanDragMotion(element, offsetX, offsetY) {
    logEvent("trace", "powan-drag-motion-begin-request", {
      nodeId: element?.dataset?.id || null,
      offsetX: Math.round(offsetX),
      offsetY: Math.round(offsetY),
      className: String(element?.className || ""),
    });
    powanDragDeform.begin(element, offsetX, offsetY, this.dragDeformRuleFor(element));
  },
  movePowanDragMotion(pointerX, pointerY) {
    const rect = powanDragDeform.moveToPointer(pointerX, pointerY);
    logEvent("trace", "powan-drag-motion-pointer", {
      pointerX: Math.round(pointerX),
      pointerY: Math.round(pointerY),
      rect: rect && {
        x: Math.round(rect.x),
        y: Math.round(rect.y),
        width: Math.round(rect.width),
        height: Math.round(rect.height),
      },
      snapshot: powanDragDeform.snapshot(),
    });
    return rect;
  },
  currentPowanDragMotionRect() {
    return powanDragDeform.currentLocalRect();
  },
  releasePowanDragMotion() {
    logEvent("trace", "powan-drag-motion-release-request", {
      snapshot: powanDragDeform.snapshot(),
    });
    powanDragDeform.release();
  },
  isPowanElement(element) {
    return Boolean(element?.matches?.(".node, .nested-meaning, .nested-preview-meaning"));
  },
  powanChildLayer(element) {
    if (!this.isPowanElement(element)) {
      return null;
    }
    return element.querySelector(":scope > .nested-layer, :scope > .nested-preview-layer");
  },
  powanChildrenInElement(element, layer = this.powanChildLayer(element)) {
    if (!layer) {
      return [];
    }
    return [...layer.children].filter((child) => this.isPowanElement(child));
  },
  powanDeformProfile(element) {
    const isPowan = this.isPowanElement(element);
    const contentLayer = isPowan ? this.powanChildLayer(element) : null;
    const childEls = isPowan ? this.powanChildrenInElement(element, contentLayer) : [];
    return {
      isPowan,
      contentLayer,
      childEls,
      hasChildren: childEls.length > 0,
    };
  },
  dragDeformRuleFor(element) {
    const profile = this.powanDeformProfile(element);
    return {
      contentLayer: profile.contentLayer,
      childEls: profile.childEls,
      contentFollowsVisualCenter: profile.isPowan,
      childrenDeformAtWall: profile.hasChildren,
    };
  },
  beginNestedDrag({ nodeId, parentId, element, layer, offsetX, offsetY, pointerId, startX = 0, startY = 0, frame = null }) {
    this.recordHistory("nested-drag-start", { groupKey: `drag:${nodeId}` });
    this.touchPowans([nodeId, parentId], "nested-drag-start-touch");
    nestedDrag = powanNestedDrag.begin({ nodeId, parentId, element, layer, offsetX, offsetY, pointerId, startX, startY, frame });
    this.beginPowanDragMotion(element, offsetX, offsetY);
    logEvent("debug", "nested-drag-start", { nodeId, parentId });
    logEvent("trace", "nested-drag-start-trace", {
      nodeId,
      parentId,
      pointerId,
      startX: Math.round(startX),
      startY: Math.round(startY),
      offsetX: Math.round(offsetX),
      offsetY: Math.round(offsetY),
      frame,
    });
  },
  moveNestedDrag(clientX, clientY) {
    if (!nestedDrag) {
      return null;
    }
    const node = nodeById(nestedDrag.id);
    const parent = nodeById(nestedDrag.parentId);
    if (!node || !parent) {
      logEvent("warn", "nested-drag-missing-node", { nodeId: nestedDrag.id, parentId: nestedDrag.parentId });
      nestedDrag = null;
      return null;
    }
    const pointer = powanNestedDrag.localPointerFromScreen(nestedDrag, clientX, clientY);
    const pointerLocalRect = powanNestedDrag.localRectFromPointer(nestedDrag, clientX, clientY);
    const deformRect = this.movePowanDragMotion(pointer.x, pointer.y);
    const localRect = deformRect || powanNestedDrag.moveToRect(nestedDrag, pointerLocalRect);
    nestedDrag.moved = true;
    nestedDrag.lastLocalRect = localRect;
    nestedDrag.lastPointerLocalRect = pointerLocalRect;
    const storedLayout = powanNestedDrag.storedLayout(parent, node, nestedDrag, localRect);
    logEvent("trace", "nested-drag-move", {
      nodeId: node.id,
      parentId: parent.id,
      clientX: Math.round(clientX),
      clientY: Math.round(clientY),
      pointer: {
        x: Math.round(pointer.x),
        y: Math.round(pointer.y),
      },
      localRect: {
        x: Math.round(localRect.x),
        y: Math.round(localRect.y),
        width: Math.round(localRect.width),
        height: Math.round(localRect.height),
      },
      pointerLocalRect: {
        x: Math.round(pointerLocalRect.x),
        y: Math.round(pointerLocalRect.y),
        width: Math.round(pointerLocalRect.width),
        height: Math.round(pointerLocalRect.height),
      },
      deformActive: Boolean(deformRect),
      storedLayout,
    });
    this.syncChildCoordinatesFromNested(
      node.id,
      parent.id,
      storedLayout,
      "nested-drag-layout",
    );
    updateCoordinateBadge(node);
    setDirty();
    return nestedDrag;
  },
  finishNestedDragAnimation(dragState) {
    dragState.element.classList.remove("dragging");
    this.releasePowanDragMotion();
    powanNestedDrag.cleanup(dragState);
  },
  clampNestedDragInsideParent(dragState) {
    const node = nodeById(dragState.id);
    const parent = nodeById(dragState.parentId);
    if (!node || !parent) {
      return;
    }
    const localRect = powanNestedDrag.clampInside(dragState);
    const storedLayout = powanNestedDrag.storedLayout(parent, node, dragState, localRect);
    this.syncChildCoordinatesFromNested(node.id, parent.id, storedLayout, "nested-drag-clamp-inside");
  },
  detachNestedDragToWorld(dragState) {
    const node = nodeById(dragState.id);
    if (!node) {
      return;
    }
    const parentBefore = node.parent || null;
    const rect = powanNestedDrag.screenRectForRelease(dragState);
    const actualRect = rectSnapshot(dragState.element?.getBoundingClientRect());
    const center = screenToWorld(rect.left + rect.width / 2, rect.top + rect.height / 2);
    const origin = currentWorldOrigin();
    const width = Math.max(NODE_LIMITS.minWidth, Math.round(rect.width / viewport.scale));
    const height = Math.max(NODE_LIMITS.minHeight, Math.round(rect.height / viewport.scale));
    const layout = {
      x: origin.x + center.x - width / 2,
      y: origin.y + center.y - height / 2,
      width,
      height,
    };
    logEvent("trace", "nested-drag-detach-visible-clamp-disabled", {
      nodeId: node.id,
      parentId: dragState.parentId,
      releaseRect: {
        left: Math.round(rect.left),
        top: Math.round(rect.top),
        width: Math.round(rect.width),
        height: Math.round(rect.height),
      },
      layout: {
        x: Math.round(layout.x),
        y: Math.round(layout.y),
        width: Math.round(layout.width),
        height: Math.round(layout.height),
      },
    });
    logEvent("debug", "nested-drag-detach-to-world", {
      nodeId: node.id,
      parentId: dragState.parentId,
      releaseRect: {
        left: Math.round(rect.left),
        top: Math.round(rect.top),
        width: Math.round(rect.width),
        height: Math.round(rect.height),
      },
      actualRect: actualRect
        ? {
            left: Math.round(actualRect.left),
            top: Math.round(actualRect.top),
            width: Math.round(actualRect.width),
            height: Math.round(actualRect.height),
          }
        : null,
      layout: {
        x: Math.round(layout.x),
        y: Math.round(layout.y),
        width: Math.round(layout.width),
        height: Math.round(layout.height),
      },
    });
    this.setNodeLayout(node.id, layout, "nested-drag-detach-layout");
    const targetParentId = powanNestedDrag.releaseParentId(dragState);
    logEvent("trace", "nested-drag-detach-dispatch", {
      nodeId: node.id,
      dragParentId: dragState.parentId,
      parentBefore,
      currentNodeParent: node.parent || null,
      targetParentId,
      dispatch: targetParentId && targetParentId !== node.parent ? "attach-to-release-parent" : "detach-to-root",
      releaseRect: {
        left: Math.round(rect.left),
        top: Math.round(rect.top),
        width: Math.round(rect.width),
        height: Math.round(rect.height),
      },
      layout,
    });
    if (targetParentId && targetParentId !== node.parent) {
      this.attach(node.id, targetParentId, { animation: "release", placement: "current", fromRect: rect, recordHistory: false });
    } else {
      this.detach(node.id, { animation: "release", fromRect: rect, recordHistory: false });
    }
    logEvent("trace", "nested-drag-detach-result", {
      nodeId: node.id,
      parentBefore,
      parentAfter: node.parent || null,
      dragParentId: dragState.parentId,
      targetParentId,
    });
  },
  screenPointInsidePowanElement(element, x, y) {
    if (!element) {
      return false;
    }
    const rect = element.getBoundingClientRect();
    if (!rect.width || !rect.height) {
      return false;
    }
    if (x < rect.left || x > rect.right || y < rect.top || y > rect.bottom) {
      return false;
    }
    const distance = powanHitTest.normalizedEllipseDistance({
      x: x - rect.left,
      y: y - rect.top,
      width: rect.width,
      height: rect.height,
    });
    return distance <= powanHitTest.edgeOuterRadius;
  },
  releaseAncestorParentIdForNestedDrag(dragState, releaseRect) {
    const node = nodeById(dragState.id);
    const currentParent = nodeById(dragState.parentId);
    if (!node || !currentParent || !releaseRect) {
      return null;
    }
    const releaseX = releaseRect.left + releaseRect.width / 2;
    const releaseY = releaseRect.top + releaseRect.height / 2;
    const candidateIds = [currentParent.parent || null, openParentId || null]
      .filter((id, index, ids) => id && id !== dragState.parentId && ids.indexOf(id) === index);
    for (const candidateId of candidateIds) {
      const candidate = nodeById(candidateId);
      const candidateElement = visualElementById(candidateId);
      if (!candidate || !candidateElement || isDescendant(candidateId, node.id)) {
        continue;
      }
      if (this.screenPointInsidePowanElement(candidateElement, releaseX, releaseY)) {
        logEvent("trace", "nested-drag-release-ancestor-hit", {
          nodeId: node.id,
          fromParentId: dragState.parentId,
          toParentId: candidateId,
          releaseX: Math.round(releaseX),
          releaseY: Math.round(releaseY),
        });
        return candidateId;
      }
    }
    return null;
  },
  clampReleasedLayoutToVisibleWorld(layout) {
    const canvasRect = canvas.getBoundingClientRect();
    const topLeft = screenToWorld(canvasRect.left, canvasRect.top);
    const bottomRight = screenToWorld(canvasRect.right, canvasRect.bottom);
    const origin = currentWorldOrigin();
    const margin = 28;
    const minDisplayX = Math.min(topLeft.x, bottomRight.x) + margin;
    const maxDisplayX = Math.max(topLeft.x, bottomRight.x) - layout.width - margin;
    const minDisplayY = Math.min(topLeft.y, bottomRight.y) + margin;
    const maxDisplayY = Math.max(topLeft.y, bottomRight.y) - layout.height - margin;
    const minX = origin.x + minDisplayX;
    const maxX = origin.x + maxDisplayX;
    const minY = origin.y + minDisplayY;
    const maxY = origin.y + maxDisplayY;
    const outsideVisibleArea = layout.x < minX || layout.x > maxX || layout.y < minY || layout.y > maxY;
    if (maxX >= minX && maxY >= minY && outsideVisibleArea) {
      const centerDisplayX = (Math.min(topLeft.x, bottomRight.x) + Math.max(topLeft.x, bottomRight.x)) / 2;
      const centerDisplayY = (Math.min(topLeft.y, bottomRight.y) + Math.max(topLeft.y, bottomRight.y)) / 2;
      return {
        ...layout,
        x: Math.round(origin.x + centerDisplayX - layout.width / 2),
        y: Math.round(origin.y + centerDisplayY - layout.height / 2),
        width: Math.round(layout.width),
        height: Math.round(layout.height),
      };
    }
    return {
      ...layout,
      x: Math.round(maxX >= minX ? Math.min(maxX, Math.max(minX, layout.x)) : layout.x),
      y: Math.round(maxY >= minY ? Math.min(maxY, Math.max(minY, layout.y)) : layout.y),
      width: Math.round(layout.width),
      height: Math.round(layout.height),
    };
  },
  endNestedDrag() {
    if (!nestedDrag) {
      return null;
    }
    const dragState = nestedDrag;
    nestedDrag = null;
    const releaseSnapshot = powanNestedDrag.releaseSnapshot(dragState);
    const rect = powanNestedDrag.screenRectForRelease(dragState);
    const dropTarget = findDropTarget(dragState.id, rect.left + rect.width / 2, rect.top + rect.height / 2);
    const node = nodeById(dragState.id);
    const rememberedLocalRect = powanNestedDrag.rememberedLocalRect(dragState);
    const layerRect = rectSnapshot(dragState.layer?.getBoundingClientRect());
    const releaseParentId = powanNestedDrag.releaseParentId(dragState);
    const ancestorReleaseParentId = this.releaseAncestorParentIdForNestedDrag(dragState, rect);
    const outsideParent = releaseSnapshot.outside;
    const releaseDecision = dropTarget
      ? "attach-drop-target"
      : (outsideParent
          ? (ancestorReleaseParentId ? "attach-release-ancestor" : "detach-from-parent")
          : "clamp-inside-parent");
    logEvent("trace", "nested-drag-release-decision", {
      nodeId: dragState.id,
      dragParentId: dragState.parentId,
      currentNodeParent: node?.parent || null,
      moved: dragState.moved,
      droppedOnId: dropTarget?.dataset.id || null,
      releaseParentId,
      ancestorReleaseParentId,
      outsideParent,
      outsideParentSource: releaseSnapshot.decidedBy,
      releaseRectSource: releaseSnapshot.releaseSource,
      decision: dragState.moved ? releaseDecision : "no-move",
      releaseRect: {
        left: Math.round(rect.left),
        top: Math.round(rect.top),
        width: Math.round(rect.width),
        height: Math.round(rect.height),
      },
      actualRect: rectSnapshot(dragState.element?.getBoundingClientRect()),
      rememberedLocalRect,
      lastPointerLocalRect: dragState.lastPointerLocalRect,
      releaseCandidates: releaseSnapshot.candidates,
      layerRect,
      layerSize: {
        width: dragState.layer?.clientWidth || 0,
        height: dragState.layer?.clientHeight || 0,
      },
    });
    if (dragState.moved) {
      if (dropTarget) {
        logEvent("trace", "nested-drag-release-dispatch", {
          nodeId: dragState.id,
          fromParentId: node?.parent || null,
          toParentId: dropTarget.dataset.id,
          dispatch: "attach-drop-target",
        });
        this.attach(dragState.id, dropTarget.dataset.id, { placement: "current", recordHistory: false });
      } else if (outsideParent && ancestorReleaseParentId) {
        logEvent("trace", "nested-drag-release-dispatch", {
          nodeId: dragState.id,
          fromParentId: node?.parent || null,
          toParentId: ancestorReleaseParentId,
          dispatch: "attach-release-ancestor",
        });
        this.attach(dragState.id, ancestorReleaseParentId, { placement: "screen", fromRect: rect, recordHistory: false });
      } else if (outsideParent) {
        logEvent("trace", "nested-drag-release-dispatch", {
          nodeId: dragState.id,
          fromParentId: node?.parent || null,
          toParentId: releaseParentId,
          dispatch: "detach-from-parent",
        });
        this.detachNestedDragToWorld(dragState);
      } else {
        logEvent("trace", "nested-drag-release-dispatch", {
          nodeId: dragState.id,
          fromParentId: node?.parent || null,
          toParentId: dragState.parentId,
          dispatch: "clamp-inside-parent",
        });
        this.clampNestedDragInsideParent(dragState);
      }
    }
    this.finishNestedDragAnimation(dragState);
    this.endHistoryGroup(`drag:${dragState.id}`);
    logEvent("debug", "nested-drag-end", {
      nodeId: dragState.id,
      parentId: dragState.parentId,
      moved: dragState.moved,
      droppedOnId: dropTarget?.dataset.id || null,
    });
    logEvent("trace", "nested-drag-end-trace", {
      nodeId: dragState.id,
      parentId: dragState.parentId,
      moved: dragState.moved,
      droppedOnId: dropTarget?.dataset.id || null,
      outsideParent,
      releaseParentId,
      ancestorReleaseParentId,
      parentAfter: nodeById(dragState.id)?.parent || null,
    });
    return dragState;
  },
  select(nodeId) {
    this.touchPowan(nodeId, "select-touch");
    this.setSelected(nodeId, "explorer-select");
    return selectNode(nodeId);
  },
  enterWorld(nodeId, sourceElement = null) {
    return this.moveToWorld(nodeId, { sourceElement });
  },
  leaveWorldOneStep() {
    if (!openParentId) {
      logEvent("debug", "leave-world-one-step-noop");
      return false;
    }
    const parent = currentWorldParent();
    return this.moveToWorld(parent?.parent || null);
  },
  leaveWorldRoot() {
    return this.moveToWorld(null);
  },
  async moveToWorld(targetId, { sourceElement = null } = {}) {
    this.touchPowans([openParentId, targetId], "world-navigation-touch");
    if (worldTransition) {
      logEvent("debug", "world-path-navigation-busy", { targetId });
      return worldTransition;
    }
    worldTransition = (async () => {
      const target = targetId ? nodeById(targetId) : null;
      if (targetId && !target) {
        logEvent("warn", "world-path-target-missing", { targetId });
        return false;
      }
      const startPath = openParentId ? worldPathIds(currentWorldParent()) : [];
      const targetPath = target ? worldPathIds(target) : [];
      let commonDepth = 0;
      while (startPath[commonDepth] && startPath[commonDepth] === targetPath[commonDepth]) {
        commonDepth += 1;
      }
      logEvent("debug", "world-path-navigation-start", {
        from: openParentId,
        to: targetId,
        leaveCount: startPath.length - commonDepth,
        enterCount: targetPath.length - commonDepth,
      });

      while (openParentId && worldPathIds(currentWorldParent()).length > commonDepth) {
        const parent = currentWorldParent();
        const parentId = openParentId;
        const nextParentId = parent?.parent || null;
        await powanStateTransition.run({
          type: "world-leave",
          explorer: this,
          parent,
          nextParentId,
        });
        logEvent("trace", "world-path-leave-step-complete", { parentId, nextParentId });
      }

      for (const nextId of targetPath.slice(commonDepth)) {
        const parent = nodeById(nextId);
        if (!parent) {
          logEvent("warn", "world-transition-enter-missing-parent", { targetId: nextId });
          return false;
        }
        if (openParentId === parent.id) {
          logEvent("debug", "world-transition-enter-already-open", { targetId: nextId });
          continue;
        }
        await powanStateTransition.run({
          type: "world-enter",
          explorer: this,
          parent,
          sourceElement,
        });
        logEvent("trace", "world-path-enter-step-complete", { parentId: parent.id });
        sourceElement = null;
      }
      logEvent("debug", "world-path-navigation-complete", { targetId });
      return true;
    })().finally(() => {
      worldTransition = null;
    });
    return worldTransition;
  },
  createChild() {
    const parent = nodeById(selectedId);
    this.recordHistory("create-child-node");
    if (parent) {
      this.touchPowan(parent.id, "create-child-parent-touch");
    }
    const center = parent ? null : visibleWorldCenter();
    const position = center ? powanWorkspace.topLeftForCenter(center) : {};
    const child = defaultNode({
      title: "",
      x: position.x,
      y: position.y,
    });
    doc.nodes.push(child);
    this.touchPowan(child.id, "create-child-touch");
    this.setSelected(child.id, "create-child-select");
    if (parent) {
      this.attach(child.id, parent.id, { placement: "pack", recordHistory: false });
    } else {
      setDirty();
      render();
    }
    logEvent("debug", "create-child-node", { nodeId: child.id, parentId: parent?.id || null });
  },
  createRoot() {
    this.recordHistory("create-root-node");
    const center = visibleWorldCenter();
    const position = powanWorkspace.topLeftForCenter(center);
    const child = defaultNode({
      title: "",
      x: position.x,
      y: position.y,
    });
    doc.nodes.push(child);
    this.touchPowan(child.id, "create-root-touch");
    this.setSelected(child.id, "create-root-select");
    setDirty();
    render();
    logEvent("debug", "create-root-node", { nodeId: child.id });
  },
  createAttachmentNodes(attachments, { parentId = null, dropCenter = null, reason = "create-attachment-nodes" } = {}) {
    const cleanAttachments = (attachments || []).filter(Boolean);
    if (!cleanAttachments.length) {
      logEvent("warn", "create-attachment-nodes-empty", { parentId, reason });
      return [];
    }
    const parent = parentId ? nodeById(parentId) : null;
    this.recordHistory(reason);
    const center = dropCenter || visibleWorldCenter();
    const anchors = powanPlacement.anchors(cleanAttachments.length);
    const created = cleanAttachments.map((attachment, index) => {
      const anchor = anchors[index] || { x: 0.5, y: 0.5 };
      const rootCenter = {
        x: Math.round(center.x + (anchor.x - 0.5) * 420),
        y: Math.round(center.y + (anchor.y - 0.5) * 300),
      };
      const position = parent ? {} : powanWorkspace.topLeftForCenter(rootCenter);
      const node = defaultNode({
        title: powanAttachments.titleForAttachment(attachment),
        x: position.x,
        y: position.y,
        attachment,
      });
      doc.nodes.push(node);
      this.touchPowan(node.id, `${reason}-touch`);
      return node;
    });
    if (parent) {
      for (const node of created) {
        this.attach(node.id, parent.id, { placement: "pack", recordHistory: false });
      }
      this.touchPowan(parent.id, `${reason}-parent-touch`);
    } else {
      setDirty();
      render();
    }
    this.setSelected(created[0].id, `${reason}-select`);
    logEvent("info", reason, {
      parentId: parent?.id || null,
      nodeIds: created.map((node) => node.id),
      kinds: cleanAttachments.map((attachment) => attachment.kind || "file"),
    });
    return created;
  },
  openCode(nodeId) {
    return openCodeEditor(nodeId);
  },
  closeCodeEditor() {
    this.closeCode("explorer-close-code");
  },
  newDocument() {
    return createDocument();
  },
  loadDocument(name) {
    return loadDocument(name);
  },
  loadFile() {
    return loadDocumentFromFile();
  },
  save() {
    return saveDocument();
  },
  saveAs() {
    return saveDocumentAs();
  },
};
