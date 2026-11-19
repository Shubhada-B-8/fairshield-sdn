# FairShield-SDN V3 — Experimental Results

## 1. Environment
- SDN controller: OS-Ken / OpenFlow 1.3
- Switch: Open vSwitch 2.17.12
- Network emulator: Mininet
- Topology: 6 hosts connected to 1 switch
- AI mode: Shadow mode
- Enforcement: Existing V2 adaptive controller

## 2. Connectivity
- Ping test: 30/30 packets received
- Packet loss: 0%

## 3. Normal UDP Experiment
- Source: h2 (10.0.0.2)
- Destination: h5 (10.0.0.5)
- Configured rate: 5 Mbps
- Sender throughput: 5.24 Mbps
- Receiver throughput: 5.25 Mbps
- Packet loss: 0%

## 4. High-Rate UDP Experiment
- Source: h2 (10.0.0.2)
- Destination: h5 (10.0.0.5)
- Configured rate: 50 Mbps
- Sender throughput: 52.4 Mbps
- Receiver throughput: 39.4 Mbps
- Packet loss: 25%
- Jitter: 1.031 ms

## 5. AI Shadow Detection
- Live traffic samples were processed by the V3 AI adapter.
- Example AI attack probability: 0.269
- V2 rule detector flagged high-rate traffic.
- AI remained in shadow mode and did not control enforcement.

## 6. Adaptive Meter Enforcement
- Source: 10.0.0.2
- Meter ID: 1
- Requested meter rate: 2419 kbps
- First reported interval: 20,214 packets, 19,287 dropped.
- Second reported interval: 21,756 packets, 20,779 dropped.
- Approximate drop ratios: 95.4% and 95.5%.

## 7. Controller Fix
- Meter flow cleanup changed to OFPFC_DELETE_STRICT.
- Deletion restricted to priority 40000.
- Priority-100 source observer rule was verified to persist.

## 8. Software Testing
- Full pytest suite: 50 passed.
- Test duration: 17.05 seconds.

## 9. Limitations
- AI model training uses synthetic data.
- AI operates in shadow mode.
- Real-world attack detection accuracy has not been established.
- Mininet throughput measurements are virtual-emulation results.
