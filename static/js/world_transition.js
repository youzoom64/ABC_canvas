var powanWorldTransition = {
  captureLeave(parent) {
    const canvasRect = canvas.getBoundingClientRect();
    return {
      direction: "leave",
      parentId: parent?.id || null,
      canvasRect,
      shell: this.createLeaveShell(parent, canvasRect),
      ghosts: this.createLeaveGhosts(canvasRect),
    };
  },

  prepareLeave(context) {
    if (!context?.shell) {
      return;
    }
    this.applyLeaveLayerOrder(context);
    canvas.appendChild(context.shell);
    for (const ghost of context.ghosts || []) {
      canvas.appendChild(ghost);
    }
    canvas.classList.add("leaving-interior-world");
  },

  playLeave(context, { parent }) {
    if (!context?.shell || !parent) {
      return waitForWorldTransition().then(() => false);
    }
    requestAnimationFrame(() => {
      const target = nodeElementById(parent.id);
      const targetRect = rectSnapshot(target?.getBoundingClientRect());
      if (!targetRect) {
        logEvent("warn", "world-transition-leave-target-missing", { parentId: parent.id });
        this.cleanupLeave(context, target);
        return;
      }
      target.classList.add("leaving-target", "receiving-interior-world");
      const latestCanvasRect = canvas.getBoundingClientRect();
      context.shell.style.setProperty("--target-left", `${targetRect.left - latestCanvasRect.left}px`);
      context.shell.style.setProperty("--target-top", `${targetRect.top - latestCanvasRect.top}px`);
      context.shell.style.setProperty("--target-scale-x", `${targetRect.width / Math.max(1, context.canvasRect.width)}`);
      context.shell.style.setProperty("--target-scale-y", `${targetRect.height / Math.max(1, context.canvasRect.height)}`);
      const records = this.prepareGhostTargets(context.ghosts || [], latestCanvasRect, parent);
      requestAnimationFrame(() => context.shell.classList.add("collapse"));
      requestAnimationFrame(() => this.collapseGhosts(records, latestCanvasRect));
      window.setTimeout(() => this.cleanupLeave(context, target, records), WORLD_TRANSITION_MS);
      logEvent("trace", "world-transition-leave-shell-start", {
        parentId: parent.id,
        childCount: records.length,
        targetRect: {
          left: Math.round(targetRect.left),
          top: Math.round(targetRect.top),
          width: Math.round(targetRect.width),
          height: Math.round(targetRect.height),
        },
      });
    });
    return waitForWorldTransition().then(() => true);
  },

  applyLeaveLayerOrder(context) {
    context.shell.style.setProperty("--transition-shell-z", "40");
    for (const ghost of context.ghosts || []) {
      ghost.style.setProperty("--transition-ghost-z", "48");
    }
  },

  captureEnter(parent, sourceElement = null) {
    const source = sourceElement || nodeElementById(parent?.id);
    const sourceRect = rectSnapshot(source?.getBoundingClientRect());
    const canvasRect = canvas.getBoundingClientRect();
    return {
      direction: "enter",
      parentId: parent?.id || null,
      sourceRect,
      canvasRect,
      ghostSources: this.captureEnterGhostSources(parent, source),
    };
  },

  playEnter(context, { parent }) {
    if (!context?.sourceRect || !parent) {
      logEvent("debug", "world-transition-enter-source-missing", { parentId: parent?.id || null });
      return waitForWorldTransition().then(() => false);
    }
    const portal = this.createEnterPortal(parent, context.sourceRect, context.canvasRect);
    canvas.appendChild(portal);
    const latestCanvasRect = canvas.getBoundingClientRect();
    const records = this.createEnterGhosts(context.ghostSources || [], latestCanvasRect);
    requestAnimationFrame(() => portal.classList.add("expand"));
    requestAnimationFrame(() => this.expandGhosts(records, latestCanvasRect));
    window.setTimeout(() => this.cleanupEnter(portal, records), WORLD_TRANSITION_MS);
    logEvent("trace", "world-transition-enter-start", {
      parentId: parent.id,
      childCount: records.length,
      sourceRect: {
        left: Math.round(context.sourceRect.left),
        top: Math.round(context.sourceRect.top),
        width: Math.round(context.sourceRect.width),
        height: Math.round(context.sourceRect.height),
      },
    });
    return waitForWorldTransition().then(() => true);
  },

  captureEnterGhostSources(parent, sourceElement) {
    if (!parent || !sourceElement) {
      return [];
    }
    const records = meaningChildren(parent)
      .map((child) => {
        const source = this.sourceChildElement(sourceElement, child.id) || visualElementById(child.id);
        const fromRect = rectSnapshot(source?.getBoundingClientRect());
        return fromRect ? { nodeId: child.id, fromRect } : null;
      })
      .filter(Boolean);
    logEvent("trace", "world-transition-enter-ghost-sources", {
      parentId: parent.id,
      count: records.length,
    });
    return records;
  },

  sourceChildElement(sourceElement, childId) {
    if (!sourceElement || !childId) {
      return null;
    }
    const selector = `.nested-meaning[data-id="${CSS.escape(childId)}"], .nested-preview-meaning[data-id="${CSS.escape(childId)}"]`;
    return sourceElement.querySelector(selector);
  },

  createLeaveShell(parent, canvasRect) {
    const style = parent?.style || {};
    const shell = document.createElement("div");
    shell.className = `interior-leave-shell shape-${style.shape || "cloud"}`;
    shell.style.left = "0px";
    shell.style.top = "0px";
    shell.style.width = `${canvasRect.width}px`;
    shell.style.height = `${canvasRect.height}px`;
    shell.style.setProperty("--node-color", style.color || "#ffffff");
    shell.style.setProperty("--accent", style.accent || "#8ddcff");
    attachSoftBodyToTransitionSurface(shell, {
      width: canvasRect.width,
      height: canvasRect.height,
    });
    logEvent("trace", "world-transition-leave-shell-snapshot", {
      parentId: parent?.id || null,
      childCount: currentWorldNodes().length,
    });
    return shell;
  },

  createLeaveGhosts(canvasRect) {
    return currentWorldNodes()
      .map((node) => this.createWorldGhost(node, canvasRect))
      .filter(Boolean);
  },

  createWorldGhost(node, canvasRect) {
    const element = visualElementById(node.id);
    const fromRect = rectSnapshot(element?.getBoundingClientRect());
    if (!element || !fromRect) {
      return null;
    }
    const ghost = element.cloneNode(true);
    this.removeDescendantPreviews(ghost);
    ghost.removeAttribute("data-id");
    ghost.dataset.transitionSourceId = node.id;
    ghost.querySelectorAll("[data-id]").forEach((child) => child.removeAttribute("data-id"));
    ghost.querySelectorAll("textarea, input").forEach((control) => {
      control.readOnly = true;
      control.tabIndex = -1;
      control.blur();
    });
    ghost.classList.remove(
      "selected",
      "dragging",
      "dragging-nested-descendant",
      "drag-softbody",
      "meaning-enter-pop",
      "meaning-release-pop",
      "nested-release-bounce",
      "leaving-target",
    );
    ghost.classList.add("meaning-shared-ghost");
    ghost.style.left = `${fromRect.left - canvasRect.left}px`;
    ghost.style.top = `${fromRect.top - canvasRect.top}px`;
    ghost.style.width = `${fromRect.width}px`;
    ghost.style.height = `${fromRect.height}px`;
    attachSoftBodyToTransitionSurface(
      ghost,
      {
        width: fromRect.width,
        height: fromRect.height,
      },
      { kind: ghost.classList.contains("node") ? "node" : "nested" },
    );
    return ghost;
  },

  removeDescendantPreviews(ghost) {
    ghost.querySelectorAll(".nested-layer, .nested-preview-layer").forEach((layer) => layer.remove());
    ghost.querySelectorAll(".nested-meaning, .nested-preview-meaning").forEach((element) => element.remove());
    ghost.classList.remove("has-nested-meanings", "has-nested-preview");
  },

  prepareGhostTargets(ghosts, canvasRect, parent = null) {
    const records = [];
    for (const ghost of ghosts) {
      const nodeId = ghost.dataset.transitionSourceId;
      const target = visualElementById(nodeId);
      const toRect = this.leaveNestedTargetRect(parent, nodeId) || rectSnapshot(target?.getBoundingClientRect());
      if (!toRect) {
        ghost.remove();
        continue;
      }
      target?.classList.add("meaning-shared-target");
      records.push({ ghost, target, toRect });
    }
    logEvent("trace", "world-transition-leave-ghost-targets", {
      count: records.length,
      canvas: {
        left: Math.round(canvasRect.left),
        top: Math.round(canvasRect.top),
        width: Math.round(canvasRect.width),
        height: Math.round(canvasRect.height),
      },
    });
    return records;
  },

  leaveNestedTargetRect(parent, nodeId) {
    const child = nodeById(nodeId);
    const parentElement = parent ? nodeElementById(parent.id) : null;
    const layer = parentElement?.querySelector(".nested-layer");
    if (!parent || !child || child.parent !== parent.id || !layer) {
      return null;
    }
    const layerRect = rectSnapshot(layer.getBoundingClientRect());
    if (!layerRect || !layerRect.width || !layerRect.height) {
      return null;
    }
    const fallback = powanPlacement.planParentChildren(parent, meaningChildren(parent))
      .find((plan) => plan.node.id === child.id)?.nestedLayout;
    const placement = nestedPlacementFromLayout(parent, child, fallback);
    if (!placement) {
      return null;
    }
    const scaleX = layerRect.width / Math.max(1, layer.offsetWidth || layerRect.width);
    const scaleY = layerRect.height / Math.max(1, layer.offsetHeight || layerRect.height);
    const toRect = {
      left: layerRect.left + placement.x * scaleX,
      top: layerRect.top + placement.y * scaleY,
      width: placement.width * scaleX,
      height: placement.height * scaleY,
    };
    logEvent("trace", "world-transition-leave-nested-target-from-layout", {
      parentId: parent.id,
      nodeId: child.id,
      nestedLayout: child.nestedLayoutByParent?.[parent.id] || null,
      toRect: {
        left: Math.round(toRect.left),
        top: Math.round(toRect.top),
        width: Math.round(toRect.width),
        height: Math.round(toRect.height),
      },
    });
    return toRect;
  },

  collapseGhosts(records, canvasRect) {
    for (const record of records) {
      record.ghost.style.left = `${record.toRect.left - canvasRect.left}px`;
      record.ghost.style.top = `${record.toRect.top - canvasRect.top}px`;
      record.ghost.style.width = `${record.toRect.width}px`;
      record.ghost.style.height = `${record.toRect.height}px`;
      record.ghost.classList.add("collapse");
    }
  },

  createEnterGhosts(sources, canvasRect) {
    const records = [];
    for (const source of sources) {
      const target = visualElementById(source.nodeId);
      const toRect = rectSnapshot(target?.getBoundingClientRect());
      if (!target || !toRect) {
        continue;
      }
      const ghost = target.cloneNode(true);
      ghost.removeAttribute("data-id");
      ghost.dataset.transitionSourceId = source.nodeId;
      ghost.querySelectorAll("[data-id]").forEach((child) => child.removeAttribute("data-id"));
      ghost.querySelectorAll("textarea, input").forEach((control) => {
        control.readOnly = true;
        control.tabIndex = -1;
        control.blur();
      });
      ghost.classList.remove(
        "selected",
        "dragging",
        "dragging-nested-descendant",
        "drag-softbody",
        "meaning-enter-pop",
        "meaning-release-pop",
        "nested-release-bounce",
      );
      ghost.classList.add("meaning-shared-ghost", "expand-source");
      ghost.style.left = `${source.fromRect.left - canvasRect.left}px`;
      ghost.style.top = `${source.fromRect.top - canvasRect.top}px`;
      ghost.style.width = `${source.fromRect.width}px`;
      ghost.style.height = `${source.fromRect.height}px`;
      attachSoftBodyToTransitionSurface(
        ghost,
        {
          width: source.fromRect.width,
          height: source.fromRect.height,
        },
        { kind: ghost.classList.contains("node") ? "node" : "nested" },
      );
      target.classList.add("meaning-shared-target");
      canvas.appendChild(ghost);
      records.push({ ghost, target, toRect });
    }
    logEvent("trace", "world-transition-enter-ghost-targets", {
      count: records.length,
      canvas: {
        left: Math.round(canvasRect.left),
        top: Math.round(canvasRect.top),
        width: Math.round(canvasRect.width),
        height: Math.round(canvasRect.height),
      },
    });
    return records;
  },

  expandGhosts(records, canvasRect) {
    for (const record of records) {
      record.ghost.style.left = `${record.toRect.left - canvasRect.left}px`;
      record.ghost.style.top = `${record.toRect.top - canvasRect.top}px`;
      record.ghost.style.width = `${record.toRect.width}px`;
      record.ghost.style.height = `${record.toRect.height}px`;
      record.ghost.classList.add("expand");
    }
  },

  createEnterPortal(parent, sourceRect, canvasRect) {
    const style = parent.style || {};
    const portal = document.createElement("div");
    portal.className = `interior-enter-portal shape-${style.shape || "cloud"}`;
    portal.style.left = `${sourceRect.left - canvasRect.left}px`;
    portal.style.top = `${sourceRect.top - canvasRect.top}px`;
    portal.style.width = `${sourceRect.width}px`;
    portal.style.height = `${sourceRect.height}px`;
    portal.style.setProperty("--node-color", style.color || "#ffffff");
    portal.style.setProperty("--accent", style.accent || "#8ddcff");
    attachSoftBodyToTransitionSurface(portal, {
      width: sourceRect.width,
      height: sourceRect.height,
    });
    return portal;
  },

  cleanupLeave(context, target, records = []) {
    context.shell?.remove();
    for (const record of records) {
      record.ghost.remove();
      record.target?.classList.remove("meaning-shared-target");
    }
    target?.classList.remove("leaving-target", "receiving-interior-world");
    canvas.classList.remove("leaving-interior-world");
  },

  cleanupEnter(portal, records = []) {
    portal?.remove();
    for (const record of records) {
      record.ghost.remove();
      record.target.classList.remove("meaning-shared-target");
    }
  },
};
