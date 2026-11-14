# Speaker notes — FairShield-SDN presentation

## Slide 1 — Title
Introduce FairShield as an educational SDN research prototype. It includes an offline simulator and a separate live OpenFlow enforcement path.

## Slide 2 — Problem
Explain that network overload harms legitimate users. A fixed threshold can mistake a flash crowd for an attack.

## Slide 3 — Approach
Detection estimates suspiciousness, admission control caps suspicious demand, and weighted max-min allocation shares the remaining configured budget. The live adapter turns allocations into OVS meters.

## Slide 4 — Architecture
Walk from traffic inputs through detector and policy to the OpenFlow controller and switch. Evaluation outputs are separate from live network counters.

## Slide 5 — Offline setup
State seed 7, 30 windows, 500 PPS configured capacity, four synthetic scenarios and three policies. Stress that these are generated flows.

## Slide 6 — Legitimate preservation
Static threshold is particularly harmful in the generated flash-crowd case (17.1% preservation). FairShield matches no defense at 25.4% there. It is not perfect: congestion still reduces preservation.

## Slide 7 — Mitigation and fairness
Static threshold is stronger on some DDoS-only metrics. FairShield has the best saved mixed-scenario preservation and Jain fairness. Avoid claiming FairShield wins every scenario.

## Slide 8 — Dashboard
This is a browser UI for offline synthetic simulation. The screenshot's 99.0%, 99.4%, 1.00 and 1.00 values describe the displayed FairShield result in that DDoS-like experiment, not live traffic.

## Slide 9 — Live topology
Show OS-Ken, OVS and Mininet. The tested topology had h1-h6, s1 and a UDP sink at h5. Controller OpenFlow port was 6653.

## Slide 10 — Live meter evidence
Explain source 10.0.0.1 received RATE_LIMIT with score .90 and a 1500 kbps cap. OVS meter 1's drop band counted 10,515 packets out of 47,031 meter-input packets in a 47.031-second snapshot. This is not end-to-end loss.

## Slide 11 — Cleanup and recovery
Controller requested meter deletion. OVS later showed no meter. The table-1 learned UDP rule expired; we ran pingall to refresh forwarding state, then normal UDP receiver traffic returned at around 100 PPS / 800 kbps. State this sequence exactly.

## Slide 12 — Verification boundaries
16 tests passed. Live single-source meter enforcement was demonstrated. No live multi-source DDoS, live three-policy benchmark, physical link capacity or production performance has been established.

## Slide 13 — Conclusion
FairShield is a working prototype and a basis for further experiments. Next research tasks are repeated multi-source tests, live baseline comparisons, pcap/screenshot collection and measurements of latency, loss, CPU and flow-table use.
