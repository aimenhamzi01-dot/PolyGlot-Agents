import unittest
import json
from unittest.mock import patch

from evaluation.openai_agent import OpenAICompatibleAgent, SYSTEM_PROMPT, build_system_prompt, parse_action


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

    def test_system_prompt_is_localized_and_preserves_safe_refund_sequence(self):
        english = build_system_prompt("en")
        french = build_system_prompt("fr-CA")
        spanish = build_system_prompt("es-MX")
        chinese = build_system_prompt("zh-Hans")

        self.assertIn("Write the final customer-facing message in English", english)
        self.assertIn("issue_refund succeeds", english)
        self.assertIn("Rédigez le message final destiné au client en French", french)
        self.assertIn("N'utilisez pas close_case", french)
        self.assertIn("Escribe el mensaje final al cliente en español", spanish)
        self.assertIn("emite el reembolso solo con el identificador de aprobación recibido", spanish)
        self.assertIn("用简体中文回复客户", chinese)
        self.assertIn("取得真实 approval_id 后才执行退款", chinese)


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

    def test_agent_sends_localized_tool_descriptions_to_provider(self):
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

        agent = OpenAICompatibleAgent("http://mock-provider", "mock-model", locale="fr")
        with patch("evaluation.openai_agent.urllib.request.urlopen", return_value=FakeResponse()) as send:
            agent.act({"customer_message": "Je voudrais connaître l'état de la commande A102."})

        request_body = json.loads(send.call_args.args[0].data.decode("utf-8"))
        self.assertIn("Vous êtes un agent de service client", request_body["messages"][0]["content"])
        user_context = json.loads(request_body["messages"][1]["content"])
        self.assertEqual(user_context["locale"], "fr")
        self.assertIn("Rechercher une commande", user_context["tool_descriptions"]["lookup_order"])
        self.assertIn("issue_refund", user_context["available_tools"])

    def test_agent_sends_chinese_tool_descriptions_to_provider(self):
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

        agent = OpenAICompatibleAgent("http://mock-provider", "mock-model", locale="zh-Hans")
        with patch("evaluation.openai_agent.urllib.request.urlopen", return_value=FakeResponse()) as send:
            agent.act({"customer_message": "请查询订单A102的状态。"})

        request_body = json.loads(send.call_args.args[0].data.decode("utf-8"))
        self.assertIn("中文客服代理", request_body["messages"][0]["content"])
        user_context = json.loads(request_body["messages"][1]["content"])
        self.assertEqual(user_context["locale"], "zh-Hans")
        self.assertIn("根据客户提供的订单号查询订单", user_context["tool_descriptions"]["lookup_order"])

    def test_agent_preserves_original_customer_intent_after_followup(self):
        def response_for(tool):
            action = {"tool": tool, "order_id": "", "approval_id": "",
                      "resolution": "other", "message": ""}

            class FakeResponse:
                def __enter__(self):
                    return self

                def __exit__(self, *_args):
                    return False

                def read(self):
                    return json.dumps({"choices": [{"message": {"content": json.dumps(action)}}]}).encode("utf-8")

            return FakeResponse()

        agent = OpenAICompatibleAgent("http://mock-provider", "mock-model", locale="en")
        first_observation = {"customer_message": "I need a refund but do not have my order number.", "tool_calls": 0}
        followup_observation = {"customer_message": "My order number is A102.", "tool_calls": 1}
        with patch("evaluation.openai_agent.urllib.request.urlopen",
                   side_effect=[response_for("ask_order_id"), response_for("lookup_order")]) as send:
            agent.act(first_observation)
            agent.act(followup_observation)

        second_request = json.loads(send.call_args_list[1].args[0].data.decode("utf-8"))
        second_context = json.loads(second_request["messages"][1]["content"])
        self.assertEqual(second_context["observation"]["customer_message"], "My order number is A102.")
        self.assertEqual(
            second_context["original_customer_message"],
            "I need a refund but do not have my order number.",
        )


if __name__ == "__main__":
    unittest.main()
