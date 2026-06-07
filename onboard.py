#!/usr/bin/env python3
"""cvBuilder P0 — guided intake for fixed profile info → knowledge/profile.yaml."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

import yaml

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from agent.format_rules import (
    append_warnings_report,
    check_profile_warnings,
    load_data_format,
    normalize_profile_periods,
    print_warnings,
)
from agent.llm import call_llm, get_provider

ROOT = Path(__file__).resolve().parent
KNOWLEDGE_DIR = ROOT / "knowledge"
KNOWLEDGE_EXAMPLE_DIR = ROOT / "knowledge.example"
PROFILE_PATH = KNOWLEDGE_DIR / "profile.yaml"
PROMPTS_DIR = ROOT / "agent" / "prompts"

PROFILE_HEADER = """# =============================================================================
# cvBuilder profile — built with onboard.py
# Bilingual storage (de/en). Edit here or re-run: python onboard.py --force
# =============================================================================

"""


def load_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, dict) else {}


def init_knowledge(force: bool = False) -> None:
    if KNOWLEDGE_DIR.exists() and any(KNOWLEDGE_DIR.iterdir()) and not force:
        raise SystemExit(
            f"{KNOWLEDGE_DIR}/ already exists.\n"
            "Use --force to overwrite from knowledge.example/, or run without --init."
        )
    if not KNOWLEDGE_EXAMPLE_DIR.is_dir():
        raise SystemExit(f"Missing template directory: {KNOWLEDGE_EXAMPLE_DIR}")

    if KNOWLEDGE_DIR.exists() and force:
        shutil.rmtree(KNOWLEDGE_DIR)

    shutil.copytree(KNOWLEDGE_EXAMPLE_DIR, KNOWLEDGE_DIR)
    print(f"Initialized {KNOWLEDGE_DIR}/ from knowledge.example/")


def prompt_line(label: str, required: bool = True) -> str:
    hint = " (required)" if required else " (optional, Enter to skip)"
    print(f"\n{label}{hint}", file=sys.stderr)
    try:
        value = input("> ").strip()
    except (EOFError, KeyboardInterrupt):
        raise SystemExit("\nCancelled.") from None
    if required and not value:
        print("  This field is required.", file=sys.stderr)
        return prompt_line(label, required)
    return value


def prompt_multiline(label: str) -> str:
    print(f"\n{label}", file=sys.stderr)
    print("  Paste below. Finish with Ctrl+D or a line containing only END.", file=sys.stderr)
    lines: list[str] = []
    try:
        for line in sys.stdin:
            if line.strip() == "END":
                break
            lines.append(line)
    except KeyboardInterrupt:
        raise SystemExit("\nCancelled.") from None
    return "".join(lines).strip()


def collect_step_by_step() -> str:
    print("\n=== cvBuilder profile setup ===", file=sys.stderr)
    print("Answer in ANY language. We'll store de + en for you.\n", file=sys.stderr)

    parts: list[str] = []

    parts.append(f"Full name: {prompt_line('1) Full name / 姓名')}")
    parts.append(f"Email: {prompt_line('2) Email / 邮箱')}")
    parts.append(
        f"Phone: {prompt_line('3) Phone / 电话 (DIN 5008: +49 152 06820364)')}"
    )
    parts.append(f"Address: {prompt_line('4) Address / 地址')}")
    parts.append(
        f"Languages: {prompt_line('5) Languages & levels / 语言能力 (e.g. Chinese native, German C1, English B2)')}"
    )

    education_blocks: list[str] = []
    index = 1
    while True:
        print(f"\n--- Education entry {index} ---", file=sys.stderr)
        school = prompt_line(f"6.{index}a) School / 学校", required=False)
        if not school:
            break
        degree = prompt_line(f"6.{index}b) Degree / 专业学位")
        period = prompt_line(
            f"6.{index}c) Period / 起止时间 (German: 01.04.2025 - heute or 04.2025 - 07.2025)"
        )
        education_blocks.append(
            f"Education {index}: school={school}; degree={degree}; period={period}"
        )
        index += 1

    if not education_blocks:
        print("  No education entered — you can add later in profile.yaml.", file=sys.stderr)
    parts.extend(education_blocks)

    parts.append(
        f"Internship goal: {prompt_line('7) Internship availability / 实习意向 (start date, duration, location)', required=False)}"
    )

    return "\n".join(parts)


def collect_paste_mode() -> str:
    print("\n=== cvBuilder profile setup (paste mode) ===", file=sys.stderr)
    print(
        "Paste ALL fixed info in one block (any language):\n"
        "  name, contact, languages, education, internship availability\n",
        file=sys.stderr,
    )
    text = prompt_multiline("Paste your info:")
    if not text:
        raise SystemExit("No input provided.")
    return text


def build_system_prompt() -> str:
    onboard_md = (PROMPTS_DIR / "onboard.md").read_text(encoding="utf-8")
    data_format = load_data_format()
    return f"""You are cvBuilder onboarding assistant.

{onboard_md}

---

{data_format}

Return ONLY one JSON object. No markdown fences. No text before or after JSON.
"""


def build_user_message(raw_intake: str, existing_profile: dict | None) -> str:
    msg = f"User intake (any language):\n\n{raw_intake}"
    if existing_profile:
        msg += (
            "\n\nExisting profile.yaml summaries to PRESERVE (copy into output unchanged):\n"
            + json.dumps(existing_profile.get("summaries", []), ensure_ascii=False, indent=2)
        )
        msg += (
            "\n\nReplace fixed sections (name, contact, languages, education, "
            "application_context) from new intake. Keep summaries from existing unless "
            "intake explicitly provides new summary text."
        )
    return msg


def ensure_profile_shape(profile: dict) -> dict:
    """Guarantee minimal structure so the file is always writable."""
    profile.setdefault("name", "")
    profile.setdefault("contact", {})
    contact = profile["contact"]
    for key in ("email", "phone", "address"):
        contact.setdefault(key, "")
    profile.setdefault("languages", [])
    profile.setdefault("summaries", [])
    profile.setdefault("education", [])
    profile.setdefault(
        "application_context",
        {
            "goal": "full-time-intern",
            "earliest_start": "",
            "duration": "",
            "days_per_week": 5,
            "note": {"de": "", "en": ""},
        },
    )
    return profile


def merge_summaries(new_profile: dict, existing_profile: dict | None, keep_summaries: bool) -> None:
    if not keep_summaries or not existing_profile:
        return
    existing = existing_profile.get("summaries")
    if existing:
        new_profile["summaries"] = existing


def write_profile(profile: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        f.write(PROFILE_HEADER)
        yaml.dump(
            profile,
            f,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
            width=88,
        )


def preview_result(result: dict) -> None:
    profile = result["profile"]
    print("\n" + "=" * 60)
    print("PREVIEW — profile.yaml")
    print("=" * 60)
    print(f"Name:    {profile.get('name')}")
    contact = profile.get("contact", {})
    print(f"Email:   {contact.get('email')}")
    print(f"Phone:   {contact.get('phone')}")
    print(f"Address: {contact.get('address')}")
    print("\nLanguages:")
    for lang in profile.get("languages", []):
        print(f"  - {lang.get('name', {}).get('en')} ({lang.get('level', {}).get('en')})")
    print("\nEducation:")
    for edu in profile.get("education", []):
        print(f"  - {edu.get('school')} | {edu.get('degree', {}).get('en')} | {edu.get('period')}")
    print("\n" + "=" * 60)
    print("INTAKE REPORT")
    print("=" * 60)
    print(result.get("intake_report", "").strip())
    print()


def confirm_write() -> bool:
    try:
        answer = input("Save to knowledge/profile.yaml? [y/N] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return False
    return answer in ("y", "yes")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build knowledge/profile.yaml from guided personal info intake (P0)."
    )
    parser.add_argument(
        "--init",
        action="store_true",
        help="Copy knowledge.example/ → knowledge/ (empty personal data template)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="With --init: overwrite existing knowledge/. With save: skip profile-exists guard.",
    )
    parser.add_argument(
        "--paste",
        action="store_true",
        help="Paste all info in one block instead of step-by-step questions",
    )
    parser.add_argument(
        "--keep-summaries",
        action="store_true",
        help="When updating, keep existing summaries from profile.yaml",
    )
    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Save without confirmation prompt",
    )
    parser.add_argument(
        "--provider",
        choices=("gemini", "ollama", "openai"),
        help="LLM backend (default: LLM_PROVIDER in .env)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show questions / intake only, do not call LLM",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.init:
        init_knowledge(force=args.force)
        if not args.paste and sys.stdin.isatty():
            print("\nNext: python onboard.py", file=sys.stderr)
        return

    if not KNOWLEDGE_DIR.is_dir():
        raise SystemExit(
            "knowledge/ not found. Run first:\n  python onboard.py --init"
        )

    if PROFILE_PATH.is_file() and not args.force and not args.keep_summaries:
        print(
            f"Note: {PROFILE_PATH} already exists. Saving will overwrite it.\n"
            "Use --keep-summaries to preserve existing summaries, or --force to skip this note.",
            file=sys.stderr,
        )

    if args.paste or not sys.stdin.isatty():
        if sys.stdin.isatty():
            raw_intake = collect_paste_mode()
        else:
            raw_intake = sys.stdin.read().strip()
            if not raw_intake:
                raise SystemExit("No input provided on stdin.")
    else:
        raw_intake = collect_step_by_step()

    if args.dry_run:
        print("\n--- Dry run: intake text ---\n")
        print(raw_intake)
        print("\nDry run complete. Re-run without --dry-run to call LLM.")
        return

    existing_profile = load_yaml(PROFILE_PATH) if PROFILE_PATH.is_file() else None
    provider = get_provider(args.provider)

    print(f"\nStructuring profile via {provider} (may take 15-40 seconds)...", file=sys.stderr)
    result = call_llm(build_system_prompt(), build_user_message(raw_intake, existing_profile), provider)

    if "profile" not in result or not isinstance(result.get("profile"), dict):
        raise SystemExit("LLM response missing usable 'profile' object — cannot continue.")

    profile = ensure_profile_shape(result["profile"])
    merge_summaries(profile, existing_profile, args.keep_summaries)

    warnings: list[str] = []
    warnings.extend(normalize_profile_periods(profile))
    warnings.extend(check_profile_warnings(profile))

    preview_result(result)
    print_warnings(warnings, "Format / missing field warnings")

    if not args.yes and not confirm_write():
        print("Discarded. No files written.", file=sys.stderr)
        return

    write_profile(profile, PROFILE_PATH)
    report_path = KNOWLEDGE_DIR / "onboard_report.md"
    report_text = append_warnings_report(result.get("intake_report", ""), warnings)
    report_path.write_text(report_text, encoding="utf-8")

    print(f"Saved: {PROFILE_PATH}", file=sys.stderr)
    print(f"Saved: {report_path}", file=sys.stderr)
    print("\nNext steps:", file=sys.stderr)
    print("  • Add projects: coming in P1 (add_experience.py)", file=sys.stderr)
    print("  • Generate resume: python generate.py", file=sys.stderr)


if __name__ == "__main__":
    main()
