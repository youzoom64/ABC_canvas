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
const arrangeSpacingInput = document.querySelector("#arrangeSpacingInput");
const arrangeSpacingValue = document.querySelector("#arrangeSpacingValue");
const arrangeSizeInput = document.querySelector("#arrangeSizeInput");
const arrangeSizeValue = document.querySelector("#arrangeSizeValue");
const saveArrangeButton = document.querySelector("#saveArrangeButton");
const settingsStatus = document.querySelector("#settingsStatus");

const settingsParams = new URLSearchParams(window.location.search);
const settingsProject = settingsParams.get("project") || "";

function setSettingsStatus(text) {
  settingsStatus.textContent = text;
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
  const spacing = normalizeRangeScale(data.arrangeSpacing, 1, 0.7, 1.4);
  const size = normalizeRangeScale(data.arrangeSize, 1, 0.7, 1.2);
  arrangeSpacingInput.value = String(spacing);
  arrangeSpacingValue.textContent = spacing.toFixed(2);
  arrangeSizeInput.value = String(size);
  arrangeSizeValue.textContent = size.toFixed(2);
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

function renderSettings(data) {
  soundFolderInput.value = data.soundRoot || "";
  defaultSoundFolder.textContent = data.defaultSoundRoot ? `default: ${data.defaultSoundRoot}` : "";
  renderSoundOptions(settingsSoundSelect, data.sounds || [], data.conversationSound || "");
  renderSoundOptions(settingsInputSoundSelect, data.sounds || [], data.inputSound || "");
  renderVolume(data.conversationSoundVolume);
  renderInputVolume(data.inputSoundVolume);
  codexSandboxSelect.value = data.codexSandbox || "danger-full-access";
  renderArrange(data);
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

async function saveArrange() {
  saveArrangeButton.disabled = true;
  setSettingsStatus("saving arrange");
  try {
    const response = await fetch("/api/settings/arrange", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        arrangeSpacing: normalizeRangeScale(arrangeSpacingInput.value, 1, 0.7, 1.4),
        arrangeSize: normalizeRangeScale(arrangeSizeInput.value, 1, 0.7, 1.2),
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
soundVolumeInput.addEventListener("input", () => {
  renderVolume(soundVolumeInput.value);
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
inputSoundVolumeInput.addEventListener("input", () => {
  renderInputVolume(inputSoundVolumeInput.value);
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
arrangeSpacingInput.addEventListener("input", () => {
  arrangeSpacingValue.textContent = normalizeRangeScale(arrangeSpacingInput.value, 1, 0.7, 1.4).toFixed(2);
});
arrangeSizeInput.addEventListener("input", () => {
  arrangeSizeValue.textContent = normalizeRangeScale(arrangeSizeInput.value, 1, 0.7, 1.2).toFixed(2);
});
saveArrangeButton.addEventListener("click", () => {
  saveArrange().catch((error) => {
    setSettingsStatus(error.message);
    console.error(error);
  });
});

loadSettings().catch((error) => {
  setSettingsStatus(error.message);
  console.error(error);
});
