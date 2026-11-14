# FairShield-SDN V2 Presentation Speaker Notes

1. Introduce FairShield-SDN as an SDN DDoS research prototype, not a production appliance.
2. Explain the bottleneck problem and the danger of static thresholds during flash crowds.
3. Summarize V1 components and identify V2 as a separate adaptive policy extension.
4. Explain that feedback is one interval delayed and affects the next cap decision.
5. Read the tightening, relaxation and benign recovery conditions; emphasize bounds.
6. State seed 7, 30 windows, 500 pps and synthetic workload assumptions.
7. Discuss DDoS preservation/mitigation improvement and throughput trade-off.
8. Discuss mixed-scenario preservation/fairness improvement without claiming statistical significance.
9. Walk through the numerical table.
10. Show CLI and dashboard mode selector if the demo environment is ready.
11. Clearly distinguish V1 live evidence from V2 simulator validation.
12. List multi-seed, ablation, live meter feedback and multi-source Mininet as next work.
13. Conclude with the limited prototype contribution and invite questions.

Do not say that V2 adaptive feedback was verified live on OVS. It was not.
