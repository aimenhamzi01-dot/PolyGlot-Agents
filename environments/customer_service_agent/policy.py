"""Deterministic policy decisions for sensitive customer-service actions.

The policy layer is deliberately independent from Gymnasium, locale wording, and
reward calculation. It returns stable reason codes so a tool gateway can audit or
reject model proposals before state mutation.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PolicyDecision:
    """Machine-readable policy result suitable for event logs and adapters."""

    allowed: bool
    code: str


class CustomerServicePolicy:
    """Enforce intent, eligibility, approval freshness, and idempotency rules."""

    REFUND_WINDOW_DAYS = 30

    def evaluate_refund(self, *, order: dict[str, Any] | None, scenario_goal: str, refund_state: str) -> PolicyDecision:
        if order is None:
            return PolicyDecision(False, "order_not_verified")
        if refund_state == "already_refunded" or order.get("already_refunded"):
            return PolicyDecision(False, "already_refunded")
        eligible = order.get("status") == "delivered" and order.get("age_days", self.REFUND_WINDOW_DAYS + 1) <= self.REFUND_WINDOW_DAYS
        return PolicyDecision(eligible, "eligible" if eligible else "ineligible")

    def authorize_approval(self, *, order: dict[str, Any] | None, scenario_goal: str, policy_result: str, refund_state: str) -> PolicyDecision:
        if order is None:
            return PolicyDecision(False, "order_not_verified")
        if scenario_goal != "refund":
            return PolicyDecision(False, "customer_intent_missing")
        if policy_result != "eligible":
            return PolicyDecision(False, "refund_policy_not_eligible")
        if refund_state != "not_issued":
            return PolicyDecision(False, "refund_not_actionable")
        return PolicyDecision(True, "approval_allowed")

    def authorize_refund(
        self,
        *,
        order: dict[str, Any] | None,
        scenario_goal: str,
        policy_result: str,
        approval_id: str,
        supplied_approval_id: str,
        refund_state: str,
    ) -> PolicyDecision:
        if order is None:
            return PolicyDecision(False, "order_not_verified")
        if scenario_goal != "refund":
            return PolicyDecision(False, "customer_intent_missing")
        if policy_result != "eligible":
            return PolicyDecision(False, "refund_policy_not_eligible")
        if not approval_id:
            return PolicyDecision(False, "approval_missing")
        if supplied_approval_id != approval_id:
            return PolicyDecision(False, "approval_mismatch")
        if refund_state != "not_issued":
            return PolicyDecision(False, "refund_already_processed")
        return PolicyDecision(True, "refund_allowed")


__all__ = ["CustomerServicePolicy", "PolicyDecision"]
