var powanAttachments = {
  imagePreviewMax: 360,

  extension(name) {
    const match = String(name || "").toLowerCase().match(/\.([a-z0-9]+)$/);
    return match ? match[1] : "";
  },

  fileKind(file) {
    const mime = String(file?.type || "").toLowerCase();
    const ext = this.extension(file?.name);
    if (mime.startsWith("image/")) {
      return "image";
    }
    if (mime.startsWith("video/") || ["mp4", "mov", "webm", "mkv", "avi"].includes(ext)) {
      return "video";
    }
    if (["html", "htm"].includes(ext) || mime.includes("html")) {
      return "html";
    }
    if (["py", "pyw"].includes(ext)) {
      return "python";
    }
    if (ext === "json" || mime.includes("json")) {
      return "json";
    }
    if (ext === "csv" || mime.includes("csv")) {
      return "csv";
    }
    if (["js", "ts", "tsx", "jsx", "css", "md", "txt", "ps1", "sh", "yaml", "yml"].includes(ext)) {
      return "code";
    }
    return "file";
  },

  fileLabel(kind) {
    return {
      image: "IMG",
      video: "VID",
      html: "HTML",
      python: "PY",
      json: "JSON",
      csv: "CSV",
      code: "CODE",
      youtube: "YT",
      x: "X",
      url: "URL",
      file: "FILE",
    }[kind] || "FILE";
  },

  async fileToAttachment(file) {
    const kind = this.fileKind(file);
    const attachment = {
      kind,
      source: "file",
      name: file.name || "file",
      mime: file.type || "",
      size: Number(file.size || 0),
      path: this.filePath(file),
      relativePath: String(file.webkitRelativePath || ""),
    };
    if (kind === "image") {
      attachment.previewUrl = await this.imageFilePreview(file);
    }
    return attachment;
  },

  async clipboardFileToAttachment(file) {
    const attachment = await this.fileToAttachment(file);
    attachment.source = "clipboard";
    attachment.name = attachment.name || `clipboard-${Date.now()}.png`;
    attachment.path = "";
    return attachment;
  },

  filePath(file) {
    const path = file && typeof file.path === "string" ? file.path : "";
    return path.trim();
  },

  imageFilePreview(file) {
    return new Promise((resolve) => {
      const objectUrl = URL.createObjectURL(file);
      const image = new Image();
      image.onload = () => {
        const scale = Math.min(1, this.imagePreviewMax / Math.max(image.naturalWidth || 1, image.naturalHeight || 1));
        const width = Math.max(1, Math.round((image.naturalWidth || 1) * scale));
        const height = Math.max(1, Math.round((image.naturalHeight || 1) * scale));
        const canvasElement = document.createElement("canvas");
        canvasElement.width = width;
        canvasElement.height = height;
        canvasElement.getContext("2d").drawImage(image, 0, 0, width, height);
        URL.revokeObjectURL(objectUrl);
        resolve(canvasElement.toDataURL("image/png"));
      };
      image.onerror = () => {
        URL.revokeObjectURL(objectUrl);
        resolve("");
      };
      image.src = objectUrl;
    });
  },

  urlToAttachment(urlText) {
    const url = this.cleanUrl(urlText);
    if (!url) {
      return null;
    }
    const parsed = new URL(url);
    if (parsed.protocol === "file:") {
      return {
        kind: "file",
        source: "url",
        name: decodeURIComponent(parsed.pathname.split(/[\\/]/).filter(Boolean).pop() || "file"),
        url,
        path: this.fileUrlPath(parsed),
      };
    }
    const youtubeId = this.youtubeId(parsed);
    if (youtubeId) {
      return {
        kind: "youtube",
        source: "url",
        name: parsed.hostname,
        url,
        host: parsed.hostname,
        previewUrl: `https://img.youtube.com/vi/${youtubeId}/hqdefault.jpg`,
      };
    }
    if (this.isXUrl(parsed)) {
      return {
        kind: "x",
        source: "url",
        name: parsed.hostname,
        url,
        host: parsed.hostname,
      };
    }
    return {
      kind: "url",
      source: "url",
      name: parsed.hostname,
      url,
      host: parsed.hostname,
    };
  },

  fileUrlPath(parsed) {
    const decoded = decodeURIComponent(parsed.pathname || "");
    if (/^\/[a-zA-Z]:\//.test(decoded)) {
      return decoded.slice(1).replace(/\//g, "\\");
    }
    return decoded;
  },

  cleanUrl(text) {
    const raw = String(text || "").trim();
    if (!raw) {
      return "";
    }
    const first = raw.split(/\s+/).find((part) => /^https?:\/\//i.test(part));
    if (!first) {
      return "";
    }
    try {
      return new URL(first).href;
    } catch (_error) {
      return "";
    }
  },

  youtubeId(parsed) {
    const host = parsed.hostname.replace(/^www\./, "");
    if (host === "youtu.be") {
      return parsed.pathname.split("/").filter(Boolean)[0] || "";
    }
    if (host === "youtube.com" || host === "m.youtube.com") {
      return parsed.searchParams.get("v") || "";
    }
    return "";
  },

  isXUrl(parsed) {
    const host = parsed.hostname.replace(/^www\./, "");
    return host === "x.com" || host === "twitter.com";
  },

  titleForAttachment(attachment) {
    if (!attachment) {
      return "";
    }
    if (attachment.source === "url") {
      return attachment.host || attachment.name || "URL";
    }
    return attachment.name || this.fileLabel(attachment.kind);
  },

  createView(node, { mode = "world" } = {}) {
    const attachment = node?.attachment;
    if (!attachment) {
      return null;
    }
    const view = document.createElement("div");
    view.className = `powan-attachment powan-attachment-${attachment.kind || "file"}`;
    view.classList.toggle("powan-attachment-url", attachment.source === "url");
    view.title = attachment.url || attachment.name || "";
    if (attachment.kind === "image" && attachment.previewUrl) {
      const image = document.createElement("img");
      image.alt = attachment.name || "image";
      image.src = attachment.previewUrl;
      view.append(image);
      return view;
    }
    if (attachment.previewUrl) {
      const image = document.createElement("img");
      image.alt = attachment.name || "preview";
      image.src = attachment.previewUrl;
      view.append(image);
    }
    const badge = document.createElement("span");
    badge.className = "powan-attachment-badge";
    badge.textContent = this.fileLabel(attachment.kind);
    view.append(badge);
    if (mode === "world" && attachment.source === "url") {
      const host = document.createElement("span");
      host.className = "powan-attachment-host";
      host.textContent = attachment.host || attachment.name || "URL";
      view.append(host);
    }
    return view;
  },
};
