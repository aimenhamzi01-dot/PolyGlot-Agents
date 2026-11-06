from __future__ import annotations

import gymnasium as gym
from . import make_action, register  # noqa: F401


def main() -> None:
    env=gym.make("PolyGlotCustomerServiceAr-v1",episode_step_budget=10)
    obs,info=env.reset(seed=0,options={"scenario_id":"cs_ar_002"})
    print("العميل:",obs["customer_message"])
    actions=[
        make_action("lookup_order",order_id="B203"),
        make_action("check_refund_policy"),
        make_action("request_approval"),
    ]
    total=0.0
    for action in actions:
        obs,reward,terminated,truncated,info=env.step(action); total+=reward
        print("الأداة:",info["tool"],"→",obs["last_tool_result"],"المكافأة:",info["reward_components"])
        if terminated or truncated: break
    if not terminated and not truncated:
        action=make_action("issue_refund",approval_id=obs["approval_id"])
        obs,reward,terminated,truncated,info=env.step(action); total+=reward
        print("الأداة:",info["tool"],"→",obs["last_tool_result"],"المكافأة:",info["reward_components"])
    if not terminated and not truncated:
        action=make_action("send_response",resolution="refund",message="تم تنفيذ استرداد المبلغ للطلب B203.")
        obs,reward,terminated,truncated,info=env.step(action); total+=reward
    print("الرد النهائي:",obs["last_reply"])
    print("نجاح متحقق:",info["is_success"],"إجمالي مكافأة الحلقة:",round(total,3))
    print("سجل أحداث الحلقة:",info["event_log"])
    env.close()

if __name__=="__main__": main()
