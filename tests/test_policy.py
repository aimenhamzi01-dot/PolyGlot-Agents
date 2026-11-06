import unittest

from environments.customer_service_agent.policy import CustomerServicePolicy


ORDER = {"id": "B203", "status": "delivered", "age_days": 7, "already_refunded": False}


class PolicyTests(unittest.TestCase):
    def setUp(self):
        self.policy = CustomerServicePolicy()

    def test_refund_eligibility_is_separate_from_customer_intent(self):
        self.assertEqual(
            self.policy.evaluate_refund(order=None, scenario_goal="refund", refund_state="unknown").code,
            "order_not_verified",
        )
        self.assertEqual(
            self.policy.evaluate_refund(order=ORDER, scenario_goal="status", refund_state="not_issued").code,
            "eligible",
        )
        decision = self.policy.authorize_approval(
            order=ORDER, scenario_goal="status", policy_result="eligible", refund_state="not_issued"
        )
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.code, "customer_intent_missing")

    def test_approval_requires_eligible_unprocessed_refund(self):
        decision = self.policy.authorize_approval(
            order=ORDER, scenario_goal="refund", policy_result="eligible", refund_state="not_issued"
        )
        self.assertTrue(decision.allowed)
        blocked = self.policy.authorize_approval(
            order=ORDER, scenario_goal="refund", policy_result="eligible", refund_state="already_refunded"
        )
        self.assertFalse(blocked.allowed)
        self.assertEqual(blocked.code, "refund_not_actionable")

    def test_refund_requires_fresh_matching_approval_and_is_idempotent(self):
        kwargs = dict(
            order=ORDER,
            scenario_goal="refund",
            policy_result="eligible",
            approval_id="APR-B203",
            refund_state="not_issued",
        )
        self.assertFalse(self.policy.authorize_refund(**kwargs, supplied_approval_id="APR-FAKE").allowed)
        self.assertTrue(self.policy.authorize_refund(**kwargs, supplied_approval_id="APR-B203").allowed)
        replay = self.policy.authorize_refund(**{**kwargs, "refund_state": "issued"}, supplied_approval_id="APR-B203")
        self.assertFalse(replay.allowed)
        self.assertEqual(replay.code, "refund_already_processed")


if __name__ == "__main__":
    unittest.main()
