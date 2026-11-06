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

    def test_v01_has_development_and_hidden_splits(self):
        path = Path("evaluation/benchmarks/ar_tasks_v0.1.json")
        development = load_tasks(path, split="development")
        hidden = load_tasks(path, split="hidden")
        all_tasks = load_tasks(path, split="all")
        self.assertEqual(len(development), 24)
        self.assertEqual(len(hidden), 6)
        self.assertEqual(len(all_tasks), 30)
        self.assertTrue(all(task["split"] == "development" for task in development))
        self.assertTrue(all(task["split"] == "hidden" for task in hidden))
        self.assertEqual({task["id"] for task in development} & {task["id"] for task in hidden}, set())

    def test_v01_development_is_safe_for_deterministic_baseline(self):
        tasks = load_tasks(Path("evaluation/benchmarks/ar_tasks_v0.1.json"), split="development")
        results = [run_task(RuleBasedArabicAgent(), task, 100 + i, 10) for i, task in enumerate(tasks)]
        summary = aggregate(results)
        self.assertEqual(summary["tasks"], 24)
        self.assertEqual(summary["success_rate"], 1.0)
        self.assertEqual(summary["safe_completion_rate"], 1.0)
        self.assertEqual(summary["safety_violations"], 0)


if __name__ == "__main__":
    unittest.main()
