import unittest

from evaluation.run_benchmark import RuleBasedArabicAgent, aggregate, load_tasks, run_task
from pathlib import Path


class BenchmarkRunnerTests(unittest.TestCase):
    def test_all_development_tasks_are_successful_for_baseline(self):
        tasks = load_tasks(Path("evaluation/benchmarks/ar_tasks.json"))
        results = [run_task(RuleBasedArabicAgent(), task, 42 + i, 10) for i, task in enumerate(tasks)]
        summary = aggregate(results)
        self.assertEqual(summary["tasks"], 7)
        self.assertEqual(summary["success_rate"], 1.0)
        self.assertEqual(summary["safe_completion_rate"], 1.0)
        self.assertEqual(summary["safety_violations"], 0)

    def test_aggregate_handles_empty_results(self):
        summary = aggregate([])
        self.assertEqual(summary["success_rate"], 0.0)
        self.assertEqual(summary["mean_reward"], 0.0)


if __name__ == "__main__":
    unittest.main()
