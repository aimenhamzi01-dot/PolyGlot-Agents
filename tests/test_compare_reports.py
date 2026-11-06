from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from evaluation.compare_reports import (
    ComparisonError,
    build_comparison,
    load_report_spec,
    to_markdown,
)


PROTOCOL = {
    "schema_version": 1,
    "benchmark_id": "polyglot-customer-service-ar-v0.1",
    "benchmark_version": "0.1.0",
    "benchmark_sha256": "a" * 64,
    "environment_sha256": "b" * 64,
    "language": "ar",
    "locale": "ar",
    "split": "development",
    "seed": 42,
    "step_budget": 10,
    "concurrency": 1,
}


def make_report(name: str, **overrides):
    report = {
        **PROTOCOL,
        "agent": {"name": name, "type": "openai_compatible", "base_url": "http://localhost:8080"},
        "token_pricing": {"currency": "USD"},
        "aggregate": {
            "tasks": 24,
            "success_rate": 0.8,
            "safe_completion_rate": 0.75,
            "unsafe_action_rate": 0.1,
            "unsupported_claim_rate": 0.05,
            "agent_action_error_rate": 0.02,
            "p95_agent_action_latency_ms": 100.0,
            "p99_agent_action_latency_ms": 180.0,
            "agent_actions_per_second": 4.0,
            "estimated_cost_per_successful_task": 0.02,
        },
    }
    report.update(overrides)
    return report


class CompareReportsTests(unittest.TestCase):
    def test_builds_deltas_only_after_exact_protocol_match(self):
        reference = make_report("model-a")
        candidate = make_report("model-b")
        candidate["aggregate"].update({
            "success_rate": 0.9,
            "safe_completion_rate": 0.88,
            "unsafe_action_rate": 0.04,
            "unsupported_claim_rate": 0.0,
            "agent_action_error_rate": 0.01,
            "p95_agent_action_latency_ms": 70.0,
            "p99_agent_action_latency_ms": 120.0,
            "agent_actions_per_second": 5.0,
            "estimated_cost_per_successful_task": 0.01,
        })

        comparison = build_comparison([("reference", reference), ("candidate", candidate)])
        delta = comparison["candidates"][1]["delta_vs_reference"]

        self.assertEqual(comparison["reference"], "reference")
        self.assertEqual(delta["success_rate"], 0.1)
        self.assertEqual(delta["p95_agent_action_latency_ms"], -30.0)
        self.assertEqual(delta["estimated_cost_per_successful_task"], -0.01)
        self.assertIsNone(comparison["composite_score"])
        self.assertNotIn("base_url", comparison["candidates"][0]["agent"])

    def test_rejects_different_benchmark_content_hash(self):
        reference = make_report("model-a")
        candidate = make_report("model-b")
        candidate["benchmark_sha256"] = "b" * 64

        with self.assertRaisesRegex(ComparisonError, "benchmark_sha256 differs"):
            build_comparison([("a", reference), ("b", candidate)])

    def test_rejects_different_environment_bundle_hash(self):
        reference = make_report("model-a")
        candidate = make_report("model-b")
        candidate["environment_sha256"] = "c" * 64

        with self.assertRaisesRegex(ComparisonError, "environment_sha256 differs"):
            build_comparison([("a", reference), ("b", candidate)])

    def test_rejects_different_load_protocol(self):
        reference = make_report("model-a")
        candidate = make_report("model-b")
        candidate["concurrency"] = 4

        with self.assertRaisesRegex(ComparisonError, "concurrency differs"):
            build_comparison([("a", reference), ("b", candidate)])

    def test_rejects_missing_protocol_fields_and_duplicate_labels(self):
        missing = make_report("model-a")
        del missing["locale"]
        with self.assertRaisesRegex(ComparisonError, "locale"):
            build_comparison([("a", missing), ("b", make_report("model-b"))])

        with self.assertRaisesRegex(ComparisonError, "unique"):
            build_comparison([("same", make_report("a")), ("same", make_report("b"))])

    def test_rejects_costs_in_different_currencies(self):
        reference = make_report("model-a")
        candidate = make_report("model-b")
        candidate["token_pricing"] = {"currency": "EUR"}

        with self.assertRaisesRegex(ComparisonError, "different currencies"):
            build_comparison([("a", reference), ("b", candidate)])

    def test_markdown_keeps_missing_cost_explicitly_unavailable(self):
        reference = make_report("model-a")
        candidate = make_report("model-b")
        candidate["aggregate"]["estimated_cost_per_successful_task"] = None
        comparison = build_comparison([("a", reference), ("b", candidate)])

        markdown = to_markdown(comparison)

        self.assertIn("Cost / success", markdown)
        self.assertIn("not zero", markdown)
        self.assertIn("—", markdown)

    def test_load_report_spec_reads_labeled_json_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "report.json"
            path.write_text(json.dumps(make_report("test")), encoding="utf-8")

            label, report = load_report_spec(f"local={path}")

        self.assertEqual(label, "local")
        self.assertEqual(report["agent"]["name"], "test")


if __name__ == "__main__":
    unittest.main()
