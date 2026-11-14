# FairShield-SDN V2.0.0 — Viva Preparation

## Core questions

### 1. What is new in V2 compared with V1?
V1 uses a fixed suspicious-source admission cap. V2 adds a stateful cap controller that adjusts the cap from feedback from the preceding observation window. It tightens under congestion or poor legitimate service, relaxes when there is spare capacity and a sufficiently high source meter-drop signal, and gradually recovers after benign observations.

### 2. Is V2 a completely new DDoS detector?
No. V2 reuses the existing rule-based detector. The new component is the adaptive admission-cap control logic. We do not claim a new detector architecture.

### 3. What inputs does the detector use?
The offline detector uses packet rate, SYN ratio, destination-port fan-out and bit rate. The V1 live adapter uses packet rate, average packet size, bit rate and destination-port fan-out because aggregate OpenFlow counters used in that adapter do not expose TCP SYN flags.

### 4. What is the role of feedback?
Feedback measures the previous interval's network condition. It is used to change the cap for the next interval. This is a closed-loop controller with one-window delay.

### 5. When does V2 tighten an attack-source cap?
When capacity utilization is at least 90% or legitimate service falls below 95%. The cap is multiplied by 0.75 and bounded by a minimum of 1 pps.

### 6. When does V2 relax a cap?
When utilization is at most 75%, legitimate service is at least 95%, and the source meter-drop ratio is at least 10%. The cap is multiplied by 1.20 and bounded by a maximum of 40 pps.

### 7. Why are there two utilization thresholds?
The 75% headroom and 90% congestion thresholds create a hysteresis region. Inside it, the controller holds the cap instead of changing it on every small fluctuation.

### 8. What happens when a source becomes benign?
After two consecutive benign observations, the stored cap recovers gradually by a factor of 1.20 until it reaches the initial 5 pps value. The cap only limits the source while it is suspicious.

### 9. Why use max-min fairness after admission control?
Admission control limits suspicious-source demand first. Weighted max-min allocation then distributes the remaining capacity while respecting each source's admitted demand.

### 10. What is Jain's Fairness Index?
It measures equality among the legitimate sources' service-satisfaction ratios. A value closer to 1 indicates more equal satisfaction.

### 11. Why can V2 have lower total delivered throughput in the DDoS scenario?
V2 suppresses a larger share of attack demand. Attack packets that are intentionally not admitted no longer contribute to total delivered throughput. This is a trade-off, not a hidden benefit.

### 12. Why is the flash-crowd result unchanged?
The current detector does not label the generated flash-crowd profiles as suspicious. Therefore the adaptive attack cap is not applied. The scenario remains constrained by the offered load and single-bottleneck capacity model.

### 13. Why is F1 the same for V1 and V2?
The detector predictions are held constant across the mitigation policies. F1 evaluates classification, not admission allocation. It is therefore expected to remain the same.

### 14. Why is F1 equal to 1 in the generated DDoS and mixed scenarios?
The synthetic generator creates deliberately distinct attack and benign feature profiles. That makes these generated classes easy for the rule detector to separate. This is not evidence of real-world accuracy.

### 15. Is the V2 meter-drop feedback a real Open vSwitch counter?
Not in this release. The simulator uses a suppression proxy derived from offered versus admitted demand. A live implementation must use the source's actual OpenFlow meter-band counters.

### 16. Is V2 live-tested on Mininet and OVS?
No. The earlier live test verified the V1 adapter's meter installation, drop-band counters, cleanup and normal UDP delivery. V2 adaptive feedback is currently validated in the offline simulator and dashboard API only.

### 17. What is the difference between a simulation and the live Mininet test?
The simulator creates synthetic traffic records and mathematically models allocation. The Mininet test sends packets through a virtual network and observes actual OVS rules, meter counters and receiver output.

### 18. What did the 10-seed experiment test?
It ran four traffic scenarios with four policies across 10 paired random seeds, with 30 windows per seed and 500 pps capacity, producing 160 policy-scenario runs. Means and sample standard deviations are reported.

### 19. Does this prove patent novelty?
No. Adaptive control, SDN meters and fairness-aware DDoS mitigation have prior art. A claim-focused prior-art search and legal review would be needed before any patentability conclusion.

### 20. What is the next technical milestone?
Connect V2 to real per-source OVS meter-band counters and receiver/egress service measurements, then run a controlled multi-source Mininet comparison against V1 and baseline policies.


## Current live-validation status — 14 November 2026

The live adapter now collects table-0 offered counters, table-1 forwarded counters, per-source meter statistics and legitimate-service feedback. Controller excerpts showed legitimate-service ratios of 1.000 in observed intervals and cap-relaxation decisions under reported headroom conditions. The excerpts are not a complete timestamp-aligned record for the archived four-source run. Its receiver interval totals do not reconcile with sender totals. Do not claim proven 200-PPS enforcement in that run or proven live congestion-driven cap tightening.

## One-minute summary

FairShield-SDN V2 preserves the existing source-level detector and max-min fairness allocator, but replaces the fixed suspicious-source cap with a bounded feedback-driven cap. It tightens when congestion or legitimate-service degradation is observed, relaxes when headroom and meter-drop feedback indicate over-restriction, and recovers gradually after benign observations. The new policy is reproducibly tested in a synthetic simulator across four scenarios and 10 paired seeds. The current V2 feedback path is not yet connected to live OVS meter counters; live enforcement evidence in this project comes from V1.


## V2 live feedback status — 14 November 2026

The live adapter now collects table-0 offered-packet counters, table-1 forwarded-packet counters, per-source meter-drop feedback and legitimate-service feedback. Controller excerpts showed legitimate-service ratios of 1.000 in observed intervals and cap-relaxation decisions under reported headroom conditions.

The four-source run used h1/h3 at 4,000 PPS with 500-byte payloads and h2/h4 at 100 PPS with 1,000-byte payloads. Receiver means were h1 2,362.8 PPS, h2 96.1 PPS, h3 2,254.2 PPS and h4 95.9 PPS. Receiver interval packet sums do not reconcile with sender totals; these are descriptive log statistics, not delivery ratios. The run does not prove 200-PPS enforcement. Live congestion-driven cap tightening remains unverified.

The Streamlit adaptive-policy sandbox is illustrative, not a live controller connection. The latest recorded automated test run passed 27 tests.
