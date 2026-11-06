"""OpenAI-compatible agent adapter for the verifiable benchmark."""
from __future__ import annotations

import json
import os
from threading import Lock, local
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
مع الأدوات غير send_response استخدم resolution="other".
في send_response يجب أن يطابق resolution نتيجة الأدوات المؤكدة: refund فقط بعد نجاح issue_refund في هذه الحلقة؛ already_refunded فقط إذا أكدت check_refund_policy وجود استرداد سابق قبل أي issue_refund؛ declined فقط بعد نتيجة ineligible؛ escalated فقط بعد تأكيد escalate؛ status فقط لحالة أكدها lookup_order؛ needs_info إذا رفض العميل تقديم رقم الطلب.
لا تستخدم already_refunded لمجرد نجاح استرداد جديد. يجب أن تتوافق قيمة resolution مع نص message ومع آخر حالة refund_state.
إذا لم يذكر العميل رقم الطلب، استخدم ask_order_id لطلبه قبل إنهاء الحالة، ثم اتبع رد العميل.
إذا رفض العميل مشاركة الرقم أو طلب موظفًا، استخدم escalate قبل send_response؛ لا تختر needs_info قبل سؤال العميل أو بعد طلب التصعيد.
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
        self._response_lock = Lock()
        self._call_state = local()

    @staticmethod
    def _normalize_usage(usage: Any) -> dict[str, int] | None:
        """Keep standard token counts when a compatible provider returns them."""
        if not isinstance(usage, dict):
            return None
        normalized: dict[str, int] = {}
        for name, alternatives in {
            "prompt_tokens": ("prompt_tokens", "input_tokens"),
            "completion_tokens": ("completion_tokens", "output_tokens"),
            "total_tokens": ("total_tokens",),
        }.items():
            for key in alternatives:
                value = usage.get(key)
                if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
                    normalized[name] = value
                    break
        if "total_tokens" not in normalized and {
            "prompt_tokens", "completion_tokens"
        }.issubset(normalized):
            normalized["total_tokens"] = normalized["prompt_tokens"] + normalized["completion_tokens"]
        return normalized or None

    def get_last_call_usage(self) -> dict[str, int] | None:
        """Return usage for this thread's most recent request, if provided."""
        usage = getattr(self._call_state, "usage", None)
        return dict(usage) if usage is not None else None

    def act(self, observation: dict[str, Any]) -> dict:
        self._call_state.usage = None
        user_prompt = json.dumps({"observation": observation, "available_tools": TOOLS}, ensure_ascii=False)
        request_body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.0,
            "response_format": {"type": "json_object"},
        }
        if self.model.lower().startswith("gpt-"):
            request_body["max_completion_tokens"] = 256
        else:
            request_body["max_tokens"] = 256
        body = json.dumps(request_body).encode("utf-8")
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
        usage_payload = payload.get("usage") if isinstance(payload, dict) else None
        self._call_state.usage = self._normalize_usage(usage_payload)
        with self._response_lock:
            self.raw_responses += 1
        try:
            content = payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ValueError("model API response has no assistant content") from exc
        action = parse_action(content)
        return make_action(**action)


def from_environment() -> OpenAICompatibleAgent:
    base_url = os.getenv("POLYGLOT_AGENT_BASE_URL", "http://localhost:8080")
    model = os.getenv("POLYGLOT_AGENT_MODEL", "polyglot-ar")
    return OpenAICompatibleAgent(base_url, model, os.getenv("POLYGLOT_AGENT_API_KEY", ""))
