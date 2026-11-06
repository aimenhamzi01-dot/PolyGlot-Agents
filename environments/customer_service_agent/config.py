"""Validated configuration loading for the customer-service environment."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "configs" / "environment.yaml"


@dataclass(frozen=True)
class EnvironmentConfig:
    max_episode_steps: int = 10
    success_reward: float = 1.0
    step_cost: float = -0.02
    truncation_penalty: float = -0.25
    invalid_action_penalty: float = -0.2


def load_environment_config(path: Path | str | None = None, profile: str = "customer_service_ar") -> EnvironmentConfig:
    config_path = Path(path) if path is not None else DEFAULT_CONFIG_PATH
    try:
        payload: Any = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except OSError as exc:
        raise ValueError(f"cannot read environment config {config_path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("environment config root must be a mapping")
    values = payload.get(profile, payload.get("customer_service", {}))
    if not isinstance(values, dict):
        raise ValueError(f"environment config profile {profile!r} must be a mapping")
    defaults = EnvironmentConfig()
    numeric = {
        "max_episode_steps": int(values.get("max_episode_steps", defaults.max_episode_steps)),
        "success_reward": float(values.get("success_reward", defaults.success_reward)),
        "step_cost": float(values.get("step_cost", defaults.step_cost)),
        "truncation_penalty": float(values.get("truncation_penalty", defaults.truncation_penalty)),
        "invalid_action_penalty": float(values.get("invalid_action_penalty", defaults.invalid_action_penalty)),
    }
    if numeric["max_episode_steps"] < 1:
        raise ValueError("max_episode_steps must be at least 1")
    if numeric["success_reward"] <= 0:
        raise ValueError("success_reward must be positive")
    if numeric["step_cost"] > 0 or numeric["truncation_penalty"] > 0 or numeric["invalid_action_penalty"] > 0:
        raise ValueError("cost and penalty values must be non-positive")
    return EnvironmentConfig(**numeric)


__all__ = ["EnvironmentConfig", "DEFAULT_CONFIG_PATH", "load_environment_config"]
