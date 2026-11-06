#!/usr/bin/env python3
"""Detect language in JSONL with fastText and route uncertain/disagreeing rows for review."""
from __future__ import annotations
import argparse, json, urllib.request
from pathlib import Path
try:
    from scripts.language_codes import canonical_iso639
except ModuleNotFoundError:
    from language_codes import canonical_iso639

MODEL_URL = "https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.ftz"
DEFAULT_MODEL = Path.home() / ".cache" / "polyglot-agents" / "lid.176.ftz"


def get_model(path: Path):
    try:
        import fasttext
    except ImportError as exc:
        raise SystemExit("Install requirements first: pip install -r scripts/requirements.txt") from exc
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        print(f"Downloading official fastText language model to {path}")
        urllib.request.urlretrieve(MODEL_URL, path)
    return fasttext.load_model(str(path))


def detect(model, text: str) -> tuple[str, float]:
    cleaned = " ".join(text.split()).replace("\n", " ")
    labels, probs = model.predict(cleaned, k=1)
    source_label = labels[0].removeprefix("__label__")
    try:
        code = canonical_iso639(source_label)
    except ValueError:
        code = "und"
    return code, float(probs[0])


def run(input_path: Path, output_path: Path, model_path: Path, min_confidence: float = 0.55,
        auto_accept_unlabelled: bool = False) -> dict[str, int]:
    model = get_model(model_path)
    labels = model.get_labels() if hasattr(model, "get_labels") else None
    detector_coverage = set()
    if labels:
        for label in labels:
            try: detector_coverage.add(canonical_iso639(label.removeprefix("__label__")))
            except ValueError: continue
    else:
        detector_coverage = None
    counts = {"written": 0, "needs_review": 0, "language_conflict": 0}
    with input_path.open(encoding="utf-8") as src, output_path.open("w", encoding="utf-8") as dst:
        for line_no, line in enumerate(src, 1):
            if not line.strip(): continue
            try:
                row = json.loads(line)
                if not isinstance(row, dict) or not isinstance(row.get("text"), str):
                    raise ValueError("expected JSON object with text string")
                code, confidence = detect(model, row["text"])
                row["detected_lang_code"] = code
                row["language_confidence"] = round(confidence, 6)
                declared = row.get("lang_code")
                declared_code = canonical_iso639(declared) if declared else None
                row["declared_lang_code"] = declared_code
                if declared and str(declared).lower() != str(declared_code).lower():
                    row.setdefault("source_lang_tag", declared)
                declared_outside_detector = bool(declared_code and detector_coverage is not None and declared_code not in detector_coverage)
                row["detector_covers_declared_language"] = not declared_outside_detector if declared_code else None
                if declared_outside_detector:
                    # A verified upstream tag is more informative than a guess from a finite model.
                    row["language_conflict"] = False
                    row["routing_status"] = "source_tag_only"
                    row["lang_code"] = declared_code
                elif declared_code and code != "und" and declared_code != code and confidence >= min_confidence:
                    row["language_conflict"] = True
                    row["routing_status"] = "needs_review"
                    counts["language_conflict"] += 1
                elif confidence < min_confidence or code == "und":
                    row["language_conflict"] = False
                    row["routing_status"] = "needs_review"
                    row["lang_code"] = declared_code or "und"
                elif declared_code:
                    row["language_conflict"] = False
                    row["routing_status"] = "accepted"
                    row["lang_code"] = declared_code
                elif auto_accept_unlabelled and confidence >= min_confidence and code != "und":
                    row["language_conflict"] = False
                    row["routing_status"] = "accepted"
                    row["lang_code"] = code
                else:
                    row["language_conflict"] = False
                    row["routing_status"] = "needs_review"
                    row["lang_code"] = code if code != "und" else "und"
                if row["routing_status"] == "needs_review":
                    counts["needs_review"] += 1
                # Preserve any previous status; this field describes review need, not approval.
                row.setdefault("human_review_status", "unreviewed")
                dst.write(json.dumps(row, ensure_ascii=False) + "\n")
                counts["written"] += 1
            except Exception as exc:
                raise ValueError(f"{input_path}:{line_no}: {exc}") from exc
    return counts


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    p.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    p.add_argument("--min-confidence", type=float, default=0.55)
    p.add_argument("--auto-accept-unlabelled", action="store_true", help="Accept high-confidence model predictions when no source language tag exists; unsafe for possible out-of-coverage languages")
    a = p.parse_args()
    if not 0 <= a.min_confidence <= 1: p.error("--min-confidence must be between 0 and 1")
    print(run(a.input, a.output, a.model, a.min_confidence, a.auto_accept_unlabelled))

if __name__ == "__main__": main()
