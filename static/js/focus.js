var powanFocus = {
  visualSelector: ".node, .nested-meaning, .nested-preview-meaning",

  applySelected(nodeId) {
    getWorldLayer().querySelectorAll(this.visualSelector).forEach((element) => {
      this.markSelected(element, nodeId);
    });
  },

  markSelected(element, nodeId = selectedId) {
    element.classList.toggle("selected", isNodeSelected(element.dataset.id) || Boolean(nodeId && element.dataset.id === nodeId));
  },
};
