var powanStateTransition = {
  run(request) {
    const transition = {
      ...(request || {}),
      animationPlan: this.animationPlanFor(request || {}),
    };
    logEvent("trace", "state-transition-run", {
      type: transition.type || null,
      childId: transition.childId || null,
      parentId: transition.parentId || transition.parent?.id || null,
      nextParentId: transition.nextParentId || null,
      animationPlan: transition.animationPlan,
    });
    if (transition.type === "attach") {
      return this.attach(transition);
    }
    if (transition.type === "detach") {
      return this.detach(transition);
    }
    if (transition.type === "world-leave") {
      return this.worldLeave(transition);
    }
    if (transition.type === "world-enter") {
      return this.worldEnter(transition);
    }
    logEvent("warn", "state-transition-unknown", { type: transition.type || null });
    return null;
  },

  animationPlanFor(request) {
    if (request.type === "attach") {
      const child = nodeById(request.childId);
      const oldParentId = child?.parent || null;
      const movesOutward = Boolean(oldParentId && request.parentId && isDescendant(oldParentId, request.parentId));
      return {
        kind: movesOutward ? "meaning-release" : "meaning-enter",
        targetParentId: movesOutward ? oldParentId : request.parentId,
        reason: movesOutward ? "attach-to-ancestor" : "attach-to-parent",
      };
    }
    if (request.type === "detach") {
      const child = nodeById(request.childId);
      return {
        kind: "meaning-release",
        targetParentId: child?.parent || null,
        reason: "detach-to-root",
      };
    }
    if (request.type === "world-leave") {
      return {
        kind: "world-leave",
        targetParentId: request.nextParentId || null,
        reason: "leave-world",
      };
    }
    if (request.type === "world-enter") {
      return {
        kind: "world-enter",
        targetParentId: request.parent?.id || null,
        reason: "enter-world",
      };
    }
    return { kind: "none", targetParentId: null, reason: "unknown" };
  },

  attach({ explorer, childId, parentId, animationPlan, placement = "current", fromRect = null }) {
    const child = nodeById(childId);
    const parent = nodeById(parentId);
    logEvent("trace", "state-transition-attach-before", {
      childId,
      parentId,
      childParentBefore: child?.parent || null,
      placement,
      hasFromRect: Boolean(fromRect),
      animationPlan,
    });
    if (!child || !parent || childId === parentId || isDescendant(parentId, childId)) {
      logEvent("warn", "set-parent-rejected", { childId, parentId });
      logEvent("trace", "state-transition-attach-rejected", {
        childId,
        parentId,
        childExists: Boolean(child),
        parentExists: Boolean(parent),
        sameNode: childId === parentId,
        wouldCycle: Boolean(child && parent && isDescendant(parentId, childId)),
      });
      return null;
    }
    const animationFromRect = fromRect || visualRectForMeaning(childId);
    const oldParentId = child.parent || null;
    const currentLayout = { ...(child.layout || {}) };

    child.parent = parent.id;
    if (oldParentId) {
      const oldParent = nodeById(oldParentId);
      if (oldParent) {
        oldParent.children = explorer.childrenOf(oldParent).filter((node) => node.id !== child.id).map((node) => node.id);
        explorer.setHoldingCount(oldParent);
        explorer.syncParentCoordinates(oldParent.id, { force: true, reason: "set-parent-old-parent-pack" });
      }
    }
    parent.children = explorer.childrenOf(parent).map((node) => node.id);
    if (!parent.children.includes(child.id)) {
      parent.children.push(child.id);
    }
    explorer.setHoldingCount(parent);

    if (placement === "pack") {
      explorer.syncParentCoordinates(parent.id, { force: true, reason: "set-parent-pack" });
    } else if (placement === "screen" && animationFromRect) {
      explorer.syncChildCoordinatesFromNested(
        child.id,
        parent.id,
        explorer.nestedLayoutFromScreenRect(parent, child, animationFromRect),
        "set-parent-screen-layout",
      );
    } else {
      explorer.syncChildCoordinatesFromWorld(child.id, parent.id, currentLayout, "set-parent-current-layout");
    }
    const arrangedIds = explorer.arrangeParentChildren(parent, "set-parent-arrange-inside-world", {
      spacing: appSettings.arrangeWorldParentSpacing,
      worldSizeScale: appSettings.arrangeWorldParentSize,
      nestedSizeScale: appSettings.arrangeNestedChildSize,
    });
    explorer.touchPowans([parent.id, ...arrangedIds], "set-parent-arrange-touch");

    explorer.setChildEditParent(null, "set-parent-clear-child-edit");
    setDirty();
    render();
    requestAnimationFrame(() => {
      if (animationPlan.kind === "meaning-release") {
        animateMeaningRelease(childId, animationPlan.targetParentId || oldParentId, { fromRect: animationFromRect });
      } else if (animationPlan.kind === "meaning-enter") {
        animateMeaningEntering(childId, parentId, { fromRect: animationFromRect });
      }
    });
    logEvent("trace", "state-transition-attach-after", {
      childId,
      parentId,
      oldParentId,
      childParentAfter: child.parent || null,
      placement,
      parentChildCount: explorer.childrenOf(parent).length,
      arrangedCount: arrangedIds.length,
      animationPlan,
    });
    logEvent("debug", "set-parent", { childId, parentId, oldParentId, placement, arrangedCount: arrangedIds.length, animationPlan });
    return child;
  },

  detach({ explorer, childId, animationPlan, fromRect = null }) {
    const child = nodeById(childId);
    logEvent("trace", "state-transition-detach-before", {
      childId,
      childParentBefore: child?.parent || null,
      hasFromRect: Boolean(fromRect),
      animationPlan,
    });
    if (!child) {
      logEvent("warn", "explorer-detach-missing-node", { childId });
      logEvent("trace", "state-transition-detach-missing", { childId });
      return null;
    }
    if (!child.parent) {
      logEvent("debug", "explorer-detach-noop", { childId });
      logEvent("trace", "state-transition-detach-noop", { childId, childParentAfter: child.parent || null });
      return child;
    }
    const oldParentId = child.parent;
    const parent = nodeById(oldParentId);
    const animationFromRect = fromRect || visualRectForMeaning(child.id);

    child.parent = null;
    if (parent) {
      parent.children = explorer.childrenOf(parent).filter((node) => node.id !== child.id).map((node) => node.id);
      explorer.setHoldingCount(parent);
      explorer.syncParentCoordinates(parent.id, { force: true, reason: "detach-parent-pack" });
    }
    explorer.setHoldingCount(child);
    setDirty();
    render();
    requestAnimationFrame(() => {
      if (animationPlan.kind === "meaning-release") {
        animateMeaningRelease(child.id, oldParentId, { fromRect: animationFromRect });
      }
    });
    logEvent("trace", "state-transition-detach-after", {
      childId: child.id,
      oldParentId,
      childParentAfter: child.parent || null,
      oldParentChildCount: parent ? explorer.childrenOf(parent).length : null,
      hasFromRect: Boolean(animationFromRect),
      animationPlan,
    });
    logEvent("debug", "release-parent", { childId: child.id, oldParentId, hasFromRect: Boolean(animationFromRect), animationPlan });
    return child;
  },

  worldLeave({ explorer, parent, nextParentId }) {
    if (!parent) {
      return Promise.resolve(false);
    }
    const animation = powanWorldTransition.captureLeave(parent);
    powanWorldTransition.prepareLeave(animation);
    explorer.setWorld(nextParentId, "world-transition-leave-set-world");
    explorer.setChildEditParent(null, "world-transition-leave-clear-child-edit");
    if (nextParentId) {
      const nextParent = nodeById(nextParentId);
      if (nextParent) {
        enterMeaningInterior(nextParent);
      }
    } else {
      viewportBeforeInterior = null;
    }
    render();
    explorer.focusViewportOnNode(parent.id, "world-transition-leave-focus-parent");
    logEvent("debug", "world-path-leave-step", { parentId: parent.id, nextParentId });
    return powanWorldTransition.playLeave(animation, { parent });
  },

  worldEnter({ explorer, parent, sourceElement = null }) {
    if (!parent) {
      return Promise.resolve(false);
    }
    const animation = powanWorldTransition.captureEnter(parent, sourceElement);
    rememberViewportBeforeInterior();
    explorer.setChildEditParent(null, "world-transition-enter-clear-child-edit");
    explorer.setWorld(parent.id, "world-transition-enter-set-world");
    enterMeaningInterior(parent);
    explorer.setSelected(explorer.childrenOf(parent)[0]?.id || parent.id, "world-transition-enter-select");
    render();
    setViewportForInteriorWorld(parent);
    logEvent("debug", "world-path-enter-step", {
      parentId: parent.id,
      childCount: explorer.childrenOf(parent).length,
    });
    return powanWorldTransition.playEnter(animation, { parent });
  },
};
