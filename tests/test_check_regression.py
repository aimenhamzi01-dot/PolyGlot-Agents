import unittest

from evaluation.check_regression import check_report


class RegressionTests(unittest.TestCase):
    def test_baseline_metrics_pass_default_thresholds(self):
        report = {"aggregate": {
            "success_rate": 1.0,
            "safe_completion_rate": 1.0,
            "unsafe_action_rate": 0.0,
            "unsupported_claim_rate": 0.0,
        }}
        self.assertEqual(check_report(report), [])

    def test_safety_regression_is_reported(self):
        report = {"aggregate": {
            "success_rate": 0.95,
            "safe_completion_rate": 0.8,
            "unsafe_action_rate": 0.1,
            "unsupported_claim_rate": 0.05,
        }}
        failures = check_report(report)
        self.assertEqual(len(failures), 4)
        self.assertTrue(any("unsafe_action_rate" in failure for failure in failures))
        self.assertTrue(any("below minimum" in failure for failure in failures))

    def test_custom_thresholds_support_non_perfect_experimental_models(self):
        report = {"aggregate": {
            "success_rate": 0.75,
            "safe_completion_rate": 0.9,
            "unsafe_action_rate": 0.02,
            "unsupported_claim_rate": 0.01,
        }}
        thresholds = {
            "success_rate_min": 0.7,
            "safe_completion_rate_min": 0.85,
            "unsafe_action_rate_max": 0.05,
            "unsupported_claim_rate_max": 0.02,
        }
        self.assertEqual(check_report(report, thresholds), [])

    def test_missing_metric_fails_closed(self):
        self.assertTrue(check_report({"aggregate": {}}))


if __name__ == "__main__":
    unittest.main()
