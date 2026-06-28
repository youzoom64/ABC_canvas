async function fetchDocument(name = documentName) {
  const response = await fetch(`/api/doc/${encodeURIComponent(name)}?project=${encodeURIComponent(projectName)}`);
  if (!response.ok) {
    throw new Error(`load failed: ${response.status}`);
  }
  return response.json();
}

function stableForSignature(value) {
  if (Array.isArray(value)) {
    return value.map(stableForSignature);
  }
  if (value && typeof value === "object") {
    return Object.fromEntries(Object.keys(value).sort().map((key) => [key, stableForSignature(value[key])]));
  }
  return value;
}

async function documentSignature(value) {
  const stableJson = JSON.stringify(stableForSignature(value));
  const bytes = new TextEncoder().encode(stableJson);
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return [...new Uint8Array(digest)].map((byte) => byte.toString(16).padStart(2, "0")).join("");
}

function parentIdsWithNewChildren(previousDoc, nextDoc) {
  const previousChildrenById = new Map();
  for (const node of previousDoc?.nodes || []) {
    previousChildrenById.set(node.id, new Set(Array.isArray(node.children) ? node.children : []));
  }
  const parentIds = [];
  for (const node of nextDoc?.nodes || []) {
    const nextChildren = Array.isArray(node.children) ? node.children : [];
    if (!nextChildren.length) {
      continue;
    }
    const previousChildren = previousChildrenById.get(node.id) || new Set();
    if (nextChildren.some((childId) => !previousChildren.has(childId))) {
      parentIds.push(node.id);
    }
  }
  return parentIds;
}

function arrangeReloadedNewChildren(parentIds, reason) {
  if (!parentIds.length) {
    return false;
  }
  const arranged = powanExplorer.arrangeSubtree(parentIds, `${reason}-arrange-new-children`);
  logEvent("info", "reload-arrange-new-children-complete", {
    message: `reload arranged: ${parentIds.length} parents`,
    parentCount: parentIds.length,
    arranged,
    reason,
  });
  return arranged;
}

function startAutoReload() {
  if (autoReloadTimer) {
    window.clearInterval(autoReloadTimer);
  }
  autoReloadTimer = window.setInterval(() => reloadCurrentDocument({ reason: "auto-reload" }), AUTO_RELOAD_INTERVAL_MS);
}

async function reloadCurrentDocument({ force = false, reason = "reload", restoreViewport = false, preserveLocalLayouts = false } = {}) {
  if (!projectName || !documentName || autoReloadInFlight) {
    return;
  }
  if (!force && (drag || nestedDrag || pointerIntent || worldTransition)) {
    logEvent("debug", "auto-reload-skip-active-interaction", { projectName, documentName });
    return;
  }
  autoReloadInFlight = true;
  try {
    const nextDoc = await fetchDocument(documentName);
    const nextSnapshot = await documentSignature(nextDoc);
    if (!force && nextSnapshot === documentSnapshot) {
      return;
    }
    const previousDoc = doc;
    const newChildParentIds = parentIdsWithNewChildren(previousDoc, nextDoc);
    const allowEditedExternalChildren = !force && saveState.textContent === "edited" && newChildParentIds.length > 0;
    if (!force && saveState.textContent === "edited" && !allowEditedExternalChildren) {
      logEvent("debug", "auto-reload-skip-edited", { projectName, documentName });
      return;
    }
    if (allowEditedExternalChildren) {
      logEvent("info", "auto-reload-accept-external-children", {
        message: `external children accepted: ${newChildParentIds.length} parents`,
        parentCount: newChildParentIds.length,
      });
    }
    documentSnapshot = nextSnapshot;
    const shouldRestoreView = Boolean(restoreViewport);
    powanExplorer.setDocument(nextDoc, {
      name: documentName,
      status: force ? "reloaded" : "auto updated",
      resetWorld: shouldRestoreView,
      preserveView: !shouldRestoreView,
      restoreViewport: shouldRestoreView,
      restoreWorld: shouldRestoreView,
      preserveLocalLayouts: preserveLocalLayouts || allowEditedExternalChildren,
      reason: `${reason}-state`,
    });
    arrangeReloadedNewChildren(newChildParentIds, reason);
    await refreshFiles();
    render();
    refreshRunningAgentRuns(`${reason}-running-runs`).catch((error) => {
      logEvent("debug", "auto-reload-running-runs-error", { reason, message: error.message });
    });
    logEvent("info", reason, { projectName, documentName, nodeCount: doc.nodes.length });
  } catch (error) {
    logEvent("warn", `${reason}-failed`, { projectName, documentName, message: error.message });
  } finally {
    autoReloadInFlight = false;
  }
}
