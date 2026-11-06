#!/usr/bin/env python3
"""Summarize corpus quality independently for each language from JSONL files."""
from __future__ import annotations
import argparse, hashlib, json, statistics
from collections import Counter
from pathlib import Path
try:
    from scripts.language_codes import canonical_iso639
except ModuleNotFoundError:
    from language_codes import canonical_iso639


def summarize(paths: list[Path]) -> dict:
    groups: dict[str, dict] = {}
    for path in paths:
        with path.open(encoding="utf-8") as source:
            for line_no, line in enumerate(source, 1):
                if not line.strip(): continue
                row = json.loads(line)
                if not isinstance(row, dict): raise ValueError(f"{path}:{line_no}: expected JSON object")
                raw_code = row.get("lang_code")
                if not raw_code: raise ValueError(f"{path}:{line_no}: missing lang_code")
                code = canonical_iso639(raw_code)
                g = groups.setdefault(code, {"count":0,"scores":[],"confidences":[],"reviews":Counter(),"sources":Counter(),"tags":Counter(),"hashes":set(),"review_required":0})
                g["count"] += 1
                if isinstance(row.get("quality_score"),(int,float)): g["scores"].append(float(row["quality_score"]))
                if isinstance(row.get("language_confidence"),(int,float)): g["confidences"].append(float(row["language_confidence"]))
                g["reviews"][row.get("human_review_status","missing")] += 1
                g["sources"][row.get("source","missing")] += 1
                g["tags"][row.get("source_lang_tag",raw_code)] += 1
                norm=" ".join(str(row.get("text","")).casefold().split())
                g["hashes"].add(hashlib.sha256(norm.encode("utf-8")).hexdigest())
                if row.get("routing_status")=="needs_review" or row.get("language_conflict") is True: g["review_required"] += 1
    result={"schema_version":1,"languages":{}}
    for code,g in sorted(groups.items()):
        scores,conf=g["scores"],g["confidences"]; n=g["count"]; unique=len(g["hashes"])
        result["languages"][code]={
            "records":n,"unique_exact_texts":unique,"exact_duplicate_rate":round(1-unique/n,6) if n else 0,
            "quality_score":{"n":len(scores),"mean":round(statistics.mean(scores),6) if scores else None,"median":round(statistics.median(scores),6) if scores else None,"min":min(scores) if scores else None,"max":max(scores) if scores else None},
            "language_confidence":{"n":len(conf),"mean":round(statistics.mean(conf),6) if conf else None},
            "human_review_status":dict(g["reviews"]),"sources":dict(g["sources"]),"source_language_tags":dict(g["tags"]),"review_required":g["review_required"]}
    return result


def main() -> None:
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--input',required=True,type=Path,help='JSONL file or directory searched recursively'); p.add_argument('--output',required=True,type=Path)
    a=p.parse_args(); paths=[a.input] if a.input.is_file() else sorted(a.input.rglob('*.jsonl'))
    report=summarize(paths); a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    for code,values in report['languages'].items(): print(f"{code}\trecords={values['records']}\tquality_mean={values['quality_score']['mean']}\treview_required={values['review_required']}")
    print(f"Wrote {len(report['languages'])} language summaries to {a.output}")

if __name__=='__main__': main()
