#!/usr/bin/env python3
"""Run verifiable agent episodes and write an auditable benchmark report."""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import math
import os
import re
from datetime import datetime, timezone
from pathlib import Path
import time
from typing import Any

try:
    from environments.customer_service_agent import CustomerServiceEnv, ArabicCustomerServiceEnv, make_action, load_locale
except ModuleNotFoundError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from environments.customer_service_agent import CustomerServiceEnv, ArabicCustomerServiceEnv, make_action, load_locale
from scripts.validate_benchmarks import validate_payload
from evaluation.openai_agent import OpenAICompatibleAgent

ORDER_ID = re.compile(r"(?<![A-Za-z0-9])[A-Z]\d{3}(?![A-Za-z0-9])")
STATUS_TEXT = {"متأخرة": "الطلب {id} متأخر، والشحنة متأخرة.", "قيد التوصيل": "الطلب {id} قيد التوصيل.", "تم التسليم": "تم تسليم الطلب {id}."}
OUTCOME_RESOLUTIONS = {
    "status": "status", "refund": "refund", "decline": "declined",
    "already_refunded": "already_refunded", "handoff": "escalated",
}


class RuleBasedAgent:
    """Deterministic locale-aware baseline; intentionally simple, not an LLM."""

    def __init__(self, locale: str = "ar"):
        self.locale = locale.lower().split("-")[0]
        self.pack = load_locale(self.locale)

    def _has_refund_request(self, customer: str) -> bool:
        terms = {"ar": ("استرداد", "المبلغ"), "fr": ("remboursement",), "en": ("refund",), "es": ("reembolso", "devolución"), "zh": ("退款", "退还")}
        return any(term in customer.lower() for term in terms.get(self.locale, ("refund",)))

    def _refusal(self, customer: str) -> bool:
        terms = {"ar": ("لا أريد مشاركة", "لا أستطيع مشاركة"), "fr": ("ne veux pas partager", "ne peux pas partager"), "en": ("do not want to share", "cannot share"), "es": ("no quiero compartir", "no puedo compartir"), "zh": ("不想提供", "无法提供", "不愿提供")}
        return any(term in customer.lower() for term in terms.get(self.locale, terms["en"]))

    def _status_message(self, order_id: str, status: str) -> str:
        labels = self.pack["status_labels"]
        if self.locale == "ar":
            return {"متأخرة": f"تحققت من الطلب {order_id}، والشحنة متأخرة.", "قيد التوصيل": f"تحققت من الطلب {order_id}، وهو قيد التوصيل.", "تم التسليم": f"تم تسليم الطلب {order_id}."}.get(status, f"تحققت من الطلب {order_id}.")
        if self.locale == "fr":
            return {labels["delayed"]: f"J'ai vérifié la commande {order_id}, elle est en retard.", labels["in_transit"]: f"J'ai vérifié la commande {order_id}, elle est en transit.", labels["delivered"]: f"La commande {order_id} a été livrée."}.get(status, f"J'ai vérifié la commande {order_id}.")
        if self.locale == "es":
            return {labels["delayed"]: f"He comprobado el pedido {order_id}; el envío está retrasado.", labels["in_transit"]: f"He comprobado el pedido {order_id}; está en tránsito.", labels["delivered"]: f"El pedido {order_id} ha sido entregado."}.get(status, f"He comprobado el pedido {order_id}.")
        if self.locale == "zh":
            return {labels["delayed"]: f"我已查询订单{order_id}，该包裹目前延误。", labels["in_transit"]: f"我已查询订单{order_id}，目前正在运输中。", labels["delivered"]: f"订单{order_id}已送达。"}.get(status, f"我已查询订单{order_id}。")
        return {labels["delayed"]: f"I checked order {order_id}; it is delayed.", labels["in_transit"]: f"I checked order {order_id}; it is in transit.", labels["delivered"]: f"Order {order_id} was delivered."}.get(status, f"I checked order {order_id}.")

    def act(self, observation: dict[str, Any]) -> dict:
        customer = observation.get("customer_message", "")
        order_id = observation.get("order_id", "")
        mentioned = ORDER_ID.search(customer)
        if observation.get("escalated"):
            message = {"ar": "سأحوّل طلبك إلى موظف مختص للمساعدة.", "fr": "Je vais transférer votre demande à un agent.", "en": "I will transfer your request to a support agent.", "es": "Transferiré su caso a un agente de atención al cliente.", "zh": "我将为您转接人工客服处理。"}.get(self.locale, "I will transfer your request to a support agent.")
            return make_action("send_response", resolution="escalated", message=message)
        if self._refusal(customer) and not order_id:
            return make_action("escalate")
        if not order_id:
            if mentioned:
                return make_action("lookup_order", order_id=mentioned.group(0))
            return make_action("ask_order_id")
        if observation.get("order_status"):
            if observation.get("refund_state") == "already_refunded":
                message = {"ar": f"يوجد استرداد سابق للمبلغ على الطلب {order_id}.", "fr": f"Un remboursement existe déjà pour la commande {order_id}.", "en": f"A refund already exists for order {order_id}.", "es": f"Ya existe un reembolso registrado para el importe del pedido {order_id}.", "zh": f"订单{order_id}已有一笔退款金额记录。"}.get(self.locale, f"A refund already exists for order {order_id}.")
                return make_action("send_response", resolution="already_refunded", message=message)
            if self._has_refund_request(customer):
                if observation.get("policy_result") == "unknown":
                    return make_action("check_refund_policy")
                if observation.get("policy_result") == "eligible":
                    if not observation.get("approval_id"):
                        return make_action("request_approval")
                    if observation.get("refund_state") != "issued":
                        return make_action("issue_refund", approval_id=observation["approval_id"])
                    message = {"ar": f"تم تنفيذ استرداد المبلغ للطلب {order_id}.", "fr": f"Le remboursement de la commande {order_id} a été effectué.", "en": f"The refund for order {order_id} was issued.", "es": f"Se ha procesado el reembolso del importe del pedido {order_id}.", "zh": f"订单{order_id}的退款金额已处理。"}.get(self.locale, f"The refund for order {order_id} was issued.")
                    return make_action("send_response", resolution="refund", message=message, approval_id=observation["approval_id"])
                if observation.get("policy_result") == "ineligible":
                    message = {"ar": f"الطلب {order_id} غير مؤهل للاسترداد حسب المدة المحددة.", "fr": f"La commande {order_id} n'est pas éligible au remboursement.", "en": f"Order {order_id} is not eligible for a refund.", "es": f"El pedido {order_id} no es elegible para el reembolso según el plazo establecido.", "zh": f"订单{order_id}已超过期限，不符合退款条件。"}.get(self.locale, f"Order {order_id} is not eligible for a refund.")
                    return make_action("send_response", resolution="declined", message=message)
            status = observation["order_status"]
            return make_action("send_response", resolution="status", message=self._status_message(order_id, status))
        mentioned = ORDER_ID.search(customer)
        if mentioned:
            return make_action("lookup_order", order_id=mentioned.group(0))
        return make_action("ask_order_id")


class RuleBasedArabicAgent(RuleBasedAgent):
    """Backward-compatible Arabic baseline name."""

    def __init__(self):
        super().__init__(locale="ar")


def select_tasks(tasks: Any, split: str | None = None, source: str = "benchmark") -> list[dict]:
    if not isinstance(tasks, list) or not tasks:
        raise ValueError(f"benchmark contains no tasks: {source}")
    if any(not isinstance(task, dict) for task in tasks):
        raise ValueError(f"every task must be an object: {source}")
    ids = [task.get("id") for task in tasks]
    if any(not isinstance(task.get("id"), str) or not task.get("id")
           or not isinstance(task.get("scenario_id"), str) or not task.get("scenario_id")
           for task in tasks):
        raise ValueError(f"every task must have string id and scenario_id: {source}")
    if len(ids) != len(set(ids)):
        raise ValueError(f"task ids must be unique: {source}")
    if split is None:
        split = "development"
    if split not in {"development", "hidden", "all"}:
        raise ValueError("split must be development, hidden, or all")
    return tasks if split == "all" else [task for task in tasks if task.get("split", "development") == split]


def load_tasks(path: Path, split: str | None = None) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"benchmark root must be an object: {path}")
    return select_tasks(payload.get("tasks"), split=split, source=str(path))


def load_benchmark_for_run(public_path: Path, split: str = "development",
                           protected_path: Path | None = None) -> tuple[dict, list[dict], str]:
    """Load public development tasks and, only when explicitly supplied, protected tests."""
    if split not in {"development", "hidden", "all"}:
        raise ValueError("split must be development, hidden, or all")
    if split == "development" and protected_path is not None:
        raise ValueError("--protected-benchmark is only valid with --split hidden or all")
    if split in {"hidden", "all"} and protected_path is None:
        raise ValueError(f"--split {split} requires --protected-benchmark")

    public_bytes = public_path.read_bytes()
    public_payload = json.loads(public_bytes.decode("utf-8"))
    if not isinstance(public_payload, dict):
        raise ValueError(f"public benchmark root must be an object: {public_path}")
    public_errors = validate_payload(public_payload, str(public_path))
    if public_errors:
        raise ValueError("invalid public benchmark: " + "; ".join(public_errors))
    public_tasks = public_payload.get("tasks")
    if not isinstance(public_tasks, list):
        raise ValueError(f"public benchmark tasks must be an array: {public_path}")
    if any(isinstance(task, dict) and task.get("split") == "hidden" for task in public_tasks):
        raise ValueError("public benchmark contains hidden task content; move it to protected storage")
    development = select_tasks(public_tasks, split="development", source=str(public_path))
    public_sha = hashlib.sha256(public_bytes).hexdigest()
    if split == "development":
        return public_payload, development, public_sha

    assert protected_path is not None
    protected_bytes = protected_path.read_bytes()
    protected_payload = json.loads(protected_bytes.decode("utf-8"))
    if not isinstance(protected_payload, dict):
        raise ValueError(f"protected benchmark root must be an object: {protected_path}")
    for field in ("benchmark_id", "benchmark_version", "language", "environment"):
        if protected_payload.get(field) != public_payload.get(field):
            raise ValueError(f"protected benchmark {field} does not match the public benchmark")
    protected_errors = validate_payload(
        protected_payload, str(protected_path), allow_hidden=True
    )
    if protected_errors:
        raise ValueError("invalid protected benchmark: " + "; ".join(protected_errors))
    protected_tasks = protected_payload.get("tasks")
    if not isinstance(protected_tasks, list) or any(
        not isinstance(task, dict) or task.get("split") != "hidden" for task in protected_tasks
    ):
        raise ValueError("protected benchmark must contain only tasks with split='hidden'")
    hidden = select_tasks(protected_tasks, split="hidden", source=str(protected_path))
    public_ids = {task["id"] for task in development}
    protected_ids = {task["id"] for task in hidden}
    public_scenarios = {task["scenario_id"] for task in development}
    protected_scenarios = {task["scenario_id"] for task in hidden}
    if public_ids & protected_ids:
        raise ValueError("public and protected task IDs must not overlap")
    if public_scenarios & protected_scenarios:
        raise ValueError("public and protected scenario IDs must not overlap")
    if split == "hidden":
        tasks = hidden
        benchmark_sha = hashlib.sha256(protected_bytes).hexdigest()
    else:
        tasks = development + hidden
        benchmark_sha = hashlib.sha256(f"{public_sha}:{hashlib.sha256(protected_bytes).hexdigest()}".encode()).hexdigest()
    return public_payload, tasks, benchmark_sha


def environment_bundle_sha256() -> str:
    """Fingerprint the environment implementation and all locale packs."""
    root = Path(__file__).resolve().parents[1] / "environments" / "customer_service_agent"
    files = sorted(path for path in root.rglob("*") if path.is_file() and path.suffix in {".py", ".yaml"})
    digest = hashlib.sha256()
    for path in files:
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def evaluator_sha256() -> str:
    """Fingerprint evaluator and adapter source that can affect measured results."""
    root = Path(__file__).resolve().parent
    files = [
        Path(__file__).resolve(), root / "openai_agent.py",
        root.parent / "scripts" / "validate_benchmarks.py",
    ]
    digest = hashlib.sha256()
    for path in sorted(files):
        digest.update(path.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _usage_metrics(call_usages: list[dict[str, int] | None]) -> dict[str, Any]:
    reported = [usage for usage in call_usages if isinstance(usage, dict) and usage]
    token_usage = {
        key: sum(usage[key] for usage in reported if key in usage)
        for key in ("prompt_tokens", "completion_tokens", "total_tokens")
        if any(key in usage for usage in reported)
    }
    complete_calls = sum(
        "prompt_tokens" in usage and "completion_tokens" in usage
        for usage in reported
    )
    return {
        "agent_usage_calls": len(reported),
        "agent_usage_complete_calls": complete_calls,
        "agent_token_usage": token_usage or None,
    }


def run_task(agent: Any, task: dict, seed: int, step_budget: int, locale: str = "ar") -> dict:
    env = CustomerServiceEnv(episode_step_budget=step_budget, locale=locale)
    observation, _ = env.reset(seed=seed, options={"scenario_id": task["scenario_id"]})
    total_reward = 0.0
    terminated = truncated = False
    action_latencies_ms: list[float] = []
    action_errors = 0
    call_usages: list[dict[str, int] | None] = []
    try:
        while not terminated and not truncated:
            started_ns = time.perf_counter_ns()
            try:
                action = agent.act(observation)
            except Exception:
                action_errors += 1
                raise
            finally:
                action_latencies_ms.append((time.perf_counter_ns() - started_ns) / 1_000_000)
                usage_getter = getattr(agent, "get_last_call_usage", None)
                try:
                    call_usages.append(usage_getter() if callable(usage_getter) else None)
                except Exception:
                    call_usages.append(None)
            observation, reward, terminated, truncated, info = env.step(action)
            total_reward += reward
        event_log = info.get("event_log", [])
        actual_resolution = next(
            (event.get("arguments", {}).get("resolution") for event in reversed(event_log)
             if event.get("tool") == "send_response"),
            None,
        )
        expected_outcome = task.get("expected_outcome")
        result = {
            "task_id": task["id"], "scenario_id": task["scenario_id"],
            "locale": locale,
            "split": task.get("split", "development"),
            "category": task.get("category", "unspecified"),
            "expected_outcome": expected_outcome,
            "actual_resolution": actual_resolution,
            "outcome_match": (
                bool(info.get("is_success")) and actual_resolution == OUTCOME_RESOLUTIONS.get(expected_outcome)
                if expected_outcome in OUTCOME_RESOLUTIONS else None
            ),
            "success": bool(info.get("is_success")),
            "safety_violations": info.get("safety_violations", 0),
            "unsupported_claims": info.get("unsupported_claims", 0),
            "tool_calls": info.get("episode_steps", 0), "truncated": bool(truncated),
            "reward": round(total_reward, 6), "reward_components": info.get("reward_components", {}),
            "event_log": event_log,
            "transient_failure": any(event.get("transient_failure") for event in event_log),
            "recovered_from_transient_failure": any(
                event.get("recovered_from_transient_failure") for event in event_log
            ),
            "agent_action_calls": len(action_latencies_ms),
            "agent_action_errors": action_errors,
            "agent_action_latency_ms": action_latencies_ms,
            **_usage_metrics(call_usages),
        }
    except Exception as exc:  # keep one broken adapter/task from hiding all results
        expected_outcome = task.get("expected_outcome")
        result = {"task_id": task["id"], "scenario_id": task["scenario_id"],
                  "locale": locale,
                  "split": task.get("split", "development"), "success": False,
                  "expected_outcome": expected_outcome, "actual_resolution": None,
                  "outcome_match": False if expected_outcome in OUTCOME_RESOLUTIONS else None,
                  "transient_failure": False, "recovered_from_transient_failure": False,
                  "error": f"{type(exc).__name__}: {exc}",
                  "unsupported_claims": 0,
                  "agent_action_calls": len(action_latencies_ms),
                  "agent_action_errors": action_errors,
                  "agent_action_latency_ms": action_latencies_ms,
                  **_usage_metrics(call_usages)}
    finally:
        env.close()
    return result


def failure_reasons(result: dict[str, Any]) -> list[str]:
    """Return stable, non-exclusive failure labels for one task result."""
    reasons: list[str] = []
    if result.get("error"):
        reasons.append("agent_error")
    if result.get("safety_violations", 0) > 0:
        reasons.append("unsafe_action")
    if result.get("unsupported_claims", 0) > 0:
        reasons.append("unsupported_claim")
    if result.get("truncated"):
        reasons.append("step_budget_exhausted")
    if result.get("outcome_match") is False:
        reasons.append("outcome_mismatch")
    if not result.get("success") and not reasons:
        reasons.append("task_failure")
    return reasons


def _percentile(values: list[float], percentile: float) -> float:
    """Return a deterministic nearest-rank percentile without extra dependencies."""
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, math.ceil(percentile * len(ordered)) - 1)
    return round(ordered[index], 6)


def aggregate(results: list[dict], elapsed_seconds: float | None = None,
              input_price_per_million_tokens: float | None = None,
              output_price_per_million_tokens: float | None = None) -> dict:
    count = len(results)
    successful = sum(bool(row.get("success")) for row in results)
    safe = sum(bool(row.get("success")) and row.get("safety_violations", 0) == 0 for row in results)
    outcome_rows = [row for row in results if row.get("outcome_match") is not None]
    transient_rows = [row for row in results if row.get("transient_failure")]
    rewards = [float(row.get("reward", 0.0)) for row in results]
    reward_mean = sum(rewards) / len(rewards) if rewards else 0.0
    action_latencies = [
        float(latency)
        for row in results
        for latency in row.get("agent_action_latency_ms", [])
    ]
    action_errors = sum(int(row.get("agent_action_errors", 0)) for row in results)
    unsupported_claims = sum(int(row.get("unsupported_claims", 0)) for row in results)
    final_response_attempts = sum(
        event.get("tool") == "send_response"
        for row in results
        for event in row.get("event_log", [])
    )
    agent_action_calls = sum(
        int(row.get("agent_action_calls", len(row.get("agent_action_latency_ms", []))))
        for row in results
    )
    reported_usage_calls = sum(int(row.get("agent_usage_calls", 0)) for row in results)
    complete_usage_calls = sum(int(row.get("agent_usage_complete_calls", 0)) for row in results)
    usage_rows = [row.get("agent_token_usage") for row in results if isinstance(row.get("agent_token_usage"), dict)]
    token_usage = {
        key: sum(int(usage.get(key, 0)) for usage in usage_rows if key in usage)
        for key in ("prompt_tokens", "completion_tokens", "total_tokens")
        if any(key in usage for usage in usage_rows)
    }
    token_usage_complete = agent_action_calls > 0 and complete_usage_calls == agent_action_calls
    pricing_supplied = input_price_per_million_tokens is not None and output_price_per_million_tokens is not None
    cost_is_available = pricing_supplied and token_usage_complete and {
        "prompt_tokens", "completion_tokens"
    }.issubset(token_usage)
    estimated_cost = None
    if cost_is_available:
        estimated_cost = (
            token_usage["prompt_tokens"] * input_price_per_million_tokens
            + token_usage["completion_tokens"] * output_price_per_million_tokens
        ) / 1_000_000
    failure_counts: dict[str, int] = {}
    scenario_breakdown: dict[str, dict[str, Any]] = {}
    locale_breakdown: dict[str, dict[str, Any]] = {}
    for row in results:
        reasons = failure_reasons(row)
        for reason in reasons:
            failure_counts[reason] = failure_counts.get(reason, 0) + 1
        for key, bucket in (("scenario_id", scenario_breakdown), ("locale", locale_breakdown)):
            value = row.get(key, "unknown")
            entry = bucket.setdefault(value, {"tasks": 0, "successful_tasks": 0, "unsafe_tasks": 0, "failure_reasons": {}})
            entry["tasks"] += 1
            entry["successful_tasks"] += int(bool(row.get("success")))
            entry["unsafe_tasks"] += int(row.get("safety_violations", 0) > 0)
            for reason in reasons:
                entry["failure_reasons"][reason] = entry["failure_reasons"].get(reason, 0) + 1
    return {
        "tasks": count,
        "success_rate": round(successful / count, 6) if count else 0.0,
        "safe_completion_rate": round(safe / count, 6) if count else 0.0,
        "unsafe_action_rate": round(sum(row.get("safety_violations", 0) > 0 for row in results) / count, 6) if count else 0.0,
        "truncation_rate": round(sum(bool(row.get("truncated")) for row in results) / count, 6) if count else 0.0,
        "mean_tool_calls": round(sum(row.get("tool_calls", 0) for row in results) / count, 6) if count else 0.0,
        "mean_reward": round(reward_mean, 6),
        "reward_std": round(math.sqrt(sum((reward - reward_mean) ** 2 for reward in rewards) / len(rewards)), 6) if rewards else 0.0,
        "outcome_match_rate": round(sum(bool(row.get("outcome_match")) for row in outcome_rows) / len(outcome_rows), 6) if outcome_rows else None,
        "tool_error_recovery_rate": round(sum(bool(row.get("recovered_from_transient_failure")) for row in transient_rows) / len(transient_rows), 6) if transient_rows else None,
        "safety_violations": sum(row.get("safety_violations", 0) for row in results),
        "unsupported_claims": unsupported_claims,
        "final_response_attempts": final_response_attempts,
        "unsupported_claim_rate": round(unsupported_claims / final_response_attempts, 6) if final_response_attempts else 0.0,
        "successful_tasks": successful,
        "safe_tasks": safe,
        "agent_action_calls": len(action_latencies),
        "agent_action_errors": action_errors,
        "agent_action_error_rate": round(action_errors / len(action_latencies), 6) if action_latencies else 0.0,
        "mean_agent_action_latency_ms": round(sum(action_latencies) / len(action_latencies), 6) if action_latencies else 0.0,
        "p50_agent_action_latency_ms": _percentile(action_latencies, 0.50),
        "p95_agent_action_latency_ms": _percentile(action_latencies, 0.95),
        "p99_agent_action_latency_ms": _percentile(action_latencies, 0.99),
        "max_agent_action_latency_ms": round(max(action_latencies), 6) if action_latencies else 0.0,
        "benchmark_elapsed_seconds": round(elapsed_seconds, 6) if elapsed_seconds is not None else None,
        "tasks_per_second": round(count / elapsed_seconds, 6) if elapsed_seconds and elapsed_seconds > 0 else None,
        "agent_actions_per_second": round(len(action_latencies) / elapsed_seconds, 6) if elapsed_seconds and elapsed_seconds > 0 else None,
        "reported_token_usage_calls": reported_usage_calls,
        "complete_token_usage_calls": complete_usage_calls,
        "token_usage_complete": token_usage_complete,
        "agent_token_usage": token_usage or None,
        "estimated_cost": round(estimated_cost, 12) if estimated_cost is not None else None,
        "estimated_cost_per_successful_task": round(estimated_cost / successful, 12) if estimated_cost is not None and successful else None,
        "failure_reasons": dict(sorted(failure_counts.items())),
        "failure_breakdown": {
            "by_scenario": dict(sorted(scenario_breakdown.items())),
            "by_locale": dict(sorted(locale_breakdown.items())),
        },
    }


def run_tasks(agent: Any, tasks: list[dict], seed: int, step_budget: int,
              locale: str = "ar", concurrency: int = 1) -> list[dict]:
    """Run independent episodes with bounded parallelism, retaining input order."""
    if concurrency < 1:
        raise ValueError("concurrency must be at least 1")

    def execute(indexed_task: tuple[int, dict]) -> dict:
        index, task = indexed_task
        return run_task(agent, task, seed + index, step_budget, locale=locale)

    indexed_tasks = enumerate(tasks)
    if concurrency == 1:
        return [execute(item) for item in indexed_tasks]
    with ThreadPoolExecutor(max_workers=concurrency, thread_name_prefix="polyglot-benchmark") as executor:
        return list(executor.map(execute, indexed_tasks))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark", type=Path, default=Path("evaluation/benchmarks/ar_tasks_v0.2.json"),
                        help="Public benchmark file containing development tasks only")
    parser.add_argument("--protected-benchmark", type=Path,
                        help="External access-controlled benchmark file containing hidden tasks only")
    parser.add_argument("--split", choices=("development", "hidden", "all"), default="development",
                        help="Defaults to development; hidden/all require --protected-benchmark")
    parser.add_argument("--output", type=Path, default=Path("/tmp/polyglot-benchmark-report.json"))
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--step-budget", type=int, default=10)
    parser.add_argument("--agent", choices=("rule-based", "openai-compatible"), default="rule-based")
    parser.add_argument("--base-url", default="http://localhost:8080", help="OpenAI-compatible gateway URL")
    parser.add_argument("--model", default="polyglot-ar", help="Model name exposed by the gateway")
    parser.add_argument("--locale", default="ar", help="Locale pack to evaluate, e.g. ar, en, or fr")
    parser.add_argument("--api-key", default="", help="API key; prefer POLYGLOT_AGENT_API_KEY")
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--concurrency", type=int, default=1,
                        help="Maximum number of independent episodes running at once")
    parser.add_argument("--input-price-per-million-tokens", type=float,
                        help="Optional provider input-token price for a cost estimate")
    parser.add_argument("--output-price-per-million-tokens", type=float,
                        help="Optional provider output-token price for a cost estimate")
    parser.add_argument("--price-currency", default="USD",
                        help="Currency for the explicitly supplied token prices")
    args = parser.parse_args()
    if args.step_budget < 1:
        parser.error("--step-budget must be positive")
    if args.concurrency < 1:
        parser.error("--concurrency must be at least 1")
    prices = (args.input_price_per_million_tokens, args.output_price_per_million_tokens)
    if any(price is not None for price in prices) and any(price is None for price in prices):
        parser.error("provide both input and output token prices, or neither")
    if any(price is not None and (not math.isfinite(price) or price < 0) for price in prices):
        parser.error("token prices must be finite and non-negative")
    try:
        payload, tasks, benchmark_sha256 = load_benchmark_for_run(
            args.benchmark, split=args.split, protected_path=args.protected_benchmark
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        parser.error(str(exc))
    if not tasks:
        parser.error(f"benchmark split has no tasks: {args.split}")
    if args.agent == "openai-compatible":
        agent = OpenAICompatibleAgent(
            args.base_url,
            args.model,
            args.api_key or os.getenv("POLYGLOT_AGENT_API_KEY", ""),
            args.timeout,
            locale=args.locale,
        )
    else:
        agent = RuleBasedAgent(locale=args.locale)
    started_ns = time.perf_counter_ns()
    results = run_tasks(agent, tasks, args.seed, args.step_budget,
                        locale=args.locale, concurrency=args.concurrency)
    elapsed_seconds = (time.perf_counter_ns() - started_ns) / 1_000_000_000
    report = {
        "schema_version": 2,
        "benchmark_id": payload.get("benchmark_id"),
        "benchmark_version": payload.get("benchmark_version"),
        "benchmark_sha256": benchmark_sha256,
        "environment_sha256": environment_bundle_sha256(),
        "evaluator_sha256": evaluator_sha256(),
        "benchmark_review_status": payload.get("human_review_status", "unknown"),
        "language": payload.get("language"),
        "locale": args.locale,
        "environment": payload.get("environment"),
        "split": args.split,
        "agent": {"name": f"rule_based_{args.locale}_v1", "type": "deterministic_baseline"} if args.agent == "rule-based" else {
            "name": args.model, "type": "openai_compatible", "base_url": args.base_url,
        },
        "created_at": datetime.now(timezone.utc).isoformat(),
        "seed": args.seed,
        "step_budget": args.step_budget,
        "concurrency": args.concurrency,
        "token_pricing": {
            "input_per_million_tokens": args.input_price_per_million_tokens,
            "output_per_million_tokens": args.output_price_per_million_tokens,
            "currency": args.price_currency,
        } if args.input_price_per_million_tokens is not None else None,
        "aggregate": aggregate(
            results,
            elapsed_seconds=elapsed_seconds,
            input_price_per_million_tokens=args.input_price_per_million_tokens,
            output_price_per_million_tokens=args.output_price_per_million_tokens,
        ),
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "aggregate": report["aggregate"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
