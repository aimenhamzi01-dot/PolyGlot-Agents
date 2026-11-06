#!/usr/bin/env python3
"""Select a reproducible review sample and mark it pending human review."""
import argparse, json, random
from pathlib import Path

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--input',required=True,type=Path); p.add_argument('--output',required=True,type=Path); p.add_argument('--n',type=int,default=50); p.add_argument('--seed',type=int,default=13); a=p.parse_args()
    rows=[json.loads(x) for x in a.input.read_text(encoding='utf-8').splitlines() if x.strip()]
    chosen=random.Random(a.seed).sample(rows,min(a.n,len(rows)))
    with a.output.open('w',encoding='utf-8') as f:
        for row in chosen: row['human_review_status']='unreviewed'; f.write(json.dumps(row,ensure_ascii=False)+'\n')
    print(f'sampled={len(chosen)} output={a.output}')
if __name__=='__main__': main()
