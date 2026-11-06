# PolyGlot Agents

**Open, multilingual data and verifiable environments for AI agents.** PolyGlot Agents is a community project for assembling traceable, quality-scored language data and practical agent tasks across languages. The code is Apache-2.0; datasets retain the license of their source and are never relicensed merely by being placed in this repository.

> **Data reality check:** “publicly accessible” does not mean “free to redistribute.” Every record must retain source, source license, quality score, and human-review status. The repository contains no bulk raw crawls. Import only content whose source terms and item-level license permit the intended use. See [Data licenses](docs/DATA_LICENSES.md).

## Project goals

- Make multilingual agent data discoverable and auditable, rather than treating English as the default.
- Keep language-specific quality measurements and language codes with every record.
- Provide reproducible filtering, deduplication, quality scoring, and annotation workflows.
- Evaluate agents in environments with explicit actions, observations, and verifiable rewards.
- Separate permissively licensed open code from source-governed datasets and any future separately licensed commercial collections.

## What the project has today

The following capabilities exist in the repository today and can be inspected or run locally. They are development capabilities, not proof of production readiness or worldwide coverage.

| Capability | Current implementation | Boundary today |
|---|---|---|
| Multilingual data pipeline | ISO language normalization, language detection, filtering, deduplication, quality scoring, provenance, and per-language reports | Detection and thresholds are finite; language quality still needs native-speaker calibration |
| Rights-gated ingestion | Pinned-source connectors for OASST1 and Aya, fail-closed rights metadata checks, PII/contact screening, reject reports, duplicate reports, and SHA-256 manifests | The rights gate checks declared evidence; it is not automated legal clearance |
| Language-neutral environment | Shared Arabic/English/French engine with intent-gated refunds, approval checks, replay protection, and evidence-grounded final claims | Locale packs are synthetic development fixtures, not reviewed public benchmarks |
| Executable evaluation | 30 deterministic Arabic scenarios, 24 public development cards, machine-checkable expected outcomes, safe tool contracts, rewards, event logs, and a rule-based baseline | No protected hidden-test set is provisioned; task wording and fixtures still need native-speaker validation |
| Benchmark runner | Auditable JSON reports with benchmark, environment, and evaluator SHA-256; expected-versus-actual outcomes, safety, latency/throughput, optional token cost, failure taxonomy, and scenario/locale breakdowns; strict protocol-matched comparisons | Human review and access-controlled holdout storage remain prerequisites for official scores |
| Policy enforcement | Independent locale-neutral policy engine for verified orders, refund eligibility, customer intent, approval matching, idempotency, and replay protection | The current engine is a deterministic research policy, not a production authorization service |
| Evaluation delivery | Markdown/HTML report renderer and CI regression gate for the deterministic baseline | Thresholds are not a substitute for native-speaker review, hidden tests, or customer-impact evidence |
| Experimental model path | Optional LoRA fine-tuning and an OpenAI-compatible evaluation adapter | No claim of model quality, production safety, or customer impact |

The current implementation is therefore a **working research foundation**, not a completed global platform. See [Locale architecture](docs/LOCALE_ARCHITECTURE.md) and [Data licenses](docs/DATA_LICENSES.md) for the operational boundaries.

## Future ambition — not current capability

Our long-term goal is to build a trusted, continuously improving multilingual data and evaluation asset that helps AI agents perform real tasks across languages—not merely to accumulate files or claim coverage. If the project develops genuinely differentiated data, credible benchmarks, sustained adoption, and clear rights, it may become strategically valuable to AI companies and could someday be an acquisition candidate. An acquisition is neither guaranteed nor the definition of success.

We intend to work toward that goal through six capabilities that are **planned or incomplete**, not claims about the current repository:

1. **Distinctive, rights-cleared data:** collect or license high-value agent trajectories, tool-use traces, and task outcomes under explicit agreements that permit the intended uses. Preserve consent, attribution, provenance, retention, and deletion requirements. Publicly available corpora are useful starting points, not an exclusive data advantage.
2. **Meaningful language coverage:** prioritize languages and dialects where current agent performance is weak, with native-speaker review, script and dialect metadata, and quality measurements calibrated within each language. Depth in a focused set of languages is more valuable than unsupported claims of universal coverage.
3. **Trusted real-task benchmarks:** build reproducible evaluations for customer service, research, and coding. Measure task completion, correctness, safety, and language-specific failure modes. Keep benchmark development separate from training data to reduce contamination, and publish reviewer and validation status.
4. **A durable data engine:** make collection, rights checks, privacy screening, deduplication, quality review, and dataset updates traceable and repeatable. The differentiator should be the reliable process and improving data—not just the pipeline code.
5. **Demonstrated customer impact:** run consented pilots with organizations and publish reproducible before/after results, such as resolution rate, error rate, escalation rate, and performance by language. Do not imply customer outcomes until measured and approved for publication.
6. **A sustainable product model:** explore hosted evaluation, workflow tooling, and separately licensed commercial datasets while keeping the Apache-2.0 codebase and each dataset's own terms clear. Build toward sustained usage and revenue without weakening contributors' rights or misrepresenting open-source data as proprietary.

The first practical wedge remains a narrow, measurable use case—customer support across selected languages—with permissioned data and an independently reviewed benchmark. Expand to other languages and tasks only as the project can support them with comparable provenance and validation. The current OASST1 samples, locale packs, and benchmark cards are groundwork; they are not exclusive assets, customer validation, or completed multilingual benchmarks.

## Developer reference: the strategic capability map

PolyGlot Agents should grow from a multilingual data repository into a **reliability platform for multilingual agents**. The goal is not to own a slightly better language model. The goal is to prove, with licensed data and reproducible evidence, that an agent can understand a request, use tools, make a safe decision, complete a real task, and recover from failures across languages and dialects.

The target closed loop is:

```text
licensed data
  -> privacy, rights and quality screening
  -> human language and safety review
  -> executable tasks and hidden evaluation split
  -> agent/tool interaction with verifiable state
  -> safety and business metrics
  -> training or policy improvement
  -> production regression cases
```

### Future capabilities to build

1. **Rights-cleared, defensible data.** Public datasets are a starting point, not the long-term moat. Build permissioned datasets from real or carefully simulated workflows. Every record should retain source, revision, license, consent basis, retrieval date, allowed use, attribution requirements and deletion status. Track derived files and model releases so a source can be quarantined or removed consistently.

2. **Executable environments, not text-only tests.** Each environment should contain hidden state, explicit tools, permissions, transient and permanent failures, timeouts, idempotency rules, event logs, verifiable rewards and protection against reward hacking. A successful response is not enough; the agent must produce the correct outcome without an unauthorized action.

3. **Deep language and dialect coverage.** Treat each language, region, script, dialect, and code-switched form as an explicit evaluation dimension when the task requires it. Arabic is the first fixture, not the project boundary. Preserve spelling variation, speech-transcription noise, politeness conventions, and language-specific metadata. Do not claim multilingual coverage from empty language folders.

4. **Independent, versioned and hidden benchmarks.** Maintain public development tasks and a protected test split that never enters training. Version every benchmark, record native-speaker review and inter-rater agreement, and prevent post-hoc changes to published scores. Report performance by language, dialect, scenario and failure type rather than one aggregate score.

5. **Native-speaker annotation operations.** Add review queues per language and dialect for language quality, factuality, task correctness, tool arguments, safety, cultural fit and privacy risk. Record reviewer identity in protected systems, review date, rubric version, confidence and disagreement. Require a second review on a measured sample.

6. **Multi-dimensional quality and risk scoring.** Replace a single unexplained quality number with separate signals such as language quality, instruction following, factuality, safety, tool correctness, cultural fit, privacy risk and training value. Calibrate thresholds per language and detect contamination, semantic duplicates, machine translation, synthetic data, contradictions and unsupported claims.

7. **Policy and permission enforcement outside the model.** Use the following boundary for every sensitive workflow:

   ```text
   LLM proposes an action
       -> policy engine checks state and permissions
       -> tool gateway executes or rejects
       -> audit log records the decision
   ```

   The model must never directly issue refunds, modify orders, delete records or access customer credentials. The policy layer must enforce identity, authorization, idempotency, approval freshness and truthfulness of the final response.

8. **Production regression loop.** Capture privacy-screened failure patterns from deployments: unsafe attempts, tool errors, parsing failures, latency, cost, timeouts, escalation quality and language-specific failures. Convert each validated failure into a regression task, review it, evaluate it, and only then use it for policy or model improvement.

9. **Model and provider comparison.** Run the same seed, tasks and tool contracts against the rule-based baseline, base model, LoRA model and external APIs. Report task success, safe completion, unsafe-action rate, unsupported claims, tool selection and argument accuracy, recovery rate, latency and cost per successful task.

10. **Reproducible training and model releases.** Every adapter or merged model must record the exact base-model revision, data manifest, source licenses, filtering version, hyperparameters, adapter hash, benchmark results and known limitations. Never train on the hidden test split. Keep unmerged LoRA adapters for rollback and reconstruction.

11. **Secure production API.** Provide an OpenAI-compatible interface, streaming, authentication, quotas, rate limiting, tenant isolation, audit trace IDs, model rollback and private or on-premise deployment. Keep vLLM private behind a gateway. Do not expose arbitrary adapter loading or tool credentials to callers.

12. **Multilingual red-team suite.** Test prompt injection, tool injection, data exfiltration, social engineering, impersonation, replayed approvals, reward exploitation, multilingual jailbreaks and language mixing intended to bypass filters. Measure whether safety holds under pressure, not only whether the model produces a fluent answer.

13. **Contributor and reviewer ecosystem.** Create language maintainers, environment owners, data stewards, benchmark authors, legal reviewers and safety reviewers. Every contribution must pass rights, schema, privacy, language, quality and contamination checks. Reward high-quality review without weakening provenance requirements.

14. **Business-impact evidence.** Run consented pilots and measure first-contact resolution, escalation, handling time, unsafe action prevention, language-specific quality and cost per successful task. Product claims must be backed by before/after methodology and reproducible evaluation artifacts.

### Current status and remaining gaps

The repository already has approved-source importing with pinned revisions, provenance and deduplication; experimental LoRA fine-tuning; vLLM/FastAPI deployment files; a verifiable customer-service environment with Arabic, English, and French locale packs; locale-aware deterministic baselines; an independent policy engine; an OpenAI-compatible evaluation adapter; publishable Markdown/HTML reports; and a CI regression gate. The locale packs are synthetic development fixtures and are not yet native-speaker-validated public benchmarks. See [Locale architecture](docs/LOCALE_ARCHITECTURE.md).

The highest-priority gaps are permissioned or partner data, native-speaker review for each locale, protected hidden test storage, dialect-specific task authoring, a review/annotation workflow, production regression data, comparisons against real models, and customer pilots.

### Future delivery roadmap

**Next 30 days:** obtain native-speaker review for the 24 public Arabic development cards; author a fresh holdout in access-controlled storage (never reuse task text previously committed to public Git history); add prompt-injection and tool-failure cases; strengthen policy reason-code auditing; and publish versioned JSON, Markdown, and HTML reports.

**By 60 days:** author independent English and French task cards rather than relying on translated parity; add Arabic dialect profiles; implement annotation queues; expand the multilingual red-team suite; record cost and latency; and extend regression gates to reviewed language-specific baselines.

**By 90 days:** secure the first data or pilot partner; collect rights-cleared workflow traces; connect production failures to benchmark tasks; publish a dashboard and a model-comparison report.

The current public executable milestone is [`ar_tasks_v0.2.json`](evaluation/benchmarks/ar_tasks_v0.2.json): 24 development cards mapped to 24 deterministic customer-service scenarios. The former public “hidden” placeholders were removed from the current tree because data inside a public repository is not hidden; their text remains in prior Git history and is permanently unsuitable as a secret holdout. No protected test set is currently provisioned. Every active customer-service card now declares an `expected_outcome` that CI checks against the environment scenario goal. The synthetic task cards still require native-speaker review and are not evidence of production performance. The runner defaults to the development split:

```bash
python evaluation/run_benchmark.py \
  --benchmark evaluation/benchmarks/ar_tasks_v0.2.json \
  --split development \
  --output /tmp/polyglot-ar-v0.2-development.json
```

Validate every benchmark task contract locally with:

```bash
python -m scripts.validate_benchmarks
# Or, after installing the package:
polyglot-validate-benchmarks
```

The validator checks required metadata and task fields, unique task IDs, declared split names, hidden-test exclusion from public files, task-count consistency, scenario references, and the machine-readable expected outcome against the executable environment's goal. Protected files can be checked separately with `--protected-benchmark /secure/path/holdout.json`; they must contain hidden tasks only. It deliberately does not treat placeholder language files as runnable benchmarks. See [Benchmark release and trust gates](docs/BENCHMARK_RELEASE.md) for the current readiness status, review contract, and holdout handling rules.

The runner records benchmark, environment, and evaluator hashes; review status; expected-versus-actual outcome; task success; safety violations; tool calls; truncation; reward; and event log. Future hidden cases must remain outside the public repository in access-controlled maintainer storage and be supplied explicitly with `--protected-benchmark`; use `--split hidden` or `--split all` only with that file. `.gitignore` is a local safeguard, not access control. Native-speaker review and genuinely protected test storage remain prerequisites for official scores.

Each report now also contains a non-exclusive failure taxonomy in `aggregate.failure_reasons`
and breakdowns under `aggregate.failure_breakdown.by_scenario` and
`aggregate.failure_breakdown.by_locale`. The labels distinguish `agent_error`,
`unsafe_action`, `unsupported_claim`, `step_budget_exhausted`, `outcome_mismatch`,
and a residual `task_failure`. A task can receive multiple labels, so these counts are
diagnostic evidence rather than a competing success-rate denominator.

Render a saved JSON report for review or publication without rerunning the agent:

```bash
python -m evaluation.report \
  --input /tmp/polyglot-ar-v0.2-development.json \
  --markdown-output /tmp/polyglot-ar-v0.2-development.md \
  --html-output /tmp/polyglot-ar-v0.2-development.html
```

The standalone outputs include protocol hashes, aggregate metrics, failure taxonomy,
and scenario/locale tables. The same command is available after installation as
`polyglot-render-report`.

CI also runs the deterministic Arabic baseline through
`evaluation/check_regression.py`. Its default gate requires `success_rate` and
`safe_completion_rate` of at least `1.0`, and `unsafe_action_rate` and
`unsupported_claim_rate` of at most `0.0`. These strict thresholds apply only to the
known rule-based baseline; experimental models can use explicit thresholds such as
`--success-rate-min 0.7` and `--unsafe-action-rate-max 0.05`.

Only after these steps should the project expand broadly into additional languages, commerce, research, coding and enterprise workflows. Depth, evidence and rights are more valuable than a large directory of unvalidated languages.

## Global coverage roadmap

The long-term strategic ambition is to make PolyGlot Agents a **Global Multilingual and Multimodal Agent Data & Reliability Platform**. This is an ambition for an open, extensible system—not a claim that the project already owns data for every language, dialect, topic, technology, or modality. Coverage must always be measured, licensed, documented, and reproducible.

The platform should model coverage across four independent dimensions:

```text
Languages / Dialects
Domains / Topics
Technologies / Tasks
Data Modalities / Formats
```

These dimensions form a coverage matrix such as `language × dialect × domain × task × modality × review status`. For example, a record may represent Moroccan Arabic + customer service + e-commerce + text conversation + tool use + licensed data + human review, while another may represent Japanese + programming + Python + executable code repair + repository data + execution-based testing.

### Strategic workstreams

1. **Open language and dialect registry.** Evolve beyond a static language list toward a registry using ISO 639-1/639-3, BCP 47, script, region, dialect metadata, resource level, documentation status, native-speaker review, coverage, and confidence. Dialects without an official code should use an internal identifier rather than an invented ISO code.
2. **Common multimodal data contract.** Support text, conversations, tool actions, agent trajectories, code, tables, databases, knowledge graphs, images, audio, video, PDFs, geospatial, time-series, sensor, scientific, and industrial data through independent adapters. Shared metadata should include `id`, `source`, `license`, `provenance`, `language`, `dialect`, `modality`, `domain`, `quality`, `safety`, and `human_review`.
3. **Extensible domain taxonomy.** Cover business, customer service, finance, health, law, education, science, engineering, programming, cybersecurity, manufacturing, logistics, travel, government, agriculture, media, retail, and research. High-risk domains require stronger expert review and controls than general-purpose data.
4. **Technology registry and executable evaluation.** Register technologies such as programming languages, databases, APIs, Docker, Kubernetes, MCP, robotics, IoT, computer vision, speech, and scientific computing. Each technology needs tasks, tool contracts, a test environment, operational and security checks, version metadata, and deprecation information. Code evaluation must test compilation, behavior, regression tests, API compatibility, and security—not just text similarity.
5. **Composable model architecture.** Prefer routing and adapters over forcing all languages, domains, and modalities into one undifferentiated model:

   ```text
   base multilingual model
     -> language / dialect adapters
     -> domain adapters
     -> task adapters
     -> tool-use policies
     -> retrieval and routing layer
   ```

6. **Coverage dashboard and evidence.** Publish what is covered, partially covered, under development, or missing. Every supported language, dialect, technology, or modality must have a data card, provenance, rights status, quality report, review status, benchmark or task card, and known limitations.

### Architecture to grow toward

The implementation should move toward independent, composable plugins rather than manual edits to central files:

```text
language_registry/
domain_registry/
technology_registry/
modality_adapters/
source_connectors/
schema_registry/
quality_engine/
annotation_platform/
rights_engine/
benchmark_engine/
policy_engine/
model_router/
coverage_dashboard/
```

### Definition of supported

A language, dialect, technology, or dataset should not be marked **supported** merely because an empty directory or configuration entry exists. The contribution must provide:

1. A documented and appropriately licensed source.
2. A valid schema and language/dialect/domain metadata.
3. PII and safety screening.
4. Deduplication and provenance tracking.
5. Appropriate human or expert review.
6. A benchmark, executable task, or task card.
7. Train/dev/test separation, including a protected test split where applicable.
8. A coverage and quality report.
9. Regression tests and reproducible versioning.
10. Documentation of limitations, bias, and rights constraints.

### Global expansion phases

**Phase 1 — Foundations:** support ISO and BCP 47 metadata; establish the language, domain, and technology registries; convert the pipeline to a plugin architecture; and stabilize text, conversations, tool traces, and code.

**Phase 2 — Modalities and verification:** add image, audio, video, PDF, and table adapters; establish native-speaker review workflows; add a sandbox for executable code; and publish the first coverage dashboard.

**Phase 3 — Adapters and routing:** add validated language, dialect, domain, and technology adapters; build the model router; add domain retrieval; and publish multilingual and multimodal benchmarks.

**Phase 4 — Global ecosystem:** accept international contributions, form data partnerships across sectors, onboard licensed operational data, support private/on-premise deployments, and publish commercial impact reports backed by evidence.

The official ambition is therefore not “we own data for every language and topic.” It is:

> **We are building the open infrastructure that allows any language, dialect, domain, technology, or data modality to be added—and verifies its rights, quality, safety, and performance with measurable evidence.**

The project’s defensible advantage should be the combination of coverage, provenance, human review, executable environments, benchmarks, policy enforcement, adapters, failure tracking, and a global contributor community. Every coverage claim must remain linked to inspectable evidence.

## Repository layout

```text
datasets/{raw,curated}/{lang_code}/{sft,tool_use,rlhf}/
pipelines/{filtering,deduplication,quality_scoring,annotation}/
environments/customer_service_agent/
evaluation/benchmarks/{lang_code}_tasks.json
docs/{DATA_LICENSES.md,LANGUAGE_STRATEGY.md,CONTRIBUTING.md}
configs/*.yaml
scripts/requirements.txt
scripts/scaffold_language.py
```

Language directories are created on demand using canonical ISO 639 codes. Region, script, dialect, and dataset-native tags remain in record metadata. Tiering is a contribution and validation strategy, not a hard-coded limit: any registered ISO 639-1 language is accepted, and ISO 639-3 is used when no alpha-2 code exists. Coverage and quality are reported per language. For very large sources, store download manifests and derived metadata here; do not commit raw corpora.

## Quick start

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r scripts/requirements.txt
python scripts/lang_id.py --input examples/multilingual.jsonl --output /tmp/lang.jsonl
python scripts/filter_data.py --input /tmp/lang.jsonl --output /tmp/filtered.jsonl
python scripts/deduplicate.py --input /tmp/filtered.jsonl --output /tmp/curated.jsonl
python scripts/score_quality.py --input /tmp/curated.jsonl --output /tmp/scored.jsonl
python scripts/import_oasst.py --source-lang ar --lang-code ar --output /tmp/oasst-ar.jsonl --limit 10
python scripts/import_oasst.py --list-languages
python scripts/import_oasst.py --all-languages --output-root datasets/curated --limit 100
python scripts/language_report.py --input datasets/curated --output /tmp/language-report.json
python scripts/scaffold_language.py --code sw --source-tag sw
python scripts/auto_import.py --limit-per-language 100
python -m scripts.validate_records --input examples/multilingual.jsonl
python -m scripts.validate_benchmarks
python -m unittest discover -s tests -v
```

### Development install and tests

For the executable environments, language registry, and test suite, install the project in editable mode with its test dependencies:

```bash
python -m pip install -e ".[test]"
python -m pytest -q
```

The larger ingestion stack is optional; install it with `python -m pip install -e ".[pipeline]"` when using fastText or the Hugging Face dataset importers. Model-training dependencies remain separate and can be installed with `python -m pip install -e ".[training]"`. GitHub Actions runs the tests on Python 3.10, 3.11, and 3.12 and checks the repository's JSON/YAML files.

`validate_records.py` checks the data contract before a JSONL file enters a pipeline:
required source and license metadata, canonical language codes, provenance timestamps,
bounded quality scores, review status, and content type. Add `--language <code>` to
enforce one language per file. After an editable install, the equivalent entry point is
`polyglot-validate-records`.

`tests/test_benchmark_stress.py` adds offline load checks: it loads 10,000 benchmark cards, runs 1,000 deterministic customer-service episodes while checking success and safety, and verifies order-ID extraction from a customer message larger than 1 MB. The timing assertions are intentionally generous regression limits; these tests exercise the local rule-based baseline and do not call external model APIs.

`tests/test_redteam_safety.py` checks Arabic, English, and French instruction-injection attempts against the refund tools, fake/replayed approvals, customer-intent enforcement, and contradictory status claims. These tests validate deterministic environment safeguards; they do not establish that an external model resists prompt injection.

`lang_id.py` uses fastText's language-identification model and normalizes predictions to ISO 639-1 when available, otherwise ISO 639-3. It downloads the official model to a local cache on first run; alternatively, pass `--model /path/to/lid.176.ftz`. Low-confidence results and declared/detected conflicts are marked `needs_review`; the input language tag is preserved. Unlabelled input is routed to review by default; `--auto-accept-unlabelled` is an opt-in for workflows that accept the finite detector's risk. fastText lid.176 has finite coverage and is not a universal language oracle. If a trusted source tag is outside detector coverage, the tag is retained instead of replacing it with a guess. Licensed data for languages it does not confidently detect can still be imported using a verified source tag.

### Open language registry

`configs/languages.yaml` is an open catalog, not a whitelist. `scripts/language_registry.py` resolves any valid ISO 639 or BCP-47 tag, preserves the exact source tag, and derives `lang_code`, `bcp47`, `script`, and `region` metadata. A language can enter staging even when it has no catalog profile; it is then marked `open_unregistered` and routed for review rather than rejected solely because a detector or config file lacks an entry.

Validate a proposed language before adding a connector or benchmark:

```bash
python -m scripts.language_registry --code sw
python -m scripts.language_registry --code pt-BR
```

The automated ingestion pipeline enriches each record with the resolved language metadata and keeps `source_lang_tag` unchanged. Registry membership is descriptive; it does not by itself mean that a language is benchmark-supported. Rights, schema, privacy, quality, native-speaker review, and benchmark checks remain separate gates.

### Experimental fine-tuning

The optional `scripts/fine_tune.py` trains a causal language model on reviewed JSONL records. It defaults to LoRA so the base model remains unchanged and only a small adapter is saved. Training dependencies are intentionally separate from the data pipeline:

```bash
pip install -r scripts/requirements-training.txt
python scripts/fine_tune.py --model <huggingface-model-id> --data /path/to/reviewed.jsonl --dry-run
python scripts/fine_tune.py --model <huggingface-model-id> --data /path/to/reviewed.jsonl --output outputs/polyglot-lora
```

If `--data` is omitted, the script searches `datasets/incoming/*/curated/*/sft/auto_import.jsonl`. Only records with `human_review_status: reviewed` are used by default. The script creates a deterministic train/validation split, supports chat templates when available, records languages and data files in `training_manifest.json`, and does not upload models or data. Use `--dry-run` first, and review licenses and the source manifest before training or publishing an adapter. This is an experimental SFT path, not evidence that the resulting model is factually correct or production-safe.

### Customer-service environment

The customer-service Gymnasium environment is an executable multi-step simulation with structured tool calls, hidden ground-truth state, a rule-based final verifier, bounded reward components, safety penalties, reproducible event logs, a step budget, and locale packs for Arabic, English, and French. Refund approval now requires both an eligible order and explicit refund intent in the scenario; duplicate/replayed refunds are rejected. Final status/refund/escalation claims are checked against state, contradictory status labels are rejected, and unsupported claims are marked in the event log. Its 30 synthetic scenarios cover status lookup, refunds, missing information, escalation, ineligible/duplicate refunds, privacy-safe refusal, and transient tool failure. It performs no real customer or payment actions. Keep trainer-side `info` fields out of the agent observation. Run the end-to-end refund episode with:

```bash
python -m environments.customer_service_agent.demo
```

The current executable benchmark is `evaluation/benchmarks/ar_tasks_v0.2.json` with 24 public development cards and no provisioned hidden split. The fixtures and task descriptions have not yet received native-speaker benchmark validation. Running the same semantic fixture through the `en` and `fr` locale packs demonstrates engine parity, not reviewed English or French benchmark coverage. A data sample alone is not a validated evaluation benchmark. `evaluation/language_coverage_report.json` is a point-in-time report for the bundled samples.

### Verifiable benchmark runner

Run the locale-aware deterministic baseline over every development task and write an auditable JSON report:

```bash
python evaluation/run_benchmark.py --locale ar --output /tmp/polyglot-benchmark-report.json
```

The report includes task success, safe completion, expected-versus-actual outcome alignment, transient tool-error recovery, unsafe-action rate, unsupported-claim count/rate, truncation rate, tool-call count, reward mean/standard deviation, per-action timing/token usage where available, and the full event log. It fingerprints the benchmark, environment bundle, evaluator and model adapter; the report also carries the benchmark's human-review status. The baseline is intentionally inspectable and is not an LLM score; use it as a sanity check before adding model adapters. The current development fixture produces 24 successful, safe episodes with the baseline, but is not yet a native-speaker-validated public benchmark.

If a maintainer later provisions a genuinely protected holdout outside Git, validate and run it explicitly:

```bash
python -m scripts.validate_benchmarks \
  --protected-benchmark /secure/maintainer/ar_holdout.json
python evaluation/run_benchmark.py \
  --split hidden \
  --protected-benchmark /secure/maintainer/ar_holdout.json \
  --output /tmp/polyglot-ar-hidden-report.json
```

The protected file must match the public benchmark ID/version/language/environment, contain only `hidden` tasks, and use task and scenario IDs disjoint from development. The software validates structure; access control must be provided by the storage system. Do not add protected task files to Git.

To evaluate a deployed vLLM/FastAPI model through its OpenAI-compatible endpoint:

```bash
export POLYGLOT_AGENT_API_KEY='<gateway-key>'
python evaluation/run_benchmark.py \
  --agent openai-compatible \
  --base-url http://localhost:8080 \
  --model polyglot-ar \
  --output /tmp/polyglot-model-report.json
```

The adapter sends only the current observation and available tool names, requires a strict JSON action, and records parsing/API failures as failed tasks. The gateway should be reachable over TLS in production. Never pass customer credentials or real tool secrets to the model; this benchmark uses the synthetic environment only.

Each task records `agent_action_latency_ms` for every `agent.act()` call. The aggregate reports mean, p50, p95, p99, maximum, error rate, benchmark wall time, and tasks/actions per second. These are client-observed action latencies—including network, provider queueing, generation, and response parsing—not provider-internal GPU time. Use `--concurrency 4` to run up to four independent episodes simultaneously; steps within an episode remain sequential. Start with concurrency `1` and increase gradually to respect provider rate limits.

When the compatible API returns usage metadata, reports also include prompt, completion, and total tokens per task and for the run. Cost remains opt-in: supply both `--input-price-per-million-tokens` and `--output-price-per-million-tokens` using the rates applicable to your provider/model, and optionally set `--price-currency`. The runner estimates total cost and cost per successful task only when every model action has complete prompt/completion counts; otherwise the estimate is `null`, not zero. Prices are not fetched automatically and the estimate may not reflect provider-specific cached-token or other billing rules.

### Protocol-matched model comparison

Every benchmark report includes SHA-256 hashes of the benchmark file, customer-service environment/locale bundle, and evaluator/adapter source. The comparator also verifies the declared review status and checks that aggregate task counts match unique per-task results. To compare models, first run each model with the same benchmark file, environment bundle, evaluator, split, locale, seed, step budget, and concurrency. Then generate a side-by-side scorecard:

```bash
python evaluation/compare_reports.py \
  --report baseline=/tmp/baseline-report.json \
  --report ollama=/tmp/ollama-report.json \
  --report openai=/tmp/openai-report.json \
  --output /tmp/model-comparison.json \
  --markdown-output /tmp/model-comparison.md
```

The comparator fails closed if protocol fields, benchmark content, environment/evaluator hashes, or result counts differ, and rejects cost comparisons across currencies. The first report is the delta reference. It reports quality, safety, latency, throughput, and cost separately—there is no opaque composite score or automatic “winner.” Pending human review remains visible and is not promoted to an official score by the software.

### Importing real source data

`scripts/import_oasst.py --list-languages` lists the current OASST1 source tags. Use `--source-lang` for one source tag, or `--all-languages --output-root datasets/curated` to stream the source once and write separate monolingual files. Canonical ISO codes name folders; tags such as `pt-BR` remain attached to their records. The bundled snapshot contains 1,661 human-reviewed SFT pairs across 23 languages from the tags that passed its filters; each is capped at 100 records, and smaller counts reflect the source's available records, not synthetic padding. The importer excludes synthetic/deleted messages and records without zero PII/spam flags, checks common contact patterns, and records source IDs and license metadata. `--limit` is for tests or samples only. `scripts/language_report.py` reports sample counts, score distributions, human review, duplicates, source mix, and review routing separately per language. Use `scripts/scaffold_language.py --code <ISO-code>` to create all dataset-stage folders and a benchmark card marked as requiring native-speaker authorship; it deliberately does not fabricate evaluation tasks. Other sources must be acquired under their own terms and normalized with full provenance. Do not infer a license from a hosting platform or crawl alone.

### Automated approved-source import

`scripts/auto_import.py` runs only sources marked `enabled: true` in `configs/sources.yaml`, and every enabled source must pass the fail-closed rights gate in `scripts/rights_engine.py`: pinned revision, source card, license URL, reviewed rights status, allowed uses, explicit redistribution permission, and a commercial-use policy. The current approved sources are the reviewed OASST1 conversations and the human-annotated Aya instruction dataset. The run writes to an isolated timestamped directory under `datasets/incoming/`, preserves source revision and license metadata, records a content SHA-256 for each imported source, screens records, removes contact patterns and cross-source duplicates, and writes a versioned `manifest.json`, reject reports, and duplicate reports. It never promotes records directly into `datasets/curated`; review the manifest and reports first.

For a bounded reproducible run:

```bash
# Check source rights metadata without downloading data
python scripts/auto_import.py --validate-only

# Run a bounded import after validation
python scripts/auto_import.py --limit-per-language 100
```

Wikimedia and arXiv remain disabled by default. Their materials require source-specific license handling and must not be mixed into the approved training pool without preserving attribution, ShareAlike or article-level license constraints. A dataset host or download URL is never treated as proof that all records are safe to redistribute.

## Data record contract

Every record must include:

```json
{
  "id": "stable-source-id",
  "text": "content",
  "lang_code": "ar",
  "source": "publisher-or-dataset",
  "source_url": "https://example.org/item",
  "license": "CC-BY-4.0",
  "quality_score": 0.91,
  "human_review_status": "unreviewed",
  "content_type": "sft",
  "provenance": {"retrieved_at": "2026-01-01T00:00:00Z"}
}
```

`quality_score` is in `[0,1]`; it is a screening signal, not a factuality or safety guarantee. `human_review_status` is one of `unreviewed`, `reviewed`, or `rejected`. Keep one language per file and report metrics by language.

## Project status and contribution

Early-stage project. We welcome language maintainers, dataset engineers, evaluation designers, and native-speaker reviewers. Start with [Contributing](docs/CONTRIBUTING.md) and the [language strategy](docs/LANGUAGE_STRATEGY.md). Please submit small manifests and reproducible scripts; do not push large datasets or personal information.

## License

Source code is available under Apache License 2.0 (see `LICENSE`). Data and documentation copied or adapted from external sources remain governed by their original licenses; see `docs/DATA_LICENSES.md` and each record's provenance. The project license does not override those terms.
