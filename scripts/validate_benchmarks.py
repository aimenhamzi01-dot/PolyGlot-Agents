#!/usr/bin/env python3
"""Validate public and protected benchmark task-card contracts."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from environments.customer_service_agent import SCENARIO_GOALS, SCENARIO_IDS, load_locale
except ModuleNotFoundError:  # Support running the script from a source checkout.
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from environments.customer_service_agent import SCENARIO_GOALS, SCENARIO_IDS, load_locale


ACTIVE_CUSTOMER_SERVICE_ENVIRONMENTS = {
    "PolyGlotCustomerService-v1",
    "PolyGlotCustomerServiceAr-v1",
}
REQUIRED_TASK_STRINGS = ("id", "scenario_id", "goal", "success_condition")
ALLOWED_OUTCOMES = {"status", "refund", "decline", "already_refunded", "handoff"}


def validate_payload(
    payload: Any,
    source: str = "benchmark",
    *,
    allow_hidden: bool = False,
) -> list[str]:
    """Return actionable validation errors for one decoded benchmark payload.

    Public benchmark files reject hidden task contents. A separate protected file
    may be checked with ``allow_hidden=True``; in that mode every authored task
    must explicitly belong to the hidden split.
    """
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
    scenario_ids: set[str] = set()
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

        if "customer_prompt" in task and "customer_prompts" in task:
            errors.append(f"{label} must use either customer_prompt or customer_prompts, not both")
        prompt = task.get("customer_prompt")
        if prompt is not None and (
            not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 500
        ):
            errors.append(f"{label}.customer_prompt must be a non-empty string of at most 500 characters")
        prompts = task.get("customer_prompts")
        if prompts is not None:
            if not isinstance(prompts, dict) or not prompts:
                errors.append(f"{label}.customer_prompts must be a non-empty object keyed by supported locale")
            else:
                for locale, customer_prompt in prompts.items():
                    if not isinstance(locale, str) or not locale.strip():
                        errors.append(f"{label}.customer_prompts keys must be non-empty locale codes")
                        continue
                    try:
                        load_locale(locale)
                    except (ValueError, OSError):
                        errors.append(f"{label}.customer_prompts contains unsupported locale {locale!r}")
                    if (
                        not isinstance(customer_prompt, str)
                        or not customer_prompt.strip()
                        or len(customer_prompt) > 500
                    ):
                        errors.append(
                            f"{label}.customer_prompts[{locale!r}] must be a non-empty string of at most 500 characters"
                        )

        task_id = task.get("id")
        if isinstance(task_id, str) and task_id.strip():
            if task_id in task_ids:
                errors.append(f"{label}.id duplicates task id {task_id!r}")
            task_ids.add(task_id)

        split = task.get("split", "development")
        if not isinstance(split, str) or split not in {"development", "hidden"}:
            errors.append(f"{label}.split must be 'development' or 'hidden'")
        elif split == "hidden" and not allow_hidden:
            errors.append(
                f"{label} contains hidden test data in a public benchmark; "
                "move it to a protected file outside the repository"
            )
        elif allow_hidden and split != "hidden":
            errors.append(f"{label} in a protected benchmark must have split='hidden'")

        if check_scenarios:
            scenario_id = task.get("scenario_id")
            if isinstance(scenario_id, str) and scenario_id not in known_scenarios:
                errors.append(
                    f"{label}.scenario_id references unknown customer-service "
                    f"scenario {scenario_id!r}"
                )
            if isinstance(scenario_id, str) and scenario_id.strip():
                if scenario_id in scenario_ids:
                    errors.append(f"{label}.scenario_id duplicates scenario {scenario_id!r}")
                scenario_ids.add(scenario_id)
            expected_outcome = task.get("expected_outcome")
            if not isinstance(expected_outcome, str) or expected_outcome not in ALLOWED_OUTCOMES:
                errors.append(
                    f"{label}.expected_outcome must be one of "
                    f"{', '.join(sorted(ALLOWED_OUTCOMES))}"
                )
            elif isinstance(scenario_id, str) and scenario_id in SCENARIO_GOALS:
                actual_goal = SCENARIO_GOALS[scenario_id]
                if expected_outcome != actual_goal:
                    errors.append(
                        f"{label}.expected_outcome={expected_outcome!r} does not match "
                        f"scenario {scenario_id!r} goal {actual_goal!r}"
                    )

        safety_checks = task.get("safety_checks")
        if not isinstance(safety_checks, list) or not safety_checks or any(
            not isinstance(check, str) or not check.strip() for check in safety_checks
        ):
            errors.append(f"{label}.safety_checks must be a non-empty array of non-empty strings")

    declared_count = payload.get("scenario_count")
    if declared_count is not None and (type(declared_count) is not int or declared_count != len(tasks)):
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


def validate_file(path: Path, *, allow_hidden: bool = False) -> list[str]:
    """Read and validate one UTF-8 JSON benchmark file."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return [f"{path}: cannot read valid UTF-8 JSON ({exc})"]
    return validate_payload(payload, str(path), allow_hidden=allow_hidden)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--benchmark",
        type=Path,
        action="append",
        help="public benchmark JSON file to validate (repeatable; defaults to evaluation/benchmarks/*.json)",
    )
    parser.add_argument(
        "--protected-benchmark",
        type=Path,
        action="append",
        default=[],
        help="separate protected file containing only hidden tasks; never commit it",
    )
    args = parser.parse_args()
    default_dir = Path(__file__).resolve().parents[1] / "evaluation" / "benchmarks"
    public_paths = args.benchmark or sorted(default_dir.glob("*.json"))
    if not public_paths and not args.protected_benchmark:
        parser.error("no benchmark JSON files found")

    failures = [error for path in public_paths for error in validate_file(path)]
    failures.extend(
        error
        for path in args.protected_benchmark
        for error in validate_file(path, allow_hidden=True)
    )
    if failures:
        print("Benchmark validation failed:")
        for failure in failures:
            print(f"- {failure}")
        raise SystemExit(1)

    print(
        f"Validated {len(public_paths)} public and "
        f"{len(args.protected_benchmark)} protected benchmark file(s)."
    )


if __name__ == "__main__":
    main()
