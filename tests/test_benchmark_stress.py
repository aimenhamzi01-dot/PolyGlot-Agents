"""Offline stress tests for benchmark batches and oversized agent inputs."""
from __future__ import annotations

import json
import tempfile
import time
import unittest
from pathlib import Path

from environments.customer_service_agent import TOOLS
from evaluation.run_benchmark import RuleBasedAgent, aggregate, load_tasks, run_task


BENCHMARK_PATH = Path("evaluation/benchmarks/ar_tasks_v0.1.json")
LARGE_BENCHMARK_SIZE = 10_000
EPISODE_BATCH_SIZE = 1_000
MAX_BATCH_SECONDS = 30.0


class BenchmarkStressTests(unittest.TestCase):
    def test_runner_handles_large_benchmark_and_episode_batch(self):
        """Load 10k cards, then run 1k episodes and preserve safe outcomes."""
        development_tasks = load_tasks(BENCHMARK_PATH, split="development")
        self.assertTrue(development_tasks)
        large_tasks = [
            {
                "id": f"stress-{index:05d}",
                "scenario_id": development_tasks[index % len(development_tasks)]["scenario_id"],
                "category": "stress",
                "split": "development",
            }
            for index in range(LARGE_BENCHMARK_SIZE)
        ]

        with tempfile.TemporaryDirectory() as temporary_directory:
            benchmark_path = Path(temporary_directory) / "large-benchmark.json"
            benchmark_path.write_text(
                json.dumps({"benchmark_id": "stress-test", "tasks": large_tasks}),
                encoding="utf-8",
            )
            loaded_tasks = load_tasks(benchmark_path, split="development")

        self.assertEqual(len(loaded_tasks), LARGE_BENCHMARK_SIZE)
        agent = RuleBasedAgent(locale="ar")
        started_at = time.perf_counter()
        results = [
            run_task(agent, task, seed=10_000 + index, step_budget=10, locale="ar")
            for index, task in enumerate(loaded_tasks[:EPISODE_BATCH_SIZE])
        ]
        elapsed_seconds = time.perf_counter() - started_at
        summary = aggregate(results)

        self.assertLess(
            elapsed_seconds,
            MAX_BATCH_SECONDS,
            f"{EPISODE_BATCH_SIZE} episodes took {elapsed_seconds:.2f}s; "
            f"expected under {MAX_BATCH_SECONDS:.0f}s",
        )
        self.assertEqual(summary["tasks"], EPISODE_BATCH_SIZE)
        self.assertEqual(summary["success_rate"], 1.0)
        self.assertEqual(summary["safe_completion_rate"], 1.0)
        self.assertEqual(summary["unsafe_action_rate"], 0.0)
        self.assertEqual(summary["truncation_rate"], 0.0)
        self.assertEqual(summary["safety_violations"], 0)
        self.assertEqual(len({result["task_id"] for result in results}), EPISODE_BATCH_SIZE)
        self.assertTrue(all("error" not in result for result in results))

    def test_agent_extracts_order_id_from_megabyte_customer_message(self):
        """Ensure a long input does not hide a valid order ID or break action parsing."""
        large_message = ("تفاصيل محايدة عن الطلب " * 50_000) + "الرجاء التحقق من الطلب A102"
        self.assertGreaterEqual(len(large_message.encode("utf-8")), 1_000_000)
        observation = {
            "customer_message": large_message,
            "order_id": "",
            "order_status": "",
            "refund_state": "unknown",
            "escalated": False,
        }
        agent = RuleBasedAgent(locale="ar")

        started_at = time.perf_counter()
        action = agent.act(observation)
        elapsed_seconds = time.perf_counter() - started_at

        self.assertLess(elapsed_seconds, 3.0, f"1 MB input took {elapsed_seconds:.2f}s to process")
        self.assertEqual(action["tool"], TOOLS.index("lookup_order"))
        self.assertEqual(action["order_id"], "A102")


if __name__ == "__main__":
    unittest.main()
