from __future__ import annotations

from . import register  # noqa: F401
import gymnasium as gym


def main() -> None:
    env = gym.make("PolyGlotCustomerServiceAr-v0")
    observation, info = env.reset(seed=0, options={"scenario_id": "status_known"})
    print("العميل:", observation["customer_message"])
    # INTENTS order is ask_order_id, check_status, refund, handoff, close.
    observation, reward, terminated, truncated, info = env.step(1)
    print("الوكيل:", observation["last_reply"])
    print("المكافأة:", reward, "تمت المهمة:", terminated, "التقييم:", info)
    env.close()


if __name__ == "__main__":
    main()
