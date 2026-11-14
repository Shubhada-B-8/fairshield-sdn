# Live Adaptive Rate-Limiting Experiment

## Environment
- Project: FairShield-SDN V2
- Controller: OS-Ken / OpenFlow 1.3
- Topology: Mininet, switch s1
- Sender: h1 (10.0.0.1)
- Receiver: h5 (10.0.0.5)

## Traffic configuration
- Protocol: UDP
- Destination port: 9000
- Payload size: 200 bytes
- Target sending rate: 1,000 packets/second
- Duration: 30 seconds
- Packets sent: 30,000
- Sender-reported average rate: 1,000 PPS
- Sender-reported offered bandwidth: 1,600 Kbps

## Controller observations
- Detected source: 10.0.0.1
- Offered rate: approximately 1,000 PPS
- Adaptive cap: 200 PPS
- Initial OpenFlow meter rate: 387 Kbps
- Meter input: approximately 5,000 packets per reporting interval
- Meter drops: approximately 4,000 packets per reporting interval
- Observed meter drop ratio: approximately 0.80
- Controller later observed a benign rate of 52.4 PPS and removed the meter.

## Receiver-side verification
During rate limiting, h5 reported approximately:
- 200–201 packets per second
- 319–320 Kbps

This independently confirms that the receiver's sustained traffic rate was close to the configured 200 PPS cap.

## Interpretation
The live experiment demonstrates high-rate source detection, adaptive policy selection, dynamic OpenFlow meter installation, meter-drop telemetry, receiver-side rate enforcement, and meter removal after a benign observation.

## Limitations
- Simultaneous legitimate-user and attack traffic fairness was not tested in this experiment.
- Legitimate-service recovery was not measured.
- Adaptive cap relaxation based on measured legitimate-service feedback was not demonstrated.
- Results are from this Mininet test configuration and should not be generalized to production networks.

## Verification status
Live rate-limiting experiment: PASS.
Evidence sources: sender output, controller logs, and receiver log.
