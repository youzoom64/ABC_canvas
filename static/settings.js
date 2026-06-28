const settingsBackButton = document.querySelector("#settingsBackButton");
const settingsProjectButton = document.querySelector("#settingsProjectButton");
const soundFolderInput = document.querySelector("#soundFolderInput");
const defaultSoundFolder = document.querySelector("#defaultSoundFolder");
const browseSoundFolderButton = document.querySelector("#browseSoundFolderButton");
const saveSoundFolderButton = document.querySelector("#saveSoundFolderButton");
const refreshSoundButton = document.querySelector("#refreshSoundButton");
const settingsSoundSelect = document.querySelector("#settingsSoundSelect");
const saveConversationSoundButton = document.querySelector("#saveConversationSoundButton");
const soundVolumeInput = document.querySelector("#soundVolumeInput");
const soundVolumeValue = document.querySelector("#soundVolumeValue");
const saveSoundVolumeButton = document.querySelector("#saveSoundVolumeButton");
const settingsInputSoundSelect = document.querySelector("#settingsInputSoundSelect");
const saveInputSoundButton = document.querySelector("#saveInputSoundButton");
const inputSoundVolumeInput = document.querySelector("#inputSoundVolumeInput");
const inputSoundVolumeValue = document.querySelector("#inputSoundVolumeValue");
const saveInputSoundVolumeButton = document.querySelector("#saveInputSoundVolumeButton");
const codexSandboxSelect = document.querySelector("#codexSandboxSelect");
const saveCodexSandboxButton = document.querySelector("#saveCodexSandboxButton");
const codexModelInput = document.querySelector("#codexModelInput");
const codexReasoningEffortSelect = document.querySelector("#codexReasoningEffortSelect");
const saveCodexModelButton = document.querySelector("#saveCodexModelButton");
const arrangeResizeParentsInput = document.querySelector("#arrangeResizeParentsInput");
const arrangeRecursiveInput = document.querySelector("#arrangeRecursiveInput");
const arrangeChildSpacingInput = document.querySelector("#arrangeChildSpacingInput");
const arrangeChildSpacingValue = document.querySelector("#arrangeChildSpacingValue");
const arrangeChildSizeInput = document.querySelector("#arrangeChildSizeInput");
const arrangeChildSizeValue = document.querySelector("#arrangeChildSizeValue");
const arrangeNestedChildSizeInput = document.querySelector("#arrangeNestedChildSizeInput");
const arrangeNestedChildSizeValue = document.querySelector("#arrangeNestedChildSizeValue");
const arrangeWorldParentSpacingInput = document.querySelector("#arrangeWorldParentSpacingInput");
const arrangeWorldParentSpacingValue = document.querySelector("#arrangeWorldParentSpacingValue");
const arrangeWorldParentSizeInput = document.querySelector("#arrangeWorldParentSizeInput");
const arrangeWorldParentSizeValue = document.querySelector("#arrangeWorldParentSizeValue");
const saveArrangeButton = document.querySelector("#saveArrangeButton");
const restartVisibleConsoleInput = document.querySelector("#restartVisibleConsoleInput");
const saveRestartVisibleConsoleButton = document.querySelector("#saveRestartVisibleConsoleButton");
const consoleLogLevelInputs = [...document.querySelectorAll("#consoleLogLevelInputs input[type='checkbox']")];
const saveConsoleLogLevelsButton = document.querySelector("#saveConsoleLogLevelsButton");
const settingsStatus = document.querySelector("#settingsStatus");

const settingsParams = new URLSearchParams(window.location.search);
const settingsProject = settingsParams.get("project") || "";
let currentSettingsData = {};
const autoSaveTimers = new Map();

function setSettingsStatus(text) {
  settingsStatus.textContent = text;
}

function reportSettingsError(error) {
  setSettingsStatus(error.message);
  console.error(error);
}

function autoSave(key, saveFn, delay = 0) {
  window.clearTimeout(autoSaveTimers.get(key));
  autoSaveTimers.set(
    key,
    window.setTimeout(() => {
      autoSaveTimers.delete(key);
      saveFn().catch(reportSettingsError);
    }, delay),
  );
}

function canvasBackUrl() {
  if (!settingsProject) {
    return "/";
  }
  return `/canvas?project=${encodeURIComponent(settingsProject)}`;
}

function renderSoundOptions(select, sounds, selected) {
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
  select.value = selected || "";
}

function normalizeVolume(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) {
    return 0.55;
  }
  return Math.min(1, Math.max(0, number));
}

function normalizeRangeScale(value, fallback, min, max) {
  const number = Number(value);
  if (!Number.isFinite(number)) {
    return fallback;
  }
  return Math.min(max, Math.max(min, number));
}

function renderArrange(data) {
  arrangeResizeParentsInput.checked = data.arrangeResizeParents !== false;
  arrangeRecursiveInput.checked = data.arrangeRecursive !== false;
  setRangeValue(arrangeChildSpacingInput, arrangeChildSpacingValue, data.arrangeChildSpacing ?? data.arrangeSpacing, 1, 0.3, 3.0);
  setRangeValue(arrangeChildSizeInput, arrangeChildSizeValue, data.arrangeChildSize ?? data.arrangeSize, 1, 0.3, 2.5);
  setRangeValue(arrangeNestedChildSizeInput, arrangeNestedChildSizeValue, data.arrangeNestedChildSize ?? data.arrangeSize, 1, 0.3, 2.5);
  setRangeValue(arrangeWorldParentSpacingInput, arrangeWorldParentSpacingValue, data.arrangeWorldParentSpacing ?? data.arrangeSpacing, 1, 0.3, 3.0);
  setRangeValue(arrangeWorldParentSizeInput, arrangeWorldParentSizeValue, data.arrangeWorldParentSize ?? data.arrangeSize, 1, 0.3, 2.5);
}

function setRangeValue(input, output, value, fallback, min, max) {
  if (!input || !output) {
    return;
  }
  const next = normalizeRangeScale(value, fallback, min, max);
  input.value = String(next);
  output.textContent = next.toFixed(2);
}

function selectedConsoleLogLevels() {
  return consoleLogLevelInputs.filter((input) => input.checked).map((input) => input.value);
}

function renderConsoleLogLevels(data) {
  const levels = new Set(Array.isArray(data.consoleLogLevels) ? data.consoleLogLevels : ["info", "warn", "error"]);
  for (const input of consoleLogLevelInputs) {
    input.checked = levels.has(input.value);
  }
}

function renderVolume(value) {
  const volume = normalizeVolume(value);
  soundVolumeInput.value = String(volume);
  soundVolumeValue.textContent = `${Math.round(volume * 100)}%`;
}

function renderInputVolume(value) {
  const volume = normalizeVolume(value);
  inputSoundVolumeInput.value = String(volume);
  inputSoundVolumeValue.textContent = `${Math.round(volume * 100)}%`;
}

function normalizeCodexReasoningEffort(value) {
  const effort = String(value || "").trim().toLowerCase();
  if (effort === "very_high" || effort === "very-high") {
    return "xhigh";
  }
  if (["none", "minimal", "low", "medium", "high", "xhigh"].includes(effort)) {
    return effort;
  }
  return "low";
}

function renderSettings(data) {
  currentSettingsData = { ...(data || {}) };
  soundFolderInput.value = data.soundRoot || "";
  defaultSoundFolder.textContent = data.defaultSoundRoot ? `default: ${data.defaultSoundRoot}` : "";
  renderSoundOptions(settingsSoundSelect, data.sounds || [], data.conversationSound || "");
  renderSoundOptions(settingsInputSoundSelect, data.sounds || [], data.inputSound || "");
  renderVolume(data.conversationSoundVolume);
  renderInputVolume(data.inputSoundVolume);
  codexSandboxSelect.value = data.codexSandbox || "danger-full-access";
  codexModelInput.value = data.codexModel || "gpt-5.5";
  codexReasoningEffortSelect.value = normalizeCodexReasoningEffort(data.codexReasoningEffort);
  renderArrange(data);
  restartVisibleConsoleInput.checked = Boolean(data.restartVisibleConsole);
  renderConsoleLogLevels(data);
}

async function loadSettings() {
  setSettingsStatus("loading");
  const response = await fetch("/api/settings");
  if (!response.ok) {
    throw new Error(`settings load failed: ${response.status}`);
  }
  const data = await response.json();
  renderSettings(data);
  setSettingsStatus("ready");
}

async function saveSoundFolder() {
  const soundRoot = soundFolderInput.value.trim();
  if (!soundRoot) {
    soundFolderInput.focus();
    setSettingsStatus("folder required");
    return;
  }
  saveSoundFolderButton.disabled = true;
  setSettingsStatus("saving folder");
  try {
    const response = await fetch("/api/settings/sound-folder", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ soundRoot }),
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "save failed" }));
      throw new Error(error.detail || "save failed");
    }
    renderSettings(await response.json());
    setSettingsStatus("folder saved");
  } finally {
    saveSoundFolderButton.disabled = false;
  }
}

async function browseSoundFolder() {
  browseSoundFolderButton.disabled = true;
  setSettingsStatus("selecting folder");
  try {
    const response = await fetch("/api/settings/sound-folder/pick", {
      method: "POST",
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "browse failed" }));
      throw new Error(error.detail || "browse failed");
    }
    const data = await response.json();
    renderSettings(data);
    setSettingsStatus(data.cancelled ? "folder unchanged" : "folder selected");
  } finally {
    browseSoundFolderButton.disabled = false;
  }
}

async function saveConversationSound() {
  saveConversationSoundButton.disabled = true;
  setSettingsStatus("saving sound");
  try {
    const response = await fetch("/api/settings/conversation-sound", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ conversationSound: settingsSoundSelect.value }),
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "save failed" }));
      throw new Error(error.detail || "save failed");
    }
    renderSettings(await response.json());
    setSettingsStatus("sound saved");
  } finally {
    saveConversationSoundButton.disabled = false;
  }
}

async function saveSoundVolume() {
  saveSoundVolumeButton.disabled = true;
  setSettingsStatus("saving volume");
  try {
    const response = await fetch("/api/settings/conversation-sound-volume", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ conversationSoundVolume: normalizeVolume(soundVolumeInput.value) }),
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "save failed" }));
      throw new Error(error.detail || "save failed");
    }
    renderSettings(await response.json());
    setSettingsStatus("volume saved");
  } finally {
    saveSoundVolumeButton.disabled = false;
  }
}

async function saveInputSound() {
  saveInputSoundButton.disabled = true;
  setSettingsStatus("saving input sound");
  try {
    const response = await fetch("/api/settings/input-sound", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ inputSound: settingsInputSoundSelect.value }),
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "save failed" }));
      throw new Error(error.detail || "save failed");
    }
    renderSettings(await response.json());
    setSettingsStatus("input sound saved");
  } finally {
    saveInputSoundButton.disabled = false;
  }
}

async function saveInputSoundVolume() {
  saveInputSoundVolumeButton.disabled = true;
  setSettingsStatus("saving input volume");
  try {
    const response = await fetch("/api/settings/input-sound-volume", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ inputSoundVolume: normalizeVolume(inputSoundVolumeInput.value) }),
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "save failed" }));
      throw new Error(error.detail || "save failed");
    }
    renderSettings(await response.json());
    setSettingsStatus("input volume saved");
  } finally {
    saveInputSoundVolumeButton.disabled = false;
  }
}

async function saveCodexSandbox() {
  saveCodexSandboxButton.disabled = true;
  setSettingsStatus("saving codex access");
  try {
    const response = await fetch("/api/settings/codex-sandbox", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ codexSandbox: codexSandboxSelect.value }),
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "save failed" }));
      throw new Error(error.detail || "save failed");
    }
    renderSettings(await response.json());
    setSettingsStatus("codex access saved");
  } finally {
    saveCodexSandboxButton.disabled = false;
  }
}

async function saveCodexModelSettings() {
  saveCodexModelButton.disabled = true;
  setSettingsStatus("saving codex model");
  try {
    const response = await fetch("/api/settings/codex-model", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        codexModel: codexModelInput.value.trim(),
        codexReasoningEffort: codexReasoningEffortSelect.value,
      }),
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "save failed" }));
      throw new Error(error.detail || "save failed");
    }
    renderSettings(await response.json());
    setSettingsStatus("codex model saved");
  } finally {
    saveCodexModelButton.disabled = false;
  }
}

async function saveArrange() {
  saveArrangeButton.disabled = true;
  setSettingsStatus("saving arrange");
  try {
    const response = await fetch("/api/settings/arrange", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        arrangeSpacing: normalizeRangeScale(arrangeChildSpacingInput?.value ?? currentSettingsData.arrangeChildSpacing ?? currentSettingsData.arrangeSpacing, 1, 0.3, 3.0),
        arrangeSize: normalizeRangeScale(arrangeChildSizeInput?.value ?? currentSettingsData.arrangeChildSize ?? currentSettingsData.arrangeSize, 1, 0.3, 2.5),
        arrangeResizeParents: arrangeResizeParentsInput.checked,
        arrangeRecursive: arrangeRecursiveInput.checked,
        arrangeChildSpacing: normalizeRangeScale(arrangeChildSpacingInput?.value ?? currentSettingsData.arrangeChildSpacing ?? currentSettingsData.arrangeSpacing, 1, 0.3, 3.0),
        arrangeChildSize: normalizeRangeScale(arrangeChildSizeInput?.value ?? currentSettingsData.arrangeChildSize ?? currentSettingsData.arrangeSize, 1, 0.3, 2.5),
        arrangeNestedChildSize: normalizeRangeScale(arrangeNestedChildSizeInput?.value ?? currentSettingsData.arrangeNestedChildSize ?? currentSettingsData.arrangeSize, 1, 0.3, 2.5),
        arrangeWorldParentSpacing: normalizeRangeScale(arrangeWorldParentSpacingInput?.value ?? currentSettingsData.arrangeWorldParentSpacing ?? currentSettingsData.arrangeSpacing, 1, 0.3, 3.0),
        arrangeWorldParentSize: normalizeRangeScale(arrangeWorldParentSizeInput?.value ?? currentSettingsData.arrangeWorldParentSize ?? currentSettingsData.arrangeSize, 1, 0.3, 2.5),
      }),
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "save failed" }));
      throw new Error(error.detail || "save failed");
    }
    renderSettings(await response.json());
    setSettingsStatus("arrange saved");
  } finally {
    saveArrangeButton.disabled = false;
  }
}

async function saveConsoleLogLevels() {
  saveConsoleLogLevelsButton.disabled = true;
  setSettingsStatus("saving CMD logs");
  try {
    const response = await fetch("/api/settings/console-log-levels", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ consoleLogLevels: selectedConsoleLogLevels() }),
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "save failed" }));
      throw new Error(error.detail || "save failed");
    }
    renderSettings(await response.json());
    setSettingsStatus("CMD logs saved");
  } finally {
    saveConsoleLogLevelsButton.disabled = false;
  }
}

async function saveRestartVisibleConsole() {
  saveRestartVisibleConsoleButton.disabled = true;
  setSettingsStatus("saving restart");
  try {
    const response = await fetch("/api/settings/restart-visible-console", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ restartVisibleConsole: restartVisibleConsoleInput.checked }),
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "save failed" }));
      throw new Error(error.detail || "save failed");
    }
    renderSettings(await response.json());
    setSettingsStatus("restart saved");
  } finally {
    saveRestartVisibleConsoleButton.disabled = false;
  }
}

settingsBackButton.textContent = settingsProject ? "Canvas" : "Projects";
settingsBackButton.addEventListener("click", () => {
  window.location.href = canvasBackUrl();
});
settingsProjectButton.addEventListener("click", () => {
  window.location.href = "/";
});
saveSoundFolderButton.addEventListener("click", () => {
  saveSoundFolder().catch((error) => {
    setSettingsStatus(error.message);
    console.error(error);
  });
});
soundFolderInput.addEventListener("change", () => {
  autoSave("soundFolder", saveSoundFolder);
});
soundFolderInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    autoSave("soundFolder", saveSoundFolder);
  }
});
browseSoundFolderButton.addEventListener("click", () => {
  browseSoundFolder().catch((error) => {
    setSettingsStatus(error.message);
    console.error(error);
  });
});
refreshSoundButton.addEventListener("click", () => {
  loadSettings().catch((error) => {
    setSettingsStatus(error.message);
    console.error(error);
  });
});
saveConversationSoundButton.addEventListener("click", () => {
  saveConversationSound().catch((error) => {
    setSettingsStatus(error.message);
    console.error(error);
  });
});
settingsSoundSelect.addEventListener("change", () => {
  autoSave("conversationSound", saveConversationSound);
});
soundVolumeInput.addEventListener("input", () => {
  renderVolume(soundVolumeInput.value);
  autoSave("conversationSoundVolume", saveSoundVolume, 350);
});
soundVolumeInput.addEventListener("change", () => {
  autoSave("conversationSoundVolume", saveSoundVolume);
});
saveSoundVolumeButton.addEventListener("click", () => {
  saveSoundVolume().catch((error) => {
    setSettingsStatus(error.message);
    console.error(error);
  });
});
saveInputSoundButton.addEventListener("click", () => {
  saveInputSound().catch((error) => {
    setSettingsStatus(error.message);
    console.error(error);
  });
});
settingsInputSoundSelect.addEventListener("change", () => {
  autoSave("inputSound", saveInputSound);
});
inputSoundVolumeInput.addEventListener("input", () => {
  renderInputVolume(inputSoundVolumeInput.value);
  autoSave("inputSoundVolume", saveInputSoundVolume, 350);
});
inputSoundVolumeInput.addEventListener("change", () => {
  autoSave("inputSoundVolume", saveInputSoundVolume);
});
saveInputSoundVolumeButton.addEventListener("click", () => {
  saveInputSoundVolume().catch((error) => {
    setSettingsStatus(error.message);
    console.error(error);
  });
});
saveCodexSandboxButton.addEventListener("click", () => {
  saveCodexSandbox().catch((error) => {
    setSettingsStatus(error.message);
    console.error(error);
  });
});
codexSandboxSelect.addEventListener("change", () => {
  autoSave("codexSandbox", saveCodexSandbox);
});
saveCodexModelButton.addEventListener("click", () => {
  saveCodexModelSettings().catch((error) => {
    setSettingsStatus(error.message);
    console.error(error);
  });
});
codexModelInput.addEventListener("change", () => {
  autoSave("codexModel", saveCodexModelSettings);
});
codexModelInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    autoSave("codexModel", saveCodexModelSettings);
  }
});
codexReasoningEffortSelect.addEventListener("change", () => {
  autoSave("codexModel", saveCodexModelSettings);
});
if (arrangeChildSpacingInput) {
  arrangeChildSpacingInput.addEventListener("input", () => {
    arrangeChildSpacingValue.textContent = normalizeRangeScale(arrangeChildSpacingInput.value, 1, 0.3, 3.0).toFixed(2);
    autoSave("arrange", saveArrange, 350);
  });
  arrangeChildSpacingInput.addEventListener("change", () => {
    autoSave("arrange", saveArrange);
  });
}
if (arrangeChildSizeInput) {
  arrangeChildSizeInput.addEventListener("input", () => {
    arrangeChildSizeValue.textContent = normalizeRangeScale(arrangeChildSizeInput.value, 1, 0.3, 2.5).toFixed(2);
    autoSave("arrange", saveArrange, 350);
  });
  arrangeChildSizeInput.addEventListener("change", () => {
    autoSave("arrange", saveArrange);
  });
}
if (arrangeNestedChildSizeInput) {
  arrangeNestedChildSizeInput.addEventListener("input", () => {
    arrangeNestedChildSizeValue.textContent = normalizeRangeScale(arrangeNestedChildSizeInput.value, 1, 0.3, 2.5).toFixed(2);
    autoSave("arrange", saveArrange, 350);
  });
  arrangeNestedChildSizeInput.addEventListener("change", () => {
    autoSave("arrange", saveArrange);
  });
}
if (arrangeWorldParentSpacingInput) {
  arrangeWorldParentSpacingInput.addEventListener("input", () => {
    arrangeWorldParentSpacingValue.textContent = normalizeRangeScale(arrangeWorldParentSpacingInput.value, 1, 0.3, 3.0).toFixed(2);
    autoSave("arrange", saveArrange, 350);
  });
  arrangeWorldParentSpacingInput.addEventListener("change", () => {
    autoSave("arrange", saveArrange);
  });
}
if (arrangeWorldParentSizeInput) {
  arrangeWorldParentSizeInput.addEventListener("input", () => {
    arrangeWorldParentSizeValue.textContent = normalizeRangeScale(arrangeWorldParentSizeInput.value, 1, 0.3, 2.5).toFixed(2);
    autoSave("arrange", saveArrange, 350);
  });
  arrangeWorldParentSizeInput.addEventListener("change", () => {
    autoSave("arrange", saveArrange);
  });
}
arrangeResizeParentsInput.addEventListener("change", () => {
  autoSave("arrange", saveArrange);
});
arrangeRecursiveInput.addEventListener("change", () => {
  autoSave("arrange", saveArrange);
});
saveArrangeButton.addEventListener("click", () => {
  saveArrange().catch((error) => {
    setSettingsStatus(error.message);
    console.error(error);
  });
});
saveConsoleLogLevelsButton.addEventListener("click", () => {
  saveConsoleLogLevels().catch((error) => {
    setSettingsStatus(error.message);
    console.error(error);
  });
});
for (const input of consoleLogLevelInputs) {
  input.addEventListener("change", () => {
    autoSave("consoleLogLevels", saveConsoleLogLevels);
  });
}
saveRestartVisibleConsoleButton.addEventListener("click", () => {
  saveRestartVisibleConsole().catch((error) => {
    setSettingsStatus(error.message);
    console.error(error);
  });
});
restartVisibleConsoleInput.addEventListener("change", () => {
  autoSave("restartVisibleConsole", saveRestartVisibleConsole);
});

loadSettings().catch((error) => {
  setSettingsStatus(error.message);
  console.error(error);
});
