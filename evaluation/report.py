#!/usr/bin/env python3
"""Render an auditable benchmark JSON report as Markdown or standalone HTML."""
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from typing import Any

METRICS = (
    ("tasks", "Tasks"),
    ("success_rate", "Success rate"),
    ("safe_completion_rate", "Safe completion"),
    ("outcome_match_rate", "Outcome alignment"),
    ("unsafe_action_rate", "Unsafe-action rate"),
    ("unsupported_claim_rate", "Unsupported-claim rate"),
    ("tool_error_recovery_rate", "Tool-error recovery"),
    ("mean_reward", "Mean reward"),
    ("mean_tool_calls", "Mean tool calls"),
)


def load_report(path: Path) -> dict[str, Any]:
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read valid report JSON: {path}: {exc}") from exc
    if not isinstance(report, dict) or not isinstance(report.get("aggregate"), dict):
        raise ValueError("report must be an object containing an aggregate object")
    return report


def _value(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.6f}".rstrip("0").rstrip(".")
    return str(value)


def _pct(value: Any) -> str:
    if value is None:
        return "—"
    return f"{float(value) * 100:.2f}%"


def _metric_value(key: str, value: Any) -> str:
    return _pct(value) if key.endswith("_rate") else _value(value)


def _breakdown_table(title: str, rows: dict[str, Any]) -> list[str]:
    lines = [f"### {title}", "", "| Key | Tasks | Successful | Unsafe | Failure reasons |", "|---|---:|---:|---:|---|"]
    if not rows:
        lines.append("| — | 0 | 0 | 0 | — |")
    for key, row in sorted(rows.items()):
        reasons = row.get("failure_reasons", {}) or {}
        reason_text = ", ".join(f"{name}: {count}" for name, count in sorted(reasons.items())) or "—"
        lines.append(f"| `{key}` | {row.get('tasks', 0)} | {row.get('successful_tasks', 0)} | {row.get('unsafe_tasks', 0)} | {reason_text} |")
    return lines


def render_markdown(report: dict[str, Any]) -> str:
    aggregate = report["aggregate"]
    agent = report.get("agent") if isinstance(report.get("agent"), dict) else {}
    lines = [
        f"# PolyGlot Agents evaluation — {report.get('benchmark_id', 'benchmark')}",
        "",
        f"- Agent: `{agent.get('name', 'unknown')}` ({agent.get('type', 'unknown')})",
        f"- Benchmark version: `{report.get('benchmark_version') or 'unspecified'}`",
        f"- Language / locale: `{report.get('language', 'unknown')}` / `{report.get('locale', 'unknown')}`",
        f"- Split: `{report.get('split', 'unknown')}`",
        f"- Review status: `{report.get('benchmark_review_status', 'unknown')}`",
        f"- Benchmark SHA-256: `{report.get('benchmark_sha256', 'unknown')}`",
        f"- Environment SHA-256: `{report.get('environment_sha256', 'unknown')}`",
        f"- Evaluator SHA-256: `{report.get('evaluator_sha256', 'unknown')}`",
        "",
        "## Aggregate metrics",
        "",
        "| Metric | Value |",
        "|---|---:|",
    ]
    for key, label in METRICS:
        lines.append(f"| {label} | {_metric_value(key, aggregate.get(key))} |")

    failure_reasons = aggregate.get("failure_reasons", {}) or {}
    lines.extend(["", "## Failure taxonomy", "", "Counts are non-exclusive: one task may have multiple diagnostic labels.", ""])
    if failure_reasons:
        lines.extend(["| Reason | Tasks |", "|---|---:|"])
        lines.extend(f"| `{key}` | {value} |" for key, value in sorted(failure_reasons.items()))
    else:
        lines.append("No failure labels were recorded.")

    breakdown = aggregate.get("failure_breakdown", {}) or {}
    lines.extend(["", *_breakdown_table("By scenario", breakdown.get("by_scenario", {}) or {}), "", *_breakdown_table("By locale", breakdown.get("by_locale", {}) or {}), ""])
    return "\n".join(lines)


def render_html(report: dict[str, Any]) -> str:
    markdown = render_markdown(report)
    # Keep the standalone artifact dependency-free while preserving table structure.
    lines = markdown.splitlines()
    body: list[str] = []
    in_table = False
    for line in lines:
        if line.startswith("# "):
            body.append(f"<h1>{html.escape(line[2:])}</h1>")
        elif line.startswith("## "):
            if in_table:
                body.append("</table>")
                in_table = False
            body.append(f"<h2>{html.escape(line[3:])}</h2>")
        elif line.startswith("### "):
            if in_table:
                body.append("</table>")
                in_table = False
            body.append(f"<h3>{html.escape(line[4:])}</h3>")
        elif line.startswith("- "):
            body.append(f"<p>{html.escape(line[2:])}</p>")
        elif line.startswith("|") and not line.replace("|", "").replace("-", "").replace(":", "").strip():
            continue
        elif line.startswith("|"):
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            tag = "th" if not in_table else "td"
            if not in_table:
                body.append("<table><thead>")
                in_table = True
            if tag == "th":
                body.append("<tr>" + "".join(f"<th>{html.escape(cell)}</th>" for cell in cells) + "</tr></thead><tbody>")
            else:
                body.append("<tr>" + "".join(f"<td>{html.escape(cell)}</td>" for cell in cells) + "</tr>")
        elif line.strip():
            body.append(f"<p>{html.escape(line)}</p>")
        elif in_table:
            body.append("</tbody></table>")
            in_table = False
    if in_table:
        body.append("</tbody></table>")
    return "<!doctype html>\n<html lang=\"en\"><head><meta charset=\"utf-8\"><title>PolyGlot Agents evaluation</title><style>body{font:16px system-ui;max-width:1100px;margin:40px auto;padding:0 20px;color:#17202a}table{border-collapse:collapse;margin:12px 0 28px;width:100%}th,td{border:1px solid #ccd3da;padding:8px;text-align:left}th{background:#eef2f5}code{background:#f1f3f5;padding:2px 4px}</style></head><body>" + "\n".join(body) + "</body></html>\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--markdown-output", type=Path)
    parser.add_argument("--html-output", type=Path)
    args = parser.parse_args(argv)
    if not args.markdown_output and not args.html_output:
        parser.error("provide --markdown-output and/or --html-output")
    try:
        report = load_report(args.input)
    except ValueError as exc:
        parser.error(str(exc))
    outputs = []
    for path, content in ((args.markdown_output, render_markdown(report)), (args.html_output, render_html(report))):
        if path:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            outputs.append(str(path))
    print(json.dumps({"input": str(args.input), "outputs": outputs}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
