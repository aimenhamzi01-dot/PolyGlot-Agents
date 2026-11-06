#!/usr/bin/env python3
"""Import reviewed human-written SFT pairs from OpenAssistant/OASST1 for one source language."""
from __future__ import annotations
import argparse, json, re
from datetime import datetime, timezone
from pathlib import Path

SOURCE = "OpenAssistant/oasst1"
DATASET_URL = "https://huggingface.co/datasets/OpenAssistant/oasst1"
LICENSE_URL = "https://huggingface.co/datasets/OpenAssistant/oasst1/blob/main/LICENSE"
CONTACT = re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b|(?:\+?\d[\d ()-]{7,}\d)")


def label(row: dict, key: str):
    labels = row.get("labels") or {}
    try:
        names = list(labels.get("name", [])); values = list(labels.get("value", []))
        return float(values[names.index(key)])
    except (ValueError, TypeError, IndexError):
        return None


def accepted(row: dict) -> bool:
    return (row.get("review_result") is True and not row.get("deleted", False)
            and not row.get("synthetic", False) and label(row, "pii") == 0.0
            and label(row, "spam") == 0.0 and bool(str(row.get("text", "")).strip())
            and not CONTACT.search(str(row.get("text", ""))))


def import_pairs(source_lang: str, output_lang: str, output: Path, limit: int | None = None) -> int:
    try:
        from datasets import load_dataset
    except ImportError as exc:
        raise SystemExit("Install dependencies: pip install -r scripts/requirements.txt") from exc
    messages = {}
    print(f"Streaming {SOURCE} train split for source language {source_lang!r}...")
    for row in load_dataset(SOURCE, split="train", streaming=True):
        if row.get("lang") == source_lang and row.get("role") in ("prompter", "assistant"):
            messages[row["message_id"]] = dict(row)
    pairs = []
    for answer in messages.values():
        if answer.get("role") != "assistant" or not accepted(answer) or not answer.get("parent_id"):
            continue
        prompt = messages.get(answer["parent_id"])
        if not prompt or prompt.get("role") != "prompter" or not accepted(prompt):
            continue
        prompt_text, answer_text = str(prompt["text"]).strip(), str(answer["text"]).strip()
        rating = label(answer, "quality")
        if rating is None:
            continue
        record = {
            "id": answer["message_id"], "text": f"User: {prompt_text}\nAssistant: {answer_text}",
            "messages": [{"role": "user", "content": prompt_text}, {"role": "assistant", "content": answer_text}],
            "lang_code": output_lang, "source_lang_tag": source_lang,
            "source": SOURCE, "source_url": DATASET_URL,
            "source_record_ids": [prompt["message_id"], answer["message_id"]],
            "license": "Apache-2.0", "license_url": LICENSE_URL,
            "quality_score": rating, "quality_basis": "upstream human quality rating; calibrate per language",
            "human_review_status": "reviewed",
            "human_review_basis": "upstream review_result=true; pii=0 and spam=0 on both messages; contact-pattern screen passed",
            "content_type": "sft",
            "provenance": {"source_split": "train", "retrieved_at": datetime.now(timezone.utc).isoformat(), "synthetic": False}
        }
        pairs.append(record)
    # Stable ordering and no duplicate assistant messages.
    pairs.sort(key=lambda x: x["id"])
    if limit is not None: pairs = pairs[:limit]
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as f:
        for row in pairs: f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return len(pairs)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-lang", required=True, help="OASST source tag, e.g. ar, en, pt-BR")
    p.add_argument("--lang-code", required=True, help="ISO 639 output folder code, e.g. ar, en, pt")
    p.add_argument("--output", required=True, type=Path)
    p.add_argument("--limit", type=int, help="Optional maximum records; default imports all qualifying pairs")
    a = p.parse_args()
    if a.limit is not None and a.limit < 1: p.error("--limit must be positive")
    n = import_pairs(a.source_lang, a.lang_code, a.output, a.limit)
    print(f"imported={n} output={a.output}; confirm license/rights before downstream redistribution")

if __name__ == "__main__": main()
