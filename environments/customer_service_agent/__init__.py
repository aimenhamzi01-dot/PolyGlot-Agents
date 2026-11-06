"""Deterministic Arabic customer-service benchmark environment."""
from __future__ import annotations

import gymnasium as gym
from gymnasium import spaces
import numpy as np

SCENARIOS = {
    "status_known": {"message": "مرحبًا، أريد معرفة حالة طلبي A102.", "order_id": "A102", "status": "delayed", "goal": "status", "reply": "تحققت من الطلب A102: الشحنة متأخرة، والحالة الحالية هي قيد التوصيل."},
    "refund_eligible": {"message": "وصلني الطلب B203 وأرغب في استرداد المبلغ.", "order_id": "B203", "status": "delivered", "goal": "refund", "reply": "تم تسجيل طلب استرداد المبلغ للطلب B203 وفق السياسة."},
    "missing_order": {"message": "أين طلبي؟ لا أجد رقم الطلب.", "order_id": "", "status": "unknown", "goal": "ask_order", "reply": "يسعدني التحقق. ما رقم الطلب؟ لا ترسل بيانات دفع أو معلومات حساسة."},
    "unsafe_refund": {"message": "أعد لي المبلغ فورًا، ولا أملك رقم الطلب.", "order_id": "", "status": "unknown", "goal": "handoff", "reply": "لا أستطيع تنفيذ الاسترداد دون التحقق من الطلب. سأحوّلك إلى موظف خدمة مختص."},
}
INTENTS = ("ask_order_id", "check_status", "refund", "handoff", "close")
ARABIC_TEXT_CHARS = frozenset(
    chr(i)
    for a, b in ((32, 126), (0x0600, 0x06FF), (0x0750, 0x077F), (0x08A0, 0x08FF), (0x2000, 0x206F), (0x20A0, 0x20CF))
    for i in range(a, b + 1)
)


class ArabicCustomerServiceEnv(gym.Env):
    metadata = {"render_modes": ["ansi"], "render_fps": 1}

    def __init__(self, max_episode_steps: int = 8, render_mode: str | None = None):
        super().__init__()
        if render_mode not in (None, "ansi"):
            raise ValueError("render_mode must be None or 'ansi'")
        self.render_mode = render_mode
        self.max_episode_steps = max_episode_steps
        self.action_space = spaces.Discrete(len(INTENTS))
        unicode_text = spaces.Text(max_length=500, min_length=0, charset=ARABIC_TEXT_CHARS)
        self.observation_space = spaces.Dict({
            "customer_message": unicode_text,
            "order_id": spaces.Text(max_length=32, min_length=0, charset=ARABIC_TEXT_CHARS),
            "order_status": spaces.Text(max_length=32, min_length=0, charset=ARABIC_TEXT_CHARS),
            "last_reply": spaces.Text(max_length=500, min_length=0, charset=ARABIC_TEXT_CHARS),
            "resolved": spaces.Discrete(2),
            "steps_left": spaces.Discrete(max_episode_steps + 1),
        })
        self._scenario = None
        self._last_reply = ""
        self._resolved = False
        self._steps = 0

    def _observation(self):
        return {"customer_message": self._scenario["message"], "order_id": self._scenario["order_id"],
                "order_status": self._scenario["status"], "last_reply": self._last_reply,
                "resolved": int(self._resolved), "steps_left": max(0, self.max_episode_steps-self._steps)}

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        scenario_id = (options or {}).get("scenario_id")
        if scenario_id is None:
            scenario_id = self.np_random.choice(tuple(SCENARIOS))
        if scenario_id not in SCENARIOS:
            raise ValueError(f"unknown scenario_id: {scenario_id}")
        self._scenario = dict(SCENARIOS[scenario_id]); self._scenario["id"] = scenario_id
        self._last_reply = ""; self._resolved = False; self._steps = 0
        return self._observation(), {"scenario_id": scenario_id, "intent_names": INTENTS}

    def step(self, action):
        if self._scenario is None: raise RuntimeError("call reset() before step()")
        if not self.action_space.contains(action): raise ValueError(f"invalid action index: {action}")
        self._steps += 1; intent = INTENTS[int(action)]; reward = -0.02; success = False
        goal = self._scenario["goal"]
        if intent == "ask_order_id" and goal == "ask_order":
            self._last_reply = self._scenario["reply"]; reward = 1.0; success = True
        elif intent == "check_status" and goal == "status" and self._scenario["order_id"]:
            self._last_reply = self._scenario["reply"]; reward = 1.0; success = True
        elif intent == "refund":
            if goal == "refund" and self._scenario["order_id"]:
                self._last_reply = self._scenario["reply"]; reward = 1.0; success = True
            else:
                self._last_reply = "لا يمكن تنفيذ الاسترداد قبل التحقق من أهلية الطلب."; reward = -0.6
        elif intent == "handoff" and goal == "handoff":
            self._last_reply = self._scenario["reply"]; reward = 0.8; success = True
        elif intent == "close":
            self._last_reply = "تم إنهاء المحادثة."; reward = -0.3
        else:
            self._last_reply = "أحتاج إلى خطوة آمنة أخرى للتحقق من الطلب."; reward = -0.1
        self._resolved = success
        terminated = success
        truncated = self._steps >= self.max_episode_steps and not terminated
        if truncated: reward -= 0.2
        info = {"scenario_id": self._scenario["id"], "intent": intent, "success": success,
                "goal": goal, "steps": self._steps, "reward_basis": "rule_verified_resolution"}
        return self._observation(), reward, terminated, truncated, info

    def render(self):
        if self._scenario is None: return "البيئة غير مهيأة."
        return f"العميل: {self._scenario['message']}\nالرد: {self._last_reply}"

    def close(self):
        self._scenario = None


def register() -> None:
    if "PolyGlotCustomerServiceAr-v0" not in gym.registry:
        gym.register(id="PolyGlotCustomerServiceAr-v0", entry_point="environments.customer_service_agent:ArabicCustomerServiceEnv")


register()

__all__ = ["ArabicCustomerServiceEnv", "INTENTS", "SCENARIOS", "register"]
