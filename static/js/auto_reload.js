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

function documentSignature(value) {
  return JSON.stringify(stableForSignature(value));
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
  if (!force && saveState.textContent === "edited") {
    logEvent("debug", "auto-reload-skip-edited", { projectName, documentName });
    return;
  }
  if (!force && (drag || nestedDrag || pointerIntent || worldTransition)) {
    logEvent("debug", "auto-reload-skip-active-interaction", { projectName, documentName });
    return;
  }
  autoReloadInFlight = true;
  try {
    const nextDoc = await fetchDocument(documentName);
    const nextSnapshot = documentSignature(nextDoc);
    if (!force && nextSnapshot === documentSnapshot) {
      return;
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
      preserveLocalLayouts,
      reason: `${reason}-state`,
    });
    await refreshFiles();
    render();
    logEvent("info", reason, { projectName, documentName, nodeCount: doc.nodes.length });
  } catch (error) {
    logEvent("warn", `${reason}-failed`, { projectName, documentName, message: error.message });
  } finally {
    autoReloadInFlight = false;
  }
}
