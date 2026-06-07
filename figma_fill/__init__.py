"""Build Figma fill payloads from cvBuilder resume.json."""

from figma_fill.map_layers import build_fill_payload, load_template_map
from figma_fill.runner import run_fill

__all__ = ["build_fill_payload", "load_template_map", "run_fill"]
