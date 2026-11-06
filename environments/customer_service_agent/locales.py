"""Locale-pack loader for the language-neutral customer-service environment."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

LOCALES_DIR = Path(__file__).with_name("locales")
_REQUIRED_KEYS = {"code", "bcp47", "name", "script", "status_labels", "status_terms", "tool_descriptions", "customer_messages"}


def load_locale(locale: str = "ar") -> dict[str, Any]:
    """Load and validate a locale pack by ISO 639-1 or BCP-47 base code."""
    key = locale.lower().split("-")[0]
    path = LOCALES_DIR / f"{key}.yaml"
    if not path.exists():
        raise ValueError(f"unsupported locale pack: {locale}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    missing = _REQUIRED_KEYS - set(data)
    if missing:
        raise ValueError(f"locale pack {locale} missing keys: {sorted(missing)}")
    return data


def available_locales() -> tuple[str, ...]:
    return tuple(sorted(path.stem for path in LOCALES_DIR.glob("*.yaml")))
