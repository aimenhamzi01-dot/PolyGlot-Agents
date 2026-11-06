#!/usr/bin/env python3
"""Filter malformed/low-signal JSONL and common contact identifiers; write a reject report."""
from __future__ import annotations
import argparse, json, re
from pathlib import Path

EMAIL = re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b")
PHONE = re.compile(r"(?<!\w)(?:\+?\d[\d ()-]{7,}\d)(?!\w)")
REQUIRED = ("source", "license", "lang_code")


def screen(row: dict, min_chars: int = 40, max_chars: int = 20000, strip_contacts: bool = True) -> tuple[dict | None, str | None]:
    text = row.get("text")
    if not isinstance(text, str): return None, "missing_text"
    text = " ".join(text.split())
    if len(text) < min_chars: return None, "too_short"
    if len(text) > max_chars: return None, "too_long"
    missing = [key for key in REQUIRED if not row.get(key)]
    if missing: return None, "missing_metadata:" + ",".join(missing)
    if strip_contacts:
        text = EMAIL.sub("[EMAIL_REDACTED]", text)
        text = PHONE.sub("[PHONE_REDACTED]", text)
    if len(set(text)) <= 3: return None, "low_character_diversity"
    result = dict(row); result["text"] = text
    return result, None


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", required=True, type=Path); p.add_argument("--output", required=True, type=Path)
    p.add_argument("--rejects", type=Path); p.add_argument("--min-chars", type=int, default=40); p.add_argument("--max-chars", type=int, default=20000)
    p.add_argument("--keep-contact-patterns", action="store_true")
    a = p.parse_args(); reject_path = a.rejects or a.output.with_suffix(a.output.suffix + ".rejects.jsonl")
    kept = rejected = 0
    with a.input.open(encoding="utf-8") as src, a.output.open("w", encoding="utf-8") as dst, reject_path.open("w", encoding="utf-8") as rej:
        for line_no, line in enumerate(src, 1):
            if not line.strip(): continue
            try: row = json.loads(line)
            except json.JSONDecodeError as exc: row = None; reason = f"invalid_json:{exc.msg}"
            else:
                if not isinstance(row, dict): row = None; reason = "not_object"
                else: row, reason = screen(row, a.min_chars, a.max_chars, not a.keep_contact_patterns)
            if row is not None:
                dst.write(json.dumps(row, ensure_ascii=False) + "\n"); kept += 1
            else:
                rej.write(json.dumps({"line": line_no, "reason": reason}, ensure_ascii=False) + "\n"); rejected += 1
    print(f"kept={kept} rejected={rejected} rejects={reject_path}")

if __name__ == "__main__": main()
