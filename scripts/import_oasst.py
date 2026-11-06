#!/usr/bin/env python3
"""Import reviewed OASST1 SFT pairs by language or in one multilingual pass."""
from __future__ import annotations
import argparse, json, re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
try:
    from scripts.language_codes import canonical_iso639
except ModuleNotFoundError:
    from language_codes import canonical_iso639

SOURCE = "OpenAssistant/oasst1"
DATASET_URL = "https://huggingface.co/datasets/OpenAssistant/oasst1"
LICENSE_URL = "https://huggingface.co/datasets/OpenAssistant/oasst1/blob/main/LICENSE"
CONTACT = re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b|(?:\+?\d[\d ()-]{7,}\d)")


def label(row: dict, key: str):
    labels = row.get("labels") or {}
    try:
        names = list(labels.get("name", [])); values = list(labels.get("value", []))
        return float(values[names.index(key)])
    except (ValueError, TypeError, IndexError): return None


def accepted(row: dict) -> bool:
    return (row.get("review_result") is True and not row.get("deleted", False)
            and not row.get("synthetic", False) and label(row, "pii") == 0.0
            and label(row, "spam") == 0.0 and bool(str(row.get("text", "")).strip())
            and not CONTACT.search(str(row.get("text", ""))))


def make_pair(prompt: dict, answer: dict, lang_code: str, source_tag: str) -> dict | None:
    if not accepted(prompt) or not accepted(answer): return None
    rating = label(answer, "quality")
    if rating is None: return None
    prompt_text, answer_text = str(prompt["text"]).strip(), str(answer["text"]).strip()
    return {
        "id": answer["message_id"], "text": f"User: {prompt_text}\nAssistant: {answer_text}",
        "messages": [{"role": "user", "content": prompt_text}, {"role": "assistant", "content": answer_text}],
        "lang_code": lang_code, "source_lang_tag": source_tag,
        "source": SOURCE, "source_url": DATASET_URL,
        "source_record_ids": [prompt["message_id"], answer["message_id"]],
        "license": "Apache-2.0", "license_url": LICENSE_URL,
        "quality_score": rating, "quality_basis": "upstream human quality rating; calibrate per language",
        "human_review_status": "reviewed",
        "human_review_basis": "upstream review_result=true; pii=0 and spam=0 on both messages; contact-pattern screen passed",
        "content_type": "sft",
        "provenance": {"source_split": "train", "retrieved_at": datetime.now(timezone.utc).isoformat(), "synthetic": False}
    }


def load_source():
    try:
        from datasets import load_dataset
    except ImportError as exc:
        raise SystemExit("Install dependencies: pip install -r scripts/requirements.txt") from exc
    return load_dataset(SOURCE, split="train", streaming=True)


def collect_messages(source_tag: str | None = None) -> dict[str, dict]:
    messages = {}
    for row in load_source():
        tag = row.get("lang")
        if (source_tag is None or tag == source_tag) and row.get("role") in ("prompter", "assistant"):
            messages[row["message_id"]] = dict(row)
    return messages


def make_records(messages: dict[str, dict], source_tag: str, output_code: str | None = None) -> list[dict]:
    lang_code = canonical_iso639(output_code or source_tag)
    records = []
    for answer in messages.values():
        if answer.get("role") != "assistant" or not answer.get("parent_id"): continue
        prompt = messages.get(answer["parent_id"])
        if not prompt or prompt.get("role") != "prompter": continue
        record = make_pair(prompt, answer, lang_code, source_tag)
        if record: records.append(record)
    records.sort(key=lambda item: item["id"])
    return records


def select_records(records: list[dict], limit: int | None = None) -> list[dict]:
    if limit is None: return records
    # Prefer upstream human-rated responses while keeping a stable, reproducible sample.
    ranked = sorted(records, key=lambda r: (float(r["quality_score"]), len(r["text"]), r["id"]), reverse=True)
    return sorted(ranked[:limit], key=lambda r: r["id"])


def write_records(records: list[dict], path: Path, limit: int | None = None) -> int:
    selected = select_records(records, limit)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for record in selected: f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return len(selected)


def list_languages() -> Counter:
    counts = Counter()
    for row in load_source():
        if row.get("lang"): counts[row["lang"]] += 1
    return counts


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    modes = p.add_mutually_exclusive_group(required=True)
    modes.add_argument("--source-lang", help="Exact source tag, e.g. ar, pt-BR, uk-UA")
    modes.add_argument("--all-languages", action="store_true", help="One pass; write each source language to its own ISO-code file")
    modes.add_argument("--list-languages", action="store_true", help="List source language tags and message counts")
    p.add_argument("--lang-code", help="Optional ISO output code override for a single source language")
    p.add_argument("--output", type=Path, help="Single-language output JSONL")
    p.add_argument("--output-root", type=Path, help="Root folder for --all-languages output")
    p.add_argument("--limit", type=int, help="Optional maximum SFT pairs per output language; picks top human-rated sample")
    a = p.parse_args()
    if a.limit is not None and a.limit < 1: p.error("--limit must be positive")
    if a.list_languages:
        for tag, count in sorted(list_languages().items()): print(f"{tag}\t{canonical_iso639(tag)}\t{count}")
        return
    if a.all_languages:
        if not a.output_root: p.error("--all-languages requires --output-root")
        messages_by_tag: dict[str, dict[str, dict]] = defaultdict(dict)
        for row in load_source():
            if row.get("lang") and row.get("role") in ("prompter", "assistant"):
                messages_by_tag[row["lang"]][row["message_id"]] = dict(row)
        totals = Counter()
        for tag, messages in sorted(messages_by_tag.items()):
            records = make_records(messages, tag)
            code = canonical_iso639(tag)
            if not records:
                print(f"{tag}\t{code}\t0\tno records passed review/privacy filters")
                continue
            suffix = "_sample" if a.limit is not None else ""
            output = a.output_root / code / "sft" / f"oasst1_{tag.replace('-', '_')}{suffix}.jsonl"
            count = write_records(records, output, a.limit)
            totals[code] += count
            print(f"{tag}\t{code}\t{count}\t{output}")
        print(f"Wrote {sum(totals.values())} reviewed pairs across {len(messages_by_tag)} source tags under {a.output_root}")
        return
    if not a.output: p.error("single-language import requires --output")
    code = canonical_iso639(a.lang_code or a.source_lang)
    messages = collect_messages(a.source_lang)
    records = make_records(messages, a.source_lang, code)
    count = write_records(records, a.output, a.limit)
    print(f"imported={count} source_tag={a.source_lang} lang_code={code} output={a.output}; verify current terms before reuse")

if __name__ == "__main__": main()
