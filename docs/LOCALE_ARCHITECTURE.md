# Locale architecture

PolyGlot Agents is a global project. Arabic is the first validated fixture, not the product boundary. Customer-service task semantics, state transitions, tool contracts, policy checks, rewards, and event logs belong to one language-neutral engine. Customer-facing wording and language-specific verification terms belong to locale packs.

## Current structure

```text
environments/customer_service_agent/
  __init__.py              # shared environment and backward-compatible ar entry point
  locales.py               # locale-pack loader and validation
  locales/
    ar.yaml                # Arabic reference pack
    en.yaml                # English reference pack
    fr.yaml                # French reference pack
```

The generic environment is `CustomerServiceEnv(locale="en")`. `ArabicCustomerServiceEnv` remains as a compatibility wrapper for existing callers and defaults to `locale="ar"`.

```python
from environments.customer_service_agent import CustomerServiceEnv

env = CustomerServiceEnv(locale="fr")
observation, info = env.reset(options={"scenario_id": "cs_ar_001"})
assert info["language"] == "fr"
```

## What belongs in a locale pack

A locale pack contains:

- ISO 639 and BCP-47 identifiers.
- Script and display name.
- Localized status labels and accepted evidence terms.
- Tool descriptions shown to the agent.
- Natural customer surface forms for the language or dialect.

A locale pack must not change the business meaning of a task. For example, `refund_eligible_order` has the same state and authorization requirements in Arabic, English, French, or a future low-resource language. Only the natural wording and language-specific evidence terms change.

## Running the same benchmark by locale

The runner accepts a locale independently from the benchmark's language metadata. This is useful for checking engine parity during development, but it does not make a translated fixture a reviewed benchmark.

```bash
python evaluation/run_benchmark.py \
  --benchmark evaluation/benchmarks/ar_tasks_v0.2.json \
  --split development \
  --locale en \
  --output /tmp/polyglot-en-development.json
```

The current `ar`, `en`, and `fr` packs are synthetic development fixtures. They require native-speaker review, natural task authoring, and language-specific calibration before publishing comparative scores.

## Adding a language

1. Add `environments/customer_service_agent/locales/<iso-639-1>.yaml` with every required key.
2. Keep the semantic scenario IDs and tool names stable.
3. Author natural customer messages; do not mechanically translate a benchmark and call it reviewed.
4. Add a language-specific benchmark directory and metadata for dialect, region, script, source, rights, reviewer status, and version.
5. Add tests for status evidence, tool descriptions, refusal/escalation language, and at least one end-to-end task.
6. Require native-speaker review and report quality separately from other languages.

A locale is **available** when its pack loads. A language is **benchmark-supported** only after it also has rights-cleared or explicitly synthetic data, reviewed task cards, train/dev/test separation, safety checks, and a reproducible report.
