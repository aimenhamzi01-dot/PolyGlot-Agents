#!/usr/bin/env python3
"""Compute a transparent heuristic quality score; it is a triage signal, not a truth metric."""
from __future__ import annotations
import argparse, json, re
from pathlib import Path


def score(row: dict) -> tuple[float, dict[str, float]]:
    text = row["text"].strip(); n = len(text)
    length = min(1.0, n / 400.0)
    alpha = sum(ch.isalpha() for ch in text) / max(1, n)
    words = text.split(); unique = len(set(words)) / max(1, len(words))
    repeated = 1.0 if not re.search(r"(.)\1{5,}", text) else 0.0
    metadata = 1.0 if all(row.get(k) for k in ("source", "source_url", "license", "lang_code")) else 0.0
    components = {"length": round(length, 4), "alphabetic_ratio": round(alpha, 4), "lexical_diversity": round(unique, 4), "repetition": repeated, "provenance": metadata}
    value = 0.20*length + 0.20*alpha + 0.20*unique + 0.10*repeated + 0.30*metadata
    return round(value, 4), components


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__); p.add_argument("--input", required=True, type=Path); p.add_argument("--output", required=True, type=Path); a = p.parse_args()
    count = 0
    with a.input.open(encoding="utf-8") as src, a.output.open("w", encoding="utf-8") as dst:
        for line_no, line in enumerate(src, 1):
            if not line.strip(): continue
            row = json.loads(line)
            if not isinstance(row, dict) or not isinstance(row.get("text"), str): raise ValueError(f"{a.input}:{line_no}: invalid record")
            value, components = score(row); row["quality_score"] = value; row["quality_components"] = components; row.setdefault("human_review_status", "unreviewed")
            dst.write(json.dumps(row, ensure_ascii=False) + "\n"); count += 1
    print(f"scored={count} output={a.output}")

if __name__ == "__main__": main()
