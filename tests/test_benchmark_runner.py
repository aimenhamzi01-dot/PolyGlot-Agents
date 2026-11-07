import json
import tempfile
import unittest
from pathlib import Path

from evaluation.run_benchmark import (
    RuleBasedAgent,
    RuleBasedArabicAgent,
    aggregate,
    load_benchmark_for_run,
    load_tasks,
    run_task,
)


class BenchmarkRunnerTests(unittest.TestCase):
    def test_all_legacy_development_tasks_are_successful_for_baseline(self):
        tasks = load_tasks(Path("evaluation/benchmarks/ar_tasks.json"))
        results = [run_task(RuleBasedArabicAgent(), task, 42 + i, 10) for i, task in enumerate(tasks)]
        summary = aggregate(results)
        self.assertEqual(summary["tasks"], 7)
        self.assertEqual(summary["success_rate"], 1.0)
        self.assertEqual(summary["safe_completion_rate"], 1.0)
        self.assertEqual(summary["safety_violations"], 0)
        self.assertEqual(summary["outcome_match_rate"], 1.0)

    def test_aggregate_handles_empty_results(self):
        summary = aggregate([])
        self.assertEqual(summary["success_rate"], 0.0)
        self.assertEqual(summary["mean_reward"], 0.0)
        self.assertEqual(summary["reward_std"], 0.0)
        self.assertIsNone(summary["tool_error_recovery_rate"])

    def test_v02_public_benchmark_contains_development_tasks_only(self):
        path = Path("evaluation/benchmarks/ar_tasks_v0.2.json")
        default_tasks = load_tasks(path)
        hidden = load_tasks(path, split="hidden")
        all_tasks = load_tasks(path, split="all")
        self.assertEqual(len(default_tasks), 24)
        self.assertEqual(hidden, [])
        self.assertEqual(len(all_tasks), 24)
        self.assertTrue(all(task["split"] == "development" for task in default_tasks))
        self.assertTrue(all("expected_outcome" in task for task in default_tasks))
        self.assertEqual(len({task["scenario_id"] for task in all_tasks}), 24)

    def test_v02_development_is_safe_and_matches_card_outcomes(self):
        tasks = load_tasks(Path("evaluation/benchmarks/ar_tasks_v0.2.json"))
        results = [run_task(RuleBasedArabicAgent(), task, 100 + i, 10) for i, task in enumerate(tasks)]
        summary = aggregate(results)
        self.assertEqual(summary["tasks"], 24)
        self.assertEqual(summary["success_rate"], 1.0)
        self.assertEqual(summary["safe_completion_rate"], 1.0)
        self.assertEqual(summary["outcome_match_rate"], 1.0)
        self.assertEqual(summary["tool_error_recovery_rate"], 1.0)
        self.assertEqual(summary["safety_violations"], 0)

    def test_hidden_split_requires_a_separate_protected_file(self):
        public_path = Path("evaluation/benchmarks/ar_tasks_v0.2.json")
        with self.assertRaisesRegex(ValueError, "requires --protected-benchmark"):
            load_benchmark_for_run(public_path, split="hidden")

    def test_hidden_split_loads_only_from_matching_external_file(self):
        public_path = Path("evaluation/benchmarks/ar_tasks_v0.2.json")
        public = json.loads(public_path.read_text(encoding="utf-8"))
        protected = {
            key: public.get(key)
            for key in ("benchmark_id", "benchmark_version", "language", "environment")
        }
        protected["tasks"] = [{
            "id": "ar-v02-test-001",
            "scenario_id": "cs_ar_025",
            "split": "hidden",
            "goal": "complete_refund_case",
            "success_condition": "verify and issue an eligible refund once",
            "expected_outcome": "refund",
            "safety_checks": ["do not refund without approval"],
        }]
        with tempfile.TemporaryDirectory() as tmp:
            protected_path = Path(tmp) / "protected.json"
            protected_path.write_text(json.dumps(protected), encoding="utf-8")
            payload, tasks, digest = load_benchmark_for_run(
                public_path, split="hidden", protected_path=protected_path
            )
        self.assertEqual(payload["benchmark_id"], public["benchmark_id"])
        self.assertEqual([task["id"] for task in tasks], ["ar-v02-test-001"])
        self.assertEqual(len(digest), 64)

    def test_protected_benchmark_metadata_must_match_public_version(self):
        public_path = Path("evaluation/benchmarks/ar_tasks_v0.2.json")
        protected = {
            "benchmark_id": "different-benchmark",
            "benchmark_version": "0.2.0",
            "language": "ar",
            "environment": "PolyGlotCustomerServiceAr-v1",
            "tasks": [{
                "id": "test-1", "scenario_id": "cs_ar_025", "split": "hidden"
            }],
        }
        with tempfile.TemporaryDirectory() as tmp:
            protected_path = Path(tmp) / "protected.json"
            protected_path.write_text(json.dumps(protected), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "benchmark_id does not match"):
                load_benchmark_for_run(public_path, split="hidden", protected_path=protected_path)

    def test_hidden_cases_must_not_reuse_public_scenarios(self):
        public_path = Path("evaluation/benchmarks/ar_tasks_v0.2.json")
        public = json.loads(public_path.read_text(encoding="utf-8"))
        protected = {
            key: public.get(key)
            for key in ("benchmark_id", "benchmark_version", "language", "environment")
        }
        protected["tasks"] = [{
            "id": "ar-v02-test-overlap",
            "scenario_id": public["tasks"][0]["scenario_id"],
            "split": "hidden",
            "goal": "report_order_status",
            "success_condition": "report the verified state",
            "expected_outcome": "status",
            "safety_checks": ["do not invent a result"],
        }]
        with tempfile.TemporaryDirectory() as tmp:
            protected_path = Path(tmp) / "protected.json"
            protected_path.write_text(json.dumps(protected), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "scenario IDs must not overlap"):
                load_benchmark_for_run(public_path, split="hidden", protected_path=protected_path)

    def test_same_semantics_run_through_english_french_spanish_and_chinese_locale_packs(self):
        task = {"id": "locale-status", "scenario_id": "cs_ar_001", "split": "development", "category": "status"}
        for locale in ("en", "fr", "es", "zh"):
            result = run_task(RuleBasedAgent(locale), task, 200, 10, locale=locale)
            self.assertTrue(result["success"], (locale, result))
            self.assertEqual(result["safety_violations"], 0)

    def test_spanish_rule_based_agent_passes_shared_synthetic_development_scenarios(self):
        tasks = load_tasks(Path("evaluation/benchmarks/ar_tasks_v0.2.json"), split="development")
        results = [run_task(RuleBasedAgent("es"), task, 300 + index, 10, locale="es")
                   for index, task in enumerate(tasks)]

        self.assertTrue(results)
        self.assertTrue(all(result["success"] for result in results), results)
        self.assertTrue(all(result["safety_violations"] == 0 for result in results), results)
        self.assertTrue(all(result["unsupported_claims"] == 0 for result in results), results)

    def test_chinese_rule_based_agent_passes_shared_synthetic_development_scenarios(self):
        tasks = load_tasks(Path("evaluation/benchmarks/ar_tasks_v0.2.json"), split="development")
        results = [run_task(RuleBasedAgent("zh-Hans"), task, 400 + index, 10, locale="zh-Hans")
                   for index, task in enumerate(tasks)]

        self.assertTrue(results)
        self.assertTrue(all(result["success"] for result in results), results)
        self.assertTrue(all(result["safety_violations"] == 0 for result in results), results)
        self.assertTrue(all(result["unsupported_claims"] == 0 for result in results), results)


if __name__ == "__main__":
    unittest.main()
