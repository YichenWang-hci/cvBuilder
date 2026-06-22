#!/usr/bin/env python3
"""cvBuilder MVP — paste a JD, get a tailored resume."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

import yaml

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from agent.format_rules import append_warnings_report, load_data_format, print_warnings, repair_generate_result
from agent.llm import call_llm as llm_call, get_provider as llm_get_provider

ROOT = Path(__file__).resolve().parent
KNOWLEDGE_DIR = ROOT / "knowledge"
EXPERIENCES_DIR = KNOWLEDGE_DIR / "experiences"
PROJECTS_DIR = KNOWLEDGE_DIR / "projects"
PROMPTS_DIR = ROOT / "agent" / "prompts"
TEMPLATES_DIR = ROOT / "templates"
APPLICATIONS_DIR = ROOT / "applications"


def load_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping in {path}")
    return data


def load_knowledge() -> dict:
    projects = []
    for path in sorted(PROJECTS_DIR.glob("*.yaml")):
        if path.name.startswith("_"):
            continue
        projects.append({"_file": path.name, **load_yaml(path)})

    experiences = []
    if EXPERIENCES_DIR.is_dir():
        for path in sorted(EXPERIENCES_DIR.glob("*.yaml")):
            if path.name.startswith("_"):
                continue
            experiences.append({"_file": path.name, **load_yaml(path)})

    return {
        "profile": load_yaml(KNOWLEDGE_DIR / "profile.yaml"),
        "abilities": load_yaml(KNOWLEDGE_DIR / "abilities.yaml"),
        "software": load_yaml(KNOWLEDGE_DIR / "software.yaml"),
        "projects": projects,
        "experiences": experiences,
        "writing_rules": (KNOWLEDGE_DIR / "WRITING_RULES.md").read_text(encoding="utf-8"),
        "resume_schema": json.loads(
            (TEMPLATES_DIR / "resume-schema.json").read_text(encoding="utf-8")
        ),
    }


def build_system_prompt(knowledge: dict) -> str:
    generate_md = (PROMPTS_DIR / "generate.md").read_text(encoding="utf-8")
    data_format = load_data_format()
    kb_json = json.dumps(
        {
            "profile": knowledge["profile"],
            "abilities": knowledge["abilities"],
            "software": knowledge["software"],
            "projects": knowledge["projects"],
            "experiences": knowledge["experiences"],
        },
        ensure_ascii=False,
        indent=2,
    )
    schema_json = json.dumps(knowledge["resume_schema"], ensure_ascii=False, indent=2)

    return f"""You are cvBuilder, a resume generator for internship applications.

Follow ALL rules below. Use ONLY facts from the knowledge base. No boilerplate.

{generate_md}

---

{knowledge["writing_rules"]}

---

{data_format}

---

## Knowledge base (source of truth)

{kb_json}

---

## Resume JSON schema (fill `resume` key with this structure)

{schema_json}

---

## Your response

Return ONLY one JSON object — no markdown fences, no text before or after the JSON.
Use exactly these keys:

{{
  "resume": {{ ... complete resume matching schema; all text fields are plain strings in ONE language ... }},
  "cover_letter": "... markdown, 250-350 words, same language as resume ...",
  "match_report": "... markdown explaining language choice, section selections, gaps ..."
}}

Rules reminder:
- Single language per run (de OR en in meta.output_language)
- Never output {{ "de": "...", "en": "..." }} in resume fields
- Max 3 projects, max 3 bullets each
- Skip education entries with incomplete period
"""


def read_jd_interactive() -> str:
    print("Paste the job description below.", file=sys.stderr)
    print(
        "When finished, do ONE of the following:",
        file=sys.stderr,
    )
    print("  • Press Ctrl+D", file=sys.stderr)
    print("  • Or type END on a new line, then press Enter\n", file=sys.stderr)

    lines: list[str] = []
    try:
        for line in sys.stdin:
            if line.strip() == "END":
                break
            lines.append(line)
    except KeyboardInterrupt:
        raise SystemExit("\nCancelled.") from None

    text = "".join(lines).strip()
    if not text:
        raise SystemExit("No job description provided.")
    return text


def read_jd(args: argparse.Namespace) -> str:
    if args.jd_file:
        text = Path(args.jd_file).read_text(encoding="utf-8").strip()
        if not text:
            raise SystemExit(f"JD file is empty: {args.jd_file}")
        return text

    if args.jd:
        return args.jd.strip()

    if sys.stdin.isatty():
        return read_jd_interactive()

    text = sys.stdin.read().strip()
    if not text:
        raise SystemExit("No job description provided.")
    return text


def build_user_message(jd: str, lang: str | None) -> str:
    user_message = f"Job description:\n\n{jd}"
    if lang:
        user_message += f"\n\nUse output_language: {lang} (override JD language detection)."
    return user_message


def get_provider(args: argparse.Namespace) -> str:
    return llm_get_provider(args.provider)


def call_llm(system_prompt: str, jd: str, lang: str | None, provider: str) -> dict:
    return llm_call(system_prompt, build_user_message(jd, lang), provider)


def validate_result(result: dict) -> list[str]:
    return repair_generate_result(result)


def make_output_dir(name: str | None) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    slug = slugify(name) if name else "application"
    return APPLICATIONS_DIR / f"{stamp}-{slug}"


def slugify(text: str, max_len: int = 40) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:max_len] or "application"


def guess_output_name(resume: dict) -> str:
    generated_for = resume.get("meta", {}).get("generated_for", "")
    return generated_for or resume.get("meta", {}).get("jd_summary", "")[:60]


def write_output(output_dir: Path, jd: str, result: dict) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_dir.joinpath("jd.txt").write_text(jd, encoding="utf-8")
    output_dir.joinpath("resume.json").write_text(
        json.dumps(result["resume"], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    output_dir.joinpath("resume.txt").write_text(
        format_resume_text(result) + "\n",
        encoding="utf-8",
    )
    output_dir.joinpath("cover_letter.md").write_text(
        result["cover_letter"].strip() + "\n",
        encoding="utf-8",
    )
    output_dir.joinpath("match_report.md").write_text(
        result["match_report"].strip() + "\n",
        encoding="utf-8",
    )


def format_resume_text(result: dict) -> str:
    """Render resume + match report + cover letter as plain text."""
    resume = result["resume"]
    sections = resume.get("sections", {})
    meta = resume.get("meta", {})
    lang = meta.get("output_language", "?")
    lines: list[str] = []

    lines.append("=" * 60)
    lines.append("CVBUILDER — GENERATED RESUME")
    lines.append("=" * 60)
    lines.append(f"Language: {lang}")
    if meta.get("generated_for"):
        lines.append(f"Position: {meta['generated_for']}")
    if meta.get("jd_summary"):
        lines.append(f"JD summary: {meta['jd_summary']}")
    lines.append("")

    # §1 Name
    name_sec = sections.get("1_name", {})
    lines.append("[1] NAME")
    lines.append(name_sec.get("value", ""))
    lines.append("")

    # §2 Summary
    summary_sec = sections.get("2_summary", {})
    lines.append("[2] SUMMARY")
    lines.append(summary_sec.get("value", ""))
    lines.append("")

    # §3 Education
    edu_sec = sections.get("3_education", {})
    lines.append("[3] EDUCATION")
    for item in edu_sec.get("items", []):
        lines.append(f"  {item.get('school', '')}")
        lines.append(f"  {item.get('degree', '')}  |  {item.get('period', '')}")
        lines.append("")
    if not edu_sec.get("items"):
        lines.append("  (none)")
        lines.append("")

    # §4 Projects
    proj_sec = sections.get("4_projects", {})
    lines.append("[4] PROJECTS")
    for item in proj_sec.get("items", []):
        lines.append(f"  {item.get('title', '')}")
        lines.append(f"  {item.get('role', '')}  |  {item.get('period', '')}")
        for bullet in item.get("bullets", []):
            text = bullet.get("text", "")
            lines.append(f"    • {text}")
        lines.append("")
    if not proj_sec.get("items"):
        lines.append("  (none)")
        lines.append("")

    # §5 Contact
    contact_sec = sections.get("5_contact", {})
    lines.append("[5] CONTACT")
    lines.append(f"  Email:   {contact_sec.get('email', '')}")
    lines.append(f"  Phone:   {contact_sec.get('phone', '')}")
    lines.append(f"  Address: {contact_sec.get('address', '')}")
    lines.append("")

    # §6 Abilities
    ab_sec = sections.get("6_abilities", {})
    lines.append("[6] ABILITIES")
    for item in ab_sec.get("items", []):
        lines.append(f"  {item.get('rank', '')}. {item.get('name', '')}")
    if not ab_sec.get("items"):
        lines.append("  (none)")
    lines.append("")

    # §7 Software
    sw_sec = sections.get("7_software", {})
    lines.append("[7] SOFTWARE")
    for item in sw_sec.get("items", []):
        lines.append(f"  {item.get('rank', '')}. {item.get('name', '')}")
    if not sw_sec.get("items"):
        lines.append("  (none)")
    lines.append("")

    # §8 Languages
    lang_sec = sections.get("8_languages", {})
    lines.append("[8] LANGUAGES")
    for item in lang_sec.get("items", []):
        lines.append(f"  {item.get('name', '')} — {item.get('level', '')}")
    lines.append("")

    lines.append("=" * 60)
    lines.append("MATCH REPORT")
    lines.append("=" * 60)
    lines.append(result.get("match_report", "").strip())
    lines.append("")
    lines.append("=" * 60)
    lines.append("COVER LETTER")
    lines.append("=" * 60)
    lines.append(result.get("cover_letter", "").strip())
    lines.append("")

    return "\n".join(lines)


def run_dry_run(knowledge: dict, provider: str) -> None:
    print("Knowledge base loaded OK")
    print(f"  Projects: {len(knowledge['projects'])}")
    for p in knowledge["projects"]:
        print(f"    - {p.get('id', p.get('_file'))}")
    print(f"  Abilities: {len(knowledge['abilities'].get('abilities', []))}")
    print(f"  Software:  {len(knowledge['software'].get('software', []))}")
    print(f"  LLM provider: {provider}")
    prompt = build_system_prompt(knowledge)
    print(f"  System prompt size: {len(prompt):,} chars")
    if provider == "gemini":
        print("\nFree tier: get GEMINI_API_KEY at https://aistudio.google.com/apikey")
    elif provider == "ollama":
        print("\nLocal free: install Ollama, run  ollama pull llama3.2")
    print("\nDry run complete. Configure .env and run without --dry-run to generate.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a tailored resume from a job description (JD)."
    )
    parser.add_argument(
        "--jd",
        help="Job description text (if omitted, reads from stdin or --jd-file)",
    )
    parser.add_argument(
        "--jd-file",
        metavar="PATH",
        help="Path to a file containing the job description",
    )
    parser.add_argument(
        "--lang",
        choices=("de", "en"),
        help="Force output language (default: detect from JD)",
    )
    parser.add_argument(
        "--output-dir",
        metavar="PATH",
        help="Output directory (default: applications/<timestamp>-<slug>)",
    )
    parser.add_argument(
        "--provider",
        choices=("gemini", "ollama", "openai"),
        help="LLM backend (default: LLM_PROVIDER in .env, else gemini)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Load knowledge base and exit without calling the LLM",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Do not print resume text to terminal (files still saved)",
    )
    parser.add_argument(
        "--fill-figma",
        action="store_true",
        help="After save, build figma-fill-payload.json for your Figma template",
    )
    parser.add_argument(
        "--copy-figma-clipboard",
        action="store_true",
        help="With --fill-figma, also copy payload JSON to clipboard (macOS)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    knowledge = load_knowledge()
    provider = get_provider(args)

    if args.dry_run:
        run_dry_run(knowledge, provider)
        return

    jd = read_jd(args)
    system_prompt = build_system_prompt(knowledge)

    print(f"Generating resume via {provider} (may take 20-60 seconds)...", file=sys.stderr)
    result = call_llm(system_prompt, jd, args.lang, provider)
    gen_warnings = validate_result(result)
    print_warnings(gen_warnings, "Generation warnings")
    result["match_report"] = append_warnings_report(result.get("match_report", ""), gen_warnings)

    output_dir = (
        Path(args.output_dir)
        if args.output_dir
        else make_output_dir(guess_output_name(result["resume"]))
    )
    write_output(output_dir, jd, result)

    lang = result["resume"]["meta"]["output_language"]

    if not args.quiet:
        print("\n" + format_resume_text(result))

    print(f"\n--- Saved to: {output_dir}/", file=sys.stderr)
    print("  resume.txt      (plain text, same as above)", file=sys.stderr)
    print("  resume.json", file=sys.stderr)
    print("  cover_letter.md", file=sys.stderr)
    print("  match_report.md", file=sys.stderr)

    if args.fill_figma:
        from figma_fill.runner import run_fill

        run_fill(
            output_dir / "resume.json",
            copy_clipboard=args.copy_figma_clipboard,
            quiet=args.quiet,
        )
        print("  figma-fill-payload.json", file=sys.stderr)
        print("  figma-fill.js", file=sys.stderr)

    print(f"Done ({lang}).", file=sys.stderr)


if __name__ == "__main__":
    main()
