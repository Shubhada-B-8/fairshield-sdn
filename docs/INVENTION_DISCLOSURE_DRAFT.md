# Preliminary invention disclosure — working draft

> **Not a patent application and not a legal opinion.** This document is a technical disclosure scaffold for discussion with an Indian patent agent/attorney. No novelty, inventive step, eligibility, ownership, or grant is asserted. Do not publicly disclose implementation details before receiving filing advice if preserving filing options is important.

## Working title

Fairness-Aware Adaptive Admission Control for Mitigating Distributed Denial-of-Service Traffic in Software-Defined Networks

## Technical field

Computer networking; software-defined networking; network traffic measurement; denial-of-service mitigation; resource allocation and network quality of service.

## Technical problem

A network controller may detect high-rate or abnormal traffic and install filtering rules. A coarse threshold can misclassify legitimate bursts, while a blanket drop policy may unnecessarily reduce service to legitimate sources during a shared-link overload. A useful mitigation objective should therefore consider both suspicious-source suppression and continued service to non-suspicious sources under a finite link budget.

## Proposed system concept

A controller receives time-windowed flow telemetry from one or more programmable switches. It derives per-source traffic indicators, computes a suspiciousness score, maps that score to an admission cap, and allocates the remaining link budget among admitted sources using a fairness-aware allocator. The system records the admitted rates and per-source delivery satisfaction to evaluate whether the policy preserves legitimate traffic while reducing attack throughput.

## Current implementation versus future candidate features

The distinction below is essential. A patent specification must accurately disclose what was actually conceived and implemented; do not present planned features as completed work.

| Element | Status in prototype v1.1 |
|---|---|
| Per-source flow telemetry with pps, bit rate, average packet size, SYN ratio and destination-port fan-out | Offline simulator includes pps, bit rate, SYN ratio and port fan-out; live SDN controller includes pps, bit rate, average packet size and port fan-out. Rate-of-change features are not implemented. |
| Multi-indicator anomaly score and binary suspicious/not-suspicious decision | Implemented in the simulator. |
| Confidence-tier mapping to several different source caps | **Not implemented.** The current prototype uses one fixed 5 pps cap for every suspicious source. |
| Max-min capacity allocation after source caps | Implemented in the offline simulator with equal weights by default. |
| Jain satisfaction-fairness measurement | Implemented as an evaluation metric; it does not currently feed back into the policy. |
| Time-bounded re-evaluation and automatic restoration | Live code re-evaluates every five seconds and removes a meter when measured demand no longer needs limiting or the source flow becomes stale; hysteresis, hold-down timers and failure recovery are not implemented. Live meter installation, drop counters, meter deletion and post-cleanup traffic delivery were observed in an isolated Mininet/OVS lab on 12 November 2026. The recovery delivery check followed a `pingall` forwarding-state refresh; hysteresis, hold-down timers and failure recovery are still not implemented. |
| OpenFlow switch enforcement | OS-Ken/Ryu-compatible OpenFlow 1.3 adapter code implements a two-table pipeline with per-source meter add/modify/delete and weighted max-min rates. Runtime execution was demonstrated in an isolated six-host Mininet/OVS lab on 12 November 2026. The test verified an OpenFlow 1.3 connection, a 1500 kbit/s source meter, nonzero drop-band counters, meter removal and normal UDP delivery after forwarding state was refreshed. The test was single-source and is not a distributed-attack benchmark. |

Potential future research directions include (a) a validated confidence-to-cap mapping, (b) a closed-loop fairness objective that adjusts admission caps based on legitimate-source satisfaction, and (c) controller failover and multi-switch coordination. These are research proposals, not current features, and need implementation, comparative testing and a new prior-art review before being considered as potential claim elements.

## Implemented method in prototype v1.1

1. Generate or receive one source-level flow observation for a measurement window.
2. Derive packet rate, bit rate, SYN ratio and destination-port fan-out in the offline path; the live path also uses average packet size.
3. Calculate a rule-based anomaly score and compare it with a fixed threshold.
4. In the offline simulator, cap suspicious source demand at 5 pps; in the live controller, cap flagged source demand at 1,500 kbit/s.
5. Allocate capacity using max-min allocation subject to admitted demand (the live adapter uses the configured 10,000 kbit/s policy budget).
6. In the live adapter, translate per-source allocations into OpenFlow meter bands and install or update source meter rules.
7. Record source-level decisions and evaluation metrics in the offline path; collect switch counters and meter statistics separately in the live Mininet path.

The optional OS-Ken/Ryu-compatible adapter implements OpenFlow 1.3 flow monitoring and per-source meter enforcement. It uses a separate heuristic (packet rate, mean packet size, bit rate and port fan-out) and applies a 1,500 kbit/s suspicious-source cap before weighted max-min allocation against a configured 10,000 kbit/s budget. The code compiles and its pure policy functions are unit tested. A live Mininet/OVS run has now demonstrated switch-level meter enforcement and cleanup; exact observations and limitations are recorded in `docs/LIVE_DEMO_EVIDENCE.md`.

## Future candidate method / claim concept — only after implementation and review

A possible future direction would be a computer-implemented method performed by an SDN controller that receives switch flow counters, derives multi-indicator source profiles, maps a calibrated confidence level to a graduated source admission cap, allocates a shared bottleneck resource subject to those caps, and updates the caps using a measured legitimate-service objective. This is not what prototype v1.1 fully implements. Do not file a claim describing these future steps as implemented until the design is actually built, experimentally validated and reviewed against prior art by a patent professional.

## Inventorship and ownership record — fill before filing

- Actual human inventor(s): [to be completed]
- Applicant / owner: [to be confirmed]
- Institution / employer / sponsor obligations: [to be checked]
- First conception date and dated notebooks: [to be documented]
- Prototype contributors and third-party components: [to be documented]
- Any public disclosure, poster, repository, presentation, demo or submission: [dates and details]
- Source-code and dataset licences: [to be audited]

Do not name an AI system as an inventor. Identify the human contributors who actually conceived the claimed technical features, with advice from a patent professional.

## Evidence to collect

- Source code commit hashes and dated design notes.
- Network diagrams and controller/switch configuration.
- Reproducible Mininet experiments with raw pcaps/flow statistics where lawful.
- Ablation and baseline comparisons.
- Measurements of goodput, delay, packet loss, controller load, flow-table use and rule-installation latency.
- A clear explanation of the technical effect attributable to each claimed feature.


## Live validation evidence (12 November 2026)

The isolated Mininet lab demonstrated OpenFlow 1.3 connectivity, per-source meter installation at 1500 kbit/s for source 10.0.0.1, 10,515 drop-band packets out of 47,031 meter-input packets in one 47.031-second statistics snapshot, meter deletion, and normal UDP delivery after a forwarding-state refresh. This is a single-source controlled lab test, not a distributed DDoS efficacy result or a live baseline comparison. See `LIVE_DEMO_EVIDENCE.md` for full details.


## V2 live feedback status — 14 November 2026

The live adapter now collects table-0 offered-packet counters, table-1 forwarded-packet counters, per-source meter-drop feedback and legitimate-service feedback. Controller excerpts showed legitimate-service ratios of 1.000 in observed intervals and cap-relaxation decisions under reported headroom conditions.

The four-source run used h1/h3 at 4,000 PPS with 500-byte payloads and h2/h4 at 100 PPS with 1,000-byte payloads. Receiver means were h1 2,362.8 PPS, h2 96.1 PPS, h3 2,254.2 PPS and h4 95.9 PPS. Receiver interval packet sums do not reconcile with sender totals; these are descriptive log statistics, not delivery ratios. The run does not prove 200-PPS enforcement. Live congestion-driven cap tightening remains unverified.

The Streamlit adaptive-policy sandbox is illustrative, not a live controller connection. The latest recorded automated test run passed 27 tests.
