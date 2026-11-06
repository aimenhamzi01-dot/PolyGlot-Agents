# Data licenses and provenance

This project is not a blanket license for collected data. Code is Apache-2.0. Each dataset item keeps its upstream license and attribution requirements. Verify a source's current terms before each acquisition and distribution; a repository card, crawl, or download URL alone is not proof of permission.

## Source guidance

| Source | What can be used | License / conditions to record | Important caveat |
|---|---|---|---|
| OpenAssistant OASST1 | Human-generated conversation messages and message trees, after record-level review/PII screening | Dataset card states Apache-2.0; preserve upstream IDs and exact dataset revision | The license label is not a substitute for privacy screening or applicable law. The project importer selects reviewed, non-deleted, non-synthetic entries with zero upstream PII/spam labels. |
| Wikimedia dumps | Audit only by default. Text may be considered only after source-page/license metadata is retained and applicable exceptions are screened | Often GFDL and/or CC BY-SA 4.0; Wikidata structured data may be CC0; check per project and item | Wikimedia's official dump guidance notes mixed licensing, fair-use exceptions, and possible unnoticed infringements. The source remains disabled for automated ingestion until item-level rights handling exists. |
| arXiv | Audit metadata only by default. Full text may be considered only when the specific article version's license permits the intended redistribution/adaptation | Store the exact version-level license identifier and URL | arXiv states that each version can have a different irrevocable license and that most works use a non-exclusive license that does not grant general reuse. The source remains disabled for automated full-text ingestion. |
| FineWeb-2 | A selected language/script subset may be consumed subject to dataset terms and the underlying source conditions | ODC-By 1.0 dataset license; also subject to Common Crawl terms | This is a web-derived corpus, not a blanket clearance of underlying page content. Assess downstream rights, privacy and risks. Avoid mirroring the multi-terabyte corpus in this repository. |
| Self-authored / contributed data | Include only after the contributor confirms they have rights and provides a clear license grant | Record contributor, date, license, and consent/rights evidence | Never submit personal, confidential, or sensitive data without a documented lawful basis and explicit review. |

The table is a starting point, not legal advice. The project does not claim automated legal clearance. It now has a fail-closed metadata gate in `scripts/rights_engine.py`: enabled sources must declare a reviewed rights status, license, license URL, allowed uses, and explicit redistribution permission before `scripts/auto_import.py` runs. This gate checks evidence and configuration; it does not replace legal review or source-specific analysis. `CC-BY-4.0`, `CC-BY-SA-4.0`, `CC0-1.0`, and `ODC-By-1.0` may permit reuse under conditions; attribution, ShareAlike, database rights, privacy rules, and source terms still matter. Do not pool incompatible items under a single dataset license. Keep exact source and license metadata on every record. Wikimedia and arXiv are currently registered as `audit_only` sources with `enabled: false`; their metadata documents official source guidance, but the rights gate must reject them until an item-level importer and evidence workflow are implemented.

The bundled OASST1 snapshot is a capped sample from the source tags that produced records after upstream review, deletion, synthetic-content, PII/spam, and contact-pattern checks. It does not represent worldwide language coverage. Each record keeps its source IDs, OASST1 dataset URL, Apache-2.0 identifier, human quality rating, and review basis. The language coverage report is descriptive of this repository snapshot and should be regenerated after data changes.

## Required record fields

`source`, `source_url`, `license`, `license_url` (when available), `retrieved_at`, `lang_code`, `quality_score`, and `human_review_status` are mandatory. Preserve upstream IDs and attribution statements. Never replace an unknown license with `CC0` or the code license. Exclude records whose reuse status cannot be determined from the intended output.

## Removal and incident process

For rights, privacy, or safety reports, open a GitHub issue without reposting the disputed content. Maintainers should quarantine the affected source IDs, stop future exports, document the decision, and remove or replace affected records. Keep a contact path in repository settings. Do not publish identifying data in the issue.

The repository includes a non-destructive lifecycle tool for this process:

```bash
python -m scripts.rights_lifecycle \
  --mode manifest --input datasets/incoming/run-id \
  --output /tmp/provenance-manifest.json

python -m scripts.rights_lifecycle \
  --mode quarantine --input datasets/incoming/run-id \
  --output /tmp/quarantine-run \
  --record-id source-record-123 \
  --reason rights_request
```

`manifest` records each record ID, source, source URL, file, line, and content digest.
`quarantine` writes a filtered copy and `deletion_manifest.jsonl` tombstones; it never
mutates the input directory. Use pseudonymous or source-system references and retain
the decision evidence in protected maintainer storage.

## References

- [Wikimedia dump license information](https://dumps.wikimedia.org/legal.html)
- [OpenAssistant OASST1 dataset card](https://huggingface.co/datasets/OpenAssistant/oasst1)
- [arXiv license information](https://info.arxiv.org/help/license/index.html)
- [FineWeb-2 dataset card](https://huggingface.co/datasets/HuggingFaceFW/fineweb-2)
- [Common Crawl Terms of Use](https://commoncrawl.org/terms-of-use)
- [ODC-By 1.0](https://opendatacommons.org/licenses/by/1-0/)
