import unittest

from environments.customer_service_agent import SCENARIO_IDS
from scripts.validate_benchmarks import validate_payload


class ValidateBenchmarksTests(unittest.TestCase):
    def test_accepts_authored_arabic_benchmark(self):
        payload = {
            "benchmark_id": "test-ar",
            "language": "ar",
            "environment": "PolyGlotCustomerServiceAr-v1",
            "scenario_count": 1,
            "metrics": ["task_success_rate"],
            "tasks": [
                {
                    "id": "ar-001",
                    "scenario_id": SCENARIO_IDS[0],
                    "goal": "report_status",
                    "success_condition": "report the verified status",
                    "safety_checks": ["do not invent a status"],
                    "split": "development",
                }
            ],
        }

        self.assertEqual(validate_payload(payload), [])

    def test_accepts_empty_placeholder_only_when_explicitly_declared(self):
        payload = {
            "benchmark_id": "polyglot-en",
            "language": "en",
            "status": "requires_native_speaker_authoring",
            "tasks": [],
        }

        self.assertEqual(validate_payload(payload), [])

    def test_rejects_duplicate_ids_invalid_splits_and_missing_safety_checks(self):
        task = {
            "id": "duplicate",
            "scenario_id": "scenario-1",
            "goal": "goal",
            "success_condition": "condition",
            "safety_checks": [],
        }
        payload = {
            "benchmark_id": "test",
            "language": "en",
            "tasks": [dict(task), {**task, "split": "validation"}],
        }

        errors = validate_payload(payload)
        self.assertTrue(any("duplicates task id" in error for error in errors))
        self.assertTrue(any("split must" in error for error in errors))
        self.assertTrue(any("safety_checks" in error for error in errors))

    def test_rejects_unknown_scenario_for_active_environment(self):
        payload = {
            "benchmark_id": "test-ar",
            "language": "ar",
            "environment": "PolyGlotCustomerServiceAr-v1",
            "tasks": [
                {
                    "id": "ar-001",
                    "scenario_id": "cs_ar_missing",
                    "goal": "report_status",
                    "success_condition": "report the verified status",
                    "safety_checks": ["do not invent a status"],
                }
            ],
        }

        errors = validate_payload(payload)
        self.assertTrue(any("unknown customer-service scenario" in error for error in errors))

    def test_rejects_unmarked_empty_benchmark(self):
        errors = validate_payload({"benchmark_id": "empty", "language": "en", "tasks": []})
        self.assertTrue(any("empty tasks array" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
