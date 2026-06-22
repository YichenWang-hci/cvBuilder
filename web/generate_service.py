"""JD → resume generation for local web UI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import generate as gen
from agent.format_rules import append_warnings_report
from agent.llm import get_provider
from figma_fill.runner import run_fill

ROOT = Path(__file__).resolve().parent.parent
APPLICATIONS_DIR = ROOT / "applications"


def list_recent_applications(limit: int = 8) -> list[dict[str, Any]]:
    if not APPLICATIONS_DIR.is_dir():
        return []
    dirs = sorted(
        [p for p in APPLICATIONS_DIR.iterdir() if p.is_dir()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    items: list[dict[str, Any]] = []
    for path in dirs[:limit]:
        items.append(
            {
                "folder": path.name,
                "has_figma": (path / "figma-fill-payload.json").is_file(),
                "has_resume": (path / "resume.json").is_file(),
            }
        )
    return items


def run_generation(
    jd: str,
    *,
    lang: str | None = None,
    fill_figma: bool = True,
    provider: str | None = None,
) -> dict[str, Any]:
    jd = jd.strip()
    if not jd:
        raise ValueError("Job description cannot be empty")

    knowledge = gen.load_knowledge()
    if not knowledge.get("profile", {}).get("name"):
        raise ValueError("Knowledge base incomplete: fill in your profile in the web UI first")

    prov = get_provider(provider)
    system_prompt = gen.build_system_prompt(knowledge)
    result = gen.call_llm(system_prompt, jd, lang or None, prov)
    warnings = gen.validate_result(result)
    result["match_report"] = append_warnings_report(
        result.get("match_report", ""), warnings
    )

    output_dir = gen.make_output_dir(gen.guess_output_name(result["resume"]))
    gen.write_output(output_dir, jd, result)

    figma_payload_str = ""
    if fill_figma:
        run_fill(output_dir / "resume.json", quiet=True)
        payload_path = output_dir / "figma-fill-payload.json"
        if payload_path.is_file():
            figma_payload_str = payload_path.read_text(encoding="utf-8")

    return {
        "output_dir": output_dir,
        "folder": output_dir.name,
        "lang": result["resume"]["meta"].get("output_language", "?"),
        "resume_text": gen.format_resume_text(result),
        "resume_json": json.dumps(result["resume"], ensure_ascii=False, indent=2),
        "figma_payload": figma_payload_str,
        "cover_letter": result.get("cover_letter", ""),
        "match_report": result.get("match_report", ""),
        "warnings": warnings,
    }
