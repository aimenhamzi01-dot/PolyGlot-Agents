"""OpenAI-compatible agent adapter for the verifiable benchmark."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from environments.customer_service_agent import RESOLUTIONS, TOOLS, make_action

SYSTEM_PROMPT = """أنت وكيل خدمة عملاء داخل محاكاة قابلة للتحقق.
أعد JSON صالحًا فقط، دون Markdown أو شرح، بهذه المفاتيح:
{{"tool":"...","order_id":"","approval_id":"","resolution":"other","message":""}}
اختر tool من: {tools}
واختر resolution من: {resolutions}
لا تدّع تنفيذ إجراء قبل أن تؤكده نتيجة الأداة. لا تخترع رقم طلب أو موافقة.
""".format(tools=", ".join(TOOLS), resolutions=", ".join(RESOLUTIONS))


def parse_action(content: str) -> dict[str, str]:
    text = content.strip()
    if text.startswith("```"):
        text = text.strip("`").strip()
        if text.startswith("json"):
            text = text[4:].strip()
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("model did not return valid JSON action") from exc
    if not isinstance(payload, dict):
        raise ValueError("model action must be a JSON object")
    required = ("tool", "order_id", "approval_id", "resolution", "message")
    missing = [key for key in required if key not in payload]
    if missing:
        raise ValueError("model action missing keys: " + ", ".join(missing))
    for key in required:
        if not isinstance(payload[key], str):
            raise ValueError(f"model action field {key} must be a string")
    return payload


class OpenAICompatibleAgent:
    def __init__(self, base_url: str, model: str, api_key: str = "", timeout: float = 60.0):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.timeout = timeout
        self.raw_responses = 0

    def act(self, observation: dict[str, Any]) -> dict:
        user_prompt = json.dumps({"observation": observation, "available_tools": TOOLS}, ensure_ascii=False)
        body = json.dumps({
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.0,
            "max_tokens": 256,
            "response_format": {"type": "json_object"},
        }).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        request = urllib.request.Request(
            f"{self.base_url}/v1/chat/completions", data=body, headers=headers, method="POST"
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError) as exc:
            raise RuntimeError(f"model API unavailable: {exc}") from exc
        try:
            content = payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ValueError("model API response has no assistant content") from exc
        self.raw_responses += 1
        action = parse_action(content)
        return make_action(**action)


def from_environment() -> OpenAICompatibleAgent:
    base_url = os.getenv("POLYGLOT_AGENT_BASE_URL", "http://localhost:8080")
    model = os.getenv("POLYGLOT_AGENT_MODEL", "polyglot-ar")
    return OpenAICompatibleAgent(base_url, model, os.getenv("POLYGLOT_AGENT_API_KEY", ""))
