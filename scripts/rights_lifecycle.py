#!/usr/bin/env python3
"""Build provenance manifests and non-destructive quarantine outputs for JSONL data."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


def _digest(record: dict[str, Any]) -> str:
    payload = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _iter_records(root: Path) -> Iterable[tuple[Path, int, dict[str, Any]]]:
    for path in sorted(root.rglob("*.jsonl")) if root.is_dir() else [root]:
        with path.open(encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"{path}:{line_number}: invalid JSON ({exc.msg})") from exc
                if not isinstance(record, dict):
                    raise ValueError(f"{path}:{line_number}: record must be an object")
                yield path, line_number, record


def build_manifest(root: Path) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    sources: dict[str, dict[str, Any]] = {}
    for path, line_number, record in _iter_records(root):
        record_id = record.get("id")
        if not isinstance(record_id, str) or not record_id:
            raise ValueError(f"{path}:{line_number}: record id is required")
        source = str(record.get("source", "unknown"))
        entry = {
            "record_id": record_id,
            "source": source,
            "source_url": record.get("source_url"),
            "record_sha256": _digest(record),
            "file": str(path),
            "line": line_number,
        }
        records.append(entry)
        source_entry = sources.setdefault(source, {"records": 0, "record_ids": []})
        source_entry["records"] += 1
        source_entry["record_ids"].append(record_id)
    return {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "records": records,
        "sources": sources,
        "record_count": len(records),
    }


def quarantine(root: Path, output: Path, *, record_ids: set[str], sources: set[str], reason: str) -> dict[str, int]:
    """Write a filtered copy and a tombstone log; never mutate the input root."""
    if not record_ids and not sources:
        raise ValueError("provide at least one record id or source")
    kept = removed = 0
    tombstones: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*.jsonl")):
        relative = path.relative_to(root)
        destination = output / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        with path.open(encoding="utf-8") as source_handle, destination.open("w", encoding="utf-8") as destination_handle:
            for line_number, line in enumerate(source_handle, 1):
                if not line.strip():
                    continue
                record = json.loads(line)
                if not isinstance(record, dict):
                    raise ValueError(f"{path}:{line_number}: record must be an object")
                record_id = record.get("id")
                source_name = record.get("source")
                if record_id in record_ids or source_name in sources:
                    removed += 1
                    tombstones.append({
                        "record_id": record_id,
                        "source": source_name,
                        "original_file": str(relative),
                        "original_line": line_number,
                        "record_sha256": _digest(record),
                        "reason": reason,
                    })
                else:
                    destination_handle.write(json.dumps(record, ensure_ascii=False) + "\n")
                    kept += 1
    output.mkdir(parents=True, exist_ok=True)
    tombstone_path = output / "deletion_manifest.jsonl"
    with tombstone_path.open("w", encoding="utf-8") as handle:
        for tombstone in tombstones:
            handle.write(json.dumps(tombstone, ensure_ascii=False, sort_keys=True) + "\n")
    return {"kept": kept, "removed": removed, "tombstones": len(tombstones)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("manifest", "quarantine"), required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--record-id", action="append", default=[])
    parser.add_argument("--source", action="append", default=[])
    parser.add_argument("--reason", default="rights_request")
    args = parser.parse_args(argv)
    if args.mode == "manifest":
        manifest = build_manifest(args.input)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"records": manifest["record_count"], "output": str(args.output)}))
    else:
        summary = quarantine(args.input, args.output, record_ids=set(args.record_id), sources=set(args.source), reason=args.reason)
        print(json.dumps({**summary, "output": str(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
