"""Figma template layer naming list from knowledge + template map."""

from __future__ import annotations

from typing import Any

from figma_fill.map_layers import build_fill_payload, load_template_map

from web.knowledge_store import build_preview_resume


def list_figma_layers() -> list[dict[str, Any]]:
    template_map = load_template_map()
    resume = build_preview_resume()
    payload = build_fill_payload(resume, template_map)

    figma_cfg = template_map.get("figma", {})
    skip_layers = set(figma_cfg.get("skip_layers", []))

    layers: list[dict[str, Any]] = []

    def add(
        name: str,
        group: str,
        *,
        fillable: bool = True,
        hint: str = "",
    ) -> None:
        preview = payload.get(name, "")
        layers.append(
            {
                "name": name,
                "group": group,
                "fillable": fillable,
                "hint": hint,
                "preview": preview,
                "has_data": bool(str(preview).strip()),
            }
        )

    for name in figma_cfg.get("static_values", {}):
        add(name, "Decorations", hint="Fixed symbols like @ — not from knowledge base")

    add("1_name", "§1 Name")
    add("2_summary", "§2 Summary")

    edu_slots = int(template_map.get("education", {}).get("slots", 3))
    edu_fields = template_map.get("education", {}).get(
        "fields", {"uni": "school", "major": "degree", "period": "period"}
    )
    field_hints = {"uni": "School", "major": "Degree", "period": "Period", "symbol": "Decoration"}
    for i in range(1, edu_slots + 1):
        for suffix in edu_fields:
            add(
                f"edu_{i}_{suffix}",
                f"§3 Education #{i}",
                hint=field_hints.get(suffix, suffix),
            )

    max_proj = int(template_map.get("projects", {}).get("max", 3))
    max_bullets = int(template_map.get("projects", {}).get("bullets_max", 3))
    for i in range(1, max_proj + 1):
        add(f"proj_{i}_title", f"§4 Experience #{i}", hint="Title (project or company name)")
        add(f"proj_{i}_role", f"§4 Experience #{i}", hint="Role or job title")
        add(f"proj_{i}_period", f"§4 Experience #{i}", hint="Period")
        for b in range(1, max_bullets + 1):
            add(f"proj_{i}_bullet_{b}", f"§4 Experience #{i}", hint=f"Bullet {b}")

    add("contact_email", "§5 Contact", hint="Email")
    add("contact_phone", "§5 Contact", hint="Phone (DIN 5008)")
    add("contact_address", "§5 Contact", hint="Address")

    max_ab = int(template_map.get("abilities", {}).get("max", 6))
    for i in range(1, max_ab + 1):
        add(f"ability_{i}", "§6 Abilities", hint=f"Ability {i}")

    max_sw = int(template_map.get("software", {}).get("max", 7))
    for i in range(1, max_sw + 1):
        add(f"software_{i}", "§7 Software", hint=f"Software {i}")

    lang_cfg = template_map.get("languages", {})
    for layer_name, spec in lang_cfg.items():
        if layer_name == "format" or not isinstance(spec, dict):
            continue
        terms = ", ".join(spec.get("match", []))
        add(f"{layer_name}", "§8 Languages", hint=f"Match: {terms}")

    for name in skip_layers:
        add(str(name), "Section headings (design)", fillable=False, hint="Plugin skips — keeps template text")

    hide_frames = template_map.get("hide_frames", {}).get("project_blocks", [])
    for frame in hide_frames:
        add(
            str(frame),
            "Optional frames",
            fillable=False,
            hint="Hide when empty (if this frame exists in template)",
        )

    return layers


def layers_grouped() -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for layer in list_figma_layers():
        grouped.setdefault(layer["group"], []).append(layer)
    return grouped
