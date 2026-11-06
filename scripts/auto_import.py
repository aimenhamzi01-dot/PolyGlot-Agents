#!/usr/bin/env python3
"""Run the approved, pinned multilingual data import pipeline.

The command writes to an isolated run directory by default. It never promotes
records directly into the curated dataset; review the manifest and rejects first.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

try:
    from scripts.deduplicate import fingerprint
    from scripts.filter_data import screen
    from scripts.import_hf import import_aya
    from scripts.import_oasst import make_records
except ModuleNotFoundError:
    from deduplicate import fingerprint
    from filter_data import screen
    from import_hf import import_aya
    from import_oasst import make_records

DEFAULT_CONFIG = Path("configs/sources.yaml")


def load_sources(path: Path) -> dict:
    try:
        import yaml
    except ImportError as exc:
        raise SystemExit("Install dependencies: pip install -r scripts/requirements.txt") from exc
    return yaml.safe_load(path.read_text(encoding="utf-8")).get("sources", {})


def run_id(source_names: list[str], revisions: list[str]) -> str:
    payload = "|".join(source_names + revisions)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{stamp}-{hashlib.sha256(payload.encode()).hexdigest()[:10]}"


def source_rows(name: str, cfg: dict, limit: int | None) -> dict[str, list[dict]]:
    kind = cfg.get("kind")
    if kind == "oasst1":
        by_tag: dict[str, dict] = defaultdict(dict)
        for row in __import__("scripts.import_oasst", fromlist=["load_source"]).load_source():
            tag = row.get("lang")
            if tag and row.get("role") in ("prompter", "assistant"):
                by_tag[tag][row["message_id"]] = dict(row)
        groups: dict[str, list[dict]] = {}
        for tag, messages in sorted(by_tag.items()):
            records = make_records(messages, tag)
            if limit is not None:
                records = sorted(records, key=lambda r: (float(r["quality_score"]), r["id"]), reverse=True)[:limit]
            if records:
                groups.setdefault(records[0]["lang_code"], []).extend(records)
        return groups
    if kind == "aya":
        return import_aya(
            cfg["dataset_id"], cfg["revision"], cfg.get("split", "train"),
            cfg["license"], cfg["license_url"], cfg["dataset_card"], limit,
        )
    raise ValueError(f"Unsupported source kind for {name}: {kind}")


def screen_and_write(groups: dict[str, list[dict]], root: Path, config: dict) -> tuple[Counter, Counter]:
    kept_by_lang: Counter = Counter()
    rejected_by_reason: Counter = Counter()
    seen: set[str] = set()
    for lang, rows in sorted(groups.items()):
        output = root / "curated" / lang / "sft" / "auto_import.jsonl"
        rejects = root / "reports" / f"{lang}.rejects.jsonl"
        duplicates = root / "reports" / f"{lang}.duplicates.jsonl"
        output.parent.mkdir(parents=True, exist_ok=True)
        rejects.parent.mkdir(parents=True, exist_ok=True)
        with output.open("w", encoding="utf-8") as dst, rejects.open("w", encoding="utf-8") as rej, duplicates.open("w", encoding="utf-8") as dup:
            for index, row in enumerate(rows, 1):
                clean, reason = screen(
                    row,
                    language_profiles=config.get("language_profiles", {}),
                    default_min_chars=config.get("min_characters", 40),
                    default_max_chars=config.get("max_characters", 20000),
                )
                if clean is None:
                    rejected_by_reason[reason] += 1
                    rej.write(json.dumps({"line": index, "reason": reason, "id": row.get("id")}, ensure_ascii=False) + "\n")
                    continue
                key = fingerprint(clean["lang_code"], clean["text"])
                if key in seen:
                    rejected_by_reason["duplicate"] += 1
                    dup.write(json.dumps({"line": index, "id": clean.get("id"), "duplicate_of_hash": key}, ensure_ascii=False) + "\n")
                    continue
                seen.add(key)
                dst.write(json.dumps(clean, ensure_ascii=False) + "\n")
                kept_by_lang[lang] += 1
    return kept_by_lang, rejected_by_reason


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-root", type=Path, default=Path("datasets/incoming"))
    parser.add_argument("--source", action="append", dest="sources", help="Repeat to select named source; default is all enabled sources")
    parser.add_argument("--limit-per-language", type=int, help="Safety limit for each source and language")
    parser.add_argument("--keep-run", action="store_true", help="Do not replace an existing run directory")
    args = parser.parse_args()
    if args.limit_per_language is not None and args.limit_per_language < 1:
        parser.error("--limit-per-language must be positive")
    source_cfg = load_sources(args.config)
    selected = args.sources or [name for name, cfg in source_cfg.items() if cfg.get("enabled", False)]
    unknown = sorted(set(selected) - set(source_cfg))
    if unknown:
        parser.error("unknown source(s): " + ", ".join(unknown))
    disabled = [name for name in selected if not source_cfg[name].get("enabled", False)]
    if disabled:
        parser.error("source(s) are disabled in config: " + ", ".join(disabled))
    revisions = [str(source_cfg[name].get("revision", "")) for name in selected]
    run = run_id(selected, revisions)
    root = args.output_root / run
    if root.exists() and not args.keep_run:
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)
    groups: dict[str, list[dict]] = defaultdict(list)
    source_manifest = []
    for name in selected:
        cfg = source_cfg[name]
        if not cfg.get("revision"):
            raise SystemExit(f"{name}: pinned revision is required for reproducible imports")
        imported = source_rows(name, cfg, args.limit_per_language)
        source_manifest.append({"name": name, "dataset_id": cfg.get("dataset_id"), "revision": cfg["revision"], "records": sum(map(len, imported.values()))})
        for lang, rows in imported.items():
            groups[lang].extend(rows)
    pipeline_config = load_sources(Path("configs/sources.yaml"))  # source config is also the audit manifest input
    kept, rejected = screen_and_write(groups, root, {"min_characters": 40, "max_characters": 20000, "language_profiles": {}})
    manifest = {
        "schema_version": 1,
        "run_id": run,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "sources": source_manifest,
        "policy": {"default_destination": "datasets/incoming", "requires_manual_review_before_promotion": True, "raw_data_not_committed": True},
        "kept_by_language": dict(kept),
        "rejected_by_reason": dict(rejected),
    }
    (root / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
