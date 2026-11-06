#!/usr/bin/env python3
"""Filter malformed/low-signal JSONL with language-specific thresholds and a reject report."""
from __future__ import annotations
import argparse, json, re
from pathlib import Path
try:
    from scripts.language_codes import canonical_iso639
except ModuleNotFoundError:
    from language_codes import canonical_iso639

EMAIL = re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b")
PHONE = re.compile(r"(?<!\w)(?:\+?\d[\d ()-]{7,}\d)(?!\w)")
REQUIRED = ("source", "license", "lang_code")
DEFAULT_CONFIG = Path("configs/pipeline.yaml")


def screen(row: dict, min_chars: int | None = None, max_chars: int | None = None,
           strip_contacts: bool = True, language_profiles: dict | None = None,
           default_min_chars: int = 40, default_max_chars: int = 20000) -> tuple[dict | None, str | None]:
    if not isinstance(row, dict): return None, "not_object"
    if row.get("routing_status") == "needs_review" or row.get("language_conflict") is True:
        return None, "language_requires_review"
    text = row.get("text")
    if not isinstance(text, str): return None, "missing_text"
    text = " ".join(text.split())
    missing = [key for key in REQUIRED if not row.get(key)]
    if missing: return None, "missing_metadata:" + ",".join(missing)
    try:
        raw_lang = row["lang_code"]
        canonical_lang = canonical_iso639(raw_lang)
    except (ValueError, RuntimeError):
        return None, "invalid_iso639_language_code"
    if str(raw_lang).lower() != canonical_lang:
        row = dict(row)
        row.setdefault("source_lang_tag", raw_lang)
    row["lang_code"] = canonical_lang
    profile = (language_profiles or {}).get(canonical_lang, {})
    low = min_chars if min_chars is not None else profile.get("min_characters", default_min_chars)
    high = max_chars if max_chars is not None else profile.get("max_characters", default_max_chars)
    if len(text) < low: return None, "too_short"
    if len(text) > high: return None, "too_long"
    if strip_contacts:
        text = EMAIL.sub("[EMAIL_REDACTED]", text)
        text = PHONE.sub("[PHONE_REDACTED]", text)
    if len(set(text)) <= 3: return None, "low_character_diversity"
    result = dict(row); result["text"] = text
    return result, None


def load_config(path: Path) -> dict:
    try:
        import yaml
    except ImportError as exc:
        raise SystemExit("Install requirements first: pip install -r scripts/requirements.txt") from exc
    if not path.exists(): raise FileNotFoundError(f"Pipeline config not found: {path}")
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", required=True, type=Path); p.add_argument("--output", required=True, type=Path)
    p.add_argument("--rejects", type=Path); p.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    p.add_argument("--min-chars", type=int); p.add_argument("--max-chars", type=int)
    p.add_argument("--keep-contact-patterns", action="store_true")
    a = p.parse_args(); config = load_config(a.config)
    reject_path = a.rejects or a.output.with_suffix(a.output.suffix + ".rejects.jsonl")
    kept = rejected = 0
    with a.input.open(encoding="utf-8") as src, a.output.open("w", encoding="utf-8") as dst, reject_path.open("w", encoding="utf-8") as rej:
        for line_no, line in enumerate(src, 1):
            if not line.strip(): continue
            try: row = json.loads(line)
            except json.JSONDecodeError as exc: row = None; reason = f"invalid_json:{exc.msg}"
            else:
                row, reason = screen(row, a.min_chars, a.max_chars, not a.keep_contact_patterns,
                                     config.get("language_profiles", {}), config.get("min_characters", 40),
                                     config.get("max_characters", 20000))
            if row is not None:
                dst.write(json.dumps(row, ensure_ascii=False) + "\n"); kept += 1
            else:
                rej.write(json.dumps({"line": line_no, "reason": reason}, ensure_ascii=False) + "\n"); rejected += 1
    print(f"kept={kept} rejected={rejected} rejects={reject_path}")

if __name__ == "__main__": main()
