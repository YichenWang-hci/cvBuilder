from __future__ import annotations

from typing import Any

import httpx


def _walk_nodes(node: dict[str, Any], text_names: set[str], frame_names: set[str]) -> None:
    node_type = node.get("type")
    name = node.get("name", "")
    if node_type == "TEXT" and name:
        text_names.add(name)
    if node_type in ("FRAME", "COMPONENT", "INSTANCE", "GROUP") and name:
        frame_names.add(name)
    for child in node.get("children", []) or []:
        _walk_nodes(child, text_names, frame_names)


def fetch_document_layers(file_key: str, token: str) -> tuple[set[str], set[str]]:
    """Return (text_layer_names, frame_layer_names) from Figma REST API."""
    url = f"https://api.figma.com/v1/files/{file_key}"
    headers = {"X-Figma-Token": token}
    try:
        response = httpx.get(url, headers=headers, timeout=60.0)
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        body = exc.response.text[:400]
        raise SystemExit(
            f"Figma API error ({exc.response.status_code}): {body}\n"
            "Check FIGMA_FILE_KEY and FIGMA_ACCESS_TOKEN in .env"
        ) from None
    except httpx.RequestError as exc:
        raise SystemExit(f"Could not reach Figma API: {exc}") from None

    data = response.json()
    text_names: set[str] = set()
    frame_names: set[str] = set()
    document = data.get("document", {})
    for page in document.get("children", []) or []:
        _walk_nodes(page, text_names, frame_names)
    return text_names, frame_names


def validate_payload_against_file(
    payload: dict[str, str],
    file_key: str,
    token: str,
    *,
    optional_frames: list[str] | None = None,
) -> dict[str, list[str]]:
    text_names, frame_names = fetch_document_layers(file_key, token)
    optional = set(optional_frames or [])
    missing = sorted(name for name in payload if name not in text_names)
    extra_candidates = sorted(text_names - set(payload.keys()) - optional)
    frames_found = sorted(name for name in optional if name in frame_names)
    return {
        "missing_text_layers": missing,
        "unmapped_text_layers_in_file": extra_candidates,
        "optional_frames_found": frames_found,
    }
