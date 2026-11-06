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
    from scripts.rights_engine import RightsError, validate_record, validate_source
    from scripts.language_registry import enrich_record, load_registry
except ModuleNotFoundError:
    from deduplicate import fingerprint
    from filter_data import screen
    from import_hf import import_aya
    from import_oasst import make_records
    from rights_engine import RightsError, validate_record, validate_source
    from language_registry import enrich_record, load_registry

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


def json_digest(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


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
    parser.add_argument("--language-registry", type=Path, default=Path("configs/languages.yaml"))
    parser.add_argument("--output-root", type=Path, default=Path("datasets/incoming"))
    parser.add_argument("--source", action="append", dest="sources", help="Repeat to select named source; default is all enabled sources")
    parser.add_argument("--limit-per-language", type=int, help="Safety limit for each source and language")
    parser.add_argument("--keep-run", action="store_true", help="Do not replace an existing run directory")
    parser.add_argument("--validate-only", action="store_true", help="Validate source rights metadata without downloading data")
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
    try:
        for name in selected:
            validate_source(name, source_cfg[name])
    except RightsError as exc:
        parser.error(str(exc))
    if args.validate_only:
        print(json.dumps({"valid": True, "sources": selected}, ensure_ascii=False, indent=2))
        return
    revisions = [str(source_cfg[name].get("revision", "")) for name in selected]
    run = run_id(selected, revisions)
    root = args.output_root / run
    if root.exists() and not args.keep_run:
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)
    groups: dict[str, list[dict]] = defaultdict(list)
    source_manifest = []
    language_registry = load_registry(args.language_registry)
    for name in selected:
        cfg = source_cfg[name]
        if not cfg.get("revision"):
            raise SystemExit(f"{name}: pinned revision is required for reproducible imports")
        imported = source_rows(name, cfg, args.limit_per_language)
        imported_rows = [enrich_record(row, language_registry) for rows in imported.values() for row in rows]
        imported = defaultdict(list)
        for row in imported_rows:
            imported[row["lang_code"]].append(row)
        try:
            for row in imported_rows:
                validate_record(row)
        except RightsError as exc:
            raise SystemExit(str(exc)) from exc
        source_manifest.append({
            "name": name,
            "dataset_id": cfg.get("dataset_id"),
            "revision": cfg["revision"],
            "license": cfg["license"],
            "license_url": cfg["license_url"],
            "rights_status": cfg["rights_status"],
            "allowed_uses": cfg["allowed_uses"],
            "commercial_use": cfg["commercial_use"],
            "records": len(imported_rows),
            "content_sha256": json_digest(imported_rows),
        })
        for lang, rows in imported.items():
            groups[lang].extend(rows)
    kept, rejected = screen_and_write(groups, root, {"min_characters": 40, "max_characters": 20000, "language_profiles": {}})
    manifest = {
        "schema_version": 2,
        "run_id": run,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "sources": source_manifest,
        "policy": {"default_destination": "datasets/incoming", "requires_manual_review_before_promotion": True, "raw_data_not_committed": True, "rights_gate": "fail_closed"},
        "kept_by_language": dict(kept),
        "rejected_by_reason": dict(rejected),
    }
    (root / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
