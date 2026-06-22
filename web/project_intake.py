"""Narrative project intake via LLM."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from agent.format_rules import load_data_format, normalize_period
from agent.llm import call_llm, get_provider

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "agent" / "prompts"


def build_system_prompt() -> str:
    intake_md = (PROMPTS_DIR / "intake_project.md").read_text(encoding="utf-8")
    data_format = load_data_format()
    return f"""You are cvBuilder project intake assistant.

{intake_md}

---

{data_format}

Return ONLY one JSON object. No markdown fences.
"""


def extract_project(narrative: str, provider: str | None = None) -> dict[str, Any]:
    if not narrative.strip():
        raise ValueError("Description is empty")
    result = call_llm(
        build_system_prompt(),
        f"User narrative (any language):\n\n{narrative.strip()}",
        get_provider(provider),
    )
    if "project" not in result or not isinstance(result.get("project"), dict):
        raise ValueError("LLM did not return a valid project object")
    project = ensure_project_shape(result["project"])
    period, _ = normalize_period(str(project.get("period", "")))
    project["period"] = period
    result["project"] = project
    return result


def ensure_project_shape(raw: dict[str, Any]) -> dict[str, Any]:
    pid = str(raw.get("id", "")).strip()
    project: dict[str, Any] = {
        "id": pid,
        "title": _bilingual(raw.get("title")),
        "role": _bilingual(raw.get("role")),
        "period": str(raw.get("period", "")).strip(),
        "type": _bilingual(raw.get("type")),
        "tech_stack": _str_list(raw.get("tech_stack")),
        "keywords": _str_list(raw.get("keywords")),
        "target_roles": _str_list(raw.get("target_roles")),
        "bullets": _normalize_bullets(raw.get("bullets")),
        "links": {
            "github": (raw.get("links") or {}).get("github"),
            "demo": (raw.get("links") or {}).get("demo"),
            "paper": (raw.get("links") or {}).get("paper"),
        },
        "story_hooks": _story_hooks(raw.get("story_hooks")),
    }
    return project


def _bilingual(val: Any) -> dict[str, str]:
    if isinstance(val, dict):
        return {"de": str(val.get("de", "")).strip(), "en": str(val.get("en", "")).strip()}
    if isinstance(val, str) and val.strip():
        return {"de": val.strip(), "en": val.strip()}
    return {"de": "", "en": ""}


def _str_list(val: Any) -> list[str]:
    if not isinstance(val, list):
        return []
    return [str(x).strip() for x in val if str(x).strip()]


def _normalize_bullets(val: Any) -> list[dict[str, Any]]:
    bullets: list[dict[str, Any]] = []
    if not isinstance(val, list):
        return bullets
    for i, b in enumerate(val[:3], start=1):
        if not isinstance(b, dict):
            continue
        bullets.append(
            {
                "id": str(b.get("id") or f"b{i}").strip(),
                "text": _bilingual(b.get("text")),
                "tags": _str_list(b.get("tags")),
                "metric": b.get("metric"),
            }
        )
    return bullets


def _story_hooks(val: Any) -> dict[str, dict[str, str]]:
    keys = ("problem", "constraint", "decision", "outcome", "lesson")
    hooks: dict[str, dict[str, str]] = {}
    src = val if isinstance(val, dict) else {}
    for key in keys:
        hooks[key] = _bilingual(src.get(key))
    return hooks
