import unittest

from environments.customer_service_agent import SCENARIO_GOALS, SCENARIO_IDS
from scripts.validate_benchmarks import validate_payload


class ValidateBenchmarksTests(unittest.TestCase):
    def _customer_service_task(self, *, scenario_id=None, expected_outcome=None, split="development"):
        scenario_id = scenario_id or SCENARIO_IDS[0]
        expected_outcome = expected_outcome or SCENARIO_GOALS[scenario_id]
        return {
            "id": "ar-001",
            "scenario_id": scenario_id,
            "goal": "complete_the_customer_request",
            "success_condition": "complete the state-verified customer request",
            "expected_outcome": expected_outcome,
            "safety_checks": ["do not invent a result"],
            "split": split,
        }

    def test_accepts_authored_arabic_benchmark_with_matching_outcome_oracle(self):
        scenario_id = SCENARIO_IDS[0]
        payload = {
            "benchmark_id": "test-ar",
            "language": "ar",
            "environment": "PolyGlotCustomerServiceAr-v1",
            "scenario_count": 1,
            "metrics": ["task_success_rate"],
            "tasks": [self._customer_service_task(scenario_id=scenario_id)],
        }

        self.assertEqual(validate_payload(payload), [])

    def test_accepts_customer_prompts_for_supported_locales(self):
        task = self._customer_service_task()
        task["customer_prompts"] = {
            "ar": "أين وصل طلبي A102؟",
            "en": "Could you check order A102?",
            "es": "¿Podrían revisar el pedido A102?",
            "zh-Hans": "请帮我查一下订单 A102。",
        }
        payload = {
            "benchmark_id": "test-multilingual-prompts",
            "language": "ar",
            "environment": "PolyGlotCustomerServiceAr-v1",
            "tasks": [task],
        }

        self.assertEqual(validate_payload(payload), [])

    def test_rejects_invalid_or_unsupported_customer_prompts(self):
        task = self._customer_service_task()
        task["customer_prompts"] = {"xx": "Hello"}
        task["customer_prompt"] = "Ambiguous single-locale prompt"
        payload = {
            "benchmark_id": "test-invalid-prompts",
            "language": "en",
            "environment": "PolyGlotCustomerServiceAr-v1",
            "tasks": [task],
        }

        errors = validate_payload(payload)
        self.assertTrue(any("either customer_prompt or customer_prompts" in error for error in errors))
        self.assertTrue(any("unsupported locale 'xx'" in error for error in errors))

    def test_accepts_empty_placeholder_only_when_explicitly_declared(self):
        payload = {
            "benchmark_id": "polyglot-en",
            "language": "en",
            "status": "requires_native_speaker_authoring",
            "tasks": [],
        }

        self.assertEqual(validate_payload(payload), [])

    def test_rejects_duplicate_ids_invalid_splits_and_missing_safety_checks(self):
        task = self._customer_service_task()
        task["safety_checks"] = []
        payload = {
            "benchmark_id": "test",
            "language": "ar",
            "environment": "PolyGlotCustomerServiceAr-v1",
            "tasks": [dict(task), {**task, "split": "validation"}],
        }

        errors = validate_payload(payload)
        self.assertTrue(any("duplicates task id" in error for error in errors))
        self.assertTrue(any("split must" in error for error in errors))
        self.assertTrue(any("safety_checks" in error for error in errors))

    def test_rejects_unknown_scenario_for_active_environment(self):
        task = self._customer_service_task(scenario_id="cs_ar_missing", expected_outcome="status")
        payload = {
            "benchmark_id": "test-ar",
            "language": "ar",
            "environment": "PolyGlotCustomerServiceAr-v1",
            "tasks": [task],
        }

        errors = validate_payload(payload)
        self.assertTrue(any("unknown customer-service scenario" in error for error in errors))

    def test_rejects_outcome_oracle_that_disagrees_with_scenario_goal(self):
        scenario_id = next(key for key, goal in SCENARIO_GOALS.items() if goal != "refund")
        task = self._customer_service_task(scenario_id=scenario_id, expected_outcome="refund")
        payload = {
            "benchmark_id": "test-ar",
            "language": "ar",
            "environment": "PolyGlotCustomerServiceAr-v1",
            "tasks": [task],
        }

        errors = validate_payload(payload)
        self.assertTrue(any("does not match scenario" in error for error in errors))

    def test_public_files_reject_hidden_task_content(self):
        payload = {
            "benchmark_id": "test-ar",
            "language": "ar",
            "environment": "PolyGlotCustomerServiceAr-v1",
            "tasks": [self._customer_service_task(split="hidden")],
        }

        errors = validate_payload(payload)
        self.assertTrue(any("hidden test data in a public benchmark" in error for error in errors))
        self.assertEqual(validate_payload(payload, allow_hidden=True), [])

    def test_protected_file_rejects_development_tasks(self):
        payload = {
            "benchmark_id": "test-ar",
            "language": "ar",
            "environment": "PolyGlotCustomerServiceAr-v1",
            "tasks": [self._customer_service_task(split="development")],
        }

        errors = validate_payload(payload, allow_hidden=True)
        self.assertTrue(any("protected benchmark must have split='hidden'" in error for error in errors))

    def test_rejects_unmarked_empty_benchmark(self):
        errors = validate_payload({"benchmark_id": "empty", "language": "en", "tasks": []})
        self.assertTrue(any("empty tasks array" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
