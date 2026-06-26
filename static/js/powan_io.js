function powanFileNameForNode(node) {
  const base = meaningName(node).replace(/[<>:"/\\|?*\x00-\x1f]/g, "_").trim() || "powan";
  return `${base}.powan`;
}

function descendantIdsForExport(rootId) {
  const ids = new Set();
  const visit = (nodeId) => {
    const node = nodeById(nodeId);
    if (!node || ids.has(node.id)) {
      return;
    }
    ids.add(node.id);
    for (const child of powanExplorer.childrenOf(node)) {
      visit(child.id);
    }
  };
  visit(rootId);
  return ids;
}

function exportableNodeCopy(node, ids, rootId) {
  const copy = clonePlain(node);
  copy.parent = node.id === rootId ? null : ids.has(node.parent) ? node.parent : null;
  copy.children = (node.children || []).filter((childId) => ids.has(childId));
  const nested = {};
  for (const [parentId, layout] of Object.entries(node.nestedLayoutByParent || {})) {
    if (ids.has(parentId)) {
      nested[parentId] = clonePlain(layout);
    }
  }
  if (Object.keys(nested).length) {
    copy.nestedLayoutByParent = nested;
  } else {
    delete copy.nestedLayoutByParent;
  }
  return copy;
}

function powanSubtreeDocument(rootId) {
  const root = nodeById(rootId);
  if (!root) {
    throw new Error("export target powan not found");
  }
  const ids = descendantIdsForExport(root.id);
  const nodes = doc.nodes
    .filter((node) => ids.has(node.id))
    .map((node) => exportableNodeCopy(node, ids, root.id));
  return {
    version: 1,
    canvas: {
      background: doc.canvas?.background || "#e8f8ff",
      workspace: clonePlain(doc.canvas?.workspace || powanWorkspace.documentState()),
    },
    nodes,
  };
}

function topLevelSelectionRootIds(ids) {
  const selected = new Set(uniqueActiveNodeIds(ids));
  return [...selected].filter((id) => {
    let current = nodeById(id);
    while (current?.parent) {
      if (selected.has(current.parent)) {
        return false;
      }
      current = nodeById(current.parent);
    }
    return true;
  });
}

function exportableSelectionNodeCopy(node, ids, rootIds) {
  const copy = clonePlain(node);
  copy.parent = rootIds.has(node.id) ? null : ids.has(node.parent) ? node.parent : null;
  copy.children = (node.children || []).filter((childId) => ids.has(childId));
  const nested = {};
  for (const [parentId, layout] of Object.entries(node.nestedLayoutByParent || {})) {
    if (ids.has(parentId)) {
      nested[parentId] = clonePlain(layout);
    }
  }
  if (Object.keys(nested).length) {
    copy.nestedLayoutByParent = nested;
  } else {
    delete copy.nestedLayoutByParent;
  }
  return copy;
}

function powanSelectionDocument(ids) {
  const rootIds = topLevelSelectionRootIds(ids);
  if (!rootIds.length) {
    throw new Error("copy target powan not found");
  }
  const allIds = new Set();
  for (const rootId of rootIds) {
    for (const id of descendantIdsForExport(rootId)) {
      allIds.add(id);
    }
  }
  const rootIdSet = new Set(rootIds);
  const nodes = doc.nodes
    .filter((node) => allIds.has(node.id))
    .map((node) => exportableSelectionNodeCopy(node, allIds, rootIdSet));
  return {
    version: 1,
    canvas: {
      background: doc.canvas?.background || "#e8f8ff",
      workspace: clonePlain(doc.canvas?.workspace || powanWorkspace.documentState()),
    },
    nodes,
  };
}

async function copyTextToClipboard(text) {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text);
    return true;
  }
  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.setAttribute("readonly", "");
  textarea.style.position = "fixed";
  textarea.style.left = "-9999px";
  document.body.appendChild(textarea);
  textarea.select();
  const ok = document.execCommand("copy");
  textarea.remove();
  return ok;
}

async function readTextFromClipboard() {
  if (navigator.clipboard?.readText) {
    return navigator.clipboard.readText();
  }
  throw new Error("clipboard read is not available");
}

function downloadPowanDocument(exportDoc, fileName) {
  const blob = new Blob([JSON.stringify(exportDoc, null, 2)], { type: "application/json;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = fileName;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 0);
}

function rootNodesInDocument(sourceDoc) {
  const nodes = Array.isArray(sourceDoc?.nodes) ? sourceDoc.nodes.filter((node) => !node?.archived) : [];
  const ids = new Set(nodes.map((node) => node.id).filter(Boolean));
  return nodes.filter((node) => !node.parent || !ids.has(node.parent));
}

function sourceLayoutForNode(node) {
  const layout = node?.layout || {};
  const width = Math.max(1, Number(layout.width || powanWorkspace.defaultNodeSize.width));
  const height = Math.max(1, Number(layout.height || powanWorkspace.defaultNodeSize.height));
  return {
    x: Number.isFinite(Number(layout.x)) ? Number(layout.x) : powanWorkspace.origin.x - width / 2,
    y: Number.isFinite(Number(layout.y)) ? Number(layout.y) : powanWorkspace.origin.y - height / 2,
    width,
    height,
  };
}

function remapNestedLayouts(sourceNode, idMap, importedParentId) {
  const nested = {};
  for (const [sourceParentId, layout] of Object.entries(sourceNode.nestedLayoutByParent || {})) {
    const parentId = idMap.get(sourceParentId);
    if (parentId) {
      nested[parentId] = clonePlain(layout);
    }
  }
  if (importedParentId && !sourceNode.parent) {
    nested[importedParentId] = {};
  }
  return nested;
}

function planImportedRootLayouts(parentId, rootCount, dropCenter) {
  const parent = nodeById(parentId);
  if (!parent) {
    return [];
  }
  if (dropCenter) {
    return [];
  }
  const children = [...powanExplorer.childrenOf(parent)];
  const placeholders = Array.from({ length: rootCount }, () => ({
    id: makeId(),
    parent: parent.id,
    layout: { ...powanWorkspace.defaultNodeSize },
    children: [],
  }));
  const plans = powanPlacement.planParentChildren(parent, [...children, ...placeholders]);
  return plans.slice(children.length).map((plan) => ({
    worldLayout: plan.worldLayout,
    nestedLayout: plan.nestedLayout,
  }));
}

function importedRootLayout(sourceRoot, index, firstSourceRoot, options, rootPlans) {
  const source = sourceLayoutForNode(sourceRoot);
  if (rootPlans[index]) {
    return rootPlans[index].worldLayout;
  }
  const first = sourceLayoutForNode(firstSourceRoot);
  const center = options.dropCenter || visibleWorldCenter();
  const firstTopLeft = powanWorkspace.topLeftForCenter(center, first.width, first.height);
  return powanWorkspace.clampLayout({
    ...source,
    x: firstTopLeft.x + (source.x - first.x),
    y: firstTopLeft.y + (source.y - first.y),
  });
}

function cloneImportedNodes(sourceDoc, options) {
  const sourceNodes = Array.isArray(sourceDoc?.nodes) ? sourceDoc.nodes.filter((node) => !node?.archived) : [];
  if (!sourceNodes.length) {
    throw new Error("powan file has no nodes");
  }
  const sourceById = new Map(sourceNodes.map((node) => [node.id, node]));
  const roots = rootNodesInDocument(sourceDoc);
  if (!roots.length) {
    throw new Error("powan file has no root powan");
  }
  const idMap = new Map();
  for (const sourceNode of sourceNodes) {
    idMap.set(sourceNode.id, makeId());
  }
  const rootPlan = new Map();
  const plans = planImportedRootLayouts(options.parentId, roots.length, options.dropCenter);
  roots.forEach((root, index) => {
    rootPlan.set(root.id, {
      layout: importedRootLayout(root, index, roots[0], options, plans),
      nestedLayout: plans[index]?.nestedLayout || null,
    });
  });
  const firstSource = sourceLayoutForNode(roots[0]);
  const firstImported = rootPlan.get(roots[0].id).layout;
  const delta = {
    x: firstImported.x - firstSource.x,
    y: firstImported.y - firstSource.y,
  };

  return sourceNodes.map((sourceNode) => {
    const sourceLayout = sourceLayoutForNode(sourceNode);
    const isRoot = roots.some((root) => root.id === sourceNode.id);
    const rootInfo = rootPlan.get(sourceNode.id);
    const node = {
      ...clonePlain(sourceNode),
      id: idMap.get(sourceNode.id),
      parent: sourceNode.parent && idMap.has(sourceNode.parent) ? idMap.get(sourceNode.parent) : options.parentId || null,
      children: (sourceNode.children || []).map((childId) => idMap.get(childId)).filter(Boolean),
      layout: powanWorkspace.clampLayout(rootInfo?.layout || {
        ...sourceLayout,
        x: sourceLayout.x + delta.x,
        y: sourceLayout.y + delta.y,
      }),
      nestedLayoutByParent: remapNestedLayouts(sourceNode, idMap, isRoot ? options.parentId : null),
    };
    if (isRoot && options.parentId && rootInfo?.nestedLayout) {
      node.nestedLayoutByParent[options.parentId] = rootInfo.nestedLayout;
    }
    return node;
  });
}

function normalizeImportedChildren(importedNodes) {
  const byId = new Map(importedNodes.map((node) => [node.id, node]));
  for (const node of importedNodes) {
    const children = new Set((node.children || []).filter((childId) => byId.get(childId)?.parent === node.id));
    for (const child of importedNodes) {
      if (child.parent === node.id) {
        children.add(child.id);
      }
    }
    node.children = [...children];
  }
}

function importedRootIds(importedNodes) {
  const ids = new Set(importedNodes.map((node) => node.id));
  return importedNodes.filter((node) => !node.parent || !ids.has(node.parent)).map((node) => node.id);
}

function readPowanDocumentFile(file) {
  return file.text().then((text) => {
    const parsed = JSON.parse(text);
    if (!Array.isArray(parsed.nodes)) {
      throw new Error("ABC document must contain nodes");
    }
    return parsed;
  });
}

function powanFileDropPoint(event) {
  const local = screenToWorld(event.clientX, event.clientY);
  const origin = currentWorldOrigin();
  return powanWorkspace.clampPoint({
    x: Math.round(origin.x + local.x),
    y: Math.round(origin.y + local.y),
  });
}

function dataTransferHasFile(event) {
  return [...(event.dataTransfer?.types || [])].includes("Files");
}

function dataTransferHasExternalUrl(event) {
  const types = [...(event.dataTransfer?.types || [])];
  if (types.includes("text/uri-list")) {
    return true;
  }
  return types.includes("text/plain") && typeof treeDragSourceId !== "undefined" && !treeDragSourceId;
}

function dataTransferHasAttachmentDrop(event) {
  return dataTransferHasFile(event) || dataTransferHasExternalUrl(event);
}

function isPowanFile(file) {
  return /\.powan$/i.test(file?.name || "");
}

function firstPowanFile(event) {
  return [...(event.dataTransfer?.files || [])].find((file) => isPowanFile(file));
}

function droppedAttachmentFiles(event) {
  return [...(event.dataTransfer?.files || [])].filter((file) => !isPowanFile(file));
}

function droppedUrlText(event) {
  return event.dataTransfer?.getData("text/uri-list")
    || event.dataTransfer?.getData("text/plain")
    || "";
}

async function attachmentsFromDrop(event) {
  const attachments = [];
  for (const file of droppedAttachmentFiles(event)) {
    attachments.push(await powanAttachments.fileToAttachment(file));
  }
  const urlAttachment = powanAttachments.urlToAttachment(droppedUrlText(event));
  if (urlAttachment) {
    attachments.push(urlAttachment);
  }
  return attachments;
}

Object.assign(powanExplorer, {
  async copySelectedPowans() {
    const ids = selectedNodeIds();
    if (!ids.length) {
      logEvent("warn", "powan-copy-selection-empty");
      return false;
    }
    const exportDoc = powanSelectionDocument(ids);
    const text = JSON.stringify(exportDoc, null, 2);
    await copyTextToClipboard(text);
    saveState.textContent = `copied ${exportDoc.nodes.length}`;
    logEvent("info", "powan-copy-selection", {
      selectedIds: ids,
      nodeCount: exportDoc.nodes.length,
    });
    return true;
  },

  importPowanSubtreeDocument(sourceDoc, { parentId = null, dropCenter = null, reason = "powan-import-subtree" } = {}) {
    this.recordHistory(reason);
    const imported = cloneImportedNodes(sourceDoc, { parentId, dropCenter });
    normalizeImportedChildren(imported);
    const roots = importedRootIds(imported);
    doc.nodes.push(...imported);
    if (parentId) {
      const parent = nodeById(parentId);
      if (parent) {
        parent.children = [...new Set([...(parent.children || []), ...roots])];
        this.setHoldingCount(parent);
      }
      this.touchPowan(parentId, `${reason}-parent-touch`);
    }
    this.touchPowans(roots, `${reason}-root-touch`);
    this.setSelected(roots[0] || selectedId, `${reason}-select`);
    setDirty();
    render();
    logEvent("info", reason, {
      parentId,
      nodeCount: imported.length,
      rootIds: roots,
      dropCenter,
    });
    return imported;
  },

  async pastePowansFromClipboard({ parentId = null, dropCenter = null, reason = "powan-paste-clipboard" } = {}) {
    const text = await readTextFromClipboard();
    const sourceDoc = JSON.parse(text);
    if (!Array.isArray(sourceDoc.nodes)) {
      throw new Error("clipboard does not contain powan nodes");
    }
    const imported = this.importPowanSubtreeDocument(sourceDoc, { parentId, dropCenter, reason });
    saveState.textContent = `pasted ${imported.length}`;
    logEvent("info", "powan-paste-clipboard-complete", {
      message: `clipboard pasted: ${imported.length} nodes`,
      parentId,
      nodeCount: imported.length,
    });
    return imported;
  },

  exportPowanSubtree(nodeId) {
    const node = nodeById(nodeId);
    if (!node) {
      logEvent("warn", "powan-export-missing-node", { nodeId });
      return false;
    }
    const exportDoc = powanSubtreeDocument(node.id);
    downloadPowanDocument(exportDoc, powanFileNameForNode(node));
    logEvent("info", "powan-export-subtree", { nodeId: node.id, nodeCount: exportDoc.nodes.length });
    return true;
  },

  async importPowanSubtreeFile(file, { parentId = null, dropCenter = null, reason = "powan-import-subtree" } = {}) {
    const sourceDoc = await readPowanDocumentFile(file);
    const imported = this.importPowanSubtreeDocument(sourceDoc, { parentId, dropCenter, reason });
    logEvent("info", reason, {
      fileName: file.name,
      parentId,
      nodeCount: imported.length,
      rootIds: importedRootIds(imported),
      dropCenter,
    });
    return imported;
  },

  choosePowanImportTarget(nodeId) {
    const node = nodeById(nodeId);
    if (!node || !subtreeImportInput) {
      logEvent("warn", "powan-import-target-missing", { nodeId });
      return false;
    }
    subtreeImportTargetNodeId = node.id;
    subtreeImportInput.value = "";
    subtreeImportInput.click();
    logEvent("debug", "powan-import-file-picker-open", { nodeId: node.id });
    return true;
  },
});
