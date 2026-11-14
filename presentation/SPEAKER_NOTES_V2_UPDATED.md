# FairShield-SDN V2 — Speaker Notes

**Status date:** 14 November 2026

## Project overview
FairShield-SDN is an academic SDN research prototype combining an interpretable source detector, suspicious-source admission caps, weighted max-min allocation and OpenFlow meter enforcement. V2 adds a stateful adaptive admission policy driven by preceding-window feedback.

## Adaptive policy
The simulator tightens suspicious-source caps when utilization is at least 90% or legitimate service falls below 95%. It relaxes caps when utilization is at most 75%, legitimate service is at least 95%, and source meter-drop feedback is at least 10%. Missing feedback causes the controller to hold its current cap. Benign recovery is gradual.

## Synthetic results
The ten-seed paired simulation shows higher mean legitimate preservation and policy-level attack-demand mitigation for V2 in DDoS and mixed scenarios. Pure-DDoS delivered throughput is lower for V2; this is a trade-off, not a result to hide. All these figures are synthetic.

## Live evidence
The original single-source Mininet experiment verified a 200-PPS cap, meter-drop counters, meter cleanup and normal UDP recovery after forwarding-state refresh. Later V2 changes added table-0 offered counters, table-1 forwarded counters, meter feedback and legitimate-service feedback. Controller excerpts showed service measurements and cap-relaxation decisions under reported headroom conditions.

## Limitations
The four-source receiver interval totals do not reconcile with sender totals. Controller excerpts are not a complete timestamp-aligned record for that run. It does not establish exact delivery percentages or successful 200-PPS enforcement. Live congestion-driven cap tightening remains unverified. The Streamlit policy sandbox is illustrative, not a live controller connection.

## Demo sequence
1. Introduce the problem and architecture.
2. Explain detection, adaptive caps and max-min allocation.
3. Run the V1/V2 synthetic comparison.
4. Explain the ten-seed results and pure-DDoS throughput trade-off.
5. Show archived Mininet evidence and its limitations.
6. Demonstrate the illustrative adaptive-policy sandbox.
7. Close with 27 passing automated tests and remaining validation work.
