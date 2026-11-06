import unittest
import json
from unittest.mock import patch

from evaluation.openai_agent import OpenAICompatibleAgent, SYSTEM_PROMPT, parse_action


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

    def test_prompt_distinguishes_refund_status_and_escalation_flows(self):
        self.assertIn("refund فقط بعد نجاح issue_refund في هذه الحلقة", SYSTEM_PROMPT)
        self.assertIn("already_refunded فقط إذا أكدت check_refund_policy", SYSTEM_PROMPT)
        self.assertIn("لا تستخدم already_refunded لمجرد نجاح استرداد جديد", SYSTEM_PROMPT)
        self.assertIn("إذا لم يذكر العميل رقم الطلب، استخدم ask_order_id", SYSTEM_PROMPT)
        self.assertIn("إذا رفض العميل مشاركة الرقم أو طلب موظفًا، استخدم escalate", SYSTEM_PROMPT)

    def test_openai_compatible_agent_exposes_provider_token_usage(self):
        action_payload = {
            "tool": "lookup_order",
            "order_id": "A102",
            "approval_id": "",
            "resolution": "other",
            "message": "",
        }
        response_payload = {
            "choices": [{"message": {"content": json.dumps(action_payload)}}],
            "usage": {"prompt_tokens": 23, "completion_tokens": 7, "total_tokens": 30},
        }

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self):
                return json.dumps(response_payload).encode("utf-8")

        agent = OpenAICompatibleAgent("http://mock-provider", "mock-model")
        with patch("evaluation.openai_agent.urllib.request.urlopen", return_value=FakeResponse()):
            action = agent.act({"customer_message": "Where is order A102?"})

        self.assertEqual(action["tool"], 0)
        self.assertEqual(agent.raw_responses, 1)
        self.assertEqual(
            agent.get_last_call_usage(),
            {"prompt_tokens": 23, "completion_tokens": 7, "total_tokens": 30},
        )

    def test_usage_normalization_accepts_input_output_token_names(self):
        self.assertEqual(
            OpenAICompatibleAgent._normalize_usage({"input_tokens": 12, "output_tokens": 9}),
            {"prompt_tokens": 12, "completion_tokens": 9, "total_tokens": 21},
        )

    def test_gpt_model_uses_max_completion_tokens(self):
        action = {"tool": "lookup_order", "order_id": "A102", "approval_id": "",
                  "resolution": "other", "message": ""}
        response_payload = {"choices": [{"message": {"content": json.dumps(action)}}]}

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self):
                return json.dumps(response_payload).encode("utf-8")

        agent = OpenAICompatibleAgent("http://mock-provider", "gpt-6-luna")
        with patch("evaluation.openai_agent.urllib.request.urlopen", return_value=FakeResponse()) as send:
            agent.act({"customer_message": "Where is order A102?"})

        request_body = json.loads(send.call_args.args[0].data.decode("utf-8"))
        self.assertEqual(request_body["max_completion_tokens"], 256)
        self.assertNotIn("max_tokens", request_body)


if __name__ == "__main__":
    unittest.main()
