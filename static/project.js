const projectCreateForm = document.querySelector("#projectCreateForm");
const projectNameInput = document.querySelector("#projectNameInput");
const projectList = document.querySelector("#projectList");
const projectStatus = document.querySelector("#projectStatus");
const projectSettingsButton = document.querySelector("#projectSettingsButton");
const projectShutdownButton = document.querySelector("#projectShutdownButton");

if (projectShutdownButton) {
  projectShutdownButton.disabled = false;
}

async function writeProjectInfoLog(action, details = {}) {
  await fetch("/api/logs/client", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      entries: [
        {
          level: "info",
          action,
          source: "project-page",
          clientTime: new Date().toISOString(),
          ...details,
        },
      ],
    }),
  });
}

async function revealProjectRoot(name) {
  const response = await fetch("/api/projects/open", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "open failed" }));
    throw new Error(error.detail || "open failed");
  }
  return response.json();
}

async function openProject(name) {
  setProjectStatus("opening");
  try {
    await revealProjectRoot(name);
  } catch (error) {
    setProjectStatus("explorer open failed");
    console.error(error);
  }
  window.location.href = `/canvas?project=${encodeURIComponent(name)}`;
}

function setProjectStatus(text) {
  projectStatus.textContent = text;
}

async function shutdownProjectApplication() {
  projectShutdownButton.disabled = true;
  setProjectStatus("stopping");
  await writeProjectInfoLog("shutdown-button-click");
  const response = await fetch("/api/shutdown", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ reason: "project-button" }),
  });
  if (!response.ok) {
    projectShutdownButton.disabled = false;
    setProjectStatus("stop failed");
    await writeProjectInfoLog("shutdown-request-failed", { status: response.status });
    return;
  }
  await writeProjectInfoLog("shutdown-request-sent", await response.json());
  setProjectStatus("stopping");
}

function renderProjectList(projects) {
  projectList.innerHTML = "";
  if (!projects.length) {
    const empty = document.createElement("div");
    empty.className = "project-empty";
    empty.textContent = "プロジェクトはまだありません";
    projectList.appendChild(empty);
    return;
  }
  for (const project of projects) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "project-item";
    button.innerHTML = `
      <span class="project-item-name"></span>
      <span class="project-item-path"></span>
    `;
    button.querySelector(".project-item-name").textContent = project.name;
    button.querySelector(".project-item-path").textContent = project.path;
    button.addEventListener("click", () => {
      openProject(project.name).catch((error) => {
        setProjectStatus("open failed");
        console.error(error);
      });
    });
    projectList.appendChild(button);
  }
}

async function refreshProjects() {
  setProjectStatus("loading");
  const response = await fetch("/api/projects");
  const data = await response.json();
  renderProjectList(data.projects || []);
  setProjectStatus("ready");
}

async function createProject(name) {
  setProjectStatus("creating");
  const response = await fetch("/api/projects", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "create failed" }));
    setProjectStatus(error.detail || "create failed");
    return;
  }
  const project = await response.json();
  await openProject(project.name);
}

projectCreateForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const name = projectNameInput.value.trim();
  if (!name) {
    setProjectStatus("name required");
    projectNameInput.focus();
    return;
  }
  createProject(name).catch((error) => {
    setProjectStatus("create failed");
    console.error(error);
  });
});

if (projectShutdownButton) {
  projectShutdownButton.addEventListener("click", () => shutdownProjectApplication().catch((error) => {
    projectShutdownButton.disabled = false;
    setProjectStatus("stop failed");
    console.error(error);
  }));
}

if (projectSettingsButton) {
  projectSettingsButton.addEventListener("click", () => {
    window.location.href = "/settings";
  });
}

refreshProjects().catch((error) => {
  setProjectStatus("load failed");
  console.error(error);
});
