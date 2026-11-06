# Processing pipeline

The executable CLI implementations are in `scripts/` so they can be invoked directly from a checkout. Each corresponding area below documents the step; scripts are intentionally separated into stages to make intermediate artifacts inspectable.

- `filtering/`: rejects malformed/short records and redacts common email/phone patterns; every rejection has a reason.
- `deduplication/`: stable exact duplicate detection with Unicode normalization and language-scoped hashes.
- `quality_scoring/`: transparent heuristic score plus component breakdown; calibrate per language and never interpret as factuality.
- `annotation/`: reproducible human-review sample selection; review status stays explicit.

Run the CLI tools in order. Keep raw inputs outside version control and retain source manifests. A successful filter is not a legal clearance or safety guarantee.
