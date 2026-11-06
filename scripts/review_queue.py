#!/usr/bin/env python3
"""Create and apply auditable, reproducible human-review queues for JSONL records."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

DECISIONS = {"reviewed", "rejected", "needs_adjudication"}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSON ({exc.msg})") from exc
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number}: expected an object")
            rows.append(value)
    return rows


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def create_queue(records: list[dict[str, Any]], *, sample_size: int, seed: int = 13, language: str | None = None, rubric_version: str = "v1") -> list[dict[str, Any]]:
    """Select a deterministic sample and emit review work items without reviewer PII."""
    import random

    candidates = [row for row in records if language is None or row.get("lang_code") == language]
    if sample_size < 1:
        raise ValueError("sample_size must be positive")
    if len({row.get("id") for row in candidates}) != len(candidates):
        raise ValueError("candidate records must have unique ids")
    chosen = random.Random(seed).sample(candidates, min(sample_size, len(candidates)))
    queue: list[dict[str, Any]] = []
    for row in chosen:
        record_id = row.get("id")
        if not isinstance(record_id, str) or not record_id:
            raise ValueError("every record in a review queue must have a non-empty id")
        review_id = hashlib.sha256(f"{seed}:{record_id}".encode("utf-8")).hexdigest()[:20]
        queue.append({
            "review_id": review_id,
            "record_id": record_id,
            "lang_code": row.get("lang_code"),
            "rubric_version": rubric_version,
            "status": "pending",
            "record": row,
        })
    return queue


def apply_decisions(records: list[dict[str, Any]], decisions: list[dict[str, Any]], *, rubric_version: str = "v1") -> list[dict[str, Any]]:
    """Apply completed decisions, requiring a reviewer reference and review date."""
    by_id = {row.get("id"): dict(row) for row in records}
    if len(by_id) != len(records) or None in by_id:
        raise ValueError("records must have unique non-empty ids")
    seen_reviews: set[str] = set()
    for decision in decisions:
        review_id = decision.get("review_id")
        record_id = decision.get("record_id")
        status = decision.get("decision") or decision.get("status")
        if not isinstance(review_id, str) or not review_id or review_id in seen_reviews:
            raise ValueError(f"duplicate or missing review_id: {review_id!r}")
        seen_reviews.add(review_id)
        if record_id not in by_id:
            raise ValueError(f"decision references unknown record_id: {record_id!r}")
        if status not in DECISIONS:
            raise ValueError(f"invalid review decision for {record_id!r}: {status!r}")
        reviewer_ref = decision.get("reviewer_ref")
        reviewed_at = decision.get("reviewed_at")
        if not isinstance(reviewer_ref, str) or not reviewer_ref.strip():
            raise ValueError(f"{record_id}: reviewer_ref is required")
        if not isinstance(reviewed_at, str) or not reviewed_at.strip():
            raise ValueError(f"{record_id}: reviewed_at is required")
        if decision.get("rubric_version", rubric_version) != rubric_version:
            raise ValueError(f"{record_id}: rubric version mismatch")
        row = by_id[record_id]
        row["human_review_status"] = status if status != "needs_adjudication" else "unreviewed"
        row["human_review"] = {
            "reviewer_ref": reviewer_ref.strip(),
            "reviewed_at": reviewed_at.strip(),
            "rubric_version": rubric_version,
            "decision": status,
            "notes": decision.get("notes", ""),
        }
    return [by_id[row.get("id")] for row in records]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("create", "apply"), required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--decisions", type=Path, help="JSONL decisions file required in apply mode")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=13)
    parser.add_argument("--sample-size", type=int, default=50)
    parser.add_argument("--language")
    parser.add_argument("--rubric-version", default="v1")
    args = parser.parse_args(argv)
    records = _read_jsonl(args.input)
    if args.mode == "create":
        output = create_queue(records, sample_size=args.sample_size, seed=args.seed, language=args.language, rubric_version=args.rubric_version)
    else:
        if args.decisions is None:
            parser.error("--decisions is required in apply mode")
        output = apply_decisions(records, _read_jsonl(args.decisions), rubric_version=args.rubric_version)
    _write_jsonl(args.output, output)
    print(f"wrote={len(output)} output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
