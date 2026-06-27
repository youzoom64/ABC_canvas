var powanFocus = {
  visualSelector: ".node, .nested-meaning, .nested-preview-meaning",

  selectionContextIds(nodeId = selectedId) {
    const selected = typeof selectedNodeIds === "function"
      ? selectedNodeIds()
      : (nodeId ? [nodeId] : []);
    const selectedSet = new Set(selected.filter(Boolean));
    const context = new Set(selectedSet);
    const nodes = Array.isArray(doc?.nodes)
      ? doc.nodes.filter((node) => !(typeof isArchivedNode === "function" && isArchivedNode(node)))
      : [];
    const byId = new Map(nodes.map((node) => [node.id, node]));
    const childrenByParent = new Map();
    for (const node of nodes) {
      if (!node.parent) {
        continue;
      }
      const children = childrenByParent.get(node.parent) || [];
      children.push(node.id);
      childrenByParent.set(node.parent, children);
    }
    const addAncestors = (id) => {
      let current = byId.get(id);
      while (current?.parent && byId.has(current.parent)) {
        context.add(current.parent);
        current = byId.get(current.parent);
      }
    };
    const addDescendants = (id) => {
      const stack = [...(childrenByParent.get(id) || [])];
      while (stack.length) {
        const childId = stack.pop();
        if (!childId || context.has(childId)) {
          continue;
        }
        context.add(childId);
        stack.push(...(childrenByParent.get(childId) || []));
      }
    };
    for (const id of selectedSet) {
      addAncestors(id);
      addDescendants(id);
    }
    return context;
  },

  applySelected(nodeId) {
    const hasSelection = typeof selectedNodeIds === "function"
      ? selectedNodeIds().length > 0
      : Boolean(nodeId);
    const contextIds = this.selectionContextIds(nodeId);
    canvas?.classList?.toggle("has-selection", hasSelection);
    getWorldLayer().querySelectorAll(this.visualSelector).forEach((element) => {
      this.markSelected(element, nodeId);
      element.classList.toggle("selected-context", contextIds.has(element.dataset.id));
    });
  },

  markSelected(element, nodeId = selectedId) {
    element.classList.toggle("selected", isNodeSelected(element.dataset.id) || Boolean(nodeId && element.dataset.id === nodeId));
  },
};
