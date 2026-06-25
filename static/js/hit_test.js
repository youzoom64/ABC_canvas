var powanHitTest = {
  edgeInnerRadius: 1,
  edgeOuterRadius: 1.3,

  localPoint(event, element) {
    const rect = element.getBoundingClientRect();
    return {
      x: event.clientX - rect.left,
      y: event.clientY - rect.top,
      width: rect.width,
      height: rect.height,
    };
  },

  normalizedEllipseDistance(point) {
    const rx = Math.max(1, point.width / 2);
    const ry = Math.max(1, point.height / 2);
    const dx = (point.x - point.width / 2) / rx;
    const dy = (point.y - point.height / 2) / ry;
    return Math.hypot(dx, dy);
  },

  isInsideEllipse(event, element) {
    return this.normalizedEllipseDistance(this.localPoint(event, element)) <= this.edgeOuterRadius;
  },

  isOnEdge(event, element) {
    const distance = this.normalizedEllipseDistance(this.localPoint(event, element));
    return distance >= this.edgeInnerRadius && distance <= this.edgeOuterRadius;
  },

  isNestedTarget(target) {
    return Boolean(target.closest(".nested-meaning, .nested-preview-meaning"));
  },

  closestNestedTarget(target) {
    return target.closest(".nested-meaning, .nested-preview-meaning");
  },

  isNestedElement(element) {
    return Boolean(element?.matches?.(".nested-meaning, .nested-preview-meaning"));
  },

  isTextTarget(target) {
    return Boolean(target.closest(".node-body, input, textarea, select, button"));
  },

  isDragHitTarget(target, element) {
    const hit = target?.closest?.(".powan-drag-hit");
    if (!hit) {
      return false;
    }
    const owner = hit.closest(".node, .nested-meaning, .nested-preview-meaning");
    return owner === element;
  },

  dragDecision(event, element) {
    const point = this.localPoint(event, element);
    const distance = this.normalizedEllipseDistance(point);
    const dragHitTarget = this.isDragHitTarget(event.target, element);
    const insideEllipse = dragHitTarget || distance <= this.edgeOuterRadius;
    const onEdge = dragHitTarget || (distance >= this.edgeInnerRadius && distance <= this.edgeOuterRadius);
    const nestedTarget = this.isNestedTarget(event.target);
    const textTarget = this.isTextTarget(event.target);
    const nestedLayerTarget = Boolean(event.target.closest(".nested-layer"));
    let reason = "accepted";
    let canDrag = true;
    if (!insideEllipse) {
      canDrag = false;
      reason = "outside-ellipse";
    } else if (nestedTarget) {
      canDrag = false;
      reason = "nested-target";
    } else if (textTarget && !onEdge) {
      canDrag = false;
      reason = "text-target-not-edge";
    } else if (nestedLayerTarget && !onEdge) {
      canDrag = false;
      reason = "nested-layer-not-edge";
    } else if (!onEdge) {
      canDrag = false;
      reason = event.target === element ? "host-not-edge" : "not-edge";
    }
    return {
      canDrag,
      reason,
      nodeId: element.dataset.id || null,
      targetClass: String(event.target?.className || ""),
      point: {
        x: Math.round(point.x),
        y: Math.round(point.y),
        width: Math.round(point.width),
        height: Math.round(point.height),
      },
      distance: Number(distance.toFixed(3)),
      insideEllipse,
      onEdge,
      dragHitTarget,
      nestedTarget,
      textTarget,
      nestedLayerTarget,
      targetIsHost: event.target === element,
    };
  },

  canDragNode(event, element) {
    return this.dragDecision(event, element).canDrag;
  },

  dragCueDecision(event, element) {
    if (!this.isNestedElement(element)) {
      return this.dragDecision(event, element);
    }
    const point = this.localPoint(event, element);
    const distance = this.normalizedEllipseDistance(point);
    const closestNested = this.closestNestedTarget(event.target);
    const dragHitTarget = this.isDragHitTarget(event.target, element);
    const insideEllipse = dragHitTarget || distance <= this.edgeOuterRadius;
    const onEdge = dragHitTarget || (distance >= this.edgeInnerRadius && distance <= this.edgeOuterRadius);
    const textTarget = this.isTextTarget(event.target);
    const ownNestedSurface = !closestNested || closestNested === element;
    const canDrag = insideEllipse && onEdge && ownNestedSurface && !textTarget;
    return {
      canDrag,
      reason: canDrag
        ? "accepted"
        : !insideEllipse
          ? "outside-ellipse"
          : !onEdge
            ? "not-edge"
            : !ownNestedSurface
              ? "nested-target"
              : "text-target",
      nodeId: element.dataset.id || null,
      targetClass: String(event.target?.className || ""),
      point: {
        x: Math.round(point.x),
        y: Math.round(point.y),
        width: Math.round(point.width),
        height: Math.round(point.height),
      },
      distance: Number(distance.toFixed(3)),
      insideEllipse,
      onEdge,
      dragHitTarget,
      nestedTarget: !ownNestedSurface,
      textTarget,
      nestedLayerTarget: false,
      targetIsHost: event.target === element,
    };
  },

  syncNodeCursor(event, element) {
    element.classList.toggle("drag-edge", this.dragCueDecision(event, element).canDrag);
  },

  clearNodeCursor(element) {
    element.classList.remove("drag-edge");
  },
};
