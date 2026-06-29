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
  item.classList.toggle("focus-ancestor-text", isFocusedAncestor(node.id));
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
  if (selectChildPowansMenuButton) {
    const parent = nodeById(nodeContextMenuNodeId);
    selectChildPowansMenuButton.disabled = !parent || !powanExplorer.childrenOf(parent).length;
  }
  if (bulkCommandMenuButton) {
    const targetIds = selectedNodeIds();
    const groups = bulkCommandGroupsForIds(targetIds);
    bulkCommandMenuButton.disabled = targetIds.length < 2 || !groups.groups.length || bulkCommandSending;
    bulkCommandMenuButton.title = targetIds.length < 2
      ? "複数選択してから使う"
      : groups.groups.length
        ? `${targetIds.length}件へ一括指示`
        : "親ポワンがない選択には使えない";
  }
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

function bulkCommandGroupsForIds(ids) {
  const nodes = uniqueActiveNodeIds(ids).map((id) => nodeById(id)).filter(Boolean);
  const groupsByParent = new Map();
  const skipped = [];
  for (const node of nodes) {
    const parentId = node.parent || null;
    const parent = parentId ? nodeById(parentId) : null;
    if (!parent) {
      skipped.push({
        nodeId: node.id,
        name: meaningName(node),
        reason: parentId ? "missing-parent" : "root-node",
      });
      continue;
    }
    if (!groupsByParent.has(parent.id)) {
      groupsByParent.set(parent.id, {
        parent,
        nodes: [],
      });
    }
    groupsByParent.get(parent.id).nodes.push(node);
  }
  return {
    nodes,
    groups: [...groupsByParent.values()],
    skipped,
  };
}

function isBulkCommandTab(tab = activeConversationTab()) {
  return tab?.kind === "bulk-command";
}

function activeBulkCommandState() {
  const tab = activeConversationTab();
  if (!isBulkCommandTab(tab)) {
    return null;
  }
  return conversationTabState(tab.id);
}

function bulkCommandTargetSummary(nodes) {
  const names = nodes.map(meaningName);
  return `${nodes.length}件: ${names.join(" / ")}`;
}

function historyTextPreview(value, limit = 30) {
  const text = String(value || "").replace(/\s+/g, " ").trim();
  if (!text) {
    return "";
  }
  const chars = [...text];
  return chars.length > limit ? `${chars.slice(0, limit).join("")}...` : text;
}

function historyIsoNow() {
  return new Date().toISOString();
}

function nodeHistoryPath(nodeId) {
  const path = [];
  const seen = new Set();
  let node = nodeById(nodeId);
  while (node && !seen.has(node.id)) {
    seen.add(node.id);
    path.unshift(meaningName(node));
    node = node.parent ? nodeById(node.parent) : null;
  }
  return path.length ? path : ["外側"];
}

function nodeTreeSortKey(nodeId) {
  const nodes = Array.isArray(doc?.nodes) ? doc.nodes.filter((node) => node && !node.archived) : [];
  const orderById = new Map(nodes.map((node, index) => [node.id, index]));
  const parts = [];
  const seen = new Set();
  let node = nodeById(nodeId);
  while (node && !seen.has(node.id)) {
    seen.add(node.id);
    const siblings = nodes.filter((item) => (item.parent || null) === (node.parent || null));
    const siblingIndex = Math.max(0, siblings.findIndex((item) => item.id === node.id));
    const originalIndex = orderById.get(node.id) ?? siblingIndex;
    parts.unshift(`${String(siblingIndex).padStart(5, "0")}:${String(originalIndex).padStart(5, "0")}:${meaningName(node)}`);
    node = node.parent ? nodeById(node.parent) : null;
  }
  return parts.join("/");
}

function bulkCommandHistoryStorageKey() {
  return `${BULK_COMMAND_HISTORY_STORAGE_PREFIX}:${projectName || "default"}:${documentName || "project.powan"}`;
}

function makeBulkCommandHistoryId() {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return `bulk-${crypto.randomUUID()}`;
  }
  conversationTabSerial += 1;
  return `bulk-${Date.now().toString(36)}-${conversationTabSerial}`;
}

function loadStoredBulkCommandHistories() {
  try {
    const rows = JSON.parse(localStorage.getItem(bulkCommandHistoryStorageKey()) || "[]");
    return Array.isArray(rows) ? rows.filter((row) => row && row.id) : [];
  } catch {
    return [];
  }
}

function saveStoredBulkCommandHistories(rows) {
  const clean = Array.isArray(rows) ? rows.filter((row) => row && row.id).slice(0, 80) : [];
  localStorage.setItem(bulkCommandHistoryStorageKey(), JSON.stringify(clean));
}

function storedBulkCommandHistoryItem(row) {
  const targetIds = Array.isArray(row.targetIds) ? row.targetIds : [];
  const targetNames = Array.isArray(row.targetNames) ? row.targetNames : [];
  const messages = Array.isArray(row.messages)
    ? row.messages.filter((message) => message && typeof message.role === "string").map((message) => ({
      role: message.role,
      text: String(message.text || ""),
      createdAt: message.createdAt || row.updatedAt || row.createdAt || "",
    }))
    : [];
  const lastResultMessage = [...messages].reverse().find((message) => String(message.text || "").startsWith("送信完了:"));
  const lastUserMessage = [...messages].reverse().find((message) => message.role === "user");
  const lastMessage = lastResultMessage || lastUserMessage || messages[messages.length - 1] || null;
  const sortKeys = targetIds.map(nodeTreeSortKey).filter(Boolean).sort();
  const sortKey = sortKeys[0] || "zzzzz";
  return {
    type: "bulk",
    key: `bulk:${row.id}`,
    id: row.id,
    bulkHistoryId: row.id,
    createdAt: row.createdAt || row.updatedAt || "",
    updatedAt: row.updatedAt || row.createdAt || "",
    targetIds,
    targetNames,
    messages,
    title: "一括送信",
    pathText: targetNames.length ? targetNames.join(" / ") : targetIds.join(" / "),
    preview: historyTextPreview(lastMessage?.text || "", 42),
    treeSortKey: `${sortKey}/bulk`,
  };
}

function upsertStoredBulkCommandHistory(item) {
  const rows = loadStoredBulkCommandHistories();
  const index = rows.findIndex((row) => row.id === item.id);
  if (index >= 0) {
    rows[index] = item;
  } else {
    rows.unshift(item);
  }
  rows.sort((left, right) => String(right.updatedAt || "").localeCompare(String(left.updatedAt || "")));
  saveStoredBulkCommandHistories(rows);
}

function saveBulkCommandHistoryToServer(item) {
  if (!projectName || !documentName || !item?.id) {
    return;
  }
  fetch("/api/bulk-conversation-history", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      project: projectName,
      file: documentName,
      id: item.id,
      targetIds: item.targetIds || [],
      targetNames: item.targetNames || [],
      messages: item.messages || [],
      createdAt: item.createdAt || "",
      updatedAt: item.updatedAt || "",
    }),
  }).then((response) => {
    if (!response.ok) {
      throw new Error(`bulk history save failed: ${response.status}`);
    }
    return response.json();
  }).then((data) => {
    conversationHistoryBulkServerItems = [
      ...conversationHistoryBulkServerItems.filter((row) => row.id !== data.id),
      storedBulkCommandHistoryItem(data),
    ];
    mergeConversationHistoryItems();
  }).catch((error) => {
    logEvent("warn", "bulk-history-save-error", { message: error.message, bulkHistoryId: item.id });
  });
}

function persistBulkCommandTab(tab = activeConversationTab()) {
  if (!isBulkCommandTab(tab)) {
    return;
  }
  const state = conversationTabState(tab.id);
  if (!state.bulkHistoryId) {
    state.bulkHistoryId = makeBulkCommandHistoryId();
  }
  const now = historyIsoNow();
  state.bulkCreatedAt = state.bulkCreatedAt || now;
  state.bulkUpdatedAt = now;
  const item = {
    id: state.bulkHistoryId,
    projectName,
    documentName,
    createdAt: state.bulkCreatedAt,
    updatedAt: state.bulkUpdatedAt,
    targetIds: Array.isArray(state.bulkTargetIds) ? state.bulkTargetIds : [],
    targetNames: Array.isArray(state.bulkTargetNames) ? state.bulkTargetNames : [],
    messages: Array.isArray(state.bulkMessages) ? state.bulkMessages : [],
  };
  upsertStoredBulkCommandHistory(item);
  saveBulkCommandHistoryToServer(item);
  mergeConversationHistoryItems();
}

function normalizeConversationHistorySession(session) {
  const node = nodeById(session.powanId);
  const path = nodeHistoryPath(session.powanId);
  const preview = historyTextPreview(session.firstUserText || session.lastMessageText || session.title || "", 42);
  return {
    type: "powan",
    key: `powan:${session.powanId}:${session.id}`,
    id: normalizeConversationId(session.id),
    conversationId: normalizeConversationId(session.id),
    nodeId: session.powanId,
    active: Boolean(session.active),
    title: node ? meaningName(node) : session.powanId,
    pathText: path.join(" / "),
    preview,
    messageCount: Number(session.messageCount) || 0,
    createdAt: session.createdAt || "",
    updatedAt: session.updatedAt || session.createdAt || "",
    treeSortKey: node ? nodeTreeSortKey(session.powanId) : "zzzzz",
  };
}

function sortedConversationHistoryItems(items) {
  const list = [...items];
  if (conversationHistorySort === "tree") {
    list.sort((left, right) => {
      const tree = String(left.treeSortKey || "").localeCompare(String(right.treeSortKey || ""), "ja");
      if (tree) {
        return tree;
      }
      return String(right.updatedAt || "").localeCompare(String(left.updatedAt || ""));
    });
    return list;
  }
  list.sort((left, right) => String(right.updatedAt || "").localeCompare(String(left.updatedAt || "")));
  return list;
}

function mergeConversationHistoryItems() {
  const bulkById = new Map();
  for (const item of conversationHistoryBulkServerItems) {
    bulkById.set(item.id, item);
  }
  for (const item of loadStoredBulkCommandHistories().map(storedBulkCommandHistoryItem)) {
    const current = bulkById.get(item.id);
    if (!current || String(item.updatedAt || "") >= String(current.updatedAt || "")) {
      bulkById.set(item.id, item);
    }
  }
  conversationHistoryItems = sortedConversationHistoryItems([...conversationHistoryServerItems, ...bulkById.values()]);
  renderConversationHistoryList();
}

async function requestConversationHistory() {
  const response = await fetch(
    `/api/conversation-history?project=${encodeURIComponent(projectName)}&file=${encodeURIComponent(documentName)}`,
  );
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: `history failed: ${response.status}` }));
    throw new Error(body.detail || `history failed: ${response.status}`);
  }
  return response.json();
}

async function requestBulkConversationHistory() {
  const response = await fetch(
    `/api/bulk-conversation-history?project=${encodeURIComponent(projectName)}&file=${encodeURIComponent(documentName)}`,
  );
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: `bulk history failed: ${response.status}` }));
    throw new Error(body.detail || `bulk history failed: ${response.status}`);
  }
  return response.json();
}

async function refreshConversationHistory({ includeServer = true, reason = "conversation-history-refresh" } = {}) {
  if (!conversationHistoryList || !projectName || !documentName) {
    return;
  }
  conversationHistorySort = conversationHistorySortSelect?.value || conversationHistorySort || "newest";
  if (!includeServer) {
    mergeConversationHistoryItems();
    return;
  }
  conversationHistoryLoading = true;
  renderConversationHistoryList();
  try {
    const [data, bulkData] = await Promise.all([
      requestConversationHistory(),
      requestBulkConversationHistory(),
    ]);
    conversationHistoryServerItems = (data.sessions || []).map(normalizeConversationHistorySession);
    conversationHistoryBulkServerItems = (bulkData.sessions || []).map(storedBulkCommandHistoryItem);
    logEvent("debug", reason, {
      normalCount: conversationHistoryServerItems.length,
      bulkCount: conversationHistoryBulkServerItems.length,
      localBulkCount: loadStoredBulkCommandHistories().length,
    });
  } catch (error) {
    saveState.textContent = "history error";
    logEvent("error", "conversation-history-refresh-error", { message: error.message });
  } finally {
    conversationHistoryLoading = false;
    mergeConversationHistoryItems();
  }
}

function renderConversationHistoryList() {
  if (!conversationHistoryList) {
    return;
  }
  conversationHistoryList.innerHTML = "";
  if (conversationHistoryLoading && !conversationHistoryItems.length) {
    const loading = document.createElement("div");
    loading.className = "conversation-history-loading";
    loading.textContent = "読み込み中";
    conversationHistoryList.appendChild(loading);
    return;
  }
  if (!conversationHistoryItems.length) {
    const empty = document.createElement("div");
    empty.className = "conversation-history-empty";
    empty.textContent = "履歴なし";
    conversationHistoryList.appendChild(empty);
    return;
  }
  for (const item of conversationHistoryItems) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "conversation-history-item";
    button.dataset.historyKey = item.key;
    button.title = item.pathText || item.title;
    const title = document.createElement("div");
    title.className = "conversation-history-title";
    title.textContent = item.type === "bulk" ? item.title : `${item.title} #${item.conversationId || "-"}`;
    const meta = document.createElement("div");
    meta.className = "conversation-history-meta";
    meta.textContent = item.type === "bulk"
      ? `${item.pathText || "対象なし"}`
      : `${item.pathText} / ${item.messageCount}件`;
    const preview = document.createElement("div");
    preview.className = "conversation-history-preview";
    preview.textContent = item.preview || " ";
    button.append(title, meta, preview);
    button.addEventListener("click", () => openConversationHistoryItem(item));
    conversationHistoryList.appendChild(button);
  }
}

function findOpenPowanConversationHistoryTab(item) {
  return conversationTabs.find((tab) => {
    if (isBulkCommandTab(tab) || tab.nodeId !== item.nodeId) {
      return false;
    }
    const state = conversationTabState(tab.id);
    return normalizeConversationId(state.viewingSessionId) === normalizeConversationId(item.conversationId);
  }) || null;
}

function findOpenBulkConversationHistoryTab(item) {
  return conversationTabs.find((tab) => {
    if (!isBulkCommandTab(tab)) {
      return false;
    }
    const state = conversationTabState(tab.id);
    return state.bulkHistoryId === item.bulkHistoryId;
  }) || null;
}

function openPowanConversationHistoryItem(item) {
  const node = nodeById(item.nodeId);
  if (!node) {
    saveState.textContent = "history missing";
    logEvent("warn", "conversation-history-open-missing-node", { nodeId: item.nodeId, conversationId: item.conversationId });
    return;
  }
  if (activeConversationTabId) {
    rememberConversationTabState(activeConversationTabId);
  }
  const existing = findOpenPowanConversationHistoryTab(item);
  if (existing) {
    switchConversationTab(existing.id, "conversation-history-focus-open-tab");
    return;
  }
  const tab = createConversationTab(item.nodeId, "conversation-history-tab-created");
  const state = conversationTabState(tab.id);
  state.viewingSessionId = normalizeConversationId(item.conversationId);
  state.viewingAllSessions = false;
  openConversationPanel(item.nodeId, { tabMode: "activate", tabId: tab.id, reason: "conversation-history-open" });
}

function openBulkConversationHistoryItem(item) {
  if (activeConversationTabId) {
    rememberConversationTabState(activeConversationTabId);
  }
  const existing = findOpenBulkConversationHistoryTab(item);
  if (existing) {
    showBulkCommandTab(existing, "bulk-history-focus-open-tab");
    return;
  }
  const tab = createConversationTab(null, "bulk-history-tab-created", { kind: "bulk-command" });
  const state = conversationTabState(tab.id);
  state.bulkHistoryId = item.bulkHistoryId;
  state.bulkCreatedAt = item.createdAt || historyIsoNow();
  state.bulkUpdatedAt = item.updatedAt || state.bulkCreatedAt;
  state.bulkTargetIds = Array.isArray(item.targetIds) ? item.targetIds : [];
  state.bulkTargetNames = Array.isArray(item.targetNames) ? item.targetNames : [];
  state.bulkMessages = Array.isArray(item.messages) ? item.messages : [];
  bulkCommandTargetIds = state.bulkTargetIds;
  showBulkCommandTab(tab, "bulk-history-open");
}

function openConversationHistoryItem(item) {
  if (item.type === "bulk") {
    openBulkConversationHistoryItem(item);
  } else {
    openPowanConversationHistoryItem(item);
  }
  logEvent("info", "conversation-history-open-item", {
    type: item.type,
    key: item.key,
    nodeId: item.nodeId || null,
    conversationId: item.conversationId || null,
    bulkHistoryId: item.bulkHistoryId || null,
  });
}

function renderBulkCommandMessages(tab) {
  const state = conversationTabState(tab.id);
  conversationLog.innerHTML = "";
  for (const message of state.bulkMessages || []) {
    appendConversationMessage(message.role, message.text, { forceFollow: false });
  }
  if (Number.isFinite(Number(state.scrollTop))) {
    conversationLog.scrollTop = Number(state.scrollTop);
  } else {
    followConversationBottom();
  }
}

function appendBulkCommandMessage(role, text, options = {}) {
  const state = activeBulkCommandState();
  if (state) {
    if (!Array.isArray(state.bulkMessages)) {
      state.bulkMessages = [];
    }
    state.bulkMessages.push({ role, text, createdAt: historyIsoNow() });
    persistBulkCommandTab(activeConversationTab());
  }
  return appendConversationMessage(role, text, options);
}

function showBulkCommandTab(tab, reason = "bulk-command-tab-show") {
  if (activeConversationTabId && activeConversationTabId !== tab.id) {
    rememberConversationTabState(activeConversationTabId);
  }
  activeConversationTabId = tab.id;
  tab.nodeId = null;
  tab.kind = "bulk-command";
  conversationNodeId = null;
  conversationActiveSessionId = null;
  conversationViewingSessionId = null;
  conversationViewingAllSessions = false;
  conversationSessionList = [];
  conversationPendingAttachments = [];
  conversationPanel.hidden = false;
  setConversationPanelCollapsed(false, `${reason}-expand`);
  conversationNodeName.textContent = "一括指示";
  conversationInput.value = conversationTabState(tab.id).draft || "";
  conversationInput.placeholder = "選択したポワンに一括で話しかける";
  renderConversationAttachmentTray();
  renderConversationSessions([]);
  renderBulkCommandMessages(tab);
  updateConversationSessionMode();
  renderConversationTabs();
  focusConversationInputIfOpen();
  logEvent("info", reason, {
    tabId: tab.id,
    targetIds: conversationTabState(tab.id).bulkTargetIds || [],
  });
}

function openBulkCommandDialog() {
  const targetIds = selectedNodeIds();
  const grouped = bulkCommandGroupsForIds(targetIds);
  logEvent("info", "bulk-command-tab-open-request", {
    selectedIds: targetIds,
    selectedCount: targetIds.length,
    eligibleCount: grouped.groups.reduce((count, group) => count + group.nodes.length, 0),
    skipped: grouped.skipped,
    groups: grouped.groups.map((group) => ({
      parentId: group.parent.id,
      parentName: meaningName(group.parent),
      childIds: group.nodes.map((node) => node.id),
      childNames: group.nodes.map(meaningName),
    })),
  });
  if (targetIds.length < 2 || !grouped.groups.length) {
    saveState.textContent = "bulk unavailable";
    logEvent("warn", "bulk-command-tab-open-rejected", {
      selectedIds: targetIds,
      selectedCount: targetIds.length,
      skipped: grouped.skipped,
    });
    return;
  }
  const eligibleNodes = grouped.groups.flatMap((group) => group.nodes);
  const names = eligibleNodes.map(meaningName);
  if (activeConversationTabId) {
    rememberConversationTabState(activeConversationTabId);
  }
  const tab = createConversationTab(null, "bulk-command-tab-created", { kind: "bulk-command" });
  const state = conversationTabState(tab.id);
  state.bulkHistoryId = makeBulkCommandHistoryId();
  state.bulkCreatedAt = historyIsoNow();
  state.bulkUpdatedAt = state.bulkCreatedAt;
  state.bulkTargetIds = eligibleNodes.map((node) => node.id);
  state.bulkTargetNames = names;
  state.bulkMessages = [
    {
      role: "system",
      text: `一括指示の対象: ${bulkCommandTargetSummary(eligibleNodes)}`,
      createdAt: state.bulkCreatedAt,
    },
  ];
  if (grouped.skipped.length) {
    state.bulkMessages.push({
      role: "system",
      text: `送らない対象: ${grouped.skipped.map((item) => item.name).join(" / ")}`,
      createdAt: state.bulkCreatedAt,
    });
  }
  bulkCommandTargetIds = state.bulkTargetIds;
  persistBulkCommandTab(tab);
  showBulkCommandTab(tab, "bulk-command-tab-opened");
  logEvent("info", "bulk-command-tab-ready", {
    tabId: tab.id,
    targetIds: state.bulkTargetIds,
    targetNames: names,
    skipped: grouped.skipped,
  });
}

function parseJsonResponseText(text) {
  if (!text) {
    return {};
  }
  try {
    return JSON.parse(text);
  } catch {
    return { raw: text };
  }
}

function shortBulkReplyPreview(result, limit = 30) {
  const text = String(result?.assistantMessage?.text || result?.error || "").replace(/\s+/g, " ").trim();
  if (!text) {
    return "";
  }
  const chars = [...text];
  return chars.length > limit ? `${chars.slice(0, limit).join("")}...` : text;
}

function bulkResultLine(result) {
  const name = result?.meaning || result?.nodeId || "名前のないポワン";
  const status = result?.status || "unknown";
  const preview = shortBulkReplyPreview(result);
  return preview ? `${name}: ${status} / ${preview}` : `${name}: ${status}`;
}

async function sendBulkCommandToSelected() {
  if (bulkCommandSending) {
    logEvent("warn", "bulk-command-submit-ignored-sending", { targetIds: bulkCommandTargetIds });
    return;
  }
  const bulkState = activeBulkCommandState();
  if (!bulkState) {
    logEvent("warn", "bulk-command-submit-no-active-tab", { targetIds: bulkCommandTargetIds });
    return;
  }
  const inputElement = conversationInput;
  const targetIds = bulkState.bulkTargetIds || [];
  const instruction = (inputElement?.value || "").trim();
  if (!instruction) {
    logEvent("warn", "bulk-command-submit-empty", { targetIds });
    return;
  }
  const grouped = bulkCommandGroupsForIds(targetIds);
  const eligibleCount = grouped.groups.reduce((count, group) => count + group.nodes.length, 0);
  if (!eligibleCount) {
    logEvent("warn", "bulk-command-submit-no-targets", {
      targetIds,
      skipped: grouped.skipped,
    });
    return;
  }
  bulkCommandSending = true;
  setConversationSending(true);
  inputElement.value = "";
  bulkState.draft = "";
  appendBulkCommandMessage("user", instruction, { forceFollow: true });
  appendBulkCommandMessage("system", `一括指示を開始: ${eligibleCount}件`, { forceFollow: true });
  saveState.textContent = "bulk sending";
  logEvent("info", "bulk-command-submit-start", {
    targetIds: grouped.nodes.map((node) => node.id),
    eligibleCount,
    skipped: grouped.skipped,
    groupCount: grouped.groups.length,
    instructionLength: instruction.length,
    includeMeaningTree: Boolean(conversationTreeContextInput?.checked),
  });
  const allResults = [];
  try {
    for (const group of grouped.groups) {
      const payload = {
        project: projectName,
        file: documentName,
        instruction: "",
        bulkHistoryId: bulkState.bulkHistoryId || "",
        instructions: group.nodes.map((node) => ({
          childId: node.id,
          title: node.title || "",
          body: node.body || "",
          instruction,
        })),
        includeMeaningTree: Boolean(conversationTreeContextInput?.checked),
      };
      if (bulkState) {
        appendBulkCommandMessage("system", `送信開始: ${meaningName(group.parent)} -> ${group.nodes.map(meaningName).join(" / ")}`);
      }
      logEvent("info", "bulk-command-group-fetch-start", {
        parentId: group.parent.id,
        parentName: meaningName(group.parent),
        childIds: group.nodes.map((node) => node.id),
        childNames: group.nodes.map(meaningName),
        instructionLength: instruction.length,
      });
      const response = await fetch(
        `/api/ai/powans/${encodeURIComponent(group.parent.id)}/actions/command-children`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        },
      );
      const responseText = await response.text();
      const data = parseJsonResponseText(responseText);
      if (!response.ok) {
        logEvent("error", "bulk-command-group-fetch-failed", {
          parentId: group.parent.id,
          status: response.status,
          response: data,
        });
        throw new Error(data?.detail || data?.error || `一括指示に失敗した: ${response.status}`);
      }
      const results = data.results || [];
      allResults.push(...results);
      if (bulkState) {
        const groupLabel = data.detached ? "指示受付" : "送信完了";
        appendBulkCommandMessage(
          "system",
          `${groupLabel}: ${meaningName(group.parent)}\n${results.map(bulkResultLine).join("\n")}`,
        );
      }
      logEvent("info", "bulk-command-group-fetch-complete", {
        parentId: group.parent.id,
        parentName: meaningName(group.parent),
        detached: Boolean(data.detached),
        resultCount: results.length,
        results: results.map((result) => ({
          nodeId: result.nodeId,
          meaning: result.meaning,
          status: result.status,
          conversationId: result.conversationId || null,
          assistantMessageId: result.assistantMessage?.id || null,
          replyPreview: shortBulkReplyPreview(result),
          error: result.error || "",
        })),
      });
    }
    const detached = allResults.some((result) => result.status === "accepted");
    appendBulkCommandMessage(
      "assistant",
      detached
        ? `一括指示を子ポワンへ渡したよ。\n親側の送信はここで完了。${allResults.length}件が受け取った。`
        : `一括指示が完了したよ。\n${allResults.length}件の結果を受け取った。`,
      { forceFollow: true },
    );
    saveState.textContent = "bulk done";
    logEvent("info", "bulk-command-submit-complete", {
      detached,
      resultCount: allResults.length,
      results: allResults.map((result) => ({
        nodeId: result.nodeId,
        status: result.status,
        conversationId: result.conversationId || null,
      })),
    });
    const activeNodeNeedsRefresh = conversationNodeId && targetIds.includes(conversationNodeId);
    if (activeNodeNeedsRefresh) {
      await loadConversationMessages(conversationNodeId);
      logEvent("debug", "bulk-command-active-conversation-refreshed", { nodeId: conversationNodeId });
    }
  } catch (error) {
    appendBulkCommandMessage("system", `一括指示エラー: ${error.message}`, { forceFollow: true });
    saveState.textContent = "bulk error";
    logEvent("error", "bulk-command-submit-error", {
      targetIds,
      message: error.message,
      error: clientErrorLogPayload(error),
    });
    console.error(error);
  } finally {
    bulkCommandSending = false;
    setConversationSending(false);
    persistBulkCommandTab(activeConversationTab());
    if (activePanelTab === "history") {
      refreshConversationHistory({ reason: "bulk-command-refresh-history-after-send" });
    }
  }
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

function conversationRoleLabel(role) {
  if (role === "assistant" || role === "ai") {
    return "ポワン";
  }
  if (role === "user") {
    return "ユーザー";
  }
  return "システム";
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

function nextConversationTabId() {
  conversationTabSerial += 1;
  return `tab-${Date.now().toString(36)}-${conversationTabSerial}`;
}

function conversationTabIndex(tabId) {
  return conversationTabs.findIndex((tab) => tab.id === tabId);
}

function activeConversationTab() {
  return conversationTabs.find((tab) => tab.id === activeConversationTabId) || null;
}

function conversationTabState(tabId) {
  const current = conversationTabStates.get(tabId) || {};
  conversationTabStates.set(tabId, current);
  return current;
}

function conversationTabForNode(nodeId) {
  return conversationTabs.find((tab) => !isBulkCommandTab(tab) && tab.nodeId === nodeId) || null;
}

function clearConversationTabAttention(tabId, reason = "conversation-tab-attention-clear") {
  const state = conversationTabStates.get(tabId);
  if (!state?.attention) {
    return;
  }
  delete state.attention;
  logEvent("debug", reason, { tabId });
}

function flashConversationTabOpening(tabId, nodeId, reason = "conversation-tab-open-flash") {
  if (!tabId || !nodeId) {
    return;
  }
  const state = conversationTabState(tabId);
  const until = Date.now() + 1100;
  state.openFlash = { nodeId, until };
  renderConversationTabs();
  window.setTimeout(() => {
    const latest = conversationTabStates.get(tabId);
    if (!latest?.openFlash || Number(latest.openFlash.until || 0) > Date.now()) {
      return;
    }
    delete latest.openFlash;
    renderConversationTabs();
  }, 1150);
  logEvent("debug", reason, { tabId, nodeId });
}

function markConversationTabAttention(tabId, nodeId, kind = "reply", text = "", detailId = null) {
  if (!tabId || !nodeId) {
    return;
  }
  const state = conversationTabState(tabId);
  state.attention = {
    nodeId,
    kind,
    text: text || (kind === "running" ? "作業中" : "返事あり"),
    detailId,
    updatedAt: historyIsoNow(),
  };
  renderConversationTabs();
  logEvent("debug", "conversation-tab-attention-marked", {
    tabId,
    nodeId,
    kind,
    detailId,
  });
}

function openConversationTabForNode(nodeId, { reason = "conversation-tab-open-for-node" } = {}) {
  const node = nodeById(nodeId);
  if (!node) {
    logEvent("warn", "conversation-tab-open-missing-node", { nodeId, reason });
    return null;
  }
  const existing = conversationTabForNode(node.id);
  const tabMode = existing ? "activate" : "new";
  const tabId = existing?.id || null;
  openConversationPanel(node.id, {
    tabMode,
    tabId,
    reason: existing ? `${reason}-existing-tab` : `${reason}-new-tab`,
  });
  const opened = existing || activeConversationTab();
  if (opened?.id) {
    clearConversationTabAttention(opened.id, "conversation-tab-attention-cleared-open");
    flashConversationTabOpening(opened.id, node.id, "conversation-tab-opened-flash");
  }
  return opened || null;
}

function ensureConversationTabForNode(nodeId, reason = "conversation-tab-ensure") {
  const node = nodeById(nodeId);
  if (!node) {
    return null;
  }
  let tab = conversationTabForNode(nodeId);
  if (!tab) {
    tab = createConversationTab(nodeId, reason);
  }
  const state = conversationTabState(tab.id);
  state.nodeId = nodeId;
  if (conversationPanel?.hidden) {
    conversationPanel.hidden = false;
    setConversationPanelCollapsed(false, "conversation-attention-panel-open");
  }
  return tab;
}

function cloneConversationAttachments(attachments) {
  return Array.isArray(attachments)
    ? attachments.map((attachment) => ({ ...attachment }))
    : [];
}

function createConversationTab(nodeId = null, reason = "conversation-tab-created", options = {}) {
  const tab = {
    id: nextConversationTabId(),
    nodeId,
    kind: options.kind || "powan",
    openedAt: Date.now(),
  };
  conversationTabs.push(tab);
  conversationTabStates.set(tab.id, {});
  logEvent("debug", reason, { tabId: tab.id, nodeId, kind: tab.kind, name: conversationTabLabel(tab) });
  return tab;
}

function rememberConversationTabState(tabId = activeConversationTabId) {
  if (!tabId) {
    return;
  }
  const tab = conversationTabs.find((item) => item.id === tabId);
  if (!tab) {
    return;
  }
  const state = conversationTabState(tabId);
  state.nodeId = tab.nodeId || null;
  state.draft = conversationInput?.value || "";
  state.attachments = cloneConversationAttachments(conversationPendingAttachments);
  state.scrollTop = conversationLog ? conversationLog.scrollTop : 0;
  state.activeSessionId = normalizeConversationId(conversationActiveSessionId);
  state.viewingSessionId = normalizeConversationId(conversationViewingSessionId);
  state.viewingAllSessions = Boolean(conversationViewingAllSessions);
  state.autoFollow = Boolean(conversationAutoFollow);
}

function rememberConversationDraft(tabId = activeConversationTabId) {
  if (!tabId) {
    return;
  }
  const state = conversationTabState(tabId);
  state.draft = conversationInput?.value || "";
  state.attachments = cloneConversationAttachments(conversationPendingAttachments);
}

function queuedConversationLabel(send) {
  const target = send?.nodeId ? nodeById(send.nodeId) : null;
  const name = target ? shortConversationTargetName(target) : "ポワン";
  const text = shortWorkText(send?.text || (send?.attachments?.length ? "添付を渡す" : ""), 28);
  return text ? `${name}へ送信待ち / ${text}` : `${name}へ送信待ち`;
}

function conversationRequestKey(nodeId) {
  return String(nodeId || "");
}

function conversationRequestForNode(nodeId) {
  const key = conversationRequestKey(nodeId);
  return key ? conversationActiveRequests.get(key) || null : null;
}

function conversationRequestVisibleInView(request, tabId = activeConversationTabId, nodeId = conversationNodeId) {
  if (!request || !tabId || !nodeId) {
    return false;
  }
  if (request.tabId !== tabId || request.nodeId !== nodeId) {
    return false;
  }
  const requestConversationId = normalizeConversationId(request.conversationId);
  const viewingConversationId = normalizeConversationId(conversationViewingSessionId || conversationActiveSessionId);
  return !requestConversationId || !viewingConversationId || requestConversationId === viewingConversationId;
}

function visibleConversationRequest(tabId = activeConversationTabId, nodeId = conversationNodeId) {
  const request = conversationRequestForNode(nodeId);
  return conversationRequestVisibleInView(request, tabId, nodeId) ? request : null;
}

function syncVisibleConversationRequestState() {
  const request = visibleConversationRequest();
  conversationRequestAbortController = request?.controller || null;
  conversationRequestNodeId = request?.nodeId || null;
  conversationRequestTabId = request?.tabId || null;
  conversationRequestConversationId = request?.conversationId || null;
  conversationRequestWaitingText = request?.waitingText || "";
  conversationPendingMessage = request?.pendingMessage || null;
  conversationCancelRequested = Boolean(request?.cancelRequested);
  return request;
}

function setConversationTabRunningStatus(tabId, nodeId, text, conversationId = null) {
  if (!tabId || !nodeId) {
    return;
  }
  const state = conversationTabState(tabId);
  state.runningStatus = {
    nodeId,
    conversationId: normalizeConversationId(conversationId),
    text: text || "処理中",
    updatedAt: historyIsoNow(),
  };
}

function clearConversationTabRunningStatus(tabId, nodeId = null) {
  if (!tabId) {
    return;
  }
  const state = conversationTabStates.get(tabId);
  if (!state?.runningStatus) {
    return;
  }
  if (nodeId && state.runningStatus.nodeId !== nodeId) {
    return;
  }
  delete state.runningStatus;
}

function rememberConversationRequestWaitingText(text, request = visibleConversationRequest()) {
  if (!request) {
    return;
  }
  request.waitingText = text || request.waitingText || "処理中";
  setConversationTabRunningStatus(
    request.tabId,
    request.nodeId,
    request.waitingText,
    request.conversationId,
  );
  if (conversationRequestVisibleInView(request)) {
    syncVisibleConversationRequestState();
  }
}

function conversationRequestMatchesView(tabId, nodeId) {
  return Boolean(visibleConversationRequest(tabId, nodeId));
}

function rememberRunningPowanRun(run) {
  if (!run?.powanId) {
    return;
  }
  runningPowanRuns.set(run.powanId, run);
  schedulePowanFaceRefresh([run.powanId], "running-powan-run-remembered");
}

function dbRunningConversationText(run, nodeId) {
  const node = nodeById(nodeId || run?.powanId);
  const name = node ? shortConversationTargetName(node) : "ポワン";
  const task = shortWorkText(run?.userText || "");
  return task ? `${name} / 作業中 / ${task}` : `${name} / 作業中`;
}

function setPendingConversationMessage(message, text) {
  if (!message?.isConnected) {
    return null;
  }
  setConversationMessageText(message, "system", text);
  message.classList.add("pending");
  setInputWaitingMessageAnimation(message, text);
  return message;
}

function ensureConversationPendingMessage(text, key = "") {
  if (conversationPendingMessage?.isConnected) {
    conversationPendingMessage.dataset.pendingKey = key || conversationPendingMessage.dataset.pendingKey || "";
    return setPendingConversationMessage(conversationPendingMessage, text);
  }
  const pending = appendConversationMessage("system", text, { forceFollow: true });
  pending.dataset.pendingKey = key || "";
  conversationPendingMessage = setPendingConversationMessage(pending, text);
  return conversationPendingMessage;
}

function notifyConversationRunStarted(run, reason = "conversation-run-started") {
  const nodeId = run?.powanId;
  if (!nodeId || conversationRunningNotifiedRunIds.has(Number(run.id))) {
    return;
  }
  const tab = ensureConversationTabForNode(nodeId, "conversation-running-tab-created");
  if (!tab) {
    return;
  }
  conversationRunningNotifiedRunIds.add(Number(run.id));
  const state = conversationTabState(tab.id);
  state.activeSessionId = normalizeConversationId(run.conversationId);
  state.viewingSessionId = normalizeConversationId(run.conversationId);
  state.viewingAllSessions = false;
  state.autoFollow = true;
  setConversationTabRunningStatus(tab.id, nodeId, dbRunningConversationText(run, nodeId), run.conversationId);
  markConversationTabAttention(tab.id, nodeId, "running", dbRunningConversationText(run, nodeId), run.id);
  if (!activeConversationTabId) {
    openConversationPanel(nodeId, { tabMode: "activate", tabId: tab.id, reason: "conversation-running-auto-open" });
  } else {
    renderConversationTabs();
  }
  logEvent("info", "conversation-running-tab-notified", {
    nodeId,
    tabId: tab.id,
    runId: run.id,
    reason,
  });
}

function notifyConversationRunFinished(nodeId, reason = "conversation-run-finished") {
  const tab = conversationTabForNode(nodeId);
  if (!tab) {
    return;
  }
  clearConversationTabRunningStatus(tab.id, nodeId);
  if (activeConversationTabId === tab.id && conversationNodeId === nodeId) {
    return;
  }
  markConversationTabAttention(tab.id, nodeId, "reply", "返事が届きました", null);
  logEvent("info", "conversation-reply-tab-notified", { nodeId, tabId: tab.id, reason });
}

function restoreConversationTransientStatus(tabId, nodeId, activeRun = null) {
  if (!conversationLog || !tabId || !nodeId) {
    return;
  }
  if (conversationPendingMessage && !conversationPendingMessage.isConnected) {
    conversationPendingMessage = null;
  }
  const request = visibleConversationRequest(tabId, nodeId);
  if (request) {
    request.soundOwner = request.soundOwner || `conversation-request-${request.id}`;
    const state = conversationTabState(tabId);
    const text = state.runningStatus?.text || request.waitingText || "処理中";
    const pending = request.pendingMessage?.isConnected
      ? setPendingConversationMessage(request.pendingMessage, text)
      : ensureConversationPendingMessage(text, `request:${request.id}`);
    request.pendingMessage = pending;
    rememberConversationRequestWaitingText(text, request);
    syncVisibleConversationRequestState();
    startInputWaitingSound(request.soundOwner);
    startConversationWorkPolling(conversationWorkEventSequence);
    return;
  }
  const dbRun = activeRun || (conversationCanEditSession() ? runningPowanRuns.get(nodeId) : null) || null;
  if (dbRun?.status === "running") {
    rememberRunningPowanRun(dbRun);
    const text = dbRunningConversationText(dbRun, nodeId);
    ensureConversationPendingMessage(text, `run:${dbRun.id || ""}`);
    setConversationTabRunningStatus(tabId, nodeId, text, dbRun.conversationId);
  }
  if (conversationCanEditSession()) {
    for (const send of conversationQueuedSends) {
      if (send.tabId !== tabId || send.nodeId !== nodeId) {
        continue;
      }
      send.statusMessage = appendConversationMessage("system", queuedConversationLabel(send), { forceFollow: true });
    }
  }
}

function queueConversationSend(send) {
  conversationQueuedSends.push(send);
  if (activeConversationTabId === send.tabId && conversationNodeId === send.nodeId) {
    send.statusMessage = appendConversationMessage("system", queuedConversationLabel(send), { forceFollow: true });
  }
  conversationInput.value = "";
  conversationPendingAttachments = [];
  renderConversationAttachmentTray();
  rememberConversationDraft(activeConversationTabId);
  setConversationSending(conversationSending);
  logEvent("info", "conversation-send-queued", {
    nodeId: send.nodeId,
    tabId: send.tabId,
    queueLength: conversationQueuedSends.length,
    length: (send.text || "").length,
    attachmentCount: send.attachments?.length || 0,
  });
}

function sendNextQueuedConversation(reason = "conversation-queue-next", nodeId = null) {
  if (!conversationQueuedSends.length) {
    return;
  }
  const index = conversationQueuedSends.findIndex((send) => {
    if (nodeId && send.nodeId !== nodeId) {
      return false;
    }
    return !conversationRequestForNode(send.nodeId);
  });
  if (index < 0) {
    return;
  }
  const [next] = conversationQueuedSends.splice(index, 1);
  window.setTimeout(() => {
    sendConversation({ queuedSend: next }).catch((error) => {
      logEvent("error", "conversation-queued-send-error", {
        nodeId: next?.nodeId || null,
        message: error.message,
        reason,
      });
      console.error(error);
      sendNextQueuedConversation("conversation-queue-error-next", next?.nodeId || null);
    });
  }, 0);
}

async function requestRunningAgentRuns() {
  const response = await fetch(
    `/api/agent-runs/running?project=${encodeURIComponent(projectName)}&file=${encodeURIComponent(documentName)}`,
  );
  if (!response.ok) {
    throw new Error(`running runs load failed: ${response.status}`);
  }
  return response.json();
}

function applyRunningAgentRuns(runs = [], reason = "running-runs-refresh") {
  const previousIds = new Set(runningPowanRuns.keys());
  const nextMap = new Map();
  for (const run of runs || []) {
    if (run?.powanId && run.status === "running") {
      nextMap.set(run.powanId, run);
    }
  }
  runningPowanRuns = nextMap;
  for (const run of nextMap.values()) {
    if (!previousIds.has(run.powanId)) {
      notifyConversationRunStarted(run, reason);
    }
  }
  const changedIds = new Set([...previousIds, ...runningPowanRuns.keys()]);
  schedulePowanFaceRefresh([...changedIds], reason);
  for (const nodeId of previousIds) {
    if (!nextMap.has(nodeId)) {
      notifyConversationRunFinished(nodeId, reason);
    }
  }
  const activeNodeWasRunning = conversationNodeId && previousIds.has(conversationNodeId);
  const activeNodeIsRunning = conversationNodeId && runningPowanRuns.has(conversationNodeId);
  if (
    conversationNodeId
      && !conversationRequestForNode(conversationNodeId)
      && !activeNodeIsRunning
      && activeNodeWasRunning
      && !runningPowanConversationReloading
  ) {
    runningPowanConversationReloading = true;
    loadConversationMessages(conversationNodeId).finally(() => {
      runningPowanConversationReloading = false;
    });
  } else if (
    conversationNodeId
      && activeNodeIsRunning
      && !conversationRequestForNode(conversationNodeId)
      && !conversationPendingMessage?.isConnected
  ) {
    restoreConversationTransientStatus(activeConversationTabId, conversationNodeId, runningPowanRuns.get(conversationNodeId));
  }
}

async function refreshRunningAgentRuns(reason = "running-runs-refresh") {
  if (!projectName || !documentName) {
    return;
  }
  try {
    const data = await requestRunningAgentRuns();
    applyRunningAgentRuns(data.runs || [], reason);
  } catch (error) {
    logEvent("debug", "running-runs-refresh-error", { message: error.message, reason });
  }
}

function startRunningAgentRunRefresh() {
  if (runningPowanRefreshTimer) {
    window.clearInterval(runningPowanRefreshTimer);
  }
  refreshRunningAgentRuns("running-runs-refresh-start");
  runningPowanRefreshTimer = window.setInterval(() => {
    refreshRunningAgentRuns("running-runs-refresh-tick");
  }, 1500);
}

function conversationTabLabel(tab) {
  if (isBulkCommandTab(tab)) {
    return "一括送信";
  }
  const node = tab?.nodeId ? nodeById(tab.nodeId) : null;
  return node ? meaningName(node) : "新規タブ";
}

function cleanupConversationTabs() {
  conversationTabs = conversationTabs.filter((tab) => isBulkCommandTab(tab) || !tab.nodeId || nodeById(tab.nodeId));
  const ids = new Set(conversationTabs.map((tab) => tab.id));
  for (const tabId of [...conversationTabStates.keys()]) {
    if (!ids.has(tabId)) {
      conversationTabStates.delete(tabId);
    }
  }
  if (activeConversationTabId && !ids.has(activeConversationTabId)) {
    activeConversationTabId = conversationTabs[0]?.id || null;
  }
}

function renderConversationTabs() {
  if (!conversationTabBar) {
    return;
  }
  cleanupConversationTabs();
  conversationTabBar.innerHTML = "";
  conversationTabBar.hidden = Boolean(conversationPanel?.hidden);
  for (const tab of conversationTabs) {
    const state = conversationTabStates.get(tab.id) || {};
    const openFlashActive = Boolean(state.openFlash && Number(state.openFlash.until || 0) > Date.now());
    if (state.openFlash && !openFlashActive) {
      delete state.openFlash;
    }
    const tabRunning = Boolean(tab.nodeId && runningPowanRuns.has(tab.nodeId)) || Boolean(state.runningStatus);
    const tabDisconnected = Boolean(tab.nodeId && powanCodexDisconnected(tab.nodeId));
    const tabAttention = Boolean(state.attention);
    const item = document.createElement("div");
    item.className = "conversation-tab";
    item.classList.toggle("active", tab.id === activeConversationTabId);
    item.classList.toggle("blank", !tab.nodeId);
    item.classList.toggle("bulk", isBulkCommandTab(tab));
    item.classList.toggle("running", tabRunning);
    item.classList.toggle("disconnected", tabDisconnected);
    item.classList.toggle("attention", tabAttention);
    item.classList.toggle("reply-ready", tabAttention && state.attention?.kind === "reply");
    item.classList.toggle("opening", openFlashActive);
    item.role = "tab";
    item.ariaSelected = tab.id === activeConversationTabId ? "true" : "false";
    item.title = state.attention?.text || (tabRunning ? "作業中" : tabDisconnected ? powanCodexDisconnectedMessage(tab.nodeId) : conversationTabLabel(tab));
    const label = document.createElement("button");
    label.type = "button";
    label.className = "conversation-tab-label";
    const marker = tabRunning ? "🫨 " : tabDisconnected ? "😵 " : tabAttention ? "● " : "";
    label.textContent = `${marker}${conversationTabLabel(tab)}`;
    label.addEventListener("click", () => switchConversationTab(tab.id));
    const close = document.createElement("button");
    close.type = "button";
    close.className = "conversation-tab-close";
    close.textContent = "×";
    close.title = "タブを閉じる";
    close.addEventListener("click", (event) => {
      event.stopPropagation();
      closeConversationTab(tab.id);
    });
    item.append(label, close);
    conversationTabBar.appendChild(item);
  }
  const addButton = document.createElement("button");
  addButton.type = "button";
  addButton.className = "conversation-tab-add";
  addButton.textContent = "+";
  addButton.title = "新規タブ";
  addButton.addEventListener("click", () => openBlankConversationTab());
  conversationTabBar.appendChild(addButton);
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
  conversationNodeName.textContent = "新規タブ";
  renderConversationAttachmentTray();
  updateConversationSessionMode();
  renderConversationTabs();
}

function restoreConversationDraftState(tabId) {
  const state = conversationTabStates.get(tabId) || {};
  conversationInput.value = state.draft || "";
  conversationPendingAttachments = cloneConversationAttachments(state.attachments);
  renderConversationAttachmentTray();
  return state;
}

async function restoreConversationScroll(tabId, nodeId, state) {
  if (!state || !conversationLog || activeConversationTabId !== tabId || conversationNodeId !== nodeId) {
    return;
  }
  await Promise.resolve();
  if (activeConversationTabId === tabId && conversationNodeId === nodeId && Number.isFinite(Number(state.scrollTop))) {
    conversationLog.scrollTop = Number(state.scrollTop);
    conversationAutoFollow = Boolean(state.autoFollow);
  }
}

function showBlankConversationTab(tab, reason = "conversation-blank-tab") {
  if (activeConversationTabId && activeConversationTabId !== tab.id) {
    rememberConversationTabState(activeConversationTabId);
  }
  activeConversationTabId = tab.id;
  tab.nodeId = null;
  conversationPanel.hidden = false;
  setConversationPanelCollapsed(false, `${reason}-expand`);
  clearConversationView();
  const state = restoreConversationDraftState(tab.id);
  if (Number.isFinite(Number(state.scrollTop))) {
    conversationLog.scrollTop = Number(state.scrollTop);
  }
  focusConversationInputIfOpen();
  logEvent("debug", reason, { tabId: tab.id });
}

function openBlankConversationTab(reason = "conversation-new-blank-tab") {
  if (activeConversationTabId) {
    rememberConversationTabState(activeConversationTabId);
  }
  const tab = createConversationTab(null, reason);
  showBlankConversationTab(tab, reason);
}

function switchConversationTab(tabId, reason = "conversation-tab-switch") {
  const tab = conversationTabs.find((item) => item.id === tabId);
  if (!tab) {
    return;
  }
  if (activeConversationTabId === tab.id && conversationPanel && !conversationPanel.hidden) {
    clearConversationTabAttention(tab.id, "conversation-tab-attention-cleared-active-click");
    expandConversationPanel(reason);
    renderConversationTabs();
    return;
  }
  clearConversationTabAttention(tab.id, "conversation-tab-attention-cleared-switch");
  if (!tab.nodeId) {
    if (isBulkCommandTab(tab)) {
      showBulkCommandTab(tab, reason);
      return;
    }
    showBlankConversationTab(tab, reason);
    return;
  }
  openConversationPanel(tab.nodeId, { tabMode: "activate", tabId: tab.id, reason });
}

function closeConversationTab(tabId, reason = "conversation-tab-close") {
  const index = conversationTabIndex(tabId);
  if (index < 0) {
    return;
  }
  const wasActive = activeConversationTabId === tabId;
  if (wasActive) {
    rememberConversationTabState(tabId);
  }
  const [closed] = conversationTabs.splice(index, 1);
  conversationTabStates.delete(tabId);
  logEvent("debug", reason, { tabId, nodeId: closed?.nodeId || null, wasActive, remaining: conversationTabs.length });
  if (wasActive) {
    const next = conversationTabs[Math.min(index, conversationTabs.length - 1)];
    activeConversationTabId = null;
    conversationNodeId = null;
    if (next) {
      switchConversationTab(next.id, "conversation-tab-close-switch-next");
    } else {
      clearConversationView();
      conversationPanel.hidden = true;
    }
  } else {
    renderConversationTabs();
  }
}

function conversationCanEditSession() {
  if (isBulkCommandTab(activeConversationTab())) {
    return true;
  }
  if (!conversationNodeId) {
    return false;
  }
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
    conversationInput.placeholder = isBulkCommandTab(activeConversationTab())
      ? "選択したポワンに一括で話しかける"
      : !conversationNodeId
      ? "ポワンを選ぶ"
      : canEdit
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
      logEvent("debug", "conversation-sessions-load-skipped", {
        message: `sessions load skipped: node changed ${nodeId} -> ${conversationNodeId || "none"}`,
        nodeId,
        currentNodeId: conversationNodeId,
      });
      return;
    }
    conversationSessionList = data.sessions || [];
    conversationActiveSessionId = normalizeConversationId(data.activeConversationId);
    renderConversationSessions(conversationSessionList, selectedId);
    renderConversationTabs();
    updateConversationSessionMode();
    logEvent("debug", "conversation-sessions-load-complete", {
      message: `sessions loaded: ${nodeId}, ${(data.sessions || []).length} sessions`,
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
      logEvent("debug", "conversation-load-skipped", {
        message: `conversation load skipped: stale view for ${nodeId}`,
        nodeId,
        currentNodeId: conversationNodeId,
      });
      return;
    }
    conversationActiveSessionId = normalizeConversationId(data.conversationId);
    conversationViewingSessionId = normalizeConversationId(data.conversationId);
    conversationViewingAllSessions = false;
    conversationLog.innerHTML = "";
    for (const message of data.messages || []) {
      appendConversationMessage(message.role, message.text || "");
    }
    if (data.activeRun) {
      rememberRunningPowanRun(data.activeRun);
    }
    restoreConversationTransientStatus(activeConversationTabId, nodeId, data.activeRun);
    renderConversationTabs();
    refreshConversationSessions(nodeId, data.conversationId);
    logEvent("debug", "conversation-load-complete", {
      message: `conversation loaded: ${nodeId}, ${(data.messages || []).length} messages`,
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
      logEvent("debug", "conversation-session-load-skipped", {
        message: `session load skipped: stale view for ${nodeId}`,
        nodeId,
        conversationId,
        currentNodeId: conversationNodeId,
      });
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
    if (data.activeRun) {
      rememberRunningPowanRun(data.activeRun);
    }
    restoreConversationTransientStatus(activeConversationTabId, nodeId, data.activeRun);
    if (conversationSessionSelect) {
      conversationSessionSelect.value = String(data.conversationId);
    }
    refreshConversationSessions(nodeId, data.conversationId);
    renderConversationTabs();
    updateConversationSessionMode();
    logEvent("debug", "conversation-session-load-complete", {
      message: `session loaded: ${nodeId}/${data.conversationId}, ${(data.messages || []).length} messages`,
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
      logEvent("debug", "conversation-all-sessions-load-skipped", {
        message: `all sessions load skipped: stale view for ${nodeId}`,
        nodeId,
        currentNodeId: conversationNodeId,
      });
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
        logEvent("debug", "conversation-all-sessions-load-skipped", {
          message: `all sessions load stopped: node changed while rendering ${nodeId}`,
          nodeId,
          currentNodeId: conversationNodeId,
        });
        return;
      }
      appendConversationMessage("system", conversationSessionLabel(session));
      const payload = await requestConversationSessionMessages(nodeId, session.id);
      if (conversationNodeId !== nodeId || serial !== conversationLoadSerial) {
        logEvent("debug", "conversation-all-sessions-load-skipped", {
          message: `all sessions load stopped: node changed after session ${session.id}`,
          nodeId,
          currentNodeId: conversationNodeId,
        });
        return;
      }
      for (const message of payload.messages || []) {
        appendConversationMessage(message.role, message.text || "");
      }
    }
    updateConversationSessionMode();
    conversationLog.scrollTop = 0;
    logEvent("debug", "conversation-all-sessions-load-complete", {
      message: `all sessions loaded: ${nodeId}, ${orderedSessions.length} sessions`,
      nodeId,
      activeConversationId: conversationActiveSessionId,
      count: orderedSessions.length,
    });
  } catch (error) {
    appendConversationMessage("system", `全会話を開けなかった: ${error.message}`, { forceFollow: true });
    logEvent("error", "conversation-all-sessions-load-error", { nodeId, message: error.message });
  }
}

async function requestPowanCodexReply(
  nodeId,
  text,
  { signal = null, includeMeaningTree = false, includeDirectChildCode = false, attachments = [] } = {},
) {
  const response = await fetch(
    `/api/conversations/${encodeURIComponent(nodeId)}/codex?project=${encodeURIComponent(projectName)}&file=${encodeURIComponent(documentName)}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, includeMeaningTree, includeDirectChildCode, attachments }),
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
    message: `reply received: ${nodeId}/${data.conversationId}, ${(data.assistantMessage?.text || "").length} chars`,
    nodeId,
    conversationId: data.conversationId,
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
  applyTitleStyleSettings(data);
  applyArrangeSettings(data);
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
    appSettings.restartVisibleConsole = Boolean(data.restartVisibleConsole);
    appSettings.autoSummaryEnabled = data.autoSummaryEnabled !== false;
    appSettings.autoSummaryTurns = normalizeConversationAutoSummaryTurns(data.autoSummaryTurns);
    applyTitleStyleSettings(data);
    applyArrangeSettings(data);
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
      restartVisibleConsole: appSettings.restartVisibleConsole,
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
  if (conversationSoundIsPlaying && !audio.paused) {
    return;
  }
  conversationSoundIsPlaying = true;
  if (!audio.paused || audio.ended) {
    audio.currentTime = 0;
  }
  audio.play().catch((error) => {
    conversationSoundIsPlaying = false;
    logEvent("warn", "conversation-sound-play-error", { message: error.message, sound: appSettings.conversationSound });
  });
}

function startInputWaitingSound(owner = "") {
  const url = inputSoundUrl();
  if (!url || appSettings.inputSoundVolume <= 0) {
    return;
  }
  const audio = ensureInputWaitingAudio(url);
  inputWaitingSoundOwner = owner || inputWaitingSoundOwner || "conversation";
  if (inputSoundIsPlaying && !audio.paused) {
    return;
  }
  inputSoundIsPlaying = true;
  if (!audio.paused || audio.ended) {
    audio.currentTime = 0;
  }
  audio.play().catch((error) => {
    inputSoundIsPlaying = false;
    inputWaitingSoundOwner = "";
    logEvent("warn", "input-sound-play-error", { message: error.message, sound: appSettings.inputSound });
  });
}

function resumeActiveConversationAudio(reason = "conversation-audio-resume") {
  if (visibleConversationRequest() && inputSoundIsPlaying && inputWaitingAudio?.paused) {
    inputWaitingAudio.play().catch((error) => {
      inputSoundIsPlaying = false;
      logEvent("warn", "input-sound-resume-error", { message: error.message, reason, sound: appSettings.inputSound });
    });
  }
  if (conversationTypingNodeId && conversationSoundIsPlaying && conversationChunkAudio?.paused) {
    conversationChunkAudio.play().catch((error) => {
      conversationSoundIsPlaying = false;
      logEvent("warn", "conversation-sound-resume-error", { message: error.message, reason, sound: appSettings.conversationSound });
    });
  }
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

function stopInputWaitingSound(reason = "input-sound-stop", owner = "") {
  if (!inputWaitingAudio && !inputSoundIsPlaying) {
    return;
  }
  if (owner && inputWaitingSoundOwner && inputWaitingSoundOwner !== owner) {
    logEvent("debug", "input-sound-stop-ignored-owner-mismatch", {
      reason,
      owner,
      currentOwner: inputWaitingSoundOwner,
    });
    return;
  }
  const audio = inputWaitingAudio;
  inputSoundIsPlaying = false;
  inputWaitingSoundOwner = "";
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
  applyTitleStyleSettings(data);
  applyArrangeSettings(data);
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
  applyTitleStyleSettings(data);
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
  applyTitleStyleSettings(data);
  applyArrangeSettings(data);
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
  applyTitleStyleSettings(data);
  syncSettingsInputs();
  saveStoredSettings();
  logEvent("info", "set-input-volume-saved", { volume: appSettings.inputSoundVolume });
}

var titleStyleSaveTimer = null;

async function saveTitleStyleSettings(reason = "title-style-settings") {
  const response = await fetch("/api/settings/title-style", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(titleStylePayload()),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "title style save failed" }));
    throw new Error(error.detail || "title style save failed");
  }
  const data = await response.json();
  applyTitleStyleSettings(data);
  syncSettingsInputs();
  saveStoredSettings();
  logEvent("info", "title-style-settings-saved", {
    message: "title style settings saved",
    reason,
    ...titleStylePayload(),
  });
}

function updateTitleStyleSettings(reason = "title-style-settings-change", options = {}) {
  setTitleStyleFromInputs(reason);
  if (titleStyleSaveTimer) {
    window.clearTimeout(titleStyleSaveTimer);
    titleStyleSaveTimer = null;
  }
  const delay = Number.isFinite(Number(options.delayMs)) ? Number(options.delayMs) : 220;
  titleStyleSaveTimer = window.setTimeout(() => {
    titleStyleSaveTimer = null;
    saveTitleStyleSettings(reason).catch((error) => {
      logEvent("error", "title-style-settings-save-error", { message: error.message, reason });
      console.error(error);
      refreshConversationSounds();
    });
  }, delay);
}

function arrangeSettingsPayload() {
  return {
    arrangeSpacing: appSettings.arrangeChildSpacing,
    arrangeSize: appSettings.arrangeChildSize,
    arrangeResizeParents: appSettings.arrangeResizeParents,
    arrangeRecursive: appSettings.arrangeRecursive,
    arrangeChildSpacing: appSettings.arrangeChildSpacing,
    arrangeChildSize: appSettings.arrangeChildSize,
    arrangeNestedChildSize: appSettings.arrangeNestedChildSize,
    nestedLayerScale: appSettings.nestedLayerScale,
    arrangeWorldParentSpacing: appSettings.arrangeWorldParentSpacing,
    arrangeWorldParentSize: appSettings.arrangeWorldParentSize,
  };
}

async function savePanelArrangeSettings(reason = "panel-arrange-settings") {
  const response = await fetch("/api/settings/arrange", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(arrangeSettingsPayload()),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "arrange save failed" }));
    throw new Error(error.detail || "arrange save failed");
  }
  const data = await response.json();
  applyTitleStyleSettings(data);
  applyArrangeSettings(data);
  syncSettingsInputs();
  saveStoredSettings();
  logEvent("info", "panel-arrange-settings-saved", {
    message: "panel arrange settings saved",
    reason,
  });
}

function updatePanelArrangeSettings(reason = "panel-arrange-settings-change") {
  appSettings.arrangeResizeParents = panelArrangeResizeParentsInput ? panelArrangeResizeParentsInput.checked : appSettings.arrangeResizeParents;
  appSettings.arrangeRecursive = panelArrangeRecursiveInput ? panelArrangeRecursiveInput.checked : appSettings.arrangeRecursive;
  appSettings.arrangeWorldParentSpacing = normalizeArrangeSpacing(panelArrangeChildSpacingInput?.value);
  appSettings.arrangeWorldParentSize = normalizeArrangeSize(panelArrangeChildSizeInput?.value);
  appSettings.arrangeNestedChildSize = normalizeArrangeSize(panelArrangeNestedChildSizeInput?.value);
  appSettings.nestedLayerScale = normalizeNestedLayerScale(panelNestedLayerScaleInput?.value);
  if (panelArrangeWorldParentSpacingInput) {
    appSettings.arrangeChildSpacing = normalizeArrangeSpacing(panelArrangeWorldParentSpacingInput.value);
  }
  if (panelArrangeWorldParentSizeInput) {
    appSettings.arrangeChildSize = normalizeArrangeSize(panelArrangeWorldParentSizeInput.value);
  }
  document.documentElement.style.setProperty("--nested-layer-scale", appSettings.nestedLayerScale.toFixed(2));
  appSettings.arrangeSpacing = appSettings.arrangeChildSpacing;
  appSettings.arrangeSize = appSettings.arrangeChildSize;
  syncArrangePanelInputs();
  saveStoredSettings();
  savePanelArrangeSettings(reason).catch((error) => {
    logEvent("error", "panel-arrange-settings-save-error", { message: error.message, reason });
    console.error(error);
  });
}

function setConversationSending(enabled) {
  const visibleRequest = syncVisibleConversationRequestState();
  const hasNode = Boolean(conversationNodeId);
  const hasBulkTab = isBulkCommandTab(activeConversationTab());
  const canEdit = conversationCanEditSession();
  const viewBusy = Boolean(visibleRequest) || (hasBulkTab && bulkCommandSending) || (Boolean(enabled) && conversationActiveRequests.size === 0);
  conversationSending = viewBusy;
  sendConversationButton.disabled = (!hasNode && !hasBulkTab) || !canEdit;
  if (sendCodeConversationButton) {
    sendCodeConversationButton.disabled = !hasNode || Boolean(visibleRequest) || !canEdit;
  }
  conversationInput.disabled = (!hasNode && !hasBulkTab) || !canEdit;
  if (newConversationButton) {
    newConversationButton.disabled = !hasNode || Boolean(visibleRequest) || hasBulkTab;
  }
  if (summarizeConversationButton) {
    summarizeConversationButton.disabled = !hasNode || Boolean(visibleRequest) || conversationAutoSummaryInFlight || !canEdit || hasBulkTab;
  }
  if (conversationSessionSelect) {
    conversationSessionSelect.disabled = !hasNode || Boolean(visibleRequest) || Boolean(conversationTypingNodeId) || hasBulkTab;
  }
  if (saveButton) {
    saveButton.disabled = false;
  }
  if (saveAsButton) {
    saveAsButton.disabled = false;
  }
  updateConversationCancelButton();
}

function conversationCanCancel() {
  const request = visibleConversationRequest();
  const requestMatchesVisibleConversation = Boolean(
    request?.controller,
  );
  const typingMatchesVisibleConversation = Boolean(
    conversationTypingNodeId
      && conversationTypingTabId
      && activeConversationTabId === conversationTypingTabId
      && conversationNodeId === conversationTypingNodeId,
  );
  return Boolean(requestMatchesVisibleConversation || typingMatchesVisibleConversation);
}

function updateConversationCancelButton() {
  if (!cancelConversationButton) {
    return;
  }
  const canCancel = conversationCanCancel();
  cancelConversationButton.hidden = !canCancel;
  cancelConversationButton.disabled = !canCancel;
  const request = visibleConversationRequest();
  if (canCancel && request?.nodeId) {
    const target = nodeById(request.nodeId);
    cancelConversationButton.title = `${target ? meaningName(target) : "このポワン"}の返事をキャンセル`;
  } else {
    cancelConversationButton.title = "";
  }
  if (conversationSessionSelect) {
    conversationSessionSelect.disabled = !conversationNodeId || Boolean(visibleConversationRequest()) || Boolean(conversationTypingNodeId) || isBulkCommandTab(activeConversationTab());
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

function conversationWaitingText(
  node,
  { includeMeaningTree = false, includeDirectChildCode = false, attachmentCount = 0, status = "送信中", workText = "" } = {},
) {
  const parts = [`${shortConversationTargetName(node)}へ${status}`];
  if (workText) {
    parts.push(shortWorkText(workText));
  }
  if (includeMeaningTree) {
    parts.push("全体");
  }
  if (includeDirectChildCode) {
    parts.push("直下コード");
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
  const request = visibleConversationRequest();
  rememberConversationRequestWaitingText(text || "処理中", request);
  if (!request?.pendingMessage || !request.pendingMessage.isConnected) {
    return;
  }
  setInputWaitingMessageAnimation(request.pendingMessage, text || "処理中");
  syncVisibleConversationRequestState();
}

function stopConversationWorkPolling() {
  if (conversationWorkPollTimer) {
    window.clearInterval(conversationWorkPollTimer);
    conversationWorkPollTimer = null;
  }
  conversationWorkPollingActive = false;
}

async function pollConversationWorkEvents() {
  const request = visibleConversationRequest();
  if (!request?.pendingMessage || !request.pendingMessage.isConnected || !conversationWorkPollingActive) {
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
  const matchingEvents = events.filter((event) => event?.to?.id === request.nodeId);
  if (!matchingEvents.length) {
    return;
  }
  const latest = matchingEvents[matchingEvents.length - 1];
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

async function writeTextToClipboard(text) {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text);
    return;
  }
  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.setAttribute("readonly", "");
  textarea.style.position = "fixed";
  textarea.style.left = "-9999px";
  textarea.style.top = "0";
  document.body.appendChild(textarea);
  textarea.select();
  const copied = document.execCommand("copy");
  textarea.remove();
  if (!copied) {
    throw new Error("copy failed");
  }
}

function copyConversationMessage(message, button) {
  const text = message.dataset.copyText || message.querySelector(".conversation-message-body")?.textContent || "";
  if (!text) {
    return;
  }
  writeTextToClipboard(text).then(() => {
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

function conversationAllCopyText() {
  if (!conversationLog) {
    return "";
  }
  return [...conversationLog.querySelectorAll(".conversation-message")]
    .map((message) => {
      const text = message.dataset.copyText || message.querySelector(".conversation-message-body")?.textContent || "";
      if (!text.trim()) {
        return "";
      }
      return `${conversationRoleLabel(message.dataset.role)}:\n${text}`;
    })
    .filter(Boolean)
    .join("\n\n");
}

function copyAllConversationMessages(button) {
  const text = conversationAllCopyText();
  if (!text) {
    saveState.textContent = "copy empty";
    logEvent("debug", "conversation-copy-all-empty", { nodeId: conversationNodeId });
    return;
  }
  writeTextToClipboard(text).then(() => {
    const previous = button.textContent;
    button.textContent = "Copied";
    window.setTimeout(() => {
      button.textContent = previous;
    }, 900);
    logEvent("debug", "conversation-copy-all", {
      nodeId: conversationNodeId,
      length: text.length,
      count: conversationLog.querySelectorAll(".conversation-message").length,
    });
  }).catch((error) => {
    saveState.textContent = "copy error";
    logEvent("error", "conversation-copy-all-error", { nodeId: conversationNodeId, message: error.message });
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
  if (!conversationPanel || (!conversationNodeId && !activeConversationTabId)) {
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
  const { tabMode = "current", tabId = null, reason = "conversation-open" } = options;
  const node = nodeById(nodeId);
  if (!node) {
    return;
  }
  if (activeConversationTabId) {
    rememberConversationTabState(activeConversationTabId);
  }
  let tab = null;
  if (tabMode === "activate" && tabId) {
    tab = conversationTabs.find((item) => item.id === tabId) || null;
  } else if (tabMode === "new") {
    tab = createConversationTab(node.id, "conversation-tab-new-powan");
  } else {
    tab = activeConversationTab() || createConversationTab(node.id, "conversation-tab-current-powan");
    if (tab.nodeId !== node.id) {
      tab.nodeId = node.id;
      conversationTabStates.set(tab.id, {});
    }
  }
  if (!tab) {
    tab = createConversationTab(node.id, "conversation-tab-fallback-powan");
  }
  activeConversationTabId = tab.id;
  tab.nodeId = node.id;
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
  const state = restoreConversationDraftState(tab.id);
  renderConversationTabs();
  updateConversationSessionMode();
  focusConversationInputIfOpen();
  logEvent("debug", reason, { nodeId: node.id, tabId: tab.id, tabMode });
  let loader;
  if (tabMode === "activate" && state.viewingAllSessions) {
    loader = loadAllConversationSessions(node.id);
  } else if (tabMode === "activate" && state.viewingSessionId) {
    loader = loadConversationSession(node.id, state.viewingSessionId);
  } else {
    loader = loadConversationMessages(node.id);
  }
  loader.then(() => restoreConversationScroll(tab.id, node.id, state));
}

function closeConversationPanel(reason = "conversation-close") {
  if (!conversationNodeId) {
    conversationPanel.hidden = true;
    logEvent("debug", reason, { nodeId: null, collapsed: false });
    return;
  }
  rememberConversationTabState(activeConversationTabId);
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
  const copyButton = document.createElement("button");
  copyButton.type = "button";
  copyButton.className = "conversation-copy-button";
  copyButton.textContent = "Copy";
  copyButton.title = "この発言をコピー";
  copyButton.addEventListener("click", () => copyConversationMessage(message, copyButton));
  message.appendChild(copyButton);
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
  conversationTypingTabId = null;
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

function clearBackgroundSpeaking(nodeId) {
  const timer = conversationBackgroundSpeakingTimers.get(nodeId);
  if (timer) {
    window.clearTimeout(timer);
  }
  conversationBackgroundSpeakingTimers.delete(nodeId);
  conversationBackgroundSpeakingMouthOpenByNode.delete(nodeId);
  for (const element of powanSpeakingElements(nodeId)) {
    element.classList.remove("speaking", "mouth-open", "mouth-closed");
    updatePowanFaceButton(element);
  }
}

function setBackgroundSpeakingFrame(nodeId, open) {
  conversationBackgroundSpeakingMouthOpenByNode.set(nodeId, Boolean(open));
  for (const element of powanSpeakingElements(nodeId)) {
    element.classList.add("speaking");
    element.classList.toggle("mouth-open", Boolean(open));
    element.classList.toggle("mouth-closed", !open);
    updatePowanFaceButton(element);
  }
}

function typeConversationReplyMouthOnly(nodeId, text, onComplete = null) {
  clearBackgroundSpeaking(nodeId);
  const visibleText = formatConversationText("assistant", text || "");
  if (!visibleText.length) {
    if (onComplete) {
      onComplete();
    }
    return;
  }
  let index = 0;
  setBackgroundSpeakingFrame(nodeId, true);
  function tick() {
    const char = visibleText[index];
    const pauseMs = conversationTypingPauseMs(char);
    if (pauseMs > 0) {
      setBackgroundSpeakingFrame(nodeId, false);
    } else {
      setBackgroundSpeakingFrame(nodeId, index % 2 === 0);
    }
    index += 1;
    if (index >= visibleText.length) {
      clearBackgroundSpeaking(nodeId);
      logEvent("debug", "conversation-background-mouth-complete", {
        message: `background mouth complete: ${nodeId}, ${visibleText.length} chars`,
        nodeId,
        length: visibleText.length,
      });
      if (onComplete) {
        onComplete();
      }
      return;
    }
    const timer = window.setTimeout(tick, pauseMs || 32);
    conversationBackgroundSpeakingTimers.set(nodeId, timer);
  }
  tick();
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
  clearBackgroundSpeaking(nodeId);
  const typingTabId = activeConversationTabId;
  const message = appendConversationMessage("assistant", "");
  const visibleText = formatConversationText("assistant", text);
  let index = 0;
  conversationTypingNodeId = nodeId;
  conversationTypingTabId = typingTabId;
  conversationTypingMouthOpen = true;
  updateConversationCancelButton();
  setPowanSpeaking(nodeId, true);
  if (!visibleText.length) {
    setConversationMessageText(message, "assistant", "");
    setPowanSpeaking(nodeId, false);
    conversationTypingNodeId = null;
    conversationTypingTabId = null;
    conversationTypingMouthOpen = false;
    updateConversationCancelButton();
    logEvent("debug", "conversation-reply-display-complete", {
      message: `reply display complete: ${nodeId}, 0 chars`,
      nodeId,
      length: 0,
    });
    if (onComplete) {
      onComplete();
    }
    return;
  }
  function tick() {
    if (activeConversationTabId !== typingTabId || conversationNodeId !== nodeId) {
      logEvent("warn", "conversation-reply-display-aborted-node-changed", {
        message: `reply display skipped: target changed ${typingTabId}/${nodeId} -> ${activeConversationTabId || "none"}/${conversationNodeId || "none"}`,
        tabId: typingTabId,
        nodeId,
        currentTabId: activeConversationTabId,
        currentNodeId: conversationNodeId,
        typedLength: index,
        length: visibleText.length,
      });
      setPowanSpeaking(nodeId, false);
      stopConversationChunkSound("conversation-node-changed");
      conversationTypingNodeId = null;
      conversationTypingTabId = null;
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
      conversationTypingTabId = null;
      conversationTypingMouthOpen = false;
      updateConversationCancelButton();
      logEvent("debug", "conversation-reply-display-complete", {
        message: `reply display complete: ${nodeId}, ${visibleText.length} chars`,
        nodeId,
        length: visibleText.length,
      });
      if (onComplete) {
        onComplete();
      }
      return;
    }
    conversationTypingTimer = window.setTimeout(tick, pauseMs || 32);
  }
  tick();
}

function rememberInactiveConversationReply(tabId, nodeId, conversationId) {
  const tab = conversationTabs.find((item) => item.id === tabId);
  if (!tab || tab.nodeId !== nodeId) {
    return;
  }
  const state = conversationTabState(tab.id);
  state.nodeId = nodeId;
  state.activeSessionId = normalizeConversationId(conversationId);
  state.viewingSessionId = normalizeConversationId(conversationId);
  state.viewingAllSessions = false;
  state.autoFollow = true;
  markConversationTabAttention(tab.id, nodeId, "reply", "返事が届きました", conversationId);
  logEvent("debug", "conversation-inactive-tab-reply-remembered", {
    tabId: tab.id,
    nodeId,
    conversationId: normalizeConversationId(conversationId),
  });
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
      logEvent("debug", "conversation-new-session-skipped", {
        message: `new session skipped: node changed ${node.id} -> ${conversationNodeId || "none"}`,
        nodeId: node.id,
        currentNodeId: conversationNodeId,
      });
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
    rememberConversationTabState(activeConversationTabId);
    renderConversationTabs();
    refreshConversationSessions(node.id, data.conversationId);
    logEvent("info", reason, {
      message: `new session ready: ${node.id}/${data.conversationId}`,
      nodeId: node.id,
      conversationId: data.conversationId,
    });
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
      logEvent("debug", "conversation-summary-skipped", {
        message: `summary skipped: node changed ${node.id} -> ${conversationNodeId || "none"}`,
        nodeId: node.id,
        currentNodeId: conversationNodeId,
      });
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
    rememberConversationTabState(activeConversationTabId);
    renderConversationTabs();
    refreshConversationSessions(node.id, data.conversationId);
    logEvent("info", reason, {
      message: `summary session ready: ${node.id}/${data.conversationId}, ${(data.summary || "").length} chars`,
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
  const request = visibleConversationRequest();
  const pendingMessage = request?.pendingMessage || conversationPendingMessage;
  if (!pendingMessage || !pendingMessage.isConnected) {
    return false;
  }
  setConversationMessageText(pendingMessage, "system", text);
  pendingMessage.classList.remove("pending");
  return true;
}

async function cancelConversationReply(reason = "conversation-cancel") {
  const request = visibleConversationRequest();
  const requestNodeId = request?.nodeId || null;
  const requestTabId = request?.tabId || null;
  const typingNodeId = conversationTypingNodeId;
  const typingTabId = conversationTypingTabId;
  const requestMatchesVisibleConversation = Boolean(
    request?.controller,
  );
  const typingMatchesVisibleConversation = Boolean(
    typingNodeId
      && typingTabId
      && activeConversationTabId === typingTabId
      && conversationNodeId === typingNodeId,
  );
  if (!requestMatchesVisibleConversation && !typingMatchesVisibleConversation) {
    logEvent("warn", "conversation-cancel-ignored-target-mismatch", {
      reason,
      activeTabId: activeConversationTabId,
      activeNodeId: conversationNodeId,
      requestTabId,
      requestNodeId,
      typingTabId,
      typingNodeId,
    });
    updateConversationCancelButton();
    return;
  }
  stopInputWaitingSound(reason, request?.soundOwner || "");
  if (requestMatchesVisibleConversation) {
    request.cancelRequested = true;
    syncVisibleConversationRequestState();
    markConversationPendingCancelled("キャンセル中...");
    request.controller.abort();
    if (requestNodeId) {
      requestCancelPowanCodex(requestNodeId).then((data) => {
        logEvent("info", "conversation-cancel-requested", {
          reason,
          tabId: requestTabId,
          nodeId: requestNodeId,
          cancelled: Boolean(data.cancelled),
          running: Boolean(data.running),
        });
      }).catch((error) => {
        logEvent("warn", "conversation-cancel-error", { nodeId: requestNodeId, message: error.message });
      });
    }
  }
  if (typingMatchesVisibleConversation) {
    stopConversationTyping();
    appendConversationMessage("system", "返事をキャンセルしました", { forceFollow: true });
    logEvent("info", "conversation-typing-cancelled", { reason, tabId: typingTabId, nodeId: typingNodeId });
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

if (panelWorldTab) {
  panelWorldTab.addEventListener("click", () => setPanelTab("world", { reason: "panel-world-tab-click" }));
}
if (panelSettingsTab) {
  panelSettingsTab.addEventListener("click", () => setPanelTab("settings", { reason: "panel-settings-tab-click" }));
}
if (panelHistoryTab) {
  panelHistoryTab.addEventListener("click", () => setPanelTab("history", { reason: "panel-history-tab-click" }));
}
if (panelCodeTab) {
  panelCodeTab.addEventListener("click", () => setPanelTab("code", { reason: "panel-code-tab-click" }));
}
if (conversationHistorySortSelect) {
  conversationHistorySortSelect.addEventListener("change", () => {
    conversationHistorySort = conversationHistorySortSelect.value || "newest";
    mergeConversationHistoryItems();
    logEvent("debug", "conversation-history-sort-change", { sort: conversationHistorySort });
  });
}
if (conversationHistoryRefreshButton) {
  conversationHistoryRefreshButton.addEventListener("click", () => {
    refreshConversationHistory({ reason: "conversation-history-refresh-button" });
  });
}
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
if (copyAllConversationButton) {
  copyAllConversationButton.addEventListener("click", () => copyAllConversationMessages(copyAllConversationButton));
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
  conversationInput.addEventListener("input", () => {
    rememberConversationDraft(activeConversationTabId);
  });
  conversationInput.addEventListener("focus", () => {
    resumeActiveConversationAudio("conversation-input-focus");
  });
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
if (bulkCommandMenuButton) {
  bulkCommandMenuButton.addEventListener("click", () => {
    powanExplorer.closeNodeMenu("bulk-command-menu-close");
    openBulkCommandDialog();
  });
}
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
  powanExplorer.arrangeNodeChildren(nodeId, "arrange-node-children");
});
if (selectChildPowansMenuButton) {
  selectChildPowansMenuButton.addEventListener("click", () => {
    const nodeId = nodeContextMenuNodeId;
    const parent = nodeById(nodeId);
    const childIds = parent ? powanExplorer.childrenOf(parent).map((child) => child.id) : [];
    powanExplorer.closeNodeMenu("select-child-powans-menu-close");
    if (!childIds.length) {
      logEvent("debug", "child-select-all-empty", { parentId: nodeId || null });
      return;
    }
    const selected = applySelection(childIds, {
      primaryId: childIds[0],
      anchorId: childIds[0],
      reason: "child-menu-select-all",
    });
    logEvent("info", "child-select-all-complete", {
      parentId: nodeId,
      count: selected.length,
    });
  });
}
if (arrangeWorldMenuButton) {
  arrangeWorldMenuButton.addEventListener("click", () => {
    powanExplorer.closeWorldMenu("arrange-current-world-menu-close");
    powanExplorer.arrangeCurrentWorld();
  });
}
if (selectWorldParentsMenuButton) {
  selectWorldParentsMenuButton.addEventListener("click", () => {
    powanExplorer.closeWorldMenu("select-world-parents-menu-close");
    selectAllCanvasNodes("world-menu-select-all-parents");
  });
}
if (pasteWorldMenuButton) {
  pasteWorldMenuButton.addEventListener("click", () => {
    const dropCenter = worldContextMenuDropCenter ? { ...worldContextMenuDropCenter } : visibleWorldCenter();
    const parentId = openParentId || null;
    powanExplorer.closeWorldMenu("paste-world-menu-close");
    powanExplorer.pastePowansFromClipboard({
      parentId,
      dropCenter,
      reason: "world-menu-paste-clipboard",
    }).catch((error) => {
      saveState.textContent = "paste error";
      logEvent("error", "world-menu-paste-clipboard-error", { message: error.message });
      console.error(error);
    });
  });
}
if (panelArrangeWorldButton) {
  panelArrangeWorldButton.addEventListener("click", () => {
    powanExplorer.arrangeCurrentWorld("panel-arrange-current-world");
  });
}
for (const input of [
  panelArrangeResizeParentsInput,
  panelArrangeRecursiveInput,
  panelArrangeChildSpacingInput,
  panelArrangeChildSizeInput,
  panelArrangeNestedChildSizeInput,
  panelNestedLayerScaleInput,
  panelArrangeWorldParentSpacingInput,
  panelArrangeWorldParentSizeInput,
]) {
  if (!input) {
    continue;
  }
  const eventName = input.type === "checkbox" ? "change" : "input";
  input.addEventListener(eventName, () => updatePanelArrangeSettings(`panel-${input.id}`));
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
if (copyTitleMenuButton) {
  copyTitleMenuButton.addEventListener("click", () => {
    const nodeId = nodeContextMenuNodeId;
    const node = nodeById(nodeId);
    powanExplorer.closeNodeMenu("copy-title-menu-close");
    if (!node) {
      saveState.textContent = "copy title missing";
      logEvent("warn", "copy-title-missing-node", { nodeId });
      return;
    }
    const title = meaningName(node);
    copyTextToClipboard(title).then((copied) => {
      if (!copied) {
        throw new Error("copy failed");
      }
      saveState.textContent = "title copied";
      logEvent("info", "copy-title-complete", { nodeId: node.id, title });
    }).catch((error) => {
      saveState.textContent = "copy title error";
      logEvent("error", "copy-title-error", { nodeId: node.id, message: error.message });
      console.error(error);
    });
  });
}
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
async function sendConversation({ forceDirectChildCode = false, queuedSend = null } = {}) {
  const isQueuedSend = Boolean(queuedSend);
  if (!isQueuedSend && isBulkCommandTab(activeConversationTab())) {
    await sendBulkCommandToSelected();
    return;
  }
  const node = nodeById(isQueuedSend ? queuedSend.nodeId : conversationNodeId);
  const requestTabId = isQueuedSend ? queuedSend.tabId : activeConversationTabId;
  const text = isQueuedSend ? String(queuedSend.text || "").trim() : conversationInput.value.trim();
  const includeMeaningTree = isQueuedSend ? Boolean(queuedSend.includeMeaningTree) : Boolean(conversationTreeContextInput?.checked);
  const includeDirectChildCode = isQueuedSend
    ? Boolean(queuedSend.includeDirectChildCode)
    : forceDirectChildCode || Boolean(conversationDirectChildCodeInput?.checked);
  const effectiveText = text || (!isQueuedSend && forceDirectChildCode ? "自分のコードを書いて" : "");
  const displayAttachments = isQueuedSend
    ? cloneConversationAttachments(queuedSend.attachments || [])
    : [...conversationPendingAttachments];
  const attachmentPayloads = displayAttachments.map(conversationPayloadAttachment);
  const canEdit = isQueuedSend || conversationCanEditSession();
  if (!node || (!effectiveText && !attachmentPayloads.length) || !canEdit) {
    return;
  }
  if (conversationRequestForNode(node.id)) {
    if (!isQueuedSend) {
      queueConversationSend({
        tabId: requestTabId,
        nodeId: node.id,
        text: effectiveText,
        attachments: displayAttachments,
        includeMeaningTree,
        includeDirectChildCode,
        conversationId: normalizeConversationId(conversationViewingSessionId || conversationActiveSessionId),
      });
    } else {
      conversationQueuedSends.unshift(queuedSend);
    }
    return;
  }
  const requestViewIsActiveAtSend = activeConversationTabId === requestTabId && conversationNodeId === node.id;
  if (isQueuedSend && queuedSend.statusMessage?.isConnected) {
    queuedSend.statusMessage.remove();
  }
  if (requestViewIsActiveAtSend) {
    appendConversationMessage("user", effectiveText || "添付を渡す", { forceFollow: true, attachments: displayAttachments });
    if (!isQueuedSend) {
      conversationInput.value = "";
      conversationPendingAttachments = [];
      renderConversationAttachmentTray();
      rememberConversationTabState(activeConversationTabId);
    }
  }
  logEvent("debug", "conversation-send", {
    nodeId: node.id,
    length: effectiveText.length,
    includeMeaningTree,
    includeDirectChildCode,
    attachmentCount: attachmentPayloads.length,
    attachmentPathCount: attachmentPayloads.filter((attachment) => attachment.pathAvailable).length,
  });
  const controller = new AbortController();
  const requestConversationId = isQueuedSend
    ? normalizeConversationId(queuedSend.conversationId)
    : normalizeConversationId(conversationViewingSessionId || conversationActiveSessionId);
  const request = {
    id: ++conversationRequestSerial,
    controller,
    tabId: requestTabId,
    nodeId: node.id,
    conversationId: requestConversationId,
    waitingText: "",
    pendingMessage: null,
    cancelRequested: false,
    soundOwner: `conversation-request-${conversationRequestSerial}`,
  };
  conversationActiveRequests.set(conversationRequestKey(node.id), request);
  runningPowanRuns.set(node.id, {
    id: null,
    conversationId: requestConversationId,
    powanId: node.id,
    status: "running",
    userText: effectiveText,
    source: "conversation",
  });
  schedulePowanFaceRefresh([node.id], "conversation-send-running-face");
  setConversationSending(true);
  const waitingText = conversationWaitingText(node, {
    includeMeaningTree,
    includeDirectChildCode,
    attachmentCount: attachmentPayloads.length,
    status: "送信中",
    workText: effectiveText || (attachmentPayloads.length ? "添付を渡す" : ""),
  });
  rememberConversationRequestWaitingText(waitingText, request);
  const pendingMessage = requestViewIsActiveAtSend
    ? appendConversationMessage("system", waitingText, { forceFollow: true })
    : document.createElement("div");
  if (requestViewIsActiveAtSend) {
    request.pendingMessage = pendingMessage;
    syncVisibleConversationRequestState();
    pendingMessage.classList.add("pending");
    setInputWaitingMessageAnimation(pendingMessage, waitingText);
    startInputWaitingSound(request.soundOwner);
  }
  try {
    if (documentDirty) {
      await saveDocument({ reason: "conversation-preflight-save", auto: true });
    }
    let workEventStartSequence = conversationWorkEventSequence;
    try {
      workEventStartSequence = await currentPowanWorkEventSequence();
    } catch (error) {
      logEvent("debug", "conversation-work-events-start-error", { message: error.message });
    }
    if (requestViewIsActiveAtSend) {
      startConversationWorkPolling(workEventStartSequence);
    }
    const data = await requestPowanCodexReply(node.id, effectiveText, {
      signal: controller.signal,
      includeMeaningTree,
      includeDirectChildCode,
      attachments: attachmentPayloads,
    });
    const replyConversationId = normalizeConversationId(data.conversationId);
    const requestViewIsActive = activeConversationTabId === requestTabId && conversationNodeId === node.id;
    stopInputWaitingSound("conversation-reply-received", request.soundOwner);
    if (requestViewIsActive) {
      conversationActiveSessionId = replyConversationId;
      conversationViewingSessionId = replyConversationId;
      conversationViewingAllSessions = false;
      rememberConversationTabState(activeConversationTabId);
    } else {
      rememberInactiveConversationReply(requestTabId, node.id, replyConversationId);
    }
    renderConversationTabs();
    if (requestViewIsActive) {
      refreshConversationSessions(node.id, data.conversationId);
    }
    await reloadCurrentDocument({
      force: true,
      reason: "conversation-agent-sync",
      restoreViewport: false,
      preserveLocalLayouts: true,
    });
    if (data.cancelled) {
      if (requestViewIsActive) {
        markConversationPendingCancelled("キャンセルしました");
      }
      logEvent("info", "conversation-codex-cancelled", {
        message: `reply cancelled: ${node.id}/${data.conversationId}`,
        nodeId: node.id,
        conversationId: data.conversationId,
      });
      return;
    }
    if (conversationRequestForNode(node.id) === request) {
      conversationActiveRequests.delete(conversationRequestKey(node.id));
    }
    runningPowanRuns.delete(node.id);
    schedulePowanFaceRefresh([node.id], "conversation-send-finished-face");
    clearConversationTabRunningStatus(requestTabId, node.id);
    if (requestViewIsActive && pendingMessage.isConnected) {
      pendingMessage.remove();
    }
    const reply = data.assistantMessage?.text || "";
    if (requestViewIsActive) {
      typeConversationReply(node.id, reply, () => maybeAutoSummarizeConversation(node.id));
    } else {
      typeConversationReplyMouthOnly(node.id, reply);
    }
  } catch (error) {
    const requestViewIsActive = activeConversationTabId === requestTabId && conversationNodeId === node.id;
    stopInputWaitingSound("conversation-codex-error", request.soundOwner);
    if (error.name === "AbortError" || request.cancelRequested) {
      if (requestViewIsActive) {
        markConversationPendingCancelled("キャンセルしました");
      }
      logEvent("info", "conversation-fetch-cancelled", {
        message: `reply fetch cancelled: ${node.id}`,
        nodeId: node.id,
      });
    } else {
      if (requestViewIsActive && pendingMessage.isConnected) {
        pendingMessage.remove();
      }
      if (requestViewIsActive) {
        appendConversationMessage("system", `Codex execで返事できなかった: ${error.message}`, { forceFollow: true });
      }
      logEvent("error", "conversation-codex-error", {
        message: `reply failed: ${node.id}: ${error.message}`,
        nodeId: node.id,
      });
    }
  } finally {
    const requestViewIsActive = activeConversationTabId === requestTabId && conversationNodeId === node.id;
    stopInputWaitingSound("conversation-send-finally", request.soundOwner);
    if (requestViewIsActive) {
      stopConversationWorkPolling();
    }
    if (conversationRequestForNode(node.id) === request) {
      conversationActiveRequests.delete(conversationRequestKey(node.id));
    }
    runningPowanRuns.delete(node.id);
    schedulePowanFaceRefresh([node.id], "conversation-send-finally-face");
    clearConversationTabRunningStatus(requestTabId, node.id);
    if (request.pendingMessage === pendingMessage) {
      request.pendingMessage = null;
    }
    setConversationSending(false);
    updateConversationCancelButton();
    if (requestViewIsActive) {
      focusConversationInputIfOpen();
    }
    syncVisibleConversationRequestState();
    sendNextQueuedConversation("conversation-send-finally", node.id);
  }
}

conversationForm.addEventListener("submit", (event) => {
  event.preventDefault();
  sendConversation();
});
if (sendCodeConversationButton) {
  sendCodeConversationButton.addEventListener("click", () => {
    sendConversation({ forceDirectChildCode: true });
  });
}
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
if (titleFontFamilySelect) {
  titleFontFamilySelect.addEventListener("change", () => updateTitleStyleSettings("title-font-family-change", { delayMs: 0 }));
}
if (titleFontScaleInput) {
  titleFontScaleInput.addEventListener("input", () => updateTitleStyleSettings("title-font-scale-input"));
  titleFontScaleInput.addEventListener("change", () => updateTitleStyleSettings("title-font-scale-change", { delayMs: 0 }));
}
if (titleOutlineInput) {
  titleOutlineInput.addEventListener("change", () => updateTitleStyleSettings("title-outline-toggle", { delayMs: 0 }));
}
if (titleOutlineColorInput) {
  titleOutlineColorInput.addEventListener("input", () => updateTitleStyleSettings("title-outline-color-input"));
  titleOutlineColorInput.addEventListener("change", () => updateTitleStyleSettings("title-outline-color-change", { delayMs: 0 }));
}
if (titleOutlineWidthInput) {
  titleOutlineWidthInput.addEventListener("input", () => updateTitleStyleSettings("title-outline-width-input"));
  titleOutlineWidthInput.addEventListener("change", () => updateTitleStyleSettings("title-outline-width-change", { delayMs: 0 }));
}
if (titleShadowInput) {
  titleShadowInput.addEventListener("change", () => updateTitleStyleSettings("title-shadow-toggle", { delayMs: 0 }));
}
if (titleShadowColorInput) {
  titleShadowColorInput.addEventListener("input", () => updateTitleStyleSettings("title-shadow-color-input"));
  titleShadowColorInput.addEventListener("change", () => updateTitleStyleSettings("title-shadow-color-change", { delayMs: 0 }));
}
if (titleShadowBlurInput) {
  titleShadowBlurInput.addEventListener("input", () => updateTitleStyleSettings("title-shadow-blur-input"));
  titleShadowBlurInput.addEventListener("change", () => updateTitleStyleSettings("title-shadow-blur-change", { delayMs: 0 }));
}
if (titleShadowXInput) {
  titleShadowXInput.addEventListener("input", () => updateTitleStyleSettings("title-shadow-x-input"));
  titleShadowXInput.addEventListener("change", () => updateTitleStyleSettings("title-shadow-x-change", { delayMs: 0 }));
}
if (titleShadowYInput) {
  titleShadowYInput.addEventListener("input", () => updateTitleStyleSettings("title-shadow-y-input"));
  titleShadowYInput.addEventListener("change", () => updateTitleStyleSettings("title-shadow-y-change", { delayMs: 0 }));
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
    openSettingsPage();
  });
}

function openSettingsPage() {
  const params = new URLSearchParams();
  if (projectName) {
    params.set("project", projectName);
  }
  if (documentName) {
    params.set("file", documentName);
  }
  window.location.href = `/settings?${params.toString()}`;
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

function eventTargetElement(target) {
  if (!target) {
    return null;
  }
  return target.nodeType === 1 ? target : target.parentElement || null;
}

function selectedTextTouchesConversationPanel() {
  if (!conversationPanel || conversationPanel.hidden || !window.getSelection) {
    return false;
  }
  const selection = window.getSelection();
  if (!selection || selection.isCollapsed) {
    return false;
  }
  for (let index = 0; index < selection.rangeCount; index += 1) {
    const range = selection.getRangeAt(index);
    const element = eventTargetElement(range.commonAncestorContainer);
    if (element && conversationPanel.contains(element)) {
      return true;
    }
  }
  return false;
}

function conversationOwnsKeyboardEvent(event) {
  if (!conversationPanel || conversationPanel.hidden) {
    return false;
  }
  const target = eventTargetElement(event.target);
  const active = eventTargetElement(document.activeElement);
  return Boolean(
    (target && conversationPanel.contains(target))
    || (active && conversationPanel.contains(active))
    || selectedTextTouchesConversationPanel()
  );
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
  if (conversationOwnsKeyboardEvent(event)) {
    return;
  }
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
    if (key === "a") {
      event.preventDefault();
      selectSelectedNodeChildrenOrCanvas("keyboard-canvas-select-all");
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
      const resizeFactor = event.deltaY < 0 ? 1.08 : 0.92;
      powanExplorer.resizeSelectedByWheel(resizeFactor);
      return;
    }
    if (event.shiftKey) {
      powanExplorer.spreadSelectedNestedPowansFromParentCenter(factor);
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
  const nextDoc = await fetchDocument(name);
  documentSnapshot = await documentSignature(nextDoc);
  powanExplorer.setDocument(nextDoc, { name, status: "loaded", reason: "load-document-state" });
  await refreshFiles();
  render();
  startRunningAgentRunRefresh();
  if (activePanelTab === "history") {
    refreshConversationHistory({ reason: "load-document-refresh-history" });
  }
  startAutoReload();
  logEvent("debug", "load-document-complete", {
    message: `document loaded: ${name}, ${doc.nodes.length} nodes`,
    name,
    nodeCount: doc.nodes.length,
  });
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
    documentSnapshot = await documentSignature(imported);
    await refreshFiles();
    render();
    logEvent("debug", "load-file-complete", {
      message: `file loaded: ${documentName}, ${doc.nodes.length} nodes`,
      name: documentName,
      nodeCount: doc.nodes.length,
    });
  } catch (error) {
    saveState.textContent = "load error";
    logEvent("error", "load-file-error", { message: `file load failed: ${error.message}` });
    console.error(error);
  } finally {
    fileInput.value = "";
  }
}

function scheduleDocumentAutoSave(reason = "dirty") {
  documentAutoSavePendingReason = reason;
  if (documentAutoSaveTimer) {
    window.clearTimeout(documentAutoSaveTimer);
  }
  documentAutoSaveTimer = window.setTimeout(() => {
    documentAutoSaveTimer = null;
    runDocumentAutoSave(documentAutoSavePendingReason);
  }, 450);
}

async function runDocumentAutoSave(reason = "auto-save") {
  if (!documentDirty || documentAutoSaveInFlight || !doc || !projectName || !documentName) {
    return;
  }
  documentAutoSaveInFlight = true;
  try {
    await saveDocument({ reason: `auto-save:${reason}`, auto: true });
  } finally {
    documentAutoSaveInFlight = false;
    if (documentDirty && documentAutoSavePendingReason !== reason) {
      scheduleDocumentAutoSave(documentAutoSavePendingReason || "auto-save-pending");
    }
  }
}

async function saveDocument({ reason = "manual-save", auto = false } = {}) {
  if (auto && !documentDirty) {
    return;
  }
  saveState.textContent = auto ? "auto saving" : "saving";
  const savedViewport = saveViewportToDocument();
  const savedDirtyRevision = documentDirtyRevision;
  const savePayload = JSON.stringify(doc);
  const saveUrl = `/api/doc/${encodeURIComponent(documentName)}?project=${encodeURIComponent(projectName)}`;
  const saveHeaders = {
    "Content-Type": "application/json",
  };
  if (documentSnapshot) {
    saveHeaders["X-ABC-Document-Snapshot"] = encodeURIComponent(documentSnapshot);
  }
  try {
    let response = await fetch(saveUrl, {
      method: "POST",
      headers: saveHeaders,
      body: savePayload,
    });
    if (response.status === 409 || response.status === 428) {
      saveState.textContent = "resaving";
      logEvent("warn", "save-document-stale-rejected", {
        message: `save rejected once, retrying visible document: ${documentName}, status ${response.status}`,
        name: documentName,
        status: response.status,
        reason,
        auto,
        console: true,
      });
      const latestDocument = await fetchDocument(documentName);
      saveHeaders["X-ABC-Document-Snapshot"] = encodeURIComponent(await documentSignature(latestDocument));
      response = await fetch(saveUrl, {
        method: "POST",
        headers: saveHeaders,
        body: savePayload,
      });
    }
    if (!response.ok) {
      const responseText = await response.text();
      logEvent("error", "save-document-failed-response", {
        message: `save failed: ${documentName}, status ${response.status}`,
        name: documentName,
        status: response.status,
        responseText: responseText.slice(0, 160),
        console: true,
      });
      throw new Error(`save failed: ${response.status}`);
    }
    const data = await response.json();
    const savedCurrentRevision = savedDirtyRevision === documentDirtyRevision;
    if (savedCurrentRevision) {
      documentDirty = false;
    } else {
      scheduleDocumentAutoSave("save-dirtied-during-save");
    }
    saveState.textContent = savedCurrentRevision ? "saved" : "edited";
    documentSnapshot = data.snapshot || await documentSignature(doc);
    await refreshFiles();
    logEvent("info", "save-document-complete", {
      message: `document saved: ${documentName}, ${doc.nodes.length} nodes`,
      name: documentName,
      nodeCount: doc.nodes.length,
      reason,
      auto,
      console: true,
    });
    return true;
  } catch (error) {
    saveState.textContent = "save error";
    logEvent("error", "save-document-error", {
      message: `save error: ${documentName}: ${error?.message || String(error)}`,
      name: documentName,
      nodeCount: doc?.nodes?.length || 0,
      console: true,
    });
    await flushLogQueue();
    return false;
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
  await saveDocument();
}

async function createDocument() {
  const response = await fetch(
    `/api/doc?project=${encodeURIComponent(projectName)}&random_color=${appSettings.randomPowanColor ? "true" : "false"}`,
    { method: "POST" },
  );
  const data = await response.json();
  await powanExplorer.loadDocument(data.file);
  logEvent("debug", "create-document-complete", {
    message: `document created: ${data.file}`,
    name: data.file,
  });
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
    logEvent("error", "load-document-error", {
      message: `document load failed: ${documentName}: ${error.message}`,
      name: documentName,
    });
    console.error(error);
  });
}
