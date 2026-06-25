var powanPlacement = {
  nestedLayerInset: 14,
  nestedDisplayInset: 28,

  number(value, fallback = 0) {
    const next = Number(value);
    return Number.isFinite(next) ? next : fallback;
  },

  clamp(value, min, max) {
    if (max < min) {
      return min;
    }
    return Math.min(max, Math.max(min, value));
  },

  rectCenter(rect) {
    return {
      x: this.number(rect?.x) + this.number(rect?.width) / 2,
      y: this.number(rect?.y) + this.number(rect?.height) / 2,
    };
  },

  nodeLayout(node) {
    const layout = node?.layout || {};
    return {
      x: this.number(layout.x),
      y: this.number(layout.y),
      width: this.number(layout.width, 260),
      height: this.number(layout.height, 150),
    };
  },

  parentWorldArea(parent) {
    const layout = this.nodeLayout(parent);
    return {
      x: layout.x + INTERIOR_STAGE.x,
      y: layout.y + INTERIOR_STAGE.y,
      width: INTERIOR_STAGE.width,
      height: INTERIOR_STAGE.height,
    };
  },

  parentLocalWorldArea() {
    return {
      x: INTERIOR_STAGE.x,
      y: INTERIOR_STAGE.y,
      width: INTERIOR_STAGE.width,
      height: INTERIOR_STAGE.height,
    };
  },

  parentNestedArea(parent) {
    const layout = this.nodeLayout(parent);
    const inset = this.nestedDisplayInset;
    return {
      x: inset,
      y: inset,
      width: Math.max(56, layout.width - inset * 2),
      height: Math.max(40, layout.height - inset * 2),
    };
  },

  scaledSize(size, scale = 1) {
    const factor = this.clamp(this.number(scale, 1), 0.5, 1.8);
    return {
      width: Math.round(size.width * factor),
      height: Math.round(size.height * factor),
    };
  },

  worldChildSize(count, scale = 1) {
    let size;
    if (count <= 1) {
      size = { width: 300, height: 180 };
    } else if (count <= 4) {
      size = { width: 220, height: 132 };
    } else if (count <= 9) {
      size = { width: 180, height: 112 };
    } else {
      size = { width: 150, height: 96 };
    }
    return this.scaledSize(size, scale);
  },

  nestedChildSize(count, scale = 1) {
    let size;
    if (count <= 1) {
      size = { width: 150, height: 58 };
    } else if (count <= 4) {
      size = { width: 96, height: 38 };
    } else if (count <= 9) {
      size = { width: 72, height: 30 };
    } else {
      size = { width: 58, height: 24 };
    }
    return this.scaledSize(size, scale);
  },

  minimumParentSizeForChildren(count, scale = 1) {
    if (count <= 0) {
      return { width: 0, height: 0 };
    }
    const columns = Math.max(1, Math.ceil(Math.sqrt(count)));
    const rows = Math.max(1, Math.ceil(count / columns));
    const size = this.nestedChildSize(count, scale);
    return {
      width: this.nestedDisplayInset * 2 + columns * size.width + Math.max(0, columns - 1) * 12,
      height: this.nestedDisplayInset * 2 + rows * size.height + Math.max(0, rows - 1) * 10,
    };
  },

  anchors(count, spacing = 1) {
    if (count <= 1) {
      return [{ x: 0.5, y: 0.5 }];
    }
    const spacingScale = this.clamp(this.number(spacing, 1), 0.5, 1.5);
    if (count === 2) {
      const offset = this.clamp(0.18 * spacingScale, 0.08, 0.46);
      return [
        { x: 0.5 - offset, y: 0.5 },
        { x: 0.5 + offset, y: 0.5 },
      ];
    }
    const radius = this.clamp((count <= 4 ? 0.34 : 0.38) * spacingScale, 0.12, 0.48);
    return Array.from({ length: count }, (_, index) => {
      const angle = -Math.PI / 2 + (Math.PI * 2 * index) / count;
      return {
        x: 0.5 + Math.cos(angle) * radius,
        y: 0.5 + Math.sin(angle) * radius,
      };
    });
  },

  rectAtAnchor(area, size, anchor) {
    const width = Math.min(size.width, Math.max(8, area.width));
    const height = Math.min(size.height, Math.max(6, area.height));
    const centerX = area.x + area.width * anchor.x;
    const centerY = area.y + area.height * anchor.y;
    return {
      x: Math.round(this.clamp(centerX - width / 2, area.x, area.x + area.width - width)),
      y: Math.round(this.clamp(centerY - height / 2, area.y, area.y + area.height - height)),
      width: Math.round(width),
      height: Math.round(height),
    };
  },

  planParentChildren(parent, children, options = {}) {
    const anchors = this.anchors(children.length, options.spacing);
    const worldArea = this.parentWorldArea(parent);
    const nestedArea = this.parentNestedArea(parent);
    const worldSize = this.worldChildSize(children.length, options.sizeScale);
    const nestedSize = this.nestedChildSize(children.length, options.sizeScale);
    return children.map((child, index) => ({
      node: child,
      worldLayout: this.rectAtAnchor(worldArea, worldSize, anchors[index]),
      nestedLayout: this.rectAtAnchor(nestedArea, nestedSize, anchors[index]),
    }));
  },

  rootWorldArea() {
    return {
      x: powanWorkspace.origin.x - INTERIOR_STAGE.width / 2,
      y: powanWorkspace.origin.y - INTERIOR_STAGE.height / 2,
      width: INTERIOR_STAGE.width,
      height: INTERIOR_STAGE.height,
    };
  },

  planRootChildren(children, options = {}) {
    const anchors = this.anchors(children.length, options.spacing);
    const worldArea = this.rootWorldArea();
    const worldSize = this.worldChildSize(children.length, options.sizeScale);
    return children.map((child, index) => ({
      node: child,
      worldLayout: this.rectAtAnchor(worldArea, worldSize, anchors[index]),
    }));
  },

  hasWorldLayout(node) {
    const layout = node?.layout || {};
    return Number.isFinite(Number(layout.x)) && Number.isFinite(Number(layout.y));
  },

  hasNestedLayout(node, parentId) {
    const layout = node?.nestedLayoutByParent?.[parentId] || {};
    return Number.isFinite(Number(layout.x)) && Number.isFinite(Number(layout.y));
  },

  nestedLayoutFromWorld(parent, child, nestedSize = null) {
    const worldArea = this.parentWorldArea(parent);
    const nestedArea = this.parentNestedArea(parent);
    const childLayout = this.nodeLayout(child);
    const center = this.rectCenter(childLayout);
    const tX = this.clamp((center.x - worldArea.x) / Math.max(1, worldArea.width), 0, 1);
    const tY = this.clamp((center.y - worldArea.y) / Math.max(1, worldArea.height), 0, 1);
    const existing = child?.nestedLayoutByParent?.[parent.id] || {};
    const siblingCount = typeof powanExplorer !== "undefined" && powanExplorer?.childrenOf
      ? Math.max(1, powanExplorer.childrenOf(parent).length)
      : 1;
    const size = nestedSize || {
      width: this.number(existing.width, this.nestedChildSize(siblingCount).width),
      height: this.number(existing.height, this.nestedChildSize(siblingCount).height),
    };
    return this.rectAtAnchor(nestedArea, size, { x: tX, y: tY });
  },

  worldLayoutFromNested(parent, child, nestedLayout) {
    const worldArea = this.parentWorldArea(parent);
    const nestedArea = this.parentNestedArea(parent);
    const childLayout = this.nodeLayout(child);
    const center = this.rectCenter(nestedLayout);
    const tX = this.clamp((center.x - nestedArea.x) / Math.max(1, nestedArea.width), 0, 1);
    const tY = this.clamp((center.y - nestedArea.y) / Math.max(1, nestedArea.height), 0, 1);
    return {
      x: Math.round(worldArea.x + worldArea.width * tX - childLayout.width / 2),
      y: Math.round(worldArea.y + worldArea.height * tY - childLayout.height / 2),
      width: Math.round(childLayout.width),
      height: Math.round(childLayout.height),
    };
  },

  displayRectForNode(node) {
    const layout = this.nodeLayout(node);
    const origin = currentWorldOrigin();
    return {
      x: layout.x - origin.x,
      y: layout.y - origin.y,
      width: layout.width,
      height: layout.height,
    };
  },

  dragFrameForNestedLayer(layer, element) {
    const isPreview = layer?.classList?.contains("nested-preview-layer");
    return {
      type: isPreview ? "preview" : "nested",
      width: Math.max(1, layer?.offsetWidth || 1),
      height: Math.max(1, layer?.offsetHeight || 1),
      depth: this.number(element?.style?.getPropertyValue("--preview-depth"), 1),
    };
  },

  nestedLayoutFromDragFrame(parent, child, frame, localRect) {
    if (frame?.type !== "preview") {
      return {
        x: Math.round(localRect.x),
        y: Math.round(localRect.y),
        width: Math.round(localRect.width),
        height: Math.round(localRect.height),
      };
    }
    const previewArea = typeof nestedPreviewArea === "function"
      ? nestedPreviewArea(frame.width, frame.height, frame.depth)
      : { x: 0, y: 0, width: frame.width, height: frame.height };
    const center = this.rectCenter(localRect);
    const anchor = {
      x: this.clamp((center.x - previewArea.x) / Math.max(1, previewArea.width), 0, 1),
      y: this.clamp((center.y - previewArea.y) / Math.max(1, previewArea.height), 0, 1),
    };
    const existing = child?.nestedLayoutByParent?.[parent.id] || {};
    const size = {
      width: this.number(existing.width, this.nestedChildSize(1).width),
      height: this.number(existing.height, this.nestedChildSize(1).height),
    };
    return this.rectAtAnchor(this.parentNestedArea(parent), size, anchor);
  },

  // === A2: 入れ子チップは「親の内部世界の等比縮小ビュー」 ===
  // 子の位置の真実は世界座標(layout)のみ。チップ位置はそこから導出する。

  // 子の位置を親の内部世界フレーム(INTERIOR_STAGE と同じ座標)で返す。
  // = 親世界に入ったときの表示位置（child.layout - parent.layout）。
  childInteriorRect(parent, child) {
    const parentLayout = this.nodeLayout(parent);
    const childLayout = this.nodeLayout(child);
    return {
      x: childLayout.x - parentLayout.x,
      y: childLayout.y - parentLayout.y,
      width: childLayout.width,
      height: childLayout.height,
    };
  },

  // 親の箱の入れ子レイヤー(layerSize)へ INTERIOR_STAGE を等比で収めるスケールと、
  // 余白を中央寄せするオフセット。形を保つため x/y 同一スケール。
  nestedViewScale(layerSize) {
    const layerWidth = Math.max(1, this.number(layerSize?.width, 1));
    const layerHeight = Math.max(1, this.number(layerSize?.height, 1));
    const scale = Math.min(layerWidth / INTERIOR_STAGE.width, layerHeight / INTERIOR_STAGE.height);
    return {
      scale,
      offsetX: (layerWidth - INTERIOR_STAGE.width * scale) / 2,
      offsetY: (layerHeight - INTERIOR_STAGE.height * scale) / 2,
    };
  },

  // 世界座標の子 → 入れ子レイヤー内のチップ矩形（等比縮小ビュー）。
  nestedViewRect(parent, child, layerSize) {
    const interior = this.childInteriorRect(parent, child);
    const { scale, offsetX, offsetY } = this.nestedViewScale(layerSize);
    return {
      x: Math.round(offsetX + (interior.x - INTERIOR_STAGE.x) * scale),
      y: Math.round(offsetY + (interior.y - INTERIOR_STAGE.y) * scale),
      width: Math.round(interior.width * scale),
      height: Math.round(interior.height * scale),
    };
  },

  // 入れ子レイヤー内のチップ矩形 → 世界座標の子 layout（nestedViewRect の逆）。
  // チップをドラッグしたとき、世界座標へ書き戻すために使う。
  worldLayoutFromNestedView(parent, child, chipRect, layerSize) {
    const parentLayout = this.nodeLayout(parent);
    const { scale, offsetX, offsetY } = this.nestedViewScale(layerSize);
    const safeScale = Math.max(0.0001, scale);
    const interiorX = INTERIOR_STAGE.x + (this.number(chipRect?.x) - offsetX) / safeScale;
    const interiorY = INTERIOR_STAGE.y + (this.number(chipRect?.y) - offsetY) / safeScale;
    const childLayout = this.nodeLayout(child);
    const width = chipRect?.width != null ? this.number(chipRect.width) / safeScale : childLayout.width;
    const height = chipRect?.height != null ? this.number(chipRect.height) / safeScale : childLayout.height;
    return {
      x: Math.round(parentLayout.x + interiorX),
      y: Math.round(parentLayout.y + interiorY),
      width: Math.round(width),
      height: Math.round(height),
    };
  },
};
