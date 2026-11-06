"""Open, non-whitelist language registry and source-tag resolver."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import yaml

try:
    from scripts.language_codes import canonical_iso639
except ModuleNotFoundError:  # direct execution: python scripts/language_registry.py
    from language_codes import canonical_iso639

DEFAULT_PATH = Path("configs/languages.yaml")


def load_registry(path: Path = DEFAULT_PATH) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    payload.setdefault("defaults", {})
    payload.setdefault("languages", {})
    if not isinstance(payload["languages"], dict):
        raise ValueError("languages registry must contain a mapping")
    return payload


def _profile_for(raw_tag: str, canonical: str, registry: dict[str, Any]) -> tuple[str, dict[str, Any] | None]:
    raw = raw_tag.lower().replace("_", "-")
    profiles = registry.get("languages", {})
    if canonical in profiles:
        return canonical, profiles[canonical]
    for code, profile in profiles.items():
        tags = {str(tag).lower().replace("_", "-") for tag in profile.get("source_tags", [])}
        if raw in tags:
            return code, profile
    return canonical, None


def resolve(tag: str, registry: dict[str, Any] | None = None) -> dict[str, Any]:
    """Resolve any valid ISO/BCP-47 source tag without requiring a registry entry."""
    registry = registry or load_registry()
    raw = str(tag or "").strip()
    if not raw:
        raise ValueError("language tag cannot be empty")
    canonical = canonical_iso639(raw)
    try:
        import langcodes
        language = langcodes.Language.get(raw.replace("_", "-"))
        bcp47 = language.to_tag()
        script = language.script
        region = language.territory
    except ImportError as exc:  # pragma: no cover - requirements provide langcodes
        raise RuntimeError("Install project dependencies: pip install -r scripts/requirements.txt") from exc
    code, profile = _profile_for(raw, canonical, registry)
    return {
        "lang_code": code,
        "source_lang_tag": raw,
        "bcp47": bcp47,
        "script": script or (profile or {}).get("scripts", [None])[0],
        "region": region,
        "dialect": (profile or {}).get("dialect"),
        "registered": profile is not None,
        "registry_status": (profile or {}).get("stage", "open_unregistered"),
        "resource_level": (profile or {}).get("resource_level"),
        "native_review_required": (profile or {}).get("native_review_required", registry.get("defaults", {}).get("require_native_speaker_review", True)),
    }


def enrich_record(record: dict[str, Any], registry: dict[str, Any] | None = None) -> dict[str, Any]:
    """Add language metadata while preserving the exact source tag."""
    source_tag = record.get("source_lang_tag") or record.get("bcp47") or record.get("lang_code")
    metadata = resolve(str(source_tag), registry)
    result = dict(record)
    result.update({key: value for key, value in metadata.items() if value is not None})
    result["lang_code"] = metadata["lang_code"]
    result["language_resolution"] = "source_tag"
    return result


def validate_language(code: str, registry: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return machine-readable checks for a newly proposed language code."""
    registry = registry or load_registry()
    metadata = resolve(code, registry)
    checks = {
        "valid_iso_or_bcp47": True,
        "canonical_directory_code": bool(metadata["lang_code"] and metadata["lang_code"] != "und"),
        "source_tag_preserved": metadata["source_lang_tag"] == code,
        "script_known_or_reviewable": bool(metadata.get("script") or metadata.get("native_review_required")),
        "open_registry": True,
        "registered_profile": metadata["registered"],
    }
    # Registry presence is useful metadata, not a whitelist requirement. A
    # valid ISO/BCP-47 tag may enter staging and be routed for review.
    required_checks = [name for name in checks if name != "registered_profile"]
    return {"code": code, "metadata": metadata, "checks": checks, "ready_for_ingestion": all(checks[name] for name in required_checks)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--code", required=True, help="ISO 639 or BCP-47 language tag")
    parser.add_argument("--registry", type=Path, default=DEFAULT_PATH)
    args = parser.parse_args()
    try:
        result = validate_language(args.code, load_registry(args.registry))
    except (ValueError, RuntimeError) as exc:
        parser.error(str(exc))
    print(yaml.safe_dump(result, allow_unicode=True, sort_keys=False))


if __name__ == "__main__":
    main()
