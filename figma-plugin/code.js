figma.showUI(__html__, { width: 420, height: 320 });

figma.ui.onmessage = async (msg) => {
  if (msg.type !== "fill") return;

  const raw = String(msg.payloadText || "").trim();
  if (!raw) {
    figma.ui.postMessage({
      type: "result",
      ok: false,
      error:
        "Payload is empty. Copy the entire figma-fill-payload.json file into the text box, then click Fill resume again.",
    });
    return;
  }

  let payload;
  try {
    payload = JSON.parse(raw);
  } catch (error) {
    figma.ui.postMessage({
      type: "result",
      ok: false,
      error:
        "Invalid JSON: " +
        String(error) +
        "\n\nMake sure you pasted the complete figma-fill-payload.json (starts with { and ends with }).",
    });
    return;
  }

  if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
    figma.ui.postMessage({
      type: "result",
      ok: false,
      error: "Payload must be a JSON object { layerName: value }.",
    });
    return;
  }

  const templateFrameName = String(msg.templateFrameName || "").trim();
  const frameVisibility = msg.frameVisibility && typeof msg.frameVisibility === "object"
    ? msg.frameVisibility
    : {};

  function collectTextNodes(root) {
    const map = {};
    function walk(node) {
      if (node.type === "TEXT" && node.name) {
        map[node.name] = node;
      }
      if ("children" in node) {
        for (const child of node.children) walk(child);
      }
    }
    walk(root);
    return map;
  }

  function findFrameByName(root, name) {
    if (!name) return null;
    let found = null;
    function walk(node) {
      if (found) return;
      if (
        (node.type === "FRAME" ||
          node.type === "COMPONENT" ||
          node.type === "INSTANCE") &&
        node.name === name
      ) {
        found = node;
        return;
      }
      if ("children" in node) {
        for (const child of node.children) walk(child);
      }
    }
    walk(root);
    return found;
  }

  async function loadFontsForTextNode(node) {
    const segments = node.getStyledTextSegments(["fontName"]);
    const seen = new Set();
    for (const segment of segments) {
      if (segment.fontName === figma.mixed) continue;
      const key = JSON.stringify(segment.fontName);
      if (seen.has(key)) continue;
      seen.add(key);
      await figma.loadFontAsync(segment.fontName);
    }
  }

  try {
    const page = figma.currentPage;
    let scope = page;
    if (templateFrameName) {
      const frame = findFrameByName(page, templateFrameName);
      if (!frame) {
        figma.ui.postMessage({
          type: "result",
          ok: false,
          error: "Template frame not found: " + templateFrameName,
        });
        return;
      }
      scope = frame;
    }

    const textNodes = collectTextNodes(scope);
    const filled = [];
    const missing = [];

    for (const [layerName, value] of Object.entries(payload)) {
      const node = textNodes[layerName];
      if (!node) {
        missing.push(layerName);
        continue;
      }
      await loadFontsForTextNode(node);
      node.characters = String(value);
      filled.push(layerName);
    }

    for (const [frameName, visible] of Object.entries(frameVisibility)) {
      const frame = findFrameByName(scope, frameName);
      if (frame) {
        frame.visible = Boolean(visible);
      }
    }

    figma.ui.postMessage({
      type: "result",
      ok: true,
      filledCount: filled.length,
      missingCount: missing.length,
      missing,
      scope: scope.name,
    });
  } catch (error) {
    figma.ui.postMessage({
      type: "result",
      ok: false,
      error: String(error),
    });
  }
};
