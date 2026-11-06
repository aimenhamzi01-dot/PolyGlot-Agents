#!/usr/bin/env python3
"""Render a descriptive multilingual coverage dashboard from JSON reports."""
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from typing import Any


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read JSON {path}: {exc}") from exc


def collect_rows(coverage: dict[str, Any], benchmark_dir: Path | None = None) -> list[dict[str, Any]]:
    languages = coverage.get("languages")
    if not isinstance(languages, dict):
        raise ValueError("coverage report must contain a languages object")
    benchmark_status: dict[str, str] = {}
    if benchmark_dir and benchmark_dir.exists():
        for path in sorted(benchmark_dir.glob("*_tasks*.json")):
            payload = load_json(path)
            if isinstance(payload, dict) and isinstance(payload.get("language"), str):
                benchmark_status[payload["language"]] = payload.get("status") or payload.get("human_review_status", "unknown")
    rows = []
    for language, value in sorted(languages.items()):
        if not isinstance(value, dict):
            continue
        quality = value.get("quality_score") if isinstance(value.get("quality_score"), dict) else {}
        reviews = value.get("human_review_status") if isinstance(value.get("human_review_status"), dict) else {}
        rows.append({
            "language": language,
            "records": value.get("records", 0),
            "quality_mean": quality.get("mean"),
            "reviewed": reviews.get("reviewed", 0),
            "review_required": value.get("review_required", 0),
            "benchmark_status": benchmark_status.get(language, "no benchmark file"),
        })
    return rows


def render_markdown(rows: list[dict[str, Any]], *, source: str = "coverage report") -> str:
    lines = ["# PolyGlot Agents coverage dashboard", "", f"Source: `{source}`", "", "This is descriptive coverage, not proof of benchmark support or model quality.", "", "| Language | Records | Mean quality | Reviewed | Review required | Benchmark status |", "|---|---:|---:|---:|---:|---|"]
    for row in rows:
        mean = "—" if row["quality_mean"] is None else f"{float(row['quality_mean']):.3f}"
        lines.append(f"| `{row['language']}` | {row['records']} | {mean} | {row['reviewed']} | {row['review_required']} | {row['benchmark_status']} |")
    return "\n".join(lines) + "\n"


def render_html(rows: list[dict[str, Any]], *, source: str = "coverage report") -> str:
    markdown = render_markdown(rows, source=source)
    table = []
    for line in markdown.splitlines():
        if not line.startswith("|") or set(line.replace("|", "").replace("-", "").replace(":", "").strip()) == set():
            continue
        cells = [html.escape(cell.strip()) for cell in line.strip("|").split("|")]
        tag = "th" if not table else "td"
        table.append("<tr>" + "".join(f"<{tag}>{cell}</{tag}>" for cell in cells) + "</tr>")
    return "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\"><title>PolyGlot Agents coverage</title><style>body{font:16px system-ui;max-width:1100px;margin:40px auto;padding:0 20px}table{border-collapse:collapse;width:100%}th,td{border:1px solid #ccd3da;padding:8px;text-align:left}th{background:#eef2f5}</style></head><body><h1>PolyGlot Agents coverage dashboard</h1><p>Descriptive coverage, not proof of benchmark support or model quality.</p><table>" + "".join(table) + "</table></body></html>\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--coverage", type=Path, required=True)
    parser.add_argument("--benchmark-dir", type=Path)
    parser.add_argument("--markdown-output", type=Path)
    parser.add_argument("--html-output", type=Path)
    args = parser.parse_args(argv)
    if not args.markdown_output and not args.html_output:
        parser.error("provide --markdown-output and/or --html-output")
    rows = collect_rows(load_json(args.coverage), args.benchmark_dir)
    outputs = []
    for path, content in ((args.markdown_output, render_markdown(rows, source=str(args.coverage))), (args.html_output, render_html(rows, source=str(args.coverage)))):
        if path:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            outputs.append(str(path))
    print(json.dumps({"languages": len(rows), "outputs": outputs}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
