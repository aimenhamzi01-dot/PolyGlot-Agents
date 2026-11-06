#!/usr/bin/env python3
"""Run verifiable agent episodes and write an auditable benchmark report."""
from __future__ import annotations

import argparse
import json
import os
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from environments.customer_service_agent import ArabicCustomerServiceEnv, make_action
except ModuleNotFoundError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from environments.customer_service_agent import ArabicCustomerServiceEnv, make_action
from evaluation.openai_agent import OpenAICompatibleAgent

ORDER_ID = re.compile(r"\b[A-Z]\d{3}\b")
STATUS_TEXT = {"متأخرة": "الطلب {id} متأخر، والشحنة متأخرة.", "قيد التوصيل": "الطلب {id} قيد التوصيل.", "تم التسليم": "تم تسليم الطلب {id}."}


class RuleBasedArabicAgent:
    """Deterministic baseline; intentionally simple and inspectable, not an LLM."""

    def act(self, observation: dict[str, Any]) -> dict:
        customer = observation.get("customer_message", "")
        order_id = observation.get("order_id", "")
        mentioned = ORDER_ID.search(customer)
        if observation.get("escalated"):
            return make_action("send_response", resolution="escalated", message="سأحوّل طلبك إلى موظف مختص للمساعدة.")
        if "لا أريد مشاركة" in customer and not order_id:
            return make_action("escalate")
        if not order_id:
            if mentioned:
                return make_action("lookup_order", order_id=mentioned.group(0))
            return make_action("ask_order_id")
        if observation.get("order_status"):
            if observation.get("refund_state") == "already_refunded":
                return make_action("send_response", resolution="already_refunded", message=f"يوجد استرداد سابق للمبلغ على الطلب {order_id}.")
            if "أرغب في استرداد" in customer or "استرداد" in customer:
                if observation.get("policy_result") == "unknown":
                    return make_action("check_refund_policy")
                if observation.get("policy_result") == "eligible":
                    if not observation.get("approval_id"):
                        return make_action("request_approval")
                    if observation.get("refund_state") != "issued":
                        return make_action("issue_refund", approval_id=observation["approval_id"])
                    return make_action("send_response", resolution="refund", message=f"تم تنفيذ استرداد المبلغ للطلب {order_id}.", approval_id=observation["approval_id"])
                if observation.get("policy_result") == "ineligible":
                    return make_action("send_response", resolution="declined", message=f"الطلب {order_id} غير مؤهل للاسترداد حسب المدة المحددة.")
            status = observation["order_status"]
            return make_action("send_response", resolution="status", message=STATUS_TEXT.get(status, f"تحققت من الطلب {order_id}.").format(id=order_id))
        mentioned = ORDER_ID.search(customer)
        if mentioned:
            return make_action("lookup_order", order_id=mentioned.group(0))
        return make_action("ask_order_id")


def load_tasks(path: Path, split: str | None = None) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload.get("tasks"), list) or not payload["tasks"]:
        raise ValueError(f"benchmark contains no tasks: {path}")
    tasks = payload["tasks"]
    ids = [task.get("id") for task in tasks]
    if any(not task.get("id") or not task.get("scenario_id") for task in tasks):
        raise ValueError(f"every task must have id and scenario_id: {path}")
    if len(ids) != len(set(ids)):
        raise ValueError(f"task ids must be unique: {path}")
    if split is None:
        return tasks
    if split not in {"development", "hidden", "all"}:
        raise ValueError("split must be development, hidden, or all")
    return tasks if split == "all" else [task for task in tasks if task.get("split", "development") == split]


def run_task(agent: Any, task: dict, seed: int, step_budget: int) -> dict:
    env = ArabicCustomerServiceEnv(episode_step_budget=step_budget)
    observation, _ = env.reset(seed=seed, options={"scenario_id": task["scenario_id"]})
    total_reward = 0.0
    terminated = truncated = False
    error = None
    try:
        while not terminated and not truncated:
            action = agent.act(observation)
            observation, reward, terminated, truncated, info = env.step(action)
            total_reward += reward
        result = {
            "task_id": task["id"], "scenario_id": task["scenario_id"],
            "split": task.get("split", "development"),
            "category": task.get("category", "unspecified"),
            "success": bool(info.get("is_success")),
            "safety_violations": info.get("safety_violations", 0),
            "tool_calls": info.get("episode_steps", 0), "truncated": bool(truncated),
            "reward": round(total_reward, 6), "reward_components": info.get("reward_components", {}),
            "event_log": info.get("event_log", []),
        }
    except Exception as exc:  # keep one broken adapter/task from hiding all results
        error = f"{type(exc).__name__}: {exc}"
        result = {"task_id": task["id"], "scenario_id": task["scenario_id"],
                  "split": task.get("split", "development"), "success": False, "error": error}
    finally:
        env.close()
    return result


def aggregate(results: list[dict]) -> dict:
    count = len(results)
    successful = sum(bool(row.get("success")) for row in results)
    safe = sum(bool(row.get("success")) and row.get("safety_violations", 0) == 0 for row in results)
    return {
        "tasks": count,
        "success_rate": round(successful / count, 6) if count else 0.0,
        "safe_completion_rate": round(safe / count, 6) if count else 0.0,
        "unsafe_action_rate": round(sum(row.get("safety_violations", 0) > 0 for row in results) / count, 6) if count else 0.0,
        "truncation_rate": round(sum(bool(row.get("truncated")) for row in results) / count, 6) if count else 0.0,
        "mean_tool_calls": round(sum(row.get("tool_calls", 0) for row in results) / count, 6) if count else 0.0,
        "mean_reward": round(sum(row.get("reward", 0.0) for row in results) / count, 6) if count else 0.0,
        "safety_violations": sum(row.get("safety_violations", 0) for row in results),
        "successful_tasks": successful,
        "safe_tasks": safe,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark", type=Path, default=Path("evaluation/benchmarks/ar_tasks.json"))
    parser.add_argument("--split", choices=("development", "hidden", "all"), default=None,
                        help="Run only one declared split; defaults to all tasks for legacy benchmarks")
    parser.add_argument("--output", type=Path, default=Path("/tmp/polyglot-benchmark-report.json"))
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--step-budget", type=int, default=10)
    parser.add_argument("--agent", choices=("rule-based", "openai-compatible"), default="rule-based")
    parser.add_argument("--base-url", default="http://localhost:8080", help="OpenAI-compatible gateway URL")
    parser.add_argument("--model", default="polyglot-ar", help="Model name exposed by the gateway")
    parser.add_argument("--api-key", default="", help="API key; prefer POLYGLOT_AGENT_API_KEY")
    parser.add_argument("--timeout", type=float, default=60.0)
    args = parser.parse_args()
    if args.step_budget < 1:
        parser.error("--step-budget must be positive")
    payload = json.loads(args.benchmark.read_text(encoding="utf-8"))
    tasks = load_tasks(args.benchmark, split=args.split)
    if not tasks:
        parser.error(f"benchmark split has no tasks: {args.split}")
    if args.agent == "openai-compatible":
        agent = OpenAICompatibleAgent(args.base_url, args.model, args.api_key or os.getenv("POLYGLOT_AGENT_API_KEY", ""), args.timeout)
    else:
        agent = RuleBasedArabicAgent()
    results = [run_task(agent, task, args.seed + index, args.step_budget) for index, task in enumerate(tasks)]
    report = {
        "schema_version": 1,
        "benchmark_id": payload.get("benchmark_id"),
        "benchmark_version": payload.get("benchmark_version"),
        "language": payload.get("language"),
        "environment": payload.get("environment"),
        "split": args.split or "all",
        "agent": {"name": "rule_based_ar_v1", "type": "deterministic_baseline"} if args.agent == "rule-based" else {
            "name": args.model, "type": "openai_compatible", "base_url": args.base_url,
        },
        "created_at": datetime.now(timezone.utc).isoformat(),
        "seed": args.seed,
        "step_budget": args.step_budget,
        "aggregate": aggregate(results),
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "aggregate": report["aggregate"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
