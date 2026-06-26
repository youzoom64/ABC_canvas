var NESTED_PREVIEW_MAX_DEPTH = 1;

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
  const savedWidth = Math.max(8, Number(nestedLayout?.width || size.width));
  const savedHeight = Math.max(6, Number(nestedLayout?.height || size.height));
  const sourceCenterX = savedX + savedWidth / 2;
  const sourceCenterY = savedY + savedHeight / 2;
  const anchor = {
    x: (sourceCenterX - sourceArea.x) / Math.max(1, sourceArea.width),
    y: (sourceCenterY - sourceArea.y) / Math.max(1, sourceArea.height),
  };
  const defaultStoredSize = powanPlacement.nestedChildSize(Math.max(1, meaningChildren(parent).length), 1);
  const savedScale = powanPlacement.clamp(
    ((savedWidth / Math.max(1, defaultStoredSize.width)) + (savedHeight / Math.max(1, defaultStoredSize.height))) / 2,
    0.3,
    2.5,
  );
  const displaySize = {
    width: Math.min(Math.max(8, area.width), size.width * savedScale),
    height: Math.min(Math.max(6, area.height), size.height * savedScale),
  };
  const placement = {
    x: Math.round(area.x + area.width * anchor.x - displaySize.width / 2),
    y: Math.round(area.y + area.height * anchor.y - displaySize.height / 2),
    width: Math.round(displaySize.width),
    height: Math.round(displaySize.height),
  };
  return {
    node: child,
    ...placement,
  };
}

function nestedPreviewChildSize(cellWidth, cellHeight, depth) {
  const depthScale = Math.max(0.52, 1 - depth * 0.14);
  const width = Math.max(8, Math.min(54, cellWidth * 0.76 * depthScale));
  const height = Math.max(5, Math.min(24, width * 0.42, cellHeight * 0.78));
  return { width, height };
}

function renderNestedPreviewMeaning(node, placement, depth) {
  const element = createPowanSurfaceWithoutSoftBody(node, placement, { mode: "preview", depth });
  element.classList.add("nested-preview-simple");
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
