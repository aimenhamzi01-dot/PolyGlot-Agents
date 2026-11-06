"""Tests for measured agent latency and bounded concurrent benchmark execution."""
from __future__ import annotations

import threading
import time
import unittest
from pathlib import Path

from evaluation.run_benchmark import (
    RuleBasedAgent,
    aggregate,
    failure_reasons,
    load_tasks,
    run_task,
    run_tasks,
)


class BenchmarkMetricsTests(unittest.TestCase):
    def test_failure_reasons_are_stable_and_non_exclusive(self):
        result = {
            "success": False,
            "safety_violations": 1,
            "unsupported_claims": 1,
            "outcome_match": False,
            "truncated": False,
        }
        self.assertEqual(
            failure_reasons(result),
            ["unsafe_action", "unsupported_claim", "outcome_mismatch"],
        )

    def test_aggregate_breaks_failures_down_by_scenario_and_locale(self):
        results = [
            {"task_id": "a", "scenario_id": "status", "locale": "ar", "success": True, "safety_violations": 0, "outcome_match": True},
            {"task_id": "b", "scenario_id": "refund", "locale": "ar", "success": False, "safety_violations": 1, "unsupported_claims": 0, "outcome_match": False},
            {"task_id": "c", "scenario_id": "refund", "locale": "fr", "success": False, "safety_violations": 0, "unsupported_claims": 1, "outcome_match": False},
        ]
        summary = aggregate(results)
        self.assertEqual(summary["failure_reasons"], {"outcome_mismatch": 2, "unsafe_action": 1, "unsupported_claim": 1})
        self.assertEqual(summary["failure_breakdown"]["by_scenario"]["refund"]["tasks"], 2)
        self.assertEqual(summary["failure_breakdown"]["by_scenario"]["refund"]["failure_reasons"]["unsafe_action"], 1)
        self.assertEqual(summary["failure_breakdown"]["by_locale"]["fr"]["failure_reasons"]["unsupported_claim"], 1)

    def test_run_task_records_each_agent_action_latency(self):
        class DelayedAgent:
            def __init__(self):
                self.baseline = RuleBasedAgent("ar")

            def act(self, observation):
                time.sleep(0.002)
                return self.baseline.act(observation)

        task = {"id": "latency-status", "scenario_id": "cs_ar_001", "split": "development"}
        result = run_task(DelayedAgent(), task, seed=41, step_budget=10, locale="ar")

        self.assertTrue(result["success"], result)
        self.assertGreater(result["agent_action_calls"], 0)
        self.assertEqual(result["agent_action_calls"], len(result["agent_action_latency_ms"]))
        self.assertTrue(all(latency > 0 for latency in result["agent_action_latency_ms"]))

    def test_aggregate_reports_latency_percentiles_errors_and_throughput(self):
        result = {
            "success": True,
            "agent_action_calls": 4,
            "agent_action_errors": 1,
            "agent_action_latency_ms": [10.0, 20.0, 30.0, 40.0],
            "agent_usage_calls": 4,
            "agent_usage_complete_calls": 4,
            "agent_token_usage": {
                "prompt_tokens": 300,
                "completion_tokens": 80,
                "total_tokens": 380,
            },
        }

        summary = aggregate(
            [result],
            elapsed_seconds=2.0,
            input_price_per_million_tokens=1.0,
            output_price_per_million_tokens=2.0,
        )

        self.assertEqual(summary["agent_action_calls"], 4)
        self.assertEqual(summary["agent_action_errors"], 1)
        self.assertEqual(summary["agent_action_error_rate"], 0.25)
        self.assertEqual(summary["mean_agent_action_latency_ms"], 25.0)
        self.assertEqual(summary["p50_agent_action_latency_ms"], 20.0)
        self.assertEqual(summary["p95_agent_action_latency_ms"], 40.0)
        self.assertEqual(summary["p99_agent_action_latency_ms"], 40.0)
        self.assertEqual(summary["max_agent_action_latency_ms"], 40.0)
        self.assertEqual(summary["tasks_per_second"], 0.5)
        self.assertEqual(summary["agent_actions_per_second"], 2.0)
        self.assertTrue(summary["token_usage_complete"])
        self.assertEqual(summary["agent_token_usage"]["total_tokens"], 380)
        self.assertEqual(summary["estimated_cost"], 0.00046)
        self.assertEqual(summary["estimated_cost_per_successful_task"], 0.00046)

    def test_cost_is_not_estimated_when_provider_usage_is_missing(self):
        result = {
            "success": True,
            "agent_action_calls": 1,
            "agent_action_latency_ms": [15.0],
        }

        summary = aggregate(
            [result],
            input_price_per_million_tokens=1.0,
            output_price_per_million_tokens=2.0,
        )

        self.assertFalse(summary["token_usage_complete"])
        self.assertIsNone(summary["estimated_cost"])
        self.assertIsNone(summary["estimated_cost_per_successful_task"])

    def test_run_task_collects_provider_usage_per_model_action(self):
        class UsageAgent:
            def __init__(self):
                self.baseline = RuleBasedAgent("ar")
                self.usage = None

            def act(self, observation):
                action = self.baseline.act(observation)
                self.usage = {
                    "prompt_tokens": 10,
                    "completion_tokens": 4,
                    "total_tokens": 14,
                }
                return action

            def get_last_call_usage(self):
                return self.usage

        task = {"id": "usage-status", "scenario_id": "cs_ar_001", "split": "development"}
        result = run_task(UsageAgent(), task, seed=43, step_budget=10, locale="ar")

        self.assertTrue(result["success"], result)
        self.assertEqual(result["agent_usage_calls"], result["agent_action_calls"])
        self.assertEqual(result["agent_usage_complete_calls"], result["agent_action_calls"])
        self.assertEqual(result["agent_token_usage"]["prompt_tokens"], 20)
        self.assertEqual(result["agent_token_usage"]["completion_tokens"], 8)
        self.assertEqual(result["agent_token_usage"]["total_tokens"], 28)

    def test_failed_agent_call_keeps_its_latency_and_counts_as_an_error(self):
        class FailingAgent:
            def act(self, observation):
                raise RuntimeError("simulated model timeout")

        task = {"id": "failed-request", "scenario_id": "cs_ar_001", "split": "development"}
        result = run_task(FailingAgent(), task, seed=42, step_budget=10, locale="ar")
        summary = aggregate([result])

        self.assertFalse(result["success"])
        self.assertIn("simulated model timeout", result["error"])
        self.assertEqual(result["agent_action_calls"], 1)
        self.assertEqual(result["agent_action_errors"], 1)
        self.assertEqual(summary["agent_action_error_rate"], 1.0)
        self.assertGreater(result["agent_action_latency_ms"][0], 0)

    def test_concurrent_runner_preserves_input_order_and_runs_in_parallel(self):
        class TrackingAgent:
            def __init__(self):
                self.baseline = RuleBasedAgent("ar")
                self.lock = threading.Lock()
                self.active_calls = 0
                self.peak_calls = 0

            def act(self, observation):
                with self.lock:
                    self.active_calls += 1
                    self.peak_calls = max(self.peak_calls, self.active_calls)
                try:
                    time.sleep(0.01)
                    return self.baseline.act(observation)
                finally:
                    with self.lock:
                        self.active_calls -= 1

        base_tasks = load_tasks(Path("evaluation/benchmarks/ar_tasks.json"))
        tasks = [
            {**base_tasks[index % len(base_tasks)], "id": f"concurrent-{index:02d}"}
            for index in range(12)
        ]
        agent = TrackingAgent()

        results = run_tasks(agent, tasks, seed=100, step_budget=10, locale="ar", concurrency=4)

        self.assertEqual([row["task_id"] for row in results], [task["id"] for task in tasks])
        self.assertGreater(agent.peak_calls, 1)
        self.assertLessEqual(agent.peak_calls, 4)
        self.assertTrue(all(row["success"] for row in results))
        self.assertEqual(aggregate(results)["unsafe_action_rate"], 0.0)

    def test_concurrency_must_be_positive(self):
        with self.assertRaisesRegex(ValueError, "at least 1"):
            run_tasks(RuleBasedAgent("ar"), [], seed=0, step_budget=10, concurrency=0)


if __name__ == "__main__":
    unittest.main()
