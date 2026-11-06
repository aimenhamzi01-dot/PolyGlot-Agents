# PolyGlot Agents

**Open, multilingual data and verifiable environments for AI agents.** PolyGlot Agents is a community project for assembling traceable, quality-scored language data and practical agent tasks across languages. The code is Apache-2.0; datasets retain the license of their source and are never relicensed merely by being placed in this repository.

> **Data reality check:** “publicly accessible” does not mean “free to redistribute.” Every record must retain source, source license, quality score, and human-review status. The repository contains no bulk raw crawls. Import only content whose source terms and item-level license permit the intended use. See [Data licenses](docs/DATA_LICENSES.md).

## Project goals

- Make multilingual agent data discoverable and auditable, rather than treating English as the default.
- Keep language-specific quality measurements and language codes with every record.
- Provide reproducible filtering, deduplication, quality scoring, and annotation workflows.
- Evaluate agents in environments with explicit actions, observations, and verifiable rewards.
- Separate permissively licensed open code from source-governed datasets and any future separately licensed commercial collections.

## Long-term ambition

Our long-term goal is to build a trusted, continuously improving multilingual data and evaluation asset that helps AI agents perform real tasks across languages—not merely to accumulate files or claim coverage. If the project develops genuinely differentiated data, credible benchmarks, sustained adoption, and clear rights, it may become strategically valuable to AI companies and could someday be an acquisition candidate. An acquisition is neither guaranteed nor the definition of success.

We intend to work toward that goal through six evidence-based capabilities:

1. **Distinctive, rights-cleared data:** collect or license high-value agent trajectories, tool-use traces, and task outcomes under explicit agreements that permit the intended uses. Preserve consent, attribution, provenance, retention, and deletion requirements. Publicly available corpora are useful starting points, not an exclusive data advantage.
2. **Meaningful language coverage:** prioritize languages and dialects where current agent performance is weak, with native-speaker review, script and dialect metadata, and quality measurements calibrated within each language. Depth in a focused set of languages is more valuable than unsupported claims of universal coverage.
3. **Trusted real-task benchmarks:** build reproducible evaluations for customer service, research, and coding. Measure task completion, correctness, safety, and language-specific failure modes. Keep benchmark development separate from training data to reduce contamination, and publish reviewer and validation status.
4. **A durable data engine:** make collection, rights checks, privacy screening, deduplication, quality review, and dataset updates traceable and repeatable. The differentiator should be the reliable process and improving data—not just the pipeline code.
5. **Demonstrated customer impact:** run consented pilots with organizations and publish reproducible before/after results, such as resolution rate, error rate, escalation rate, and performance by language. Do not imply customer outcomes until measured and approved for publication.
6. **A sustainable product model:** explore hosted evaluation, workflow tooling, and separately licensed commercial datasets while keeping the Apache-2.0 codebase and each dataset's own terms clear. Build toward sustained usage and revenue without weakening contributors' rights or misrepresenting open-source data as proprietary.

The first practical wedge is a narrow, measurable use case—such as Arabic customer support and its dialects—with permissioned data and an independently reviewed benchmark. Expand to other languages and tasks only as the project can support them with comparable provenance and validation. The current OASST1 samples and scaffolded benchmark cards are groundwork; they are not exclusive assets, customer validation, or completed multilingual benchmarks.

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

### Capabilities the project should build

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

### Current status and gaps

The repository already has approved-source importing with pinned revisions, provenance and deduplication; experimental LoRA fine-tuning; vLLM/FastAPI deployment files; a verifiable customer-service environment with Arabic, English, and French locale packs; locale-aware deterministic baselines; and an OpenAI-compatible evaluation adapter. The locale packs are synthetic development fixtures and are not yet native-speaker-validated public benchmarks. See [Locale architecture](docs/LOCALE_ARCHITECTURE.md).

The highest-priority gaps are permissioned or partner data, native-speaker review, a hidden test split, multiple Arabic dialects, an independent policy engine, a review/annotation workflow, production regression data, cost and latency reporting, comparisons against real models, and customer pilots.

### Delivery roadmap

**First 30 days:** expand the Arabic environment to 30–50 tasks; add prompt-injection and tool-failure cases; define a benchmark schema and train/dev/test split; separate the policy verifier; run the real API adapter; publish JSON and HTML reports.

**By 60 days:** add three Arabic dialect profiles; onboard native-speaker reviewers; implement annotation queues; add the multilingual red-team suite; record cost and latency; and block safety regressions in CI.

**By 90 days:** secure the first data or pilot partner; collect rights-cleared workflow traces; connect production failures to benchmark tasks; publish a dashboard and a model-comparison report.

The first executable milestone is now tracked as [`ar_tasks_v0.1.json`](evaluation/benchmarks/ar_tasks_v0.1.json): 30 task cards mapped one-to-one to 30 independent deterministic Arabic customer-service scenarios, with 24 development tasks and 6 declared hidden-test placeholders. The task cards and fixtures are synthetic and still require native-speaker review; they are not evidence of production performance. Run only the development split by default when preparing a model or report:

```bash
python evaluation/run_benchmark.py \
  --benchmark evaluation/benchmarks/ar_tasks_v0.1.json \
  --split development \
  --output /tmp/polyglot-ar-v0.1-development.json
```

The runner records the benchmark version, split, task category, success, safe completion, safety violations, tool calls, truncation, reward, and event log. The hidden split must remain outside training and should be moved to protected maintainer storage before publishing official scores. The current 30 scenarios cover status lookup, clarification, transient recovery, eligible and ineligible refunds, duplicate prevention, escalation, and privacy-safe refusal. Native-speaker review and protected test storage remain the next validation steps.

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
python -m unittest discover -s tests -v
```

`lang_id.py` uses fastText's language-identification model and normalizes predictions to ISO 639-1 when available, otherwise ISO 639-3. It downloads the official model to a local cache on first run; alternatively, pass `--model /path/to/lid.176.ftz`. Low-confidence results and declared/detected conflicts are marked `needs_review`; the input language tag is preserved. Unlabelled input is routed to review by default; `--auto-accept-unlabelled` is an opt-in for workflows that accept the finite detector's risk. fastText lid.176 has finite coverage and is not a universal language oracle. If a trusted source tag is outside detector coverage, the tag is retained instead of replacing it with a guess. Licensed data for languages it does not confidently detect can still be imported using a verified source tag.

### Experimental fine-tuning

The optional `scripts/fine_tune.py` trains a causal language model on reviewed JSONL records. It defaults to LoRA so the base model remains unchanged and only a small adapter is saved. Training dependencies are intentionally separate from the data pipeline:

```bash
pip install -r scripts/requirements-training.txt
python scripts/fine_tune.py --model <huggingface-model-id> --data /path/to/reviewed.jsonl --dry-run
python scripts/fine_tune.py --model <huggingface-model-id> --data /path/to/reviewed.jsonl --output outputs/polyglot-lora
```

If `--data` is omitted, the script searches `datasets/incoming/*/curated/*/sft/auto_import.jsonl`. Only records with `human_review_status: reviewed` are used by default. The script creates a deterministic train/validation split, supports chat templates when available, records languages and data files in `training_manifest.json`, and does not upload models or data. Use `--dry-run` first, and review licenses and the source manifest before training or publishing an adapter. This is an experimental SFT path, not evidence that the resulting model is factually correct or production-safe.

### Customer-service environment

The Arabic Gymnasium v1 environment is an executable multi-step simulation with structured tool calls, hidden ground-truth state, a rule-based final verifier, bounded reward components, safety penalties, reproducible event logs, and a step budget. Its seven synthetic scenarios cover status lookup, refunds, missing information, escalation, ineligible/duplicate refunds, and a transient tool failure. It performs no real customer or payment actions. Keep trainer-side `info` fields out of the agent observation. Run the end-to-end refund episode with:

```bash
python -m environments.customer_service_agent.demo
```

Arabic development tasks are in `evaluation/benchmarks/ar_tasks.json`. The fixture and its task descriptions have not yet received native-speaker benchmark validation. English task parity and native-speaker-reviewed benchmark tasks for additional data languages remain planned; a data sample alone is not a validated evaluation benchmark. `evaluation/language_coverage_report.json` is a point-in-time report for the bundled samples.

### Verifiable benchmark runner

Run the deterministic Arabic baseline over every development task and write an auditable JSON report:

```bash
python evaluation/run_benchmark.py --output /tmp/polyglot-benchmark-report.json
```

The report includes task success, safe completion, unsafe-action rate, truncation rate, tool-call count, reward and the full event log. The baseline is intentionally inspectable and is not an LLM score; use it as a sanity check before adding model adapters. The current development fixture produces seven successful, safe episodes with the baseline, but it is not yet a native-speaker-validated public benchmark.

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

### Importing real source data

`scripts/import_oasst.py --list-languages` lists the current OASST1 source tags. Use `--source-lang` for one source tag, or `--all-languages --output-root datasets/curated` to stream the source once and write separate monolingual files. Canonical ISO codes name folders; tags such as `pt-BR` remain attached to their records. The bundled snapshot contains 1,661 human-reviewed SFT pairs across 23 languages from the tags that passed its filters; each is capped at 100 records, and smaller counts reflect the source's available records, not synthetic padding. The importer excludes synthetic/deleted messages and records without zero PII/spam flags, checks common contact patterns, and records source IDs and license metadata. `--limit` is for tests or samples only. `scripts/language_report.py` reports sample counts, score distributions, human review, duplicates, source mix, and review routing separately per language. Use `scripts/scaffold_language.py --code <ISO-code>` to create all dataset-stage folders and a benchmark card marked as requiring native-speaker authorship; it deliberately does not fabricate evaluation tasks. Other sources must be acquired under their own terms and normalized with full provenance. Do not infer a license from a hosting platform or crawl alone.

### Automated approved-source import

`scripts/auto_import.py` runs only sources marked `enabled: true` in `configs/sources.yaml`, and every enabled Hugging Face source must have a pinned commit revision. The current approved sources are the reviewed OASST1 conversations and the human-annotated Aya instruction dataset. The run writes to an isolated timestamped directory under `datasets/incoming/`, preserves source revision and license metadata, screens records, removes contact patterns and cross-source duplicates, and writes `manifest.json`, reject reports, and duplicate reports. It never promotes records directly into `datasets/curated`; review the manifest and reports first.

For a bounded reproducible run:

```bash
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
