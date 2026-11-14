# FairShield-SDN V2: Feedback-Driven Adaptive Admission Control for Fairness-Aware SDN DDoS Mitigation

**Research paper draft — not peer reviewed and not ready for journal/conference submission**

## Abstract

DDoS traffic can consume a constrained network bottleneck and reduce service available to legitimate clients. Static rate limits are simple to enforce but may be poorly matched to changing traffic and service conditions. This paper presents FairShield-SDN V2, a research prototype that adds a stateful feedback-driven admission-cap controller to an existing software-defined networking (SDN) mitigation framework. The controller classifies source traffic using an interpretable rule-based detector, adjusts suspicious-source admission caps using preceding-window bottleneck utilization, legitimate-service ratio and source meter-drop feedback, and allocates admitted demands using weighted max-min water filling. A deterministic simulator compares V2 with no defense, a fixed threshold and the V1 fixed-cap policy across normal, DDoS-like, flash-crowd and mixed traffic. In a 10-seed paired synthetic experiment, V2 improves mean legitimate preservation from 98.77% to 99.55% in the DDoS scenario and from 36.91% to 38.63% in the mixed scenario relative to V1; mean policy-level attack-demand mitigation also increases modestly. In the pure DDoS case, mean delivered throughput decreases from 469.37 to 452.05 pps, exposing a trade-off caused by more aggressive attack-demand suppression. The live OS-Ken/OpenFlow 1.3 implementation was extended with table-based offered/forwarded packet counters and legitimate-service feedback. Controller excerpts showed legitimate-service feedback and adaptive cap relaxation under reported headroom conditions. A separate four-source high-load run was archived, but its receiver log does not reconcile with sender totals, and it does not establish enforcement at the configured 200-pps attack cap. Live congestion-driven cap tightening has not been conclusively validated. These results are preliminary synthetic and testbed evidence, not production-network measurements or evidence of superiority over the state of the art.

**Keywords:** Software-Defined Networking, DDoS mitigation, admission control, max-min fairness, OpenFlow, adaptive feedback, Open vSwitch.

## 1. Introduction

DDoS mitigation at a constrained network bottleneck must balance attack suppression against legitimate-user service. A mitigation rule that is too permissive can leave the bottleneck congested; a rule that is too restrictive can discard benign traffic, particularly during sudden demand bursts. SDN provides a programmable control plane that can observe traffic and configure data-plane rules, including OpenFlow meters. However, the presence of a controller and a meter is not, by itself, a new DDoS mitigation technique.

FairShield-SDN V1 combined an interpretable source-level traffic score, suspicious-source demand capping, max-min allocation and a live OS-Ken/OpenFlow 1.3 adapter. V2 investigates a narrower extension: use preceding-window feedback to adjust a per-source admission cap rather than rely only on a fixed cap. This is an engineering research question. The implementation does not claim that feedback-driven rate control or fair allocation is novel in general.

The paper makes three limited contributions: (1) a transparent and testable source-cap update rule, (2) a reproducible simulator that compares fixed and feedback-driven caps under four generated workload scenarios, and (3) an implementation study that extends the live adapter with table-based offered/forwarded packet observations and legitimate-service feedback, while distinguishing demonstrated controller behavior from live congestion-control behavior that remains unverified.

## 2. Related Work

DDoS throttling combined with max-min fair resource allocation was studied by Yau et al. [1]. SDN-based detection and mitigation, including protection of the controller and flow-table path, has been studied in FloodDefender [2]. DoSGuard combines monitoring, detection and mitigation in SDN [3]. Dayal and Srivastava compare DDoS mitigation strategies and their effects on legitimate traffic [4]. Recent work on Fractional Fair Shares addresses bandwidth allocation and isolation under volumetric DDoS using a different in-network mechanism [5]. These studies establish that SDN mitigation, traffic rate limiting, feedback/control and fairness during DDoS are active and prior research areas.

The scope of this paper is not to claim first use of any of those broad ideas. The question is whether the specific V2 cap-adjustment rule and its integration into this prototype produce measurable benefits under controlled workloads. A complete state-of-the-art comparison would require implementing or faithfully reproducing additional published baselines; that has not yet been done.

## 3. System Design

### 3.1 Source classification

Each source observation contains packet count, bytes, SYN count, destination-port fan-out and observation duration. The detector assigns a bounded score from packet rate, SYN ratio, port fan-out and bit rate. Simulation labels are used only for evaluation metrics, not as detector input. The live adapter uses the same general rule-based detection approach with its live configuration thresholds; the simulator and live controller configurations are not numerically identical.

### 3.2 Adaptive admission cap

The cap controller maintains per-source state. The simulator configuration and live Mininet configuration are intentionally reported separately because they use different operating scales.

**Simulator configuration.** Each source cap is initially 5 packets/s, with a minimum of 1 packets/s and a maximum of 40 packets/s. Feedback from the preceding observation interval includes normalized capacity utilization \(u\), legitimate-service ratio \(g\) and source meter-drop ratio \(d\). For a suspicious source, congestion is declared when \(u\) is at least 0.90 or \(g\) is below 0.95. Under congestion, the cap is multiplied by 0.75 and bounded below by 1 packets/s. If there is headroom (\(u\) at most 0.75), legitimate service is at least 0.95, and source meter-drop feedback is at least 0.10, the cap is multiplied by 1.20 and bounded above by 40 packets/s. Otherwise the cap is held. After two consecutive benign observations, a reduced stored cap recovers gradually by a factor of 1.20 until it reaches its initial 5 packets/s value.

The simulator computes admitted demand by applying the cap only to suspicious sources, then uses the existing weighted max-min water-filling allocator against a 500-pps bottleneck. The current implementation calls the allocator with equal weights by default.

**Live Mininet configuration.** The live OS-Ken adapter uses an initial suspicious-source cap of 200 packets/s, a minimum of 50 packets/s and a maximum of 1,000 packets/s. Its configured detector thresholds include 300 pps for the packet-rate threshold, 800 pps for the high-rate threshold, destination-port fan-out of 8, 1,000,000 bps and a score threshold of 0.55. The live controller also has a configured capacity parameter of 12,500 pps. The Mininet host-switch links used in the reported experiment were configured at 20 Mbps. These values are experimental settings for this testbed, not generally optimal settings or a measured universal network capacity.

For a suspicious source, the live adapter translates the packet-rate cap into a meter rate using the observed average packet size and installs or modifies an OpenFlow meter. The meter's rate is expressed in kbps. Consequently, the meter rate depends on packet size and byte-accounting semantics; a 200-pps cap does not imply one fixed kbps value for every packet size.

### 3.3 Feedback semantics and live implementation

The `NetworkFeedback` interface accepts three normalized signals in a common data structure: capacity utilization, legitimate-service ratio and source meter-drop ratio. In the simulator, the meter-drop input is an estimated admission-suppression proxy calculated from the difference between offered and admitted demand. The simulator can also supply a legitimate-service ratio, so the complete three-signal cap-adjustment rule can be evaluated offline.

The live adapter collects OpenFlow port-statistics and meter-statistics deltas. Port deltas provide an estimate of egress utilization. Meter deltas provide per-source input packet/byte counts and dropped packet/byte counts, from which a source meter-drop ratio is calculated. For an already-metered source, the live adapter uses meter input deltas as the source observation rather than relying only on post-meter forwarded-flow counts.

The later V2 feedback instrumentation adds low-priority source-observation rules in OpenFlow table 0 and collects flow statistics across all tables. Table 0 source counters are used as offered-packet observations, while table 1 counters are used as forwarded-packet observations through the learning-switch pipeline. Higher-priority source meter rules take precedence over the low-priority observation rules. The receiver host `10.0.0.5` is excluded from legitimate-client service calculations. The controller calculates an aggregate legitimate-service ratio from eligible legitimate-source offered and forwarded counter deltas and makes that feedback available to the adaptive policy.

Controller console excerpts from the development session showed legitimate-service feedback for h2 and h4 at a ratio of 1.000 in observed reporting intervals. Other excerpts showed adaptive relaxation decisions under reported headroom, healthy legitimate service and material meter-drop conditions. These observations demonstrate that the live feedback path can produce service measurements and that the controller has selected relaxation actions. They are not a complete, timestamp-aligned controller record for the archived four-source high-load experiment.

**Live feedback limitation.** The newer live path is no longer accurately described as having no legitimate-service measurement. However, the available excerpts do not establish a complete, synchronized live evaluation of all feedback signals under controlled congestion. In particular, live cap tightening under genuine congestion with trustworthy service feedback has not been conclusively demonstrated. Missing or stale feedback is treated conservatively: it does not imply healthy service, and the policy holds the current cap when required feedback is unavailable.

## 4. Experimental Method

### 4.1 Deterministic simulation

The simulation uses deterministic synthetic source records generated by the V1 workload generator. Four scenarios are evaluated: normal, DDoS-like, flash crowd and mixed. Each experiment has 30 observation windows and a 500-packets/s link capacity. The single-seed illustrative results in Section 5.1 use seed 7. A separate 10-seed paired evaluation is summarized in Section 5.2. The policies are no defense, a fixed 150-pps static threshold, fixed-cap FairShield V1 and feedback-driven FairShield V2. V2 uses the same detector and fairness allocator as V1, but changes the suspicious-source cap using preceding-window feedback. The result CSV/JSON and per-source V2 trace are distributed with the source package.

Metrics include legitimate traffic preservation, policy-level attack-demand mitigation, Jain fairness over legitimate source satisfaction ratios, total delivered packets/s, precision, recall and F1. Attack mitigation measures demand suppressed by the policy before shared-link contention; delivered attack throughput is a separate measure. The detector is held constant across policies, so F1 is expected to remain the same across policy rows.

### 4.2 Live Mininet integration experiment

A single-source UDP experiment was run on a six-host Mininet topology using an OS-Ken controller and OpenFlow 1.3 switch. Host h1 (`10.0.0.1`) sent traffic to receiver h5 (`10.0.0.5`) on UDP port 9000. The sender was configured for a 200-byte payload, a target rate of 1,000 packets/s and a duration of 30 seconds. The sender reported 30,000 datagrams sent, an average of 1,000 pps and an application-payload rate of 1,600 kbps. The host-switch links were configured at 20 Mbps.

The controller reported an offered rate close to 1,000 pps, selected `RATE_LIMIT` with a 200-pps cap and requested an OpenFlow meter at 387 kbps. During sustained traffic, consecutive meter-statistics intervals reported approximately 5,000 input packets and 4,000 dropped packets, corresponding to a drop ratio close to 0.80. The receiver independently reported approximately 200–201 packets/s and 319–320 kbps during the rate-limited intervals. The difference between the meter rate in kbps and the receiver's payload-rate calculation reflects that the meter rate conversion uses the controller's observed average byte count, while the sender/receiver application-rate calculation uses the 200-byte payload size.

At the end of the run, the controller observed a low-rate interval of approximately 52.4 pps, selected `ALLOW` with `benign_observation`, and requested meter removal. This original experiment verifies single-source meter enforcement and subsequent benign-source cleanup; it does not itself validate live feedback-driven cap adaptation.

#### 4.2.1 V2 four-source high-load follow-up

A later four-source UDP run was archived under `outputs/final_archive_20261114/`. The sender configurations and reported packet counts were:

| Host | Role | Target rate | Payload | Sender-reported packets |
|---|---|---:|---:|---:|
| h1 (`10.0.0.1`) | Attack-like | 4,000 pps | 500 bytes | 120,000 |
| h3 (`10.0.0.3`) | Attack-like | 4,000 pps | 500 bytes | 120,000 |
| h2 (`10.0.0.2`) | Legitimate | 100 pps | 1,000 bytes | 3,000 |
| h4 (`10.0.0.4`) | Legitimate | 100 pps | 1,000 bytes | 3,000 |

The sender logs therefore report 246,000 packets offered in total. The archived receiver log contains the following descriptive interval statistics:

| Source | Samples | Mean logged pps | Minimum pps | Maximum pps | Sum of interval packet counts |
|---|---:|---:|---:|---:|---:|
| h1 | 61 | 2,362.8 | 22.9 | 4,002.4 | 144,186 |
| h2 | 62 | 96.1 | 29.8 | 100.8 | 6,000 |
| h3 | 62 | 2,254.2 | 62.7 | 4,001.6 | 140,118 |
| h4 | 62 | 95.9 | 21.9 | 101.0 | 6,000 |

The receiver interval packet sums do not reconcile with sender totals. For example, h2 and h4 each have 6,000 summed receiver interval packets against 3,000 sender-reported packets. These interval sums must not be interpreted as unique delivered datagrams, and the mean rates must not be interpreted as steady-state rates or delivery guarantees. In particular, this run does not establish that h1 and h3 were held to the configured 200-pps cap. The receiver log is retained as descriptive evidence, not as a clean end-to-end delivery measurement.

The controller excerpts showing legitimate-service feedback and cap relaxation were captured during the development session but are not archived as a complete, timestamp-aligned controller log for this four-source run. They therefore should not be attributed to this exact high-load run.

### 4.3 Automated tests

The project test suite completed with 27 tests passing and no failures or errors. The suite covers adaptive-policy behavior, detector scenarios, fairness allocation, simulator behavior, telemetry socket round trips, dashboard API behavior and live SDN policy logic. These automated tests complement, but do not replace, the separate Mininet integration experiment; the test count should not be interpreted as 27 live network experiments.

## 5. Results

### 5.1 Single-seed illustrative simulation results (seed 7)

| Scenario | Policy | Legitimate preserved | Attack mitigated | Jain fairness | Delivered pps |
|---|---|---:|---:|---:|---:|
| DDoS | No defense | 70.24% | 0.00% | 0.9980 | 500.00 |
| DDoS | Static threshold | 99.87% | 100.00% | 1.0000 | 440.17 |
| DDoS | V1 fixed-cap | 98.99% | 99.38% | 1.0000 | 466.27 |
| DDoS | V2 adaptive | 99.50% | 99.80% | 1.0000 | 448.21 |
| Mixed | No defense | 27.35% | 0.00% | 0.8211 | 500.00 |
| Mixed | Static threshold | 35.10% | 100.00% | 0.7143 | 449.17 |
| Mixed | V1 fixed-cap | 36.73% | 99.36% | 0.8266 | 500.00 |
| Mixed | V2 adaptive | 38.44% | 99.83% | 0.8284 | 500.00 |

In the seed-7 DDoS scenario, V2 raises legitimate preservation by about 0.51 percentage points relative to V1 and raises policy-level attack mitigation by about 0.42 percentage points. Total delivered throughput is about 18.06 pps lower, consistent with additional attack-demand suppression. In the seed-7 mixed scenario, legitimate preservation rises by about 1.71 percentage points, mitigation rises by about 0.47 percentage points, fairness rises by about 0.0018 and total throughput remains at capacity. In normal and flash-crowd scenarios, V2 does not adjust traffic because the current detector does not label those generated sources suspicious. The flash-crowd workload remains a difficult capacity condition; V2 is not claimed to solve it.

### 5.2 Ten-seed paired simulation results

| Scenario | Policy | Legitimate preserved (mean ± SD) | Attack mitigated (mean ± SD) | Jain fairness (mean ± SD) | Delivered pps (mean ± SD) |
|---|---|---:|---:|---:|---:|
| DDoS | V1 | 98.77 ± 0.42% | 99.375 ± 0.006% | 0.999972 ± 0.000022 | 469.37 ± 5.02 |
| DDoS | V2 | 99.55 ± 0.28% | 99.808 ± 0.014% | 0.999988 ± 0.000011 | 452.05 ± 5.35 |
| Mixed | V1 | 36.91 ± 0.21% | 99.369 ± 0.007% | 0.826969 ± 0.000909 | 500.00 ± 0.00 |
| Mixed | V2 | 38.63 ± 0.22% | 99.830 ± 0.002% | 0.829037 ± 0.000948 | 500.00 ± 0.00 |

The 10-seed results support the same trade-off seen in the single-seed example: V2 increases legitimate preservation and policy-level attack-demand mitigation, while mean total delivered throughput is lower in the DDoS scenario. The small standard deviations characterize the generated traffic only; they are not confidence intervals for deployment performance. The exact seed identifiers and raw per-seed results should be retained with the experiment artifacts for reproducibility.

### 5.3 Live Mininet results

The original single-source Mininet experiment produced the following observations:

| Measure | Observed result |
|---|---:|
| Sender target rate | 1,000 pps |
| Sender packets | 30,000 in 30 s |
| Application payload size | 200 bytes |
| Sender-reported payload rate | 1,600 kbps |
| Controller-observed offered rate | Approximately 1,000 pps |
| Selected suspicious-source cap | 200 pps |
| Requested OpenFlow meter rate | 387 kbps |
| Meter input per reported interval | Approximately 5,000 packets |
| Meter drops per reported interval | Approximately 4,000 packets |
| Meter drop ratio | Approximately 0.80 |
| Receiver rate while meter active | Approximately 200–201 pps |
| Receiver payload rate while meter active | Approximately 319–320 kbps |
| Later benign observation | 52.4 pps; meter removal requested |

The receiver-side observations independently support enforcement near the configured packet-rate cap in this single-source run. The live evidence establishes meter installation, meter counter collection, rate enforcement at the receiver and meter removal after a subsequent benign observation.

#### 5.3.1 V2 feedback and multi-source evidence

The later V2 controller excerpts showed h2 and h4 legitimate-service feedback at a ratio of 1.000 in observed reporting intervals. Other excerpts showed adaptive relaxation under reported headroom and meter-drop conditions, including h1 cap changes from 200 to 240 and then 288 pps, and h3 from 200 to 240 pps.

These are controller observations from the development session, not a complete synchronized record of the archived four-source run. The four-source sender and receiver logs provide evidence of traffic generation and receiver observations, but their packet totals do not reconcile. They cannot establish exact end-to-end delivery ratios or successful enforcement at a 200-pps cap. Live congestion-driven cap tightening remains unverified.

## 6. Discussion

The simulation results suggest that feedback-driven cap adjustment can preserve slightly more legitimate demand in the generated DDoS and mixed workloads, while suppressing slightly more attack demand. The pure DDoS throughput reduction is an important cost rather than an improvement to hide. The results do not show a higher detector F1 because detection is independent of mitigation in this simulator. The simulator uses simple generated patterns, so perfect F1 in some scenarios should not be interpreted as realistic detection accuracy.

The original live Mininet experiment verifies that the OS-Ken/OpenFlow adapter can install a source meter, collect meter counters and enforce a packet-rate cap at the receiver. The later V2 instrumentation adds table-based offered/forwarded packet observations and a legitimate-service feedback signal. Controller excerpts showed legitimate-service ratios and cap-relaxation decisions under reported headroom conditions. These observations extend the implementation evidence beyond the original single-source enforcement test.

The evidence still has important limits. The available controller excerpts are not fully archived and timestamp-aligned with the four-source sender and receiver logs. The receiver interval packet sums do not reconcile with sender totals, so they cannot support exact packet-delivery claims. The available high-load run does not prove attack-source enforcement at 200 pps. Nor does the current evidence conclusively establish live cap tightening under genuine congestion with complete, trustworthy service feedback. This distinction between an implemented feedback path, observed relaxation decisions and unverified live congestion tightening is central to interpreting the results.

## 7. Limitations and Future Work

1. Validate the semantics and timing of the live legitimate-service measurement under controlled concurrent traffic, including the relationship between table-0 offered counters and table-1 forwarded counters.
2. Validate live cap tightening and relaxation under controlled conditions using synchronized capacity-utilization, legitimate-service and per-source meter-drop measurements. Do not infer successful adaptation solely from meter installation or removal.
3. Repeat multi-source Mininet tests with synchronized sender start/stop times, complete controller logs, receiver-side packet accounting and independently reconciled offered/forwarded packet totals.
4. Compare V1 and V2 under identical captured traffic traces and controlled live link capacity.
5. Retain exact random-seed identifiers and per-seed outputs; expand repeated-seed evaluation and report appropriate paired statistical analyses.
6. Sweep thresholds, cap bounds, multipliers and polling periods.
7. Perform ablation experiments for utilization-only, service-only and meter-feedback-only control.
8. Evaluate against representative, appropriately licensed traffic datasets and more diverse attack patterns.
9. Measure controller overhead, decision latency, flow/meter table usage, goodput and latency.
10. Perform a detailed literature and patent claim search before asserting novelty or pursuing a filing.

## 8. Conclusion

FairShield-SDN V2 implements a feedback-driven adaptive admission-cap rule in an offline simulator and extends a live OS-Ken/OpenFlow 1.3 adapter with table-based offered/forwarded packet observations and legitimate-service feedback. The 10-seed synthetic experiments show modest gains in legitimate traffic preservation and policy-level attack-demand mitigation in DDoS and mixed scenarios, accompanied by lower total delivered throughput in the pure DDoS scenario.

The original live Mininet experiment verified a 200-pps source cap, meter-drop counters, receiver traffic near the configured cap and meter removal after a subsequent benign observation. Later controller excerpts showed legitimate-service feedback and adaptive cap-relaxation decisions under reported headroom conditions. A four-source high-load run was also archived, but its receiver interval packet sums do not reconcile with sender totals and it does not prove enforcement at a 200-pps attack cap. Live congestion-driven cap tightening has not been conclusively validated.

These results establish a working research prototype and preliminary simulation and testbed evidence, but they do not establish production effectiveness, superiority over the state of the art or patent novelty. Further synchronized multi-source experiments, complete controller logging, valid live congestion tests, sensitivity analysis and ablation studies are necessary next steps.

## References

[1] D. K. Y. Yau, J. C. S. Lui, F. Liang and Y. Yam, “Defending Against Distributed Denial-of-Service Attacks With Max-Min Fair Server-Centric Router Throttles,” *IEEE/ACM Transactions on Networking*, 13(1), 2005. DOI: 10.1109/TNET.2004.842221.

[2] S. Gao et al., “Detection and Mitigation of DoS Attacks in Software Defined Networks,” *IEEE/ACM Transactions on Networking*, 28(3), 2020.

[3] “DoSGuard: Mitigating Denial-of-Service Attacks in Software-Defined Networks,” *Sensors*, 22(3), 1061, 2022.

[4] N. Dayal and S. Srivastava, “Analyzing effective mitigation of DDoS attack with software defined networking,” *Computers & Security*, 130, 103269, 2023. DOI: 10.1016/j.cose.2023.103269.

[5] M. Wyss et al., “Lightweight Internet Bandwidth Allocation and Isolation with Fractional Fair Shares,” NDSS 2026. DOI: 10.14722/ndss.2026.240023.

---

**Author and institutional metadata must be completed by the student and supervisor. Check each reference and venue format against the publisher's final version before formal submission.**
