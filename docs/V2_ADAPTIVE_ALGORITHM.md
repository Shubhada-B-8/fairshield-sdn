# FairShield-SDN V2: Feedback-Driven Adaptive Admission Control

## Status

The V2 policy is implemented in the adaptive policy engine and deterministic simulator. The live OS-Ken adapter now includes table-0 offered-packet observations, table-1 forwarded-packet observations, source meter-drop feedback and legitimate-service feedback. Controller excerpts showed service measurements and cap-relaxation decisions under reported headroom conditions. Live congestion-driven cap tightening has not been conclusively validated.

## Motivation

V1 uses a fixed attacker admission cap. A fixed cap is easy to explain and test, but it cannot react to changes in bottleneck pressure or service quality. V2 adds a stateful feedback controller that changes the suspicious-source cap between measurement windows.

## Inputs

For each source and control interval:

- Source traffic sample: packet count, byte count, SYN count, destination-port fan-out and duration.
- `capacity_utilization`: delivered traffic divided by configured link capacity, clipped to [0, 1].
- `legitimate_service_ratio`: legitimate delivered traffic divided by legitimate offered traffic.
- `source_meter_drop_ratio`: share of the source traffic dropped by its meter in the preceding interval. A live deployment must obtain this from that source's OpenFlow meter band counters.

The simulator cannot observe actual OVS counters. It supplies an explicitly named `simulated_meter_drop_proxy`, calculated from the simulator's admission suppression. This proxy is suitable for deterministic algorithm tests only; it is not a measured meter drop rate.

## Control rule

Each source maintains a cap state `C_i(t)`. The detector is the existing interpretable `RuleBasedDetector`.

For a suspicious source:

1. Define congestion if `capacity_utilization >= 0.90` **or** `legitimate_service_ratio < 0.95`.
2. Under congestion, tighten the cap: `C_i(t+1) = max(C_min, 0.75 * C_i(t))`.
3. Otherwise, if utilization is at most 0.75, legitimate service is at least 0.95, and source meter drop ratio is at least 0.10, relax the cap: `C_i(t+1) = min(C_max, 1.20 * C_i(t))`.
4. Otherwise hold the cap (hysteresis band).

For a benign source, count consecutive benign observations. After two such observations, increase a previously reduced stored cap by 20% per observation until it returns to the configured initial cap. The cap is only applied to a source while it is classified as suspicious.

After admitted demand has been calculated for all sources, the controller uses the existing weighted max-min allocator against the configured link capacity.

## Default parameters

| Parameter | Default |
|---|---:|
| Link capacity | 500 pps |
| Initial suspicious-source cap | 5 pps |
| Minimum cap | 1 pps |
| Maximum cap | 40 pps |
| Congestion threshold | 90% utilization |
| Headroom threshold | 75% utilization |
| Legitimate service target | 95% |
| Meter-drop relaxation threshold | 10% |
| Tightening multiplier | 0.75 |
| Relaxation multiplier | 1.20 |
| Benign recovery delay | 2 consecutive windows |

## Why this is not yet an established novel invention

Adaptive rate control, feedback control, fair allocation and SDN meter enforcement all have prior art. V2 is a concrete experimental extension, not a claim of novelty or patentability. Novelty requires a separate exhaustive literature/patent search, claim mapping and review by a registered patent professional.

## Safety and limitations

- V2 is for an isolated lab/simulator, not a production DDoS defense.
- The detector remains rule-based and can misclassify traffic outside its designed feature patterns.
- Feedback is one window delayed. Delayed or noisy measurements may cause oscillation.
- The simulator uses a proxy for meter-drop feedback; only real per-source OVS meter counters can validate that feedback path.
- The live adapter has not yet been migrated to V2. It continues using the V1 fixed-cap policy until live feedback polling and a controlled Mininet comparison are implemented and tested.
