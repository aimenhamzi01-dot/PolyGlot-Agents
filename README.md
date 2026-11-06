# PolyGlot Agents

**Open, multilingual data and verifiable environments for AI agents.** PolyGlot Agents is a community project for assembling traceable, quality-scored language data and practical agent tasks across languages. The code is Apache-2.0; datasets retain the license of their source and are never relicensed merely by being placed in this repository.

> **Data reality check:** “publicly accessible” does not mean “free to redistribute.” Every record must retain source, source license, quality score, and human-review status. The repository contains no bulk raw crawls. Import only content whose source terms and item-level license permit the intended use. See [Data licenses](docs/DATA_LICENSES.md).

## Project goals

- Make multilingual agent data discoverable and auditable, rather than treating English as the default.
- Keep language-specific quality measurements and language codes with every record.
- Provide reproducible filtering, deduplication, quality scoring, and annotation workflows.
- Evaluate agents in environments with explicit actions, observations, and verifiable rewards.
- Separate permissively licensed open code from source-governed datasets and any future separately licensed commercial collections.

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
python -m unittest discover -s tests -v
```

`lang_id.py` uses fastText's language-identification model and normalizes predictions to ISO 639-1 when available, otherwise ISO 639-3. It downloads the official model to a local cache on first run; alternatively, pass `--model /path/to/lid.176.ftz`. Low-confidence results and declared/detected conflicts are marked `needs_review`; the input language tag is preserved. Unlabelled input is routed to review by default; `--auto-accept-unlabelled` is an opt-in for workflows that accept the finite detector's risk. fastText lid.176 has finite coverage and is not a universal language oracle. If a trusted source tag is outside detector coverage, the tag is retained instead of replacing it with a guess. Licensed data for languages it does not confidently detect can still be imported using a verified source tag.

### Customer-service environment

The Arabic Gymnasium environment is a fully executable benchmark fixture with deterministic state transitions and rule-based reward verification. Scenarios are project-authored and are not real customer records. Run it with:

```bash
python -m environments.customer_service_agent.demo
```

Arabic task definitions are in `evaluation/benchmarks/ar_tasks.json`. English task parity and native-speaker-reviewed benchmark tasks for the additional data languages remain planned; a data sample alone is not a validated evaluation benchmark. `evaluation/language_coverage_report.json` is a point-in-time report for the bundled samples.

### Importing real source data

`scripts/import_oasst.py --list-languages` lists the current OASST1 source tags. Use `--source-lang` for one source tag, or `--all-languages --output-root datasets/curated` to stream the source once and write separate monolingual files. Canonical ISO codes name folders; tags such as `pt-BR` remain attached to their records. The bundled snapshot contains 1,661 human-reviewed SFT pairs across 23 languages from the tags that passed its filters; each is capped at 100 records, and smaller counts reflect the source's available records, not synthetic padding. The importer excludes synthetic/deleted messages and records without zero PII/spam flags, checks common contact patterns, and records source IDs and license metadata. `--limit` is for tests or samples only. `scripts/language_report.py` reports sample counts, score distributions, human review, duplicates, source mix, and review routing separately per language. Use `scripts/scaffold_language.py --code <ISO-code>` to create all dataset-stage folders and a benchmark card marked as requiring native-speaker authorship; it deliberately does not fabricate evaluation tasks. Other sources must be acquired under their own terms and normalized with full provenance. Do not infer a license from a hosting platform or crawl alone.

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
