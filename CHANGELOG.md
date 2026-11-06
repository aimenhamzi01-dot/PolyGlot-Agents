# Changelog

All notable project changes are documented here. Benchmark results remain subject to the
review status and holdout rules declared in each release manifest.

## [Unreleased]

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
