# واجهة أدوات الوكلاء

تضيف بوابة PolyGlot Agents مساراً لاكتشاف تعريفات الأدوات بصيغة OpenAI function calling، وتقبل البوابة تمرير `tools` و`tool_choice` و`parallel_tool_calls` إلى خادم vLLM المتوافق. الغرض هو تسهيل ربط الوكيل بمُنفّذ أدوات يملكه التطبيق.

> **حد أمني مهم:** البوابة تعرض المخططات وتمرّر اقتراحات النموذج فقط. لا تنفّذ `lookup_order` أو `issue_refund` أو أي أداة أخرى، ولا تمنح النموذج صلاحية الوصول إلى بيانات أو أدوات. يجب على تطبيق العميل التحقق من اسم الأداة ومعاملاتها، ثم إرسالها إلى منفّذ منفصل ومصادق عليه يطبق سياسة الصلاحيات ويسجل التدقيق.

## المصادقة

تتطلب المسارات `/v1/tools` و`/v1/chat/completions` مفتاح `GATEWAY_API_KEY` في ترويسة Bearer:

```http
Authorization: Bearer <GATEWAY_API_KEY>
```

تعرض وثائق OpenAPI التفاعلية في `/docs` ومخططها في `/openapi.json`.

## تشغيل البوابة محلياً

ثبّت اعتماديات HTTP الاختيارية، ثم شغّل البوابة أمام خادم vLLM متاح على الشبكة المحلية:

```bash
python -m pip install -e ".[api]"
export GATEWAY_API_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
export VLLM_BASE_URL="http://localhost:8000"
export VLLM_MODEL_NAME="your-served-model"
uvicorn serving.gateway:app --host 127.0.0.1 --port 8080 --reload
```

هذا إعداد تطوير محلي؛ لا تربط منفذ التطوير بالإنترنت. إعدادات الإنتاج ومتطلبات حماية الشبكة موضحة في [دليل النشر](DEPLOYMENT.md).

## اكتشاف الأدوات

```bash
curl --fail-with-body \
  -H "Authorization: Bearer $GATEWAY_API_KEY" \
  "http://localhost:8080/v1/tools?locale=ja"
```

يرجع المسار تعريفات يمكن تمريرها مباشرة في حقل `tools` لطلبات Chat Completions:

```json
{
  "object": "list",
  "locale": "ja",
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "lookup_order",
        "description": "…",
        "parameters": {
          "type": "object",
          "properties": {"order_id": {"type": "string"}},
          "required": ["order_id"],
          "additionalProperties": false
        }
      }
    }
  ]
}
```

اللغات المتاحة حالياً: `ar`, `en`, `fr`, `es`, `zh-Hans`, `ja`, و`ru`. تقبل المعلمة اختصار اللغة أيضاً؛ فمثلاً `zh` يعيد الحزمة الصينية المبسطة `zh-Hans`. يعيد الرمز غير المدعوم `422`.

## طلب إكمال مع أدوات

يمكن تمرير مصفوفة `tools` المعادة كما هي إلى `/v1/chat/completions`. يمرّر الـgateway خيارات الأدوات إلى vLLM دون تنفيذ أي استدعاء:

```python
import os
import httpx

base_url = "http://localhost:8080"
headers = {"Authorization": f"Bearer {os.environ['GATEWAY_API_KEY']}"}

catalog = httpx.get(
    f"{base_url}/v1/tools?locale=ru", headers=headers, timeout=10
)
catalog.raise_for_status()

response = httpx.post(
    f"{base_url}/v1/chat/completions",
    headers=headers,
    json={
        "messages": [{"role": "user", "content": "Проверьте заказ A102."}],
        "tools": catalog.json()["tools"],
        "tool_choice": "auto",
        "parallel_tool_calls": False,
        "temperature": 0,
        "max_tokens": 256,
    },
    timeout=120,
)
response.raise_for_status()
message = response.json()["choices"][0]["message"]

# قد يحتوي على نص عادي أو tool_calls. لا تنفّذ tool_calls تلقائياً.
for call in message.get("tool_calls", []):
    function_name = call["function"]["name"]
    raw_arguments = call["function"]["arguments"]
    print(function_name, raw_arguments)
    # تحقق من allowlist والمخطط والسياق والصلاحية قبل إرسالها إلى منفّذ أدواتك.
```

القيم المدعومة لـ`tool_choice` هي `auto` و`none` و`required`، أو اختيار دالة بصيغة OpenAI. يحد `parallel_tool_calls: false` من اقتراحات التنفيذ المتوازي عندما يتطلب سير العمل تسلسلاً، لكنه ليس بديلاً عن التحقق من الحالة لدى المنفّذ.

## الأدوات ومخطط المعاملات

| الأداة | المعاملات |
|---|---|
| `lookup_order` | `order_id` مطلوب |
| `check_refund_policy` | بلا معاملات |
| `request_approval` | بلا معاملات |
| `issue_refund` | `approval_id` مطلوب |
| `ask_order_id` | بلا معاملات |
| `escalate` | بلا معاملات |
| `send_response` | `resolution` و`message` مطلوبان؛ `order_id` و`approval_id` اختياريان |
| `close_case` | بلا معاملات؛ لا تستخدمها لإنهاء مهمة غير مكتملة |

قيم `resolution`: `status`, `refund`, `declined`, `escalated`, `needs_info`, `already_refunded`, `other`.
تُترجم أوصاف الأدوات بحسب locale؛ أما أسماء الأدوات ومفاتيح JSON فتبقى ثابتة.

## مسؤوليات منفّذ الأدوات

على التطبيق المنفّذ أن:

1. يسمح فقط بأسماء الأدوات المعروفة ويتحقق من JSON arguments وفق المخطط.
2. يربط الطلب بهوية المستخدم وطلبه ومجاله المصرح به؛ لا يثق بمعرّفات أو قرارات يرسلها النموذج وحده.
3. يعيد فحص السياسة عند كل أثر جانبي، مع تحقق الطلب والأهلية والموافقة ومنع التكرار قبل الاسترداد.
4. يقيّد المعدل والحجم والمهلة، ويتعامل مع إعادة المحاولة بمفاتيح idempotency عند الحاجة.
5. يسجل قرار السياسة والنتيجة دون تسجيل مفاتيح API أو بيانات شخصية غير لازمة.
6. يعيد نتيجة الأداة إلى النموذج فقط بعد نجاح التنفيذ، ثم يتحقق مجدداً من الرد النهائي.

المحاكاة الموجودة في `environments/customer_service_agent` بيئة بحث واختبار اصطناعية، وليست خدمة تفويض أو نظاماً لمعالجة طلبات حقيقية. راجع [دليل النشر](DEPLOYMENT.md) قبل تعريض البوابة للشبكة العامة.
