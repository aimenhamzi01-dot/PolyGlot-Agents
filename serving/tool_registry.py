"""OpenAI-compatible function schemas for the customer-service agent tools."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

LOCALES_DIR = Path(__file__).resolve().parents[1] / "environments" / "customer_service_agent" / "locales"

_TOOL_PARAMETERS: dict[str, dict[str, Any]] = {
    "lookup_order": {
        "type": "object",
        "properties": {"order_id": {"type": "string"}},
        "required": ["order_id"],
        "additionalProperties": False,
    },
    "check_refund_policy": {"type": "object", "properties": {}, "additionalProperties": False},
    "request_approval": {"type": "object", "properties": {}, "additionalProperties": False},
    "issue_refund": {
        "type": "object",
        "properties": {"approval_id": {"type": "string"}},
        "required": ["approval_id"],
        "additionalProperties": False,
    },
    "ask_order_id": {"type": "object", "properties": {}, "additionalProperties": False},
    "escalate": {"type": "object", "properties": {}, "additionalProperties": False},
    "send_response": {
        "type": "object",
        "properties": {
            "resolution": {
                "type": "string",
                "enum": ["status", "refund", "declined", "escalated", "needs_info", "already_refunded", "other"],
            },
            "message": {"type": "string"},
            "order_id": {"type": "string"},
            "approval_id": {"type": "string"},
        },
        "required": ["resolution", "message"],
        "additionalProperties": False,
    },
    "close_case": {"type": "object", "properties": {}, "additionalProperties": False},
}


def available_tool_locales() -> tuple[str, ...]:
    """Return language pack identifiers that can provide tool descriptions."""
    return tuple(sorted(path.stem for path in LOCALES_DIR.glob("*.yaml")))


def canonical_tool_locale(locale: str = "en") -> str:
    """Resolve an ISO or BCP-47 input to the locale pack's canonical tag."""
    requested = locale.replace("_", "-").split("-")[0].lower()
    if requested not in available_tool_locales():
        raise ValueError(f"unsupported tool-description locale: {locale}")
    locale_path = LOCALES_DIR / f"{requested}.yaml"
    pack = yaml.safe_load(locale_path.read_text(encoding="utf-8"))
    return str(pack.get("bcp47", requested))


def get_tool_definitions(locale: str = "en") -> list[dict[str, Any]]:
    """Return OpenAI Chat Completions tool declarations for a supported locale.

    These declarations allow a model to propose tool calls. They do not execute
    tools or authorize side effects; applications must dispatch proposals through
    a separately authenticated and policy-aware executor.
    """
    requested = locale.replace("_", "-").split("-")[0].lower()
    if requested not in available_tool_locales():
        raise ValueError(f"unsupported tool-description locale: {locale}")
    locale_path = LOCALES_DIR / f"{requested}.yaml"
    pack = yaml.safe_load(locale_path.read_text(encoding="utf-8"))
    descriptions = pack.get("tool_descriptions", {})
    missing = set(_TOOL_PARAMETERS) - set(descriptions)
    if missing:
        raise ValueError(f"locale {requested!r} is missing tool descriptions: {', '.join(sorted(missing))}")
    return [
        {
            "type": "function",
            "function": {
                "name": name,
                "description": descriptions[name],
                "parameters": _TOOL_PARAMETERS[name],
            },
        }
        for name in _TOOL_PARAMETERS
    ]


__all__ = ["available_tool_locales", "canonical_tool_locale", "get_tool_definitions"]
