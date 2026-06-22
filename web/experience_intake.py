"""Narrative work/internship intake via LLM."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from agent.format_rules import load_data_format, normalize_period
from agent.llm import call_llm, get_provider
from web.project_intake import (
    _bilingual,
    _normalize_bullets,
    _str_list,
)

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "agent" / "prompts"


def build_system_prompt() -> str:
    intake_md = (PROMPTS_DIR / "intake_experience.md").read_text(encoding="utf-8")
    data_format = load_data_format()
    return f"""You are cvBuilder work/internship intake assistant.

{intake_md}

---

{data_format}

Return ONLY one JSON object. No markdown fences.
"""


def extract_experience(narrative: str, provider: str | None = None) -> dict[str, Any]:
    if not narrative.strip():
        raise ValueError("Description is empty")
    result = call_llm(
        build_system_prompt(),
        f"User narrative (any language):\n\n{narrative.strip()}",
        get_provider(provider),
    )
    if "experience" not in result or not isinstance(result.get("experience"), dict):
        raise ValueError("LLM did not return a valid experience object")
    experience = ensure_experience_shape(result["experience"])
    period, _ = normalize_period(str(experience.get("period", "")))
    experience["period"] = period
    result["experience"] = experience
    return result


def ensure_experience_shape(raw: dict[str, Any]) -> dict[str, Any]:
    kind = str(raw.get("kind", "internship")).strip().lower()
    if kind not in ("internship", "work"):
        kind = "internship"
    return {
        "id": str(raw.get("id", "")).strip(),
        "kind": kind,
        "company": str(raw.get("company", "")).strip(),
        "title": _bilingual(raw.get("title")),
        "role": _bilingual(raw.get("role")),
        "period": str(raw.get("period", "")).strip(),
        "type": _bilingual(raw.get("type")),
        "location": str(raw.get("location", "")).strip(),
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


def _story_hooks(val: Any) -> dict[str, dict[str, str]]:
    keys = ("problem", "constraint", "decision", "outcome", "lesson")
    src = val if isinstance(val, dict) else {}
    return {key: _bilingual(src.get(key)) for key in keys}


def _empty_story_hooks() -> dict[str, dict[str, str]]:
    blank = {"de": "", "en": ""}
    return {k: dict(blank) for k in ("problem", "constraint", "decision", "outcome", "lesson")}
