import unittest

from evaluation.openai_agent import parse_action


class OpenAIAgentTests(unittest.TestCase):
    def test_parse_action_accepts_strict_json(self):
        payload = parse_action('{"tool":"lookup_order","order_id":"A102","approval_id":"","resolution":"other","message":""}')
        self.assertEqual(payload["tool"], "lookup_order")

    def test_parse_action_accepts_json_fence(self):
        payload = parse_action('```json\n{"tool":"escalate","order_id":"","approval_id":"","resolution":"other","message":""}\n```')
        self.assertEqual(payload["tool"], "escalate")

    def test_parse_action_rejects_missing_field(self):
        with self.assertRaises(ValueError):
            parse_action('{"tool":"lookup_order"}')


if __name__ == "__main__":
    unittest.main()
