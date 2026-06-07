#!/usr/bin/env python3
"""Fill a Figma resume template from resume.json."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from figma_fill.map_layers import build_fill_payload, load_template_map
from figma_fill.runner import run_fill

ROOT = Path(__file__).resolve().parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build Figma fill payload from cvBuilder resume.json."
    )
    parser.add_argument(
        "resume_json",
        type=Path,
        help="Path to resume.json (e.g. applications/.../resume.json)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        metavar="DIR",
        help="Where to write figma-fill-payload.json (default: same dir as resume)",
    )
    parser.add_argument(
        "--template-map",
        type=Path,
        metavar="PATH",
        help="Override templates/figma-template-map.yaml",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Check layer names against Figma file (needs FIGMA_* in .env)",
    )
    parser.add_argument(
        "--copy-clipboard",
        action="store_true",
        help="Copy payload JSON to clipboard (macOS pbcopy)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print payload to stdout, do not write files",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress status messages",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    resume_path = args.resume_json.expanduser().resolve()
    if not resume_path.is_file():
        raise SystemExit(f"File not found: {resume_path}")

    if args.dry_run:
        template_map = load_template_map(args.template_map)
        resume = json.loads(resume_path.read_text(encoding="utf-8"))
        payload = build_fill_payload(resume, template_map)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    run_fill(
        resume_path,
        output_dir=args.output_dir,
        template_map_path=args.template_map,
        validate=args.validate,
        copy_clipboard=args.copy_clipboard,
        quiet=args.quiet,
    )


if __name__ == "__main__":
    main()
