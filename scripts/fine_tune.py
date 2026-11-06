#!/usr/bin/env python3
"""Experimental supervised fine-tuning for PolyGlot Agents JSONL records.

The default mode is LoRA: it trains a small adapter and leaves the base model
unchanged. Data must come from an explicit reviewable JSONL path or from the
latest isolated run under datasets/incoming/.
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import random
from pathlib import Path
from typing import Any

DEFAULT_GLOB = "datasets/incoming/*/curated/*/sft/auto_import.jsonl"


def discover_files(pattern: str = DEFAULT_GLOB) -> list[Path]:
    return sorted(Path(path) for path in glob.glob(pattern, recursive=True) if Path(path).is_file())


def read_records(paths: list[Path], include_unreviewed: bool = False, max_samples: int | None = None) -> list[dict]:
    records: list[dict] = []
    seen: set[str] = set()
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for line_no, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"{path}:{line_no}: invalid JSON: {exc.msg}") from exc
                if not isinstance(row, dict) or not isinstance(row.get("text"), str):
                    continue
                if row.get("human_review_status") == "rejected":
                    continue
                if not include_unreviewed and row.get("human_review_status") != "reviewed":
                    continue
                record_id = str(row.get("id") or hashlib.sha256(row["text"].encode("utf-8")).hexdigest())
                if record_id in seen:
                    continue
                seen.add(record_id)
                records.append(row)
                if max_samples and len(records) >= max_samples:
                    return records
    return records


def format_record(row: dict, tokenizer: Any) -> str:
    messages = row.get("messages")
    if isinstance(messages, list) and messages and all(isinstance(item, dict) for item in messages):
        normalized = [
            {"role": str(item.get("role", "user")), "content": str(item.get("content", ""))}
            for item in messages
        ]
        template = getattr(tokenizer, "chat_template", None)
        if template:
            return tokenizer.apply_chat_template(normalized, tokenize=False, add_generation_prompt=False)
    return str(row["text"])


def split_records(records: list[dict], validation_ratio: float, seed: int) -> tuple[list[dict], list[dict]]:
    if not 0 <= validation_ratio < 1:
        raise ValueError("validation ratio must be in [0, 1)")
    shuffled = list(records)
    random.Random(seed).shuffle(shuffled)
    if len(shuffled) < 2 or validation_ratio == 0:
        return shuffled, []
    validation_size = max(1, round(len(shuffled) * validation_ratio))
    validation_size = min(validation_size, len(shuffled) - 1)
    return shuffled[validation_size:], shuffled[:validation_size]


def load_training_stack():
    try:
        import torch
        from datasets import Dataset
        from peft import LoraConfig, TaskType, get_peft_model
        from transformers import (AutoModelForCausalLM, AutoTokenizer, DataCollatorForLanguageModeling,
                                  Trainer, TrainingArguments)
    except ImportError as exc:
        raise SystemExit(
            "Training dependencies are missing. Install with: "
            "pip install -r scripts/requirements-training.txt"
        ) from exc
    return (torch, Dataset, LoraConfig, TaskType, get_peft_model, AutoModelForCausalLM,
            AutoTokenizer, DataCollatorForLanguageModeling, Trainer, TrainingArguments)


def choose_lora_targets(model, requested: str | None) -> list[str]:
    if requested:
        return [item.strip() for item in requested.split(",") if item.strip()]
    suffixes = ("q_proj", "v_proj", "k_proj", "o_proj", "query_key_value", "c_attn")
    found = {name.rsplit(".", 1)[-1] for name, _ in model.named_modules() if name.rsplit(".", 1)[-1] in suffixes}
    targets = [suffix for suffix in suffixes if suffix in found]
    if not targets:
        raise ValueError("Could not infer LoRA target modules; pass --target-modules explicitly")
    return targets


def build_dataset(records: list[dict], tokenizer, max_length: int, Dataset):
    texts = [{"text": format_record(row, tokenizer)} for row in records]
    dataset = Dataset.from_list(texts)

    def tokenize(batch):
        return tokenizer(batch["text"], truncation=True, max_length=max_length)

    return dataset.map(tokenize, batched=True, remove_columns=["text"])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, help="Hugging Face model ID or local model path")
    parser.add_argument("--data", nargs="+", type=Path, help="Reviewed JSONL files; omit to use the latest incoming glob")
    parser.add_argument("--output", type=Path, default=Path("outputs/polyglot-lora"))
    parser.add_argument("--max-samples", type=int)
    parser.add_argument("--max-length", type=int, default=1024)
    parser.add_argument("--validation-ratio", type=float, default=0.1)
    parser.add_argument("--epochs", type=float, default=1.0)
    parser.add_argument("--learning-rate", type=float, default=2e-4)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--gradient-accumulation", type=int, default=8)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--target-modules", help="Comma-separated LoRA target suffixes")
    parser.add_argument("--include-unreviewed", action="store_true")
    parser.add_argument("--full-finetune", action="store_true", help="Train all model weights instead of LoRA")
    parser.add_argument("--dry-run", action="store_true", help="Validate and summarize records without loading the model")
    args = parser.parse_args()
    if args.max_samples is not None and args.max_samples < 1:
        parser.error("--max-samples must be positive")
    if args.max_length < 8 or args.batch_size < 1 or args.gradient_accumulation < 1:
        parser.error("max-length must be >= 8 and batch/gradient values must be positive")

    paths = args.data or discover_files()
    paths = [path for path in paths if path.exists()]
    if not paths:
        raise SystemExit("No JSONL data found. Pass --data or run scripts/auto_import.py first.")
    records = read_records(paths, args.include_unreviewed, args.max_samples)
    if len(records) < 2:
        raise SystemExit("At least two reviewed records are required for a train/validation split.")
    train_records, validation_records = split_records(records, args.validation_ratio, args.seed)
    languages = sorted({str(row.get("lang_code", "und")) for row in records})
    summary = {
        "model": args.model,
        "data_files": [str(path) for path in paths],
        "records": len(records),
        "train_records": len(train_records),
        "validation_records": len(validation_records),
        "languages": languages,
        "max_length": args.max_length,
        "mode": "full_finetune" if args.full_finetune else "lora",
        "seed": args.seed,
    }
    if args.dry_run:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return

    (torch, Dataset, LoraConfig, TaskType, get_peft_model, AutoModelForCausalLM,
     AutoTokenizer, DataCollatorForLanguageModeling, Trainer, TrainingArguments) = load_training_stack()
    random.seed(args.seed)
    tokenizer = AutoTokenizer.from_pretrained(args.model, use_fast=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(args.model)
    if not args.full_finetune:
        targets = choose_lora_targets(model, args.target_modules)
        lora = LoraConfig(task_type=TaskType.CAUSAL_LM, r=8, lora_alpha=16, lora_dropout=0.05,
                          target_modules=targets, bias="none")
        model = get_peft_model(model, lora)
        summary["lora_target_modules"] = targets
        model.print_trainable_parameters()

    train_ds = build_dataset(train_records, tokenizer, args.max_length, Dataset)
    eval_ds = build_dataset(validation_records, tokenizer, args.max_length, Dataset) if validation_records else None
    args.output.mkdir(parents=True, exist_ok=True)
    training_args = TrainingArguments(
        output_dir=str(args.output), num_train_epochs=args.epochs,
        learning_rate=args.learning_rate, per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size, gradient_accumulation_steps=args.gradient_accumulation,
        logging_steps=5, save_strategy="epoch", evaluation_strategy="epoch" if eval_ds else "no",
        report_to="none", seed=args.seed, fp16=torch.cuda.is_available(),
    )
    trainer = Trainer(model=model, args=training_args, train_dataset=train_ds, eval_dataset=eval_ds,
                      tokenizer=tokenizer, data_collator=DataCollatorForLanguageModeling(tokenizer, mlm=False))
    trainer.train()
    trainer.save_model(str(args.output))
    tokenizer.save_pretrained(str(args.output))
    summary["status"] = "completed"
    (args.output / "training_manifest.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
