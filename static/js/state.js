var canvas = document.querySelector("#canvas");
var coordinateBadge = document.querySelector("#coordinateBadge");
var treePanel = document.querySelector(".tree-panel");
var treePanelToggleButton = document.querySelector("#treePanelToggleButton");
var rootWorldButton = document.querySelector("#rootWorldButton");
var treeList = document.querySelector("#treeList");
var treeCopyButton = document.querySelector("#treeCopyButton");
var treeDeleteButton = document.querySelector("#treeDeleteButton");
var treeResizeHandle = document.querySelector("#treeResizeHandle");
var nodeContextMenu = document.querySelector("#nodeContextMenu");
var worldContextMenu = document.querySelector("#worldContextMenu");
var editMeaningMenuButton = document.querySelector("#editMeaningMenuButton");
var talkToPowanButton = document.querySelector("#talkToPowanButton");
var bulkCommandMenuButton = document.querySelector("#bulkCommandMenuButton");
var openDesignMenuButton = document.querySelector("#openDesignMenuButton");
var openCodeMenuButton = document.querySelector("#openCodeMenuButton");
var arrangePowanMenuButton = document.querySelector("#arrangePowanMenuButton");
var selectChildPowansMenuButton = document.querySelector("#selectChildPowansMenuButton");
var arrangeWorldMenuButton = document.querySelector("#arrangeWorldMenuButton");
var selectWorldParentsMenuButton = document.querySelector("#selectWorldParentsMenuButton");
var pasteWorldMenuButton = document.querySelector("#pasteWorldMenuButton");
var panelArrangeWorldButton = document.querySelector("#panelArrangeWorldButton");
var exportPowanMenuButton = document.querySelector("#exportPowanMenuButton");
var importPowanMenuButton = document.querySelector("#importPowanMenuButton");
var copyTitleMenuButton = document.querySelector("#copyTitleMenuButton");
var copyPathMenuButton = document.querySelector("#copyPathMenuButton");
var copySelectionMenuButton = document.querySelector("#copySelectionMenuButton");
var deleteSelectionMenuButton = document.querySelector("#deleteSelectionMenuButton");
var projectBadge = document.querySelector("#projectBadge");
var fileSelect = document.querySelector("#fileSelect");
var fileInput = document.querySelector("#fileInput");
var subtreeImportInput = document.querySelector("#subtreeImportInput");
var loadButton = document.querySelector("#loadButton");
var undoButton = document.querySelector("#undoButton");
var redoButton = document.querySelector("#redoButton");
var saveButton = document.querySelector("#saveButton");
var saveAsButton = document.querySelector("#saveAsButton");
var newFileButton = document.querySelector("#newFileButton");
var settingsButton = document.querySelector("#settingsButton");
var panelArrangeResizeParentsInput = document.querySelector("#panelArrangeResizeParentsInput");
var panelArrangeRecursiveInput = document.querySelector("#panelArrangeRecursiveInput");
var panelArrangeChildSpacingInput = document.querySelector("#panelArrangeChildSpacingInput");
var panelArrangeChildSpacingValue = document.querySelector("#panelArrangeChildSpacingValue");
var panelArrangeChildSizeInput = document.querySelector("#panelArrangeChildSizeInput");
var panelArrangeChildSizeValue = document.querySelector("#panelArrangeChildSizeValue");
var panelArrangeNestedChildSizeInput = document.querySelector("#panelArrangeNestedChildSizeInput");
var panelArrangeNestedChildSizeValue = document.querySelector("#panelArrangeNestedChildSizeValue");
var panelNestedLayerScaleInput = document.querySelector("#panelNestedLayerScaleInput");
var panelNestedLayerScaleValue = document.querySelector("#panelNestedLayerScaleValue");
var panelArrangeWorldParentSpacingInput = document.querySelector("#panelArrangeWorldParentSpacingInput");
var panelArrangeWorldParentSpacingValue = document.querySelector("#panelArrangeWorldParentSpacingValue");
var panelArrangeWorldParentSizeInput = document.querySelector("#panelArrangeWorldParentSizeInput");
var panelArrangeWorldParentSizeValue = document.querySelector("#panelArrangeWorldParentSizeValue");
var shutdownButton = document.querySelector("#shutdownButton");
var restartButton = document.querySelector("#restartButton");
var saveState = document.querySelector("#saveState");
var documentDirty = false;
var documentDirtyRevision = 0;
var documentAutoSaveTimer = null;
var documentAutoSaveInFlight = false;
var documentAutoSavePendingReason = "";
var panel = document.querySelector("#panel");
var panelToggleButton = document.querySelector("#panelToggleButton");
var panelResizeHandle = document.querySelector("#panelResizeHandle");
var conversationPanel = document.querySelector("#conversationPanel");
var conversationResizeHandle = document.querySelector("#conversationResizeHandle");
var conversationTabBar = document.querySelector("#conversationTabBar");
var conversationNodeName = document.querySelector("#conversationNodeName");
var conversationLog = document.querySelector("#conversationLog");
var conversationForm = document.querySelector("#conversationForm");
var conversationInputResizeHandle = document.querySelector("#conversationInputResizeHandle");
var conversationAttachmentTray = document.querySelector("#conversationAttachmentTray");
var conversationInput = document.querySelector("#conversationInput");
var sendConversationButton = document.querySelector("#sendConversationButton");
var sendCodeConversationButton = document.querySelector("#sendCodeConversationButton");
var cancelConversationButton = document.querySelector("#cancelConversationButton");
var newConversationButton = document.querySelector("#newConversationButton");
var summarizeConversationButton = document.querySelector("#summarizeConversationButton");
var copyAllConversationButton = document.querySelector("#copyAllConversationButton");
var conversationSessionSelect = document.querySelector("#conversationSessionSelect");
var conversationAutoSummaryInput = document.querySelector("#conversationAutoSummaryInput");
var conversationAutoSummaryTurnsInput = document.querySelector("#conversationAutoSummaryTurnsInput");
var conversationTreeContextInput = document.querySelector("#conversationTreeContextInput");
var conversationDirectChildCodeInput = document.querySelector("#conversationDirectChildCodeInput");
var conversationFontDecreaseButton = document.querySelector("#conversationFontDecreaseButton");
var conversationFontIncreaseButton = document.querySelector("#conversationFontIncreaseButton");
var conversationFontSizeValue = document.querySelector("#conversationFontSizeValue");
var closeConversationButton = document.querySelector("#closeConversationButton");
var normalPanel = document.querySelector("#normalPanel");
var panelTabs = document.querySelector("#panelTabs");
var panelWorldTab = document.querySelector("#panelWorldTab");
var panelSettingsTab = document.querySelector("#panelSettingsTab");
var panelHistoryTab = document.querySelector("#panelHistoryTab");
var panelDesignTab = document.querySelector("#panelDesignTab");
var panelGitHistoryTab = document.querySelector("#panelGitHistoryTab");
var panelCodeTab = document.querySelector("#panelCodeTab");
var panelWorldPane = document.querySelector("#panelWorldPane");
var panelSettingsPane = document.querySelector("#panelSettingsPane");
var panelHistoryPane = document.querySelector("#panelHistoryPane");
var panelDesignPane = document.querySelector("#panelDesignPane");
var panelGitHistoryPane = document.querySelector("#panelGitHistoryPane");
var conversationHistorySortSelect = document.querySelector("#conversationHistorySortSelect");
var conversationHistoryRefreshButton = document.querySelector("#conversationHistoryRefreshButton");
var conversationHistoryList = document.querySelector("#conversationHistoryList");
var designPanelNodeName = document.querySelector("#designPanelNodeName");
var designMarkdownView = document.querySelector("#designMarkdownView");
var copyDesignButton = document.querySelector("#copyDesignButton");
var gitHistoryRefreshButton = document.querySelector("#gitHistoryRefreshButton");
var gitHistoryMeta = document.querySelector("#gitHistoryMeta");
var gitHistoryList = document.querySelector("#gitHistoryList");
var titleInput = document.querySelector("#titleInput");
var bodyInput = document.querySelector("#bodyInput");
var powanKindInput = document.querySelector("#powanKindInput");
var codePanel = document.querySelector("#codePanel");
var codeInput = document.querySelector("#codeInput");
var codeLineNumbers = document.querySelector("#codeLineNumbers");
var codeEditorHost = document.querySelector("#codeEditorHost");
var codeEditorNodeName = document.querySelector("#codeEditorNodeName");
var codeLanguageSelect = document.querySelector("#codeLanguageSelect");
var closeCodeButton = document.querySelector("#closeCodeButton");
var codeEditor = null;
var codeEditorReady = null;
var codeEditorModules = null;
var currentCodeEditorLanguage = null;
var syncingCodeEditor = false;
var designPanelNodeId = null;
var gitHistoryLoading = false;
var shapeInput = document.querySelector("#shapeInput");
var colorInput = document.querySelector("#colorInput");
var accentInput = document.querySelector("#accentInput");
var glowInput = document.querySelector("#glowInput");
var blurInput = document.querySelector("#blurInput");
var motionInput = document.querySelector("#motionInput");
var randomColorInput = document.querySelector("#randomColorInput");
var titleFontFamilySelect = document.querySelector("#titleFontFamilySelect");
var titleFontScaleInput = document.querySelector("#titleFontScaleInput");
var titleFontScaleValue = document.querySelector("#titleFontScaleValue");
var titleOutlineInput = document.querySelector("#titleOutlineInput");
var titleOutlineColorInput = document.querySelector("#titleOutlineColorInput");
var titleOutlineWidthInput = document.querySelector("#titleOutlineWidthInput");
var titleOutlineWidthValue = document.querySelector("#titleOutlineWidthValue");
var titleShadowInput = document.querySelector("#titleShadowInput");
var titleShadowColorInput = document.querySelector("#titleShadowColorInput");
var titleShadowBlurInput = document.querySelector("#titleShadowBlurInput");
var titleShadowBlurValue = document.querySelector("#titleShadowBlurValue");
var titleShadowXInput = document.querySelector("#titleShadowXInput");
var titleShadowXValue = document.querySelector("#titleShadowXValue");
var titleShadowYInput = document.querySelector("#titleShadowYInput");
var titleShadowYValue = document.querySelector("#titleShadowYValue");
var conversationSoundSelect = document.querySelector("#conversationSoundSelect");
var conversationVolumeInput = document.querySelector("#conversationVolumeInput");
var conversationVolumeValue = document.querySelector("#conversationVolumeValue");
var inputSoundSelect = document.querySelector("#inputSoundSelect");
var inputVolumeInput = document.querySelector("#inputVolumeInput");
var inputVolumeValue = document.querySelector("#inputVolumeValue");
var addNodeButton = document.querySelector("#addNodeButton");
var addRootButton = document.querySelector("#addRootButton");
var deleteButton = document.querySelector("#deleteButton");
var backButton = document.querySelector("#backButton");
var worldName = document.querySelector("#worldName");
var worldPath = document.querySelector("#worldPath");

var projectName = "";
var documentName = "project.powan";
var doc = null;
var selectedId = null;
var selectedIds = new Set();
var selectionAnchorId = null;
var marqueeSelection = null;
var drag = null;
var nestedDrag = null;
var measureBox = null;
var pointerIntent = null;
var openParentId = null;
var childEditParentId = null;
var codePanelNodeId = null;
var activePanelTab = "world";
var nodeContextMenuNodeId = null;
var worldContextMenuOpen = false;
var worldContextMenuDropCenter = null;
var conversationNodeId = null;
var conversationTypingTimer = null;
var conversationTypingNodeId = null;
var conversationTypingTabId = null;
var conversationTypingMouthOpen = false;
var conversationBackgroundSpeakingTimers = new Map();
var conversationBackgroundSpeakingMouthOpenByNode = new Map();
var conversationRequestAbortController = null;
var conversationRequestNodeId = null;
var conversationRequestTabId = null;
var conversationRequestConversationId = null;
var conversationRequestWaitingText = "";
var conversationPendingMessage = null;
var conversationActiveRequests = new Map();
var conversationRequestSerial = 0;
var conversationQueuedSends = [];
var runningPowanRuns = new Map();
var runningPowanRefreshTimer = null;
var runningPowanConversationReloading = false;
var conversationWorkPollTimer = null;
var conversationWorkEventSequence = 0;
var conversationWorkPollingActive = false;
var conversationEventSource = null;
var conversationEventSourceKey = "";
var conversationLiveMessageIds = new Set();
var conversationCancelRequested = false;
var conversationSending = false;
var conversationActiveSessionId = null;
var conversationViewingSessionId = null;
var conversationViewingAllSessions = false;
var conversationSessionList = [];
var conversationTabs = [];
var conversationTabStates = new Map();
var activeConversationTabId = null;
var conversationTabSerial = 0;
var conversationRunningNotifiedRunIds = new Set();
var bulkCommandTargetIds = [];
var bulkCommandSending = false;
var conversationHistoryItems = [];
var conversationHistoryServerItems = [];
var conversationHistoryBulkServerItems = [];
var conversationHistorySort = "newest";
var conversationHistoryLoading = false;
var conversationPanelCollapsed = false;
var treePanelCollapsed = false;
var panelCollapsed = false;
var conversationFontSize = 13;
var nestedNameEditNodeId = null;
var treeNameEditNodeId = null;
var worldLayer = null;
var pan = null;
var panIntent = null;
var viewportBeforeInterior = null;
var viewportMotion = null;
var treeResize = null;
var panelResize = null;
var conversationResize = null;
var conversationInputResize = null;
var treeDragSourceId = null;
var subtreeImportTargetNodeId = null;
var worldTransition = null;
var documentSnapshot = "";
var undoStack = [];
var redoStack = [];
var historyGroupKey = null;
var autoReloadTimer = null;
var autoReloadInFlight = false;
var conversationAutoFollow = true;
var conversationAutoSummaryInFlight = false;
var conversationPendingAttachments = [];
var powanFaceTouchedAtById = new Map();
var powanFaceClockTimer = null;
var collapsedTreeNodeIds = new Set();
var appSettings = {
  randomPowanColor: false,
  conversationSound: "",
  conversationSoundVolume: 0.55,
  inputSound: "",
  inputSoundVolume: 0.55,
  restartVisibleConsole: false,
  autoSummaryEnabled: true,
  autoSummaryTurns: 50,
  titleFontFamily: "",
  titleFontScale: 1,
  titleOutlineEnabled: false,
  titleOutlineColor: "#ffffff",
  titleOutlineWidth: 1.5,
  titleShadowEnabled: true,
  titleShadowColor: "#ffffff",
  titleShadowBlur: 4,
  titleShadowX: 0,
  titleShadowY: 1,
  arrangeSpacing: 1,
  arrangeSize: 1,
  arrangeResizeParents: true,
  arrangeRecursive: true,
  arrangeChildSpacing: 1,
  arrangeChildSize: 1,
  arrangeNestedChildSize: 1,
  nestedLayerScale: 0.5,
  arrangeWorldParentSpacing: 1,
  arrangeWorldParentSize: 1,
};
var availableConversationSounds = [];
var conversationChunkAudio = null;
var conversationSoundIsPlaying = false;
var inputWaitingAudio = null;
var inputSoundIsPlaying = false;
var inputWaitingSoundOwner = "";

var viewport = {
  x: 0,
  y: 0,
  scale: 1,
};

var NODE_LIMITS = {
  minWidth: 180,
  minHeight: 104,
  maxWidth: 720,
  maxHeight: 620,
  paddingX: 46,
  paddingY: 46,
  edgeGuard: 28,
  titleBodyGap: 10,
};
var NESTED_NODE_LIMITS = {
  minWidth: 36,
  minHeight: 28,
  maxWidth: 420,
  maxHeight: 300,
};
var NESTED_PREVIEW_NODE_LIMITS = {
  minWidth: 10,
  minHeight: 6,
};

var DRAG_THRESHOLD_PX = 6;
var EMPTY_MEANING_PLACEHOLDER = "ポワンに意味を与えてね";
var MIN_VIEW_SCALE = 0.12;
var MAX_VIEW_SCALE = 12;
var ZOOM_STEP = 0.0015;
var AUTO_RELOAD_INTERVAL_MS = 1800;
var DEFAULT_CONVERSATION_AUTO_SUMMARY_TURNS = 50;
var MIN_CONVERSATION_AUTO_SUMMARY_TURNS = 2;
var MAX_CONVERSATION_AUTO_SUMMARY_TURNS = 500;
var DEFAULT_CONVERSATION_FONT_SIZE = 13;
var MIN_CONVERSATION_FONT_SIZE = 11;
var MAX_CONVERSATION_FONT_SIZE = 22;
var TITLE_FONT_FAMILY_VALUES = new Set([
  "",
  "Dela Gothic One",
  "Hachi Maru Pop",
  "Klee One",
  "RocknRoll One",
  "New Tegomin",
  "Train One",
  "DotGothic16",
  "Reggae One",
  "Yuji Syuku",
  "Yuji Boku",
  "Mochiy Pop One",
  "Kaisei HarunoUmi",
  "Shippori Antique",
  "Stick",
  "Rampart One",
  "Zen Antique",
  "Mochiy Pop P One",
  "Zen Kurenaido",
  "Yusei Magic",
]);
var DEFAULT_TITLE_FONT_STACK = '"Segoe UI", "Yu Gothic UI", "Yu Gothic", sans-serif';
var DEFAULT_TITLE_OUTLINE_WIDTH = 1.5;
var DEFAULT_TITLE_FONT_SCALE = 1;
var MIN_TITLE_FONT_SCALE = 0.5;
var MAX_TITLE_FONT_SCALE = 2.0;
var MIN_TITLE_OUTLINE_WIDTH = 0;
var MAX_TITLE_OUTLINE_WIDTH = 6;
var DEFAULT_TITLE_SHADOW_BLUR = 4;
var MIN_TITLE_SHADOW_BLUR = 0;
var MAX_TITLE_SHADOW_BLUR = 18;
var DEFAULT_TITLE_SHADOW_OFFSET = 0;
var MIN_TITLE_SHADOW_OFFSET = -12;
var MAX_TITLE_SHADOW_OFFSET = 12;
var DEFAULT_ARRANGE_SPACING = 1;
var MIN_ARRANGE_SPACING = 0.3;
var MAX_ARRANGE_SPACING = 3.0;
var DEFAULT_ARRANGE_SIZE = 1;
var MIN_ARRANGE_SIZE = 0.3;
var MAX_ARRANGE_SIZE = 2.5;
var DEFAULT_ARRANGE_TOGGLE = true;
var CONVERSATION_ALL_SESSIONS_VALUE = "all";
var POWAN_FACE_CLOCK_INTERVAL_MS = 1000;
var POWAN_FACE_CYCLE_MS = 30 * 1000;
var POWAN_FACE_MINUTE_MS = 60 * 1000;
var LAYOUT_STORAGE_KEY = "abc-canvas-layout";
var APP_SETTINGS_STORAGE_KEY = "abc-canvas-settings";
var BULK_COMMAND_HISTORY_STORAGE_PREFIX = "abc-canvas-bulk-command-history";
var LOG_LEVELS = {
  trace: 0,
  debug: 10,
  info: 20,
  warn: 30,
  error: 40,
  fatal: 50,
};
var CURRENT_LOG_LEVEL = "trace";
var LOG_ENDPOINT = "/api/logs/client";
var LOG_FLUSH_INTERVAL_MS = 250;
var LOG_QUEUE_LIMIT = 1200;
var LOG_FLUSH_BATCH_SIZE = 120;
var logQueue = [];
var logFlushTimer = null;
var FOCUSED_CLIENT_LOG_ACTIONS = new Set([
  "arrange-current-world-skip-revisited",
]);
var FOCUSED_CLIENT_LOG_PREFIXES = [
  "bulk-command-",
  "client-unhandled-",
];
var INTERIOR_STAGE = {
  x: 260,
  y: 180,
  width: 560,
  height: 360,
};
var WORLD_TRANSITION_MS = 380;
var HISTORY_LIMIT = 80;

function makeId() {
  return `node-${crypto.randomUUID().replaceAll("-", "").slice(0, 10)}`;
}

function sanitizeLogValue(value, depth = 0) {
  if (value == null || typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return value;
  }
  if (depth > 3) {
    return String(value);
  }
  if (Array.isArray(value)) {
    return value.slice(0, 40).map((item) => sanitizeLogValue(item, depth + 1));
  }
  if (typeof value === "object") {
    const safe = {};
    for (const [key, item] of Object.entries(value).slice(0, 80)) {
      safe[key] = sanitizeLogValue(item, depth + 1);
    }
    return safe;
  }
  return String(value);
}

function queueLogEntry(entry) {
  logQueue.push(sanitizeLogValue(entry));
  if (logQueue.length > LOG_QUEUE_LIMIT) {
    logQueue.splice(0, logQueue.length - LOG_QUEUE_LIMIT);
  }
  if (!logFlushTimer) {
    logFlushTimer = window.setTimeout(() => {
      logFlushTimer = null;
      flushLogQueue();
    }, LOG_FLUSH_INTERVAL_MS);
  }
}

function flushLogQueue({ beacon = false } = {}) {
  if (!logQueue.length) {
    return Promise.resolve();
  }
  const entries = logQueue.splice(0, Math.min(LOG_FLUSH_BATCH_SIZE, logQueue.length));
  const body = JSON.stringify({ entries });
  if (beacon && navigator.sendBeacon) {
    const sent = navigator.sendBeacon(LOG_ENDPOINT, new Blob([body], { type: "application/json" }));
    if (!sent) {
      logQueue.unshift(...entries.slice(-LOG_QUEUE_LIMIT));
    }
    if (logQueue.length) {
      window.setTimeout(() => flushLogQueue({ beacon: true }), 0);
    }
    return Promise.resolve();
  }
  return fetch(LOG_ENDPOINT, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body,
    keepalive: true,
  }).catch(() => {
    logQueue.unshift(...entries.slice(-LOG_QUEUE_LIMIT));
  }).finally(() => {
    if (logQueue.length && !logFlushTimer) {
      logFlushTimer = window.setTimeout(() => {
        logFlushTimer = null;
        flushLogQueue();
      }, LOG_FLUSH_INTERVAL_MS);
    }
  });
}

function shouldKeepClientLog(level, action) {
  if (level === "warn" || level === "error" || level === "fatal") {
    return true;
  }
  if (FOCUSED_CLIENT_LOG_ACTIONS.has(action)) {
    return true;
  }
  return FOCUSED_CLIENT_LOG_PREFIXES.some((prefix) => action.startsWith(prefix));
}

function logEvent(level, action, details = {}) {
  const current = LOG_LEVELS[CURRENT_LOG_LEVEL] ?? LOG_LEVELS.debug;
  const value = LOG_LEVELS[level] ?? LOG_LEVELS.info;
  if (value < current) {
    return;
  }
  if (!shouldKeepClientLog(level, action)) {
    return;
  }
  const payload = {
    action,
    projectName,
    documentName,
    selectedId,
    openParentId,
    ...details,
  };
  queueLogEntry({
    level,
    clientTime: new Date().toISOString(),
    ...payload,
  });
  const message = `[abc-canvas:${level}] ${action}`;
  if (level === "fatal" || level === "error") {
    console.error(message, payload);
  } else if (level === "warn") {
    console.warn(message, payload);
  } else {
    console.log(message, payload);
  }
}

function clientErrorLogPayload(error) {
  return {
    name: error?.name || "",
    message: error?.message || String(error || ""),
    stack: error?.stack ? String(error.stack).slice(0, 1400) : "",
  };
}

window.addEventListener("error", (event) => {
  try {
    logEvent("error", "client-unhandled-error", {
      message: event.message || "",
      source: event.filename || "",
      line: event.lineno || 0,
      column: event.colno || 0,
      error: clientErrorLogPayload(event.error || event.message),
    });
    flushLogQueue();
  } catch (loggingError) {
    console.error(loggingError);
  }
});

window.addEventListener("unhandledrejection", (event) => {
  try {
    logEvent("error", "client-unhandled-rejection", {
      error: clientErrorLogPayload(event.reason),
    });
    flushLogQueue();
  } catch (loggingError) {
    console.error(loggingError);
  }
});

window.addEventListener("pagehide", () => flushLogQueue({ beacon: true }));

function loadStoredLayout() {
  try {
    const stored = JSON.parse(localStorage.getItem(LAYOUT_STORAGE_KEY) || "{}");
    if (Number.isFinite(stored.treePanelWidth)) {
      setLayoutWidth("--tree-panel-width", stored.treePanelWidth, 160, 520);
    }
    if (Number.isFinite(stored.panelWidth)) {
      setLayoutWidth("--panel-width", stored.panelWidth, 260, 760);
    }
    if (Number.isFinite(stored.conversationPanelHeight)) {
      setConversationPanelHeight(stored.conversationPanelHeight, "load-conversation-panel-height", { persist: false });
    }
    if (Number.isFinite(stored.conversationInputHeight)) {
      setConversationInputHeight(stored.conversationInputHeight, "load-conversation-input-height", { persist: false });
    }
    setTreePanelCollapsed(Boolean(stored.treePanelCollapsed), "load-tree-panel-collapsed", { persist: false });
    setPanelCollapsed(Boolean(stored.panelCollapsed), "load-panel-collapsed", { persist: false });
    setConversationFontSize(stored.conversationFontSize, "load-conversation-font-size", { persist: false });
  } catch (error) {
    console.warn("Failed to load ABC Canvas layout", error);
  }
}

function saveStoredLayoutValue(key, value) {
  let stored = {};
  try {
    stored = JSON.parse(localStorage.getItem(LAYOUT_STORAGE_KEY) || "{}");
  } catch {
    stored = {};
  }
  stored[key] = value;
  localStorage.setItem(LAYOUT_STORAGE_KEY, JSON.stringify(stored));
}

function setLayoutWidth(property, value, min, max) {
  const width = Math.round(Math.min(max, Math.max(min, value)));
  document.documentElement.style.setProperty(property, `${width}px`);
  return width;
}

function setLayoutHeight(property, value, min, max) {
  const safeMax = Math.max(min, max);
  const height = Math.round(Math.min(safeMax, Math.max(min, value)));
  document.documentElement.style.setProperty(property, `${height}px`);
  return height;
}

function conversationPanelMaxHeight() {
  return Math.max(190, window.innerHeight - 28);
}

function currentConversationPanelHeight() {
  return Number.parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--conversation-panel-height")) || 280;
}

function currentConversationInputHeight() {
  return Number.parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--conversation-input-height")) || 56;
}

function conversationInputMaxHeight() {
  const panelHeight = currentConversationPanelHeight();
  return Math.max(40, Math.min(window.innerHeight - 140, panelHeight - 150));
}

function setConversationPanelHeight(value, reason = "set-conversation-panel-height", options = {}) {
  const height = setLayoutHeight("--conversation-panel-height", value, 190, conversationPanelMaxHeight());
  if (options.persist !== false) {
    saveStoredLayoutValue("conversationPanelHeight", height);
  }
  setConversationInputHeight(currentConversationInputHeight(), `${reason}-input-clamp`, options);
  logEvent("debug", reason, { height });
  return height;
}

function setConversationInputHeight(value, reason = "set-conversation-input-height", options = {}) {
  const height = setLayoutHeight("--conversation-input-height", value, 40, conversationInputMaxHeight());
  if (options.persist !== false) {
    saveStoredLayoutValue("conversationInputHeight", height);
  }
  logEvent("debug", reason, { height });
  return height;
}

function setTreePanelCollapsed(collapsed, reason = "set-tree-panel-collapsed", options = {}) {
  treePanelCollapsed = Boolean(collapsed);
  document.body.classList.toggle("tree-panel-collapsed", treePanelCollapsed);
  if (treePanel) {
    treePanel.classList.toggle("collapsed", treePanelCollapsed);
  }
  if (treePanelToggleButton) {
    treePanelToggleButton.textContent = treePanelCollapsed ? "›" : "‹";
    treePanelToggleButton.title = treePanelCollapsed ? "左ツリーを開く" : "左ツリーをしまう";
    treePanelToggleButton.setAttribute("aria-label", treePanelToggleButton.title);
  }
  if (options.persist !== false) {
    saveStoredLayoutValue("treePanelCollapsed", treePanelCollapsed);
  }
  logEvent("debug", reason, { collapsed: treePanelCollapsed });
}

function setPanelCollapsed(collapsed, reason = "set-panel-collapsed", options = {}) {
  panelCollapsed = Boolean(collapsed);
  document.body.classList.toggle("panel-collapsed", panelCollapsed);
  if (panel) {
    panel.classList.toggle("collapsed", panelCollapsed);
  }
  if (panelToggleButton) {
    panelToggleButton.textContent = panelCollapsed ? "‹" : "›";
    panelToggleButton.title = panelCollapsed ? "右メニューを開く" : "右メニューをしまう";
    panelToggleButton.setAttribute("aria-label", panelToggleButton.title);
  }
  if (options.persist !== false) {
    saveStoredLayoutValue("panelCollapsed", panelCollapsed);
  }
  logEvent("debug", reason, { collapsed: panelCollapsed });
}

function normalizeConversationFontSize(value) {
  const size = Number.parseInt(value, 10);
  if (!Number.isFinite(size)) {
    return DEFAULT_CONVERSATION_FONT_SIZE;
  }
  return Math.min(MAX_CONVERSATION_FONT_SIZE, Math.max(MIN_CONVERSATION_FONT_SIZE, size));
}

function setConversationFontSize(value, reason = "set-conversation-font-size", options = {}) {
  conversationFontSize = normalizeConversationFontSize(value);
  document.documentElement.style.setProperty("--conversation-font-size", `${conversationFontSize}px`);
  if (conversationFontSizeValue) {
    conversationFontSizeValue.textContent = String(conversationFontSize);
  }
  if (conversationFontDecreaseButton) {
    conversationFontDecreaseButton.disabled = conversationFontSize <= MIN_CONVERSATION_FONT_SIZE;
  }
  if (conversationFontIncreaseButton) {
    conversationFontIncreaseButton.disabled = conversationFontSize >= MAX_CONVERSATION_FONT_SIZE;
  }
  if (options.persist !== false) {
    saveStoredLayoutValue("conversationFontSize", conversationFontSize);
  }
  logEvent("debug", reason, { fontSize: conversationFontSize });
}

function loadStoredSettings() {
  let stored = {};
  try {
    stored = JSON.parse(localStorage.getItem(APP_SETTINGS_STORAGE_KEY) || "{}");
  } catch {
    stored = {};
  }
  appSettings.randomPowanColor = Boolean(stored.randomPowanColor);
  appSettings.conversationSound = typeof stored.conversationSound === "string" ? stored.conversationSound : "";
  appSettings.conversationSoundVolume = normalizeConversationSoundVolume(stored.conversationSoundVolume);
  appSettings.inputSound = typeof stored.inputSound === "string" ? stored.inputSound : "";
  appSettings.inputSoundVolume = normalizeConversationSoundVolume(stored.inputSoundVolume);
  appSettings.restartVisibleConsole = Boolean(stored.restartVisibleConsole);
  appSettings.autoSummaryEnabled = stored.autoSummaryEnabled !== false;
  appSettings.autoSummaryTurns = normalizeConversationAutoSummaryTurns(stored.autoSummaryTurns);
  applyTitleStyleSettings(stored);
  applyArrangeSettings(stored);
  syncSettingsInputs();
}

function saveStoredSettings() {
  localStorage.setItem(APP_SETTINGS_STORAGE_KEY, JSON.stringify(appSettings));
}

function normalizeTitleFontFamily(value) {
  const clean = String(value || "").trim();
  return TITLE_FONT_FAMILY_VALUES.has(clean) ? clean : "";
}

function titleFontFamilyCss(value) {
  const family = normalizeTitleFontFamily(value);
  if (!family) {
    return DEFAULT_TITLE_FONT_STACK;
  }
  return `"${family.replaceAll("\"", "\\\"")}", ${DEFAULT_TITLE_FONT_STACK}`;
}

function applyTitleFontOptionStyles() {
  if (!titleFontFamilySelect) {
    return;
  }
  for (const option of titleFontFamilySelect.options) {
    option.style.fontFamily = titleFontFamilyCss(option.value);
  }
  titleFontFamilySelect.style.fontFamily = titleFontFamilyCss(titleFontFamilySelect.value);
}

function normalizeTitleFontScale(value) {
  return clampNumber(value, DEFAULT_TITLE_FONT_SCALE, MIN_TITLE_FONT_SCALE, MAX_TITLE_FONT_SCALE);
}

function normalizeHexColor(value, fallback = "#ffffff") {
  const clean = String(value || "").trim();
  return /^#[0-9a-fA-F]{6}$/.test(clean) ? clean.toLowerCase() : fallback;
}

function clampNumber(value, fallback, min, max) {
  const number = Number(value);
  if (!Number.isFinite(number)) {
    return fallback;
  }
  return Math.min(max, Math.max(min, number));
}

function normalizeTitleOutlineWidth(value) {
  return clampNumber(value, DEFAULT_TITLE_OUTLINE_WIDTH, MIN_TITLE_OUTLINE_WIDTH, MAX_TITLE_OUTLINE_WIDTH);
}

function normalizeTitleShadowBlur(value) {
  return clampNumber(value, DEFAULT_TITLE_SHADOW_BLUR, MIN_TITLE_SHADOW_BLUR, MAX_TITLE_SHADOW_BLUR);
}

function normalizeTitleShadowOffset(value, fallback = DEFAULT_TITLE_SHADOW_OFFSET) {
  return clampNumber(value, fallback, MIN_TITLE_SHADOW_OFFSET, MAX_TITLE_SHADOW_OFFSET);
}

function titleStylePayload() {
  return {
    titleFontFamily: appSettings.titleFontFamily,
    titleFontScale: appSettings.titleFontScale,
    titleOutlineEnabled: appSettings.titleOutlineEnabled,
    titleOutlineColor: appSettings.titleOutlineColor,
    titleOutlineWidth: appSettings.titleOutlineWidth,
    titleShadowEnabled: appSettings.titleShadowEnabled,
    titleShadowColor: appSettings.titleShadowColor,
    titleShadowBlur: appSettings.titleShadowBlur,
    titleShadowX: appSettings.titleShadowX,
    titleShadowY: appSettings.titleShadowY,
  };
}

function applyTitleStyleSettings(data = {}) {
  appSettings.titleFontFamily = normalizeTitleFontFamily(data.titleFontFamily ?? appSettings.titleFontFamily);
  appSettings.titleFontScale = normalizeTitleFontScale(data.titleFontScale ?? appSettings.titleFontScale);
  appSettings.titleOutlineEnabled = Boolean(data.titleOutlineEnabled ?? appSettings.titleOutlineEnabled);
  appSettings.titleOutlineColor = normalizeHexColor(data.titleOutlineColor ?? appSettings.titleOutlineColor, "#ffffff");
  appSettings.titleOutlineWidth = normalizeTitleOutlineWidth(data.titleOutlineWidth ?? appSettings.titleOutlineWidth);
  appSettings.titleShadowEnabled = data.titleShadowEnabled == null
    ? Boolean(appSettings.titleShadowEnabled)
    : Boolean(data.titleShadowEnabled);
  appSettings.titleShadowColor = normalizeHexColor(data.titleShadowColor ?? appSettings.titleShadowColor, "#ffffff");
  appSettings.titleShadowBlur = normalizeTitleShadowBlur(data.titleShadowBlur ?? appSettings.titleShadowBlur);
  appSettings.titleShadowX = normalizeTitleShadowOffset(data.titleShadowX ?? appSettings.titleShadowX, 0);
  appSettings.titleShadowY = normalizeTitleShadowOffset(data.titleShadowY ?? appSettings.titleShadowY, 1);

  const outlineWidth = appSettings.titleOutlineEnabled ? appSettings.titleOutlineWidth : 0;
  const halfBlur = Math.max(0, appSettings.titleShadowBlur / 2);
  const shadow = appSettings.titleShadowEnabled
    ? `0 0 ${halfBlur.toFixed(2)}px ${appSettings.titleShadowColor}, ${appSettings.titleShadowX.toFixed(2)}px ${appSettings.titleShadowY.toFixed(2)}px ${appSettings.titleShadowBlur.toFixed(2)}px ${appSettings.titleShadowColor}`
    : "none";
  document.documentElement.style.setProperty("--powan-title-font-family", titleFontFamilyCss(appSettings.titleFontFamily));
  document.documentElement.style.setProperty("--powan-title-font-scale", appSettings.titleFontScale.toFixed(2));
  document.documentElement.style.setProperty("--powan-title-outline-width", `${outlineWidth.toFixed(2)}px`);
  document.documentElement.style.setProperty("--powan-title-outline-color", appSettings.titleOutlineColor);
  document.documentElement.style.setProperty("--powan-title-shadow", shadow);
  if (titleFontFamilySelect) {
    titleFontFamilySelect.style.fontFamily = titleFontFamilyCss(appSettings.titleFontFamily);
  }
}

function applyArrangeSettings(data = {}) {
  appSettings.arrangeSpacing = normalizeArrangeSpacing(data.arrangeSpacing);
  appSettings.arrangeSize = normalizeArrangeSize(data.arrangeSize);
  appSettings.arrangeResizeParents = data.arrangeResizeParents !== false;
  appSettings.arrangeRecursive = data.arrangeRecursive !== false;
  appSettings.arrangeChildSpacing = normalizeArrangeSpacing(data.arrangeChildSpacing ?? data.arrangeSpacing);
  appSettings.arrangeChildSize = normalizeArrangeSize(data.arrangeChildSize ?? data.arrangeSize);
  appSettings.arrangeNestedChildSize = normalizeArrangeSize(data.arrangeNestedChildSize ?? data.arrangeSize);
  appSettings.nestedLayerScale = normalizeNestedLayerScale(data.nestedLayerScale ?? appSettings.nestedLayerScale);
  appSettings.arrangeWorldParentSpacing = normalizeArrangeSpacing(data.arrangeWorldParentSpacing ?? data.arrangeSpacing);
  appSettings.arrangeWorldParentSize = normalizeArrangeSize(data.arrangeWorldParentSize ?? data.arrangeSize);
  document.documentElement.style.setProperty("--nested-layer-scale", appSettings.nestedLayerScale.toFixed(2));
}

function syncSettingsInputs() {
  if (randomColorInput) {
    randomColorInput.checked = appSettings.randomPowanColor;
  }
  if (conversationSoundSelect) {
    conversationSoundSelect.value = appSettings.conversationSound;
  }
  if (conversationVolumeInput) {
    conversationVolumeInput.value = String(appSettings.conversationSoundVolume);
  }
  if (conversationVolumeValue) {
    conversationVolumeValue.textContent = `${Math.round(appSettings.conversationSoundVolume * 100)}%`;
  }
  if (inputSoundSelect) {
    inputSoundSelect.value = appSettings.inputSound;
  }
  if (inputVolumeInput) {
    inputVolumeInput.value = String(appSettings.inputSoundVolume);
  }
  if (inputVolumeValue) {
    inputVolumeValue.textContent = `${Math.round(appSettings.inputSoundVolume * 100)}%`;
  }
  if (conversationAutoSummaryInput) {
    conversationAutoSummaryInput.checked = Boolean(appSettings.autoSummaryEnabled);
  }
  if (conversationAutoSummaryTurnsInput) {
    conversationAutoSummaryTurnsInput.value = String(appSettings.autoSummaryTurns);
  }
  syncTitleStyleInputs();
  syncArrangePanelInputs();
}

function setRangeControl(input, output, value) {
  if (input) {
    input.value = String(value);
  }
  if (output) {
    output.textContent = Number(value).toFixed(2);
  }
}

function syncTitleStyleInputs() {
  applyTitleStyleSettings(appSettings);
  if (titleFontFamilySelect) {
    titleFontFamilySelect.value = appSettings.titleFontFamily;
    applyTitleFontOptionStyles();
  }
  setRangeControl(titleFontScaleInput, titleFontScaleValue, appSettings.titleFontScale);
  if (titleOutlineInput) {
    titleOutlineInput.checked = Boolean(appSettings.titleOutlineEnabled);
  }
  if (titleOutlineColorInput) {
    titleOutlineColorInput.value = appSettings.titleOutlineColor;
    titleOutlineColorInput.disabled = !appSettings.titleOutlineEnabled;
  }
  setRangeControl(titleOutlineWidthInput, titleOutlineWidthValue, appSettings.titleOutlineWidth);
  if (titleOutlineWidthInput) {
    titleOutlineWidthInput.disabled = !appSettings.titleOutlineEnabled;
  }
  if (titleShadowInput) {
    titleShadowInput.checked = Boolean(appSettings.titleShadowEnabled);
  }
  if (titleShadowColorInput) {
    titleShadowColorInput.value = appSettings.titleShadowColor;
    titleShadowColorInput.disabled = !appSettings.titleShadowEnabled;
  }
  setRangeControl(titleShadowBlurInput, titleShadowBlurValue, appSettings.titleShadowBlur);
  setRangeControl(titleShadowXInput, titleShadowXValue, appSettings.titleShadowX);
  setRangeControl(titleShadowYInput, titleShadowYValue, appSettings.titleShadowY);
  for (const input of [titleShadowBlurInput, titleShadowXInput, titleShadowYInput]) {
    if (input) {
      input.disabled = !appSettings.titleShadowEnabled;
    }
  }
}

function syncArrangePanelInputs() {
  if (panelArrangeResizeParentsInput) {
    panelArrangeResizeParentsInput.checked = Boolean(appSettings.arrangeResizeParents);
  }
  if (panelArrangeRecursiveInput) {
    panelArrangeRecursiveInput.checked = Boolean(appSettings.arrangeRecursive);
  }
  setRangeControl(panelArrangeChildSpacingInput, panelArrangeChildSpacingValue, appSettings.arrangeWorldParentSpacing);
  setRangeControl(panelArrangeChildSizeInput, panelArrangeChildSizeValue, appSettings.arrangeWorldParentSize);
  setRangeControl(panelArrangeNestedChildSizeInput, panelArrangeNestedChildSizeValue, appSettings.arrangeNestedChildSize);
  setRangeControl(panelNestedLayerScaleInput, panelNestedLayerScaleValue, appSettings.nestedLayerScale);
  setRangeControl(panelArrangeWorldParentSpacingInput, panelArrangeWorldParentSpacingValue, appSettings.arrangeChildSpacing);
  setRangeControl(panelArrangeWorldParentSizeInput, panelArrangeWorldParentSizeValue, appSettings.arrangeChildSize);
}

function setRandomPowanColor(enabled, reason = "set-random-powan-color") {
  appSettings.randomPowanColor = Boolean(enabled);
  syncSettingsInputs();
  saveStoredSettings();
  logEvent("info", reason, { enabled: appSettings.randomPowanColor });
}

function setConversationSound(name, reason = "set-conversation-sound") {
  appSettings.conversationSound = name || "";
  stopConversationChunkSound("conversation-sound-changed");
  conversationChunkAudio = null;
  syncSettingsInputs();
  saveStoredSettings();
  logEvent("info", reason, { name: appSettings.conversationSound });
}

function normalizeConversationSoundVolume(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) {
    return 0.55;
  }
  return Math.min(1, Math.max(0, number));
}

function normalizeArrangeSpacing(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) {
    return DEFAULT_ARRANGE_SPACING;
  }
  return Math.min(MAX_ARRANGE_SPACING, Math.max(MIN_ARRANGE_SPACING, number));
}

function normalizeArrangeSize(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) {
    return DEFAULT_ARRANGE_SIZE;
  }
  return Math.min(MAX_ARRANGE_SIZE, Math.max(MIN_ARRANGE_SIZE, number));
}

function normalizeNestedLayerScale(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) {
    return 0.5;
  }
  return Math.min(1.0, Math.max(0.3, number));
}

function normalizeConversationAutoSummaryTurns(value) {
  const number = Number.parseInt(value, 10);
  if (!Number.isFinite(number)) {
    return DEFAULT_CONVERSATION_AUTO_SUMMARY_TURNS;
  }
  return Math.min(MAX_CONVERSATION_AUTO_SUMMARY_TURNS, Math.max(MIN_CONVERSATION_AUTO_SUMMARY_TURNS, number));
}

function setConversationSoundVolume(value, reason = "set-conversation-sound-volume") {
  appSettings.conversationSoundVolume = normalizeConversationSoundVolume(value);
  if (conversationChunkAudio) {
    conversationChunkAudio.volume = appSettings.conversationSoundVolume;
    if (conversationSoundIsPlaying && appSettings.conversationSoundVolume <= 0) {
      stopConversationChunkSound("conversation-volume-zero");
    }
  }
  syncSettingsInputs();
  saveStoredSettings();
  logEvent("info", reason, { volume: appSettings.conversationSoundVolume });
}

function setInputSound(name, reason = "set-input-sound") {
  appSettings.inputSound = name || "";
  stopInputWaitingSound("input-sound-changed");
  inputWaitingAudio = null;
  syncSettingsInputs();
  saveStoredSettings();
  logEvent("info", reason, { name: appSettings.inputSound });
}

function setInputSoundVolume(value, reason = "set-input-sound-volume") {
  appSettings.inputSoundVolume = normalizeConversationSoundVolume(value);
  if (inputWaitingAudio) {
    inputWaitingAudio.volume = appSettings.inputSoundVolume;
    if (inputSoundIsPlaying && appSettings.inputSoundVolume <= 0) {
      stopInputWaitingSound("input-volume-zero");
    }
  }
  syncSettingsInputs();
  saveStoredSettings();
  logEvent("info", reason, { volume: appSettings.inputSoundVolume });
}

function setConversationAutoSummary(enabled, turns, reason = "set-conversation-auto-summary") {
  appSettings.autoSummaryEnabled = Boolean(enabled);
  appSettings.autoSummaryTurns = normalizeConversationAutoSummaryTurns(turns);
  syncSettingsInputs();
  saveStoredSettings();
  logEvent("info", reason, {
    enabled: appSettings.autoSummaryEnabled,
    turns: appSettings.autoSummaryTurns,
  });
}

function setTitleStyleFromInputs(reason = "set-title-style") {
  appSettings.titleFontFamily = normalizeTitleFontFamily(titleFontFamilySelect?.value);
  appSettings.titleFontScale = normalizeTitleFontScale(titleFontScaleInput?.value);
  appSettings.titleOutlineEnabled = Boolean(titleOutlineInput?.checked);
  appSettings.titleOutlineColor = normalizeHexColor(titleOutlineColorInput?.value, appSettings.titleOutlineColor);
  appSettings.titleOutlineWidth = normalizeTitleOutlineWidth(titleOutlineWidthInput?.value);
  appSettings.titleShadowEnabled = Boolean(titleShadowInput?.checked);
  appSettings.titleShadowColor = normalizeHexColor(titleShadowColorInput?.value, appSettings.titleShadowColor);
  appSettings.titleShadowBlur = normalizeTitleShadowBlur(titleShadowBlurInput?.value);
  appSettings.titleShadowX = normalizeTitleShadowOffset(titleShadowXInput?.value, 0);
  appSettings.titleShadowY = normalizeTitleShadowOffset(titleShadowYInput?.value, 1);
  applyTitleStyleSettings(appSettings);
  syncTitleStyleInputs();
  saveStoredSettings();
  logEvent("info", reason, titleStylePayload());
}

function defaultNode({ title = "", x = null, y = null, parent = null, attachment = null } = {}) {
  const width = powanWorkspace.defaultNodeSize.width;
  const height = powanWorkspace.defaultNodeSize.height;
  const position = Number.isFinite(Number(x)) && Number.isFinite(Number(y))
    ? { x: Number(x), y: Number(y) }
    : powanWorkspace.topLeftForCenter(powanWorkspace.origin, width, height);
  const node = {
    id: makeId(),
    title,
    body: "",
    powanKind: "nerve",
    code: "",
    parent,
    children: [],
    style: powanWorkspace.nodeStyle({ randomize: appSettings.randomPowanColor }),
    layout: powanWorkspace.clampLayout({
      x: position.x,
      y: position.y,
      width,
      height,
    }),
  };
  if (attachment) {
    node.attachment = attachment;
  }
  return node;
}

function nodeById(id) {
  return doc.nodes.find((node) => node.id === id && !isArchivedNode(node)) || null;
}

function isArchivedNode(node) {
  return Boolean(node?.archived);
}

function activeNodes() {
  return doc.nodes.filter((node) => !isArchivedNode(node));
}

function firstActiveNode() {
  return activeNodes()[0] || null;
}

function nodeElementById(id) {
  return getWorldLayer().querySelector(`.node[data-id="${id}"]`);
}

function getWorldLayer() {
  if (worldLayer) {
    return worldLayer;
  }
  worldLayer = document.createElement("div");
  worldLayer.className = "world-layer";
  canvas.appendChild(worldLayer);
  applyViewportTransform();
  return worldLayer;
}

function applyViewportTransform() {
  if (!worldLayer) {
    return;
  }
  worldLayer.style.transform = `translate(${viewport.x}px, ${viewport.y}px) scale(${viewport.scale})`;
  if (canvas) {
    canvas.style.setProperty("--abc-view-scale", viewport.scale.toFixed(4));
  }
  if (typeof powanSoftBodyView !== "undefined") {
    powanSoftBodyView.refreshViewportResolution();
  }
}

function setViewportRaw(nextViewport) {
  viewport.x = finiteViewportNumber(nextViewport.x, viewport.x);
  viewport.y = finiteViewportNumber(nextViewport.y, viewport.y);
  viewport.scale = clampViewScale(finiteViewportNumber(nextViewport.scale, viewport.scale));
  applyViewportTransform();
}

function stopViewportMotion({ finish = false } = {}) {
  const motion = viewportMotion;
  if (!motion) {
    return;
  }
  if (motion.frameId) {
    cancelAnimationFrame(motion.frameId);
  }
  viewportMotion = null;
  if (finish) {
    setViewportRaw(motion.target);
  }
}

function viewportMotionEase(progress) {
  const t = Math.max(0, Math.min(1, progress));
  return 1 - Math.pow(1 - t, 3);
}

function viewportStateForRect(rect, padding = 72) {
  const canvasWidth = Math.max(1, canvas.clientWidth);
  const canvasHeight = Math.max(1, canvas.clientHeight);
  const targetWidth = Math.max(1, Number(rect?.width || 0) + padding * 2);
  const targetHeight = Math.max(1, Number(rect?.height || 0) + padding * 2);
  const scale = clampViewScale(Math.min(canvasWidth / targetWidth, canvasHeight / targetHeight));
  return {
    scale,
    x: canvasWidth / 2 - (Number(rect?.x || 0) + Number(rect?.width || 0) / 2) * scale,
    y: canvasHeight / 2 - (Number(rect?.y || 0) + Number(rect?.height || 0) / 2) * scale,
  };
}

function animateViewportToState(target, { reason = "viewport-motion", duration = 520 } = {}) {
  const next = {
    x: finiteViewportNumber(target?.x, viewport.x),
    y: finiteViewportNumber(target?.y, viewport.y),
    scale: clampViewScale(finiteViewportNumber(target?.scale, viewport.scale)),
  };
  stopViewportMotion();
  const from = {
    x: finiteViewportNumber(viewport.x, 0),
    y: finiteViewportNumber(viewport.y, 0),
    scale: clampViewScale(finiteViewportNumber(viewport.scale, 1)),
  };
  const distance = Math.max(
    Math.abs(from.x - next.x),
    Math.abs(from.y - next.y),
    Math.abs(from.scale - next.scale) * 1000,
  );
  if (distance < 0.5) {
    setViewportRaw(next);
    return false;
  }
  const startedAt = performance.now();
  viewportMotion = {
    frameId: null,
    target: next,
    reason,
  };
  const activeMotion = viewportMotion;
  const step = (timestamp) => {
    const motion = viewportMotion;
    if (!motion || motion !== activeMotion) {
      return;
    }
    const progress = Math.min(1, (timestamp - startedAt) / Math.max(1, duration));
    const eased = viewportMotionEase(progress);
    setViewportRaw({
      x: from.x + (next.x - from.x) * eased,
      y: from.y + (next.y - from.y) * eased,
      scale: from.scale + (next.scale - from.scale) * eased,
    });
    if (progress < 1) {
      motion.frameId = requestAnimationFrame(step);
      return;
    }
    viewportMotion = null;
    setViewportRaw(next);
    logEvent("debug", "viewport-motion-complete", {
      reason,
      viewport: normalizedViewportState(),
    });
  };
  viewportMotion.frameId = requestAnimationFrame(step);
  logEvent("debug", "viewport-motion-start", {
    reason,
    from,
    to: next,
  });
  return true;
}

function animateViewportToRect(rect, padding = 72, options = {}) {
  return animateViewportToState(viewportStateForRect(rect, padding), options);
}

function screenToWorld(clientX, clientY) {
  const rect = canvas.getBoundingClientRect();
  return {
    x: (clientX - rect.left - viewport.x) / viewport.scale,
    y: (clientY - rect.top - viewport.y) / viewport.scale,
  };
}

function clampViewScale(scale) {
  return Math.min(MAX_VIEW_SCALE, Math.max(MIN_VIEW_SCALE, scale));
}

function finiteViewportNumber(value, fallback) {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
}

function normalizedViewportState(source = viewport) {
  return {
    x: Math.round(finiteViewportNumber(source.x, 0)),
    y: Math.round(finiteViewportNumber(source.y, 0)),
    scale: Number(clampViewScale(finiteViewportNumber(source.scale, 1)).toFixed(4)),
    openParentId: openParentId || null,
  };
}

function storedViewportState(nextDoc) {
  const stored = nextDoc?.canvas?.viewport;
  if (!stored || typeof stored !== "object" || Array.isArray(stored)) {
    return null;
  }
  return {
    x: Math.round(finiteViewportNumber(stored.x, 0)),
    y: Math.round(finiteViewportNumber(stored.y, 0)),
    scale: clampViewScale(finiteViewportNumber(stored.scale, 1)),
    openParentId: typeof stored.openParentId === "string" ? stored.openParentId : null,
  };
}

function applyViewportState(nextViewport) {
  stopViewportMotion();
  setViewportRaw({
    x: Math.round(finiteViewportNumber(nextViewport.x, 0)),
    y: Math.round(finiteViewportNumber(nextViewport.y, 0)),
    scale: clampViewScale(finiteViewportNumber(nextViewport.scale, 1)),
  });
}

function saveViewportToDocument() {
  if (!doc) {
    return null;
  }
  powanWorkspace.ensureCanvas(doc).workspace = powanWorkspace.documentState();
  const nextViewport = normalizedViewportState();
  doc.canvas.viewport = nextViewport;
  logEvent("debug", "save-viewport-state", { viewport: nextViewport });
  return nextViewport;
}

// 古いデータや外部インポートで layout が欠けている子だけを、共通 placement で補完する。
// 親 → 子の順（top-down）で巡回し、親の layout が決まってから子を配置する。
function fillMissingChildLayouts(nextDoc) {
  const nodes = Array.isArray(nextDoc?.nodes) ? nextDoc.nodes : [];
  if (!nodes.length || typeof powanPlacement === "undefined") {
    return nextDoc;
  }
  const byId = new Map(nodes.map((node) => [node.id, node]));
  const orderedChildren = (parent) => {
    const seen = new Set();
    const ordered = [];
    for (const id of parent.children || []) {
      const child = byId.get(id);
      if (child && child.parent === parent.id && !seen.has(child.id)) {
        seen.add(child.id);
        ordered.push(child);
      }
    }
    for (const node of nodes) {
      if (node.parent === parent.id && !seen.has(node.id)) {
        seen.add(node.id);
        ordered.push(node);
      }
    }
    return ordered;
  };
  const visited = new Set();
  let filled = 0;
  const visit = (parent) => {
    const children = orderedChildren(parent);
    if (children.length) {
      const plans = powanPlacement.planParentChildren(parent, children);
      for (const plan of plans) {
        const child = plan.node;
        if (!powanPlacement.hasWorldLayout(child)) {
          child.layout = { ...(child.layout || {}), ...plan.worldLayout };
          filled += 1;
        }
        if (!powanPlacement.hasNestedLayout(child, parent.id)) {
          child.nestedLayoutByParent = child.nestedLayoutByParent || {};
          child.nestedLayoutByParent[parent.id] = plan.nestedLayout;
          filled += 1;
        }
      }
    }
    for (const child of children) {
      if (!visited.has(child.id)) {
        visited.add(child.id);
        visit(child);
      }
    }
  };
  for (const root of nodes.filter((node) => !node.parent || !byId.has(node.parent))) {
    if (!visited.has(root.id)) {
      visited.add(root.id);
      visit(root);
    }
  }
  if (filled) {
    logEvent("debug", "fill-missing-child-layouts", { filled });
  }
  return nextDoc;
}

function normalizeDocumentWorkspace(nextDoc, reason = "normalize-document-workspace") {
  const result = powanWorkspace.ensureDocument(nextDoc);
  if (result.migrated) {
    logEvent("info", reason, { workspace: result.doc.canvas.workspace });
  }
  fillMissingChildLayouts(result.doc);
  return result.doc;
}

function focusViewportOnPoint(point, scale = 1) {
  stopViewportMotion();
  const canvasWidth = Math.max(1, canvas.clientWidth);
  const canvasHeight = Math.max(1, canvas.clientHeight);
  const nextScale = clampViewScale(scale);
  setViewportRaw({
    scale: nextScale,
    x: canvasWidth / 2 - point.x * nextScale,
    y: canvasHeight / 2 - point.y * nextScale,
  });
}

function resetViewportToWorkspaceOrigin() {
  focusViewportOnPoint(powanWorkspace.origin, 1);
}

function restoreViewportFromDocument(nextDoc, { resetMissing = true, restoreWorld = true, reason = "restore-viewport-state" } = {}) {
  const nextViewport = storedViewportState(nextDoc);
  if (!nextViewport) {
    if (resetMissing) {
      resetViewportToWorkspaceOrigin();
      if (restoreWorld) {
        openParentId = null;
        viewportBeforeInterior = null;
      }
      logEvent("debug", reason, { restored: false, viewport: normalizedViewportState() });
    }
    return false;
  }
  applyViewportState(nextViewport);
  if (restoreWorld) {
    openParentId = nextViewport.openParentId && nodeById(nextViewport.openParentId) ? nextViewport.openParentId : null;
    viewportBeforeInterior = null;
  }
  logEvent("debug", reason, { restored: true, viewport: normalizedViewportState() });
  return true;
}

function zoomAt(clientX, clientY, nextScale) {
  stopViewportMotion();
  const rect = canvas.getBoundingClientRect();
  const before = screenToWorld(clientX, clientY);
  const scale = clampViewScale(nextScale);
  setViewportRaw({
    scale,
    x: clientX - rect.left - before.x * scale,
    y: clientY - rect.top - before.y * scale,
  });
}

function focusViewportOnRect(rect, padding = 72) {
  stopViewportMotion();
  setViewportRaw(viewportStateForRect(rect, padding));
}

function rememberViewportBeforeInterior() {
  if (viewportBeforeInterior) {
    return;
  }
  viewportBeforeInterior = {
    x: viewport.x,
    y: viewport.y,
    scale: viewport.scale,
  };
}

function restoreViewportBeforeInterior() {
  if (!viewportBeforeInterior) {
    return;
  }
  stopViewportMotion();
  setViewportRaw(viewportBeforeInterior);
  viewportBeforeInterior = null;
}

function setViewportForInteriorWorld(parent) {
  const worldArea = typeof powanPlacement !== "undefined"
    ? powanPlacement.parentWorldArea(parent)
    : {
        x: powanWorkspace.origin.x - INTERIOR_STAGE.width / 2,
        y: powanWorkspace.origin.y - INTERIOR_STAGE.height / 2,
        width: INTERIOR_STAGE.width,
        height: INTERIOR_STAGE.height,
      };
  focusViewportOnRect(worldArea, 64);
}

function currentWorldParent() {
  return openParentId ? nodeById(openParentId) : null;
}

function currentWorldOrigin() {
  return {
    x: 0,
    y: 0,
  };
}

function currentWorldNodes() {
  if (!openParentId) {
    const roots = rootNodes();
    if (!childEditParentId) {
      return roots;
    }
    return [...roots, ...meaningChildren(nodeById(childEditParentId))];
  }
  const parent = currentWorldParent();
  return parent ? meaningChildren(parent) : [];
}

function rootNodes() {
  return activeNodes().filter((node) => !node.parent || !nodeById(node.parent));
}

function displayLayoutForNode(node) {
  const layout = node.layout || {};
  const origin = currentWorldOrigin();
  return {
    x: Number(layout.x || 0) - origin.x,
    y: Number(layout.y || 0) - origin.y,
    width: Number(layout.width || 240),
    height: Number(layout.height || 140),
  };
}

function visibleWorldCenter() {
  const rect = canvas.getBoundingClientRect();
  const point = screenToWorld(rect.left + rect.width / 2, rect.top + rect.height / 2);
  const origin = currentWorldOrigin();
  return powanWorkspace.clampPoint({
    x: Math.round(origin.x + point.x),
    y: Math.round(origin.y + point.y),
  });
}

function beginPan(event) {
  event.preventDefault();
  stopViewportMotion();
  window.getSelection()?.removeAllRanges();
  panIntent = null;
  pan = {
    pointerId: event.pointerId,
    startX: event.clientX,
    startY: event.clientY,
    viewX: viewport.x,
    viewY: viewport.y,
    moved: false,
  };
  document.body.classList.add("panning-canvas");
  canvas.setPointerCapture(event.pointerId);
}

function beginPanIntent(event, details = {}) {
  if (event.button !== 0) {
    return;
  }
  panIntent = {
    pointerId: event.pointerId,
    startX: event.clientX,
    startY: event.clientY,
    viewX: viewport.x,
    viewY: viewport.y,
    details,
  };
  logEvent("trace", "pan-intent-start", {
    pointerId: event.pointerId,
    startX: Math.round(event.clientX),
    startY: Math.round(event.clientY),
    ...details,
  });
}

function startPanFromIntent(intent, event) {
  event.preventDefault();
  stopViewportMotion();
  window.getSelection()?.removeAllRanges();
  pan = {
    pointerId: intent.pointerId,
    startX: intent.startX,
    startY: intent.startY,
    viewX: intent.viewX,
    viewY: intent.viewY,
    moved: true,
  };
  panIntent = null;
  document.body.classList.add("panning-canvas");
  try {
    canvas.setPointerCapture(intent.pointerId);
  } catch (error) {
    logEvent("trace", "pan-capture-skipped", { message: error.message });
  }
  logEvent("trace", "pan-intent-threshold", {
    pointerId: intent.pointerId,
    dx: Math.round(event.clientX - intent.startX),
    dy: Math.round(event.clientY - intent.startY),
    distance: Number(Math.hypot(event.clientX - intent.startX, event.clientY - intent.startY).toFixed(2)),
    ...(intent.details || {}),
  });
}

function finishPan() {
  if (!pan) {
    return null;
  }
  const finishedPan = pan;
  pan = null;
  document.body.classList.remove("panning-canvas");
  window.getSelection()?.removeAllRanges();
  return finishedPan;
}

function clearPanIntent() {
  panIntent = null;
}

function isCanvasSpace(target) {
  return target === canvas || target === worldLayer;
}

function setDirty(reason = "dirty") {
  documentDirty = true;
  documentDirtyRevision += 1;
  saveState.textContent = "edited";
  if (typeof scheduleDocumentAutoSave === "function") {
    scheduleDocumentAutoSave(reason);
  }
}

function clonePlain(value) {
  return JSON.parse(JSON.stringify(value));
}

function historyStateSnapshot() {
  if (!doc) {
    return null;
  }
  return {
    doc: clonePlain(doc),
    selectedId,
    selectedIds: selectedNodeIds(),
    openParentId,
    childEditParentId,
    codePanelNodeId,
    viewport: {
      x: viewport.x,
      y: viewport.y,
      scale: viewport.scale,
    },
  };
}

function historyStateSignature(snapshot) {
  return JSON.stringify(snapshot);
}

function updateHistoryButtons() {
  if (undoButton) {
    undoButton.disabled = undoStack.length === 0;
  }
  if (redoButton) {
    redoButton.disabled = redoStack.length === 0;
  }
}

function clearDocumentHistory(reason = "clear-history") {
  undoStack = [];
  redoStack = [];
  historyGroupKey = null;
  updateHistoryButtons();
  logEvent("debug", reason, { undoCount: 0, redoCount: 0 });
}

function applyHistoryState(snapshot, reason = "history-restore") {
  if (!snapshot?.doc) {
    return false;
  }
  doc = normalizeDocumentWorkspace(clonePlain(snapshot.doc), `${reason}-workspace`);
  selectedId = nodeById(snapshot.selectedId) ? snapshot.selectedId : (firstActiveNode()?.id || null);
  selectedIds = new Set(uniqueActiveNodeIds(snapshot.selectedIds || (selectedId ? [selectedId] : [])));
  if (selectedId && !selectedIds.has(selectedId)) {
    selectedIds.add(selectedId);
  }
  selectionAnchorId = selectedId;
  openParentId = nodeById(snapshot.openParentId) ? snapshot.openParentId : null;
  childEditParentId = nodeById(snapshot.childEditParentId) ? snapshot.childEditParentId : null;
  codePanelNodeId = nodeById(snapshot.codePanelNodeId) ? snapshot.codePanelNodeId : null;
  const nextViewport = snapshot.viewport || {};
  stopViewportMotion();
  setViewportRaw({
    x: finiteViewportNumber(nextViewport.x, viewport.x),
    y: finiteViewportNumber(nextViewport.y, viewport.y),
    scale: clampViewScale(finiteViewportNumber(nextViewport.scale, viewport.scale)),
  });
  setDirty();
  render();
  updateHistoryButtons();
  logEvent("debug", reason, {
    nodeCount: doc.nodes.length,
    selectedId,
    openParentId,
    undoCount: undoStack.length,
    redoCount: redoStack.length,
  });
  return true;
}

function meaningSurfaceText(node) {
  return (node?.title || node?.body || "").trim();
}

function meaningName(node) {
  if (typeof powanExplorer !== "undefined" && powanExplorer?.meaningDisplayText) {
    return powanExplorer.meaningDisplayText(node);
  }
  const text = meaningSurfaceText(node);
  return text ? text.split("\n")[0].slice(0, 32) : "名前のないポワン";
}

function hasMeaningText(node) {
  return Boolean(meaningSurfaceText(node));
}

function powanCodexDisconnected(nodeOrId) {
  const node = typeof nodeOrId === "string" ? nodeById(nodeOrId) : nodeOrId;
  return Boolean(node?.codexState?.disconnected);
}

function powanCodexDisconnectedMessage(nodeOrId) {
  const node = typeof nodeOrId === "string" ? nodeById(nodeOrId) : nodeOrId;
  return String(node?.codexState?.disconnectedMessage || "Codexが切断されました。返事は戻りません。");
}

function worldPathNodes(node) {
  const path = [];
  let current = node;
  while (current) {
    path.unshift(current);
    current = current.parent ? nodeById(current.parent) : null;
  }
  return path;
}

function worldPathIds(node) {
  return worldPathNodes(node).map((item) => item.id);
}

function focusedAncestorIds() {
  const ids = new Set();
  const addPathThroughNode = (node) => {
    for (const item of worldPathNodes(node)) {
      ids.add(item.id);
    }
  };
  const addStrictAncestors = (node) => {
    const path = worldPathNodes(node);
    for (const item of path.slice(0, -1)) {
      ids.add(item.id);
    }
  };

  const worldParent = currentWorldParent();
  if (worldParent) {
    addPathThroughNode(worldParent);
  }

  const editParent = childEditParentId ? nodeById(childEditParentId) : null;
  if (editParent) {
    addPathThroughNode(editParent);
  }

  const selected = typeof selectedNodeIds === "function"
    ? selectedNodeIds()
    : (selectedId ? [selectedId] : []);
  for (const id of selected) {
    const node = nodeById(id);
    if (node) {
      addStrictAncestors(node);
    }
  }

  return ids;
}

function isFocusedAncestor(nodeId) {
  return Boolean(nodeId && focusedAncestorIds().has(nodeId));
}

function syncFocusedAncestorTextVisuals() {
  const ids = focusedAncestorIds();
  const toggle = (element) => element.classList.toggle("focus-ancestor-text", ids.has(element.dataset.id));
  if (worldLayer) {
    worldLayer.querySelectorAll(".node, .nested-meaning, .nested-preview-meaning").forEach(toggle);
  }
  if (treeList) {
    treeList.querySelectorAll(".tree-item").forEach(toggle);
  }
}

function waitForWorldTransition() {
  return new Promise((resolve) => window.setTimeout(resolve, WORLD_TRANSITION_MS));
}


