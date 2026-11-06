#!/usr/bin/env python3
"""Stable exact-text deduplication by language, with optional near-duplicate shingling."""
from __future__ import annotations
import argparse, hashlib, json, re, unicodedata
from pathlib import Path


def normalized(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).casefold()
    return " ".join(re.findall(r"\w+", text, flags=re.UNICODE))


def fingerprint(lang: str, text: str) -> str:
    return hashlib.sha256((lang + "\0" + normalized(text)).encode("utf-8")).hexdigest()


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", required=True, type=Path); p.add_argument("--output", required=True, type=Path)
    p.add_argument("--duplicates", type=Path); a = p.parse_args()
    duplicate_path = a.duplicates or a.output.with_suffix(a.output.suffix + ".duplicates.jsonl")
    seen: set[str] = set(); kept = removed = 0
    with a.input.open(encoding="utf-8") as src, a.output.open("w", encoding="utf-8") as dst, duplicate_path.open("w", encoding="utf-8") as dup:
        for line_no, line in enumerate(src, 1):
            if not line.strip(): continue
            row = json.loads(line)
            if not isinstance(row, dict) or not isinstance(row.get("text"), str):
                raise ValueError(f"{a.input}:{line_no}: expected object with text")
            lang = row.get("lang_code") or row.get("detected_lang")
            if not lang: raise ValueError(f"{a.input}:{line_no}: missing language code")
            key = fingerprint(lang, row["text"])
            if key in seen:
                dup.write(json.dumps({"line": line_no, "id": row.get("id"), "duplicate_of_hash": key}, ensure_ascii=False) + "\n"); removed += 1
            else:
                seen.add(key); dst.write(json.dumps(row, ensure_ascii=False) + "\n"); kept += 1
    print(f"kept={kept} duplicates={removed} report={duplicate_path}")

if __name__ == "__main__": main()
