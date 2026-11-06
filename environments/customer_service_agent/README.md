# Arabic Customer-Service Agent Environment (Gymnasium v1)

A deterministic, offline simulator for **multi-step** Arabic agent tasks. All cases and orders are fabricated fixtures; there are no real customers, payments, network calls, or irreversible effects. The environment is a research/testbed implementation, not a production customer-service system. Version `v1` changes the old v0 integer-intent API to a structured `Dict` action; update callers to `make_action()` and the new environment ID.

## Episode contract

The agent receives a customer message and a public tool catalog. Its Gymnasium action is a `Dict`:

- `tool`: index into the returned `available_tools` tuple.
- `order_id`: string argument used by `lookup_order`.
- `approval_id`: simulated approval token used by `issue_refund`.
- `message`: natural-language text for `send_response`.
- `resolution`: index into returned `resolutions`; a semantic claim checked against internal state.

All action keys are present on every step; use `make_action()` to avoid hand-maintaining integer indexes.

```python
import gymnasium as gym
import environments.customer_service_agent as cs

env = gym.make("PolyGlotCustomerServiceAr-v1", episode_step_budget=10)
obs, info = env.reset(seed=7, options={"scenario_id": "cs_ar_002"})
obs, reward, terminated, truncated, info = env.step(
    cs.make_action("lookup_order", order_id="B203")
)
```

The environment exposes only the customer's current message and data revealed by tool calls. It does not put the expected goal, hidden order fixture, eligibility, scenario ID, or scenario internals in observations or `info`. The `scenario_id` reset option is for the evaluator to choose a reproducible case; never pass that option or its value to the agent.

## Tool workflow

1. `lookup_order` returns an order only if its exact identifier is supplied. Some scenarios include a one-time transient outage.
2. `check_refund_policy` requires a found order. Eligibility in the synthetic policy requires a delivered order no more than 30 days old. Existing refunds are identified.
3. `request_approval` issues a deterministic simulated supervisor token only after an eligible policy result.
4. `issue_refund` mutates only the episode's in-memory simulation and requires the order, positive policy result, matching approval token, and no prior refund.
5. `ask_order_id` invokes a scripted customer follow-up. The refusal case can be escalated instead of bypassing verification.
6. `escalate` records a simulated handoff.
7. `send_response` records a final response and semantic resolution code; the independent rule verifier checks it against environment state.
8. `close_case` terminates unsuccessfully if the objective has not been met.

## Scenarios and outcome verification

The seven fixtures cover truthful status reporting, an eligible refund, eliciting a missing order ID, refusal/escalation, an ineligible refund, transient tool failure/retry, and duplicate-refund prevention. The evaluator verifies order identifiers and Arabic status evidence in final messages, checks the actual refund state and policy result, and verifies that escalation happened before it is claimed. A correct-looking phrase alone is not enough.

The reward is returned with components in `info["reward_components"]`: a per-call cost, bounded one-time tool-progress rewards, safety penalties for policy violations, and a terminal outcome reward/penalty. Repeating lookups, policy checks, approval requests, or escalation cannot farm progress rewards. `info["event_log"]` contains the episode's tool arguments, results, and reward breakdown. `info["safety_violations"]` and `info["is_success"]` are trainer-side metrics; do not expose `info` as part of the agent observation during training or evaluation.

## Reproducible use

```bash
python -m environments.customer_service_agent.demo
python -m unittest tests.test_environment -v
```

Set the same seed and `scenario_id` to reproduce an episode. Keep separate training and held-out evaluation scenario files in future releases; do not train on final evaluation cases. Add new cases only with a documented objective, hidden verifier, policy, expected safety constraints, Arabic reviewer status, and tests for reward-hacking attempts. This fixture is not yet a native-speaker-validated public benchmark; its task card must remain marked accordingly until reviewed.
