#!/usr/bin/env python3
"""Detect language in JSONL using fastText lid.176 and preserve record provenance."""
from __future__ import annotations
import argparse, json, os, urllib.request
from pathlib import Path

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
    labels, probs = model.predict(" ".join(text.split()).replace("\n", " "), k=1)
    label = labels[0].removeprefix("__label__")
    # fastText lid.176 uses ISO 639-1 where available and some ISO 639-3 labels.
    return label, float(probs[0])


def run(input_path: Path, output_path: Path, model_path: Path) -> int:
    model = get_model(model_path)
    count = 0
    with input_path.open(encoding="utf-8") as src, output_path.open("w", encoding="utf-8") as dst:
        for line_no, line in enumerate(src, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
                if not isinstance(row, dict) or not isinstance(row.get("text"), str):
                    raise ValueError("expected JSON object with text string")
                code, confidence = detect(model, row["text"])
                row["detected_lang"] = code
                row["language_confidence"] = round(confidence, 6)
                row.setdefault("lang_code", code)
                dst.write(json.dumps(row, ensure_ascii=False) + "\n")
                count += 1
            except Exception as exc:
                raise ValueError(f"{input_path}:{line_no}: {exc}") from exc
    return count


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    p.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    a = p.parse_args()
    print(f"Wrote {run(a.input, a.output, a.model)} records to {a.output}")

if __name__ == "__main__":
    main()
