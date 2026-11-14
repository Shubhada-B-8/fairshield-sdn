#!/usr/bin/env python3
"""Run paired V1/V2 synthetic comparisons over multiple deterministic seeds."""
from __future__ import annotations
import argparse, csv, statistics
from pathlib import Path
from fairshield.simulator import SCENARIOS, run_suite
from fairshield.adaptive_simulator import run_adaptive_suite

METRICS = ("legitimate_preservation", "attack_mitigation", "jain_fairness", "delivered_pps", "f1")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seeds', default='1,2,3,4,5,6,7,8,9,10')
    parser.add_argument('--windows', type=int, default=30)
    parser.add_argument('--capacity', type=float, default=500)
    parser.add_argument('--out', default='outputs_v2/multiseed')
    args = parser.parse_args()
    seeds=[int(x) for x in args.seeds.split(',') if x.strip()]
    if not seeds: raise SystemExit('At least one seed is required')
    rows=[]
    for seed in seeds:
        base,_=run_suite(SCENARIOS,windows=args.windows,seed=seed,link_capacity_pps=args.capacity)
        adaptive,_=run_adaptive_suite(SCENARIOS,windows=args.windows,seed=seed,capacity_pps=args.capacity)
        for r in base:
            rows.append({'seed':seed,'scenario':r.scenario,'policy':r.policy,
                         'legitimate_preservation':r.legitimate_preservation,
                         'attack_mitigation':r.attack_mitigation,
                         'jain_fairness':r.jain_satisfaction_fairness,
                         'delivered_pps':r.delivered_pps,'f1':r.f1})
        for r in adaptive:
            rows.append({'seed':seed,'scenario':r.scenario,'policy':r.policy,
                         'legitimate_preservation':r.legitimate_preservation,
                         'attack_mitigation':r.attack_mitigation,
                         'jain_fairness':r.jain_satisfaction_fairness,
                         'delivered_pps':r.delivered_pps,'f1':r.f1})
    out=Path(args.out); out.mkdir(parents=True,exist_ok=True)
    with (out/'raw_results.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    grouped={}
    for r in rows: grouped.setdefault((r['scenario'],r['policy']),[]).append(r)
    summaries=[]
    for (scenario,policy),items in sorted(grouped.items()):
        row={'scenario':scenario,'policy':policy,'seeds':len(items),'windows_per_seed':args.windows}
        for metric in METRICS:
            vals=[float(x[metric]) for x in items]
            row[metric+'_mean']=statistics.mean(vals)
            row[metric+'_std']=statistics.stdev(vals) if len(vals)>1 else 0.0
        summaries.append(row)
    with (out/'mean_std_summary.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(summaries[0])); w.writeheader(); w.writerows(summaries)
    print(f'Completed {len(seeds)} seeds x {len(SCENARIOS)} scenarios; raw rows={len(rows)}')
    print(out/'raw_results.csv'); print(out/'mean_std_summary.csv')

if __name__=='__main__': main()
