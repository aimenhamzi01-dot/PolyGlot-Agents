#!/usr/bin/env python3
"""Validate JSONL records against the PolyGlot Agents data contract."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

try:
    from scripts.language_codes import canonical_iso639
except ModuleNotFoundError:  # Support running from a source checkout.
    from language_codes import canonical_iso639

REQUIRED_FIELDS = ("id", "text", "lang_code", "source", "source_url", "license", "quality_score", "human_review_status", "content_type", "provenance")
REVIEW_STATUSES = {"unreviewed", "reviewed", "rejected"}


def validate_record(record: Any, *, source: str = "record", expected_language: str | None = None) -> list[str]:
    """Return actionable errors for one record without mutating it."""
    errors: list[str] = []
    if not isinstance(record, dict):
        return [f"{source}: record must be an object"]

    for field in REQUIRED_FIELDS:
        if field not in record:
            errors.append(f"{source}.{field} is required")

    for field in ("id", "text", "source", "source_url", "license", "content_type"):
        value = record.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{source}.{field} must be a non-empty string")

    language = record.get("lang_code")
    if not isinstance(language, str) or not language.strip():
        errors.append(f"{source}.lang_code must be a non-empty string")
    else:
        try:
            canonical = canonical_iso639(language)
            if canonical != language.lower():
                errors.append(f"{source}.lang_code must be canonical ({canonical!r})")
            if expected_language and canonical != expected_language:
                errors.append(f"{source}.lang_code {canonical!r} disagrees with file language {expected_language!r}")
        except (ValueError, RuntimeError) as exc:
            errors.append(f"{source}.lang_code is invalid: {exc}")

    score = record.get("quality_score")
    if isinstance(score, bool) or not isinstance(score, (int, float)) or not 0 <= score <= 1:
        errors.append(f"{source}.quality_score must be a number in [0, 1]")

    review = record.get("human_review_status")
    if review not in REVIEW_STATUSES:
        errors.append(f"{source}.human_review_status must be one of {sorted(REVIEW_STATUSES)}")

    provenance = record.get("provenance")
    if not isinstance(provenance, dict):
        errors.append(f"{source}.provenance must be an object")
    else:
        retrieved_at = provenance.get("retrieved_at")
        if not isinstance(retrieved_at, str) or not retrieved_at.strip():
            errors.append(f"{source}.provenance.retrieved_at must be a non-empty string")

    return errors


def validate_file(path: Path, *, expected_language: str | None = None) -> list[str]:
    errors: list[str] = []
    try:
        handle = path.open(encoding="utf-8")
    except OSError as exc:
        return [f"{path}: cannot open file ({exc})"]

    with handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                errors.append(f"{path}:{line_number}: invalid JSON ({exc.msg})")
                continue
            errors.extend(validate_record(record, source=f"{path}:{line_number}", expected_language=expected_language))
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, action="append", required=True, help="JSONL file to validate; repeatable")
    parser.add_argument("--language", help="Require one canonical language code for every input record")
    args = parser.parse_args(argv)

    expected_language = None
    if args.language:
        try:
            expected_language = canonical_iso639(args.language)
        except (ValueError, RuntimeError) as exc:
            parser.error(f"invalid --language: {exc}")

    failures = [error for path in args.input for error in validate_file(path, expected_language=expected_language)]
    if failures:
        print("Record validation failed:", file=sys.stderr)
        print("\n".join(f"- {failure}" for failure in failures), file=sys.stderr)
        return 1
    print(f"Validated {len(args.input)} JSONL file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
