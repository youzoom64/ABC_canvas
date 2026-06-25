var NESTED_PREVIEW_MAX_DEPTH = 3;

function appendNestedMeaningPreview(container, parent, placement, depth = 1) {
  const children = meaningChildren(parent);
  if (!children.length || depth > NESTED_PREVIEW_MAX_DEPTH) {
    return;
  }
  const width = Number(placement?.width || container.offsetWidth || 0);
  const height = Number(placement?.height || container.offsetHeight || 0);
  if (width < 42 || height < 26) {
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
  const sideInset = Math.max(4, width * 0.13);
  const topInset = Math.max(8, height * (depth === 1 ? 0.48 : 0.42));
  const bottomInset = Math.max(4, height * 0.1);
  return {
    x: sideInset,
    y: topInset,
    width: Math.max(8, width - sideInset * 2),
    height: Math.max(8, height - topInset - bottomInset),
  };
}

function arrangeNestedPreviewChildren(parent, children, area, containerWidth, containerHeight, depth) {
  const columns = Math.ceil(Math.sqrt(children.length));
  const rows = Math.ceil(children.length / columns);
  const cellWidth = area.width / columns;
  const cellHeight = area.height / rows;
  return children.map((child, index) => {
    const column = index % columns;
    const row = Math.floor(index / columns);
    const size = nestedPreviewChildSize(cellWidth, cellHeight, depth);
    const savedPlacement = nestedPreviewPlacementFromLayout(parent, child, area, size);
    if (savedPlacement) {
      return savedPlacement;
    }
    return {
      node: child,
      x: area.x + column * cellWidth + (cellWidth - size.width) / 2,
      y: area.y + row * cellHeight + (cellHeight - size.height) / 2,
      width: size.width,
      height: size.height,
    };
  });
}

function nestedPreviewPlacementFromLayout(parent, child, area, size) {
  const nestedLayout = child.nestedLayoutByParent?.[parent.id];
  const savedX = Number(nestedLayout?.x);
  const savedY = Number(nestedLayout?.y);
  if (!Number.isFinite(savedX) || !Number.isFinite(savedY)) {
    return null;
  }
  const sourceArea = powanPlacement.parentNestedArea(parent);
  const savedWidth = Number(nestedLayout?.width || size.width);
  const savedHeight = Number(nestedLayout?.height || size.height);
  const sourceCenterX = savedX + savedWidth / 2;
  const sourceCenterY = savedY + savedHeight / 2;
  const anchor = {
    x: powanPlacement.clamp((sourceCenterX - sourceArea.x) / Math.max(1, sourceArea.width), 0, 1),
    y: powanPlacement.clamp((sourceCenterY - sourceArea.y) / Math.max(1, sourceArea.height), 0, 1),
  };
  const placement = powanPlacement.rectAtAnchor(area, size, anchor);
  return {
    node: child,
    ...placement,
  };
}

function nestedPreviewChildSize(cellWidth, cellHeight, depth) {
  const depthScale = Math.max(0.52, 1 - depth * 0.14);
  const width = Math.max(14, Math.min(54, cellWidth * 0.76 * depthScale));
  const height = Math.max(8, Math.min(24, width * 0.42, cellHeight * 0.78));
  return { width, height };
}

function renderNestedPreviewMeaning(node, placement, depth) {
  const element = createPowanSurface(node, placement, { mode: "preview", depth });
  element.addEventListener("pointerdown", (event) => {
    logNestedPointerDebug("nested-preview-pointerdown-capture", event, node, element, { depth });
  }, true);
  element.addEventListener("pointerdown", (event) => beginNestedPointer(event, node, element));
  element.addEventListener("pointermove", (event) => powanHitTest.syncNodeCursor(event, element));
  element.addEventListener("pointerleave", () => powanHitTest.clearNodeCursor(element));
  element.addEventListener("contextmenu", (event) => openPowanContextMenu(event, node));

  element.append(createPowanBody(node, { mode: "preview" }));
  return element;
}
