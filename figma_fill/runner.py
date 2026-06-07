from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from figma_fill.figma_api import validate_payload_against_file
from figma_fill.map_layers import build_fill_payload, load_template_map, project_block_visibility
from figma_fill.plugin_script import generate_plugin_script


def _load_resume(resume_path: Path) -> dict[str, Any]:
    data = json.loads(resume_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"Invalid resume JSON: {resume_path}")
    if "sections" not in data:
        raise SystemExit(f"resume.json missing 'sections': {resume_path}")
    return data


def run_fill(
    resume_path: Path,
    *,
    output_dir: Path | None = None,
    template_map_path: Path | None = None,
    validate: bool = False,
    copy_clipboard: bool = False,
    write_script: bool = True,
    write_payload: bool = True,
    quiet: bool = False,
) -> dict[str, Any]:
    template_map = load_template_map(template_map_path)
    resume = _load_resume(resume_path)
    payload = build_fill_payload(resume, template_map)
    frame_visibility = project_block_visibility(payload, template_map)

    out_dir = output_dir or resume_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    payload_path = out_dir / "figma-fill-payload.json"
    script_path = out_dir / "figma-fill.js"

    if write_payload:
        payload_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    figma_cfg = template_map.get("figma", {})
    template_frame = str(figma_cfg.get("template_frame", "") or "")
    import os

    template_frame = os.environ.get("FIGMA_TEMPLATE_FRAME", template_frame).strip()
    script = generate_plugin_script(
        payload,
        template_frame=template_frame,
        frame_visibility=frame_visibility,
    )
    if write_script:
        script_path.write_text(script, encoding="utf-8")

    result: dict[str, Any] = {
        "payload_path": str(payload_path),
        "script_path": str(script_path),
        "layer_count": len(payload),
        "frame_visibility": frame_visibility,
    }

    if validate:
        import os

        file_key = os.environ.get("FIGMA_FILE_KEY", "").strip()
        token = os.environ.get("FIGMA_ACCESS_TOKEN", "").strip()
        if not file_key or not token:
            raise SystemExit(
                "FIGMA_FILE_KEY and FIGMA_ACCESS_TOKEN required for --validate.\n"
                "Add them to .env (see .env.example)."
            )
        optional_frames = template_map.get("hide_frames", {}).get("project_blocks", [])
        validation = validate_payload_against_file(
            payload,
            file_key,
            token,
            optional_frames=optional_frames,
        )
        result["validation"] = validation
        if validation["missing_text_layers"] and not quiet:
            print("Missing text layers in Figma file:", file=sys.stderr)
            for name in validation["missing_text_layers"]:
                print(f"  - {name}", file=sys.stderr)

    if copy_clipboard:
        payload_text = json.dumps(payload, ensure_ascii=False)
        try:
            subprocess.run(["pbcopy"], input=payload_text.encode("utf-8"), check=True)
            result["clipboard"] = True
        except (FileNotFoundError, subprocess.CalledProcessError):
            result["clipboard"] = False
            if not quiet:
                print(
                    "Could not copy to clipboard (pbcopy unavailable). "
                    f"Use {payload_path} instead.",
                    file=sys.stderr,
                )

    if not quiet:
        print(f"Figma fill payload: {payload_path} ({len(payload)} layers)", file=sys.stderr)
        print(f"Plugin script:        {script_path}", file=sys.stderr)
        print(
            "\nApply in Figma: Plugins → Development → cvBuilder Fill "
            "(import figma-plugin/ once), then paste payload JSON.",
            file=sys.stderr,
        )

    return result
