var powanNestedDrag = {
  clipHostClass: "dragging-nested-descendant",

  begin({ nodeId, parentId, element, layer, offsetX, offsetY, pointerId, startX = 0, startY = 0, frame = null }) {
    const dragState = {
      id: nodeId,
      parentId,
      element,
      layer,
      frame: frame || powanPlacement.dragFrameForNestedLayer(layer, element),
      pointerId,
      offsetX,
      offsetY,
      lastX: startX,
      lastY: startY,
      moved: false,
      lastLocalRect: null,
      lastPointerLocalRect: null,
      clipHosts: this.clipHostsFor(layer),
    };
    element.classList.add("dragging");
    for (const host of dragState.clipHosts) {
      host.classList.add(this.clipHostClass);
    }
    return dragState;
  },

  clipHostsFor(layer) {
    const hosts = [];
    const root = typeof getWorldLayer === "function" ? getWorldLayer() : null;
    let current = layer?.parentElement || null;
    while (current && current !== root && current !== document.body) {
      if (
        current.classList?.contains("node") ||
        current.classList?.contains("nested-meaning") ||
        current.classList?.contains("nested-preview-meaning")
      ) {
        hosts.push(current);
      }
      current = current.parentElement;
    }
    return hosts;
  },

  layerScale(dragState) {
    const rect = dragState.layer.getBoundingClientRect();
    return rect.width / Math.max(1, dragState.layer.offsetWidth);
  },

  localRectFromPointer(dragState, clientX, clientY) {
    const layerRect = dragState.layer.getBoundingClientRect();
    const scale = this.layerScale(dragState);
    return {
      x: (clientX - layerRect.left) / scale - dragState.offsetX,
      y: (clientY - layerRect.top) / scale - dragState.offsetY,
      width: dragState.element.offsetWidth,
      height: dragState.element.offsetHeight,
    };
  },

  localPointerFromScreen(dragState, clientX, clientY) {
    const layerRect = dragState.layer.getBoundingClientRect();
    const scale = this.layerScale(dragState);
    return {
      x: (clientX - layerRect.left) / scale,
      y: (clientY - layerRect.top) / scale,
    };
  },

  moveToRect(dragState, localRect) {
    dragState.moved = true;
    dragState.element.style.left = `${localRect.x}px`;
    dragState.element.style.top = `${localRect.y}px`;
    return localRect;
  },

  moveFromPointer(dragState, clientX, clientY) {
    return this.moveToRect(dragState, this.localRectFromPointer(dragState, clientX, clientY));
  },

  storedLayout(parent, node, dragState, localRect) {
    return powanPlacement.nestedLayoutFromDragFrame(parent, node, dragState.frame, localRect);
  },

  rememberedLocalRect(dragState) {
    if (dragState.lastLocalRect) {
      return dragState.lastLocalRect;
    }
    if (dragState.lastPointerLocalRect) {
      return dragState.lastPointerLocalRect;
    }
    return {
      x: Number.parseFloat(dragState.element.style.left || "0"),
      y: Number.parseFloat(dragState.element.style.top || "0"),
      width: dragState.element.offsetWidth,
      height: dragState.element.offsetHeight,
    };
  },

  screenRectFromLocalRect(dragState, localRect) {
    const layerRect = dragState.layer?.getBoundingClientRect();
    if (!layerRect || !localRect) {
      return null;
    }
    const scale = this.layerScale(dragState);
    return {
      left: layerRect.left + localRect.x * scale,
      top: layerRect.top + localRect.y * scale,
      width: localRect.width * scale,
      height: localRect.height * scale,
    };
  },

  localRectFromScreenRect(dragState, screenRect) {
    const layerRect = dragState.layer?.getBoundingClientRect();
    if (!layerRect || !screenRect) {
      return null;
    }
    const scale = this.layerScale(dragState);
    return {
      x: (screenRect.left - layerRect.left) / scale,
      y: (screenRect.top - layerRect.top) / scale,
      width: screenRect.width / scale,
      height: screenRect.height / scale,
    };
  },

  rectOutsideParent(dragState, localRect) {
    if (!dragState.layer || !localRect) {
      return false;
    }
    const center = powanPlacement.rectCenter(localRect);
    return (
      center.x < 0 ||
      center.y < 0 ||
      center.x > dragState.layer.clientWidth ||
      center.y > dragState.layer.clientHeight
    );
  },

  plainScreenRect(screenRect) {
    if (!screenRect) {
      return null;
    }
    return {
      left: screenRect.left,
      top: screenRect.top,
      width: screenRect.width,
      height: screenRect.height,
    };
  },

  releaseCandidates(dragState) {
    const candidates = [];
    const remembered = this.rememberedLocalRect(dragState);
    const visualScreenRect = this.plainScreenRect(dragState.element?.getBoundingClientRect());
    const visual = this.localRectFromScreenRect(dragState, visualScreenRect);
    const pointer = dragState.lastPointerLocalRect || null;
    const add = (source, localRect, screenRect = null) => {
      if (!localRect) {
        return;
      }
      const nextScreenRect = screenRect || this.screenRectFromLocalRect(dragState, localRect);
      candidates.push({
        source,
        localRect,
        screenRect: nextScreenRect,
        outside: this.rectOutsideParent(dragState, localRect),
        center: powanPlacement.rectCenter(localRect),
      });
    };
    add("visual", visual, visualScreenRect || null);
    add("pointer", pointer);
    add("remembered", remembered);
    return candidates;
  },

  releaseSnapshot(dragState) {
    const cached = dragState.releaseSnapshot;
    if (cached) {
      return cached;
    }
    const candidates = this.releaseCandidates(dragState);
    const outsideCandidate = candidates.find((candidate) => candidate.outside) || null;
    const selected = outsideCandidate || candidates[0] || null;
    const fallbackRect = this.plainScreenRect(dragState.element?.getBoundingClientRect());
    const snapshot = {
      outside: Boolean(outsideCandidate),
      decidedBy: outsideCandidate?.source || null,
      releaseSource: selected?.source || "element",
      releaseRect: selected?.screenRect || fallbackRect,
      candidates,
      layerSize: {
        width: dragState.layer?.clientWidth || 0,
        height: dragState.layer?.clientHeight || 0,
      },
    };
    dragState.releaseSnapshot = snapshot;
    return snapshot;
  },

  isOutsideParent(dragState) {
    return this.releaseSnapshot(dragState).outside;
  },

  screenRectForRelease(dragState) {
    return this.releaseSnapshot(dragState).releaseRect || dragState.element.getBoundingClientRect();
  },

  clampInside(dragState) {
    const maxX = Math.max(0, dragState.layer.clientWidth - dragState.element.offsetWidth);
    const maxY = Math.max(0, dragState.layer.clientHeight - dragState.element.offsetHeight);
    const localRect = {
      x: Math.min(maxX, Math.max(0, Number.parseFloat(dragState.element.style.left || "0"))),
      y: Math.min(maxY, Math.max(0, Number.parseFloat(dragState.element.style.top || "0"))),
      width: dragState.element.offsetWidth,
      height: dragState.element.offsetHeight,
    };
    dragState.element.style.left = `${localRect.x}px`;
    dragState.element.style.top = `${localRect.y}px`;
    return localRect;
  },

  releaseParentId(dragState) {
    if (openParentId && openParentId !== dragState.parentId) {
      return openParentId;
    }
    return null;
  },

  cleanup(dragState) {
    for (const host of dragState.clipHosts || []) {
      host.classList.remove(this.clipHostClass);
    }
  },
};
