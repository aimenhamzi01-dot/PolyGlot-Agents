#!/usr/bin/env python3
"""Build a reproducible release manifest for a benchmark and its evaluator."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def build_manifest(benchmark: Path, *, report: Path | None = None, repository_root: Path | None = None) -> dict[str, Any]:
    root = repository_root or Path(__file__).resolve().parents[1]
    benchmark_payload = json.loads(benchmark.read_text(encoding="utf-8"))
    if not isinstance(benchmark_payload, dict):
        raise ValueError("benchmark must contain a JSON object")
    files = [benchmark, root / "evaluation" / "run_benchmark.py", root / "evaluation" / "compare_reports.py", root / "environments" / "customer_service_agent" / "__init__.py", root / "environments" / "customer_service_agent" / "policy.py", root / "configs" / "environment.yaml"]
    missing = [str(path) for path in files if not path.exists()]
    if missing:
        raise ValueError("release files are missing: " + ", ".join(missing))
    report_payload: dict[str, Any] | None = None
    if report:
        report_payload = json.loads(report.read_text(encoding="utf-8"))
        if not isinstance(report_payload, dict) or not isinstance(report_payload.get("aggregate"), dict):
            raise ValueError("report must contain an aggregate object")
        expected_sha = report_payload.get("benchmark_sha256")
        if expected_sha != sha256(benchmark):
            raise ValueError("report benchmark_sha256 does not match benchmark file")
        files.append(report)
    unique_files = []
    seen: set[Path] = set()
    for path in files:
        resolved = path.resolve()
        if resolved not in seen:
            seen.add(resolved)
            unique_files.append(resolved)
    def manifest_path(path: Path) -> str:
        try:
            return str(path.relative_to(root))
        except ValueError:
            return f"external:{path.name}"
    return {
        "manifest_schema_version": 1,
        "release_id": f"{benchmark_payload.get('benchmark_id', 'benchmark')}@{benchmark_payload.get('benchmark_version', 'unversioned')}",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "benchmark_id": benchmark_payload.get("benchmark_id"),
        "benchmark_version": benchmark_payload.get("benchmark_version"),
        "language": benchmark_payload.get("language"),
        "benchmark_review_status": benchmark_payload.get("human_review_status", "unknown"),
        "hidden_test_status": "not_provisioned" if not report_payload or report_payload.get("split") == "development" else "external_protected_file",
        "files": [
            {"path": manifest_path(path), "sha256": sha256(path)}
            for path in unique_files
        ],
        "report_aggregate": report_payload.get("aggregate") if report_payload else None,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        manifest = build_manifest(args.benchmark, report=args.report)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        parser.error(str(exc))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "release_id": manifest["release_id"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
