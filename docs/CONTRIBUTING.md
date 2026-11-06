# Contributing

Thanks for helping build useful, auditable multilingual agent data. Open an issue before large changes so maintainers can review scope, license compatibility, privacy risks, and whether the contribution belongs in code, a manifest, or a separately hosted dataset.

## Data contributions

Do not upload raw web crawls, personal data, credentials, confidential material, or content whose source/license is unknown. For every record, retain source, stable source URL or ID, exact license, retrieval date, language code, quality score, and human-review status. Keep one language per file. Large source data should be acquired outside Git and referenced by a small manifest; never commit bulk data.

Contributors must confirm they have authority to submit the material under its recorded terms. Do not claim that publicly reachable content is automatically reusable. Follow attribution and ShareAlike obligations, and flag non-commercial, no-derivatives, or unclear terms rather than silently mixing them into a commercial-compatible corpus.

## Review queues

Create a deterministic sample without embedding reviewer identity in the queue:

```bash
python -m scripts.review_queue \
  --mode create --input records.jsonl --output review-queue.jsonl \
  --sample-size 50 --seed 13 --language ar --rubric-version v1
```

After review, apply a separate decisions file containing `review_id`, `record_id`,
`decision`, a protected `reviewer_ref`, `reviewed_at`, and the rubric version:

```bash
python -m scripts.review_queue \
  --mode apply --input records.jsonl --decisions review-decisions.jsonl \
  --output reviewed.jsonl --rubric-version v1
```

Valid decisions are `reviewed`, `rejected`, and `needs_adjudication`. Adjudication
does not promote a record; reviewer references should be pseudonymous pointers to a
protected reviewer system, not personal data committed to the repository.

## Code and environments

Use Python 3.10+, type hints where useful, clear CLI help, deterministic behavior, and tests that run offline. Do not introduce network calls in unit tests. Environment rewards must be based on observable, verifiable task completion, not stylistic preference alone. Document safety boundaries and avoid asking agents to collect unnecessary customer personal information.

## Pull requests

A pull request should explain the motivation, expected behavior, test command and output, data source/license changes, and language-specific validation. Run the same checks used by CI:

```bash
make install
make test
make check
```

Keep changes focused. Include a changelog note for schema changes, and obtain native-speaker review for benchmark text where possible. By submitting code, you agree that your contribution is offered under Apache-2.0 unless the pull request states a compatible alternative accepted by maintainers. Dataset contributions remain under their declared upstream license.
