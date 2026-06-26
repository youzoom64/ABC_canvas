const ABC_CANVAS_SCRIPT_VERSION = "stable-nested-wheel-127";
const ABC_CANVAS_SCRIPTS = [
  "/static/js/workspace.js",
  "/static/js/state.js",
  "/static/js/placement.js",
  "/static/js/focus.js",
  "/static/js/selection.js",
  "/static/js/attachments.js",
  "/static/js/hit_test.js",
  "/static/js/soft_body.js",
  "/static/js/soft_body_view.js",
  "/static/js/drag_deform.js",
  "/static/js/nested_drag.js",
  "/static/js/explorer.js",
  "/static/js/powan_io.js",
  "/static/js/render.js",
  "/static/js/world_transition.js",
  "/static/js/state_transition.js",
  "/static/js/nested_preview.js",
  "/static/js/world.js",
  "/static/js/auto_reload.js",
  "/static/js/interactions.js",
  "/static/js/shutdown.js",
];

function loadAbcCanvasScript(src) {
  return new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = `${src}?v=${ABC_CANVAS_SCRIPT_VERSION}`;
    script.async = false;
    script.onload = resolve;
    script.onerror = () => reject(new Error(`failed to load ${src}`));
    document.head.appendChild(script);
  });
}

async function wireAbcCanvas() {
  for (const src of ABC_CANVAS_SCRIPTS) {
    await loadAbcCanvasScript(src);
  }
  bootstrapAbcCanvas();
}

wireAbcCanvas().catch((error) => {
  console.error(error);
});
