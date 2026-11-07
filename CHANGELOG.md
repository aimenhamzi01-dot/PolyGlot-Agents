# Changelog

All notable project changes are documented here. Benchmark results remain subject to the
review status and holdout rules declared in each release manifest.

## [Unreleased]

- Adopted Spanish (`es`) and Simplified Chinese (`zh-Hans`) as supported runtime development locales; benchmark review and release status remain separate gates.
- Added a Simplified Chinese (`zh-Hans`) locale pack, CJK action/observation support, Chinese prompts and baseline responses, end-to-end locale tests, and a CI parity regression on shared synthetic scenarios.
- Added a Spanish customer-service locale pack, localized model instructions and baseline responses, plus status/refund/follow-up/escalation tests and a CI locale-parity regression using shared synthetic scenarios.
- Localized OpenAI-compatible agent instructions and tool descriptions for Arabic, English, French, Spanish, and Simplified Chinese; preserve the original customer intent across follow-up turns.
- Added the `polyglot-run-eval` console command and a CI smoke check for the installed CLI.
- Added the PolyGlot Agents brand mark in standard and dark-background transparent PNG variants,
  and embedded the primary mark in the README.
- Rebuilt the README as a company-grade project entry point with status boundaries, quick start,
  data ingestion, evaluation, deployment, governance, security, contribution, and roadmap sections.
- Updated README with the current 72-language import snapshot, reproducible quick-start commands,
  and audit-only boundaries for Wikimedia and arXiv.
- Registered Wikimedia and arXiv as audit-only sources with explicit item-level rights blockers;
  neither source is enabled for automated ingestion.
- Added a Makefile with one-command install, test, validation, and benchmark targets.
- Hardened the production Compose file by requiring an explicitly reviewed vLLM image and
  waiting for the upstream health check before starting the gateway.
- Added auditable review queues with reproducible sampling and decision application.
- Added rights lifecycle manifests and non-destructive quarantine tombstones.
- Added validated environment configuration loaded from `configs/environment.yaml`.
- Added multilingual red-team regressions and English/French synthetic development cards.
- Added Markdown/HTML evaluation reports and CI regression gates.

## [0.1.0] — Development foundation

- Initial multilingual data pipeline, customer-service environment, benchmark runner,
  provenance checks, and deterministic Arabic development benchmark.
