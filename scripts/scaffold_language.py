#!/usr/bin/env python3
"""Scaffold dataset folders and an explicitly unfinished benchmark for any ISO 639 language."""
from __future__ import annotations
import argparse, json
from pathlib import Path
try:
    from scripts.language_codes import canonical_iso639
except ModuleNotFoundError:
    from language_codes import canonical_iso639


def scaffold(code: str, root: Path, source_tag: str | None = None) -> list[Path]:
    canonical = canonical_iso639(code)
    if canonical == "und": raise ValueError("Use a registered ISO 639-1 or ISO 639-3 code, not 'und'")
    created=[]
    for layer in ("raw", "curated"):
        for kind in ("sft", "tool_use", "rlhf"):
            folder=root/"datasets"/layer/canonical/kind
            folder.mkdir(parents=True,exist_ok=True)
            keep=folder/".gitkeep"
            if not any(folder.iterdir()) and not keep.exists(): keep.write_text("",encoding="utf-8")
            created.append(folder)
    benchmark=root/"evaluation"/"benchmarks"/f"{canonical}_tasks.json"
    benchmark.parent.mkdir(parents=True,exist_ok=True)
    if not benchmark.exists():
        doc={"benchmark_id":f"polyglot-{canonical}-v1","language":canonical,"source_language_tags":[source_tag or code],"status":"requires_native_speaker_authoring","license":"Apache-2.0","human_review_status":"unreviewed","task_schema":{"required":["id","prompt","expected_behavior","success_condition","source","license","human_review_status"],"privacy":"No real customer or personal data; use synthetic scenarios with clearly declared provenance."},"tasks":[]}
        benchmark.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        created.append(benchmark)
    return created


def main() -> None:
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--code',required=True,help='ISO 639-1 or 639-3 code, e.g. sw or tlh'); p.add_argument('--source-tag',help='Optional dataset-specific BCP-47/source tag'); p.add_argument('--root',type=Path,default=Path('.')); a=p.parse_args()
    paths=scaffold(a.code,a.root,a.source_tag)
    print(f"Scaffolded {canonical_iso639(a.code)}: {len(paths)} paths under {a.root}")

if __name__=='__main__': main()
