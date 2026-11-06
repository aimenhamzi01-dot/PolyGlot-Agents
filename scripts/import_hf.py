#!/usr/bin/env python3
"""Import an approved Hugging Face instruction dataset into the project record contract.

This importer is deliberately allowlist-oriented: callers must provide a pinned
revision and an adapter name. It never treats a dataset host as proof of rights.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

try:
    from scripts.language_codes import canonical_iso639
except ModuleNotFoundError:
    from language_codes import canonical_iso639

ADAPTERS = {"aya": {"input": "inputs", "output": "targets", "language": "language_code"}}
# Aya uses ``arb`` for Standard Arabic. Keep the source tag in metadata while
# placing it under the project's existing canonical Arabic directory.
SOURCE_LANGUAGE_OVERRIDES = {"arb": "ar"}


def stable_id(source: str, revision: str, row: dict, lang: str) -> str:
    payload = "\0".join((source, revision, lang, str(row.get("inputs", "")), str(row.get("targets", ""))))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_rows(dataset_id: str, revision: str, split: str):
    try:
        from datasets import load_dataset
    except ImportError as exc:
        raise SystemExit("Install dependencies: pip install -r scripts/requirements.txt") from exc
    return load_dataset(dataset_id, split=split, revision=revision, streaming=True)


def import_aya(dataset_id: str, revision: str, split: str, license_name: str,
               license_url: str, dataset_url: str, limit_per_language: int | None = None) -> dict[str, list[dict]]:
    rows_by_lang: dict[str, list[dict]] = {}
    for row in load_rows(dataset_id, revision, split):
        text_in = str(row.get("inputs") or "").strip()
        text_out = str(row.get("targets") or "").strip()
        raw_lang = str(row.get("language_code") or "").strip()
        if not text_in or not text_out or not raw_lang:
            continue
        try:
            lang = SOURCE_LANGUAGE_OVERRIDES.get(raw_lang.lower(), canonical_iso639(raw_lang))
        except (ValueError, RuntimeError):
            continue
        bucket = rows_by_lang.setdefault(lang, [])
        if limit_per_language is not None and len(bucket) >= limit_per_language:
            continue
        bucket.append({
            "id": stable_id(dataset_id, revision, row, lang),
            "text": f"User: {text_in}\nAssistant: {text_out}",
            "messages": [
                {"role": "user", "content": text_in},
                {"role": "assistant", "content": text_out},
            ],
            "lang_code": lang,
            "source_lang_tag": raw_lang,
            "source": dataset_id,
            "source_url": dataset_url,
            "source_record_ids": [],
            "license": license_name,
            "license_url": license_url,
            "source_revision": revision,
            "quality_score": 0.5,
            "quality_basis": "human-annotated source; no numeric source quality score; requires language-specific calibration",
            "human_review_status": "reviewed",
            "human_review_basis": "source dataset documents human annotation; project screening remains required",
            "content_type": "sft",
            "provenance": {
                "source_split": split,
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "synthetic": False,
                "importer": "scripts/import_hf.py",
            },
        })
    return rows_by_lang


def write_groups(groups: dict[str, list[dict]], output_root: Path) -> int:
    total = 0
    for lang, rows in sorted(groups.items()):
        path = output_root / lang / "sft" / "aya.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        total += len(rows)
        print(f"aya\t{lang}\t{len(rows)}\t{path}")
    return total


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-id", required=True)
    parser.add_argument("--revision", required=True, help="Pinned commit hash or tag")
    parser.add_argument("--adapter", choices=sorted(ADAPTERS), required=True)
    parser.add_argument("--split", default="train")
    parser.add_argument("--license", required=True)
    parser.add_argument("--license-url", required=True)
    parser.add_argument("--dataset-url", required=True)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--limit-per-language", type=int)
    args = parser.parse_args()
    if args.limit_per_language is not None and args.limit_per_language < 1:
        parser.error("--limit-per-language must be positive")
    if args.adapter == "aya":
        groups = import_aya(args.dataset_id, args.revision, args.split, args.license,
                             args.license_url, args.dataset_url, args.limit_per_language)
    else:  # pragma: no cover - argparse prevents this branch today
        raise SystemExit(f"No implementation for adapter {args.adapter}")
    print(f"imported={write_groups(groups, args.output_root)} dataset={args.dataset_id} revision={args.revision}")


if __name__ == "__main__":
    main()
