# FairShield-SDN: An Explainable Source-Level Admission-Control Prototype for DDoS-Like Traffic in Software-Defined Networks

**Manuscript status:** Research-paper draft for supervisor and project-team review. Not camera-ready and not yet submitted.

**Authors and affiliations:** To be completed and verified by the project team.

## Abstract

Distributed denial-of-service (DDoS) traffic can consume shared network capacity and reduce service available to legitimate users. Mitigation based only on a fixed packet-rate threshold can also restrict benign burst traffic. This paper describes FairShield-SDN, an educational software-defined networking (SDN) prototype that combines interpretable source-level traffic indicators, suspicious-source demand capping, and weighted max-min capacity allocation. The implementation has two distinct evaluation paths. A deterministic Python simulator compares no defense, a static threshold, and FairShield across normal, DDoS-like, flash-crowd, and mixed synthetic traffic. A separate OS-Ken/OpenFlow 1.3 adapter was exercised in a six-host Mininet/Open vSwitch (OVS) lab to verify source-meter installation, switch-side drop-band counters, meter cleanup, and subsequent normal UDP delivery after forwarding-state refresh. In a saved 30-window, seed-7 simulation, FairShield achieved 99.4% policy-level attack-demand mitigation in DDoS-like and mixed scenarios and the highest legitimate preservation and Jain fairness in the mixed scenario. The static threshold performed better on selected DDoS-only metrics and imposed greater collateral restriction in the generated flash-crowd scenario. The live lab observed a 1,500 kbps meter and 10,515 drop-band packets out of 47,031 meter-input packets in one counter snapshot. The results demonstrate a working academic prototype and a transparent evaluation workflow; they do not establish production readiness, real-world detection accuracy, or superiority over state-of-the-art systems.

**Keywords:** Software-defined networking; DDoS mitigation; traffic admission control; weighted max-min fairness; OpenFlow 1.3; Open vSwitch; Mininet.

## 1. Introduction

A shared network bottleneck can become congested when offered traffic exceeds the capacity available to forward it. During a DDoS event, aggressive sources may consume a large part of the available service and reduce throughput for legitimate users. A simple fixed threshold can be easy to implement, but it can also confuse an unusually busy legitimate workload, such as a flash crowd, with attack traffic. This motivates mitigation strategies that consider both attack suppression and the service experienced by legitimate users.

FairShield-SDN is a source-level admission-control prototype built around an SDN controller and an OpenFlow-capable software switch. Its policy first estimates whether a source has suspicious characteristics, limits the admitted demand of sources selected by the policy, and allocates the remaining configured capacity using weighted max-min fairness. This paper documents the implementation and its evaluation rather than claiming a new general-purpose DDoS detection algorithm.

The project deliberately separates an offline simulator from a live SDN adapter. The simulator can use synthetic labels and features that are not exposed by the live switch counters. The live adapter uses aggregate OpenFlow statistics and therefore applies a narrower heuristic. Results from these two paths are reported separately.

## 2. Related Work

Fair bandwidth allocation under DDoS pressure predates SDN. Yau et al. describe max-min fair server-centric router throttles as a mechanism to moderate aggressive packet rates before traffic converges on an overloaded server [1]. This establishes that the combination of DDoS throttling and max-min fairness is not new by itself.

FloodDefender addresses denial-of-service attacks directed at SDN control and data-plane resources. It uses table-miss engineering, packet filtering, and flow-rule management to reduce the impact of table-miss floods on controller communication and switch resources [2]. DoSGuard presents a controller extension composed of monitoring, detection, and mitigation components and uses OpenFlow-related features to identify and filter attack traffic [3]. These systems demonstrate that monitoring, classification, and switch-level mitigation are established SDN defense patterns.

Dayal and Srivastava compare DDoS mitigation approaches and mitigation locations with an emphasis on limiting performance degradation experienced by legitimate users [4]. Their focus reinforces the importance of evaluating collateral effects rather than attack detection alone. More recently, Wyss et al. introduce Fractional Fair Shares, an in-network bandwidth allocation and isolation design evaluated against multiple congestion-control algorithms and volumetric DDoS conditions [5]. Its packet-carried share labels and probabilistic forwarding differ substantially from FairShield's controller-computed allocation and OpenFlow meters, but the work demonstrates that fairness under DDoS remains an active research problem.

Relevant patent publications also describe SDN-based behavioral DDoS mitigation and the allocation or installation of rate-limiting meters. Examples include US9742800B2, which describes a central controller and distributed mitigation components using traffic-derived behavioral thresholds [6], and US9172651B2, which describes controller-directed allocation of rate-limiting meters across SDN network elements [7]. US11848959B2 describes feature-based DDoS detection and control operations in an SDN environment [8]. These records are cited as prior-art context, not as a legal claim about infringement or patentability.

## 3. System Design and Implementation

### 3.1 Architecture

The prototype has an offline path and a live path. In the offline path, a Python simulator creates source-level traffic observations, applies policy variants, and records summaries and per-window traces. In the live path, an OS-Ken-compatible controller communicates with Open vSwitch through OpenFlow 1.3. The six-host Mininet topology provides a repeatable isolated network for testing traffic forwarding and meter enforcement.

### 3.2 Offline traffic features and detector

The offline detector uses packet rate, SYN ratio, destination-port fan-out, and bit rate. It combines feature checks into an interpretable suspicion score and compares the score with a configured threshold. Ground-truth scenario labels are used to compute evaluation metrics, not as detector inputs. The generated traffic features are deliberately separable; therefore, high F1 values in these synthetic experiments should not be interpreted as expected accuracy on operational traffic.

### 3.3 Admission and fairness policy

For sources classified as suspicious, the simulator caps admitted demand before allocating the shared capacity. The remaining admitted demand is assigned using weighted max-min allocation. Jain's index is computed over legitimate sources' delivered/offered satisfaction ratios. In the current simulator configuration, the baseline comparisons use the supplied policy parameters and equal source weights unless a different weight is explicitly configured.

### 3.4 Live OpenFlow enforcement

The live adapter polls OpenFlow table-1 flow counters at five-second intervals and derives per-source packet rate, bit rate, average packet size, and destination-port fan-out. It does not observe TCP SYN flags from the aggregate counters used in this implementation. The live heuristic can classify a high-rate, small-packet source and request a source-specific OpenFlow meter with a drop band. A table-0 source rule applies the meter and then continues to table 1, where MAC-learning forwarding is performed. Meter add/modify/remove requests are logged.

The demonstrated lab configuration used a 1,500 kbps meter rate for the detected source and a configured 10,000 kbps policy budget. The latter is a policy parameter, not a measured physical link capacity.

## 4. Experimental Methodology

### 4.1 Offline simulation

The reproducibility run used random seed 7, 30 windows, and a configured bottleneck capacity of 500 packets per second. Four synthetic scenarios were evaluated: normal traffic, DDoS-like traffic, flash crowd, and mixed traffic. Three policies were compared: no defense, a fixed 150 packets-per-second static threshold, and FairShield. The same generated traffic sequence was used for policies within each scenario and seed.

Metrics include legitimate traffic preservation, policy-level attack-demand mitigation, Jain satisfaction fairness, precision, recall, F1, and modeled delivered packets per second. Policy-level attack mitigation is calculated before bottleneck contention and is not end-to-end packet loss.

### 4.2 Live Mininet/OVS experiment

The live experiment used Ubuntu on WSL, Mininet 2.3.0, Open vSwitch 2.17.12, and OS-Ken with OpenFlow 1.3. Six hosts (h1-h6) were connected through switch s1. The controller listened on TCP port 6653. Baseline and recovery UDP traffic used 100 packets per second with 1,000-byte payloads for 10 seconds. The attack-like stress test used one source, h1, configured for 1,000 packets per second, 200-byte payloads, and a 60-second duration. This is a single-source high-rate test, not a distributed multi-source DDoS experiment.

## 5. Results

### 5.1 Synthetic policy comparison

Table 1 summarizes the key results from the saved seed-7, 30-window CSV. Values are percentages except throughput.

| Scenario | Policy | Legitimate preserved | Attack mitigated | Jain fairness | Delivered PPS |
|---|---|---:|---:|---:|---:|
| DDoS-like | No defense | 70.2 | 0.0 | 0.998 | 500.00 |
| DDoS-like | Static threshold | 99.9 | 100.0 | 1.000 | 440.17 |
| DDoS-like | FairShield | 99.0 | 99.4 | 1.000 | 466.27 |
| Flash crowd | No defense | 25.4 | N/A | 0.694 | 500.00 |
| Flash crowd | Static threshold | 17.1 | N/A | 0.500 | 335.57 |
| Flash crowd | FairShield | 25.4 | N/A | 0.694 | 500.00 |
| Mixed | No defense | 27.3 | 0.0 | 0.821 | 500.00 |
| Mixed | Static threshold | 35.1 | 100.0 | 0.714 | 449.17 |
| Mixed | FairShield | 36.7 | 99.4 | 0.827 | 500.00 |

In the DDoS-like scenario, the static threshold slightly exceeded FairShield on legitimate preservation and policy-level attack mitigation in this particular generated run. FairShield nevertheless mitigated 99.4% of attack demand and delivered more modeled throughput than the static baseline. In the flash-crowd scenario, the static threshold reduced legitimate preservation from 25.4% to 17.1% and fairness from 0.694 to 0.500. FairShield matched no defense in this generated flash-crowd case, so it avoided that static-threshold collateral restriction. In the mixed scenario, FairShield achieved the highest legitimate preservation (36.7%) and fairness (0.827) among the compared policies while mitigating 99.4% of attack demand.

The F1 score was 1.0 for the DDoS-like and mixed synthetic scenarios because generated attack and benign feature profiles are deliberately separable. It is not evidence of real-world classifier accuracy.

### 5.2 Live switch observations

The controller connected to OVS at `tcp:127.0.0.1:6653`, and the six-host `pingall` test reported 0% packet loss across 30/30 reachability checks. The normal UDP sender reported 1,000 packets, 100 PPS, and 800 kbps; receiver logs showed approximately 100 PPS and 800 kbps.

During the high-rate test, the controller classified source 10.0.0.1 as RATE_LIMIT with a score of 0.90. Representative observed rates were approximately 1.77-1.94 Mbps, and the admitted rate was 1,500 kbps. OVS reported meter 1 with a drop band of 1,500 kbps and burst size 150. One statistics snapshot reported 47,031 packets and 11,381,502 bytes entering the meter, with 10,515 packets and 2,544,630 bytes counted by the drop band. The packet ratio is approximately 22.36% for that snapshot; it is not end-to-end packet loss.

After the traffic test, the controller logged a meter-deletion request. Subsequent OVS inspection showed no configured meter and no source-specific table-0 meter rule. A learned table-1 forwarding entry with a 60-second idle timeout had expired during the gap. Running `pingall` refreshed the forwarding state, after which normal UDP delivery was again observed at approximately 100 PPS and 800 kbps. This demonstrates post-refresh delivery, not autonomous immediate recovery without forwarding-state refresh.

## 6. Discussion

The results illustrate a trade-off rather than universal superiority. A static threshold can be very effective against a strongly separable synthetic attack profile but can also restrict high-rate legitimate bursts. FairShield's source classification and demand-capping design reduces this specific false-positive effect in the generated flash-crowd and mixed scenarios. However, the policy is fixed-rule based, the attacker cap is configured rather than learned, and the simulator does not model the full complexity of a physical network.

The live test is valuable because it demonstrates that the controller's policy can result in real OpenFlow meter configuration and nonzero switch-side drop counters. It does not establish that FairShield outperforms existing systems, scales to a large topology, handles spoofed distributed sources, or protects production networks.

## 7. Limitations and Threats to Validity

The synthetic traffic generator may create feature distributions that are easier to separate than real traffic. One random seed and 30 windows are insufficient to support broad statistical claims. The live test used one UDP source and did not implement a controlled live comparison among no-defense, static-threshold, and FairShield policies. No physical link capacity, end-to-end packet-loss rate, latency, jitter, controller CPU load, flow-table pressure, or meter installation latency was measured. The live detector does not use SYN flags. The live configuration uses fixed thresholds and a fixed 1,500 kbps cap. The recovery test required a forwarding-state refresh with `pingall` after a learned rule expired. Optional Random Forest code uses synthetic data and is not validated on a representative real-world dataset.

## 8. Conclusion and Future Work

This paper documented FairShield-SDN V1, an explainable source-level admission-control prototype with a deterministic synthetic simulator and a separately tested OpenFlow enforcement adapter. The simulator results show trade-offs among attack suppression, legitimate preservation, fairness and throughput. The Mininet/OVS test verified controller connectivity, source-meter installation, switch-side drop-band activity, meter cleanup, and subsequent normal UDP delivery after forwarding refresh.

Future evaluation should include multiple sources, repeated random seeds, a controlled live comparison against no-defense and static-threshold baselines, ablation of individual detection features, sensitivity analysis, and measurements of end-to-end throughput, latency, jitter, loss, CPU use, flow-table pressure, and rule-installation delay. Any adaptive feedback controller should be treated as a separate V2 research branch until implemented and independently evaluated. A systematic patent search and institutional IP review are also required before any novelty or patentability claim is made.

## References

[1] D. K. Y. Yau, J. C. S. Lui, F. Liang, and Y. Yam, “Defending against distributed denial-of-service attacks with max-min fair server-centric router throttles,” in *Proc. 10th IEEE International Workshop on Quality of Service (IWQoS)*, 2002, pp. 35-44, doi: 10.1109/IWQoS.2002.1006572.

[2] S. Gao, Z. Peng, B. Xiao, A. Hu, Y. Song, and K. Ren, “FloodDefender: Protecting data and control plane resources under SDN-aimed DoS attacks,” in *Proc. IEEE INFOCOM*, 2017, doi: 10.1109/INFOCOM.2017.8057009.

[3] J. Li, T. Tu, Y. Li, S. Qin, Y. Shi, and Q. Wen, “DoSGuard: Mitigating Denial-of-Service Attacks in Software-Defined Networks,” *Sensors*, vol. 22, no. 3, art. 1061, 2022, doi: 10.3390/s22031061.

[4] N. Dayal and S. Srivastava, “Analyzing effective mitigation of DDoS attack with software defined networking,” *Computers & Security*, vol. 130, art. 103269, 2023, doi: 10.1016/j.cose.2023.103269.

[5] M. Wyss, Y.-C. Hu, V. Lenders, R. Meier, and A. Perrig, “Lightweight Internet bandwidth allocation and isolation with Fractional Fair Shares,” in *Proc. Network and Distributed System Security Symposium (NDSS)*, 2026, doi: 10.14722/ndss.2026.240023.

[6] H. K. Jain, “System and method for software defined behavioral DDoS attack mitigation,” U.S. Patent US9742800B2, 2017.

[7] “Denial of service prevention in a software defined network,” U.S. Patent US9172651B2, 2015.

[8] D. Zhang, K. Liu, J. Dong, Y. Zhao, and R. Zhao, “Method for detecting and defending DDoS attack in SDN environment,” U.S. Patent US11848959B2, 2023.
