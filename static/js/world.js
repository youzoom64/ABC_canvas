function panelTabEntries() {
  return [
    { id: "world", button: panelWorldTab, pane: panelWorldPane },
    { id: "settings", button: panelSettingsTab, pane: panelSettingsPane },
    { id: "history", button: panelHistoryTab, pane: panelHistoryPane },
    { id: "design", button: panelDesignTab, pane: panelDesignPane },
    { id: "git-history", button: panelGitHistoryTab, pane: panelGitHistoryPane },
    { id: "code", button: panelCodeTab, pane: codePanel },
  ];
}

function normalizePanelTab(tab) {
  return ["world", "settings", "history", "design", "git-history", "code"].includes(tab) ? tab : "world";
}

function syncPanelTabs({ focus = false } = {}) {
  activePanelTab = normalizePanelTab(activePanelTab);
  const codeActive = activePanelTab === "code";
  if (panel) {
    panel.classList.remove("code-mode");
  }
  if (normalPanel) {
    normalPanel.hidden = codeActive;
  }
  for (const entry of panelTabEntries()) {
    const active = entry.id === activePanelTab;
    if (entry.button) {
      entry.button.classList.toggle("active", active);
      entry.button.setAttribute("aria-selected", active ? "true" : "false");
      entry.button.tabIndex = active ? 0 : -1;
      if (active && focus) {
        entry.button.focus();
      }
    }
    if (entry.pane) {
      entry.pane.hidden = !active;
    }
  }
}

function setPanelTab(tab, { focus = false, reason = "set-panel-tab" } = {}) {
  activePanelTab = normalizePanelTab(tab);
  if (activePanelTab === "code" && nodeById(selectedId) && codePanelNodeId !== selectedId) {
    powanExplorer.setCodeNode(selectedId, `${reason}-code-node`);
  } else if (activePanelTab === "design" && nodeById(selectedId) && designPanelNodeId !== selectedId) {
    setDesignNode(selectedId, `${reason}-design-node`);
  }
  syncPanelTabs({ focus });
  if (activePanelTab === "code") {
    syncCodePanel();
  } else if (activePanelTab === "design") {
    syncDesignPanel();
  } else if (activePanelTab === "git-history" && typeof refreshPowanGitHistory === "function") {
    refreshPowanGitHistory({ reason });
  } else if (activePanelTab === "history" && typeof refreshConversationHistory === "function") {
    refreshConversationHistory({ reason });
  }
  logEvent("debug", reason, { tab: activePanelTab });
}

function setDesignNode(nodeId, reason = "set-design-node") {
  designPanelNodeId = nodeById(nodeId) ? nodeId : null;
  logEvent("debug", reason, { nodeId: designPanelNodeId });
  syncDesignPanel();
}

function openDesignViewer(nodeId) {
  const node = nodeById(nodeId);
  if (!node) {
    logEvent("warn", "open-design-missing-node", { nodeId });
    return;
  }
  powanExplorer.touchPowan(node.id, "open-design-touch");
  powanExplorer.setSelected(node.id, "open-design-select");
  selectNode(node.id);
  setDesignNode(node.id, "open-design-set-node");
  setPanelTab("design", { reason: "open-design-tab" });
}

function syncDesignPanel() {
  if (activePanelTab === "design" && !nodeById(designPanelNodeId) && nodeById(selectedId)) {
    designPanelNodeId = selectedId;
  }
  const node = nodeById(designPanelNodeId);
  if (!designPanelNodeName || !designMarkdownView) {
    return;
  }
  if (!node) {
    designPanelNodeName.textContent = "ポワン未選択";
    designMarkdownView.textContent = "設計Markdownはまだありません。";
    if (copyDesignButton) {
      copyDesignButton.disabled = true;
    }
    return;
  }
  const design = String(node.designMarkdown || "");
  designPanelNodeName.textContent = meaningName(node);
  designMarkdownView.textContent = design.trim() ? design : "設計Markdownはまだありません。";
  if (copyDesignButton) {
    copyDesignButton.disabled = !design.trim();
  }
}

async function refreshPowanGitHistory({ reason = "git-history-refresh" } = {}) {
  if (!gitHistoryList || !projectName || !documentName || gitHistoryLoading) {
    return;
  }
  gitHistoryLoading = true;
  gitHistoryList.innerHTML = "";
  const loading = document.createElement("div");
  loading.className = "conversation-history-loading";
  loading.textContent = "Git履歴を読んでいます...";
  gitHistoryList.append(loading);
  try {
    const response = await fetch(
      `/api/powan-git-history?project=${encodeURIComponent(projectName)}&file=${encodeURIComponent(documentName)}&limit=80`,
    );
    const body = await response.json().catch(() => ({ detail: `git history failed: ${response.status}` }));
    if (!response.ok) {
      throw new Error(body.detail || `git history failed: ${response.status}`);
    }
    renderPowanGitHistory(body);
    logEvent("debug", reason, {
      count: Array.isArray(body.commits) ? body.commits.length : 0,
      historyExists: Boolean(body.historyExists),
    });
  } catch (error) {
    gitHistoryList.innerHTML = "";
    const item = document.createElement("div");
    item.className = "conversation-history-empty";
    item.textContent = `Git履歴を読めませんでした: ${error.message}`;
    gitHistoryList.append(item);
    logEvent("error", "git-history-refresh-error", { message: error.message });
  } finally {
    gitHistoryLoading = false;
  }
}

function renderPowanGitHistory(data) {
  gitHistoryList.innerHTML = "";
  const commits = Array.isArray(data?.commits) ? data.commits : [];
  if (gitHistoryMeta) {
    gitHistoryMeta.textContent = data?.snapshot || "semantic history";
  }
  if (!data?.historyExists) {
    const empty = document.createElement("div");
    empty.className = "conversation-history-empty";
    empty.textContent = ".powan_history はまだありません。保存すると作られます。";
    gitHistoryList.append(empty);
    return;
  }
  if (!commits.length) {
    const empty = document.createElement("div");
    empty.className = "conversation-history-empty";
    empty.textContent = "このpowanファイルのGit履歴はまだありません。";
    gitHistoryList.append(empty);
    return;
  }
  for (const commit of commits) {
    const item = document.createElement("article");
    item.className = "git-history-item";
    const subject = document.createElement("div");
    subject.className = "git-history-subject";
    subject.textContent = commit.subject || commit.shortSha || "commit";
    const meta = document.createElement("div");
    meta.className = "conversation-history-meta";
    meta.textContent = `${commit.shortSha || ""} / ${formatHistoryTime(commit.date)} / ${commit.author || ""}`;
    const detail = document.createElement("pre");
    detail.className = "git-history-detail";
    detail.textContent = commit.message || "";
    item.append(subject, meta, detail);
    gitHistoryList.append(item);
  }
}

function formatHistoryTime(value) {
  if (!value) {
    return "";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return String(value);
  }
  return date.toLocaleString("ja-JP", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function openCodeEditor(nodeId) {
  const node = nodeById(nodeId);
  if (!node) {
    logEvent("warn", "open-code-missing-node", { nodeId });
    return;
  }
  powanExplorer.touchPowan(node.id, "open-code-touch");
  powanExplorer.setCodeNode(node.id, "open-code-set-node");
  powanExplorer.setSelected(node.id, "open-code-select");
  selectNode(node.id);
  setPanelTab("code", { reason: "open-code-tab" });
  requestAnimationFrame(() => {
    const editor = ensureCodeEditor();
    if (editor?.then) {
      editor.then((readyEditor) => {
        if (readyEditor) {
          readyEditor.focus();
        } else {
          codeInput.focus();
        }
      });
    } else if (editor) {
      editor.focus();
    } else {
      codeInput.focus();
    }
  });
  logEvent("debug", "open-code-editor", { nodeId });
}

function closeCodeEditor() {
  powanExplorer.closeCode("close-code-editor");
}

function syncCodePanel() {
  if (activePanelTab === "code" && !nodeById(codePanelNodeId) && nodeById(selectedId)) {
    codePanelNodeId = selectedId;
  }
  const codeNode = nodeById(codePanelNodeId);
  syncPanelTabs();
  if (!codeNode) {
    codeEditorNodeName.textContent = "ポワン未選択";
    codeLanguageSelect.disabled = true;
    codeInput.disabled = true;
    if (codeInput.value !== "") {
      codeInput.value = "";
    }
    if (codeEditor) {
      setCodeEditorValue(codeEditor, "");
    }
    updateCodeLineNumbers();
    return;
  }
  codeLanguageSelect.disabled = false;
  codeInput.disabled = false;
  const editor = activePanelTab === "code" ? ensureCodeEditor() : codeEditor;
  codeEditorNodeName.textContent = meaningName(codeNode);
  codeLanguageSelect.value = codeNode.codeLanguage || "auto";
  const code = codeNode.code || "";
  if (editor) {
    Promise.resolve(editor).then((readyEditor) => {
      if (!readyEditor) {
        if (codeInput.value !== code) {
          codeInput.value = code;
        }
        return;
      }
      if (codePanelNodeId !== codeNode.id) {
        return;
      }
      setCodeEditorValue(readyEditor, code);
      setCodeEditorLanguage(readyEditor, codeNode.codeLanguage || "auto", code);
    });
  } else if (codeInput.value !== code) {
    codeInput.value = code;
  }
  updateCodeLineNumbers();
}

function ensureCodeEditor() {
  if (codeEditor) {
    return codeEditor;
  }
  if (!codeEditorHost) {
    return null;
  }
  if (codeEditorReady) {
    return codeEditorReady;
  }
  codeEditorReady = loadCodeMirror6().then((modules) => {
    codeEditorModules = modules;
    const codeNode = nodeById(codePanelNodeId);
    const initialLanguage = codeNode?.codeLanguage || "auto";
    currentCodeEditorLanguage = resolvedCodeLanguage(initialLanguage, codeInput.value || "");
    codeEditor = new modules.EditorView({
      doc: codeInput.value || "",
      parent: codeEditorHost,
      extensions: [
        modules.basicSetup,
        modules.oneDark,
        modules.EditorView.lineWrapping,
        languageExtensionForCode(initialLanguage, codeInput.value || ""),
        modules.EditorView.updateListener.of((update) => {
          if (!update.docChanged || syncingCodeEditor) {
            return;
          }
          const node = nodeById(codePanelNodeId);
          if (!node) {
            return;
          }
          powanExplorer.updateCode(node.id, update.state.doc.toString(), {
            renderAfter: true,
            reason: "codemirror6-code-change",
          });
        }),
      ],
    });
    codeInput.classList.add("code-input-hidden");
    logEvent("debug", "codemirror6-ready");
    return codeEditor;
  }).catch((error) => {
    logEvent("error", "codemirror6-load-error", { message: error.message });
    codeEditorReady = null;
    return null;
  });
  return codeEditorReady;
}

async function loadCodeMirror6() {
  const [
    codemirror,
    oneDark,
    javascript,
    python,
    html,
    css,
    json,
  ] = await Promise.all([
    import("https://esm.sh/codemirror@6.0.2"),
    import("https://esm.sh/@codemirror/theme-one-dark@6.1.3"),
    import("https://esm.sh/@codemirror/lang-javascript@6.2.4"),
    import("https://esm.sh/@codemirror/lang-python@6.2.1"),
    import("https://esm.sh/@codemirror/lang-html@6.4.9"),
    import("https://esm.sh/@codemirror/lang-css@6.3.1"),
    import("https://esm.sh/@codemirror/lang-json@6.0.2"),
  ]);
  return {
    EditorView: codemirror.EditorView,
    basicSetup: codemirror.basicSetup,
    oneDark: oneDark.oneDark,
    javascript: javascript.javascript,
    python: python.python,
    html: html.html,
    css: css.css,
    json: json.json,
  };
}

function codeEditorValue(editor) {
  return editor.state.doc.toString();
}

function setCodeEditorValue(editor, code) {
  if (codeEditorValue(editor) === code) {
    return;
  }
  syncingCodeEditor = true;
  editor.dispatch({
    changes: {
      from: 0,
      to: editor.state.doc.length,
      insert: code,
    },
  });
  syncingCodeEditor = false;
}

function inferCodeLanguage(code) {
  const trimmed = (code || "").trimStart();
  if (/^<(!doctype|html|[a-z][\w:-]*[\s>])/i.test(trimmed)) {
    return "html";
  }
  if (/^\s*[{[]/.test(trimmed)) {
    return "json";
  }
  if (/\b(from\s+\S+\s+import|def\s+\w+\(|import\s+\w+|if\s+__name__\s*==)/.test(code)) {
    return "python";
  }
  if (/\b(function|const|let|var|=>|import\s+.*from|export\s+)/.test(code)) {
    return "javascript";
  }
  if (/[.#][\w-]+\s*\{|\b[a-z-]+\s*:\s*[^;]+;/.test(code)) {
    return "css";
  }
  return "python";
}

function languageExtensionForCode(language, code) {
  if (!codeEditorModules) {
    return [];
  }
  const resolvedLanguage = resolvedCodeLanguage(language, code);
  if (resolvedLanguage === "javascript") {
    return codeEditorModules.javascript({ jsx: true, typescript: true });
  }
  if (resolvedLanguage === "html") {
    return codeEditorModules.html();
  }
  if (resolvedLanguage === "css") {
    return codeEditorModules.css();
  }
  if (resolvedLanguage === "json") {
    return codeEditorModules.json();
  }
  return codeEditorModules.python();
}

function resolvedCodeLanguage(language, code) {
  return language === "auto" ? inferCodeLanguage(code) : language;
}

function setCodeEditorLanguage(editor, language, code) {
  const nextLanguage = resolvedCodeLanguage(language, code);
  if (currentCodeEditorLanguage === nextLanguage) {
    return;
  }
  currentCodeEditorLanguage = nextLanguage;
  rebuildCodeEditor(editor, code);
}

function rebuildCodeEditor(editor, code) {
  const shouldFocus = document.activeElement && editor.dom.contains(document.activeElement);
  editor.destroy();
  codeEditor = null;
  codeEditorReady = null;
  codeEditorHost.innerHTML = "";
  codeInput.value = code;
  codeInput.classList.remove("code-input-hidden");
  const nextEditor = ensureCodeEditor();
  Promise.resolve(nextEditor).then((readyEditor) => {
    if (shouldFocus && readyEditor) {
      readyEditor.focus();
    }
  });
}

function updateCodeLineNumbers() {
  if (codeEditor) {
    return;
  }
  const lineCount = Math.max(1, codeInput.value.split("\n").length);
  codeLineNumbers.textContent = Array.from({ length: lineCount }, (_, index) => String(index + 1)).join("\n");
}

function textStats(text) {
  const value = text || "";
  const lines = value.split("\n");
  return {
    chars: value.length,
    lineBreaks: Math.max(0, lines.length - 1),
    lines,
    longestLine: lines.reduce((longest, line) => Math.max(longest, line.length), 0),
  };
}

function observeCharacterCount(node) {
  return textStats(meaningSurfaceText(node));
}

function observeLineBreaks(node) {
  return textStats(meaningSurfaceText(node)).lineBreaks;
}

function ensureMeasureBox() {
  if (measureBox) {
    return measureBox;
  }
  measureBox = document.createElement("div");
  measureBox.className = "text-measure";
  measureBox.setAttribute("aria-hidden", "true");
  document.body.appendChild(measureBox);
  return measureBox;
}

function measureTextBlock(text, className) {
  const box = ensureMeasureBox();
  box.className = `text-measure ${className}`;
  box.textContent = text || " ";
  return {
    width: Math.ceil(box.scrollWidth),
    height: Math.ceil(box.scrollHeight),
  };
}

function measureTextAndLineNeeds(node) {
  const stats = observeCharacterCount(node);
  const bodySize = measureTextBlock(meaningSurfaceText(node) || " ", "measure-body");
  return {
    stats,
    lineBreaks: observeLineBreaks(node),
    bodySize,
  };
}

function frameIsNearText(element, contentWidth, contentHeight) {
  const innerWidth = element.clientWidth - NODE_LIMITS.paddingX;
  const innerHeight = element.clientHeight - NODE_LIMITS.paddingY;
  return (
    innerWidth - contentWidth < NODE_LIMITS.edgeGuard ||
    innerHeight - contentHeight < NODE_LIMITS.edgeGuard
  );
}

function calculateFrameSize(node, element) {
  const needs = measureTextAndLineNeeds(node);
  const contentWidth = needs.bodySize.width;
  const contentHeight = needs.bodySize.height;
  const nearEdge = frameIsNearText(element, contentWidth, contentHeight);
  const pressure = nearEdge ? NODE_LIMITS.edgeGuard : Math.max(16, NODE_LIMITS.edgeGuard - needs.stats.chars * 0.02);
  const heldMinimum = minimumFrameSizeForHeldMeanings(node);
  return {
    width: Math.min(
      NODE_LIMITS.maxWidth,
      Math.max(NODE_LIMITS.minWidth, heldMinimum.width, contentWidth + NODE_LIMITS.paddingX + pressure),
    ),
    height: Math.min(
      NODE_LIMITS.maxHeight,
      Math.max(NODE_LIMITS.minHeight, heldMinimum.height, contentHeight + NODE_LIMITS.paddingY + pressure),
    ),
    needs,
  };
}

function minimumFrameSizeForHeldMeanings(node) {
  if (typeof powanExplorer === "undefined" || typeof powanPlacement === "undefined") {
    return { width: 0, height: 0 };
  }
  const childCount = powanExplorer.childrenOf(node).length;
  if (!childCount) {
    return { width: 0, height: 0 };
  }
  const columns = Math.ceil(Math.sqrt(childCount));
  const rows = Math.ceil(childCount / columns);
  const size = powanPlacement.nestedChildSize(childCount);
  const inset = powanPlacement.nestedDisplayInset || 28;
  return {
    width: inset * 2 + columns * size.width + Math.max(0, columns - 1) * 10,
    height: inset * 2 + rows * size.height + Math.max(0, rows - 1) * 8,
  };
}

function growFrame(element, width, height, { instant = false } = {}) {
  element.classList.toggle("instant-resize", instant);
  element.style.width = `${width}px`;
  element.style.height = `${height}px`;
  if (typeof powanSoftBodyView !== "undefined") {
    powanSoftBodyView.resizeElement(element, { width, height });
  }
  if (instant) {
    requestAnimationFrame(() => element.classList.remove("instant-resize"));
  }
}

function preventTextOvertake(node, element, size) {
  const body = element.querySelector(".node-body");
  if (!body) {
    return;
  }
  const availableHeight = Math.max(28, size.height - NODE_LIMITS.paddingY);
  body.style.height = "auto";
  const bodyHeight = Math.max(28, Math.min(availableHeight, body.scrollHeight || 28));
  body.style.height = `${bodyHeight}px`;
}

function fitFrameToText(node, element, { persist = true, instant = false } = {}) {
  if (node.userSized) {
    const layout = displayLayoutForNode(node);
    growFrame(element, layout.width, layout.height, { instant });
    preventTextOvertake(node, element, layout);
    return;
  }
  const size = calculateFrameSize(node, element);
  growFrame(element, size.width, size.height, { instant });
  preventTextOvertake(node, element, size);
  if (persist) {
    powanExplorer.syncChildCoordinatesFromWorld(
      node.id,
      node.parent || null,
      {
        width: Math.round(size.width),
        height: Math.round(size.height),
      },
      "fit-frame-layout",
    );
  }
}

function classifyPointerIntent(intent, event) {
  const dx = event.clientX - intent.startX;
  const dy = event.clientY - intent.startY;
  const distance = Math.hypot(dx, dy);
  return distance >= DRAG_THRESHOLD_PX ? "drag" : "click";
}

function beginPointerIntent(event, node, element) {
  if (event.button === 1) {
    event.preventDefault();
    applySelectionFromEvent(node.id, event, { scope: "canvas" });
    powanExplorer.enterWorld(node.id, element);
    return;
  }
  if (event.button !== 0) {
    return;
  }
  if (openParentId === node.id) {
    event.preventDefault();
    applySelectionFromEvent(node.id, event, { scope: "canvas" });
    logEvent("trace", "drag-intent-blocked-open-parent", {
      nodeId: node.id,
      pointerId: event.pointerId,
      clientX: Math.round(event.clientX),
      clientY: Math.round(event.clientY),
    });
    return;
  }
  event.preventDefault();
  applySelectionFromEvent(node.id, event, { scope: "canvas" });
  pointerIntent = {
    id: node.id,
    element,
    pointerId: event.pointerId,
    startX: event.clientX,
    startY: event.clientY,
    selectionApplied: true,
  };
  element.setPointerCapture(event.pointerId);
  logEvent("trace", "drag-intent-start", {
    nodeId: node.id,
    pointerId: event.pointerId,
    startX: Math.round(event.clientX),
    startY: Math.round(event.clientY),
    displayLayout: displayLayoutForNode(node),
  });
}

function leaveChildEditMode() {
  if (!childEditParentId) {
    return;
  }
  powanExplorer.setChildEditParent(null, "leave-child-edit-mode");
  render();
}

function focusNodeBody(element) {
  const body = element.querySelector(":scope > .node-body") || element.querySelector(".node-body");
  if (!body) {
    return false;
  }
  element.classList.add("meaning-editing");
  body.focus();
  const end = body.value.length;
  body.setSelectionRange(end, end);
  return true;
}

function focusPanelMeaningInput(node) {
  powanExplorer.select(node.id);
  selectNode(node.id);
  titleInput.focus();
  titleInput.select();
  logEvent("debug", "meaning-editor-open-panel", { nodeId: node.id });
}

function openMeaningEditor(nodeId) {
  const node = nodeById(nodeId);
  if (!node) {
    logEvent("warn", "meaning-editor-missing-node", { nodeId });
    return;
  }
  powanExplorer.touchPowan(node.id, "meaning-editor-touch");
  powanExplorer.select(node.id);
  selectNode(node.id);
  const element = visualElementById(node.id);
  if (!element) {
    focusPanelMeaningInput(node);
    return;
  }
  if (element.classList.contains("nested-meaning")) {
    focusPanelMeaningInput(node);
    logEvent("debug", "meaning-editor-open-nested-panel", { nodeId: node.id });
    return;
  }
  if (element.classList.contains("nested-preview-meaning")) {
    focusPanelMeaningInput(node);
    return;
  }
  if (focusNodeBody(element)) {
    logEvent("debug", "meaning-editor-open-node", { nodeId: node.id });
    return;
  }
  focusPanelMeaningInput(node);
}

function beginNestedPointer(event, node, element) {
  logNestedPointerDebug("nested-pointer-received", event, node, element);
  if (event.button !== 0) {
    logNestedPointerDebug("nested-pointer-rejected-button", event, node, element, { button: event.button });
    return;
  }
  const decision = powanHitTest.dragCueDecision(event, element);
  logNestedPointerDebug("nested-pointer-hit-test", event, node, element, decision);
  if (!decision.canDrag) {
    if (decision.insideEllipse && !decision.textTarget && !decision.nestedTarget) {
      beginPanIntent(event, {
        nodeId: node.parent || node.id,
        nestedNodeId: node.id,
        reason: decision.reason,
        distance: decision.distance,
      });
      logNestedPointerDebug("nested-pointer-pan-intent", event, node, element, decision);
      return;
    }
    applySelectionFromEvent(node.id, event, { scope: "canvas" });
    logNestedPointerDebug("nested-pointer-rejected-edge", event, node, element, decision);
    return;
  }
  event.preventDefault();
  event.stopPropagation();
  applySelectionFromEvent(node.id, event, { scope: "canvas" });
  const parentElement = element.closest(".node, .nested-meaning, .nested-preview-meaning");
  const layer = element.closest(".nested-preview-layer") || element.closest(".nested-layer");
  const parentNode = nodeById(node.parent);
  logNestedPointerDebug("nested-pointer-context", event, node, element, {
    hasParentElement: Boolean(parentElement),
    hasLayer: Boolean(layer),
    hasParentNode: Boolean(parentNode),
    parentElement: pointerDebugElement(parentElement),
    layer: pointerDebugElement(layer),
  });
  if (!parentElement || !layer || !parentNode) {
    logEvent("trace", "nested-pointer-missing-context", {
      nodeId: node.id,
      parentId: node.parent || null,
      hasParentElement: Boolean(parentElement),
      hasLayer: Boolean(layer),
      hasParentNode: Boolean(parentNode),
    });
    return;
  }
  const elementRect = element.getBoundingClientRect();
  const layerRect = layer.getBoundingClientRect();
  const layerScale = layerRect.width / Math.max(1, layer.offsetWidth);
  logEvent("trace", "nested-pointer-start", {
    nodeId: node.id,
    parentId: parentNode.id,
    pointerId: event.pointerId,
    clientX: Math.round(event.clientX),
    clientY: Math.round(event.clientY),
    layerScale: Number(layerScale.toFixed(3)),
    elementRect: {
      left: Math.round(elementRect.left),
      top: Math.round(elementRect.top),
      width: Math.round(elementRect.width),
      height: Math.round(elementRect.height),
    },
    layerRect: {
      left: Math.round(layerRect.left),
      top: Math.round(layerRect.top),
      width: Math.round(layerRect.width),
      height: Math.round(layerRect.height),
    },
  });
  powanExplorer.beginNestedDrag({
    nodeId: node.id,
    parentId: parentNode.id,
    element,
    layer,
    frame: powanPlacement.dragFrameForNestedLayer(layer, element),
    pointerId: event.pointerId,
    offsetX: (event.clientX - elementRect.left) / layerScale,
    offsetY: (event.clientY - elementRect.top) / layerScale,
    startX: event.clientX,
    startY: event.clientY,
  });
  logNestedPointerDebug("nested-pointer-begin-drag-called", event, node, element, {
    layerScale: Number(layerScale.toFixed(3)),
    offsetX: Number(((event.clientX - elementRect.left) / layerScale).toFixed(2)),
    offsetY: Number(((event.clientY - elementRect.top) / layerScale).toFixed(2)),
  });
  element.setPointerCapture(event.pointerId);
}

function startDrag(intent, event) {
  const node = nodeById(intent.id);
  const element = intent.element;
  if (!node || !element) {
    return;
  }
  powanExplorer.touchPowan(node.id, "drag-start-touch");
  const layout = displayLayoutForNode(node);
  const start = screenToWorld(intent.startX, intent.startY);
  drag = {
    id: node.id,
    offsetX: start.x - layout.x,
    offsetY: start.y - layout.y,
    element,
    lastX: event.clientX,
    lastY: event.clientY,
  };
  powanExplorer.recordHistory("drag-node-start", { groupKey: `drag:${node.id}` });
  powanExplorer.beginPowanDragMotion(element, drag.offsetX, drag.offsetY);
  logEvent("trace", "drag-node-start-trace", {
    nodeId: node.id,
    pointerId: intent.pointerId,
    start: {
      x: Math.round(start.x),
      y: Math.round(start.y),
    },
    layout,
    offsetX: Math.round(drag.offsetX),
    offsetY: Math.round(drag.offsetY),
    clientX: Math.round(event.clientX),
    clientY: Math.round(event.clientY),
  });
}

window.addEventListener("pointermove", (event) => {
  if (treeResize) {
    const nextWidth = setLayoutWidth("--tree-panel-width", treeResize.startWidth + event.clientX - treeResize.startX, 160, 520);
    saveStoredLayoutValue("treePanelWidth", nextWidth);
    return;
  }
  if (panelResize) {
    const nextWidth = setLayoutWidth("--panel-width", panelResize.startWidth + panelResize.startX - event.clientX, 260, 760);
    saveStoredLayoutValue("panelWidth", nextWidth);
    return;
  }
  if (conversationResize) {
    event.preventDefault();
    setConversationPanelHeight(
      conversationResize.startHeight + conversationResize.startY - event.clientY,
      "resize-conversation-panel",
    );
    return;
  }
  if (conversationInputResize) {
    setConversationInputHeight(
      conversationInputResize.startHeight + conversationInputResize.startY - event.clientY,
      "resize-conversation-input",
    );
    return;
  }
  if (pan) {
    event.preventDefault();
    const dx = event.clientX - pan.startX;
    const dy = event.clientY - pan.startY;
    pan.moved = pan.moved || Math.hypot(dx, dy) >= DRAG_THRESHOLD_PX;
    viewport.x = pan.viewX + dx;
    viewport.y = pan.viewY + dy;
    applyViewportTransform();
    return;
  }
  if (panIntent && Math.hypot(event.clientX - panIntent.startX, event.clientY - panIntent.startY) >= DRAG_THRESHOLD_PX) {
    startPanFromIntent(panIntent, event);
    return;
  }
  if (nestedDrag) {
    const moved = powanExplorer.moveNestedDrag(event.clientX, event.clientY);
    if (moved) {
      markDropTarget(moved.id, event.clientX, event.clientY);
    }
    return;
  }
  if (pointerIntent && classifyPointerIntent(pointerIntent, event) === "drag") {
    logEvent("trace", "drag-intent-threshold", {
      nodeId: pointerIntent.id,
      pointerId: pointerIntent.pointerId,
      dx: Math.round(event.clientX - pointerIntent.startX),
      dy: Math.round(event.clientY - pointerIntent.startY),
      distance: Number(Math.hypot(event.clientX - pointerIntent.startX, event.clientY - pointerIntent.startY).toFixed(2)),
      clientX: Math.round(event.clientX),
      clientY: Math.round(event.clientY),
    });
    startDrag(pointerIntent, event);
    pointerIntent = null;
  }
  if (!drag) {
    return;
  }
  const node = nodeById(drag.id);
  if (!node) {
    return;
  }
  const point = screenToWorld(event.clientX, event.clientY);
  const origin = currentWorldOrigin();
  const movedRect = powanExplorer.movePowanDragMotion(point.x, point.y);
  const displayX = Math.max(0, movedRect?.x ?? point.x - drag.offsetX);
  const displayY = Math.max(0, movedRect?.y ?? point.y - drag.offsetY);
  logEvent("trace", "drag-node-move", {
    nodeId: drag.id,
    clientX: Math.round(event.clientX),
    clientY: Math.round(event.clientY),
    worldPoint: {
      x: Math.round(point.x),
      y: Math.round(point.y),
    },
    origin: {
      x: Math.round(origin.x),
      y: Math.round(origin.y),
    },
    offsetX: Math.round(drag.offsetX),
    offsetY: Math.round(drag.offsetY),
    movedRect: movedRect && {
      x: Math.round(movedRect.x),
      y: Math.round(movedRect.y),
      width: Math.round(movedRect.width),
      height: Math.round(movedRect.height),
    },
    displayX: Math.round(displayX),
    displayY: Math.round(displayY),
  });
  powanExplorer.syncChildCoordinatesFromWorld(
    node.id,
    node.parent || null,
    {
      x: Math.round(origin.x + displayX),
      y: Math.round(origin.y + displayY),
    },
    "drag-node-layout",
  );
  updateCoordinateBadge(node);
  markDropTarget(drag.id, event.clientX, event.clientY);
  setDirty();
});

window.addEventListener("pointerup", (event) => {
  if (treeResize) {
    treeResize = null;
    document.body.classList.remove("resizing-tree");
    logEvent("debug", "resize-tree-panel-complete", {
      width: Number.parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--tree-panel-width")),
    });
    return;
  }
  if (panelResize) {
    panelResize = null;
    document.body.classList.remove("resizing-panel");
    logEvent("debug", "resize-panel-complete", {
      width: Number.parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--panel-width")),
    });
    return;
  }
  if (conversationResize) {
    conversationResize = null;
    document.body.classList.remove("resizing-conversation");
    logEvent("debug", "resize-conversation-panel-complete", {
      height: Number.parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--conversation-panel-height")),
    });
    return;
  }
  if (conversationInputResize) {
    conversationInputResize = null;
    document.body.classList.remove("resizing-conversation-input");
    logEvent("debug", "resize-conversation-input-complete", {
      height: currentConversationInputHeight(),
    });
    return;
  }
  if (pan) {
    const finishedPan = finishPan();
    if (!finishedPan?.moved && isCanvasSpace(event.target)) {
      clearSelection("canvas-space-click-clear-selection");
    }
    return;
  }
  if (panIntent) {
    clearPanIntent();
  }
  if (nestedDrag) {
    powanExplorer.endNestedDrag();
    clearDropTargets();
    return;
  }
  if (pointerIntent) {
    const intent = pointerIntent;
    pointerIntent = null;
    if (classifyPointerIntent(intent, event) === "click") {
      if (!intent.selectionApplied) {
        applySelectionFromEvent(intent.id, event, { scope: "canvas" });
      }
      logEvent("trace", "drag-intent-click", {
        nodeId: intent.id,
        pointerId: intent.pointerId,
        clientX: Math.round(event.clientX),
        clientY: Math.round(event.clientY),
      });
    }
    clearDropTargets();
    return;
  }
  if (!drag) {
    return;
  }
  const finalRect = powanExplorer.currentPowanDragMotionRect();
  if (finalRect) {
    const node = nodeById(drag.id);
    const origin = currentWorldOrigin();
    if (node) {
      powanExplorer.syncChildCoordinatesFromWorld(
        node.id,
        node.parent || null,
        {
          x: Math.round(origin.x + Math.max(0, finalRect.x)),
          y: Math.round(origin.y + Math.max(0, finalRect.y)),
        },
        "drag-node-final-layout",
      );
      updateCoordinateBadge(node);
    }
  }
  const target = findDropTarget(drag.id, event.clientX, event.clientY);
    if (target) {
      powanExplorer.attach(drag.id, target.dataset.id, {
        placement: "screen",
        fromRect: rectSnapshot(visualElementById(drag.id)?.getBoundingClientRect()),
        recordHistory: false,
      });
    } else if (!openParentId) {
      const draggedNode = nodeById(drag.id);
      if (draggedNode && isMeaningOutsideParent(draggedNode)) {
        powanExplorer.detach(draggedNode.id, { recordHistory: false });
      }
    }
  clearDropTargets();
  logEvent("debug", "drag-node-end", { nodeId: drag.id, droppedOnId: target?.dataset.id || null });
  logEvent("trace", "drag-node-end-trace", {
    nodeId: drag.id,
    droppedOnId: target?.dataset.id || null,
    finalRect,
    clientX: Math.round(event.clientX),
    clientY: Math.round(event.clientY),
  });
  powanExplorer.releasePowanDragMotion();
  powanExplorer.endHistoryGroup(`drag:${drag.id}`);
  drag = null;
});

window.addEventListener("pointercancel", () => {
  if (conversationInputResize) {
    conversationInputResize = null;
    document.body.classList.remove("resizing-conversation-input");
  }
  clearPanIntent();
  finishPan();
});

function findDropTarget(sourceId, x, y) {
  for (const element of document.elementsFromPoint(x, y)) {
    const target = element.closest(".nested-preview-meaning, .nested-meaning, .node");
    if (target && isDropCandidate(target, sourceId)) {
      return target;
    }
  }
  return null;
}

function isDropCandidate(element, sourceId) {
  if (element.dataset.id === sourceId || element.classList.contains("hidden-meaning")) {
    return false;
  }
  const node = nodeById(element.dataset.id);
  if (!node) {
    return false;
  }
  const source = nodeById(sourceId);
  if (source?.parent && node.id === source.parent) {
    return false;
  }
  if (isDescendant(sourceId, node.id)) {
    return false;
  }
  if (isDescendant(node.id, sourceId)) {
    return false;
  }
  if (element.classList.contains("nested-preview-meaning") || element.classList.contains("nested-meaning")) {
    return true;
  }
  if (openParentId) {
    return node.parent === openParentId;
  }
  return !node.parent || node.parent === childEditParentId;
}

function markDropTarget(sourceId, x, y) {
  clearDropTargets();
  const target = findDropTarget(sourceId, x, y);
  if (target) {
    target.classList.add("drop-target");
  }
}

function clearDropTargets() {
  document.querySelectorAll(".drop-target").forEach((element) => element.classList.remove("drop-target"));
}

function setParent(childId, parentId) {
  powanExplorer.attach(childId, parentId);
}

function isDescendant(nodeId, possibleParentId) {
  let current = nodeById(nodeId);
  while (current?.parent) {
    if (current.parent === possibleParentId) {
      return true;
    }
    current = nodeById(current.parent);
  }
  return false;
}

function updateSelected(mutator) {
  const node = nodeById(selectedId);
  if (!node) {
    return;
  }
  powanExplorer.touchPowan(node.id, "panel-update-touch");
  powanExplorer.recordHistory("panel-update", { groupKey: `panel-update:${node.id}` });
  mutator(node);
  setDirty();
  render();
}
