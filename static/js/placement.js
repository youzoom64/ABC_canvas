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

  scaleRectFromCenter(rect, factor, limits = {}) {
    const center = this.rectCenter(rect);
    const scale = this.number(factor, 1);
    const minWidth = this.number(limits.minWidth, 1);
    const minHeight = this.number(limits.minHeight, 1);
    const maxWidth = this.number(limits.maxWidth, Number.POSITIVE_INFINITY);
    const maxHeight = this.number(limits.maxHeight, Number.POSITIVE_INFINITY);
    const width = this.clamp(this.number(rect?.width, 1) * scale, minWidth, maxWidth);
    const height = this.clamp(this.number(rect?.height, 1) * scale, minHeight, maxHeight);
    return this.rectFromCenter(center, { width, height });
  },

  moveRectFromAreaCenter(rect, area, factor) {
    const rectCenter = this.rectCenter(rect);
    const areaCenter = this.rectCenter(area);
    const scale = this.number(factor, 1);
    const nextCenter = {
      x: areaCenter.x + (rectCenter.x - areaCenter.x) * scale,
      y: areaCenter.y + (rectCenter.y - areaCenter.y) * scale,
    };
    return this.rectFromCenter(nextCenter, {
      width: this.number(rect?.width, 1),
      height: this.number(rect?.height, 1),
    });
  },

  rectFromCenter(center, size, bounds = null) {
    const width = Math.round(Math.max(1, this.number(size?.width, 1)));
    const height = Math.round(Math.max(1, this.number(size?.height, 1)));
    const centerX = this.number(center?.x);
    const centerY = this.number(center?.y);
    const rawX = centerX - width / 2;
    const rawY = centerY - height / 2;
    const x = bounds
      ? this.clamp(rawX, this.number(bounds.x), this.number(bounds.x) + Math.max(0, this.number(bounds.width) - width))
      : rawX;
    const y = bounds
      ? this.clamp(rawY, this.number(bounds.y), this.number(bounds.y) + Math.max(0, this.number(bounds.height) - height))
      : rawY;
    return {
      x: Math.round(x),
      y: Math.round(y),
      width,
      height,
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

  parentWorldArea(_parent) {
    return this.rootWorldArea();
  },

  parentWorldViewportArea(_parent) {
    return {
      x: INTERIOR_STAGE.x,
      y: INTERIOR_STAGE.y,
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
    const inset = this.nestedLayerInset;
    return {
      x: 0,
      y: 0,
      width: Math.max(56, layout.width - inset * 2),
      height: Math.max(40, layout.height - inset * 2),
    };
  },

  scaledSize(size, scale = 1) {
    const factor = this.clamp(this.number(scale, 1), 0.3, 2.5);
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

  minimumParentSizeForChildren(count, scale = 1, spacing = 1) {
    if (count <= 0) {
      return { width: 0, height: 0 };
    }
    const columns = Math.max(1, Math.ceil(Math.sqrt(count)));
    const rows = Math.max(1, Math.ceil(count / columns));
    const size = this.nestedChildSize(count, scale);
    const spacingScale = this.clamp(this.number(spacing, 1), 0.3, 3);
    return {
      width: this.nestedDisplayInset * 2 + columns * size.width + Math.max(0, columns - 1) * 12 * spacingScale,
      height: this.nestedDisplayInset * 2 + rows * size.height + Math.max(0, rows - 1) * 10 * spacingScale,
    };
  },

  anchors(count, spacing = 1) {
    if (count <= 1) {
      return [{ x: 0.5, y: 0.5 }];
    }
    const spacingScale = this.clamp(this.number(spacing, 1), 0.3, 3);
    const radius = this.clamp((count <= 4 ? 0.34 : 0.38) * spacingScale, 0.12, 0.86);
    return Array.from({ length: count }, (_, index) => {
      const angle = -Math.PI / 2 - Math.PI / count + (Math.PI * 2 * index) / count;
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
    return this.rectFromCenter({ x: centerX, y: centerY }, { width, height }, area);
  },

  arrangeRadially(area, items, size, spacing = 1) {
    const anchors = this.anchors(items.length, spacing);
    return items.map((item, index) => ({
      item,
      layout: (() => {
        const anchor = anchors[index] || { x: 0.5, y: 0.5 };
        const width = this.number(size?.width, 1);
        const height = this.number(size?.height, 1);
        const centerX = area.x + area.width * anchor.x;
        const centerY = area.y + area.height * anchor.y;
        return {
          x: Math.round(centerX - width / 2),
          y: Math.round(centerY - height / 2),
          width: Math.round(width),
          height: Math.round(height),
        };
      })(),
    }));
  },

  fallbackOffset(anchor, width, height) {
    return {
      x: (this.number(anchor?.x, 0.5) - 0.5) * width,
      y: (this.number(anchor?.y, 0.5) - 0.5) * height,
    };
  },

  planWorldChildren(parent, children, options = {}) {
    const anchors = this.anchors(children.length, options.spacing);
    const worldOrigin = powanWorkspace.origin;
    const nestedArea = parent ? this.parentNestedArea(parent) : null;
    const nestedOrigin = nestedArea ? this.rectCenter(nestedArea) : null;
    const worldSize = this.worldChildSize(children.length, options.worldSizeScale ?? options.sizeScale);
    const nestedSize = parent ? this.nestedChildSize(children.length, options.nestedSizeScale ?? options.sizeScale) : null;
    const worldFallbackWidth = INTERIOR_STAGE.width * 0.76;
    const worldFallbackHeight = INTERIOR_STAGE.height * 0.76;
    return children.map((child, index) => {
      const anchor = anchors[index] || { x: 0.5, y: 0.5 };
      const worldOffset = this.fallbackOffset(anchor, worldFallbackWidth, worldFallbackHeight);
      const worldCenter = {
        x: worldOrigin.x + worldOffset.x,
        y: worldOrigin.y + worldOffset.y,
      };
      const nestedLayout = parent ? (() => {
        const nestedOffset = this.fallbackOffset(anchor, nestedArea.width * 0.76, nestedArea.height * 0.76);
        const nextCenter = {
          x: nestedOrigin.x + nestedOffset.x,
          y: nestedOrigin.y + nestedOffset.y,
        };
        return this.rectFromCenter(nextCenter, nestedSize, nestedArea);
      })() : null;
      return {
        node: child,
        worldLayout: this.rectFromCenter(worldCenter, worldSize),
        nestedLayout,
      };
    });
  },

  planParentChildren(parent, children, options = {}) {
    return this.planWorldChildren(parent, children, options);
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
    return this.planWorldChildren(null, children, options);
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
      x: (center.x - previewArea.x) / Math.max(1, previewArea.width),
      y: (center.y - previewArea.y) / Math.max(1, previewArea.height),
    };
    const childCount = typeof meaningChildren === "function"
      ? Math.max(1, meaningChildren(parent).length)
      : 1;
    const columns = Math.ceil(Math.sqrt(childCount));
    const rows = Math.ceil(childCount / columns);
    const previewSize = typeof nestedPreviewChildSize === "function"
      ? nestedPreviewChildSize(previewArea.width / columns, previewArea.height / rows, frame.depth)
      : this.nestedChildSize(childCount, 1);
    const storedBaseSize = this.nestedChildSize(childCount, 1);
    const displayScale = this.clamp(
      ((this.number(localRect?.width, previewSize.width) / Math.max(1, previewSize.width)) +
        (this.number(localRect?.height, previewSize.height) / Math.max(1, previewSize.height))) / 2,
      0.3,
      2.5,
    );
    const parentArea = this.parentNestedArea(parent);
    const size = {
      width: Math.round(storedBaseSize.width * displayScale),
      height: Math.round(storedBaseSize.height * displayScale),
    };
    return {
      x: Math.round(parentArea.x + parentArea.width * anchor.x - size.width / 2),
      y: Math.round(parentArea.y + parentArea.height * anchor.y - size.height / 2),
      width: size.width,
      height: size.height,
    };
  },

  // === A2: 入れ子チップは「親の内部世界の等比縮小ビュー」 ===
  // 子の位置の真実は世界座標(layout)のみ。チップ位置はそこから導出する。

  worldRectToInteriorRect(parent, rect) {
    const worldArea = this.parentWorldArea(parent);
    return {
      x: Math.round(INTERIOR_STAGE.x + this.number(rect?.x) - worldArea.x),
      y: Math.round(INTERIOR_STAGE.y + this.number(rect?.y) - worldArea.y),
      width: Math.round(this.number(rect?.width, 260)),
      height: Math.round(this.number(rect?.height, 150)),
    };
  },

  interiorRectToWorldLayout(parent, child, rect) {
    const worldArea = this.parentWorldArea(parent);
    const childLayout = this.nodeLayout(child);
    const width = this.number(rect?.width, childLayout.width);
    const height = this.number(rect?.height, childLayout.height);
    return {
      x: Math.round(worldArea.x + this.number(rect?.x) - INTERIOR_STAGE.x),
      y: Math.round(worldArea.y + this.number(rect?.y) - INTERIOR_STAGE.y),
      width: Math.round(width),
      height: Math.round(height),
    };
  },

  // 子の位置を親の内部世界フレーム(INTERIOR_STAGE と同じ座標)で返す。
  // 中の世界も最上位と同じ 10000 座標を使うので、親の左上ではなく共通世界エリアから写像する。
  childInteriorRect(parent, child) {
    return this.worldRectToInteriorRect(parent, this.nodeLayout(child));
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
    const { scale, offsetX, offsetY } = this.nestedViewScale(layerSize);
    const safeScale = Math.max(0.0001, scale);
    const interiorX = INTERIOR_STAGE.x + (this.number(chipRect?.x) - offsetX) / safeScale;
    const interiorY = INTERIOR_STAGE.y + (this.number(chipRect?.y) - offsetY) / safeScale;
    const childLayout = this.nodeLayout(child);
    const width = chipRect?.width != null ? this.number(chipRect.width) / safeScale : childLayout.width;
    const height = chipRect?.height != null ? this.number(chipRect.height) / safeScale : childLayout.height;
    return this.interiorRectToWorldLayout(parent, child, {
      x: interiorX,
      y: interiorY,
      width: Math.round(width),
      height: Math.round(height),
    });
  },
};
