#!/usr/bin/env python3
"""Validate locale-pack structure and shared environment contracts."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import yaml

from environments.customer_service_agent import (
    DECLINE_EVIDENCE,
    ESCALATION_EVIDENCE,
    REFUND_EVIDENCE,
    TOOLS,
    available_locales,
)
from environments.customer_service_agent.locales import LOCALES_DIR

_REQUIRED_TOP_LEVEL = {"code", "bcp47", "name", "script", "status_labels", "status_terms", "tool_descriptions", "customer_messages"}
_STATUS_KEYS = {"delayed", "in_transit", "delivered"}
_CUSTOMER_MESSAGE_KEYS = {
    "status", "refund", "already_refunded", "decline", "handoff",
    "followup", "order_id_followup", "refusal_followup",
}
_MESSAGES_WITH_ORDER_ID = {"status", "refund", "already_refunded", "decline", "order_id_followup"}
_EVIDENCE_MAPS = {
    "refund": REFUND_EVIDENCE,
    "decline": DECLINE_EVIDENCE,
    "escalation": ESCALATION_EVIDENCE,
}


def _non_empty_strings(value: Any) -> bool:
    return isinstance(value, (list, tuple)) and bool(value) and all(
        isinstance(item, str) and item.strip() for item in value
    )


def validate_locale_pack(code: str, pack: Any, source: str = "locale") -> list[str]:
    """Return actionable contract errors for one decoded locale pack."""
    if not isinstance(pack, dict):
        return [f"{source}: root must be a YAML mapping"]

    errors: list[str] = []
    missing = _REQUIRED_TOP_LEVEL - set(pack)
    if missing:
        errors.append(f"{source}: missing required keys: {', '.join(sorted(missing))}")
    if pack.get("code") != code:
        errors.append(f"{source}: code must match locale filename {code!r}")
    for field in ("bcp47", "name", "script"):
        if not isinstance(pack.get(field), str) or not pack[field].strip():
            errors.append(f"{source}: {field} must be a non-empty string")
    bcp47 = pack.get("bcp47")
    if isinstance(bcp47, str) and bcp47.split("-")[0].lower() != code.lower():
        errors.append(f"{source}: bcp47 primary language must match code {code!r}")

    status_labels = pack.get("status_labels")
    if not isinstance(status_labels, dict) or set(status_labels) != _STATUS_KEYS or any(
        not isinstance(value, str) or not value.strip() for value in status_labels.values()
    ):
        errors.append(f"{source}: status_labels must define non-empty delayed, in_transit, and delivered strings")

    status_terms = pack.get("status_terms")
    if not isinstance(status_terms, dict) or set(status_terms) != _STATUS_KEYS or any(
        not _non_empty_strings(value) for value in status_terms.values()
    ):
        errors.append(f"{source}: status_terms must define non-empty string lists for all status labels")

    tool_descriptions = pack.get("tool_descriptions")
    if not isinstance(tool_descriptions, dict) or set(tool_descriptions) != set(TOOLS) or any(
        not isinstance(value, str) or not value.strip() for value in tool_descriptions.values()
    ):
        errors.append(f"{source}: tool_descriptions must define non-empty descriptions for exactly: {', '.join(TOOLS)}")

    customer_messages = pack.get("customer_messages")
    if not isinstance(customer_messages, dict):
        errors.append(f"{source}: customer_messages must be a mapping")
    else:
        missing_messages = _CUSTOMER_MESSAGE_KEYS - set(customer_messages)
        if missing_messages:
            errors.append(f"{source}: missing customer_messages: {', '.join(sorted(missing_messages))}")
        for key in _CUSTOMER_MESSAGE_KEYS & set(customer_messages):
            value = customer_messages[key]
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{source}: customer_messages.{key} must be a non-empty string")
            elif key in _MESSAGES_WITH_ORDER_ID and "{id}" not in value:
                errors.append(f"{source}: customer_messages.{key} must include the {{id}} placeholder")

    available = set(available_locales())
    if code not in available:
        errors.append(f"{source}: locale code {code!r} is not discoverable by available_locales()")
    for evidence_name, evidence_map in _EVIDENCE_MAPS.items():
        if code not in evidence_map or not _non_empty_strings(evidence_map.get(code)):
            errors.append(f"{source}: missing non-empty {evidence_name} evidence terms for {code!r}")
    return errors


def validate_locale_file(path: Path) -> list[str]:
    """Read and validate one locale YAML file."""
    try:
        pack = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        return [f"{path}: cannot read valid UTF-8 YAML ({exc})"]
    return validate_locale_pack(path.stem, pack, str(path))


def validate_locale_dir(locale_dir: Path = LOCALES_DIR) -> list[str]:
    """Validate every YAML locale pack in a directory."""
    paths = sorted((*locale_dir.glob("*.yaml"), *locale_dir.glob("*.yml")))
    if not paths:
        return [f"{locale_dir}: no locale YAML files found"]
    return [error for path in paths for error in validate_locale_file(path)]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--locale-dir", type=Path, default=LOCALES_DIR, help="directory containing locale YAML packs")
    args = parser.parse_args()
    failures = validate_locale_dir(args.locale_dir)
    if failures:
        print("Locale validation failed:")
        for failure in failures:
            print(f"- {failure}")
        raise SystemExit(1)
    count = len(list(args.locale_dir.glob("*.yaml"))) + len(list(args.locale_dir.glob("*.yml")))
    print(f"Validated {count} locale pack(s) in {args.locale_dir}.")


if __name__ == "__main__":
    main()
