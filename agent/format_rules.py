"""Shared format checks — collect warnings, never block the pipeline."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_FORMAT_PATH = ROOT / "templates" / "DATA_FORMAT.md"

# ISO-like patterns that should be normalized to German format
_ISO_PERIOD = re.compile(
    r"(\d{4})-(\d{1,2})(?:-(\d{1,2}))?\s*-\s*(\d{4})-(\d{1,2})(?:-(\d{1,2}))?"
)
_ISO_SINGLE = re.compile(r"^(\d{4})-(\d{1,2})(?:-(\d{1,2}))?$")
_SLASH_DATE = re.compile(r"^(\d{1,2})[/.](\d{1,2})[/.](\d{4})$")

_GERMAN_MONTHS = {
    1: "Januar",
    2: "Februar",
    3: "März",
    4: "April",
    5: "Mai",
    6: "Juni",
    7: "Juli",
    8: "August",
    9: "September",
    10: "Oktober",
    11: "November",
    12: "Dezember",
}


def load_data_format() -> str:
    if DATA_FORMAT_PATH.is_file():
        return DATA_FORMAT_PATH.read_text(encoding="utf-8")
    return ""


def _pad2(n: int) -> str:
    return f"{n:02d}"


def normalize_period(period: str) -> tuple[str, list[str]]:
    """Best-effort German period normalization. Returns (value, warnings)."""
    warnings: list[str] = []
    raw = (period or "").strip()
    if not raw:
        return "", warnings

    text = raw
    lower = text.lower().replace("today", "heute").replace("present", "heute")
    if lower != text:
        text = lower

    # YYYY-MM - YYYY-MM  →  MM.JJJJ - MM.JJJJ
    m = _ISO_PERIOD.match(text.replace(" ", ""))
    if m:
        y1, mo1, d1, y2, mo2, d2 = m.groups()
        if d1 and d2:
            norm = f"{_pad2(int(d1))}.{_pad2(int(mo1))}.{y1} - {_pad2(int(d2))}.{_pad2(int(mo2))}.{y2}"
        else:
            norm = f"{_pad2(int(mo1))}.{y1} - {_pad2(int(mo2))}.{y2}"
        warnings.append(f"Normalized period {raw!r} → {norm!r}")
        return norm, warnings

    # range with one ISO side: 2025-4 - heute / 2025-4 -
    m = re.match(
        r"^(\d{4})-(\d{1,2})(?:-(\d{1,2}))?\s*-\s*(.*)$",
        text.strip(),
        re.I,
    )
    if m:
        y, mo, d, end = m.groups()
        if d:
            start = f"{_pad2(int(d))}.{_pad2(int(mo))}.{y}"
        else:
            start = f"{_pad2(int(mo))}.{y}"
        end = (end or "").strip()
        if not end:
            norm = f"{start} - "
        else:
            end_norm, end_warns = normalize_period(end)
            warnings.extend(end_warns)
            norm = f"{start} - {end_norm}"
        warnings.append(f"Normalized period {raw!r} → {norm!r}")
        return norm, warnings

    # single YYYY-MM or YYYY-MM-DD
    m = _ISO_SINGLE.match(text.replace(" ", ""))
    if m:
        y, mo, d = m.groups()
        if d:
            norm = f"{_pad2(int(d))}.{_pad2(int(mo))}.{y}"
        else:
            norm = f"{_pad2(int(mo))}.{y}"
        warnings.append(f"Normalized period {raw!r} → {norm!r}")
        return norm, warnings

    # already German-ish: ensure lowercase heute
    if re.search(r"\bheute\b", text, re.I):
        text = re.sub(r"\bheute\b", "heute", text, flags=re.I)
        text = re.sub(r"\bHeute\b", "heute", text)

    # flag remaining ISO fragments
    if re.search(r"\d{4}-\d{1,2}", text):
        warnings.append(
            f"Period {raw!r} still contains ISO-style dates — "
            "use German TT.MM.JJJJ or MM.JJJJ (see templates/DATA_FORMAT.md)"
        )

    return text, warnings


def _format_de_national(national: str) -> str:
    """Group German national number (without country code) per DIN 5008."""
    national = national.strip()
    if not national:
        return ""

    # Mobile 15x / 16x / 17x — Vorwahl usually 3 digits
    if national.startswith(("15", "16", "17")) and len(national) > 3:
        return f"{national[:3]} {national[3:]}"

    # Landline — common 3-digit Vorwahl (931, 911, 351, …)
    if len(national) >= 10:
        return f"{national[:3]} {national[3:]}"
    if len(national) >= 9:
        return f"{national[:2]} {national[2:]}"
    return national


def normalize_phone(phone: str) -> tuple[str, list[str]]:
    """Best-effort DIN 5008 / E.123 normalization. Returns (value, warnings)."""
    warnings: list[str] = []
    raw = (phone or "").strip()
    if not raw:
        return "", warnings

    text = raw.replace("(0)", "")
    text = re.sub(r"[/.\-]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    if text.startswith("00"):
        digits = re.sub(r"\D", "", text[2:])
        national = digits[2:] if digits.startswith("49") else digits
        result = f"+49 {_format_de_national(national)}" if digits.startswith("49") else f"+{digits}"
        warnings.append(f"Normalized phone {raw!r} → {result!r} (DIN 5008: use + not 00)")
        return result.strip(), warnings

    if text.startswith("+"):
        digits = re.sub(r"\D", "", text[1:])
        if digits.startswith("49"):
            result = f"+49 {_format_de_national(digits[2:])}"
        else:
            # Non-DE: space after country code (best effort for 1–3 digit CC)
            cc_len = 1 if digits.startswith("1") else 2
            result = f"+{digits[:cc_len]} {digits[cc_len:]}" if len(digits) > cc_len else f"+{digits}"
        if result != raw:
            warnings.append(f"Normalized phone {raw!r} → {result!r}")
        return result.strip(), warnings

    if text.startswith("0"):
        national = re.sub(r"\D", "", text[1:])
        result = f"+49 {_format_de_national(national)}"
        warnings.append(f"Normalized national phone {raw!r} → {result!r} (DIN 5008)")
        return result.strip(), warnings

    warnings.append(
        f"Phone {raw!r} missing + country code — use DIN 5008, e.g. +49 152 06820364"
    )
    return raw, warnings


def phone_quality_warning(phone: str) -> str | None:
    p = (phone or "").strip()
    if not p:
        return None
    if p.startswith("00"):
        return f"contact.phone {p!r} uses 00 prefix — DIN 5008 requires + (e.g. +49 ...)"
    if not p.startswith("+"):
        return f"contact.phone {p!r} is not international format — use +CC ... (DIN 5008)"
    if "(0)" in p:
        return "contact.phone contains (0) — remove per DIN 5008"
    if " " not in p:
        return f"contact.phone {p!r} has no spaces between blocks — use +49 152 06820364 (DIN 5008)"
    if re.search(r"[/.\-]", p):
        return f"contact.phone {p!r} uses / . - — DIN 5008 prefers spaces between blocks"
    return None


def period_quality_warning(period: str, label: str) -> str | None:
    if not (period or "").strip():
        return f"{label}: period is empty (will be skipped in resume generation)"
    if re.search(r"\d{4}-\d{1,2}(?:-\d{1,2})?", period):
        return (
            f"{label}: period {period!r} uses non-German date format — "
            "prefer TT.MM.JJJJ or MM.JJJJ"
        )
    return None


def check_profile_warnings(profile: dict) -> list[str]:
    warnings: list[str] = []

    if not (profile.get("name") or "").strip():
        warnings.append("name is empty — add your full name in profile.yaml")

    contact = profile.get("contact") or {}
    for field in ("email", "address"):
        if not str(contact.get(field, "")).strip():
            warnings.append(f"contact.{field} is empty — add before sending applications")
    phone = str(contact.get("phone", "")).strip()
    if not phone:
        warnings.append("contact.phone is empty — add before sending applications")
    else:
        w = phone_quality_warning(phone)
        if w:
            warnings.append(w)

    if not profile.get("languages"):
        warnings.append("languages list is empty — add at least one language")

    for edu in profile.get("education") or []:
        label = f"education[{edu.get('id', edu.get('school', '?'))}]"
        if not (edu.get("school") or "").strip():
            warnings.append(f"{label}: school is empty")
        degree = edu.get("degree") or {}
        if not str(degree.get("de", "")).strip() or not str(degree.get("en", "")).strip():
            warnings.append(f"{label}: degree missing de or en translation")
        w = period_quality_warning(str(edu.get("period", "")), label)
        if w:
            warnings.append(w)

    if not profile.get("summaries"):
        warnings.append("summaries is empty — generate.py needs at least one summary")

    ctx = profile.get("application_context") or {}
    start = str(ctx.get("earliest_start", "")).strip()
    if start and re.match(r"^\d{4}-\d{2}$", start):
        y, mo = start.split("-")
        warnings.append(
            f"application_context.earliest_start {start!r} → prefer MM.JJJJ "
            f"(e.g. {_pad2(int(mo))}.{y})"
        )

    return warnings


def normalize_profile_contact(profile: dict) -> list[str]:
    """Normalize contact.phone in place (DIN 5008). Returns warnings."""
    contact = profile.get("contact")
    if not isinstance(contact, dict):
        return []
    phone = str(contact.get("phone", ""))
    norm, warns = normalize_phone(phone)
    contact["phone"] = norm
    return warns


def normalize_profile_periods(profile: dict) -> list[str]:
    """Normalize education periods in place. Returns normalization warnings."""
    all_warnings: list[str] = []
    all_warnings.extend(normalize_profile_contact(profile))
    for edu in profile.get("education") or []:
        period = str(edu.get("period", ""))
        norm, warns = normalize_period(period)
        edu["period"] = norm
        all_warnings.extend(warns)
    ctx = profile.get("application_context")
    if isinstance(ctx, dict):
        start = str(ctx.get("earliest_start", "")).strip()
        if re.match(r"^\d{4}-\d{2}$", start):
            y, mo = start.split("-")
            ctx["earliest_start"] = f"{_pad2(int(mo))}.{y}"
            all_warnings.append(f"Normalized earliest_start → {ctx['earliest_start']!r}")
    return all_warnings


def append_warnings_report(existing: str, warnings: list[str]) -> str:
    if not warnings:
        return existing.strip()
    block = "## ⚠️ Format / missing field warnings\n\n" + "\n".join(
        f"- {w}" for w in warnings
    )
    base = existing.strip()
    return f"{base}\n\n{block}\n" if base else f"{block}\n"


def print_warnings(warnings: list[str], title: str = "Warnings") -> None:
    if not warnings:
        return
    print("\n" + "=" * 60)
    print(f"⚠️  {title}")
    print("=" * 60)
    for w in warnings:
        print(f"  • {w}")
    print("  → Fix in knowledge/ and re-run. Pipeline continued.\n")


def repair_generate_result(result: dict) -> list[str]:
    """Fill recoverable gaps. Returns warnings. Raises only if resume is missing."""
    warnings: list[str] = []

    if "resume" not in result or not isinstance(result.get("resume"), dict):
        raise SystemExit("LLM response missing usable 'resume' object — cannot continue.")

    if "cover_letter" not in result:
        result["cover_letter"] = (
            "<!-- TODO: cover letter missing from LLM output; regenerate or write manually. -->"
        )
        warnings.append("cover_letter was missing — placeholder saved")

    if "match_report" not in result:
        result["match_report"] = "Match report missing from LLM output."
        warnings.append("match_report was missing — placeholder saved")

    resume = result["resume"]
    meta = resume.setdefault("meta", {})
    lang = meta.get("output_language")
    if lang not in ("de", "en"):
        meta["output_language"] = "en"
        warnings.append(f"output_language was {lang!r} — defaulted to 'en'")

    return warnings
