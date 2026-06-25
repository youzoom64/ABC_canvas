async function shutdownApplication() {
  if (shutdownButton) {
    shutdownButton.disabled = true;
  }
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
    if (shutdownButton) {
      shutdownButton.disabled = false;
    }
    return;
  }
  logEvent("info", "shutdown-request-sent", await response.json());
  saveState.textContent = "stopping";
  await flushLogQueue();
}

if (shutdownButton) {
  shutdownButton.disabled = false;
  shutdownButton.addEventListener("click", () => shutdownApplication().catch((error) => {
    saveState.textContent = "stop failed";
    logEvent("error", "shutdown-error", { message: error.message });
    console.error(error);
    shutdownButton.disabled = false;
  }));
}
