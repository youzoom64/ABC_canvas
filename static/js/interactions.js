function renderTreePanel() {
  treeList.innerHTML = "";
  rootWorldButton.classList.toggle("current-world", !openParentId);
  const roots = rootNodes();
  if (!roots.length) {
    const empty = document.createElement("div");
    empty.className = "tree-empty";
    empty.textContent = "まだ意味がありません";
    treeList.appendChild(empty);
    return;
  }
  for (const root of roots) {
    appendTreeItem(root, 0);
  }
}

function appendTreeItem(node, depth) {
  const children = meaningChildren(node);
  const isCollapsed = collapsedTreeNodeIds.has(node.id);
  const item = document.createElement("div");
  item.className = "tree-item";
  item.classList.toggle("selected", isNodeSelected(node.id));
  item.classList.toggle("current-world", node.id === openParentId);
  item.classList.toggle("collapsed", isCollapsed);
  item.classList.toggle("has-code", Boolean((node.code || "").trim()));
  item.style.setProperty("--depth", String(depth));
  item.dataset.id = node.id;
  item.draggable = true;
  item.addEventListener("contextmenu", (event) => openPowanContextMenu(event, node));
  item.addEventListener("dragstart", (event) => {
    powanExplorer.touchPowan(node.id, "tree-drag-start-touch");
    treeDragSourceId = node.id;
    event.dataTransfer.effectAllowed = "move";
    event.dataTransfer.setData("text/plain", node.id);
    item.classList.add("tree-dragging");
  });
  item.addEventListener("dragend", () => {
    treeDragSourceId = null;
    item.classList.remove("tree-dragging");
    clearTreeDropTargets();
  });
  item.addEventListener("dragover", (event) => {
    if (dataTransferHasAttachmentDrop(event)) {
      event.preventDefault();
      event.dataTransfer.dropEffect = "copy";
      item.classList.add("tree-drop-target");
      return;
    }
    const sourceId = treeDragSourceId;
    if (!isTreeDropAllowed(sourceId, node.id)) {
      return;
    }
    event.preventDefault();
    item.classList.add("tree-drop-target");
  });
  item.addEventListener("dragleave", () => {
    item.classList.remove("tree-drop-target");
  });
  item.addEventListener("drop", (event) => {
    event.preventDefault();
    const file = firstPowanFile(event);
    if (file) {
      treeDragSourceId = null;
      clearTreeDropTargets();
      powanExplorer.importPowanSubtreeFile(file, {
        parentId: node.id,
        reason: "tree-import-powan-file",
      }).catch((error) => {
        saveState.textContent = "import error";
        logEvent("error", "tree-import-powan-file-error", { nodeId: node.id, message: error.message });
        console.error(error);
      });
      return;
    }
    if (dataTransferHasAttachmentDrop(event)) {
      treeDragSourceId = null;
      clearTreeDropTargets();
      importAttachmentsFromDrop(event, {
        parentId: node.id,
        reason: "tree-import-attachment",
      });
      return;
    }
    const sourceId = treeDragSourceId || event.dataTransfer.getData("text/plain");
    treeDragSourceId = null;
    clearTreeDropTargets();
    moveTreeNodeInto(sourceId, node.id);
  });

  const toggle = document.createElement("button");
  toggle.type = "button";
  toggle.className = "tree-toggle";
  toggle.disabled = !children.length;
  toggle.textContent = children.length ? (isCollapsed ? ">" : "v") : "";
  toggle.addEventListener("click", (event) => {
    event.stopPropagation();
    powanExplorer.touchPowan(node.id, "tree-toggle-touch");
    if (isCollapsed) {
      collapsedTreeNodeIds.delete(node.id);
      logEvent("debug", "tree-expand", { nodeId: node.id });
    } else {
      collapsedTreeNodeIds.add(node.id);
      logEvent("debug", "tree-collapse", { nodeId: node.id });
    }
    renderTreePanel();
  });

  const label = treeNameEditNodeId === node.id ? renderTreeNameInput(node) : renderTreeNameButton(node);

  item.append(toggle, label);
  treeList.appendChild(item);
  if (isCollapsed) {
    return;
  }
  for (const child of children) {
    appendTreeItem(child, depth + 1);
  }
}

function renderTreeNameButton(node) {
  const label = document.createElement("button");
  label.type = "button";
  label.className = "tree-label";
  label.textContent = meaningName(node);
  label.addEventListener("click", (event) => handleTreeSelectionClick(event, node));
  label.addEventListener("dblclick", () => {
    powanExplorer.touchPowan(node.id, "tree-label-dblclick-touch");
    powanExplorer.closeCodeEditor();
    powanExplorer.enterWorld(node.id);
  });
  return label;
}

function handleTreeSelectionClick(event, node) {
  event.preventDefault();
  event.stopPropagation();
  powanExplorer.touchPowan(node.id, "tree-label-click-touch");
  applySelectionFromEvent(node.id, event, { scope: "tree" });
  refreshSelectionVisuals();
}

function renderTreeNameInput(node) {
  const input = document.createElement("input");
  input.className = "tree-name-input";
  input.value = meaningSurfaceText(node);
  input.placeholder = "名前のないポワン";
  input.draggable = false;
  input.addEventListener("click", (event) => {
    event.stopPropagation();
    powanExplorer.touchPowan(node.id, "tree-name-input-click-touch");
  });
  input.addEventListener("dblclick", (event) => event.stopPropagation());
  input.addEventListener("dragstart", (event) => event.preventDefault());
  input.addEventListener("input", () => {
    powanExplorer.touchPowan(node.id, "tree-name-input-touch");
    powanExplorer.updateMeaning(node.id, { title: input.value }, {
      refreshTree: false,
      reason: "tree-name-input",
    });
    titleInput.value = input.value;
  });
  input.addEventListener("keydown", (event) => {
    event.stopPropagation();
    if (event.key === "Enter") {
      event.preventDefault();
      finishTreeNameEdit();
    }
    if (event.key === "Escape") {
      event.preventDefault();
      finishTreeNameEdit();
    }
  });
  input.addEventListener("blur", () => finishTreeNameEdit());
  return input;
}

function beginTreeNameEdit(nodeId) {
  treeNameEditNodeId = nodeId;
  powanExplorer.touchPowan(nodeId, "tree-name-edit-touch");
  logEvent("debug", "tree-name-edit-start", { nodeId });
  renderTreePanel();
  window.requestAnimationFrame(() => {
    const input = treeList.querySelector(`.tree-item[data-id="${CSS.escape(nodeId)}"] .tree-name-input`);
    if (!input) {
      return;
    }
    input.focus();
    input.select();
  });
}

function finishTreeNameEdit() {
  if (!treeNameEditNodeId) {
    return;
  }
  const nodeId = treeNameEditNodeId;
  treeNameEditNodeId = null;
  powanExplorer.endHistoryGroup();
  logEvent("debug", "tree-name-edit-finish", { nodeId });
  renderTreePanel();
}

function isTreeDropAllowed(sourceId, targetId) {
  return Boolean(sourceId && targetId && sourceId !== targetId && nodeById(sourceId) && nodeById(targetId) && !isDescendant(targetId, sourceId));
}

function clearTreeDropTargets() {
  document.querySelectorAll(".tree-drop-target").forEach((element) => element.classList.remove("tree-drop-target"));
}

function moveTreeNodeInto(sourceId, targetId) {
  if (!isTreeDropAllowed(sourceId, targetId)) {
    logEvent("warn", "tree-drop-rejected", { sourceId, targetId });
    return;
  }
  logEvent("debug", "tree-drop-into", { sourceId, targetId });
  powanExplorer.attach(sourceId, targetId, { placement: "pack" });
}

function moveTreeNodeToRoot(sourceId) {
  const node = nodeById(sourceId);
  if (!node || !node.parent) {
    logEvent("debug", "tree-drop-root-noop", { sourceId });
    return;
  }
  logEvent("debug", "tree-drop-root", { sourceId, oldParentId: node.parent });
  powanExplorer.detach(sourceId);
}

function importAttachmentsFromDrop(event, { parentId = null, dropCenter = null, reason = "attachment-drop" } = {}) {
  attachmentsFromDrop(event).then((attachments) => {
    if (!attachments.length) {
      logEvent("warn", `${reason}-empty`, { parentId });
      return;
    }
    powanExplorer.createAttachmentNodes(attachments, { parentId, dropCenter, reason });
  }).catch((error) => {
    saveState.textContent = "drop error";
    logEvent("error", `${reason}-error`, { parentId, message: error.message });
    console.error(error);
  });
}

function conversationPayloadAttachment(attachment) {
  const payload = {};
  for (const key of ["kind", "source", "name", "mime", "size", "path", "relativePath", "url", "host"]) {
    const value = attachment?.[key];
    if (value !== undefined && value !== null && value !== "") {
      payload[key] = value;
    }
  }
  if (
    payload.kind === "image" &&
    payload.source === "clipboard" &&
    typeof attachment?.previewUrl === "string" &&
    attachment.previewUrl.startsWith("data:image/")
  ) {
    payload.imageDataUrl = attachment.previewUrl;
  }
  payload.pathAvailable = Boolean(payload.path);
  return payload;
}

function conversationAttachmentLine(attachment) {
  const payload = conversationPayloadAttachment(attachment);
  const label = powanAttachments.fileLabel(payload.kind);
  const name = payload.name || payload.host || payload.url || label;
  if (payload.path) {
    return `${label}: ${name}\n  path: ${payload.path}`;
  }
  if (payload.url) {
    return `${label}: ${name}\n  url: ${payload.url}`;
  }
  return `${label}: ${name}\n  path: （ブラウザから取得できない）`;
}

function conversationDisplayText(text, attachments) {
  const parts = [];
  if (text.trim()) {
    parts.push(text.trim());
  }
  if (attachments.length) {
    parts.push(`添付:\n${attachments.map(conversationAttachmentLine).map((line) => `- ${line}`).join("\n")}`);
  }
  return parts.join("\n\n") || "添付を渡す";
}

function createConversationAttachmentChip(attachment, { removable = false, onRemove = null } = {}) {
  const payload = conversationPayloadAttachment(attachment);
  const chip = document.createElement("div");
  chip.className = "conversation-attachment-chip";
  chip.classList.toggle("conversation-attachment-path-missing", payload.source === "file" && !payload.path);
  chip.classList.toggle("has-preview", Boolean(attachment?.previewUrl));
  chip.title = payload.path || payload.url || payload.name || "";
  if (attachment?.previewUrl) {
    const preview = document.createElement("img");
    preview.className = "conversation-attachment-preview";
    preview.alt = payload.name || "添付画像";
    preview.src = attachment.previewUrl;
    chip.append(preview);
  } else {
    const kind = document.createElement("span");
    kind.className = "conversation-attachment-kind";
    kind.textContent = powanAttachments.fileLabel(payload.kind);
    chip.append(kind);
  }
  const name = document.createElement("span");
  name.className = "conversation-attachment-name";
  name.textContent = payload.path || payload.url || payload.name || "添付";
  chip.append(name);
  if (removable) {
    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "conversation-attachment-remove";
    remove.textContent = "x";
    remove.setAttribute("aria-label", "添付を外す");
    remove.addEventListener("click", () => onRemove?.());
    chip.append(remove);
  }
  return chip;
}

function appendConversationAttachmentViews(message, attachments) {
  if (!attachments?.length) {
    return;
  }
  const list = document.createElement("div");
  list.className = "conversation-message-attachments";
  for (const attachment of attachments) {
    list.append(createConversationAttachmentChip(attachment));
  }
  message.appendChild(list);
}

function renderConversationAttachmentTray() {
  if (!conversationAttachmentTray) {
    return;
  }
  conversationAttachmentTray.innerHTML = "";
  conversationAttachmentTray.hidden = conversationPendingAttachments.length === 0;
  for (const [index, attachment] of conversationPendingAttachments.entries()) {
    const chip = createConversationAttachmentChip(attachment, {
      removable: true,
      onRemove: () => {
      conversationPendingAttachments.splice(index, 1);
      renderConversationAttachmentTray();
      logEvent("debug", "conversation-attachment-remove", { index });
      },
    });
    conversationAttachmentTray.appendChild(chip);
  }
}

function addConversationAttachments(attachments, reason = "conversation-attachment-add") {
  const clean = (attachments || []).filter(Boolean);
  if (!clean.length) {
    logEvent("warn", `${reason}-empty`, {});
    return;
  }
  conversationPendingAttachments.push(...clean);
  renderConversationAttachmentTray();
  logEvent("info", reason, {
    count: clean.length,
    pathCount: clean.filter((attachment) => Boolean(attachment.path)).length,
    kinds: clean.map((attachment) => attachment.kind || "file"),
  });
}

function addConversationAttachmentsFromDrop(event, reason = "conversation-attachment-drop") {
  attachmentsFromDrop(event).then((attachments) => {
    addConversationAttachments(attachments, reason);
  }).catch((error) => {
    saveState.textContent = "drop error";
    logEvent("error", `${reason}-error`, { message: error.message });
    console.error(error);
  });
}

function clipboardImageFiles(event) {
  return [...(event.clipboardData?.items || [])]
    .filter((item) => String(item.type || "").startsWith("image/"))
    .map((item) => item.getAsFile())
    .filter(Boolean);
}

function addConversationAttachmentsFromPaste(event) {
  const files = clipboardImageFiles(event);
  if (!files.length) {
    return false;
  }
  event.preventDefault();
  Promise.all(files.map((file) => powanAttachments.clipboardFileToAttachment(file))).then((attachments) => {
    addConversationAttachments(attachments, "conversation-clipboard-image");
  }).catch((error) => {
    saveState.textContent = "paste error";
    logEvent("error", "conversation-clipboard-image-error", { message: error.message });
    console.error(error);
  });
  return true;
}

function showNodeContextMenu(clientX, clientY) {
  const margin = 8;
  nodeContextMenu.hidden = false;
  const rect = nodeContextMenu.getBoundingClientRect();
  const left = Math.min(window.innerWidth - rect.width - margin, Math.max(margin, clientX));
  const top = Math.min(window.innerHeight - rect.height - margin, Math.max(margin, clientY));
  nodeContextMenu.style.left = `${left}px`;
  nodeContextMenu.style.top = `${top}px`;
}

function hideNodeContextMenu() {
  nodeContextMenu.hidden = true;
}

function showWorldContextMenu(clientX, clientY) {
  if (!worldContextMenu) {
    return;
  }
  const margin = 8;
  worldContextMenu.hidden = false;
  worldContextMenuOpen = true;
  const rect = worldContextMenu.getBoundingClientRect();
  const left = Math.min(window.innerWidth - rect.width - margin, Math.max(margin, clientX));
  const top = Math.min(window.innerHeight - rect.height - margin, Math.max(margin, clientY));
  worldContextMenu.style.left = `${left}px`;
  worldContextMenu.style.top = `${top}px`;
}

function hideWorldContextMenu() {
  if (!worldContextMenu) {
    return;
  }
  worldContextMenu.hidden = true;
  worldContextMenuOpen = false;
}

var conversationLoadSerial = 0;

function conversationRoleClass(role) {
  if (role === "assistant") {
    return "ai";
  }
  if (role === "user") {
    return "user";
  }
  return "system";
}

function formatConversationText(role, text = "") {
  if (role !== "assistant" && role !== "ai") {
    return text;
  }
  return text.replace(/。(?!\r?\n)/g, "。\n");
}

function normalizeConversationId(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function conversationTabIndex(nodeId) {
  return conversationTabs.findIndex((tab) => tab.nodeId === nodeId);
}

function conversationTabState(nodeId) {
  const current = conversationTabStates.get(nodeId) || {};
  conversationTabStates.set(nodeId, current);
  return current;
}

function cloneConversationAttachments(attachments) {
  return Array.isArray(attachments)
    ? attachments.map((attachment) => ({ ...attachment }))
    : [];
}

function rememberConversationTabState(nodeId = conversationNodeId) {
  if (!nodeId) {
    return;
  }
  const state = conversationTabState(nodeId);
  state.draft = conversationInput?.value || "";
  state.attachments = cloneConversationAttachments(conversationPendingAttachments);
  state.scrollTop = conversationLog ? conversationLog.scrollTop : 0;
  state.activeSessionId = normalizeConversationId(conversationActiveSessionId);
  state.viewingSessionId = normalizeConversationId(conversationViewingSessionId);
  state.viewingAllSessions = Boolean(conversationViewingAllSessions);
  state.autoFollow = Boolean(conversationAutoFollow);
}

function ensureConversationTab(nodeId) {
  const node = nodeById(nodeId);
  if (!node) {
    return null;
  }
  let tab = conversationTabs.find((item) => item.nodeId === node.id);
  if (!tab) {
    tab = {
      nodeId: node.id,
      openedAt: Date.now(),
    };
    conversationTabs.push(tab);
    logEvent("debug", "conversation-tab-created", { nodeId: node.id, name: meaningName(node) });
  }
  return tab;
}

function renderConversationTabs() {
  if (!conversationTabBar) {
    return;
  }
  conversationTabs = conversationTabs.filter((tab) => nodeById(tab.nodeId));
  for (const nodeId of [...conversationTabStates.keys()]) {
    if (!nodeById(nodeId)) {
      conversationTabStates.delete(nodeId);
    }
  }
  conversationTabBar.innerHTML = "";
  conversationTabBar.hidden = conversationTabs.length === 0;
  for (const tab of conversationTabs) {
    const node = nodeById(tab.nodeId);
    if (!node) {
      continue;
    }
    const item = document.createElement("div");
    item.className = "conversation-tab";
    item.classList.toggle("active", tab.nodeId === conversationNodeId);
    item.role = "tab";
    item.ariaSelected = tab.nodeId === conversationNodeId ? "true" : "false";
    item.title = meaningName(node);
    const label = document.createElement("button");
    label.type = "button";
    label.className = "conversation-tab-label";
    label.textContent = meaningName(node);
    label.addEventListener("click", () => switchConversationTab(tab.nodeId));
    const close = document.createElement("button");
    close.type = "button";
    close.className = "conversation-tab-close";
    close.textContent = "×";
    close.title = "タブを閉じる";
    close.addEventListener("click", (event) => {
      event.stopPropagation();
      closeConversationTab(tab.nodeId);
    });
    item.append(label, close);
    conversationTabBar.appendChild(item);
  }
}

function clearConversationView() {
  conversationNodeId = null;
  conversationActiveSessionId = null;
  conversationViewingSessionId = null;
  conversationViewingAllSessions = false;
  conversationSessionList = [];
  conversationPendingAttachments = [];
  conversationLog.innerHTML = "";
  conversationInput.value = "";
  renderConversationAttachmentTray();
  updateConversationSessionMode();
  renderConversationTabs();
}

function restoreConversationDraftState(nodeId) {
  const state = conversationTabStates.get(nodeId) || {};
  conversationInput.value = state.draft || "";
  conversationPendingAttachments = cloneConversationAttachments(state.attachments);
  renderConversationAttachmentTray();
  return state;
}

async function restoreConversationScroll(nodeId, state) {
  if (!state || !conversationLog || conversationNodeId !== nodeId) {
    return;
  }
  await Promise.resolve();
  if (conversationNodeId === nodeId && Number.isFinite(Number(state.scrollTop))) {
    conversationLog.scrollTop = Number(state.scrollTop);
    conversationAutoFollow = Boolean(state.autoFollow);
  }
}

function switchConversationTab(nodeId, reason = "conversation-tab-switch") {
  const node = nodeById(nodeId);
  if (!node) {
    closeConversationTab(nodeId, "conversation-tab-missing-close");
    return;
  }
  if (conversationNodeId === node.id && conversationPanel && !conversationPanel.hidden) {
    expandConversationPanel(reason);
    renderConversationTabs();
    return;
  }
  openConversationPanel(node.id, { fromTab: true, reason });
}

function closeConversationTab(nodeId, reason = "conversation-tab-close") {
  const index = conversationTabIndex(nodeId);
  if (index < 0) {
    return;
  }
  const wasActive = conversationNodeId === nodeId;
  if (wasActive) {
    rememberConversationTabState(nodeId);
  }
  conversationTabs.splice(index, 1);
  conversationTabStates.delete(nodeId);
  logEvent("debug", reason, { nodeId, wasActive, remaining: conversationTabs.length });
  if (wasActive) {
    const next = conversationTabs[Math.min(index, conversationTabs.length - 1)];
    conversationNodeId = null;
    if (next) {
      switchConversationTab(next.nodeId, "conversation-tab-close-switch-next");
    } else {
      clearConversationView();
      conversationPanel.hidden = true;
    }
  } else {
    renderConversationTabs();
  }
}

function conversationCanEditSession() {
  if (conversationViewingAllSessions) {
    return false;
  }
  const activeId = normalizeConversationId(conversationActiveSessionId);
  const viewingId = normalizeConversationId(conversationViewingSessionId);
  return !activeId || !viewingId || activeId === viewingId;
}

function conversationSessionLabel(session) {
  const id = normalizeConversationId(session.id);
  const title = String(session.title || "").trim();
  const base = session.active ? "現在" : "履歴";
  const count = Number.isFinite(Number(session.messageCount)) ? Number(session.messageCount) : 0;
  const name = title || `セッション${id || ""}`;
  return `${base} #${id || "-"} ${name} (${count})`;
}

function renderConversationSessions(sessions = [], selectedId = null) {
  if (!conversationSessionSelect) {
    return;
  }
  conversationSessionSelect.innerHTML = "";
  const selected = selectedId === CONVERSATION_ALL_SESSIONS_VALUE
    ? CONVERSATION_ALL_SESSIONS_VALUE
    : normalizeConversationId(selectedId)
      || normalizeConversationId(conversationViewingSessionId)
      || normalizeConversationId(conversationActiveSessionId);
  if (sessions.length > 1) {
    const allOption = document.createElement("option");
    allOption.value = CONVERSATION_ALL_SESSIONS_VALUE;
    allOption.textContent = `All (${sessions.length})`;
    conversationSessionSelect.appendChild(allOption);
  }
  for (const session of sessions) {
    const option = document.createElement("option");
    option.value = String(session.id);
    option.textContent = conversationSessionLabel(session);
    conversationSessionSelect.appendChild(option);
  }
  if (selected != null) {
    conversationSessionSelect.value = String(selected);
  }
}

function updateConversationSessionMode() {
  const canEdit = conversationCanEditSession();
  if (conversationInput) {
    conversationInput.placeholder = canEdit
      ? "ポワンに話しかける"
      : conversationViewingAllSessions
        ? "全会話を表示中"
        : "過去会話を表示中";
  }
  setConversationSending(conversationSending);
}

async function refreshConversationSessions(nodeId, selectedId = null) {
  try {
    const data = await requestConversationSessions(nodeId);
    if (conversationNodeId !== nodeId) {
      return;
    }
    conversationSessionList = data.sessions || [];
    conversationActiveSessionId = normalizeConversationId(data.activeConversationId);
    renderConversationSessions(conversationSessionList, selectedId);
    renderConversationTabs();
    updateConversationSessionMode();
    logEvent("debug", "conversation-sessions-load-complete", {
      nodeId,
      activeConversationId: conversationActiveSessionId,
      selectedConversationId: normalizeConversationId(selectedId),
      count: (data.sessions || []).length,
    });
  } catch (error) {
    logEvent("error", "conversation-sessions-load-error", { nodeId, message: error.message });
  }
}

async function loadConversationMessages(nodeId) {
  const serial = ++conversationLoadSerial;
  try {
    const response = await fetch(
      `/api/conversations/${encodeURIComponent(nodeId)}?project=${encodeURIComponent(projectName)}&file=${encodeURIComponent(documentName)}`,
    );
    if (!response.ok) {
      throw new Error(`conversation load failed: ${response.status}`);
    }
    const data = await response.json();
    if (conversationNodeId !== nodeId || serial !== conversationLoadSerial) {
      return;
    }
    conversationActiveSessionId = normalizeConversationId(data.conversationId);
    conversationViewingSessionId = normalizeConversationId(data.conversationId);
    conversationViewingAllSessions = false;
    conversationLog.innerHTML = "";
    for (const message of data.messages || []) {
      appendConversationMessage(message.role, message.text || "");
    }
    renderConversationTabs();
    refreshConversationSessions(nodeId, data.conversationId);
    logEvent("debug", "conversation-load-complete", {
      nodeId,
      conversationId: data.conversationId,
      messageCount: (data.messages || []).length,
    });
  } catch (error) {
    logEvent("error", "conversation-load-error", { nodeId, message: error.message });
  }
}

async function loadConversationSession(nodeId, conversationId) {
  const serial = ++conversationLoadSerial;
  try {
    const data = await requestConversationSessionMessages(nodeId, conversationId);
    if (conversationNodeId !== nodeId || serial !== conversationLoadSerial) {
      return;
    }
    conversationViewingSessionId = normalizeConversationId(data.conversationId);
    conversationViewingAllSessions = false;
    if (data.conversation?.active) {
      conversationActiveSessionId = conversationViewingSessionId;
    }
    conversationLog.innerHTML = "";
    for (const message of data.messages || []) {
      appendConversationMessage(message.role, message.text || "");
    }
    if (conversationSessionSelect) {
      conversationSessionSelect.value = String(data.conversationId);
    }
    refreshConversationSessions(nodeId, data.conversationId);
    renderConversationTabs();
    updateConversationSessionMode();
    logEvent("debug", "conversation-session-load-complete", {
      nodeId,
      conversationId: data.conversationId,
      active: Boolean(data.conversation?.active),
      messageCount: (data.messages || []).length,
    });
  } catch (error) {
    appendConversationMessage("system", `会話履歴を開けなかった: ${error.message}`, { forceFollow: true });
    logEvent("error", "conversation-session-load-error", { nodeId, conversationId, message: error.message });
  }
}

async function loadAllConversationSessions(nodeId) {
  const serial = ++conversationLoadSerial;
  try {
    const data = await requestConversationSessions(nodeId);
    if (conversationNodeId !== nodeId || serial !== conversationLoadSerial) {
      return;
    }
    conversationSessionList = data.sessions || [];
    conversationActiveSessionId = normalizeConversationId(data.activeConversationId);
    conversationViewingSessionId = null;
    conversationViewingAllSessions = true;
    renderConversationSessions(conversationSessionList, CONVERSATION_ALL_SESSIONS_VALUE);
    renderConversationTabs();
    conversationLog.innerHTML = "";
    conversationAutoFollow = false;
    const orderedSessions = [...conversationSessionList].sort((left, right) => normalizeConversationId(left.id) - normalizeConversationId(right.id));
    for (const session of orderedSessions) {
      if (conversationNodeId !== nodeId || serial !== conversationLoadSerial) {
        return;
      }
      appendConversationMessage("system", conversationSessionLabel(session));
      const payload = await requestConversationSessionMessages(nodeId, session.id);
      if (conversationNodeId !== nodeId || serial !== conversationLoadSerial) {
        return;
      }
      for (const message of payload.messages || []) {
        appendConversationMessage(message.role, message.text || "");
      }
    }
    updateConversationSessionMode();
    conversationLog.scrollTop = 0;
    logEvent("debug", "conversation-all-sessions-load-complete", {
      nodeId,
      activeConversationId: conversationActiveSessionId,
      count: orderedSessions.length,
    });
  } catch (error) {
    appendConversationMessage("system", `全会話を開けなかった: ${error.message}`, { forceFollow: true });
    logEvent("error", "conversation-all-sessions-load-error", { nodeId, message: error.message });
  }
}

async function requestPowanCodexReply(nodeId, text, { signal = null, includeMeaningTree = false, attachments = [] } = {}) {
  const response = await fetch(
    `/api/conversations/${encodeURIComponent(nodeId)}/codex?project=${encodeURIComponent(projectName)}&file=${encodeURIComponent(documentName)}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, includeMeaningTree, attachments }),
      signal,
    },
  );
  if (!response.ok) {
    let detail = `codex failed: ${response.status}`;
    const contentType = response.headers.get("content-type") || "";
    if (contentType.includes("application/json")) {
      const body = await response.json();
      detail = body.detail || detail;
    } else {
      const body = await response.text();
      detail = body ? `${detail}: ${body.slice(0, 500)}` : detail;
    }
    throw new Error(detail);
  }
  const data = await response.json();
  logEvent("debug", "conversation-codex-reply-received", {
    nodeId,
    includeMeaningTree,
    attachmentCount: attachments.length,
    conversationId: data.conversationId,
    threadId: data.codexThreadId,
    length: (data.assistantMessage?.text || "").length,
  });
  return data;
}

async function requestCancelPowanCodex(nodeId) {
  const response = await fetch(
    `/api/conversations/${encodeURIComponent(nodeId)}/codex/cancel?project=${encodeURIComponent(projectName)}&file=${encodeURIComponent(documentName)}`,
    { method: "POST" },
  );
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: `cancel failed: ${response.status}` }));
    throw new Error(body.detail || `cancel failed: ${response.status}`);
  }
  return response.json();
}

async function requestNewConversationSession(nodeId) {
  const response = await fetch(
    `/api/conversations/${encodeURIComponent(nodeId)}/sessions?project=${encodeURIComponent(projectName)}&file=${encodeURIComponent(documentName)}`,
    { method: "POST" },
  );
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: `new session failed: ${response.status}` }));
    throw new Error(body.detail || `new session failed: ${response.status}`);
  }
  return response.json();
}

async function requestConversationSessions(nodeId) {
  const response = await fetch(
    `/api/conversations/${encodeURIComponent(nodeId)}/sessions?project=${encodeURIComponent(projectName)}&file=${encodeURIComponent(documentName)}`,
  );
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: `sessions failed: ${response.status}` }));
    throw new Error(body.detail || `sessions failed: ${response.status}`);
  }
  return response.json();
}

async function requestConversationSessionMessages(nodeId, conversationId) {
  const response = await fetch(
    `/api/conversations/${encodeURIComponent(nodeId)}/sessions/${encodeURIComponent(conversationId)}?project=${encodeURIComponent(projectName)}&file=${encodeURIComponent(documentName)}`,
  );
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: `session load failed: ${response.status}` }));
    throw new Error(body.detail || `session load failed: ${response.status}`);
  }
  return response.json();
}

async function requestConversationSummary(nodeId) {
  const response = await fetch(
    `/api/conversations/${encodeURIComponent(nodeId)}/summarize?project=${encodeURIComponent(projectName)}&file=${encodeURIComponent(documentName)}`,
    { method: "POST" },
  );
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: `summary failed: ${response.status}` }));
    throw new Error(body.detail || `summary failed: ${response.status}`);
  }
  return response.json();
}

async function saveConversationAutoSummarySetting() {
  const enabled = conversationAutoSummaryInput ? conversationAutoSummaryInput.checked : appSettings.autoSummaryEnabled;
  const turns = conversationAutoSummaryTurnsInput ? conversationAutoSummaryTurnsInput.value : appSettings.autoSummaryTurns;
  setConversationAutoSummary(enabled, turns, "set-conversation-auto-summary-local");
  const response = await fetch("/api/settings/conversation-auto-summary", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      enabled: appSettings.autoSummaryEnabled,
      turns: appSettings.autoSummaryTurns,
    }),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "auto summary save failed" }));
    throw new Error(error.detail || "auto summary save failed");
  }
  const data = await response.json();
  appSettings.autoSummaryEnabled = data.autoSummaryEnabled !== false;
  appSettings.autoSummaryTurns = normalizeConversationAutoSummaryTurns(data.autoSummaryTurns);
  appSettings.arrangeSpacing = normalizeArrangeSpacing(data.arrangeSpacing);
  appSettings.arrangeSize = normalizeArrangeSize(data.arrangeSize);
  syncSettingsInputs();
  saveStoredSettings();
  logEvent("info", "set-conversation-auto-summary-saved", {
    enabled: appSettings.autoSummaryEnabled,
    turns: appSettings.autoSummaryTurns,
  });
}

async function refreshConversationSounds() {
  if (!conversationSoundSelect && !inputSoundSelect) {
    return;
  }
  try {
    const response = await fetch("/api/settings");
    if (!response.ok) {
      throw new Error(`settings load failed: ${response.status}`);
    }
    const data = await response.json();
    availableConversationSounds = data.sounds || [];
    appSettings.conversationSound = data.conversationSound || "";
    appSettings.conversationSoundVolume = normalizeConversationSoundVolume(data.conversationSoundVolume);
    appSettings.inputSound = data.inputSound || "";
    appSettings.inputSoundVolume = normalizeConversationSoundVolume(data.inputSoundVolume);
    appSettings.autoSummaryEnabled = data.autoSummaryEnabled !== false;
    appSettings.autoSummaryTurns = normalizeConversationAutoSummaryTurns(data.autoSummaryTurns);
    appSettings.arrangeSpacing = normalizeArrangeSpacing(data.arrangeSpacing);
    appSettings.arrangeSize = normalizeArrangeSize(data.arrangeSize);
    stopConversationChunkSound("conversation-settings-refreshed");
    stopInputWaitingSound("input-settings-refreshed");
    conversationChunkAudio = null;
    inputWaitingAudio = null;
    fillSoundSelect(conversationSoundSelect, availableConversationSounds);
    fillSoundSelect(inputSoundSelect, availableConversationSounds);
    syncSettingsInputs();
    saveStoredSettings();
    logEvent("debug", "conversation-settings-loaded", {
      count: availableConversationSounds.length,
      sound: appSettings.conversationSound,
      volume: appSettings.conversationSoundVolume,
      inputSound: appSettings.inputSound,
      inputVolume: appSettings.inputSoundVolume,
      autoSummaryEnabled: appSettings.autoSummaryEnabled,
      autoSummaryTurns: appSettings.autoSummaryTurns,
      soundRoot: data.soundRoot,
    });
  } catch (error) {
    logEvent("warn", "conversation-sounds-load-error", { message: error.message });
  }
}

function fillSoundSelect(select, sounds) {
  if (!select) {
    return;
  }
  select.innerHTML = "";
  const none = document.createElement("option");
  none.value = "";
  none.textContent = "なし";
  select.appendChild(none);
  for (const sound of sounds || []) {
    const option = document.createElement("option");
    option.value = sound.name;
    option.textContent = sound.name;
    select.appendChild(option);
  }
}

function conversationSoundUrl() {
  const sound = availableConversationSounds.find((item) => item.name === appSettings.conversationSound);
  return sound?.url || "";
}

function inputSoundUrl() {
  const sound = availableConversationSounds.find((item) => item.name === appSettings.inputSound);
  return sound?.url || "";
}

function ensureConversationChunkAudio(url) {
  if (!conversationChunkAudio || conversationChunkAudio.dataset?.url !== url) {
    stopConversationChunkSound("conversation-sound-source-changed");
    conversationChunkAudio = new Audio(url);
    conversationChunkAudio.dataset.url = url;
    conversationChunkAudio.preload = "auto";
    conversationChunkAudio.loop = true;
  }
  conversationChunkAudio.volume = appSettings.conversationSoundVolume;
  return conversationChunkAudio;
}

function ensureInputWaitingAudio(url) {
  if (!inputWaitingAudio || inputWaitingAudio.dataset?.url !== url) {
    stopInputWaitingSound("input-sound-source-changed");
    inputWaitingAudio = new Audio(url);
    inputWaitingAudio.dataset.url = url;
    inputWaitingAudio.preload = "auto";
    inputWaitingAudio.loop = true;
  }
  inputWaitingAudio.volume = appSettings.inputSoundVolume;
  return inputWaitingAudio;
}

function startConversationChunkSound() {
  const url = conversationSoundUrl();
  if (!url || appSettings.conversationSoundVolume <= 0) {
    return;
  }
  const audio = ensureConversationChunkAudio(url);
  if (conversationSoundIsPlaying) {
    return;
  }
  conversationSoundIsPlaying = true;
  audio.currentTime = 0;
  audio.play().catch((error) => {
    conversationSoundIsPlaying = false;
    logEvent("warn", "conversation-sound-play-error", { message: error.message, sound: appSettings.conversationSound });
  });
}

function startInputWaitingSound() {
  const url = inputSoundUrl();
  if (!url || appSettings.inputSoundVolume <= 0) {
    return;
  }
  const audio = ensureInputWaitingAudio(url);
  if (inputSoundIsPlaying) {
    return;
  }
  inputSoundIsPlaying = true;
  audio.currentTime = 0;
  audio.play().catch((error) => {
    inputSoundIsPlaying = false;
    logEvent("warn", "input-sound-play-error", { message: error.message, sound: appSettings.inputSound });
  });
}

function stopConversationChunkSound(reason = "conversation-sound-stop") {
  if (!conversationChunkAudio && !conversationSoundIsPlaying) {
    return;
  }
  const audio = conversationChunkAudio;
  conversationSoundIsPlaying = false;
  if (!audio) {
    return;
  }
  audio.pause();
  try {
    audio.currentTime = 0;
  } catch (error) {
    logEvent("warn", "conversation-sound-reset-error", { message: error.message, reason });
  }
}

function stopInputWaitingSound(reason = "input-sound-stop") {
  if (!inputWaitingAudio && !inputSoundIsPlaying) {
    return;
  }
  const audio = inputWaitingAudio;
  inputSoundIsPlaying = false;
  if (!audio) {
    return;
  }
  audio.pause();
  try {
    audio.currentTime = 0;
  } catch (error) {
    logEvent("warn", "input-sound-reset-error", { message: error.message, reason });
  }
}

async function saveConversationSoundSetting(name) {
  setConversationSound(name, "set-conversation-sound-local");
  const response = await fetch("/api/settings/conversation-sound", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ conversationSound: name || "" }),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "sound save failed" }));
    throw new Error(error.detail || "sound save failed");
  }
  const data = await response.json();
  availableConversationSounds = data.sounds || [];
  appSettings.conversationSound = data.conversationSound || "";
  appSettings.conversationSoundVolume = normalizeConversationSoundVolume(data.conversationSoundVolume);
  appSettings.inputSound = data.inputSound || "";
  appSettings.inputSoundVolume = normalizeConversationSoundVolume(data.inputSoundVolume);
  appSettings.autoSummaryEnabled = data.autoSummaryEnabled !== false;
  appSettings.autoSummaryTurns = normalizeConversationAutoSummaryTurns(data.autoSummaryTurns);
  appSettings.arrangeSpacing = normalizeArrangeSpacing(data.arrangeSpacing);
  appSettings.arrangeSize = normalizeArrangeSize(data.arrangeSize);
  stopConversationChunkSound("conversation-sound-saved");
  conversationChunkAudio = null;
  syncSettingsInputs();
  saveStoredSettings();
  logEvent("info", "set-conversation-sound-saved", { sound: appSettings.conversationSound });
}

async function saveConversationSoundVolumeSetting(value) {
  setConversationSoundVolume(value, "set-conversation-volume-local");
  const response = await fetch("/api/settings/conversation-sound-volume", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ conversationSoundVolume: appSettings.conversationSoundVolume }),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "volume save failed" }));
    throw new Error(error.detail || "volume save failed");
  }
  const data = await response.json();
  appSettings.conversationSoundVolume = normalizeConversationSoundVolume(data.conversationSoundVolume);
  syncSettingsInputs();
  saveStoredSettings();
  logEvent("info", "set-conversation-volume-saved", { volume: appSettings.conversationSoundVolume });
}

async function saveInputSoundSetting(name) {
  setInputSound(name, "set-input-sound-local");
  const response = await fetch("/api/settings/input-sound", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ inputSound: name || "" }),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "input sound save failed" }));
    throw new Error(error.detail || "input sound save failed");
  }
  const data = await response.json();
  availableConversationSounds = data.sounds || [];
  appSettings.conversationSound = data.conversationSound || "";
  appSettings.conversationSoundVolume = normalizeConversationSoundVolume(data.conversationSoundVolume);
  appSettings.inputSound = data.inputSound || "";
  appSettings.inputSoundVolume = normalizeConversationSoundVolume(data.inputSoundVolume);
  appSettings.autoSummaryEnabled = data.autoSummaryEnabled !== false;
  appSettings.autoSummaryTurns = normalizeConversationAutoSummaryTurns(data.autoSummaryTurns);
  appSettings.arrangeSpacing = normalizeArrangeSpacing(data.arrangeSpacing);
  appSettings.arrangeSize = normalizeArrangeSize(data.arrangeSize);
  stopInputWaitingSound("input-sound-saved");
  inputWaitingAudio = null;
  syncSettingsInputs();
  saveStoredSettings();
  logEvent("info", "set-input-sound-saved", { sound: appSettings.inputSound });
}

async function saveInputSoundVolumeSetting(value) {
  setInputSoundVolume(value, "set-input-volume-local");
  const response = await fetch("/api/settings/input-sound-volume", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ inputSoundVolume: appSettings.inputSoundVolume }),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "input volume save failed" }));
    throw new Error(error.detail || "input volume save failed");
  }
  const data = await response.json();
  appSettings.inputSoundVolume = normalizeConversationSoundVolume(data.inputSoundVolume);
  syncSettingsInputs();
  saveStoredSettings();
  logEvent("info", "set-input-volume-saved", { volume: appSettings.inputSoundVolume });
}

function setConversationSending(enabled) {
  conversationSending = Boolean(enabled);
  const canEdit = conversationCanEditSession();
  sendConversationButton.disabled = conversationSending || !canEdit;
  conversationInput.disabled = conversationSending || !canEdit;
  if (newConversationButton) {
    newConversationButton.disabled = conversationSending;
  }
  if (summarizeConversationButton) {
    summarizeConversationButton.disabled = conversationSending || conversationAutoSummaryInFlight || !canEdit;
  }
  if (conversationSessionSelect) {
    conversationSessionSelect.disabled = conversationSending || Boolean(conversationTypingNodeId);
  }
  if (saveButton) {
    saveButton.disabled = conversationSending;
  }
  if (saveAsButton) {
    saveAsButton.disabled = conversationSending;
  }
  updateConversationCancelButton();
}

function conversationCanCancel() {
  return Boolean(conversationRequestAbortController || conversationTypingNodeId);
}

function updateConversationCancelButton() {
  if (!cancelConversationButton) {
    return;
  }
  const canCancel = conversationCanCancel();
  cancelConversationButton.hidden = !canCancel;
  cancelConversationButton.disabled = !canCancel;
  if (conversationSessionSelect) {
    conversationSessionSelect.disabled = conversationSending || Boolean(conversationTypingNodeId);
  }
}

function conversationIsAtBottom() {
  if (!conversationLog) {
    return true;
  }
  return conversationLog.scrollHeight - conversationLog.scrollTop - conversationLog.clientHeight <= 18;
}

function followConversationBottom() {
  conversationAutoFollow = true;
  conversationLog.scrollTop = conversationLog.scrollHeight;
}

function maybeFollowConversationBottom() {
  if (conversationAutoFollow || conversationIsAtBottom()) {
    followConversationBottom();
  }
}

function conversationUserTurnCount() {
  return conversationLog.querySelectorAll(".conversation-message.user").length;
}

function setConversationMessageText(message, role, text = "") {
  const body = message.querySelector(".conversation-message-body");
  const displayText = formatConversationText(role, text);
  if (body) {
    body.textContent = displayText;
  } else {
    message.textContent = displayText;
  }
  message.dataset.copyText = displayText;
}

function setInputWaitingMessageAnimation(message, text = "入力中...") {
  const body = message.querySelector(".conversation-message-body");
  if (!body) {
    return;
  }
  const displayText = formatConversationText("system", text);
  body.textContent = "";
  [...displayText].forEach((char, index) => {
    const letter = document.createElement("span");
    letter.className = "input-waiting-letter";
    letter.textContent = char;
    letter.style.setProperty("--input-waiting-index", index);
    body.appendChild(letter);
  });
  message.classList.add("typing-indicator");
  message.dataset.copyText = displayText;
}

function shortConversationTargetName(node) {
  const name = meaningName(node);
  return [...name].slice(0, 12).join("");
}

function shortWorkText(value, limit = 24) {
  return [...String(value || "").replace(/\s+/g, " ").trim()].slice(0, limit).join("");
}

function conversationWaitingText(node, { includeMeaningTree = false, attachmentCount = 0, status = "送信中", workText = "" } = {}) {
  const parts = [`${shortConversationTargetName(node)}へ${status}`];
  if (workText) {
    parts.push(shortWorkText(workText));
  }
  if (includeMeaningTree) {
    parts.push("全体");
  }
  if (attachmentCount > 0) {
    parts.push(`添付${attachmentCount}`);
  }
  return parts.join(" / ");
}

function powanWorkStatusLabel(status) {
  return {
    received: "受信",
    working: "作業中",
    completed: "完了",
    failed: "失敗",
    cancelled: "キャンセル",
  }[status] || status || "処理中";
}

function powanWorkShortTask(event) {
  return event?.instructionPreview || event?.textPreview || event?.message || "";
}

function powanWorkEventText(event) {
  const base = String(event?.displayMessage || event?.message || "").trim();
  const task = shortWorkText(powanWorkShortTask(event));
  if (base) {
    return task && !base.includes(task) ? `${base} / ${task}` : base;
  }
  const from = event?.from?.meaning || "ユーザー";
  const to = event?.to?.meaning || "ポワン";
  const status = powanWorkStatusLabel(event?.status);
  const head = `${shortWorkText(from, 10)} -> ${shortWorkText(to, 10)} / ${status}`;
  return task ? `${head} / ${task}` : head;
}

function updateConversationPendingWorkText(text) {
  if (!conversationPendingMessage || !conversationPendingMessage.isConnected) {
    return;
  }
  setInputWaitingMessageAnimation(conversationPendingMessage, text || "処理中");
}

function stopConversationWorkPolling() {
  if (conversationWorkPollTimer) {
    window.clearInterval(conversationWorkPollTimer);
    conversationWorkPollTimer = null;
  }
  conversationWorkPollingActive = false;
}

async function pollConversationWorkEvents() {
  if (!conversationPendingMessage || !conversationPendingMessage.isConnected || !conversationWorkPollingActive) {
    stopConversationWorkPolling();
    return;
  }
  const url = `/api/powan-work-events?project=${encodeURIComponent(projectName)}&file=${encodeURIComponent(documentName)}&after=${conversationWorkEventSequence}`;
  const response = await fetch(url);
  if (!response.ok) {
    return;
  }
  const data = await response.json();
  conversationWorkEventSequence = Math.max(conversationWorkEventSequence, Number(data.latestSequence || 0));
  const events = data.events || [];
  if (!events.length) {
    return;
  }
  const latest = events[events.length - 1];
  updateConversationPendingWorkText(powanWorkEventText(latest));
}

async function currentPowanWorkEventSequence() {
  const url = `/api/powan-work-events?project=${encodeURIComponent(projectName)}&file=${encodeURIComponent(documentName)}&after=0`;
  const response = await fetch(url);
  if (!response.ok) {
    return conversationWorkEventSequence;
  }
  const data = await response.json();
  return Number(data.latestSequence || 0);
}

function startConversationWorkPolling(afterSequence = conversationWorkEventSequence) {
  stopConversationWorkPolling();
  conversationWorkPollingActive = true;
  conversationWorkEventSequence = Number(afterSequence || 0);
  pollConversationWorkEvents().catch((error) => logEvent("debug", "conversation-work-events-poll-error", { message: error.message }));
  conversationWorkPollTimer = window.setInterval(() => {
    pollConversationWorkEvents().catch((error) => logEvent("debug", "conversation-work-events-poll-error", { message: error.message }));
  }, 500);
}

function copyConversationMessage(message, button) {
  const text = message.dataset.copyText || message.querySelector(".conversation-message-body")?.textContent || "";
  if (!text) {
    return;
  }
  navigator.clipboard.writeText(text).then(() => {
    const previous = button.textContent;
    button.textContent = "Copied";
    window.setTimeout(() => {
      button.textContent = previous;
    }, 900);
    logEvent("debug", "conversation-copy-reply", { nodeId: conversationNodeId, length: text.length });
  }).catch((error) => {
    logEvent("error", "conversation-copy-error", { nodeId: conversationNodeId, message: error.message });
  });
}

function setConversationPanelCollapsed(collapsed, reason = "conversation-panel-collapse") {
  if (!conversationPanel) {
    return;
  }
  conversationPanelCollapsed = Boolean(collapsed);
  conversationPanel.classList.toggle("collapsed", conversationPanelCollapsed);
  conversationPanel.hidden = false;
  conversationPanel.title = conversationPanelCollapsed ? "クリックで会話を開く" : "";
  logEvent("debug", reason, { nodeId: conversationNodeId, collapsed: conversationPanelCollapsed });
}

function expandConversationPanel(reason = "conversation-expand") {
  if (!conversationPanel || !conversationNodeId) {
    return;
  }
  setConversationPanelCollapsed(false, reason);
  focusConversationInputIfOpen();
}

function focusConversationInputIfOpen() {
  if (!conversationPanelCollapsed && !conversationInput.disabled) {
    conversationInput.focus();
  }
}

function openConversationPanel(nodeId, options = {}) {
  const { fromTab = false, reason = "conversation-open" } = options;
  const node = nodeById(nodeId);
  if (!node) {
    return;
  }
  if (conversationNodeId && conversationNodeId !== node.id) {
    rememberConversationTabState(conversationNodeId);
  }
  ensureConversationTab(node.id);
  if (conversationNodeId === node.id && conversationPanel && !conversationPanel.hidden) {
    conversationNodeName.textContent = meaningName(node);
    renderConversationTabs();
    expandConversationPanel("conversation-open-existing");
    return;
  }
  conversationNodeId = node.id;
  conversationActiveSessionId = null;
  conversationViewingSessionId = null;
  conversationViewingAllSessions = false;
  conversationSessionList = [];
  conversationNodeName.textContent = meaningName(node);
  conversationPanel.hidden = false;
  setConversationPanelCollapsed(false, "conversation-open-expand");
  conversationAutoFollow = true;
  conversationLog.innerHTML = "";
  const state = restoreConversationDraftState(node.id);
  renderConversationTabs();
  focusConversationInputIfOpen();
  logEvent("debug", reason, { nodeId: node.id, fromTab });
  let loader;
  if (fromTab && state.viewingAllSessions) {
    loader = loadAllConversationSessions(node.id);
  } else if (fromTab && state.viewingSessionId) {
    loader = loadConversationSession(node.id, state.viewingSessionId);
  } else {
    loader = loadConversationMessages(node.id);
  }
  loader.then(() => restoreConversationScroll(node.id, state));
}

function closeConversationPanel(reason = "conversation-close") {
  if (!conversationNodeId) {
    conversationPanel.hidden = true;
    logEvent("debug", reason, { nodeId: null, collapsed: false });
    return;
  }
  rememberConversationTabState(conversationNodeId);
  setConversationPanelCollapsed(true, reason);
}

function appendConversationMessage(role, text = "", options = {}) {
  const shouldFollow = Boolean(options.forceFollow) || conversationAutoFollow || conversationIsAtBottom();
  const attachments = Array.isArray(options.attachments) ? options.attachments : [];
  const message = document.createElement("div");
  const roleClass = conversationRoleClass(role);
  message.className = `conversation-message ${roleClass}`;
  message.dataset.role = role;
  const body = document.createElement("div");
  body.className = "conversation-message-body";
  message.appendChild(body);
  setConversationMessageText(message, role, text);
  appendConversationAttachmentViews(message, attachments);
  if (roleClass === "ai") {
    const copyButton = document.createElement("button");
    copyButton.type = "button";
    copyButton.className = "conversation-copy-button";
    copyButton.textContent = "Copy";
    copyButton.addEventListener("click", () => copyConversationMessage(message, copyButton));
    message.appendChild(copyButton);
  }
  conversationLog.appendChild(message);
  if (shouldFollow) {
    followConversationBottom();
  }
  return message;
}

function stopConversationTyping() {
  if (conversationTypingTimer) {
    window.clearTimeout(conversationTypingTimer);
    conversationTypingTimer = null;
  }
  stopConversationChunkSound("conversation-typing-stop");
  conversationTypingMouthOpen = false;
  if (conversationTypingNodeId) {
    setPowanSpeaking(conversationTypingNodeId, false);
    conversationTypingNodeId = null;
  } else if (conversationNodeId) {
    setPowanSpeaking(conversationNodeId, false);
  }
  updateConversationCancelButton();
}

function powanSpeakingElements(nodeId) {
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

function setPowanSpeaking(nodeId, enabled) {
  if (enabled) {
    conversationTypingMouthOpen = true;
  } else if (conversationTypingNodeId === nodeId || !conversationTypingNodeId) {
    conversationTypingMouthOpen = false;
  }
  for (const element of powanSpeakingElements(nodeId)) {
    element.classList.toggle("speaking", enabled);
    if (!enabled) {
      element.classList.remove("mouth-open", "mouth-closed");
    } else {
      element.classList.toggle("mouth-open", Boolean(conversationTypingMouthOpen));
      element.classList.toggle("mouth-closed", !conversationTypingMouthOpen);
    }
    updatePowanFaceButton(element);
  }
}

function setPowanMouthFrame(nodeId, open) {
  conversationTypingMouthOpen = Boolean(open);
  for (const element of powanSpeakingElements(nodeId)) {
    element.classList.toggle("mouth-open", open);
    element.classList.toggle("mouth-closed", !open);
    updatePowanFaceButton(element);
  }
}

function conversationTypingPauseMs(char) {
  if (char === "\n") {
    return 0;
  }
  if (char === "、") {
    return 100;
  }
  if (char === "。") {
    return 300;
  }
  return 0;
}

function typeConversationReply(nodeId, text, onComplete = null) {
  stopConversationTyping();
  const message = appendConversationMessage("assistant", "");
  const visibleText = formatConversationText("assistant", text);
  let index = 0;
  conversationTypingNodeId = nodeId;
  conversationTypingMouthOpen = true;
  updateConversationCancelButton();
  setPowanSpeaking(nodeId, true);
  if (!visibleText.length) {
    setConversationMessageText(message, "assistant", "");
    setPowanSpeaking(nodeId, false);
    conversationTypingNodeId = null;
    conversationTypingMouthOpen = false;
    updateConversationCancelButton();
    if (onComplete) {
      onComplete();
    }
    return;
  }
  function tick() {
    if (conversationNodeId !== nodeId) {
      setPowanSpeaking(nodeId, false);
      stopConversationChunkSound("conversation-node-changed");
      conversationTypingNodeId = null;
      conversationTypingMouthOpen = false;
      updateConversationCancelButton();
      return;
    }
    const char = visibleText[index];
    setConversationMessageText(message, "assistant", visibleText.slice(0, index + 1));
    maybeFollowConversationBottom();
    const pauseMs = conversationTypingPauseMs(char);
    if (pauseMs > 0) {
      setPowanMouthFrame(nodeId, false);
      stopConversationChunkSound(char === "\n" ? "conversation-line-break-pause" : "conversation-punctuation-pause");
    } else {
      setPowanMouthFrame(nodeId, index % 2 === 0);
      startConversationChunkSound();
    }
    index += 1;
    if (index >= visibleText.length) {
      conversationTypingTimer = null;
      stopConversationChunkSound("conversation-typing-complete");
      setPowanSpeaking(nodeId, false);
      conversationTypingNodeId = null;
      conversationTypingMouthOpen = false;
      updateConversationCancelButton();
      if (onComplete) {
        onComplete();
      }
      return;
    }
    conversationTypingTimer = window.setTimeout(tick, pauseMs || 32);
  }
  tick();
}

async function startNewConversationSession(nodeId, reason = "conversation-new-session") {
  const node = nodeById(nodeId);
  if (!node) {
    return;
  }
  setConversationSending(true);
  try {
    const data = await requestNewConversationSession(node.id);
    if (conversationNodeId !== node.id) {
      return;
    }
    conversationActiveSessionId = normalizeConversationId(data.conversationId);
    conversationViewingSessionId = normalizeConversationId(data.conversationId);
    conversationViewingAllSessions = false;
    conversationLog.innerHTML = "";
    conversationAutoFollow = true;
    for (const message of data.messages || []) {
      appendConversationMessage(message.role, message.text || "");
    }
    appendConversationMessage("system", "新規セッションを開始しました", { forceFollow: true });
    rememberConversationTabState(node.id);
    renderConversationTabs();
    refreshConversationSessions(node.id, data.conversationId);
    logEvent("info", reason, { nodeId: node.id, conversationId: data.conversationId });
  } catch (error) {
    appendConversationMessage("system", `新規セッションを開始できなかった: ${error.message}`, { forceFollow: true });
    logEvent("error", "conversation-new-session-error", { nodeId: node.id, message: error.message });
  } finally {
    setConversationSending(false);
    if (conversationNodeId === node.id) {
      focusConversationInputIfOpen();
    }
  }
}

async function summarizeConversationIntoNewSession(nodeId, reason = "conversation-summarize") {
  const node = nodeById(nodeId);
  if (!node || conversationAutoSummaryInFlight) {
    return;
  }
  conversationAutoSummaryInFlight = true;
  setConversationSending(true);
  const pending = appendConversationMessage("system", "要約中...", { forceFollow: true });
  pending.classList.add("pending");
  try {
    const data = await requestConversationSummary(node.id);
    if (conversationNodeId !== node.id) {
      return;
    }
    conversationActiveSessionId = normalizeConversationId(data.conversationId);
    conversationViewingSessionId = normalizeConversationId(data.conversationId);
    conversationViewingAllSessions = false;
    conversationLog.innerHTML = "";
    conversationAutoFollow = true;
    for (const message of data.messages || []) {
      appendConversationMessage(message.role, message.text || "");
    }
    if (!(data.messages || []).length) {
      appendConversationMessage("system", "要約できる会話がまだありません", { forceFollow: true });
    }
    rememberConversationTabState(node.id);
    renderConversationTabs();
    refreshConversationSessions(node.id, data.conversationId);
    logEvent("info", reason, {
      nodeId: node.id,
      conversationId: data.conversationId,
      summaryLength: (data.summary || "").length,
    });
  } catch (error) {
    pending.remove();
    appendConversationMessage("system", `会話を要約できなかった: ${error.message}`, { forceFollow: true });
    logEvent("error", "conversation-summary-error", { nodeId: node.id, message: error.message });
  } finally {
    conversationAutoSummaryInFlight = false;
    setConversationSending(false);
    if (conversationNodeId === node.id) {
      focusConversationInputIfOpen();
    }
  }
}

function maybeAutoSummarizeConversation(nodeId) {
  if (
    !appSettings.autoSummaryEnabled
    || !conversationCanEditSession()
    || conversationAutoSummaryInFlight
    || conversationUserTurnCount() < appSettings.autoSummaryTurns
  ) {
    return;
  }
  summarizeConversationIntoNewSession(nodeId, "conversation-auto-summarize");
}

function markConversationPendingCancelled(text) {
  if (!conversationPendingMessage || !conversationPendingMessage.isConnected) {
    return false;
  }
  setConversationMessageText(conversationPendingMessage, "system", text);
  conversationPendingMessage.classList.remove("pending");
  return true;
}

async function cancelConversationReply(reason = "conversation-cancel") {
  const requestNodeId = conversationRequestNodeId;
  const typingNodeId = conversationTypingNodeId;
  if (!requestNodeId && !typingNodeId) {
    return;
  }
  conversationCancelRequested = true;
  stopInputWaitingSound(reason);
  if (conversationRequestAbortController) {
    markConversationPendingCancelled("キャンセル中...");
    conversationRequestAbortController.abort();
    if (requestNodeId) {
      requestCancelPowanCodex(requestNodeId).then((data) => {
        logEvent("info", "conversation-cancel-requested", {
          nodeId: requestNodeId,
          cancelled: Boolean(data.cancelled),
          running: Boolean(data.running),
        });
      }).catch((error) => {
        logEvent("warn", "conversation-cancel-error", { nodeId: requestNodeId, message: error.message });
      });
    }
  }
  if (typingNodeId) {
    stopConversationTyping();
    appendConversationMessage("system", "返事をキャンセルしました", { forceFollow: true });
    logEvent("info", "conversation-typing-cancelled", { nodeId: typingNodeId });
  }
  setConversationSending(false);
  updateConversationCancelButton();
}

titleInput.addEventListener("input", () => {
  if (!selectedId) {
    return;
  }
  powanExplorer.updateMeaning(selectedId, { title: titleInput.value }, {
    renderAfter: true,
    reason: "panel-title-input",
  });
});
bodyInput.addEventListener("input", () => {
  if (!selectedId) {
    return;
  }
  powanExplorer.updateMeaning(selectedId, { body: bodyInput.value }, {
    renderAfter: true,
    reason: "panel-body-input",
  });
});
powanKindInput.addEventListener("change", () => {
  if (!selectedId) {
    return;
  }
  powanExplorer.updateMeaning(selectedId, { powanKind: powanKindInput.value }, {
    renderAfter: false,
    reason: "panel-kind-input",
  });
});
codeInput.addEventListener("input", () => {
  const node = nodeById(codePanelNodeId);
  if (!node) {
    return;
  }
  powanExplorer.updateCode(node.id, codeInput.value, {
    renderAfter: true,
    reason: "textarea-code-change",
  });
  updateCodeLineNumbers();
});
codeInput.addEventListener("scroll", () => {
  codeLineNumbers.scrollTop = codeInput.scrollTop;
});
codeInput.addEventListener("blur", () => powanExplorer.endHistoryGroup());
codeInput.addEventListener("keydown", (event) => {
  if (event.key !== "Tab") {
    return;
  }
  event.preventDefault();
  const start = codeInput.selectionStart;
  const end = codeInput.selectionEnd;
  const value = codeInput.value;
  codeInput.value = `${value.slice(0, start)}  ${value.slice(end)}`;
  codeInput.selectionStart = start + 2;
  codeInput.selectionEnd = start + 2;
  codeInput.dispatchEvent(new Event("input", { bubbles: true }));
});
closeCodeButton.addEventListener("click", () => powanExplorer.closeCodeEditor());
if (conversationPanel) {
  conversationPanel.addEventListener("click", (event) => {
    if (!conversationPanelCollapsed) {
      return;
    }
    event.preventDefault();
    expandConversationPanel("conversation-bar-click-expand");
  });
}
closeConversationButton.addEventListener("click", (event) => {
  event.stopPropagation();
  powanExplorer.closeConversation();
});
if (newConversationButton) {
  newConversationButton.addEventListener("click", () => {
    if (conversationNodeId) {
      startNewConversationSession(conversationNodeId);
    }
  });
}
if (summarizeConversationButton) {
  summarizeConversationButton.addEventListener("click", () => {
    if (conversationNodeId) {
      summarizeConversationIntoNewSession(conversationNodeId);
    }
  });
}
if (conversationSessionSelect) {
  conversationSessionSelect.addEventListener("change", () => {
    if (!conversationNodeId || !conversationSessionSelect.value) {
      return;
    }
    if (conversationSessionSelect.value === CONVERSATION_ALL_SESSIONS_VALUE) {
      loadAllConversationSessions(conversationNodeId);
    } else {
      loadConversationSession(conversationNodeId, conversationSessionSelect.value);
    }
  });
}
if (conversationAutoSummaryInput) {
  conversationAutoSummaryInput.addEventListener("change", () => {
    saveConversationAutoSummarySetting().catch((error) => {
      logEvent("error", "set-conversation-auto-summary-error", { message: error.message });
      refreshConversationSounds();
    });
  });
}
if (conversationAutoSummaryTurnsInput) {
  conversationAutoSummaryTurnsInput.addEventListener("change", () => {
    saveConversationAutoSummarySetting().catch((error) => {
      logEvent("error", "set-conversation-auto-summary-turns-error", { message: error.message });
      refreshConversationSounds();
    });
  });
}
if (conversationLog) {
  conversationLog.addEventListener("scroll", () => {
    conversationAutoFollow = conversationIsAtBottom();
  });
  conversationLog.addEventListener(
    "wheel",
    (event) => {
      if (event.deltaY < 0) {
        conversationAutoFollow = false;
      }
    },
    { passive: true },
  );
}
if (conversationInput) {
  conversationInput.addEventListener("keydown", (event) => {
    if (event.key !== "Enter" || event.shiftKey) {
      return;
    }
    event.preventDefault();
    conversationForm.requestSubmit();
  });
  conversationInput.addEventListener("paste", (event) => {
    addConversationAttachmentsFromPaste(event);
  });
}
if (cancelConversationButton) {
  cancelConversationButton.addEventListener("click", () => {
    cancelConversationReply("conversation-cancel-button");
  });
}
editMeaningMenuButton.addEventListener("click", () => {
  const nodeId = nodeContextMenuNodeId;
  powanExplorer.closeNodeMenu("edit-meaning-menu-close");
  if (!nodeId) {
    return;
  }
  openMeaningEditor(nodeId);
});
talkToPowanButton.addEventListener("click", () => {
  const nodeId = nodeContextMenuNodeId;
  powanExplorer.closeNodeMenu("talk-menu-close");
  if (!nodeId) {
    return;
  }
  powanExplorer.talkToPowan(nodeId);
});
openCodeMenuButton.addEventListener("click", () => {
  const nodeId = nodeContextMenuNodeId;
  powanExplorer.closeNodeMenu("open-code-menu-close");
  if (!nodeId) {
    return;
  }
  powanExplorer.openCode(nodeId);
});
arrangePowanMenuButton.addEventListener("click", () => {
  const nodeId = nodeContextMenuNodeId;
  powanExplorer.closeNodeMenu("arrange-subtree-menu-close");
  if (!nodeId) {
    return;
  }
  const selected = selectedNodeIds();
  const arrangeIds = selected.length > 1 && selected.includes(nodeId) ? selected : [nodeId];
  powanExplorer.arrangeSubtree(arrangeIds, arrangeIds.length > 1 ? "arrange-selected-subtrees" : "arrange-subtree");
});
if (arrangeWorldMenuButton) {
  arrangeWorldMenuButton.addEventListener("click", () => {
    powanExplorer.closeWorldMenu("arrange-current-world-menu-close");
    powanExplorer.arrangeCurrentWorld();
  });
}
exportPowanMenuButton.addEventListener("click", () => {
  const nodeId = nodeContextMenuNodeId;
  powanExplorer.closeNodeMenu("export-powan-menu-close");
  if (!nodeId) {
    return;
  }
  powanExplorer.exportPowanSubtree(nodeId);
});
importPowanMenuButton.addEventListener("click", () => {
  const nodeId = nodeContextMenuNodeId;
  powanExplorer.closeNodeMenu("import-powan-menu-close");
  if (!nodeId) {
    return;
  }
  powanExplorer.choosePowanImportTarget(nodeId);
});
if (copySelectionMenuButton) {
  copySelectionMenuButton.addEventListener("click", () => {
    powanExplorer.closeNodeMenu("copy-selection-menu-close");
    powanExplorer.copySelectedPowans().catch((error) => {
      saveState.textContent = "copy error";
      logEvent("error", "copy-selection-menu-error", { message: error.message });
      console.error(error);
    });
  });
}
if (deleteSelectionMenuButton) {
  deleteSelectionMenuButton.addEventListener("click", () => {
    powanExplorer.closeNodeMenu("delete-selection-menu-close");
    powanExplorer.deleteSelected();
  });
}
if (conversationPanel) {
  conversationPanel.addEventListener("dragenter", (event) => {
    if (!dataTransferHasAttachmentDrop(event)) {
      return;
    }
    event.preventDefault();
    event.stopPropagation();
    event.dataTransfer.dropEffect = "copy";
    conversationPanel.classList.add("drag-over");
  });
  conversationPanel.addEventListener("dragover", (event) => {
    if (!dataTransferHasAttachmentDrop(event)) {
      return;
    }
    event.preventDefault();
    event.stopPropagation();
    event.dataTransfer.dropEffect = "copy";
    conversationPanel.classList.add("drag-over");
  });
  conversationPanel.addEventListener("dragleave", (event) => {
    if (!dataTransferHasAttachmentDrop(event) || conversationPanel.contains(event.relatedTarget)) {
      return;
    }
    conversationPanel.classList.remove("drag-over");
  });
  conversationPanel.addEventListener("drop", (event) => {
    if (!dataTransferHasAttachmentDrop(event)) {
      return;
    }
    event.preventDefault();
    event.stopPropagation();
    conversationPanel.classList.remove("drag-over");
    addConversationAttachmentsFromDrop(event);
  });
}
conversationForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const node = nodeById(conversationNodeId);
  const text = conversationInput.value.trim();
  const attachmentPayloads = conversationPendingAttachments.map(conversationPayloadAttachment);
  if (!node || (!text && !attachmentPayloads.length) || sendConversationButton.disabled) {
    return;
  }
  const includeMeaningTree = Boolean(conversationTreeContextInput?.checked);
  const displayAttachments = [...conversationPendingAttachments];
  appendConversationMessage("user", text || "添付を渡す", { forceFollow: true, attachments: displayAttachments });
  conversationInput.value = "";
  conversationPendingAttachments = [];
  renderConversationAttachmentTray();
  rememberConversationTabState(node.id);
  logEvent("debug", "conversation-send", {
    nodeId: node.id,
    length: text.length,
    includeMeaningTree,
    attachmentCount: attachmentPayloads.length,
    attachmentPathCount: attachmentPayloads.filter((attachment) => attachment.pathAvailable).length,
  });
  const controller = new AbortController();
  conversationCancelRequested = false;
  conversationRequestAbortController = controller;
  conversationRequestNodeId = node.id;
  setConversationSending(true);
  const waitingText = conversationWaitingText(node, {
    includeMeaningTree,
    attachmentCount: attachmentPayloads.length,
    status: "送信中",
    workText: text || (attachmentPayloads.length ? "添付を渡す" : ""),
  });
  const pendingMessage = appendConversationMessage("system", waitingText, { forceFollow: true });
  conversationPendingMessage = pendingMessage;
  pendingMessage.classList.add("pending");
  setInputWaitingMessageAnimation(pendingMessage, waitingText);
  startInputWaitingSound();
  try {
    let workEventStartSequence = conversationWorkEventSequence;
    try {
      workEventStartSequence = await currentPowanWorkEventSequence();
    } catch (error) {
      logEvent("debug", "conversation-work-events-start-error", { message: error.message });
    }
    startConversationWorkPolling(workEventStartSequence);
    const data = await requestPowanCodexReply(node.id, text, {
      signal: controller.signal,
      includeMeaningTree,
      attachments: attachmentPayloads,
    });
    stopInputWaitingSound("conversation-reply-received");
    conversationActiveSessionId = normalizeConversationId(data.conversationId);
    conversationViewingSessionId = normalizeConversationId(data.conversationId);
    conversationViewingAllSessions = false;
    rememberConversationTabState(node.id);
    renderConversationTabs();
    refreshConversationSessions(node.id, data.conversationId);
    await reloadCurrentDocument({
      force: true,
      reason: "conversation-agent-sync",
      restoreViewport: false,
      preserveLocalLayouts: true,
    });
    if (data.cancelled) {
      markConversationPendingCancelled("キャンセルしました");
      logEvent("info", "conversation-codex-cancelled", { nodeId: node.id, conversationId: data.conversationId });
      return;
    }
    if (pendingMessage.isConnected) {
      pendingMessage.remove();
    }
    const reply = data.assistantMessage?.text || "";
    typeConversationReply(node.id, reply, () => maybeAutoSummarizeConversation(node.id));
  } catch (error) {
    stopInputWaitingSound("conversation-codex-error");
    if (error.name === "AbortError" || conversationCancelRequested) {
      markConversationPendingCancelled("キャンセルしました");
      logEvent("info", "conversation-fetch-cancelled", { nodeId: node.id });
    } else {
      if (pendingMessage.isConnected) {
        pendingMessage.remove();
      }
      appendConversationMessage("system", `Codex execで返事できなかった: ${error.message}`, { forceFollow: true });
      logEvent("error", "conversation-codex-error", { nodeId: node.id, message: error.message });
    }
  } finally {
    stopInputWaitingSound("conversation-send-finally");
    stopConversationWorkPolling();
    if (conversationRequestAbortController === controller) {
      conversationRequestAbortController = null;
      conversationRequestNodeId = null;
    }
    if (conversationPendingMessage === pendingMessage) {
      conversationPendingMessage = null;
    }
    setConversationSending(false);
    updateConversationCancelButton();
    if (conversationNodeId === node.id) {
      focusConversationInputIfOpen();
    }
    conversationCancelRequested = false;
  }
});
titleInput.addEventListener("blur", () => powanExplorer.endHistoryGroup());
bodyInput.addEventListener("blur", () => powanExplorer.endHistoryGroup());
powanKindInput.addEventListener("blur", () => powanExplorer.endHistoryGroup());
codeLanguageSelect.addEventListener("change", () => {
  const node = nodeById(codePanelNodeId);
  if (!node) {
    return;
  }
  powanExplorer.setCodeLanguage(node.id, codeLanguageSelect.value);
  if (codeEditor) {
    setCodeEditorLanguage(codeEditor, codeLanguageSelect.value, codeEditorValue(codeEditor));
  }
});
shapeInput.addEventListener("change", () => updateSelected((node) => (node.style.shape = shapeInput.value)));
colorInput.addEventListener("input", () => updateSelected((node) => (node.style.color = colorInput.value)));
accentInput.addEventListener("input", () => updateSelected((node) => (node.style.accent = accentInput.value)));
glowInput.addEventListener("change", () => updateSelected((node) => (node.style.glow = glowInput.checked)));
blurInput.addEventListener("change", () => updateSelected((node) => (node.style.blur = blurInput.checked)));
motionInput.addEventListener("change", () => updateSelected((node) => (node.style.motion = motionInput.checked ? "soft" : "none")));
shapeInput.addEventListener("blur", () => powanExplorer.endHistoryGroup());
colorInput.addEventListener("change", () => powanExplorer.endHistoryGroup());
accentInput.addEventListener("change", () => powanExplorer.endHistoryGroup());
glowInput.addEventListener("change", () => powanExplorer.endHistoryGroup());
blurInput.addEventListener("change", () => powanExplorer.endHistoryGroup());
motionInput.addEventListener("change", () => powanExplorer.endHistoryGroup());
if (randomColorInput) {
  randomColorInput.addEventListener("change", () => powanExplorer.setRandomPowanColor(randomColorInput.checked));
}
if (conversationSoundSelect) {
  conversationSoundSelect.addEventListener("change", () => {
    saveConversationSoundSetting(conversationSoundSelect.value).catch((error) => {
      logEvent("error", "set-conversation-sound-error", { message: error.message });
      refreshConversationSounds();
    });
  });
}
if (conversationVolumeInput) {
  conversationVolumeInput.addEventListener("input", () => {
    setConversationSoundVolume(conversationVolumeInput.value, "set-conversation-volume-preview");
  });
  conversationVolumeInput.addEventListener("change", () => {
    saveConversationSoundVolumeSetting(conversationVolumeInput.value).catch((error) => {
      logEvent("error", "set-conversation-volume-error", { message: error.message });
      refreshConversationSounds();
    });
  });
}
if (inputSoundSelect) {
  inputSoundSelect.addEventListener("change", () => {
    saveInputSoundSetting(inputSoundSelect.value).catch((error) => {
      logEvent("error", "set-input-sound-error", { message: error.message });
      refreshConversationSounds();
    });
  });
}
if (inputVolumeInput) {
  inputVolumeInput.addEventListener("input", () => {
    setInputSoundVolume(inputVolumeInput.value, "set-input-volume-preview");
  });
  inputVolumeInput.addEventListener("change", () => {
    saveInputSoundVolumeSetting(inputVolumeInput.value).catch((error) => {
      logEvent("error", "set-input-volume-error", { message: error.message });
      refreshConversationSounds();
    });
  });
}
if (settingsButton) {
  settingsButton.addEventListener("click", () => {
    const params = new URLSearchParams();
    if (projectName) {
      params.set("project", projectName);
    }
    if (documentName) {
      params.set("file", documentName);
    }
    window.location.href = `/settings?${params.toString()}`;
  });
}

function createChildMeaning() {
  powanExplorer.createChild();
}

function createRootMeaning() {
  powanExplorer.createRoot();
}

function deleteSelectedMeaning() {
  powanExplorer.deleteSelected();
}

function restoreFocusedNodeBodyPlaceholder(event) {
  const active = document.activeElement;
  if (!active?.classList?.contains("node-body")) {
    return;
  }
  if (event.target?.closest?.(".node-body")) {
    return;
  }
  if (!active.value) {
    active.placeholder = EMPTY_MEANING_PLACEHOLDER;
  }
  active.blur();
  logEvent("trace", "node-body-placeholder-restored-outside", {
    nodeId: active.closest(".node")?.dataset?.id || null,
    targetClass: String(event.target?.className || ""),
  });
}

function isUndoRedoTextTarget(target) {
  if (!target) {
    return false;
  }
  if (target.isContentEditable) {
    return true;
  }
  const tag = String(target.tagName || "").toLowerCase();
  return tag === "input" || tag === "textarea" || tag === "select" || Boolean(target.closest?.(".cm-editor"));
}

addNodeButton.addEventListener("click", () => powanExplorer.createChild());
addRootButton.addEventListener("click", () => powanExplorer.createRoot());
deleteButton.addEventListener("click", () => powanExplorer.deleteSelected());
if (treeCopyButton) {
  treeCopyButton.addEventListener("click", () => {
    powanExplorer.copySelectedPowans().catch((error) => {
      saveState.textContent = "copy error";
      logEvent("error", "tree-copy-selection-error", { message: error.message });
      console.error(error);
    });
  });
}
if (treeDeleteButton) {
  treeDeleteButton.addEventListener("click", () => powanExplorer.deleteSelected());
}
undoButton.addEventListener("click", () => powanExplorer.undo());
redoButton.addEventListener("click", () => powanExplorer.redo());

saveButton.addEventListener("click", () => powanExplorer.save());
saveAsButton.addEventListener("click", () => powanExplorer.saveAs());
newFileButton.addEventListener("click", () => powanExplorer.newDocument());
loadButton.addEventListener("click", () => reloadCurrentDocument({ force: true, reason: "manual-reload", restoreViewport: true }));
fileInput.addEventListener("change", () => powanExplorer.loadFile());
if (subtreeImportInput) {
  subtreeImportInput.addEventListener("change", async () => {
    const file = subtreeImportInput.files?.[0];
    const targetId = subtreeImportTargetNodeId;
    subtreeImportTargetNodeId = null;
    if (!file || !targetId) {
      subtreeImportInput.value = "";
      return;
    }
    try {
      await powanExplorer.importPowanSubtreeFile(file, {
        parentId: targetId,
        reason: "menu-import-powan-file",
      });
    } catch (error) {
      saveState.textContent = "import error";
      logEvent("error", "menu-import-powan-file-error", { nodeId: targetId, message: error.message });
      console.error(error);
    } finally {
      subtreeImportInput.value = "";
    }
  });
}
fileSelect.addEventListener("change", () => powanExplorer.loadDocument(fileSelect.value));
backButton.addEventListener("click", () => powanExplorer.leaveWorldOneStep());
rootWorldButton.addEventListener("click", () => powanExplorer.leaveWorldRoot());
treeList.addEventListener("dragover", (event) => {
  if (dataTransferHasAttachmentDrop(event)) {
    event.preventDefault();
    event.dataTransfer.dropEffect = "copy";
    return;
  }
  if (!event.dataTransfer.types.includes("text/plain")) {
    return;
  }
  event.preventDefault();
});
treeList.addEventListener("pointerdown", (event) => {
  if (event.button !== 0 || !event.shiftKey || event.target.closest(".tree-toggle, .tree-label, .tree-name-input")) {
    return;
  }
  beginMarqueeSelection(event, "tree");
});
treeList.addEventListener("drop", (event) => {
  if (event.target.closest(".tree-item")) {
    return;
  }
  const file = firstPowanFile(event);
  if (file) {
    event.preventDefault();
    treeDragSourceId = null;
    clearTreeDropTargets();
    powanExplorer.importPowanSubtreeFile(file, {
      parentId: null,
      dropCenter: visibleWorldCenter(),
      reason: "tree-root-import-powan-file",
    }).catch((error) => {
      saveState.textContent = "import error";
      logEvent("error", "tree-root-import-powan-file-error", { message: error.message });
      console.error(error);
    });
    return;
  }
  if (dataTransferHasAttachmentDrop(event)) {
    event.preventDefault();
    treeDragSourceId = null;
    clearTreeDropTargets();
    importAttachmentsFromDrop(event, {
      parentId: null,
      dropCenter: visibleWorldCenter(),
      reason: "tree-root-import-attachment",
    });
    return;
  }
  event.preventDefault();
  const sourceId = treeDragSourceId || event.dataTransfer.getData("text/plain");
  treeDragSourceId = null;
  clearTreeDropTargets();
  moveTreeNodeToRoot(sourceId);
});
if (treePanelToggleButton) {
  treePanelToggleButton.addEventListener("click", () => {
    setTreePanelCollapsed(!treePanelCollapsed, "toggle-tree-panel-collapsed");
  });
}
if (panelToggleButton) {
  panelToggleButton.addEventListener("click", () => {
    setPanelCollapsed(!panelCollapsed, "toggle-panel-collapsed");
  });
}
if (conversationFontDecreaseButton) {
  conversationFontDecreaseButton.addEventListener("click", () => {
    setConversationFontSize(conversationFontSize - 1, "conversation-font-decrease");
  });
}
if (conversationFontIncreaseButton) {
  conversationFontIncreaseButton.addEventListener("click", () => {
    setConversationFontSize(conversationFontSize + 1, "conversation-font-increase");
  });
}

treeResizeHandle.addEventListener("pointerdown", (event) => {
  event.preventDefault();
  const width = Number.parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--tree-panel-width")) || 260;
  treeResize = {
    startX: event.clientX,
    startWidth: width,
  };
  document.body.classList.add("resizing-tree");
  treeResizeHandle.setPointerCapture(event.pointerId);
});
panelResizeHandle.addEventListener("pointerdown", (event) => {
  event.preventDefault();
  const width = Number.parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--panel-width")) || 300;
  panelResize = {
    startX: event.clientX,
    startWidth: width,
  };
  document.body.classList.add("resizing-panel");
  panelResizeHandle.setPointerCapture(event.pointerId);
});
if (conversationResizeHandle) {
  conversationResizeHandle.addEventListener("pointerdown", (event) => {
    event.preventDefault();
    const height = Number.parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--conversation-panel-height")) || 280;
    conversationResize = {
      startY: event.clientY,
      startHeight: height,
    };
    document.body.classList.add("resizing-conversation");
    conversationResizeHandle.setPointerCapture(event.pointerId);
  });
}
canvas.addEventListener("dragenter", (event) => {
  if (!dataTransferHasAttachmentDrop(event)) {
    return;
  }
  event.preventDefault();
  event.dataTransfer.dropEffect = "copy";
});
canvas.addEventListener("dragover", (event) => {
  if (!dataTransferHasAttachmentDrop(event)) {
    return;
  }
  event.preventDefault();
  event.dataTransfer.dropEffect = "copy";
  clearDropTargets();
  const target = findDropTarget(null, event.clientX, event.clientY);
  if (target) {
    target.classList.add("drop-target");
  }
});
canvas.addEventListener("dragleave", (event) => {
  if (!dataTransferHasAttachmentDrop(event) || canvas.contains(event.relatedTarget)) {
    return;
  }
  clearDropTargets();
});
canvas.addEventListener("drop", (event) => {
  const file = firstPowanFile(event);
  const hasAttachmentDrop = dataTransferHasAttachmentDrop(event);
  if (!file && !hasAttachmentDrop) {
    return;
  }
  event.preventDefault();
  clearDropTargets();
  const target = findDropTarget(null, event.clientX, event.clientY);
  const targetId = target?.dataset?.id || null;
  if (!file) {
    const parentId = targetId || openParentId || null;
    const reason = targetId ? "canvas-import-attachment-into-node" : "canvas-import-attachment-at-space";
    importAttachmentsFromDrop(event, {
      parentId,
      dropCenter: targetId ? null : powanFileDropPoint(event),
      reason,
    });
    return;
  }
  const reason = targetId ? "canvas-import-powan-file-into-node" : "canvas-import-powan-file-at-space";
  powanExplorer.importPowanSubtreeFile(file, {
    parentId: targetId || openParentId || null,
    dropCenter: targetId ? null : powanFileDropPoint(event),
    reason,
  }).catch((error) => {
    saveState.textContent = "import error";
    logEvent("error", `${reason}-error`, { targetId, message: error.message });
    console.error(error);
  });
});
canvas.addEventListener("contextmenu", (event) => {
  if (!isCanvasSpace(event.target)) {
    return;
  }
  event.preventDefault();
  event.stopPropagation();
  powanExplorer.openWorldMenu(event.clientX, event.clientY);
});
canvas.addEventListener("pointerdown", (event) => {
  if (!nodeContextMenu.hidden) {
    powanExplorer.closeNodeMenu("canvas-pointer-close-menu");
  }
  if (worldContextMenu && !worldContextMenu.hidden) {
    powanExplorer.closeWorldMenu("canvas-pointer-close-world-menu");
  }
  if (event.button === 0 && isCanvasSpace(event.target)) {
    if (event.shiftKey) {
      beginMarqueeSelection(event, "canvas");
      return;
    }
    beginPan(event);
  }
});
window.addEventListener("pointerdown", (event) => {
  restoreFocusedNodeBodyPlaceholder(event);
  if (!nodeContextMenu.hidden && !event.target.closest("#nodeContextMenu")) {
    powanExplorer.closeNodeMenu("window-pointer-close-menu");
  }
  if (worldContextMenu && !worldContextMenu.hidden && !event.target.closest("#worldContextMenu")) {
    powanExplorer.closeWorldMenu("window-pointer-close-world-menu");
  }
});
window.addEventListener("keydown", (event) => {
  if ((event.ctrlKey || event.metaKey) && !isUndoRedoTextTarget(event.target)) {
    const key = event.key.toLowerCase();
    if (key === "z") {
      event.preventDefault();
      if (event.shiftKey) {
        powanExplorer.redo();
      } else {
        powanExplorer.undo();
      }
      return;
    }
    if (key === "y") {
      event.preventDefault();
      powanExplorer.redo();
      return;
    }
    if (key === "c") {
      event.preventDefault();
      powanExplorer.copySelectedPowans().catch((error) => {
        saveState.textContent = "copy error";
        logEvent("error", "keyboard-copy-selection-error", { message: error.message });
        console.error(error);
      });
      return;
    }
  }
  if ((event.key === "Delete" || event.key === "Backspace") && !isUndoRedoTextTarget(event.target) && selectionCount() > 0) {
    event.preventDefault();
    powanExplorer.deleteSelected();
    return;
  }
  if (event.key === "Escape" && !nodeContextMenu.hidden) {
    powanExplorer.closeNodeMenu("escape-close-menu");
  }
  if (event.key === "Escape" && worldContextMenu && !worldContextMenu.hidden) {
    powanExplorer.closeWorldMenu("escape-close-world-menu");
  }
});
canvas.addEventListener(
  "wheel",
  (event) => {
    event.preventDefault();
    const factor = Math.exp(-event.deltaY * ZOOM_STEP);
    if (event.ctrlKey) {
      powanExplorer.resizeSelectedByWheel(factor);
      return;
    }
    if (event.shiftKey) {
      powanExplorer.spreadSelectedFromOriginByWheel(factor);
      return;
    }
    zoomAt(event.clientX, event.clientY, viewport.scale * factor);
  },
  { passive: false },
);

async function refreshFiles() {
  const response = await fetch(`/api/files?project=${encodeURIComponent(projectName)}`);
  const data = await response.json();
  fileSelect.innerHTML = "";
  for (const file of data.files) {
    const option = document.createElement("option");
    option.value = file;
    option.textContent = file;
    fileSelect.appendChild(option);
  }
  fileSelect.value = documentName;
}

async function loadDocument(name = "project.powan") {
  logEvent("debug", "load-document-start", { projectName, name });
  const nextDoc = await fetchDocument(name);
  documentSnapshot = documentSignature(nextDoc);
  powanExplorer.setDocument(nextDoc, { name, status: "loaded", reason: "load-document-state" });
  await refreshFiles();
  render();
  startAutoReload();
  logEvent("debug", "load-document-complete", { projectName, name, nodeCount: doc.nodes.length });
}

async function loadDocumentFromFile() {
  const file = fileInput.files?.[0];
  if (!file) {
    return;
  }
  try {
    const imported = JSON.parse(await file.text());
    if (!Array.isArray(imported.nodes)) {
      throw new Error("ABC document must contain nodes");
    }
    const importedName = file.name.endsWith(".powan") ? file.name : `${file.name}.powan`;
    powanExplorer.setDocument(imported, { name: importedName, status: "loaded file", reason: "load-file-state" });
    documentSnapshot = documentSignature(imported);
    await refreshFiles();
    render();
    logEvent("debug", "load-file-complete", { name: documentName, nodeCount: doc.nodes.length });
  } catch (error) {
    saveState.textContent = "load error";
    logEvent("error", "load-file-error", { message: error.message });
    console.error(error);
  } finally {
    fileInput.value = "";
  }
}

async function saveDocument() {
  if (conversationRequestAbortController) {
    saveState.textContent = "agent running";
    logEvent("warn", "save-document-blocked-during-agent-run", {
      projectName,
      name: documentName,
      nodeCount: doc?.nodes?.length || 0,
      conversationNodeId,
      conversationRequestNodeId,
    });
    return;
  }
  saveState.textContent = "saving";
  const savedViewport = saveViewportToDocument();
  logEvent("debug", "save-document-start", { projectName, name: documentName, nodeCount: doc.nodes.length, viewport: savedViewport });
  const savePayload = JSON.stringify(doc);
  const saveUrl = `/api/doc/${encodeURIComponent(documentName)}?project=${encodeURIComponent(projectName)}`;
  const saveHeaders = {
    "Content-Type": "application/json",
  };
  if (documentSnapshot) {
    saveHeaders["X-ABC-Document-Snapshot"] = encodeURIComponent(documentSnapshot);
  }
  try {
    logEvent("debug", "save-document-fetch-start", {
      projectName,
      name: documentName,
      nodeCount: doc.nodes.length,
      viewport: savedViewport,
      payloadLength: savePayload.length,
      hasSnapshot: Boolean(documentSnapshot),
    });
    const response = await fetch(saveUrl, {
      method: "POST",
      headers: saveHeaders,
      body: savePayload,
    });
    logEvent("debug", "save-document-response", {
      projectName,
      name: documentName,
      status: response.status,
      ok: response.ok,
      viewport: savedViewport,
    });
    if (response.status === 409 || response.status === 428) {
      saveState.textContent = "server updated";
      logEvent("warn", "save-document-stale-rejected", {
        projectName,
        name: documentName,
        nodeCount: doc.nodes.length,
        viewport: savedViewport,
        status: response.status,
      });
      await reloadCurrentDocument({ force: true, reason: "save-conflict-reload", restoreViewport: false });
      return;
    }
    if (!response.ok) {
      const responseText = await response.text();
      logEvent("error", "save-document-failed-response", {
        projectName,
        name: documentName,
        status: response.status,
        viewport: savedViewport,
        responseText: responseText.slice(0, 1200),
      });
      throw new Error(`save failed: ${response.status}`);
    }
    const data = await response.json();
    saveState.textContent = "saved";
    documentSnapshot = data.snapshot || documentSignature(doc);
    await refreshFiles();
    logEvent("debug", "save-document-complete", { projectName, name: documentName, nodeCount: doc.nodes.length, viewport: savedViewport });
  } catch (error) {
    saveState.textContent = "save error";
    logEvent("error", "save-document-error", {
      projectName,
      name: documentName,
      nodeCount: doc?.nodes?.length || 0,
      viewport: savedViewport,
      message: error?.message || String(error),
    });
    await flushLogQueue();
  }
}

async function saveDocumentAs() {
  const value = window.prompt("保存するPowanファイル名", documentName);
  if (!value) {
    return;
  }
  const trimmed = value.trim();
  if (!trimmed) {
    return;
  }
  powanExplorer.setDocumentName(trimmed.endsWith(".powan") ? trimmed : `${trimmed}.powan`, "save-document-as-name");
  logEvent("debug", "save-document-as", { name: documentName });
  await saveDocument();
}

async function createDocument() {
  logEvent("debug", "create-document-start", { projectName });
  const response = await fetch(
    `/api/doc?project=${encodeURIComponent(projectName)}&random_color=${appSettings.randomPowanColor ? "true" : "false"}`,
    { method: "POST" },
  );
  const data = await response.json();
  await powanExplorer.loadDocument(data.file);
  logEvent("debug", "create-document-complete", { projectName, name: data.file });
}

function bootstrapAbcCanvas() {
  const params = new URLSearchParams(window.location.search);
  const project = params.get("project")?.trim();
  if (!project) {
    window.location.href = "/";
    return;
  }
  powanExplorer.setProjectName(project, "bootstrap-project");
  loadStoredLayout();
  loadStoredSettings();
  refreshConversationSounds();
  startPowanFaceClock();
  powanExplorer.loadDocument(documentName).catch((error) => {
    saveState.textContent = "error";
    logEvent("error", "load-document-error", { projectName, name: documentName, message: error.message });
    console.error(error);
  });
}
