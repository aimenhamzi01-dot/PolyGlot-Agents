#!/usr/bin/env python3
"""Validate benchmark task-card files before evaluation or contribution."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from environments.customer_service_agent import SCENARIO_IDS
except ModuleNotFoundError:  # Support running the script from a source checkout.
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from environments.customer_service_agent import SCENARIO_IDS


ACTIVE_CUSTOMER_SERVICE_ENVIRONMENTS = {
    "PolyGlotCustomerService-v1",
    "PolyGlotCustomerServiceAr-v1",
}
REQUIRED_TASK_STRINGS = ("id", "scenario_id", "goal", "success_condition")


def validate_payload(payload: Any, source: str = "benchmark") -> list[str]:
    """Return actionable validation errors for one decoded benchmark payload."""
    errors: list[str] = []
    if not isinstance(payload, dict):
        return [f"{source}: root must be a JSON object"]

    for field in ("benchmark_id", "language"):
        if not isinstance(payload.get(field), str) or not payload[field].strip():
            errors.append(f"{source}: {field} must be a non-empty string")

    tasks = payload.get("tasks")
    if not isinstance(tasks, list):
        return errors + [f"{source}: tasks must be an array"]

    if not tasks and payload.get("status") != "requires_native_speaker_authoring":
        errors.append(
            f"{source}: an empty tasks array must declare "
            "status='requires_native_speaker_authoring'"
        )
    if tasks and payload.get("status") == "requires_native_speaker_authoring":
        errors.append(f"{source}: authored tasks cannot retain the placeholder status")

    task_ids: set[str] = set()
    known_scenarios = set(SCENARIO_IDS)
    environment = payload.get("environment")
    check_scenarios = environment in ACTIVE_CUSTOMER_SERVICE_ENVIRONMENTS

    for index, task in enumerate(tasks):
        label = f"{source}: tasks[{index}]"
        if not isinstance(task, dict):
            errors.append(f"{label} must be an object")
            continue

        for field in REQUIRED_TASK_STRINGS:
            value = task.get(field)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{label}.{field} must be a non-empty string")

        task_id = task.get("id")
        if isinstance(task_id, str) and task_id.strip():
            if task_id in task_ids:
                errors.append(f"{label}.id duplicates task id {task_id!r}")
            task_ids.add(task_id)

        if check_scenarios:
            scenario_id = task.get("scenario_id")
            if isinstance(scenario_id, str) and scenario_id not in known_scenarios:
                errors.append(
                    f"{label}.scenario_id references unknown customer-service "
                    f"scenario {scenario_id!r}"
                )

        if "split" in task and task["split"] not in {"development", "hidden"}:
            errors.append(f"{label}.split must be 'development' or 'hidden'")

        safety_checks = task.get("safety_checks")
        if not isinstance(safety_checks, list) or not safety_checks or any(
            not isinstance(check, str) or not check.strip() for check in safety_checks
        ):
            errors.append(f"{label}.safety_checks must be a non-empty array of non-empty strings")

    declared_count = payload.get("scenario_count")
    if declared_count is not None and declared_count != len(tasks):
        errors.append(
            f"{source}: scenario_count is {declared_count!r}, but tasks contains {len(tasks)} entries"
        )

    metrics = payload.get("metrics")
    if metrics is not None and (
        not isinstance(metrics, list)
        or any(not isinstance(metric, str) or not metric.strip() for metric in metrics)
    ):
        errors.append(f"{source}: metrics must be an array of non-empty strings")

    return errors


def validate_file(path: Path) -> list[str]:
    """Read and validate one UTF-8 JSON benchmark file."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return [f"{path}: cannot read valid UTF-8 JSON ({exc})"]
    return validate_payload(payload, str(path))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--benchmark",
        type=Path,
        action="append",
        help="benchmark JSON file to validate (repeatable; defaults to all files under evaluation/benchmarks)",
    )
    args = parser.parse_args()
    default_dir = Path(__file__).resolve().parents[1] / "evaluation" / "benchmarks"
    paths = args.benchmark or sorted(default_dir.glob("*.json"))
    if not paths:
        parser.error("no benchmark JSON files found")

    failures = [error for path in paths for error in validate_file(path)]
    if failures:
        print("Benchmark validation failed:")
        for failure in failures:
            print(f"- {failure}")
        raise SystemExit(1)

    print(f"Validated {len(paths)} benchmark file(s); schemas and scenario references are consistent.")


if __name__ == "__main__":
    main()
