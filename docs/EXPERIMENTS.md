# FairShield-SDN Experiments and Results

## Experimental tracks

FairShield has two different evaluation tracks. They must not be conflated:

1. **Offline synthetic simulator:** controlled, deterministic comparisons of no defense, static threshold and FairShield across normal, DDoS-like, flash-crowd and mixed traffic.
2. **Live Mininet / Open vSwitch lab:** a single-source UDP stress test that verifies controller-to-switch integration, OpenFlow meter enforcement, drop counters, meter cleanup and post-cleanup traffic delivery.

The simulator is not a packet-level network emulator. Live results do not provide a controlled three-policy benchmark.

## Reproducible simulator configuration

- Input: synthetic source-level traffic observations.
- Scenario set: normal, DDoS-like, flash crowd and mixed.
- Policies: `no_defense`, `static_threshold`, `fairshield`.
- Reproducibility: random seed 7, 30 windows.
- Configured bottleneck capacity: 500 packets/second.
- Output: CSV and JSON summaries plus per-window/source traces in `outputs/reproducibility_seed7_30/`.

Run (from the project root, with the package installed or `PYTHONPATH=src`):

```bash
PYTHONPATH=src python -m fairshield.cli demo --windows 30 --seed 7 --capacity 500 --out outputs/reproducibility_seed7_30
```

The repository's saved outputs are the source for the tables and figures in this report.

## Core synthetic results

| Scenario | Policy | Legitimate preserved | Attack demand mitigated | Jain fairness | F1 | Delivered PPS |
|---|---|---:|---:|---:|---:|---:|
| DDoS-like | No defense | 70.2% | 0.0% | 0.998 | 1.000 | 500.00 |
| DDoS-like | Static threshold | 99.9% | 100.0% | 1.000 | 1.000 | 440.17 |
| DDoS-like | FairShield | 99.0% | 99.4% | 1.000 | 1.000 | 466.27 |
| Flash crowd | No defense | 25.4% | N/A | 0.694 | 0.000 | 500.00 |
| Flash crowd | Static threshold | 17.1% | N/A | 0.500 | 0.000 | 335.57 |
| Flash crowd | FairShield | 25.4% | N/A | 0.694 | 0.000 | 500.00 |
| Mixed | No defense | 27.3% | 0.0% | 0.821 | 1.000 | 500.00 |
| Mixed | Static threshold | 35.1% | 100.0% | 0.714 | 1.000 | 449.17 |
| Mixed | FairShield | 36.7% | 99.4% | 0.827 | 1.000 | 500.00 |

Normal scenario: all three policies are identical in this run, with 95.5% legitimate preservation, 0.9999 fairness and 487.83 delivered PPS. There is no attack traffic, so attack mitigation and detector F1 are not meaningful performance differentiators.

## Interpretation

- **DDoS-like:** Static threshold slightly exceeds FairShield on legitimate preservation and policy-level suppression in this particular synthetic run. FairShield still suppresses 99.4% of attack demand and delivers more total PPS than the static-threshold policy (466.27 vs 440.17).
- **Flash crowd:** Static threshold reduces legitimate preservation to 17.1% and fairness to 0.500. FairShield matches no defense in this generated scenario (25.4% preservation, 0.694 fairness), indicating it avoids the static threshold's false-positive collateral restriction. Congestion still limits delivered traffic.
- **Mixed:** FairShield has the highest legitimate preservation (36.7%) and fairness (0.827) among the three policies in this run, while policy-level attack suppression is 99.4%. Static threshold suppresses all attack demand but provides lower legitimate preservation and fairness.
- **Detector F1:** The 1.0 values for DDoS-like and mixed synthetic scenarios result from deliberately separable generated features. They must not be interpreted as expected real-world classifier performance.

All results above are synthetic simulator metrics. The attack mitigation metric is policy-level suppression of attack demand before bottleneck contention; it is not end-to-end packet loss.

## Live Mininet / OVS findings

The 12 November 2026 isolated lab demo is documented with values and limitations in `LIVE_DEMO_EVIDENCE.md`. Key observations:

- OpenFlow 1.3 switch connection to controller `127.0.0.1:6653` was active.
- `pingall` passed with 0% packet loss (30/30).
- Normal UDP test: sender 1000 packets, 100 PPS, 800 kbps; receiver logged approximately 100 PPS / 800 kbps.
- High-rate source `10.0.0.1`: controller score 0.90 and `RATE_LIMIT`; observed rate approximately 1.77–1.94 Mbps, capped at 1500 kbps.
- OVS meter 1 was configured with a drop band at 1500 kbps and burst size 150.
- At one statistics snapshot (47.031 s): 47,031 packets entered the meter; the drop band counted 10,515 packets and 2,544,630 bytes. This is 22.36% of meter-input packets for that snapshot, not end-to-end loss.
- Controller requested meter deletion; subsequent OVS inspection showed no meter config and no source-specific table-0 rule.
- Normal UDP delivery was confirmed again after running `pingall` to refresh learned forwarding state.

This live experiment is a single-source attack-like UDP stress test. It does not compare all three policies on a live network, and it does not measure physical-link capacity, latency or end-to-end loss.


## V2 live feedback and four-source follow-up — 14 November 2026

The live controller added table-0 offered-packet observations, table-1 forwarded-packet observations, per-source meter feedback and legitimate-service feedback. Development-session excerpts showed h2 and h4 legitimate-service ratios of 1.000 in observed reporting intervals. Other excerpts showed cap relaxation under reported headroom conditions. These excerpts are not a complete timestamp-aligned controller log for the four-source run.

| Host | Role | Target PPS | Payload | Sender packets |
|---|---|---:|---:|---:|
| h1 | Attack-like | 4,000 | 500 bytes | 120,000 |
| h3 | Attack-like | 4,000 | 500 bytes | 120,000 |
| h2 | Legitimate | 100 | 1,000 bytes | 3,000 |
| h4 | Legitimate | 100 | 1,000 bytes | 3,000 |

Receiver-log mean rates were h1 2,362.8 PPS, h2 96.1 PPS, h3 2,254.2 PPS and h4 95.9 PPS. Receiver interval packet sums do not reconcile with sender totals: h2 and h4 each show 6,000 summed interval packets against 3,000 sender-reported packets. These are descriptive log statistics, not unique delivered datagrams or delivery ratios. The run does not prove enforcement at the 200-PPS cap. Live congestion-driven cap tightening remains unverified. See `LIVE_DEMO_EVIDENCE.md` for the full evidence record.

## Further experiments recommended

- Multi-source mixed UDP tests using legitimate larger-packet sources and two attack-like smaller-packet sources.
- Live baselines: no meter / static fixed meter / FairShield, using identical traffic and repeated trials.
- Capture receiver counts, packet captures, throughput, latency, packet loss, CPU and flow-table occupancy.
- Repeat across seeds and traffic profiles; report confidence intervals and sensitivity to the 300 PPS / 800 PPS thresholds, 1500 kbps attacker cap and 10000 kbps configured policy budget.
- Add ablations for packet-rate-only, packet-size-only, fan-out, and combined scoring.


## V2 live feedback status — 14 November 2026

The live adapter now collects table-0 offered-packet counters, table-1 forwarded-packet counters, per-source meter-drop feedback and legitimate-service feedback. Controller excerpts showed legitimate-service ratios of 1.000 in observed intervals and cap-relaxation decisions under reported headroom conditions.

The four-source run used h1/h3 at 4,000 PPS with 500-byte payloads and h2/h4 at 100 PPS with 1,000-byte payloads. Receiver means were h1 2,362.8 PPS, h2 96.1 PPS, h3 2,254.2 PPS and h4 95.9 PPS. Receiver interval packet sums do not reconcile with sender totals; these are descriptive log statistics, not delivery ratios. The run does not prove 200-PPS enforcement. Live congestion-driven cap tightening remains unverified.

The Streamlit adaptive-policy sandbox is illustrative, not a live controller connection. The latest recorded automated test run passed 27 tests.
