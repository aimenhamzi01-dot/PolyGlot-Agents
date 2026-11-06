#!/usr/bin/env python3
"""Compare auditable benchmark reports without collapsing quality into one score."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re
from typing import Any

PROTOCOL_FIELDS = (
    "schema_version",
    "benchmark_id",
    "benchmark_version",
    "benchmark_sha256",
    "environment_sha256",
    "evaluator_sha256",
    "benchmark_review_status",
    "language",
    "locale",
    "split",
    "seed",
    "step_budget",
    "concurrency",
)
METRIC_LABELS = {
    "tasks": "Tasks",
    "success_rate": "Success rate",
    "safe_completion_rate": "Safe completion",
    "outcome_match_rate": "Outcome alignment",
    "unsafe_action_rate": "Unsafe-action rate",
    "tool_error_recovery_rate": "Tool-error recovery",
    "unsupported_claim_rate": "Unsupported-claim rate",
    "agent_action_error_rate": "Action error rate",
    "p95_agent_action_latency_ms": "p95 latency (ms)",
    "p99_agent_action_latency_ms": "p99 latency (ms)",
    "agent_actions_per_second": "Actions/second",
    "estimated_cost_per_successful_task": "Cost/successful task",
}
LOWER_IS_BETTER = {
    "unsafe_action_rate",
    "unsupported_claim_rate",
    "agent_action_error_rate",
    "p95_agent_action_latency_ms",
    "p99_agent_action_latency_ms",
    "estimated_cost_per_successful_task",
}
RATE_METRICS = {
    "success_rate",
    "safe_completion_rate",
    "outcome_match_rate",
    "unsafe_action_rate",
    "tool_error_recovery_rate",
    "unsupported_claim_rate",
    "agent_action_error_rate",
}


class ComparisonError(ValueError):
    """Raised when reports are incomplete or not directly comparable."""


def load_report_spec(spec: str) -> tuple[str, dict[str, Any]]:
    label, separator, raw_path = spec.partition("=")
    label = label.strip()
    raw_path = raw_path.strip()
    if not separator or not label or not raw_path:
        raise ComparisonError("each --report must use LABEL=PATH")
    path = Path(raw_path)
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ComparisonError(f"cannot read report {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ComparisonError(f"report is not valid JSON: {path}") from exc
    if not isinstance(report, dict):
        raise ComparisonError(f"report root must be a JSON object: {path}")
    return label, report


def _validate_named_reports(named_reports: list[tuple[str, dict[str, Any]]]) -> tuple[dict[str, Any], str | None]:
    if len(named_reports) < 2:
        raise ComparisonError("provide at least two reports")
    labels = [label.strip() for label, _ in named_reports]
    if any(not label for label in labels):
        raise ComparisonError("report labels cannot be empty")
    if len(set(labels)) != len(labels):
        raise ComparisonError("report labels must be unique")

    reference_label, reference = named_reports[0]
    for field in PROTOCOL_FIELDS:
        if field not in reference or reference[field] in (None, ""):
            raise ComparisonError(f"report {reference_label!r} is missing protocol field {field!r}")
    if type(reference["schema_version"]) is not int or reference["schema_version"] != 2:
        raise ComparisonError(f"unsupported report schema_version: {reference['schema_version']!r}")
    if not isinstance(reference["benchmark_review_status"], str) or not reference["benchmark_review_status"].strip():
        raise ComparisonError("benchmark_review_status must be a non-empty string")
    for hash_field in ("benchmark_sha256", "environment_sha256", "evaluator_sha256"):
        if not isinstance(reference[hash_field], str) or not re.fullmatch(r"[0-9a-fA-F]{64}", reference[hash_field]):
            raise ComparisonError(f"{hash_field} must be a 64-character hexadecimal SHA-256")
    reference_tasks = _validate_report_results(reference_label, reference)

    for label, report in named_reports[1:]:
        for field in PROTOCOL_FIELDS:
            if field not in report or report[field] in (None, ""):
                raise ComparisonError(f"report {label!r} is missing protocol field {field!r}")
            if report[field] != reference[field]:
                raise ComparisonError(
                    f"reports are not comparable: {field} differs "
                    f"({reference_label}={reference[field]!r}, {label}={report[field]!r})"
                )
        if _validate_report_results(label, report) != reference_tasks:
            raise ComparisonError(f"reports are not comparable: task/scenario coverage differs for {label!r}")

    currencies = set()
    for label, report in named_reports:
        aggregate = report["aggregate"]
        for metric in METRIC_LABELS:
            value = aggregate.get(metric)
            if value is not None and (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(float(value))
            ):
                raise ComparisonError(f"report {label!r} has invalid metric {metric!r}: {value!r}")
        if aggregate.get("estimated_cost_per_successful_task") is not None:
            pricing = report.get("token_pricing")
            currency = pricing.get("currency") if isinstance(pricing, dict) else None
            if not isinstance(currency, str) or not currency.strip():
                raise ComparisonError(f"report {label!r} has a cost estimate without a currency")
            currencies.add(currency.strip().upper())
    if len(currencies) > 1:
        raise ComparisonError("cost estimates use different currencies")
    return reference, next(iter(currencies), None)


def _validate_report_results(label: str, report: dict[str, Any]) -> dict[str, str]:
    aggregate = report.get("aggregate")
    results = report.get("results")
    if not isinstance(aggregate, dict):
        raise ComparisonError(f"report {label!r} is missing aggregate metrics")
    if not isinstance(results, list):
        raise ComparisonError(f"report {label!r} is missing per-task results")
    tasks = aggregate.get("tasks")
    if type(tasks) is not int or tasks != len(results):
        raise ComparisonError(
            f"report {label!r} aggregate task count does not match its per-task results"
        )
    task_ids = [row.get("task_id") for row in results if isinstance(row, dict)]
    if len(task_ids) != len(results) or any(
        not isinstance(task_id, str) or not task_id
        or not isinstance(row.get("scenario_id"), str) or not row["scenario_id"]
        or not isinstance(row.get("success"), bool)
        for task_id, row in zip(task_ids, results)
    ):
        raise ComparisonError(f"report {label!r} contains a malformed per-task result")
    if len(task_ids) != len(set(task_ids)):
        raise ComparisonError(f"report {label!r} contains duplicate task IDs")
    return {row["task_id"]: row["scenario_id"] for row in results}


def build_comparison(named_reports: list[tuple[str, dict[str, Any]]]) -> dict[str, Any]:
    reference, currency = _validate_named_reports(named_reports)
    reference_label, _ = named_reports[0]
    reference_metrics = reference["aggregate"]
    candidates = []
    for label, report in named_reports:
        aggregate = report["aggregate"]
        metrics = {key: aggregate.get(key) for key in METRIC_LABELS}
        deltas = {}
        for key, value in metrics.items():
            baseline_value = reference_metrics.get(key)
            if isinstance(value, (int, float)) and not isinstance(value, bool) and isinstance(baseline_value, (int, float)) and not isinstance(baseline_value, bool):
                deltas[key] = round(float(value) - float(baseline_value), 8)
            else:
                deltas[key] = None
        agent = report.get("agent") if isinstance(report.get("agent"), dict) else {}
        candidates.append({
            "label": label,
            "agent": {key: agent.get(key) for key in ("name", "type") if agent.get(key) is not None},
            "metrics": metrics,
            "delta_vs_reference": deltas,
        })
    return {
        "comparison_schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "reference": reference_label,
        "protocol": {field: reference[field] for field in PROTOCOL_FIELDS},
        "cost_currency": currency,
        "metric_directions": {
            key: ("lower_is_better" if key in LOWER_IS_BETTER else "higher_is_better")
            for key in METRIC_LABELS
        },
        "candidates": candidates,
        "composite_score": None,
        "interpretation_note": (
            "Reports passed strict protocol matching. Review status is reported, not inferred; "
            "metrics are separate and no weighted composite score or universal winner is inferred."
        ),
    }


def _display_metric(key: str, value: Any, currency: str | None) -> str:
    if value is None:
        return "—"
    if key in RATE_METRICS:
        return f"{float(value) * 100:.2f}%"
    if key in {"p95_agent_action_latency_ms", "p99_agent_action_latency_ms"}:
        return f"{float(value):.2f}"
    if key == "estimated_cost_per_successful_task":
        return f"{currency or ''} {float(value):.8f}".strip()
    if key == "agent_actions_per_second":
        return f"{float(value):.2f}"
    return str(value)


def to_markdown(comparison: dict[str, Any]) -> str:
    protocol = comparison["protocol"]
    lines = [
        "# PolyGlot Agents — Model Comparison",
        "",
        f"Reference: **{comparison['reference']}**",
        "",
        "## Matched evaluation protocol",
        "",
        f"- Benchmark: `{protocol['benchmark_id']}` v`{protocol['benchmark_version']}`",
        f"- Benchmark SHA-256: `{protocol['benchmark_sha256']}`",
        f"- Environment bundle SHA-256: `{protocol['environment_sha256']}`",
        f"- Evaluator/adapter SHA-256: `{protocol['evaluator_sha256']}`",
        f"- Language/locale: `{protocol['language']}` / `{protocol['locale']}`",
        f"- Benchmark review status: `{protocol['benchmark_review_status']}`",
        f"- Split, seed, step budget, concurrency: `{protocol['split']}`, `{protocol['seed']}`, `{protocol['step_budget']}`, `{protocol['concurrency']}`",
        "",
        "## Results",
        "",
        "| Candidate | Tasks | Success | Safe completion | Outcome alignment | Tool-error recovery | Unsafe actions | Unsupported claims | Action errors | p95 ms | Cost / success |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    visible_metrics = (
        "tasks", "success_rate", "safe_completion_rate", "outcome_match_rate",
        "tool_error_recovery_rate", "unsafe_action_rate",
        "unsupported_claim_rate", "agent_action_error_rate",
        "p95_agent_action_latency_ms", "estimated_cost_per_successful_task",
    )
    for candidate in comparison["candidates"]:
        cells = [candidate["label"]]
        cells.extend(_display_metric(key, candidate["metrics"].get(key), comparison.get("cost_currency")) for key in visible_metrics)
        lines.append("| " + " | ".join(cell.replace("|", "\\|") for cell in cells) + " |")
    lines.extend([
        "",
        "Cost is shown only when token usage and user-supplied prices are complete and currencies match. A dash means unavailable, not zero.",
        "Metrics are separate decision signals; this report does not create a composite score or universal winner.",
        "",
    ])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", action="append", required=True, metavar="LABEL=PATH",
                        help="Add a benchmark JSON report; first report is the delta reference")
    parser.add_argument("--output", type=Path, default=Path("/tmp/polyglot-comparison.json"))
    parser.add_argument("--markdown-output", type=Path,
                        help="Optional human-readable Markdown scorecard")
    args = parser.parse_args()
    try:
        reports = [load_report_spec(spec) for spec in args.report]
        comparison = build_comparison(reports)
    except ComparisonError as exc:
        parser.error(str(exc))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(comparison, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.markdown_output:
        args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_output.write_text(to_markdown(comparison), encoding="utf-8")
    print(json.dumps({
        "comparison": str(args.output),
        "markdown": str(args.markdown_output) if args.markdown_output else None,
        "candidates": len(comparison["candidates"]),
        "protocol_sha256": comparison["protocol"]["benchmark_sha256"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
