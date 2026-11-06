# Language strategy

PolyGlot Agents is designed for broad multilingual coverage, not a fixed English-first language list. The import and processing tools are not whitelisted to the language entries in `configs/languages.yaml`: any valid ISO 639-1 code is accepted, and ISO 639-3 is used when no alpha-2 code exists. Use the canonical code for a directory. Keep region, script, dialect, and dataset-native language labels in record metadata; for example, OASST's `pt-BR` source tag maps to directory code `pt` while preserving `source_lang_tag: pt-BR`. A file must contain one canonical language only.

The executable resolver is `scripts/language_registry.py`. It treats the YAML catalog as an open profile catalog rather than a whitelist, preserves the source tag, and derives `bcp47`, `script`, and `region`. A valid language without a profile is marked `open_unregistered` and can enter staging with `native_review_required: true`; it is not silently promoted to benchmark-supported status.

## Current tooling coverage

`scripts/import_oasst.py --list-languages` queries the source and prints every language tag and record count the current OASST1 version exposes. `--all-languages` streams that source once and writes each source tag to its own monolingual JSONL file under the corresponding ISO directory. `scripts/lang_id.py` uses fastText lid.176, so automatic detection is not guaranteed for every language on Earth; low-confidence records go to review, and the code preserves declared language rather than silently guessing. An unsupported detector is not a reason to reject a licensed language dataset: a verified source tag may be supplied directly to an importer.

Run an inventory before importing:

```bash
python scripts/import_oasst.py --list-languages
python scripts/import_oasst.py --all-languages --output-root datasets/curated --limit 100
python scripts/language_report.py --input datasets/curated --output reports/language_report.json
python scripts/scaffold_language.py --code sw --source-tag sw
```

The optional `--limit` is a smoke-test/sample control. Remove it to import all qualifying records. The scaffold command creates `raw` and `curated` SFT/tool-use/RLHF directories and a benchmark task card marked as requiring native-speaker authoring; it does not invent benchmark tasks. Review the source license and privacy obligations before distributing the resulting files.

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
3. Keep the exact source tag, script, and dialect in metadata; validate the directory code with `scripts/language_codes.py`.
4. Create `datasets/{raw,curated}/<code>/{sft,tool_use,rlhf}/` only when records are ready.
5. Add a benchmark task file and language-specific tests, with native-speaker review where possible.
6. Calibrate filtering and quality thresholds on an in-language reviewed set. Do not copy an English threshold without evidence.
7. Publish a data card describing gaps, bias risks, collection dates, and known limitations.
