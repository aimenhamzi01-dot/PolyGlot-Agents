# Arabic Customer Service Gymnasium Environment

A deterministic, offline testbed for Arabic service-agent behavior. It has scripted order scenarios, explicit action choices, observable state, and rule-based reward verification. It uses no customer data and makes no network calls.

```python
import gymnasium as gym
import environments.customer_service_agent  # registers the environment

env = gym.make("PolyGlotCustomerServiceAr-v0")
obs, info = env.reset(seed=7)
print(obs["customer_message"])
obs, reward, terminated, truncated, info = env.step(1)  # check_status; see INTENTS order in __init__.py
```

Supported intents: `ask_order_id`, `check_status`, `refund`, `handoff`, and `close`. The environment rewards a correct, policy-compliant resolution; it penalizes unsupported refunds and premature closure. See `demo.py` for a complete episode.
