# PolyGlot Agents

<p align="center">
  <img src="assets/polyglot-agents-mark.png" alt="PolyGlot Agents logo" width="180" />
</p>

<p align="center"><strong>PolyGlot Agents</strong> · Traceable multilingual agent infrastructure</p>

[![CI](https://github.com/aimenhamzi01-dot/PolyGlot-Agents/actions/workflows/ci.yml/badge.svg)](https://github.com/aimenhamzi01-dot/PolyGlot-Agents/actions/workflows/ci.yml)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB.svg)](https://www.python.org/)

**Open infrastructure for traceable multilingual agent data, verifiable environments, and safety-aware evaluation.**

PolyGlot Agents helps teams build and inspect multilingual agent datasets and task environments without hiding the hard parts: provenance, licensing, privacy screening, language quality, tool safety, reproducibility, and measurable evidence.

> **Status:** Research foundation, not a production platform or an official global benchmark. Current locale fixtures are synthetic development assets and require native-speaker validation before external claims are made.

## Why this project exists

Multilingual agent quality is not measured by the number of language folders in a repository. A useful dataset or benchmark must answer five questions:

1. Where did each record come from, and what exact revision produced it?
2. Is the intended use permitted, and can the record be redistributed?
3. Was the record screened for privacy, spam, duplicates, and basic quality?
4. Can an agent complete a verifiable task without taking an unsafe action?
5. Can another researcher reproduce the result from pinned inputs and code?

This repository provides the open-source foundation for answering those questions. It does not claim that public availability is the same as permission to reuse, or that deterministic baselines represent real-world model performance.

## Current status

| Area | Available now | Important boundary |
|---|---|---|
| Data ingestion | Pinned OASST1 and Aya connectors with fail-closed rights metadata, provenance, privacy/contact screening, duplicate reports, and SHA-256 manifests | Rights metadata is evidence for review, not automated legal clearance |
| Imported snapshot | 229,420 accepted records across 72 language codes in the latest local incoming run | Stored under `datasets/incoming`; ignored by Git, not a curated release, and not native-speaker validated |
| Agent environment | Deterministic customer-service environment with explicit tools, policy checks, rewards, event logs, replay protection, and seven available runtime locales: Arabic (`ar`), English (`en`), French (`fr`), Spanish (`es`), Simplified Chinese (`zh-Hans`), Japanese (`ja`), and Russian (`ru`) | Spanish, Chinese, Japanese, and Russian are development locales; benchmark claims still require native-speaker review and independent evaluation data |
| Evaluation | JSON reports, failure taxonomy, latency/throughput metrics, token-cost hooks, release manifests, and regression gates | Official scores still require reviewed tasks and access-controlled holdouts |
| Serving | FastAPI gateway in front of a private vLLM deployment with API-key authentication and streaming support | Production exposure still requires TLS, quotas, WAF/rate limiting, load testing, and operational controls |
| Source audits | Wikimedia and arXiv registered as audit-only sources | Both remain disabled for automated full-text ingestion until item-level rights workflows exist |

The project measures coverage separately from support. An imported language code is not automatically a supported language, and a passing rule-based baseline is not evidence of customer impact.

## Quick start

### 1. Set up a local environment

```bash
git clone https://github.com/aimenhamzi01-dot/PolyGlot-Agents.git
cd PolyGlot-Agents
python3 -m venv .venv
. .venv/bin/activate
make install
```

The package requires Python 3.10 or newer. The test extra installs the core runtime and pytest. The data-pipeline dependencies can be installed with:

```bash
pip install -r scripts/requirements.txt
```

### 2. Run the repository checks

```bash
make test
make check
```

These commands run the test suite, validate benchmark contracts and example records, and compile the Python packages. CI runs the same checks on Python 3.10, 3.11, and 3.12.

### 3. Run a deterministic benchmark

```bash
polyglot-run-eval \
  --benchmark evaluation/benchmarks/ar_tasks_v0.2.json \
  --split development \
  --output /tmp/polyglot-ar-development.json

polyglot-check-regression \
  --report /tmp/polyglot-ar-development.json
```

The bundled rule-based baseline is expected to pass its strict regression gate. This is a health check for the environment and evaluator, not a claim about an external model.

For a compatible model gateway, add `--agent openai-compatible --locale en` (or `ar`, `fr`, `es`, `zh-Hans`, `ja`, or `ru`). Benchmark cards may provide `customer_prompts` keyed by locale; the runner passes the selected customer wording into the environment observation, falling back to its locale fixture when no prompt is authored. The adapter preserves that initial customer message across follow-up turns so an agent can retain the original intent. This makes task wording part of the evaluated input; model quality still needs to be measured against reviewed, independent tasks.

To check a locale pack against the shared synthetic development scenarios, pass a locale independently from the benchmark metadata:

```bash
polyglot-run-eval \
  --benchmark evaluation/benchmarks/ar_tasks_v0.2.json \
  --split development \
  --locale zh-Hans \
  --output /tmp/polyglot-zh-parity.json
polyglot-check-regression --report /tmp/polyglot-zh-parity.json
```

This parity run checks locale integration only. The Spanish, Chinese, Japanese, and Russian task files remain empty, unreviewed templates; passing shared Arabic-derived scenarios is not evidence of reviewed language-specific benchmarks or real-world model quality.

## Training-data ingestion

The approved importer reads source configuration from [`configs/sources.yaml`](configs/sources.yaml). Enabled sources must have a pinned revision, explicit license metadata, redistribution permission, and an accepted rights status before the importer can run.

```bash
python -m scripts.auto_import \
  --output-root datasets/incoming
```

The importer:

- uses the exact revisions declared in configuration;
- normalizes language metadata while preserving source language tags;
- screens records for basic quality and contact patterns;
- removes duplicates using stable content fingerprints;
- writes per-language JSONL files, reject reports, duplicate reports, and a manifest;
- keeps the result in `datasets/incoming/<run-id>/`;
- never promotes records into `datasets/curated` automatically.

The latest local run produced 229,420 accepted records from 246,071 source records across 72 language codes. All 24 languages currently listed in [`configs/languages.yaml`](configs/languages.yaml) were present, alongside 48 additional codes discovered in the sources. The generated `manifest.json` is the source of truth for exact counts and hashes for that run.

Do not commit bulk data, credentials, private review decisions, or raw crawls. Review rights, privacy, language quality, attribution, and deletion requirements before promoting any incoming record to a curated dataset.

### Source policy

OASST1 and Aya are configured as approved research/training sources with pinned revisions and per-record provenance. Their use remains subject to the source terms, applicable law, privacy review, and the project's own review gates.

Wikimedia is registered for audit only because project and item licenses vary, some material may be subject to exceptions, and attribution or ShareAlike obligations may apply. arXiv is also audit-only because each article version can carry a different irrevocable license, and the default non-exclusive license does not grant general downstream reuse. Neither source is enabled for automated full-text ingestion. See [`docs/DATA_LICENSES.md`](docs/DATA_LICENSES.md) and [`configs/sources.yaml`](configs/sources.yaml).

## Evaluation and reporting

Validate public benchmark contracts before running an evaluation:

```bash
python -m scripts.validate_benchmarks
python -m scripts.validate_records --input examples/multilingual.jsonl
```

Render a saved report without rerunning the agent:

```bash
python -m evaluation.report \
  --input /tmp/polyglot-ar-development.json \
  --markdown-output /tmp/polyglot-ar-development.md \
  --html-output /tmp/polyglot-ar-development.html
```

Create a release manifest that records hashes for the benchmark, evaluator, environment, configuration, and optional report:

```bash
python -m evaluation.release_manifest \
  --benchmark evaluation/benchmarks/ar_tasks_v0.2.json \
  --report /tmp/polyglot-ar-development.json \
  --output /tmp/polyglot-ar-development-manifest.json
```

Generate a descriptive coverage dashboard:

```bash
python -m evaluation.coverage_dashboard \
  --coverage evaluation/language_coverage_report.json \
  --benchmark-dir evaluation/benchmarks \
  --markdown-output /tmp/polyglot-coverage.md \
  --html-output /tmp/polyglot-coverage.html
```

The evaluation pipeline records task outcomes, expected-versus-actual results, safety violations, tool calls, truncation, rewards, latency, throughput, failure reasons, and scenario/locale breakdowns. It does not turn synthetic development cards into an official benchmark. Hidden tests must be authored independently and stored outside the public repository in access-controlled storage.

## Environment and policy model

The customer-service environment separates model proposals from authorization and state mutation:

```text
agent proposes an action
        -> policy engine checks identity, state, intent, approval, and idempotency
        -> tool gateway accepts or rejects
        -> event log records the decision
        -> verifier calculates the outcome and reward
```

The policy engine is intentionally deterministic. It covers verified orders, refund eligibility, customer intent, approval matching, replay protection, and evidence-grounded final claims. It is a research policy and must not be treated as a production authorization service.

## Production reference deployment

The repository includes a reference deployment for a trained adapter:

```text
client -> FastAPI gateway:8080 -> private vLLM:8000 -> base model + static LoRA adapter
```

See [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) and [`docker-compose.production.yml`](docker-compose.production.yml):

```bash
cp .env.production.example .env.production
# Set the exact base model, adapter path, reviewed VLLM_IMAGE, and long random keys.
docker compose --env-file .env.production \
  -f docker-compose.production.yml config

docker compose --env-file .env.production \
  -f docker-compose.production.yml up -d --build
```

Before public exposure, add TLS, a WAF or API gateway, per-client authentication and quotas, rate limiting, log redaction, egress restrictions, model and adapter provenance, load tests, benchmark regressions, and a rollback drill. Never expose vLLM directly or provide model/tool credentials to an untrusted model.

## Repository layout

```text
configs/
  environment.yaml       # validated environment behavior
  languages.yaml         # language registry seed and review defaults
  pipeline.yaml          # pipeline configuration
  sources.yaml           # enabled sources and rights metadata

datasets/
  raw/                   # ignored; never commit bulk source data
  curated/               # reviewed release data
  incoming/              # ignored import runs awaiting review

environments/
  customer_service_agent/ # state machine, tools, policy, locales, verifier

evaluation/
  benchmarks/            # public development task cards
  run_benchmark.py       # reproducible evaluation runner
  report.py              # Markdown/HTML report renderer
  release_manifest.py    # hash-bound release metadata

pipelines/               # annotation, filtering, quality, deduplication
scripts/                 # importers, validators, rights and lifecycle tools
serving/                 # FastAPI gateway for private vLLM

tests/                   # offline unit and regression tests
docs/                    # governance, licenses, deployment and strategy
```

Language folders use canonical ISO 639 codes. Region, script, dialect, and source-native tags remain in record metadata rather than being discarded during normalization.

## Data governance and security

Every accepted record should preserve its source, source URL, source revision, license, license URL, retrieval time, language metadata, quality basis, and review status. The repository does not treat a dataset card or download URL as proof that every item may be redistributed.

Do not commit raw web crawls, credentials, confidential material, personal data, private reviewer identities, protected benchmarks, model weights, or unreviewed source exports. Use quarantine and deletion manifests when a rights, privacy, or safety issue is reported. See [`docs/DATA_LICENSES.md`](docs/DATA_LICENSES.md) for the removal workflow.

For security reports, do not publish exploit details or sensitive records in a public issue. Contact the maintainers privately with the affected component, reproduction steps that do not expose data, and the minimum evidence needed to investigate.

## Contributing

Start with an issue for substantial changes so maintainers can review scope, rights, privacy, language coverage, and benchmark contamination risks. For code changes:

```bash
make install
make test
make check
git diff --check
```

For data contributions, include the source identifier, stable source URL or ID, exact license, retrieval date, allowed use, language code, quality basis, human-review status, and deletion or quarantine path. Never submit material simply because it is publicly reachable.

Read [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md) before opening a pull request. Dataset terms remain governed by their upstream licenses; the code is licensed under Apache-2.0.

## Roadmap

The near-term priorities are deliberately narrow:

1. Obtain native-speaker review and calibration for the public Arabic, English, and French development cards.
2. Author a fresh protected holdout outside the public Git history.
3. Expand multilingual red-team and tool-failure coverage.
4. Add item-level rights workflows for any new source, including Wikimedia or arXiv.
5. Connect reviewed production failure patterns to reproducible regression cases.
6. Publish coverage and quality reports that distinguish imported records from supported languages.

Future work may add dialect-aware tasks, permissioned workflow traces, model comparisons, annotation operations, and additional modalities. Expansion should follow evidence, rights, and review capacity rather than directory count.

## License

The software in this repository is licensed under the [Apache License 2.0](LICENSE). Datasets and source-derived records retain their upstream licenses and obligations. Placing a record in this repository does not relicense it under Apache-2.0.

For the detailed source, review, deployment, and benchmark policies, start with:

- [`docs/DATA_LICENSES.md`](docs/DATA_LICENSES.md)
- [`docs/BENCHMARK_RELEASE.md`](docs/BENCHMARK_RELEASE.md)
- [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md)
- [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md)
- [`docs/LOCALE_ARCHITECTURE.md`](docs/LOCALE_ARCHITECTURE.md)
