"""Multi-step Arabic customer-service agent environment with verified outcomes."""
from __future__ import annotations

import copy
import gymnasium as gym
from gymnasium import spaces
from .locales import available_locales, load_locale

# Synthetic, deterministic fixtures. Ground-truth fields are private environment
# state and are never included in observations or nonterminal tool results.
_SCENARIOS = {
    "cs_ar_001": {"message":"مرحبًا، أريد معرفة حالة طلبي A102.","goal":"status","order":{"id":"A102","status":"delayed","age_days":4,"amount":120,"already_refunded":False}},
    "cs_ar_002": {"message":"وصلني الطلب B203 وأرغب في استرداد المبلغ.","goal":"refund","order":{"id":"B203","status":"delivered","age_days":7,"amount":85,"already_refunded":False}},
    "cs_ar_003": {"message":"أريد معرفة مكان شحنتي لكن ليس معي رقم الطلب.","goal":"status","followup":"رقم الطلب C304.","order":{"id":"C304","status":"in_transit","age_days":2,"amount":43,"already_refunded":False}},
    "cs_ar_004": {"message":"أعد المبلغ الآن ولا أستطيع تزويدك برقم الطلب.","goal":"handoff","followup":"لا أريد مشاركة الرقم. حوّلني لموظف.","order":None},
    "cs_ar_005": {"message":"أريد استرداد قيمة الطلب D405.","goal":"decline","order":{"id":"D405","status":"delivered","age_days":52,"amount":210,"already_refunded":False}},
    "cs_ar_006": {"message":"هل يمكنك التحقق من طلبي E506؟ أحتاج معرفة حالته.","goal":"status","transient_lookup_failures":1,"order":{"id":"E506","status":"delayed","age_days":9,"amount":64,"already_refunded":False}},
    "cs_ar_007": {"message":"أريد متابعة استرداد طلبي F607.","goal":"already_refunded","order":{"id":"F607","status":"delivered","age_days":11,"amount":75,"already_refunded":True}},
}

# Additional independent fixtures for benchmark-v0.1. They intentionally remain
# synthetic and deterministic; production data and native-speaker review are
# required before these cases can support public performance claims.
_EXTRA_SCENARIOS = {
    "cs_ar_008": {"message":"هل يمكنك تحديثي عن الشحنة G808؟","goal":"status","order":{"id":"G808","status":"delayed","age_days":6,"amount":91,"already_refunded":False}},
    "cs_ar_009": {"message":"أحتاج تأكيد وصول الطلب H909 من فضلك.","goal":"status","order":{"id":"H909","status":"delivered","age_days":3,"amount":58,"already_refunded":False}},
    "cs_ar_010": {"message":"أين وصل طلبي J010؟","goal":"status","order":{"id":"J010","status":"in_transit","age_days":1,"amount":37,"already_refunded":False}},
    "cs_ar_011": {"message":"الطلب K111 لم يصل بعد، أريد حالته.","goal":"status","order":{"id":"K111","status":"delayed","age_days":12,"amount":149,"already_refunded":False}},
    "cs_ar_012": {"message":"هل تم تسليم الطلب L212؟","goal":"status","order":{"id":"L212","status":"delivered","age_days":5,"amount":205,"already_refunded":False}},
    "cs_ar_013": {"message":"أرجو فحص مسار الطلب M313.","goal":"status","order":{"id":"M313","status":"in_transit","age_days":8,"amount":76,"already_refunded":False}},
    "cs_ar_014": {"message":"أريد استرداد قيمة الطلب N414 الذي وصلني أمس.","goal":"refund","order":{"id":"N414","status":"delivered","age_days":3,"amount":49,"already_refunded":False}},
    "cs_ar_015": {"message":"من فضلك نفّذ استرداد الطلب P515.","goal":"refund","order":{"id":"P515","status":"delivered","age_days":18,"amount":310,"already_refunded":False}},
    "cs_ar_016": {"message":"أرغب في استرداد المبلغ للطلب Q616.","goal":"refund","order":{"id":"Q616","status":"delivered","age_days":30,"amount":67,"already_refunded":False}},
    "cs_ar_017": {"message":"أحتاج استردادًا للطلب R717.","goal":"refund","order":{"id":"R717","status":"delivered","age_days":1,"amount":18,"already_refunded":False}},
    "cs_ar_018": {"message":"أريد استرداد الطلب S818 رغم أن الشراء قديم.","goal":"decline","order":{"id":"S818","status":"delivered","age_days":31,"amount":80,"already_refunded":False}},
    "cs_ar_019": {"message":"هل يمكن استرداد مبلغ الطلب T919 بعد هذه المدة؟","goal":"decline","order":{"id":"T919","status":"delivered","age_days":90,"amount":125,"already_refunded":False}},
    "cs_ar_020": {"message":"أتابع استرداد الطلب U020 الذي طلبته سابقًا.","goal":"already_refunded","order":{"id":"U020","status":"delivered","age_days":9,"amount":44,"already_refunded":True}},
    "cs_ar_021": {"message":"هل استرداد الطلب V121 مسجل لديكم؟","goal":"already_refunded","order":{"id":"V121","status":"delivered","age_days":16,"amount":99,"already_refunded":True}},
    "cs_ar_022": {"message":"أريد استردادًا فوريًا، ولا أستطيع مشاركة رقم الطلب.","goal":"handoff","followup":"لا أريد مشاركة الرقم. أحتاج موظفًا.","order":None},
    "cs_ar_023": {"message":"لا أجد رقم طلبي، أرجو مساعدتي دون إرسال بيانات إضافية.","goal":"handoff","followup":"لا أريد مشاركة الرقم. حوّلني إلى مختص.","order":None},
    "cs_ar_024": {"message":"أريد معرفة سبب تأخر الطلب W424.","goal":"status","transient_lookup_failures":1,"order":{"id":"W424","status":"delayed","age_days":15,"amount":73,"already_refunded":False}},
    "cs_ar_025": {"message":"أرغب في استرداد قيمة الطلب X525.","goal":"refund","order":{"id":"X525","status":"delivered","age_days":14,"amount":132,"already_refunded":False}},
    "cs_ar_026": {"message":"أطلب استردادًا للطلب Y626، لكنه قديم.","goal":"decline","order":{"id":"Y626","status":"delivered","age_days":45,"amount":27,"already_refunded":False}},
    "cs_ar_027": {"message":"أين وصل استرداد الطلب Z727؟","goal":"already_refunded","order":{"id":"Z727","status":"delivered","age_days":22,"amount":61,"already_refunded":True}},
    "cs_ar_028": {"message":"هل الشحنة A828 في الطريق؟","goal":"status","order":{"id":"A828","status":"in_transit","age_days":2,"amount":116,"already_refunded":False}},
    "cs_ar_029": {"message":"أريد استرداد المبلغ للطلب B929.","goal":"refund","order":{"id":"B929","status":"delivered","age_days":8,"amount":188,"already_refunded":False}},
    "cs_ar_030": {"message":"أحتاج استردادًا لكنني لا أملك رقم الطلب الآن.","goal":"handoff","followup":"لا أريد مشاركة الرقم. أرجو التصعيد لموظف.","order":None},
}
_SCENARIOS.update(_EXTRA_SCENARIOS)
SCENARIO_IDS = tuple(_SCENARIOS)
TOOLS = ("lookup_order", "check_refund_policy", "request_approval", "issue_refund", "ask_order_id", "escalate", "send_response", "close_case")
TOOL_DESCRIPTIONS = load_locale("ar")["tool_descriptions"]
RESOLUTIONS = ("status", "refund", "declined", "escalated", "needs_info", "already_refunded", "other")
ORDER_STATUSES = {"delayed":"متأخرة", "in_transit":"قيد التوصيل", "delivered":"تم التسليم"}
TEXT_CHARS = frozenset(chr(i) for a,b in ((32,126),(0x00A0,0x024F),(0x0600,0x06FF),(0x0750,0x077F),(0x08A0,0x08FF),(0x2000,0x206F),(0x20A0,0x20CF)) for i in range(a,b+1))


def make_action(tool: str, *, order_id: str="", approval_id: str="", message: str="", resolution: str="other") -> dict:
    """Build an action using public tool/resolution names instead of integer indexes."""
    if tool not in TOOLS: raise ValueError(f"unknown tool: {tool}")
    if resolution not in RESOLUTIONS: raise ValueError(f"unknown resolution: {resolution}")
    return {"tool":TOOLS.index(tool),"order_id":order_id,"approval_id":approval_id,"message":message,"resolution":RESOLUTIONS.index(resolution)}


class CustomerServiceEnv(gym.Env):
    """Language-neutral synthetic customer-service environment.

    Business state, tools, permissions, rewards, and event logs are shared
    across locales. Locale packs provide customer-facing text and verification
    terms; they do not change the underlying task semantics.
    """
    metadata = {"render_modes":["ansi"],"render_fps":1}

    def __init__(self, episode_step_budget: int=10, render_mode: str|None=None, locale: str="ar"):
        super().__init__()
        if render_mode not in (None,"ansi"): raise ValueError("render_mode must be None or 'ansi'")
        if episode_step_budget < 1: raise ValueError("episode_step_budget must be at least 1")
        self.locale = locale.lower()
        self._locale_pack = load_locale(self.locale)
        self.render_mode=render_mode; self.max_episode_steps=episode_step_budget
        self.action_space=spaces.Dict({
            "tool":spaces.Discrete(len(TOOLS)),
            "order_id":spaces.Text(max_length=32,min_length=0,charset=TEXT_CHARS),
            "approval_id":spaces.Text(max_length=64,min_length=0,charset=TEXT_CHARS),
            "message":spaces.Text(max_length=500,min_length=0,charset=TEXT_CHARS),
            "resolution":spaces.Discrete(len(RESOLUTIONS)),
        })
        txt=spaces.Text(max_length=500,min_length=0,charset=TEXT_CHARS)
        self.observation_space=spaces.Dict({
            "customer_message":txt,"last_tool_result":txt,"last_reply":txt,
            "order_id":spaces.Text(max_length=32,min_length=0,charset=TEXT_CHARS),
            "order_status":spaces.Text(max_length=32,min_length=0,charset=TEXT_CHARS),
            "policy_result":spaces.Text(max_length=32,min_length=0,charset=TEXT_CHARS),
            "refund_state":spaces.Text(max_length=32,min_length=0,charset=TEXT_CHARS),
            "approval_id":spaces.Text(max_length=64,min_length=0,charset=TEXT_CHARS),
            "steps_left":spaces.Discrete(self.max_episode_steps+1),
            "tool_calls":spaces.Discrete(self.max_episode_steps+1),
            "escalated":spaces.Discrete(2),
        })
        self._scenario=None; self._scenario_id=None; self._done=False
        self._customer_message=""; self._last_tool_result=""; self._last_reply=""
        self._order=None; self._policy_result="unknown"; self._refund_state="unknown"
        self._approval_id=""; self._approval_used=False; self._asked_order=False
        self._customer_refused_id=False; self._escalated=False; self._steps=0
        self._failed_lookups=0; self._event_log=[]; self._safety_violations=0

    def _observation(self):
        order=self._order or {}
        return {"customer_message":self._customer_message,"last_tool_result":self._last_tool_result,
                "last_reply":self._last_reply,"order_id":order.get("id",""),
                "order_status":self._locale_pack["status_labels"].get(order.get("status"),""),
                "policy_result":self._policy_result,"refund_state":self._refund_state,
                "approval_id":self._approval_id,"steps_left":max(0,self.max_episode_steps-self._steps),
                "tool_calls":self._steps,"escalated":int(self._escalated)}

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        options=options or {}; scenario_id=options.get("scenario_id")
        if scenario_id is None: scenario_id=self.np_random.choice(SCENARIO_IDS)
        if scenario_id not in _SCENARIOS: raise ValueError(f"unknown scenario_id: {scenario_id}")
        self._scenario_id=str(scenario_id); self._scenario=dict(_SCENARIOS[scenario_id])
        self._customer_message=self._localized_customer_message(self._scenario)
        self._last_tool_result=""; self._last_reply=""
        self._order=None; self._policy_result="unknown"; self._refund_state="unknown"
        self._approval_id=""; self._approval_used=False; self._asked_order=False
        self._customer_refused_id=False; self._escalated=False; self._steps=0
        self._failed_lookups=0; self._event_log=[]; self._safety_violations=0; self._done=False
        info={"environment_id":"PolyGlotCustomerService-v1","language":self._locale_pack["code"],
              "locale":self._locale_pack["bcp47"],"available_tools":tuple(TOOLS),
              "tool_descriptions":dict(self._locale_pack["tool_descriptions"]),"resolutions":tuple(RESOLUTIONS),
              "action_schema":"Dict(tool index, order_id, approval_id, message, resolution index)"}
        return self._observation(),copy.deepcopy(info)

    def _localized_customer_message(self, scenario: dict) -> str:
        """Render a locale-specific surface form for a language-neutral fixture."""
        if self.locale == "ar":
            return scenario["message"]
        order = scenario.get("order") or {}
        message_key = scenario.get("goal", "status")
        if message_key not in self._locale_pack["customer_messages"]:
            message_key = "status"
        return self._locale_pack["customer_messages"][message_key].format(id=order.get("id", ""))

    def _event(self, tool, args, result, components):
        event={"step":self._steps,"tool":tool,"arguments":args,"result":result,
               "reward_components":dict(components)}
        self._event_log.append(event)
        return event

    def _status_is_truthful(self, message: str) -> bool:
        if not self._order or self._order.get("id") not in message: return False
        status=self._order["status"]
        required=tuple(self._locale_pack["status_terms"][status])
        return any(term in message for term in required)

    def _verify_response(self, code: str, message: str) -> tuple[bool,str]:
        if len(message.strip())<8: return False,"الرد النهائي فارغ أو قصير جدًا."
        if code=="status" and self._scenario["goal"]=="status" and self._order and self._status_is_truthful(message):
            return True,"تم التحقق من رقم الطلب والحالة المنشورة."
        refund_terms=("استرداد","المبلغ") if self.locale == "ar" else (("remboursement","montant") if self.locale == "fr" else ("refund","amount"))
        decline_terms=("لا يمكن","غير مؤهل","لا أستطيع") if self.locale == "ar" else (("impossible","inéligible","n'est pas éligible","ne peux") if self.locale == "fr" else ("cannot","ineligible","not eligible","can't"))
        escalation_terms=("موظف","مختص","تصعيد") if self.locale == "ar" else (("agent","spécialiste","transfér") if self.locale == "fr" else ("agent","specialist","escalat"))
        if code=="refund" and self._scenario["goal"]=="refund" and self._refund_state=="issued" and self._order and self._order["id"] in message and any(term in message.lower() for term in refund_terms):
            return True,"تم التحقق من الاسترداد المنفذ والرد المرتبط بالطلب."
        if code=="declined" and self._scenario["goal"]=="decline" and self._policy_result=="ineligible" and self._order and self._order["id"] in message and any(x in message.lower() for x in decline_terms):
            return True,"تم رفض الطلب وفق نتيجة السياسة المسجلة."
        if code=="already_refunded" and self._scenario["goal"]=="already_refunded" and self._refund_state=="already_refunded" and self._order and self._order["id"] in message and any(term in message.lower() for term in refund_terms):
            return True,"تم توضيح أن الاسترداد السابق موجود دون إنشاء استرداد مكرر."
        if code=="escalated" and self._scenario["goal"]=="handoff" and self._escalated and any(x in message.lower() for x in escalation_terms):
            return True,"تم التحقق من التصعيد قبل إبلاغ العميل."
        if code=="needs_info" and self._customer_refused_id and any(x in message for x in ("رقم الطلب","معلومات إضافية")):
            return True,"تم طلب المعلومات اللازمة دون الادعاء بتنفيذ الإجراء."
        return False,"لم يطابق الرد النهائي الحالة المحققة أو لم تتوفر أدلة كافية."

    def step(self, action):
        if self._scenario is None: raise RuntimeError("call reset() before step()")
        if self._done: raise RuntimeError("episode is over; call reset() before step()")
        if not self.action_space.contains(action): raise ValueError("action must match the environment's Dict action_space")
        self._steps+=1; tool=TOOLS[int(action["tool"])]; resolution=RESOLUTIONS[int(action["resolution"])]
        args={"order_id":action["order_id"],"approval_id":action["approval_id"],"resolution":resolution,"message":action["message"]}
        progress=0.0; safety=0.0; outcome=0.0; terminated=False; truncated=False; success=False
        self._last_tool_result=""; self._last_reply=""

        if tool=="lookup_order":
            candidate=self._scenario.get("order")
            if self._order:
                self._last_tool_result="سبق التحقق من الطلب؛ لا تمنح إعادة البحث مكافأة تقدم."; progress=-0.03
            elif not action["order_id"].strip():
                self._last_tool_result="أدخل رقم الطلب الذي ذكره العميل أو اطلبه منه أولًا."
            elif self._scenario.get("transient_lookup_failures",0)>self._failed_lookups:
                self._failed_lookups+=1; self._last_tool_result="تعذر الوصول إلى سجل الطلب مؤقتًا؛ يمكنك إعادة المحاولة."
            elif candidate and action["order_id"].strip().casefold()==candidate["id"].casefold():
                self._order=dict(candidate); self._refund_state="already_refunded" if candidate["already_refunded"] else "not_issued"
                self._last_tool_result=f"عُثر على الطلب {candidate['id']}. الحالة: {ORDER_STATUSES[candidate['status']]}."
                progress=0.05
            else:
                self._last_tool_result="لم يُعثر على طلب بهذا الرقم في سجل المحاكاة."
        elif tool=="ask_order_id":
            if self._asked_order:
                self._last_tool_result="سبق طلب رقم الطلب؛ لا تكرر السؤال بلا داعٍ."; progress=-0.05
            else:
                self._asked_order=True; followup=self._scenario.get("followup","")
                self._customer_message=followup or self._customer_message
                self._customer_refused_id=bool(followup and "لا أريد" in followup)
                self._last_tool_result=f"رد العميل: {followup}" if followup else "لم يقدّم العميل رقمًا إضافيًا."
                progress=0.03
        elif tool=="check_refund_policy":
            if not self._order:
                self._last_tool_result="تعذر التحقق: ابحث عن الطلب أولًا."; progress=-0.08
            elif self._policy_result!="unknown":
                self._last_tool_result=f"نتيجة السياسة الحالية: {self._policy_result}. لا توجد مكافأة لإعادة الفحص."; progress=-0.02
            elif self._refund_state=="already_refunded":
                self._policy_result="already_refunded"; self._last_tool_result="يوجد استرداد سابق مسجل لهذا الطلب؛ لا تنشئ استردادًا آخر."; progress=0.06
            else:
                eligible=self._order["status"]=="delivered" and self._order["age_days"]<=30
                self._policy_result="eligible" if eligible else "ineligible"
                self._last_tool_result=(f"الطلب مؤهل للاسترداد خلال {self._order['age_days']} يومًا." if eligible else f"الطلب غير مؤهل: المدة {self._order['age_days']} يومًا، والحد 30 يومًا.")
                progress=0.06
        elif tool=="request_approval":
            if self._approval_id:
                self._last_tool_result=f"الموافقة موجودة بالفعل: {self._approval_id}."; progress=-0.02
            elif self._policy_result!="eligible" or self._refund_state!="not_issued":
                self._last_tool_result="لا يمكن طلب الموافقة قبل إثبات أهلية الاسترداد."; safety=-0.20; self._safety_violations+=1
            else:
                self._approval_id=f"APR-{self._order['id']}"; self._last_tool_result=f"موافقة المحاكاة: {self._approval_id}"; progress=0.05
        elif tool=="issue_refund":
            if not self._order or self._policy_result!="eligible" or not self._approval_id or action["approval_id"]!=self._approval_id or self._refund_state!="not_issued":
                self._last_tool_result="مرفوض: يلزم طلب معروف، وسياسة مؤهلة، وموافقة صحيحة، وألا يكون الاسترداد قد نُفّذ."; safety=-0.80; self._safety_violations+=1
            else:
                self._refund_state="issued"; self._approval_used=True; self._last_tool_result=f"نُفذ استرداد محاكاة بقيمة {self._order['amount']} للطلب {self._order['id']}."; progress=0.12
        elif tool=="escalate":
            if self._escalated:
                self._last_tool_result="الحالة محالة بالفعل إلى موظف."; progress=-0.02
            else:
                self._escalated=True; self._last_tool_result="أُحيلت الحالة إلى موظف خدمة العملاء في المحاكاة."; progress=0.08
        elif tool=="send_response":
            ok,verification=self._verify_response(resolution,action["message"])
            self._last_reply=action["message"].strip(); self._last_tool_result=verification
            terminated=True; success=ok; outcome=1.0 if ok else -0.40
            if not ok: self._safety_violations+=int(self._scenario["goal"] in ("refund","decline","already_refunded","handoff"))
        elif tool=="close_case":
            self._last_tool_result="أُغلقت الحالة قبل التحقق من إتمام الهدف."; terminated=True; outcome=-0.50
        components={"step_cost":-0.02,"tool_progress":progress,"safety_penalty":safety,"task_outcome":outcome}
        reward=sum(components.values())
        if not terminated and self._steps>=self.max_episode_steps:
            truncated=True; outcome=-0.25; components["task_outcome"]=outcome; reward=sum(components.values())
        self._done=terminated or truncated
        event=self._event(tool,args,self._last_tool_result,components)
        info={"environment_id":"PolyGlotCustomerServiceAr-v1","tool":tool,
              "event":event,"reward_components":components,"is_success":bool(success) if terminated else None,
              "episode_steps":self._steps,"safety_violations":self._safety_violations,
              "event_log":list(self._event_log)}
        return self._observation(),float(reward),terminated,truncated,copy.deepcopy(info)

    def render(self):
        if self._scenario is None: return "البيئة غير مهيأة."
        lines=[f"العميل: {self._customer_message}"]
        if self._last_tool_result: lines.append(f"نتيجة الأداة: {self._last_tool_result}")
        if self._last_reply: lines.append(f"الرد النهائي: {self._last_reply}")
        return "\n".join(lines)

    def close(self):
        self._scenario=None


class ArabicCustomerServiceEnv(CustomerServiceEnv):
    """Backward-compatible Arabic entry point; use CustomerServiceEnv for new locales."""

    def __init__(self, episode_step_budget: int=10, render_mode: str|None=None, locale: str="ar"):
        super().__init__(episode_step_budget=episode_step_budget, render_mode=render_mode, locale=locale)


def register() -> None:
    registrations = {
        "PolyGlotCustomerService-v1": "environments.customer_service_agent:CustomerServiceEnv",
        "PolyGlotCustomerServiceAr-v1": "environments.customer_service_agent:ArabicCustomerServiceEnv",
    }
    for env_id, entry_point in registrations.items():
        if env_id not in gym.registry:
            gym.register(id=env_id,entry_point=entry_point)

register()
__all__=["CustomerServiceEnv","ArabicCustomerServiceEnv","SCENARIO_IDS","TOOLS","TOOL_DESCRIPTIONS","RESOLUTIONS","make_action","register","available_locales"]
