from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MAP_PATH = ROOT / "templates" / "figma-template-map.yaml"


def load_template_map(path: Path | None = None) -> dict[str, Any]:
    map_path = path or DEFAULT_MAP_PATH
    with map_path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping in {map_path}")
    return data


def _item_at(items: list[dict[str, Any]], index: int) -> dict[str, Any]:
    if index < len(items):
        return items[index]
    return {}


def _find_language_item(
    items: list[dict[str, Any]], match_terms: list[str]
) -> dict[str, Any] | None:
    for item in items:
        name = str(item.get("name", "")).lower()
        if any(term.lower() in name for term in match_terms):
            return item
    return None


def build_fill_payload(resume: dict[str, Any], template_map: dict[str, Any]) -> dict[str, str]:
    """Return Figma Text layer name → string value."""
    sections = resume.get("sections", {})
    figma_cfg = template_map.get("figma", {})
    skip_layers = set(figma_cfg.get("skip_layers", []))
    payload: dict[str, str] = {}

    for layer, value in figma_cfg.get("static_values", {}).items():
        payload[str(layer)] = str(value)

    name_sec = sections.get("1_name", {})
    payload["1_name"] = str(name_sec.get("value", ""))

    summary_sec = sections.get("2_summary", {})
    payload["2_summary"] = str(summary_sec.get("value", ""))

    edu_cfg = template_map.get("education", {})
    edu_items = sections.get("3_education", {}).get("items", [])
    slots = int(edu_cfg.get("slots", 3))
    fields = edu_cfg.get("fields", {"uni": "school", "major": "degree", "period": "period"})
    for i in range(1, slots + 1):
        item = _item_at(edu_items, i - 1)
        for suffix, json_key in fields.items():
            payload[f"edu_{i}_{suffix}"] = str(item.get(json_key, ""))

    proj_cfg = template_map.get("projects", {})
    max_projects = int(proj_cfg.get("max", 3))
    max_bullets = int(proj_cfg.get("bullets_max", 3))
    proj_items = sections.get("4_projects", {}).get("items", [])
    for i in range(1, max_projects + 1):
        item = _item_at(proj_items, i - 1)
        payload[f"proj_{i}_title"] = str(item.get("title", ""))
        payload[f"proj_{i}_role"] = str(item.get("role", ""))
        payload[f"proj_{i}_period"] = str(item.get("period", ""))
        bullets = item.get("bullets", [])
        for b in range(1, max_bullets + 1):
            bullet = _item_at(bullets, b - 1)
            payload[f"proj_{i}_bullet_{b}"] = str(bullet.get("text", ""))

    contact = sections.get("5_contact", {})
    payload["contact_email"] = str(contact.get("email", ""))
    payload["contact_phone"] = str(contact.get("phone", ""))
    payload["contact_address"] = str(contact.get("address", ""))

    abilities_cfg = template_map.get("abilities", {})
    ability_items = sections.get("6_abilities", {}).get("items", [])
    for i in range(1, int(abilities_cfg.get("max", 6)) + 1):
        item = _item_at(ability_items, i - 1)
        payload[f"ability_{i}"] = str(item.get("name", ""))

    software_cfg = template_map.get("software", {})
    software_items = sections.get("7_software", {}).get("items", [])
    for i in range(1, int(software_cfg.get("max", 7)) + 1):
        item = _item_at(software_items, i - 1)
        payload[f"software_{i}"] = str(item.get("name", ""))

    lang_cfg = template_map.get("languages", {})
    lang_format = str(lang_cfg.get("format", "{name} {level}"))
    lang_items = sections.get("8_languages", {}).get("items", [])
    for layer_name, spec in lang_cfg.items():
        if layer_name == "format" or not isinstance(spec, dict):
            continue
        match_terms = [str(x) for x in spec.get("match", [])]
        item = _find_language_item(lang_items, match_terms)
        if item:
            payload[str(layer_name)] = lang_format.format(
                name=str(item.get("name", "")).strip(),
                level=str(item.get("level", "")).strip(),
            ).strip()
        else:
            payload[str(layer_name)] = ""

    for layer in skip_layers:
        payload.pop(str(layer), None)

    return payload


def project_block_visibility(payload: dict[str, str], template_map: dict[str, Any]) -> dict[str, bool]:
    """Return optional project block frame name → visible."""
    hide_cfg = template_map.get("hide_frames", {})
    block_names = hide_cfg.get("project_blocks", [])
    visibility: dict[str, bool] = {}
    for idx, frame_name in enumerate(block_names, start=1):
        has_content = any(
            payload.get(key, "").strip()
            for key in (
                f"proj_{idx}_title",
                f"proj_{idx}_role",
                f"proj_{idx}_period",
                f"proj_{idx}_bullet_1",
                f"proj_{idx}_bullet_2",
                f"proj_{idx}_bullet_3",
            )
        )
        visibility[str(frame_name)] = has_content
    return visibility
