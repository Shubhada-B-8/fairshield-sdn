# FairShield-SDN: Literature and Prior-Art Comparison

**Prepared:** 12 November 2026
**Basis:** Inspection of the uploaded FairShield-SDN source archive and a preliminary web search of published papers, patent publications, and Indian patent guidance.

> **Scope warning:** This is a preliminary technical literature/prior-art map, not an exhaustive patent search, legal opinion, patentability opinion, or freedom-to-operate analysis. A registered Indian patent agent should conduct a claim-focused search before filing or commercialization.

## 1. What FairShield-SDN currently implements

The inspected implementation contains the following mechanisms:

1. **Offline detector:** an explainable rule score using packet rate, SYN ratio, destination-port fan-out and bit rate.
2. **Live SDN detector:** a separate rule score using packet rate, mean packet size, bit rate and destination-port fan-out. The live adapter sets `syn_packets=0`; therefore it does not actually use SYN-ratio detection.
3. **Admission policy:** demand from suspicious sources is capped before capacity allocation.
4. **Fair allocation:** a water-filling max-min allocator. Its function supports optional weights, but the current simulator and live-policy calls do not pass a weights map, so the current operational allocation is equal-weight max-min.
5. **Live enforcement:** an OS-Ken/Ryu-compatible OpenFlow 1.3 controller installs per-source IPv4 meter rules in OVS table 0. A drop band enforces the rate; table 1 handles learning-switch forwarding.
6. **Recovery:** controller logic requests deletion of the source flow rule and meter when the source is no longer being limited or is considered stale.
7. **Evaluation:** a deterministic synthetic simulator compares no defense, a simple static 150-pps threshold, and FairShield in normal, DDoS, flash-crowd and mixed scenarios.

The live controller uses fixed thresholds and a fixed 1,500-kbit/s attacker cap. It polls table-1 flow statistics every five seconds. The code does not feed OVS meter-drop counters or receiver-side service measurements back into the next allocation decision.

## 2. Closest research comparisons

| Prior work | What it already establishes | Overlap with FairShield | Difference from current FairShield |
|---|---|---|---|
| Yau et al., **“Defending Against Distributed Denial-of-Service Attacks With Max-Min Fair Server-Centric Router Throttles,”** IEEE/ACM ToN, 2005. DOI: 10.1109/TNET.2004.842221 | DDoS traffic throttling plus max-min fair allocation to protect good users. | Strong conceptual overlap with the idea of capping aggressive traffic while sharing constrained capacity fairly. | Server-centric, router-throttle model; it is not the same single-switch SDN/OpenFlow implementation or FairShield’s per-source score. It nevertheless means that “DDoS + max-min fairness” alone is not a novel claim. |
| Gao et al., **“Detection and Mitigation of DoS Attacks in Software Defined Networks” (FloodDefender),** IEEE/ACM ToN, 2020. | SDN/OpenFlow detection and mitigation; packet-in/table-miss protection, filtering and flow-rule management. | SDN controller-based traffic monitoring, attack detection and switch-level mitigation. | Focuses on attacks against SDN control-plane resources and table-miss traffic; FairShield focuses more on source admission and bottleneck bandwidth sharing. |
| **DoSGuard: Mitigating Denial-of-Service Attacks in Software-Defined Networks,** Sensors, 2022, 22(3), 1061. | Monitor/detector/mitigator architecture; OpenFlow message and flow features; SVM-based detection and malicious-host filtering. | Feature-based monitoring, controller-side classification and switch-side mitigation. | DoSGuard focuses on spoofed-source/SDN DoS and blocks malicious hosts; FairShield uses a simple interpretable score and rate-cap/fair-allocation policy. |
| Dayal & Srivastava, **“Analyzing effective mitigation of DDoS attack with software defined networking,”** Computers & Security, 2023, 130, 103269. | Compares dynamic blocking, rate limiting and controller migration, including the effect of mitigation location on legitimate traffic. | Legitimate-user collateral damage and mitigation trade-offs are already established research concerns. | FairShield adds a particular synthetic flash-crowd comparison and a simple admission/fair-share policy; this is not proof of a new general method. |
| Wyss et al., **“Lightweight Internet Bandwidth Allocation and Isolation with Fractional Fair Shares,”** NDSS 2026. DOI: 10.14722/ndss.2026.240023. | Fair bandwidth allocation and isolation during volumetric DDoS; a per-stream fractional fair-share mechanism with packet-carried labels, probabilistic forwarding and security analysis. | Directly overlaps the broad goal of preserving legitimate bandwidth fairness during DDoS. | FFS is a materially different in-network mechanism, not FairShield’s controller-side max-min water-filling and OpenFlow meter approach. It is an important 2026 comparator showing that fairness under DDoS remains active research. |
| Vasudevan et al., **“DDoS Mitigation in Software-Defined Networks” / ADAPT-SDN-Guard,** RMKMATE 2026, DOI: 10.1109/RMKMATE69073.2026.11518631. | Its published abstract describes adaptive polling, multi-view control/data-plane features, temporal convolutional autoencoders with online drift adaptation and closed-loop flow-rule synthesis. | Integrated SDN DDoS detection and automated mitigation. | It describes a substantially more advanced adaptive/ML feedback framework. FairShield currently uses fixed thresholds and a fixed source cap, a five-second polling period, and no online drift adaptation. Comparison is based on the public abstract/metadata; full paper claims have not been independently verified here. |

## 3. Patent documents relevant to the current design

| Patent publication | Publicly described subject matter | Why it matters to FairShield |
|---|---|---|
| **US 9,172,651 B2 / EP 3,105,906 A1**, “Denial of service prevention in a software defined network,” priority date 14 February 2014. | SDN controller receives per-flow rate-limit indicators and configures rate-limiting meters on network elements; the claims include meter placement based on path and meter-slot availability. | Very relevant to the use of SDN/OpenFlow meters for DoS rate limiting. FairShield uses a simpler one-switch, source-specific meter path; it does not implement the patent’s multi-element meter-placement optimization. |
| **US 9,742,800 B2**, “System and method for software defined behavioral DDoS attack mitigation.” | Central controller gathers granular traffic rates and derives adaptive behavioral thresholds/policies for mitigation appliances. | Shows that central-controller behavioral traffic-rate analysis and policy-driven DDoS mitigation were patented concepts before this project. FairShield currently uses fixed thresholds and one OVS switch, not the described distributed appliance architecture. |
| **US 2021/0092153 A1 / US 11,483,341 B2**, “DDoS attack detection and mitigation method for industrial SDN network,” priority 5 February 2018. | Monitors flow counters and Packet-In/Flow-Mod/Packet-Out rates, classifies suspicious traffic, coordinates resource reallocation/mitigation, and removes a dedicated mitigation flow entry after attack conditions return to normal. | Overlap with SDN monitoring, suspicious-flow response, resource handling and removal of mitigation state after attack recovery. Its industrial-network identifiers and cross-domain architecture differ from FairShield. |
| **US 2021/0360024 A1 / US 11,848,959 B2**, “Method for detecting and defending DDoS attack in SDN environment,” priority 13 May 2020. | Uses entropy pre-detection, feature messages, a CART detector and rate-limiting/host-blocking actions. | Shows prior patent work combining SDN traffic features, detection and mitigation. FairShield’s scoring features and max-min admission logic are not the same disclosed algorithm, but broad SDN DDoS claims need careful differentiation. |

Foreign patent publications may be relevant as prior publications to a later Indian novelty assessment, but their existence does not automatically mean they are enforceable in India. Patentability and freedom-to-operate are separate questions and require jurisdiction- and claim-specific review.

## 4. Feature-by-feature novelty assessment

| FairShield feature | Preliminary assessment | Reason |
|---|---|---|
| SDN controller monitors traffic and detects DDoS-like behavior | **Known area** | FloodDefender, DoSGuard and multiple patents already describe controller-side monitoring/detection. |
| Multi-feature threshold/weighted suspicion score | **Known general technique** | Flow rate, flow counts, port behavior, entropy and other features are established in prior work. The exact FairShield coefficients may be a design choice, but no evidence yet shows they are novel or technically superior. |
| Per-source OpenFlow meter with drop band | **Known mechanism** | SDN rate-limiting meter allocation has been described in patent literature since at least the 2014 priority date of EP3105906A1/US9172651. |
| Attacker cap followed by max-min allocation | **Strong conceptual prior art** | DDoS throttling combined with max-min fair allocation was published by Yau et al. in 2005. A different integration into SDN is not automatically inventive. |
| Flash-crowd scenario to test false restrictions | **Useful evaluation choice; not a patentable mechanism by itself** | Benign bursts and legitimate-user impact are known concerns in SDN DDoS research. |
| Automatic removal of mitigation state after traffic normalizes/stales | **Known recovery pattern** | The 2018-priority industrial-SDN patent describes deleting a dedicated mitigation flow entry once attack counters return to normal. |
| Dashboard, CLI, socket lab and project packaging | **Implementation/educational contribution** | Useful for demonstration and reproducibility, but not the core basis for a technical patent claim. |

## 5. What our own experiments actually establish

The saved 30-window, seed-7, 500-pps synthetic run shows:

- **DDoS scenario:** No defense preserved 70.2% of legitimate demand; static threshold preserved 99.9% and suppressed 100% of attack demand; FairShield preserved 99.0% and suppressed 99.4%.
- **Flash crowd:** No defense and FairShield each preserved 25.4%; static threshold preserved 17.1%. FairShield avoids the static threshold’s false blocking, but does not improve on no defense in this particular flash-crowd simulation.
- **Mixed scenario:** No defense preserved 27.3% of legitimate demand, static threshold 35.1%, and FairShield 36.7%. FairShield’s Jain satisfaction fairness was 0.827 versus 0.714 for static threshold and 0.821 for no defense. Static threshold suppressed 100% of attack demand, compared with 99.4% for FairShield.

The simulator’s F1 score is evaluated from the same detector predictions independently of which mitigation policy is selected. Thus the same F1 under all three policies is expected; it does not show that FairShield detects attacks better than the baselines. Perfect F1 in the synthetic DDoS/mixed scenarios reflects the deliberately separable generated feature profiles, not demonstrated real-world detection accuracy.

The live Mininet evidence verifies that a single virtual source generated high-rate UDP traffic, the controller requested a 1,500-kbit/s meter, OVS meter statistics recorded 10,515 drop-band packets out of 47,031 meter-input packets in the observed interval, the meter was later removed, and normal UDP traffic was received again after refreshing forwarding state. This verifies an enforcement path. It is not a multi-source live fairness experiment or a live comparison against no-defense and static-threshold policies.

## 6. What could be presented as the current project contribution?

A defensible current statement is:

> FairShield-SDN is an educational SDN prototype and comparative evaluation of an explainable source-level traffic admission policy. It combines a multi-indicator rule score, suspicious-source demand caps, equal-weight max-min capacity allocation, and source-specific OpenFlow meter enforcement. Its deterministic synthetic experiments examine the trade-off between attack suppression and legitimate traffic preservation, including benign flash-crowd conditions; a Mininet/OVS test demonstrates live meter installation, drop counters, cleanup and subsequent normal traffic delivery.

This is a **system integration and evaluation contribution**. Do not claim that FairShield invented SDN DDoS detection, OpenFlow meter rate limiting, max-min fairness, or fairness-aware DDoS mitigation.

## 7. What would need to change for a stronger research or patent case?

1. **Define one precise technical problem** not already solved by the prior work. Do not rely on a broad claim like “fairness-aware SDN DDoS mitigation.”
2. **Search and compare claim-by-claim** against relevant patent families, especially US9172651/EP3105906, US9742800 and US11483341, as well as relevant Indian national-phase publications.
3. **Design a specific technical mechanism.** For example, investigate a measurable feedback-driven source-admission controller that jointly uses meter-drop telemetry and benign service satisfaction to revise per-source limits under workload shifts. This is only a research direction; it is not in the current code and may itself overlap with other control/feedback literature.
4. **Add baselines and ablations:** detector-only, cap-only, fairness-only, combined FairShield, static threshold, and a relevant published method. Use identical workloads and clearly documented parameters.
5. **Use multiple seeds, capacity levels and confidence intervals.** Include parameter sensitivity for suspicion thresholds, cap rate and polling period.
6. **Use realistic datasets and diverse attacks:** licensed SDN/flow datasets, spoofing/low-rate patterns, multiple simultaneous sources, and benign flash crowds.
7. **Measure system effects:** detection latency, time to install meter, packet loss, legitimate goodput, RTT/latency, controller CPU/memory, flow/meter table occupancy and control-channel load.
8. **Run live multi-source Mininet/OVS trials** and compare no-defense, static threshold and FairShield under the same attack/benign workload. The current live test used one sender and does not validate live fairness among multiple legitimate sources.
9. **Document inventorship and ownership** and consult a registered Indian patent agent before any public disclosure or filing.

## 8. Indian patent-law context

The Indian Patents Act requires an invention to be new, involve an inventive step and be capable of industrial application. IP India's own summary states that novelty is assessed against publications or use anywhere in the world before the filing date. Section 3(k) excludes mathematical or business methods, computer programmes *per se* and algorithms. The Indian Patent Office published the CRI Examination Guidelines 2025; a claim based on software must be assessed for its actual technical contribution and applicable exclusions, not merely described as an algorithm running on a computer.

A preliminary review cannot decide whether any future claim meets these tests. The current combination of known software/networking techniques is at significant risk of being considered obvious or excluded if the claim is framed merely as software logic.

## 9. Sources

### Research papers

1. Yau, D.K.Y., Lui, J.C.S., Liang, F. & Yam, Y. (2005). “Defending Against Distributed Denial-of-Service Attacks With Max-Min Fair Server-Centric Router Throttles.” *IEEE/ACM Transactions on Networking*, 13(1), 29–42. DOI: https://doi.org/10.1109/TNET.2004.842221. Full text: https://www.cse.cuhk.edu.hk/~cslui/PUBLICATION/TON_ddos.pdf
2. Gao, S. et al. (2020). “Detection and Mitigation of DoS Attacks in Software Defined Networks.” *IEEE/ACM Transactions on Networking*, 28(3), 1419 onward. Full text: https://www4.comp.polyu.edu.hk/~shanggao/publications/Detection_and_Mitigation_of_DoS_Attacks_in_Software_Defined_Networks.pdf
3. “DoSGuard: Mitigating Denial-of-Service Attacks in Software-Defined Networks.” *Sensors* (2022), 22(3), 1061. https://www.mdpi.com/1424-8220/22/3/1061
4. Dayal, N. & Srivastava, S. (2023). “Analyzing effective mitigation of DDoS attack with software defined networking.” *Computers & Security*, 130, 103269. DOI: https://doi.org/10.1016/j.cose.2023.103269
5. Wyss, M. et al. (2026). “Lightweight Internet Bandwidth Allocation and Isolation with Fractional Fair Shares.” NDSS 2026. DOI: https://doi.org/10.14722/ndss.2026.240023. https://www.ndss-symposium.org/ndss-paper/lightweight-internet-bandwidth-allocation-and-isolation-with-fractional-fair-shares/
6. Vasudevan, S., Chowdary, N.P. & Chaitanya, M.K. (2026). “DDoS Mitigation in Software-Defined Networks” (ADAPT-SDN-Guard). RMKMATE 2026. DOI: https://doi.org/10.1109/RMKMATE69073.2026.11518631

### Patent documents

1. “Denial of service prevention in a software defined network.” EP3105906A1 / US9172651B2. Google Patents: https://patents.google.com/patent/EP3105906A1/en
2. “System and method for software defined behavioral DDoS attack mitigation.” US9742800B2. Google Patents: https://patents.google.com/patent/US9742800B2/en
3. “DDoS attack detection and mitigation method for industrial SDN network.” US20210092153A1 / US11483341B2. Google Patents: https://patents.google.com/patent/US20210092153A1/en
4. “Method for detecting and defending DDoS attack in SDN environment.” US20210360024A1 / US11848959B2. Google Patents: https://patents.google.com/patent/US20210360024A1/en

### Indian law and guidance

1. IP India, Patents Act, Section 3 (including Section 3(k)): https://ipindia.gov.in/acts/patent-act-1970/section-3
2. IP India, Patents Act, Section 2 (definitions of invention, inventive step and new invention): https://ipindia.gov.in/acts/patent-act-1970/section-2-5
3. IP India, Guidelines for Examination of Computer Related Inventions (CRIs) 2025: https://ipindia.gov.in/frontend/pdf/patents/guidelines/GUIDELINES%20FOR%20EXAMINATION%20OF%20COMPUTER%20RELATED%20INVENTIONS%20%28CRIs%29%20-%202025.pdf
4. IP India, CRI Guidelines resources page: https://www.ipindia.gov.in/resource/patents-resources-guidelines

---

**Bottom line:** FairShield-SDN is a working prototype with a credible implementation/evaluation story. The present implementation does not yet establish a clearly novel patentable mechanism. Its strongest current academic contribution is the transparent integration and comparison of source-level admission, fairness allocation and OpenFlow enforcement, with explicit flash-crowd trade-off analysis. A patent path would require a more precise technical invention, a deeper claim-by-claim search and stronger controlled experiments.


## V2 live feedback status — 14 November 2026

The live adapter now collects table-0 offered-packet counters, table-1 forwarded-packet counters, per-source meter-drop feedback and legitimate-service feedback. Controller excerpts showed legitimate-service ratios of 1.000 in observed intervals and cap-relaxation decisions under reported headroom conditions.

The four-source run used h1/h3 at 4,000 PPS with 500-byte payloads and h2/h4 at 100 PPS with 1,000-byte payloads. Receiver means were h1 2,362.8 PPS, h2 96.1 PPS, h3 2,254.2 PPS and h4 95.9 PPS. Receiver interval packet sums do not reconcile with sender totals; these are descriptive log statistics, not delivery ratios. The run does not prove 200-PPS enforcement. Live congestion-driven cap tightening remains unverified.

The Streamlit adaptive-policy sandbox is illustrative, not a live controller connection. The latest recorded automated test run passed 27 tests.
