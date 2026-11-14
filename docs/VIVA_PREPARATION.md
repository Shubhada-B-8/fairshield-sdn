# FairShield-SDN — Viva Preparation (Beginner-Friendly)

## Core questions

**1. What is FairShield-SDN?**
It is a research prototype that detects suspicious traffic patterns, caps the admitted rate of suspicious sources, and allocates remaining configured network capacity using weighted max-min fairness. It includes a simulator and a separate live SDN adapter.

**2. What is DDoS?**
A Distributed Denial of Service attack attempts to make a service unavailable by overwhelming it with traffic from multiple sources. Our live demonstration used one controlled high-rate source; it is attack-like stress traffic, not a distributed attack.

**3. What is SDN?**
Software-Defined Networking separates the control logic from packet forwarding. A controller makes policy decisions; switches forward packets and enforce rules.

**4. What are control plane and data plane?**
The control plane decides what should happen. The data plane forwards packets and applies rules. In our lab, OS-Ken is the controller and Open vSwitch is the data-plane switch.

**5. What is OpenFlow?**
OpenFlow is a southbound protocol that lets an SDN controller configure flow tables and meters on a compatible switch. Our lab used OpenFlow 1.3.

**6. Why use Mininet?**
Mininet creates virtual hosts, switches and links in a Linux environment so we can test network behavior without physical switches.

**7. What is Open vSwitch?**
It is a software switch that forwards network packets and supports OpenFlow rules and meters.

**8. What is OS-Ken?**
It is an SDN controller framework compatible with the Ryu application model. Our application runs as an OS-Ken controller app.

**9. How does the detector work?**
The offline detector uses rule-based indicators such as packet rate, SYN ratio, destination-port fan-out and bit rate. The live adapter uses the features available from aggregate OpenFlow counters: packet rate, mean packet size, bit rate and destination-port fan-out.

**10. Why are there two different detectors?**
Standard aggregate OpenFlow flow counters do not reveal TCP SYN flags. Therefore the live adapter uses a narrower heuristic and must not be described as running the richer offline detector.

**11. What is PPS?**
Packets per second: the number of packets observed or transmitted in one second.

**12. What is a meter in OpenFlow?**
A meter measures traffic against a configured rate and can apply a band action. Our lab used a drop band at 1500 kbps for the suspicious source.

**13. What does RATE_LIMIT mean?**
The policy decided that the source's admitted rate should be lower than its offered rate. In the live test, the controller capped the source at 1500 kbps.

**14. What is weighted max-min fairness?**
It allocates a shared resource progressively among active sources according to weights, without giving a source more than its admitted demand. Unused demand can leave capacity available for other sources.

**15. What is Jain's fairness index?**
It is a metric for how evenly a resource is shared. A value closer to 1 indicates more equal satisfaction across the measured users.

**16. What is a flash crowd?**
A sudden increase in legitimate users accessing a service. A good detector should avoid labelling every high-rate burst as malicious.

**17. What are the three comparison policies?**
No defense, a fixed static threshold and FairShield. They are compared in the offline simulator.

**18. Are your experiment numbers real network measurements?**
No. The three-policy comparison values are synthetic simulator results. The live Mininet tests provide separate evidence of controller connection, meter configuration, drop-band counters, cleanup and UDP delivery.

**19. What did the live test prove?**
The controller connected using OpenFlow 1.3, Mininet hosts communicated, the controller classified one high-rate source as RATE_LIMIT, OVS installed a 1500 kbps meter, the meter recorded drop-band packets, the meter was removed, and normal UDP delivery was observed again after forwarding state was refreshed.

**20. What does 10,515 dropped packets mean?**
It is the drop-band packet counter from one OVS meter statistics snapshot. The meter had 47,031 packets counted as inputs in that snapshot. Their ratio is about 22.36%, but that is not the end-to-end network packet-loss rate.

**21. Why did we run pingall before recovery?**
The learned table-1 UDP forwarding rule had an idle timeout of 60 seconds and was no longer present after the gap. `pingall` refreshed forwarding/learning state; then normal UDP packets reached the receiver again.

**22. What is the main limitation?**
We have not run a controlled three-policy live comparison or a multi-source live DDoS benchmark. We also have not measured physical-link capacity, latency, CPU impact or end-to-end loss.

**23. Why is F1 = 1.0 in the synthetic DDoS scenario?**
The simulated attack and benign features are deliberately separable in the generated dataset. It does not imply 100% accuracy on real network traffic.

**24. Is the prototype production ready?**
No. It is a single-switch educational prototype. It does not include production-grade failover, spoofing defense, multi-controller coordination, IPv6, or hardened resilience.

**25. What would you do next?**
Run multi-source live tests, compare no-defense/static/FairShield under identical live traffic, collect packet captures and screenshots, measure throughput/latency/loss/CPU/rule installation overhead, and repeat experiments across seeds and parameter settings.

## 30-second project explanation

“FairShield-SDN is an SDN research prototype for DDoS-like traffic management. It uses traffic indicators to identify suspicious sources, caps their admitted demand, and allocates the remaining configured capacity using weighted max-min fairness. We compared three policies in a deterministic synthetic simulator across normal, DDoS-like, flash-crowd and mixed scenarios. We also connected an OS-Ken controller to an Open vSwitch switch in Mininet and verified a live OpenFlow meter, drop-band counters, meter cleanup and normal UDP delivery after forwarding refresh. The results are promising for an academic prototype, but live multi-source benchmarking and production-level evaluation remain future work.”
