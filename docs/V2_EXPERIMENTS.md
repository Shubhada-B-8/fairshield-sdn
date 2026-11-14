# V2 Experimental Evaluation

## Reproducibility settings

- Scenarios: normal, DDoS-like, flash crowd and mixed.
- Windows: 30 per scenario.
- Pseudorandom seed: 7.
- Bottleneck capacity: 500 pps.
- V1 baseline policies: no defense, static threshold and fixed-cap FairShield.
- V2 policy: feedback-driven adaptive FairShield.

Run from the repository root after installing the package:

```bash
python -m pip install -e .
python -m fairshield.cli adaptive-demo --scenario all --windows 30 --seed 7 --capacity 500 --out outputs_v2
```

The `outputs_v2/` directory contains `adaptive_summary.csv`, `adaptive_summary.json`, `adaptive_trace.csv`, and `v1_v2_comparison.csv`. A 10-seed paired robustness run (seeds 1–10, 30 windows per seed, same 500-pps capacity) is also stored under `outputs_v2/multiseed/`.

Run the paired multi-seed analysis:

```bash
python scripts/run_v2_multiseed.py --seeds 1,2,3,4,5,6,7,8,9,10 --windows 30 --capacity 500 --out outputs_v2/multiseed
```

## Results

| Scenario | Policy | Legitimate preserved | Attack demand mitigated | Jain fairness | Delivered pps | Mean attack cap |
|---|---|---:|---:|---:|---:|---:|
| DDoS | No defense | 70.24% | 0.00% | 0.9980 | 500.00 | — |
| DDoS | Static threshold | 99.87% | 100.00% | 1.0000 | 440.17 | — |
| DDoS | V1 FairShield | 98.99% | 99.38% | 1.0000 | 466.27 | 5.00 pps fixed cap |
| DDoS | V2 adaptive FairShield | 99.50% | 99.80% | 1.0000 | 448.21 | 1.62 pps |
| Mixed | No defense | 27.35% | 0.00% | 0.8211 | 500.00 | — |
| Mixed | Static threshold | 35.10% | 100.00% | 0.7143 | 449.17 | — |
| Mixed | V1 FairShield | 36.73% | 99.36% | 0.8266 | 500.00 | 5.00 pps fixed cap |
| Mixed | V2 adaptive FairShield | 38.44% | 99.83% | 0.8284 | 500.00 | 1.35 pps |

V1 fixed cap baseline is 5 pps in the offline simulator. V2 uses the same 5 pps initial cap, but changes it using preceding-window feedback. The mean cap values are averaged over attack-source observations only.

## Interpretation

- In the DDoS scenario, V2 increased legitimate preservation from 98.99% to 99.50% and increased policy-level attack mitigation from 99.38% to 99.80% relative to V1. Total delivered throughput fell from 466.27 to 448.21 pps, indicating a trade-off: more aggressive attack suppression also reduced attack traffic contributing to total throughput.
- In the mixed scenario, V2 increased legitimate preservation from 36.73% to 38.44%, attack mitigation from 99.36% to 99.83%, and Jain fairness from 0.8266 to 0.8284 relative to V1. Delivered throughput remained at 500 pps.
- In normal and flash-crowd scenarios, V2 behaves like V1 because the detector does not classify those sources as suspicious under the current feature rules. The flash-crowd scenario remains constrained by the offered load and the capacity model; V2 is not claimed to solve this condition.
- F1 is a detector metric and does not change across mitigation policies when the detector predictions are held constant. In no-positive scenarios (normal and flash crowd), F1 is reported as zero.

## Critical caveat

These are synthetic deterministic simulator results, not measurements from Mininet or a production network. The simulator feeds the adaptive controller a suppression proxy for source meter-drop feedback. It does **not** query Open vSwitch meter counters. The earlier V1 live demonstration independently verified OVS meter installation, drop-band counters, cleanup and subsequent normal UDP delivery. That V1 live evidence does not establish V2 live performance.

## Recommended next experiments

1. Multi-source Mininet experiment with at least two legitimate senders and two attack-like senders.
2. Poll OVS meter statistics and table counters to generate per-source feedback from real switch measurements.
3. Compare V1 and V2 under identical traffic traces and equal link capacity.
4. Sweep attack start/stop times and traffic intensity; report repeated seeds and confidence intervals.
5. Measure controller processing time, rule update frequency and false-positive duration.
6. Add ablations: no feedback, utilization-only feedback, legitimate-service-only feedback, and full feedback.


## Ten-seed paired robustness analysis

We additionally ran 10 deterministic seeds (1 through 10), 30 windows per seed, across all four scenarios and all V1/V2 policies. This produced 160 policy-scenario runs. The table below reports mean ± sample standard deviation over seeds.

| Scenario | Policy | Legitimate preserved | Attack mitigated | Jain fairness | Delivered pps |
|---|---|---:|---:|---:|---:|
| DDoS | V1 FairShield | 98.77 ± 0.42% | 99.375 ± 0.006% | 0.999972 ± 0.000022 | 469.37 ± 5.02 |
| DDoS | V2 adaptive | 99.55 ± 0.28% | 99.808 ± 0.014% | 0.999988 ± 0.000011 | 452.05 ± 5.35 |
| Mixed | V1 FairShield | 36.91 ± 0.21% | 99.369 ± 0.007% | 0.826969 ± 0.000909 | 500.00 ± 0.00 |
| Mixed | V2 adaptive | 38.63 ± 0.22% | 99.830 ± 0.002% | 0.829037 ± 0.000948 | 500.00 ± 0.00 |

Across these 10 seeds, V2's mean legitimate preservation is higher than V1 in the DDoS and mixed scenarios. V2 also has a higher mean policy-level attack mitigation. DDoS total delivered throughput is lower under V2, which is consistent with stronger suppression of attack demand; in mixed traffic, both policies reach the configured 500-pps total throughput. The small standard deviations reflect this deterministic generator and should not be interpreted as a guarantee about real networks.

F1 remains 1.0 in the generated DDoS and mixed scenarios for both versions. The generator's attack and benign profiles are deliberately well-separated, so this F1 value is not evidence of real-world detection performance.
