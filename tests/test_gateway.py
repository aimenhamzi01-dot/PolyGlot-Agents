import json
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from serving import gateway
from serving.tool_registry import get_tool_definitions


class ToolApiTests(unittest.TestCase):
    def setUp(self):
        self.gateway_key = patch.object(gateway, "GATEWAY_API_KEY", "test-gateway-key")
        self.gateway_key.start()
        self.addCleanup(self.gateway_key.stop)
        self.client = TestClient(gateway.app)

    def test_tool_registry_requires_authentication(self):
        response = self.client.get("/v1/tools")
        self.assertEqual(response.status_code, 401)

    def test_tool_registry_returns_localized_openai_schemas(self):
        response = self.client.get("/v1/tools?locale=ja", headers={"Authorization": "Bearer test-gateway-key"})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["locale"], "ja")
        chinese = self.client.get("/v1/tools?locale=zh", headers={"Authorization": "Bearer test-gateway-key"})
        self.assertEqual(chinese.json()["locale"], "zh-Hans")
        names = {item["function"]["name"] for item in payload["tools"]}
        self.assertEqual(names, {"lookup_order", "check_refund_policy", "request_approval", "issue_refund",
                                 "ask_order_id", "escalate", "send_response", "close_case"})
        lookup = next(item["function"] for item in payload["tools"] if item["function"]["name"] == "lookup_order")
        self.assertIn("注文番号", lookup["description"])
        self.assertEqual(lookup["parameters"]["required"], ["order_id"])
        send_response = next(item["function"] for item in payload["tools"]
                             if item["function"]["name"] == "send_response")
        self.assertIn("refund", send_response["parameters"]["properties"]["resolution"]["enum"])

    def test_tool_registry_rejects_unsupported_locale(self):
        response = self.client.get("/v1/tools?locale=xx", headers={"Authorization": "Bearer test-gateway-key"})
        self.assertEqual(response.status_code, 422)
        self.assertIn("Supported primary language codes", response.json()["detail"])

    def test_chat_gateway_forwards_tool_calls_without_executing_them(self):
        expected_tools = get_tool_definitions("ru")
        captured = {}

        class FakeResponse:
            status_code = 200

            @staticmethod
            def json():
                return {"choices": [{"message": {"tool_calls": [{"type": "function", "function": {
                    "name": "lookup_order", "arguments": json.dumps({"order_id": "A102"})
                }}]}}]}

        class FakeAsyncClient:
            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *_args):
                return False

            async def post(self, url, *, json, headers):
                captured["url"] = url
                captured["body"] = json
                return FakeResponse()

        with patch.object(gateway, "DEFAULT_MODEL", "test-model"), \
                patch("serving.gateway.httpx.AsyncClient", FakeAsyncClient):
            response = self.client.post(
                "/v1/chat/completions",
                headers={"Authorization": "Bearer test-gateway-key"},
                json={
                    "messages": [{"role": "user", "content": "Проверьте заказ A102."}],
                    "tools": expected_tools,
                    "tool_choice": "auto",
                    "parallel_tool_calls": False,
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(captured["body"]["tools"], expected_tools)
        self.assertEqual(captured["body"]["tool_choice"], "auto")
        self.assertFalse(captured["body"]["parallel_tool_calls"])
        self.assertEqual(response.json()["choices"][0]["message"]["tool_calls"][0]["function"]["name"],
                         "lookup_order")


class ToolSchemaConsistencyTests(unittest.TestCase):
    def test_tool_schema_names_match_environment_tools_for_every_locale(self):
        from environments.customer_service_agent import TOOLS, available_locales

        for locale in available_locales():
            with self.subTest(locale=locale):
                names = [item["function"]["name"] for item in get_tool_definitions(locale)]
                self.assertEqual(names, list(TOOLS))


if __name__ == "__main__":
    unittest.main()
