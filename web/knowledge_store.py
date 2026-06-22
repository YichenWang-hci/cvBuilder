"""Read/write local knowledge/ YAML — no LLM."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
KNOWLEDGE_DIR = ROOT / "knowledge"
PROJECTS_DIR = KNOWLEDGE_DIR / "projects"
EXPERIENCES_DIR = KNOWLEDGE_DIR / "experiences"
PROFILE_PATH = KNOWLEDGE_DIR / "profile.yaml"
ABILITIES_PATH = KNOWLEDGE_DIR / "abilities.yaml"
SOFTWARE_PATH = KNOWLEDGE_DIR / "software.yaml"


def ensure_knowledge_dir() -> None:
    if not KNOWLEDGE_DIR.is_dir():
        example = ROOT / "knowledge.example"
        if example.is_dir():
            import shutil

            shutil.copytree(example, KNOWLEDGE_DIR)
        else:
            KNOWLEDGE_DIR.mkdir(parents=True)
            PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
            EXPERIENCES_DIR.mkdir(parents=True, exist_ok=True)
    else:
        EXPERIENCES_DIR.mkdir(parents=True, exist_ok=True)


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, dict) else {}


def save_yaml(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.dump(
            data,
            f,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
            width=88,
        )


def load_profile() -> dict[str, Any]:
    return load_yaml(PROFILE_PATH)


def save_profile(data: dict[str, Any]) -> None:
    save_yaml(PROFILE_PATH, data)


def load_abilities() -> dict[str, Any]:
    return load_yaml(ABILITIES_PATH)


def save_abilities(data: dict[str, Any]) -> None:
    save_yaml(ABILITIES_PATH, data)


def load_software() -> dict[str, Any]:
    return load_yaml(SOFTWARE_PATH)


def save_software(data: dict[str, Any]) -> None:
    save_yaml(SOFTWARE_PATH, data)


def list_projects() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    if not PROJECTS_DIR.is_dir():
        return items
    for path in sorted(PROJECTS_DIR.glob("*.yaml")):
        if path.name.startswith("_"):
            continue
        data = load_yaml(path)
        if data:
            data["_file"] = path.name
            items.append(data)
    return items


def project_path(project_id: str) -> Path:
    slug = project_id.strip().lower().replace(" ", "-")
    return PROJECTS_DIR / f"{slug}.yaml"


def load_project(project_id: str) -> dict[str, Any] | None:
    path = project_path(project_id)
    if not path.is_file():
        for p in PROJECTS_DIR.glob("*.yaml"):
            data = load_yaml(p)
            if data.get("id") == project_id:
                data["_file"] = p.name
                return data
        return None
    data = load_yaml(path)
    data["_file"] = path.name
    return data


def save_project(data: dict[str, Any]) -> Path:
    pid = str(data.get("id", "")).strip()
    if not pid:
        raise ValueError("project id is required")
    path = project_path(pid)
    clean = {k: v for k, v in data.items() if not k.startswith("_")}
    save_yaml(path, clean)
    return path


def delete_project(project_id: str) -> bool:
    path = project_path(project_id)
    if path.is_file():
        path.unlink()
        return True
    for p in PROJECTS_DIR.glob("*.yaml"):
        data = load_yaml(p)
        if data.get("id") == project_id:
            p.unlink()
            return True
    return False


def list_experiences() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    if not EXPERIENCES_DIR.is_dir():
        return items
    for path in sorted(EXPERIENCES_DIR.glob("*.yaml")):
        if path.name.startswith("_"):
            continue
        data = load_yaml(path)
        if data:
            data["_file"] = path.name
            items.append(data)
    return items


def experience_path(exp_id: str) -> Path:
    slug = exp_id.strip().lower().replace(" ", "-")
    return EXPERIENCES_DIR / f"{slug}.yaml"


def load_experience(exp_id: str) -> dict[str, Any] | None:
    path = experience_path(exp_id)
    if not path.is_file():
        for p in EXPERIENCES_DIR.glob("*.yaml"):
            data = load_yaml(p)
            if data.get("id") == exp_id:
                data["_file"] = p.name
                return data
        return None
    data = load_yaml(path)
    data["_file"] = path.name
    return data


def save_experience(data: dict[str, Any]) -> Path:
    eid = str(data.get("id", "")).strip()
    if not eid:
        raise ValueError("experience id is required")
    path = experience_path(eid)
    clean = {k: v for k, v in data.items() if not k.startswith("_")}
    save_yaml(path, clean)
    return path


def delete_experience(exp_id: str) -> bool:
    path = experience_path(exp_id)
    if path.is_file():
        path.unlink()
        return True
    for p in EXPERIENCES_DIR.glob("*.yaml"):
        data = load_yaml(p)
        if data.get("id") == exp_id:
            p.unlink()
            return True
    return False


def _pick_lang_text(field: Any, prefer: str = "en") -> str:
    if isinstance(field, dict):
        return str(field.get(prefer) or field.get("de") or field.get("en") or "").strip()
    return str(field or "").strip()


def _experience_display_title(exp: dict[str, Any], prefer: str = "en") -> str:
    company = str(exp.get("company", "")).strip()
    subtitle = _pick_lang_text(exp.get("title"), prefer)
    if company and subtitle and subtitle.lower() != company.lower():
        return f"{company} — {subtitle}"
    return company or subtitle


def _item_to_section4(entry: dict[str, Any], source: str, prefer: str = "en") -> dict[str, Any]:
    bullets = []
    for b in (entry.get("bullets") or [])[:3]:
        text = b.get("text", {})
        bullets.append(
            {
                "text": _pick_lang_text(text, prefer) if isinstance(text, dict) else str(text)
            }
        )
    if source == "experience":
        title = _experience_display_title(entry, prefer)
        role = _pick_lang_text(entry.get("role"), prefer)
    else:
        title = _pick_lang_text(entry.get("title"), prefer)
        role = _pick_lang_text(entry.get("role"), prefer)
    return {
        "title": title,
        "role": role,
        "period": str(entry.get("period", "")),
        "bullets": bullets,
    }


def build_section4_items(max_items: int = 3, prefer: str = "en") -> list[dict[str, Any]]:
    """Merge work/internship + projects for resume §4 preview (experiences first)."""
    items: list[dict[str, Any]] = []
    for exp in list_experiences():
        if len(items) >= max_items:
            break
        items.append(_item_to_section4(exp, "experience", prefer))
    for proj in list_projects():
        if len(items) >= max_items:
            break
        items.append(_item_to_section4(proj, "project", prefer))
    return items


def build_preview_resume() -> dict[str, Any]:
    """Build a resume-shaped dict from knowledge for Figma layer preview."""
    profile = load_profile()
    abilities = load_abilities().get("abilities", [])
    software = load_software().get("software", [])
    proj_items = build_section4_items(max_items=3)

    summary = (profile.get("summaries") or [{}])[0]
    summary_text = summary.get("text", {})
    if isinstance(summary_text, dict):
        summary_value = summary_text.get("en") or summary_text.get("de") or ""
    else:
        summary_value = str(summary_text)

    edu_items = []
    for edu in profile.get("education") or []:
        degree = edu.get("degree", {})
        edu_items.append(
            {
                "school": edu.get("school", ""),
                "degree": degree.get("en") or degree.get("de") or "",
                "period": edu.get("period", ""),
            }
        )

    contact = profile.get("contact", {})
    lang_items = []
    for lang in profile.get("languages") or []:
        name = lang.get("name", {})
        level = lang.get("level", {})
        lang_items.append(
            {
                "name": name.get("en") or name.get("de") or "",
                "level": level.get("en") or level.get("de") or "",
            }
        )

    return {
        "sections": {
            "1_name": {"value": profile.get("name", "")},
            "2_summary": {"value": summary_value},
            "3_education": {"items": edu_items},
            "4_projects": {"items": proj_items},
            "5_contact": {
                "email": contact.get("email", ""),
                "phone": contact.get("phone", ""),
                "address": contact.get("address", ""),
            },
            "6_abilities": {
                "items": [
                    {
                        "name": (
                            (a.get("name") or {}).get("en")
                            or (a.get("name") or {}).get("de")
                            or ""
                        )
                    }
                    for a in abilities[:6]
                ]
            },
            "7_software": {
                "items": [
                    {
                        "name": (
                            (s.get("name") or {}).get("en")
                            or (s.get("name") or {}).get("de")
                            or ""
                        )
                    }
                    for s in software[:7]
                ]
            },
            "8_languages": {"items": lang_items},
        }
    }
