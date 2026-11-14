# FairShield-SDN Architecture

## 1. Goal

FairShield explores a network-control loop for detecting suspicious source traffic, limiting its admitted demand and sharing constrained capacity fairly. The design is intended to reduce attack impact without treating every high-rate burst as malicious.

## 2. Two distinct execution paths

### Offline synthetic path

The simulator generates source-level observations with packet rate, bit rate, SYN ratio, destination-port fan-out and scenario labels used only for evaluation. The rule-based detector does not consume the ground-truth label. The policy caps suspicious demand (the simulator configuration uses a packet-rate cap) and applies weighted max-min allocation. Results are written to CSV/JSON and shown in the dashboard.

### Live SDN path

The OS-Ken-compatible OpenFlow 1.3 adapter polls table-1 flow counters every five seconds. It derives per-source packet/bit rates, mean packet size and destination-port fan-out. Aggregate counters do not expose TCP SYN flags, so the live adapter deliberately uses a separate high-rate/small-packet heuristic rather than claiming to run the richer offline detector.

The live controller sends meter and flow modification messages to Open vSwitch. This was exercised in the isolated six-host Mininet lab on 12 November 2026. See `LIVE_DEMO_EVIDENCE.md` for the exact observed counters and boundaries of the evidence.

## 3. Components

| Component | File | Responsibility |
|---|---|---|
| Data models | `models.py` | Traffic samples and policy result records |
| Offline detector | `detector.py` | Rule-based suspiciousness score using synthetic flow features |
| Fairness allocator | `fairness.py` | Weighted max-min allocation and Jain index |
| Offline controller | `controller.py` | Connects the detector and allocation policy in the simulator path |
| Live policy | `sdn_policy.py` | Live source-level detection, demand cap and allocation |
| OpenFlow adapter | `ryu_app.py` | Flow stats, OpenFlow pipeline, source meters and forwarding |
| Simulator | `simulator.py` | Deterministic synthetic scenarios and policy comparisons |
| Dashboard | `dashboard.py` | Browser UI for offline experiment runs and metrics |
| Reporting | `reporting.py` | CSV/JSON experiment summaries |
| Socket lab | `socket_lab.py` | TCP/UDP telemetry client-server exercise |
| Optional ML | `ml_optional.py` | Synthetic-data Random Forest experiment; optional only |

## 4. OpenFlow pipeline

- **Table 0:** source-specific IPv4 match, meter instruction and `goto_table:1`; a default rule forwards other traffic to table 1.
- **Table 1:** learning-switch forwarding and controller fallback for unknown destinations.
- **Meters:** OpenFlow meter drop bands enforce per-source rate limits. The controller adds, modifies or removes meter rules as source policy changes.

The live lab verified meter creation, switch-side drop-band counters, deletion and subsequent normal UDP delivery after forwarding state was refreshed.


### V2 live feedback instrumentation

The live table-0 pipeline includes low-priority source-observation rules that collect offered-packet counters. Higher-priority source meter rules take precedence for limited sources. Table 1 provides learning-switch forwarding and forwarded-packet counters. The controller combines eligible legitimate-source offered and forwarded deltas to estimate legitimate service, excludes receiver h5 from the legitimate-client set, and uses source meter-band deltas for meter-drop feedback. Missing or stale feedback is not treated as healthy feedback.

The live feedback path has been exercised in Mininet and controller excerpts show service measurements and cap-relaxation actions. A synchronized live congestion-driven tightening test remains outstanding.

## 5. Controller loop

1. Request table-1 flow stats at a five-second interval.
2. Calculate per-source packet and byte deltas from prior counters.
3. Construct live source observations from available aggregate flow statistics.
4. Apply high-rate/small-packet indicators and compute policy result.
5. Cap suspicious source demand using the configured live packet-rate policy (initial attack cap 200 PPS, with configured minimum and maximum bounds); convert the cap into a meter rate using observed packet size.
6. Allocate admitted demand against a configured 10000 kbps policy budget using weighted max-min allocation.
7. Add/modify/remove OpenFlow meter rules and log the decision.

The 10000 kbps value is a policy budget, not a measured physical link capacity. The 1500 kbps meter used in the live test is a configured cap, not a universal threshold.

## 6. Evaluation

The simulator compares no defense, static threshold and FairShield using legitimate preservation, policy-level attack suppression, Jain satisfaction fairness, F1 and delivered PPS. The live Mininet test separately verifies switch integration and meter behavior; it is not a live three-policy comparison.

## 7. Constraints

- Single-switch and single-bottleneck prototype.
- IPv4 source address is the identity key; spoofing, NAT and shared-address complications are not resolved.
- The live adapter has no SYN-flag feature from aggregate flow counters.
- No multi-controller coordination, failover, anti-spoofing, IPv6, deep packet inspection, or production-grade resilience.
- MAC-learning forwarding rules use an idle timeout. In the observed recovery sequence, `pingall` was run after a learned forwarding rule had expired and before normal UDP delivery was rechecked.
- Synthetic simulator results are not production-network measurements.
