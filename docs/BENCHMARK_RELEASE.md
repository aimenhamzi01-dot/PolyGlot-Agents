# Benchmark release and trust gates

This document defines what PolyGlot Agents can verify automatically and what still requires human review or access-controlled infrastructure. Passing CI is not, by itself, evidence that a benchmark is linguistically valid or suitable for official model claims.

## Current release state

Spanish (`es`) and Simplified Chinese (`zh-Hans`) are adopted as supported runtime development locales. The current public Arabic benchmark is `evaluation/benchmarks/ar_tasks_v0.2.json` (24 development tasks). Each task references a deterministic environment scenario and declares an `expected_outcome`; the validator checks that the declared outcome matches the scenario's machine-readable goal. The runner also records the actual final resolution and explicit transient-failure/recovery markers. Locale-parity runs in Spanish or Simplified Chinese reuse these shared synthetic scenarios for implementation checks only; they do not represent authored or reviewed Spanish/Chinese benchmark sets.

The benchmark is **not yet an official or native-speaker-validated benchmark**: its review status remains `pending_native_speaker_review`, and no protected hidden test set is provisioned. Earlier placeholder test cards were present in public Git history. Their contents are therefore compromised and must never be reused as a secret holdout. This repository does not rewrite its published history.

## Public development-task gates

Before merging a public benchmark change, run:

```bash
python -m pip install -e ".[test]"
python -m pytest -q
python -m scripts.validate_benchmarks
polyglot-run-eval --output /tmp/polyglot-ar-development.json
```

For active customer-service benchmarks, every card must include non-empty `id`, `scenario_id`, `goal`, `success_condition`, `safety_checks`, and a machine-readable `expected_outcome`. The outcome must match the environment goal; task IDs and scenario IDs must be unique within the benchmark. New task wording must not be treated as reviewed merely because its JSON schema passes.

The runner defaults to `development`. Public benchmark files reject records marked `hidden`; CI runs this validator against all benchmark JSON files in the repository.

## Native-speaker and expert review

Human review is a separate gate and is not created or simulated by code. Before describing Arabic task wording as reviewed, maintainers should capture at minimum:

- locale, region/dialect, script, and register being reviewed;
- a stable reviewer code held in an appropriate privacy-protected system;
- review date and rubric version;
- separate judgments for language naturalness, task intent, factual/tool correctness, safety, and cultural fit;
- decision, confidence, and unresolved disagreements;
- independent second review for a predeclared sample, with agreement reported.

Do not add personal reviewer data to public task files. Until review artifacts exist and have been checked, retain a pending review state and label all reports as developmental evidence.

## Protected holdout handling

A real holdout must be newly authored, independent of public task text and training data, and kept in access-controlled storage outside the public repository. Do not reuse the former public placeholder cases: they are visible in Git history. The `.gitignore` rules are an accidental-commit safeguard, not a security boundary.

A protected JSON file must use the same `benchmark_id`, `benchmark_version`, `language`, and `environment` as its public development benchmark. It must contain only task records with `split: "hidden"`; task IDs and scenario IDs must not overlap with the public development set. Validate and evaluate it explicitly:

```bash
python -m scripts.validate_benchmarks \
  --protected-benchmark /secure/maintainer/ar_holdout.json
python evaluation/run_benchmark.py \
  --split hidden \
  --protected-benchmark /secure/maintainer/ar_holdout.json \
  --output /tmp/polyglot-ar-holdout-report.json
```

Use `--split all` only in a controlled maintainer run when both development and protected tasks are intentionally being evaluated together. Never put holdout text, generated agent prompts containing holdout text, or task-level hidden metadata into public reports.

## Reports and model comparisons

Runner report schema version 2 records hashes for the benchmark input, environment/locale bundle, and evaluator/adapter source, plus benchmark review status and per-task outcomes. The comparison tool requires matching protocol fields and hashes, checks that aggregate task counts equal the unique per-task result rows, and reports metrics separately. It does not infer review approval or declare a universal winner.

For comparable model runs, keep the benchmark file, environment, evaluator, split, locale, seed, step budget, and concurrency fixed. Record model/provider identity and revision where available; API model endpoints may change independently of their URL, so source hashes alone do not pin a hosted model. Cost estimates remain provider-price inputs supplied by the user.

## Readiness criteria for an official benchmark claim

Do not label results official until all of the following are true:

1. The task set has documented rights/provenance and passes the public schema and outcome-alignment checks.
2. Native-speaker review is complete for each claimed locale/dialect, with reviewer methodology and limitations documented.
3. The hidden holdout is newly authored, genuinely access-controlled, disjoint from development/training data, and has an auditable administration process.
4. The environment, evaluator, benchmark version, model identity, and run protocol are recorded; comparison reports pass strict compatibility checks.
5. Results, failures, uncertainty/limitations, and language-specific breakdowns are published without hiding safety regressions or overstating coverage.

Items 2 and 3 require people and infrastructure outside this codebase. The current project has implemented software safeguards for reproducibility and accidental leakage prevention, but has not yet passed those external release gates.
