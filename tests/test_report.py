import json
import tempfile
import unittest
from pathlib import Path

from evaluation.report import load_report, render_html, render_markdown


REPORT = {
    "benchmark_id": "polyglot-ar",
    "benchmark_version": "0.2",
    "language": "ar",
    "locale": "ar",
    "split": "development",
    "benchmark_review_status": "unreviewed",
    "benchmark_sha256": "a" * 64,
    "environment_sha256": "b" * 64,
    "evaluator_sha256": "c" * 64,
    "agent": {"name": "rule_based_ar_v1", "type": "deterministic_baseline"},
    "aggregate": {
        "tasks": 2,
        "success_rate": 0.5,
        "safe_completion_rate": 0.5,
        "outcome_match_rate": 0.5,
        "unsafe_action_rate": 0.5,
        "unsupported_claim_rate": 0.0,
        "tool_error_recovery_rate": None,
        "mean_reward": 0.4,
        "mean_tool_calls": 3,
        "failure_reasons": {"unsafe_action": 1, "outcome_mismatch": 1},
        "failure_breakdown": {
            "by_scenario": {"cs_ar_001": {"tasks": 2, "successful_tasks": 1, "unsafe_tasks": 1, "failure_reasons": {"unsafe_action": 1}}},
            "by_locale": {"ar": {"tasks": 2, "successful_tasks": 1, "unsafe_tasks": 1, "failure_reasons": {"unsafe_action": 1}}},
        },
    },
}


class ReportTests(unittest.TestCase):
    def test_markdown_contains_protocol_metrics_and_breakdowns(self):
        output = render_markdown(REPORT)
        self.assertIn("# PolyGlot Agents evaluation", output)
        self.assertIn("50.00%", output)
        self.assertIn("`unsafe_action`", output)
        self.assertIn("By scenario", output)
        self.assertIn("cs_ar_001", output)

    def test_html_escapes_report_values_and_contains_tables(self):
        output = render_html(REPORT)
        self.assertIn("<!doctype html>", output)
        self.assertIn("<table>", output)
        self.assertIn("rule_based_ar_v1", output)

    def test_load_report_rejects_missing_aggregate(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            path.write_text(json.dumps({"results": []}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "aggregate"):
                load_report(path)


if __name__ == "__main__":
    unittest.main()
