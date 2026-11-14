# Patent-readiness checklist (preliminary)

## Important

A working academic project does not automatically qualify for a patent. Patentability depends on the precise claims, prior art, inventiveness, subject-matter eligibility, disclosure quality, ownership and filing strategy. This repository is a research prototype, not a patentability opinion or filing-ready application.

## Preliminary prior-art warning

A quick public-web scan found existing work on SDN-based DDoS detection and mitigation, including:

- A patent family describing software-defined behavioral DDoS mitigation with adaptive thresholds and distributed mitigation appliances: https://patents.google.com/patent/US9602535B2/en and https://patents.google.com/patent/US9742800B2/en
- Dynamic rate limiting for mitigating DDoS attacks: https://patents.google.com/patent/US11108813B2/en
- FloodDefender, a published SDN DoS defense architecture: https://doi.org/10.1109/TNET.2020.2983976
- DoSGuard, a monitor/detector/mitigator design for OpenFlow networks: https://pmc.ncbi.nlm.nih.gov/articles/PMC8840592/
- Research comparing SDN DDoS mitigation methods and collateral effects on legitimate traffic: https://doi.org/10.1016/j.cose.2023.103269
- A 2026 paper proposing a three-tier SDN defense using adaptive statistical detection and port-level mitigation: https://www.nature.com/articles/s41598-025-33463-z
- A 2026 PLOS ONE study of DDoS detection/mitigation in SD-WAN that describes sFlow monitoring, OpenFlow rules, meter-based rate limiting, drop rules and time-bounded enforcement: https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0346673
- RADAR-SDN (published 8 September 2026), describing resource-aware adaptive SDN mitigation and cooperative defense: https://jidmis.org/index.php/jidmis/article/view/3215
- A 2026 IEEE paper on dynamic entropy-based SDN DDoS protection with adaptive parameters and OpenFlow meter-table mitigation: https://ieeexplore.ieee.org/abstract/document/11366562
- Earlier work on max-min fair server-centric router throttling for DDoS protection (IEEE/ACM Transactions on Networking, 2005): https://repository.sutd.edu.sg/esploro/outputs/journalArticle/Defending-against-distributed-denial-of-service-attacks-with/9911321709846

Additional related rate-limiting prior art includes US11108813B2, which describes dynamic DDoS rate limiting based on historical traffic. These references do **not** establish that every element of FairShield is known, nor that any claim is unpatentable. They do show that broad claims to “using SDN/ML to detect and mitigate DDoS” or “adaptive DDoS rate limiting” are unlikely to be a strong point of distinction by themselves. A formal search should cover patent databases, academic literature, standards, product documentation and public code.

## What may need to be made genuinely distinctive

The potential contribution should be narrowed to a specific, demonstrable technical mechanism, for example a precise confidence-to-admission mapping combined with a constrained fairness allocator and a measured feedback-driven rule lifecycle. The exact combination must be compared with the complete claims and descriptions in relevant prior art. Merely adding machine learning or calling an approach “fairness-aware” does not establish novelty.

## Work remaining before consulting a patent agent

- [ ] Confirm that the proposed technical features are your own conception and document each human contributor.
- [ ] Perform a structured prior-art search in Indian Patent Advanced Search System (InPASS), WIPO PATENTSCOPE, Espacenet, Google Patents, IEEE Xplore, ACM DL, arXiv and relevant product documentation.
- [ ] Prepare claim charts against the closest prior-art documents.
- [ ] Implement confidence tiers, reversible/time-bounded mitigation, and a measurable feedback loop if those are the features you intend to claim.
- [x] Run an isolated Mininet/Open vSwitch integration test; meter and traffic observations are transcribed in `docs/LIVE_DEMO_EVIDENCE.md`. [ ] Preserve terminal screenshots/pcaps and run controlled repeated baselines.
- [ ] Audit all libraries, datasets, code snippets and licences.
- [ ] Check institutional IP policy, funding terms, contributor agreements and any prior public disclosure.
- [ ] Consult a registered Indian patent agent/attorney before filing or public disclosure.

## India-specific practical note

The Indian Patent Office has published the **Revised Guidelines for Examination of Computer Related Inventions (CRIs), 2025**. The Department of Promotion of Industry and Internal Trade / CGPDTM press release dated 29 July 2025 describes the revised guidance, including a step-wise Section 3(k) assessment framework and examples for AI/ML and other computer-related inventions. The current official IP India guidelines page lists the CRI 2025 document. Review the actual official guideline with a registered Indian patent agent/attorney; this project note is not a legal interpretation. A patent professional should assess the precise technical contribution and complete claims, not just the project title, code volume or presence of ML.

For this prototype, the most important next step is not adding AI for appearance. It is proving a specific technical mechanism that produces a measurable technical effect over credible prior art. The current fixed cap and offline max-min simulator are a useful academic starting point, but they do not by themselves establish patentability.

## Official starting points

- Indian Patent Office CRI guidelines: https://ipindia.gov.in/resource/patents-resources-guidelines
- PIB release on Revised CRI Guidelines 2025 (29 July 2025): https://www.pib.gov.in/PressReleasePage.aspx?PRID=2149719&lang=2&reg=48
- Indian Patent Act, Section 3: https://ipindia.gov.in/acts/patent-act-1970/section-3
- Indian Patent Office basics of patents: https://ipindia.gov.in/pages/patents/learn/basics-of-patents
- WIPO PATENTSCOPE: https://patentscope.wipo.int/
- WIPO patent information: https://www.wipo.int/patents/en/

This checklist is informational and is not legal advice.


## Prototype validation status update

The prototype has now completed a limited live integration test in an isolated Mininet/OVS lab: controller connection, meter creation, drop-band counters, meter cleanup and normal UDP delivery after forwarding-state refresh were observed. This does not establish patentability, distributed DDoS effectiveness, a live baseline comparison or production readiness. The original checklist remains incomplete for raw screenshots/pcaps, repeated baselines, performance measurements and a formal prior-art/claim analysis.
