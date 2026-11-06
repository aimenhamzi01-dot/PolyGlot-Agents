"""Fail-closed rights checks for automated ingestion."""
from __future__ import annotations

from typing import Any


class RightsError(ValueError):
    """Raised when a source or record lacks the rights evidence required to ingest it."""


_ACCEPTED_STATUS = {"reviewed", "approved_for_import"}
_BLOCKED_LICENSE_VALUES = {"", "unknown", "unclear", "tbd", "proprietary_unspecified"}
_REQUIRED_SOURCE_FIELDS = ("dataset_card", "license", "license_url", "rights_status", "allowed_uses", "commercial_use")


def validate_source(name: str, cfg: dict[str, Any]) -> None:
    """Validate source metadata before a connector is allowed to run."""
    missing = [field for field in _REQUIRED_SOURCE_FIELDS if not cfg.get(field)]
    if missing:
        raise RightsError(f"{name}: missing rights metadata: {', '.join(missing)}")
    license_name = str(cfg["license"]).strip().lower()
    if license_name in _BLOCKED_LICENSE_VALUES:
        raise RightsError(f"{name}: license is unknown or unclear")
    if str(cfg["rights_status"]).lower() not in _ACCEPTED_STATUS:
        raise RightsError(f"{name}: rights_status must be reviewed or approved_for_import")
    if not isinstance(cfg["allowed_uses"], list) or not cfg["allowed_uses"]:
        raise RightsError(f"{name}: allowed_uses must be a non-empty list")
    if cfg.get("redistribution") is not True:
        raise RightsError(f"{name}: redistribution must be explicitly true for repository ingestion")


def validate_record(record: dict[str, Any]) -> None:
    """Ensure every normalized record retains item-level rights provenance."""
    required = ("source", "source_url", "license", "license_url", "source_revision", "provenance")
    missing = [field for field in required if not record.get(field)]
    if missing:
        raise RightsError(f"record {record.get('id', '<unknown>')}: missing rights fields: {', '.join(missing)}")
    if str(record.get("license", "")).strip().lower() in _BLOCKED_LICENSE_VALUES:
        raise RightsError(f"record {record.get('id', '<unknown>')}: blocked license value")
    provenance = record["provenance"]
    if not isinstance(provenance, dict) or not provenance.get("retrieved_at"):
        raise RightsError(f"record {record.get('id', '<unknown>')}: retrieved_at is required")
