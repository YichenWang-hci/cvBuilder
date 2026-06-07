from __future__ import annotations

import json


def generate_plugin_script(
    payload: dict[str, str],
    *,
    template_frame: str = "",
    frame_visibility: dict[str, bool] | None = None,
) -> str:
    """Generate Figma Plugin API JavaScript (for use_figma or cvBuilder plugin)."""
    payload_json = json.dumps(payload, ensure_ascii=False)
    frame_visibility_json = json.dumps(frame_visibility or {}, ensure_ascii=False)
    template_frame_json = json.dumps(template_frame, ensure_ascii=False)

    return f"""const payload = {payload_json};
const frameVisibility = {frame_visibility_json};
const templateFrameName = {template_frame_json};

function collectTextNodes(root) {{
  const map = {{}};
  function walk(node) {{
    if (node.type === "TEXT" && node.name) {{
      map[node.name] = node;
    }}
    if ("children" in node) {{
      for (const child of node.children) walk(child);
    }}
  }}
  walk(root);
  return map;
}}

function findFrameByName(root, name) {{
  if (!name) return null;
  let found = null;
  function walk(node) {{
    if (found) return;
    if (
      (node.type === "FRAME" || node.type === "COMPONENT" || node.type === "INSTANCE") &&
      node.name === name
    ) {{
      found = node;
      return;
    }}
    if ("children" in node) {{
      for (const child of node.children) walk(child);
    }}
  }}
  walk(root);
  return found;
}}

async function loadFontsForTextNode(node) {{
  const segments = node.getStyledTextSegments(["fontName"]);
  const seen = new Set();
  for (const segment of segments) {{
    if (segment.fontName === figma.mixed) continue;
    const key = JSON.stringify(segment.fontName);
    if (seen.has(key)) continue;
    seen.add(key);
    await figma.loadFontAsync(segment.fontName);
  }}
}}

const page = figma.currentPage;
let scope = page;
if (templateFrameName) {{
  const frame = findFrameByName(page, templateFrameName);
  if (!frame) {{
    return {{
      ok: false,
      error: `Template frame not found: ${{templateFrameName}}`,
    }};
  }}
  scope = frame;
}}

const textNodes = collectTextNodes(scope);
const filled = [];
const missing = [];

for (const [layerName, value] of Object.entries(payload)) {{
  const node = textNodes[layerName];
  if (!node) {{
    missing.push(layerName);
    continue;
  }}
  await loadFontsForTextNode(node);
  node.characters = value;
  filled.push(layerName);
}}

for (const [frameName, visible] of Object.entries(frameVisibility)) {{
  const frame = findFrameByName(scope, frameName);
  if (frame) {{
    frame.visible = visible;
  }}
}}

return {{
  ok: true,
  filled,
  missing,
  scope: scope.name,
}};
"""
