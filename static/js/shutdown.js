function setPowerButtonsDisabled(disabled) {
  if (shutdownButton) {
    shutdownButton.disabled = disabled;
  }
  if (restartButton) {
    restartButton.disabled = disabled;
  }
}

async function shutdownApplication() {
  setPowerButtonsDisabled(true);
  saveState.textContent = "stopping";
  logEvent("info", "shutdown-button-click", { projectName, documentName });
  await flushLogQueue();
  const response = await fetch("/api/shutdown", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ reason: "canvas-button" }),
  });
  if (!response.ok) {
    logEvent("warn", "shutdown-request-failed", { status: response.status });
    saveState.textContent = "stop failed";
    setPowerButtonsDisabled(false);
    return;
  }
  logEvent("info", "shutdown-request-sent", await response.json());
  saveState.textContent = "stopping";
  await flushLogQueue();
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function reloadWhenRestarted() {
  logEvent("info", "restart-reload-wait-start", { projectName, documentName });
  await flushLogQueue();
  await sleep(900);
  for (let attempt = 0; attempt < 60; attempt += 1) {
    try {
      const response = await fetch(`/canvas?restart=${Date.now()}`, { cache: "no-store" });
      if (response.ok) {
        logEvent("info", "restart-reload-ready", { attempt: attempt + 1 });
        await flushLogQueue();
        window.location.reload();
        return;
      }
    } catch (error) {
      // The server is expected to disappear briefly while restarting.
    }
    await sleep(500);
  }
  saveState.textContent = "restart pending";
  logEvent("warn", "restart-reload-timeout", { attempts: 60 });
  await flushLogQueue();
}

async function restartApplication() {
  setPowerButtonsDisabled(true);
  saveState.textContent = "restarting";
  logEvent("info", "restart-button-click", { projectName, documentName });
  await flushLogQueue();
  const response = await fetch("/api/restart", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ reason: "canvas-button" }),
  });
  if (!response.ok) {
    logEvent("warn", "restart-request-failed", { status: response.status });
    saveState.textContent = "restart failed";
    setPowerButtonsDisabled(false);
    return;
  }
  logEvent("info", "restart-request-sent", await response.json());
  saveState.textContent = "restarting";
  await flushLogQueue();
  reloadWhenRestarted();
}

if (shutdownButton) {
  shutdownButton.disabled = false;
  shutdownButton.addEventListener("click", () => shutdownApplication().catch((error) => {
    saveState.textContent = "stop failed";
    logEvent("error", "shutdown-error", { message: error.message });
    console.error(error);
    setPowerButtonsDisabled(false);
  }));
}

if (restartButton) {
  restartButton.disabled = false;
  restartButton.addEventListener("click", () => restartApplication().catch((error) => {
    saveState.textContent = "restart failed";
    logEvent("error", "restart-error", { message: error.message });
    console.error(error);
    setPowerButtonsDisabled(false);
  }));
}
