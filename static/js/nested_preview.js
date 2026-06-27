var NESTED_PREVIEW_MAX_DEPTH = 2;

function appendNestedMeaningPreview(container, parent, placement, depth = 1) {
  const children = meaningChildren(parent);
  if (!children.length || depth > NESTED_PREVIEW_MAX_DEPTH) {
    return;
  }
  const width = Number(placement?.width || container.offsetWidth || 0);
  const height = Number(placement?.height || container.offsetHeight || 0);
  const minWidth = depth <= 1 ? 42 : 8;
  const minHeight = depth <= 1 ? 26 : 5;
  if (width < minWidth || height < minHeight) {
    return;
  }
  const layer = document.createElement("div");
  layer.className = "nested-preview-layer";
  container.classList.add("has-nested-preview");
  container.append(layer);

  const area = nestedPreviewArea(width, height, depth);
  for (const childPlacement of arrangeNestedPreviewChildren(parent, children, area, width, height, depth)) {
    const childElement = renderNestedPreviewMeaning(childPlacement.node, childPlacement, depth);
    layer.append(childElement);
    appendNestedMeaningPreview(childElement, childPlacement.node, childPlacement, depth + 1);
  }
}

function nestedPreviewArea(width, height, depth) {
  const sideInset = Math.max(4, width * 0.12);
  const verticalInset = Math.max(4, height * (depth === 1 ? 0.18 : 0.16));
  return {
    x: sideInset,
    y: verticalInset,
    width: Math.max(8, width - sideInset * 2),
    height: Math.max(8, height - verticalInset * 2),
  };
}

function arrangeNestedPreviewChildren(parent, children, area, containerWidth, containerHeight, depth) {
  return children.map((child) => {
    const rect = nestedPreviewPlacementFromWorld(parent, child, area);
    return {
      node: child,
      ...rect,
    };
  });
}

function nestedPreviewPlacementFromWorld(parent, child, area) {
  const rect = powanPlacement.nestedViewRect(parent, child, {
    width: area.width,
    height: area.height,
  });
  return {
    x: Math.round(area.x + rect.x),
    y: Math.round(area.y + rect.y),
    width: Math.max(8, Math.round(rect.width)),
    height: Math.max(5, Math.round(rect.height)),
  };
}

function nestedPreviewChildSize(cellWidth, cellHeight, depth) {
  const depthScale = Math.max(0.52, 1 - depth * 0.14);
  const width = Math.max(8, Math.min(54, cellWidth * 0.76 * depthScale));
  const height = Math.max(5, Math.min(24, width * 0.42, cellHeight * 0.78));
  return { width, height };
}

function renderNestedPreviewMeaning(node, placement, depth) {
  const element = createPowanSurface(node, placement, { mode: "preview", depth });
  element.dataset.previewDepth = String(depth);
  element.addEventListener("pointerdown", (event) => {
    logNestedPointerDebug("nested-preview-pointerdown-capture", event, node, element, { depth });
  }, true);
  element.addEventListener("pointerdown", (event) => beginNestedPointer(event, node, element));
  element.addEventListener("pointermove", (event) => powanHitTest.syncNodeCursor(event, element));
  element.addEventListener("pointerleave", () => powanHitTest.clearNodeCursor(element));
  element.addEventListener("contextmenu", (event) => openPowanContextMenu(event, node));
  element.addEventListener("dblclick", (event) => {
    event.stopPropagation();
    powanExplorer.enterWorld(node.id, element);
  });

  const body = document.createElement("div");
  body.className = "node-body nested-preview-label";
  body.textContent = meaningSurfaceText(node) || EMPTY_MEANING_PLACEHOLDER;
  body.addEventListener("pointerdown", (event) => {
    resetPowanFaceClock(node.id, "nested-preview-body-pointerdown");
    event.preventDefault();
    event.stopPropagation();
  });
  body.addEventListener("dblclick", (event) => {
    event.preventDefault();
    event.stopPropagation();
  });
  element.append(body);
  return element;
}
