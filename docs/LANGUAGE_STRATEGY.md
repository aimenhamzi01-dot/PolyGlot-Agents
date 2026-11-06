# Language strategy

PolyGlot Agents is designed for broad multilingual coverage, not a fixed English-first language list. Add any language when an available source and a reviewer or validation plan exist. Use ISO 639 language codes for directory names (prefer ISO 639-1 when unambiguous and available; otherwise use the registered ISO 639-3 code). Store script, region, dialect, and source language labels as record metadata rather than inventing directory codes. A file must contain one language only.

## Coverage tiers

Tiers help sequence work; they do not block contributions.

- **Foundation:** Arabic (`ar`) and English (`en`) have starter tooling, benchmarks, and community review.
- **Expansion:** add languages based on licensed data availability, native-speaker review, and measured quality. The candidate list is intentionally open and includes Chinese, Spanish, Hindi, Portuguese, Bengali, Russian, Japanese, Urdu, German, French, Turkish, Korean, Italian, and others.
- **Community:** support low-resource and endangered languages through community-sourced materials with documented rights, orthography/dialect metadata, and locally appropriate evaluation.

## Quality is language-relative

Never compare a language's raw score to another language's score as if the same thresholds had equal meaning. Report sample size, source mix, score distribution, detector confidence, duplicate rate, script/dialect coverage, human-review rate, and benchmark performance by language. Calibrate thresholds using language-specific validation sets and reviewers. Preserve dialects, code-switching, and non-standard orthography where they are valid; do not treat them as noise by default.

## Onboarding checklist

1. Confirm the ISO code and whether script/dialect distinctions are needed.
2. Record source and item-level license; confirm redistribution and any intended commercial use.
3. Create `datasets/{raw,curated}/<code>/{sft,tool_use,rlhf}/` only when records are ready.
4. Add a benchmark task file and language-specific tests, with native-speaker review where possible.
5. Publish a data card describing gaps, bias risks, collection dates, and known limitations.
