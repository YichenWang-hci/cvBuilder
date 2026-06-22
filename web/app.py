"""Local web UI for knowledge/ management."""

from __future__ import annotations

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from pathlib import Path

import os
import struct

import yaml
from flask import Flask, abort, flash, redirect, render_template, request, send_file, session, url_for

from web import knowledge_store as ks
from web.figma_layers import layers_grouped, list_figma_layers
from web.generate_service import list_recent_applications, run_generation
from web.experience_intake import extract_experience
from web.project_intake import extract_project

APPLICATIONS_DIR = Path(__file__).resolve().parent.parent / "applications"
WEB_DIR = Path(__file__).resolve().parent
DESIGN_SRC_DIR = WEB_DIR / "design"
DESIGN_STATIC_DIR = WEB_DIR / "static" / "design"
HERO_STATIC_NAME = "hero.png"
HERO_STATIC_2X_NAME = "hero@2x.png"
HERO_PREFERRED_NAMES = ("webdesign.png", "webDesign.png", "hero.png", "webfrist.png")
LEGACY_HERO_FILES = ("webfrist.png", "webfrist@2x.png", "webDesign.png", "webdesign.png")
ALLOWED_DL = frozenset(
    {
        "resume.json",
        "figma-fill-payload.json",
        "resume.txt",
        "cover_letter.md",
        "match_report.md",
        "jd.txt",
    }
)


def _discover_hero_sources() -> tuple[Path | None, Path | None]:
    if not DESIGN_SRC_DIR.is_dir():
        return None, None
    candidates = [
        p
        for p in DESIGN_SRC_DIR.glob("*.png")
        if "@2x" not in p.name.lower() and not p.name.startswith("_")
    ]
    if not candidates:
        return None, None
    hero: Path | None = None
    lower_map = {p.name.lower(): p for p in candidates}
    for preferred in HERO_PREFERRED_NAMES:
        hit = lower_map.get(preferred.lower())
        if hit:
            hero = hit
            break
    if hero is None:
        hero = sorted(candidates, key=lambda p: p.name.lower())[0]
    stem = hero.stem
    hero_2x = DESIGN_SRC_DIR / f"{stem}@2x.png"
    return hero, hero_2x if hero_2x.is_file() else None


def sync_design_assets() -> None:
    """Copy latest hero images from web/design/ to static/design/hero.png."""
    DESIGN_STATIC_DIR.mkdir(parents=True, exist_ok=True)
    import shutil

    hero, hero_2x = _discover_hero_sources()
    if hero:
        dst = DESIGN_STATIC_DIR / HERO_STATIC_NAME
        if not dst.is_file() or hero.stat().st_mtime > dst.stat().st_mtime:
            shutil.copy2(hero, dst)
    if hero_2x:
        dst2 = DESIGN_STATIC_DIR / HERO_STATIC_2X_NAME
        if not dst2.is_file() or hero_2x.stat().st_mtime > dst2.stat().st_mtime:
            shutil.copy2(hero_2x, dst2)

    for legacy in LEGACY_HERO_FILES:
        legacy_path = DESIGN_STATIC_DIR / legacy
        if legacy_path.is_file():
            legacy_path.unlink()


def _png_size(path: Path) -> tuple[int, int] | None:
    try:
        with path.open("rb") as handle:
            handle.seek(16)
            width, height = struct.unpack(">II", handle.read(8))
            return int(width), int(height)
    except OSError:
        return None


def load_site_config() -> dict[str, str]:
    cfg: dict[str, str] = {}
    site_path = WEB_DIR / "site.yaml"
    if site_path.is_file():
        raw = yaml.safe_load(site_path.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            cfg = {str(k): str(v) for k, v in raw.items() if v is not None}
    env_url = os.getenv("TEMPLATES_VIDEO_URL", "").strip()
    if env_url:
        cfg["templates_video_url"] = env_url
    return cfg


def hero_image_context() -> dict[str, object]:
    sync_design_assets()
    hero_1x = DESIGN_STATIC_DIR / HERO_STATIC_NAME
    hero_2x = DESIGN_STATIC_DIR / HERO_STATIC_2X_NAME
    size = _png_size(hero_1x) if hero_1x.is_file() else None
    hero_width = size[0] if size else 2000
    hero_height = size[1] if size else 1125
    ctx: dict[str, object] = {
        "hero_image": hero_1x.is_file(),
        "hero_src": f"design/{HERO_STATIC_NAME}",
        "hero_2x": hero_2x.is_file(),
        "hero_width": hero_width,
        "hero_height": hero_height,
        "hero_max_width": hero_width,
    }
    if hero_2x.is_file():
        size_2x = _png_size(hero_2x)
        ctx["hero_src_2x"] = f"design/{HERO_STATIC_2X_NAME}"
        ctx["hero_width_2x"] = size_2x[0] if size_2x else hero_width * 2
        ctx["hero_height_2x"] = size_2x[1] if size_2x else hero_height * 2
        ctx["hero_max_width"] = max(hero_width, ctx["hero_width_2x"])
    return ctx


def create_app() -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.secret_key = "cvbuilder-local-dev"

    @app.context_processor
    def _inject_site_config() -> dict[str, object]:
        site = load_site_config()
        return {
            "templates_video_url": site.get("templates_video_url", "").strip(),
        }

    @app.before_request
    def _ensure_kb() -> None:
        ks.ensure_knowledge_dir()

    @app.route("/")
    def index():
        profile = ks.load_profile()
        projects = ks.list_projects()
        experiences = ks.list_experiences()
        abilities = ks.load_abilities().get("abilities", [])
        software = ks.load_software().get("software", [])
        layers = list_figma_layers()
        filled = sum(1 for l in layers if l["fillable"] and l["has_data"])
        fillable = sum(1 for l in layers if l["fillable"])
        return render_template(
            "index.html",
            profile=profile,
            project_count=len(projects),
            experience_count=len(experiences),
            ability_count=len(abilities),
            software_count=len(software),
            layer_filled=filled,
            layer_fillable=fillable,
            **hero_image_context(),
        )

    @app.route("/profile", methods=["GET", "POST"])
    def profile():
        if request.method == "POST":
            data = ks.load_profile()
            data["name"] = request.form.get("name", "").strip()
            data["contact"] = {
                "email": request.form.get("email", "").strip(),
                "phone": request.form.get("phone", "").strip(),
                "address": request.form.get("address", "").strip(),
            }
            data["languages"] = _parse_languages(request.form)
            data["education"] = _parse_education(request.form)
            data["summaries"] = _parse_summaries(request.form)
            ctx = data.get("application_context") or {}
            ctx["goal"] = request.form.get("goal", "full-time-intern").strip()
            ctx["earliest_start"] = request.form.get("earliest_start", "").strip()
            ctx["duration"] = request.form.get("duration", "").strip()
            ctx["days_per_week"] = int(request.form.get("days_per_week") or 5)
            ctx["note"] = {
                "de": request.form.get("note_de", "").strip(),
                "en": request.form.get("note_en", "").strip(),
            }
            data["application_context"] = ctx
            ks.save_profile(data)
            flash("Profile saved.", "ok")
            return redirect(url_for("profile"))

        return render_template("profile.html", profile=ks.load_profile())

    @app.route("/projects")
    def projects():
        return render_template("projects.html", projects=ks.list_projects())

    @app.route("/projects/new/narrative", methods=["GET", "POST"])
    def project_narrative():
        if request.method == "POST":
            narrative = request.form.get("narrative", "").strip()
            if not narrative:
                flash("Please enter a project description first.", "err")
                return redirect(url_for("project_narrative"))
            try:
                result = extract_project(narrative)
            except Exception as exc:
                flash(f"Extraction failed: {exc}", "err")
                return render_template(
                    "project_narrative.html",
                    narrative=narrative,
                )
            session["draft_project"] = result["project"]
            session["draft_intake_report"] = result.get("intake_report", "")
            flash("Project extracted. Review and save.", "ok")
            return redirect(url_for("project_form", project_id="new"))

        return render_template("project_narrative.html", narrative="")

    @app.route("/projects/new", methods=["GET", "POST"])
    @app.route("/projects/<project_id>/edit", methods=["GET", "POST"])
    def project_form(project_id: str | None = None):
        is_new = project_id is None or project_id == "new"
        intake_report = ""
        if is_new and session.get("draft_project"):
            project = session.get("draft_project")
            intake_report = session.get("draft_intake_report", "")
        elif is_new:
            project = None
        else:
            project = ks.load_project(project_id)
        if not is_new and not project:
            flash("Project not found.", "err")
            return redirect(url_for("projects"))

        if request.method == "POST":
            bullets = _parse_bullets(request.form)
            pid = request.form.get("id", "").strip()
            project_data = {
                "id": pid,
                "title": {
                    "de": request.form.get("title_de", "").strip(),
                    "en": request.form.get("title_en", "").strip(),
                },
                "role": {
                    "de": request.form.get("role_de", "").strip(),
                    "en": request.form.get("role_en", "").strip(),
                },
                "period": request.form.get("period", "").strip(),
                "type": {
                    "de": request.form.get("type_de", "").strip(),
                    "en": request.form.get("type_en", "").strip(),
                },
                "tech_stack": [
                    t.strip() for t in request.form.get("tech_stack", "").split(",") if t.strip()
                ],
                "keywords": [
                    t.strip() for t in request.form.get("keywords", "").split(",") if t.strip()
                ],
                "target_roles": [
                    t.strip() for t in request.form.get("target_roles", "").split(",") if t.strip()
                ],
                "bullets": bullets,
                "links": {"github": None, "demo": None, "paper": None},
                "story_hooks": _empty_story_hooks(),
            }
            draft = session.get("draft_project") or {}
            existing = ks.load_project(pid) if not is_new else {}
            for src in (draft, existing or {}):
                if src.get("links"):
                    project_data["links"] = src["links"]
                if src.get("story_hooks"):
                    project_data["story_hooks"] = src["story_hooks"]
            ks.save_project(project_data)
            session.pop("draft_project", None)
            session.pop("draft_intake_report", None)
            flash(f"Project '{pid}' saved.", "ok")
            return redirect(url_for("projects"))

        return render_template(
            "project_form.html",
            project=project,
            is_new=is_new,
            intake_report=intake_report,
            from_narrative=bool(intake_report),
        )

    @app.post("/projects/<project_id>/delete")
    def project_delete(project_id: str):
        if ks.delete_project(project_id):
            flash(f"Deleted '{project_id}'.", "ok")
        else:
            flash("Project not found.", "err")
        return redirect(url_for("projects"))

    @app.route("/experiences")
    def experiences():
        return render_template("experiences.html", experiences=ks.list_experiences())

    @app.route("/experiences/new/narrative", methods=["GET", "POST"])
    def experience_narrative():
        if request.method == "POST":
            narrative = request.form.get("narrative", "").strip()
            if not narrative:
                flash("Please enter a work or internship description first.", "err")
                return redirect(url_for("experience_narrative"))
            try:
                result = extract_experience(narrative)
            except Exception as exc:
                flash(f"Extraction failed: {exc}", "err")
                return render_template(
                    "experience_narrative.html",
                    narrative=narrative,
                )
            session["draft_experience"] = result["experience"]
            session["draft_experience_report"] = result.get("intake_report", "")
            flash("Work/internship extracted. Review and save.", "ok")
            return redirect(url_for("experience_form", experience_id="new"))

        return render_template("experience_narrative.html", narrative="")

    @app.route("/experiences/new", methods=["GET", "POST"])
    @app.route("/experiences/<experience_id>/edit", methods=["GET", "POST"])
    def experience_form(experience_id: str | None = None):
        is_new = experience_id is None or experience_id == "new"
        intake_report = ""
        if is_new and session.get("draft_experience"):
            experience = session.get("draft_experience")
            intake_report = session.get("draft_experience_report", "")
        elif is_new:
            experience = None
        else:
            experience = ks.load_experience(experience_id)
        if not is_new and not experience:
            flash("Experience not found.", "err")
            return redirect(url_for("experiences"))

        if request.method == "POST":
            bullets = _parse_bullets(request.form)
            eid = request.form.get("id", "").strip()
            kind = request.form.get("kind", "internship").strip().lower()
            if kind not in ("internship", "work"):
                kind = "internship"
            experience_data = {
                "id": eid,
                "kind": kind,
                "company": request.form.get("company", "").strip(),
                "title": {
                    "de": request.form.get("title_de", "").strip(),
                    "en": request.form.get("title_en", "").strip(),
                },
                "role": {
                    "de": request.form.get("role_de", "").strip(),
                    "en": request.form.get("role_en", "").strip(),
                },
                "period": request.form.get("period", "").strip(),
                "type": {
                    "de": request.form.get("type_de", "").strip(),
                    "en": request.form.get("type_en", "").strip(),
                },
                "location": request.form.get("location", "").strip(),
                "tech_stack": [
                    t.strip() for t in request.form.get("tech_stack", "").split(",") if t.strip()
                ],
                "keywords": [
                    t.strip() for t in request.form.get("keywords", "").split(",") if t.strip()
                ],
                "target_roles": [
                    t.strip() for t in request.form.get("target_roles", "").split(",") if t.strip()
                ],
                "bullets": bullets,
                "links": {"github": None, "demo": None, "paper": None},
                "story_hooks": _empty_story_hooks(),
            }
            draft = session.get("draft_experience") or {}
            existing = ks.load_experience(eid) if not is_new else {}
            for src in (draft, existing or {}):
                if src.get("links"):
                    experience_data["links"] = src["links"]
                if src.get("story_hooks"):
                    experience_data["story_hooks"] = src["story_hooks"]
            ks.save_experience(experience_data)
            session.pop("draft_experience", None)
            session.pop("draft_experience_report", None)
            flash(f"Experience '{eid}' saved.", "ok")
            return redirect(url_for("experiences"))

        return render_template(
            "experience_form.html",
            experience=experience,
            is_new=is_new,
            intake_report=intake_report,
            from_narrative=bool(intake_report),
        )

    @app.post("/experiences/<experience_id>/delete")
    def experience_delete(experience_id: str):
        if ks.delete_experience(experience_id):
            flash(f"Deleted '{experience_id}'.", "ok")
        else:
            flash("Experience not found.", "err")
        return redirect(url_for("experiences"))

    @app.route("/abilities", methods=["GET", "POST"])
    def abilities():
        if request.method == "POST":
            items = []
            ids = request.form.getlist("ability_id")
            for i, aid in enumerate(ids):
                aid = aid.strip()
                if not aid:
                    continue
                items.append(
                    {
                        "id": aid,
                        "name": {
                            "de": request.form.getlist("ability_name_de")[i].strip(),
                            "en": request.form.getlist("ability_name_en")[i].strip(),
                        },
                        "keywords": [
                            t.strip()
                            for t in request.form.getlist("ability_keywords")[i].split(",")
                            if t.strip()
                        ],
                        "evidence": [
                            {"project_id": e.strip()}
                            for e in request.form.getlist("ability_evidence")[i].split(",")
                            if e.strip()
                        ],
                    }
                )
            ks.save_abilities({"abilities": items})
            flash("Abilities saved.", "ok")
            return redirect(url_for("abilities"))

        return render_template(
            "abilities.html",
            abilities=ks.load_abilities().get("abilities", []),
            projects=ks.list_projects(),
        )

    @app.route("/software", methods=["GET", "POST"])
    def software():
        if request.method == "POST":
            items = []
            ids = request.form.getlist("software_id")
            for i, sid in enumerate(ids):
                sid = sid.strip()
                if not sid:
                    continue
                items.append(
                    {
                        "id": sid,
                        "name": {
                            "de": request.form.getlist("software_name_de")[i].strip(),
                            "en": request.form.getlist("software_name_en")[i].strip(),
                        },
                        "keywords": [
                            t.strip()
                            for t in request.form.getlist("software_keywords")[i].split(",")
                            if t.strip()
                        ],
                        "evidence": [
                            {"project_id": e.strip()}
                            for e in request.form.getlist("software_evidence")[i].split(",")
                            if e.strip()
                        ],
                    }
                )
            ks.save_software({"software": items})
            flash("Software saved.", "ok")
            return redirect(url_for("software"))

        return render_template(
            "software.html",
            software=ks.load_software().get("software", []),
            projects=ks.list_projects(),
        )

    @app.route("/figma-layers")
    def figma_layers():
        layers = list_figma_layers()
        grouped = layers_grouped()
        names_only = [l["name"] for l in layers if l["fillable"]]
        return render_template(
            "figma_layers.html",
            layers=layers,
            grouped=grouped,
            names_text="\n".join(names_only),
        )

    @app.route("/generate", methods=["GET", "POST"])
    def generate_resume():
        if request.method == "POST":
            jd = request.form.get("jd", "").strip()
            lang = request.form.get("lang", "").strip() or None
            if lang == "auto":
                lang = None
            fill_figma = request.form.get("fill_figma") == "on"
            try:
                out = run_generation(jd, lang=lang, fill_figma=fill_figma)
            except Exception as exc:
                flash(f"Generation failed: {exc}", "err")
                return render_template(
                    "generate.html",
                    jd=jd,
                    lang=request.form.get("lang", "auto"),
                    fill_figma=fill_figma,
                    recent=list_recent_applications(),
                )
            return render_template(
                "generate.html",
                jd=jd,
                lang=request.form.get("lang", "auto"),
                fill_figma=fill_figma,
                recent=list_recent_applications(),
                output=out,
            )

        return render_template(
            "generate.html",
            jd="",
            lang="auto",
            fill_figma=True,
            recent=list_recent_applications(),
            output=None,
        )

    @app.route("/applications/<folder>/<filename>")
    def application_file(folder: str, filename: str):
        if filename not in ALLOWED_DL:
            abort(404)
        if ".." in folder or "/" in folder:
            abort(404)
        path = (APPLICATIONS_DIR / folder / filename).resolve()
        if not str(path).startswith(str(APPLICATIONS_DIR.resolve())):
            abort(404)
        if not path.is_file():
            abort(404)
        as_attachment = request.args.get("download") == "1"
        return send_file(path, as_attachment=as_attachment)

    return app


def _parse_languages(form) -> list[dict]:
    items = []
    for i in range(len(form.getlist("lang_name_de"))):
        de = form.getlist("lang_name_de")[i].strip()
        if not de and not form.getlist("lang_name_en")[i].strip():
            continue
        items.append(
            {
                "name": {
                    "de": de,
                    "en": form.getlist("lang_name_en")[i].strip(),
                },
                "level": {
                    "de": form.getlist("lang_level_de")[i].strip(),
                    "en": form.getlist("lang_level_en")[i].strip(),
                },
            }
        )
    return items


def _parse_education(form) -> list[dict]:
    items = []
    ids = form.getlist("edu_id")
    for i, eid in enumerate(ids):
        school = form.getlist("edu_school")[i].strip()
        if not school and not eid.strip():
            continue
        items.append(
            {
                "id": eid.strip() or f"edu-{i+1}",
                "school": school,
                "degree": {
                    "de": form.getlist("edu_degree_de")[i].strip(),
                    "en": form.getlist("edu_degree_en")[i].strip(),
                },
                "period": form.getlist("edu_period")[i].strip(),
                "relevance": [
                    t.strip()
                    for t in form.getlist("edu_relevance")[i].split(",")
                    if t.strip()
                ],
            }
        )
    return items


def _parse_summaries(form) -> list[dict]:
    items = []
    ids = form.getlist("summary_id")
    for i, sid in enumerate(ids):
        if not sid.strip():
            continue
        ctx = [t.strip() for t in form.getlist("summary_context")[i].split(",") if t.strip()]
        items.append(
            {
                "id": sid.strip(),
                "context": ctx,
                "text": {
                    "de": form.getlist("summary_text_de")[i].strip(),
                    "en": form.getlist("summary_text_en")[i].strip(),
                },
            }
        )
    return items


def _empty_story_hooks() -> dict:
    blank = {"de": "", "en": ""}
    return {k: dict(blank) for k in ("problem", "constraint", "decision", "outcome", "lesson")}


def _parse_bullets(form) -> list[dict]:
    bullets = []
    ids = form.getlist("bullet_id")
    for i, bid in enumerate(ids):
        if not bid.strip():
            continue
        bullets.append(
            {
                "id": bid.strip(),
                "text": {
                    "de": form.getlist("bullet_text_de")[i].strip(),
                    "en": form.getlist("bullet_text_en")[i].strip(),
                },
                "tags": [
                    t.strip() for t in form.getlist("bullet_tags")[i].split(",") if t.strip()
                ],
                "metric": None,
            }
        )
    return bullets
