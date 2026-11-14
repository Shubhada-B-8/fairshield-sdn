# FairShield-SDN — Live Mininet / Open vSwitch Demo Evidence

**Evidence date:** 12 November 2026
**Environment:** Ubuntu on WSL, Mininet 2.3.0, Open vSwitch 2.17.12, OS-Ken / OpenFlow 1.3
**Scope:** Isolated six-host Mininet lab. The high-rate test used one UDP source (`h1`, 10.0.0.1); it is a controlled attack-like stress test, not a distributed real-world DDoS event.

> Evidence note: The values below are transcribed from terminal output shared during the live demonstration. No raw terminal screenshot or pcap was collected in that session, so this file is a structured transcript, not a claim that image artifacts were captured.

## 1. Environment and connectivity

- Controller process ran as PID `12398` and listened on TCP port `6653`.
- Open vSwitch controller entry `tcp:127.0.0.1:6653` reported `is_connected: true` and state `ACTIVE`.
- Mininet nodes: `c0 h1 h2 h3 h4 h5 h6 s1`.
- `pingall` completed with `0% dropped (30/30 received)`.
- Open vSwitch version reported: `2.17.12`.

## 2. Normal UDP baseline

Command executed from the Mininet prompt:

```bash
h1 python3 /home/shubhada/projects/fairshield_sdn/mininet/udp_traffic.py send --dst 10.0.0.5 --port 9000 --pps 100 --duration 10 --size 1000
```

Sender output:

```text
sent=1000 average_pps=100.0 average_kbps=800.0
```

Receiver log samples included approximately 100 packets/s and 800 kbps, for example:

```text
received=100 pps=100.0 kbps=799.9
received=101 pps=100.0 kbps=800.1
received=100 pps=100.0 kbps=800.0
```

This confirms normal UDP delivery during the baseline interval.

## 3. High-rate attack-like traffic and controller decision

A bounded sender was launched from `h1` to the sink on `h5` with the following configuration:

```bash
h1 python3 /home/shubhada/projects/fairshield_sdn/mininet/udp_traffic.py send --dst 10.0.0.5 --port 9000 --pps 1000 --duration 60 --size 200
```

The controller log reported source `10.0.0.1` repeatedly classified as `RATE_LIMIT`. Representative observations:

- Score: `0.90`.
- Packet rate: approximately `915–1002 pps`.
- Observed bit rate: approximately `1.77–1.94 Mbps`.
- Mean packet size reported by flow counters: approximately `242 bytes`.
- Admitted and allocated rate: `1500.0 kbps`.
- Reasons included high packet rate, small mean packet size, and high bit rate.

The controller logged the following requests:

```text
METER_REQUEST action=ADD source=10.0.0.1 meter_id=1 rate=1500 kbps
METER_RULE_REQUEST source=10.0.0.1 meter_id=1 table=0 priority=40000
...
METER_DELETE_REQUEST source=10.0.0.1 meter_id=1
```

## 4. OpenFlow meter configuration and counters

Open vSwitch meter configuration:

```text
meter=1 kbps burst bands=
type=drop rate=1500 burst_size=150
```

Meter statistics captured during the high-rate interval:

| Counter | Value |
|---|---:|
| Meter ID | 1 |
| Meter duration | 47.031 s |
| Packets entering meter | 47,031 |
| Bytes entering meter | 11,381,502 |
| Drop-band packets | 10,515 |
| Drop-band bytes | 2,544,630 |

The drop-band packet counter is approximately **22.36%** of the packets counted as entering the meter in that statistics snapshot. This ratio describes the meter counters for that observation only; it is not an end-to-end packet-loss rate and must not be reported as such.

## 5. Meter cleanup

After the controller requested deletion:

- `dump-meters s1` returned an empty meter configuration list.
- `dump-flows s1 table=0` showed only the default `priority=0 actions=goto_table:1` rule; the source-specific meter rule was no longer present.

A table-1 forwarding entry had an `idle_timeout=60`. At one point after the test, the normal UDP forwarding entry had expired and only the controller fallback remained. Running `pingall` refreshed forwarding/learning state; the subsequent recovery test delivered traffic successfully. Therefore, describe recovery as **verified after forwarding-state refresh**, not as a fully autonomous immediate restoration guarantee.

## 6. Normal UDP recovery after cleanup

After meter cleanup and a successful `pingall`, the same 100 PPS / 1000-byte UDP test was run again.

Sender output:

```text
sent=1000 average_pps=100.0 average_kbps=800.0
```

Receiver log showed sustained values around 100 PPS and 800 kbps, including:

```text
received=100 pps=100.0 kbps=799.8
received=101 pps=100.0 kbps=800.1
received=100 pps=100.0 kbps=800.0
received=100 pps=100.0 kbps=800.0
```

This verifies successful normal UDP delivery after the meter was removed and forwarding state refreshed.

## 7. What this live evidence proves — and does not prove

**Supported by the observed lab output:**

1. The OS-Ken controller connected to the OVS switch through OpenFlow 1.3.
2. The six-host Mininet topology had full ping reachability.
3. Normal UDP traffic reached the sink at approximately the configured rate.
4. The live controller classified the high-rate source as `RATE_LIMIT` and requested a 1500 kbps meter.
5. OVS reported meter input counters and drop-band counters greater than zero.
6. The meter and source-specific table-0 rule were absent after cleanup.
7. Normal UDP traffic reached the sink again after a forwarding-state refresh.

**Not established by this live test:**

- Multi-source distributed DDoS resistance; only one high-rate UDP source was used in this particular test.
- A live controlled comparison against no-defense and static-threshold baselines.
- End-to-end packet-loss, latency, jitter, physical-link goodput, or controller CPU impact.
- A live controller `ALLOW` log for the recovery interval.
- Production readiness or generalization to real Internet traffic.

## 8. Recommended evidence screenshots for the final presentation

For a later rehearsal, capture these directly from the actual terminals:

1. `nodes`, `pingall`, and `ovs-vsctl list Controller` showing `is_connected: true`.
2. Controller `RATE_LIMIT` and `METER_REQUEST` lines.
3. `ovs-ofctl -O OpenFlow13 dump-meters s1` while the attack is active.
4. `ovs-ofctl -O OpenFlow13 meter-stats s1` while the attack is active.
5. `dump-meters` after cleanup showing no configured meters.
6. Receiver output after the post-cleanup normal test.

Do not fabricate screenshots from the transcript. Keep these as a follow-up capture task if visual evidence is required by the evaluator.

---

## 9. V2 follow-up validation — 14 November 2026

This section records additional implementation and experiment evidence collected after the original 12 November demonstration. It supplements the earlier single-source meter experiment; it does not replace it.

### 9.1 Four-source traffic experiment

Four UDP senders were used in the archived high-load traffic run. The sender logs are stored under `outputs/final_archive_20261114/`.

| Host | Role in experiment | Target rate | Payload | Packets sent | Sender-reported bandwidth |
|---|---|---:|---:|---:|---:|
| h1 (10.0.0.1) | Attack-like | 4,000 PPS | 500 bytes | 120,000 | 16,000 Kbps |
| h3 (10.0.0.3) | Attack-like | 4,000 PPS | 500 bytes | 120,000 | 16,000 Kbps |
| h2 (10.0.0.2) | Legitimate | 100 PPS | 1,000 bytes | 3,000 | 800 Kbps |
| h4 (10.0.0.4) | Legitimate | 100 PPS | 1,000 bytes | 3,000 | 800 Kbps |

The four sender logs therefore report 246,000 packets offered in total. These are sender-side counts and are not equivalent to packets delivered at the receiver.

### 9.2 Receiver-side log summary

The archived receiver log contains per-source interval observations. The following values are descriptive summaries calculated from all matching `SOURCE` records in that file.

| Source | Log samples | Mean logged PPS | Minimum logged PPS | Maximum logged PPS | Sum of interval packet counts |
|---|---:|---:|---:|---:|---:|
| h1 (10.0.0.1) | 61 | 2,362.8 | 22.9 | 4,002.4 | 144,186 |
| h2 (10.0.0.2) | 62 | 96.1 | 29.8 | 100.8 | 6,000 |
| h3 (10.0.0.3) | 62 | 2,254.2 | 62.7 | 4,001.6 | 140,118 |
| h4 (10.0.0.4) | 62 | 95.9 | 21.9 | 101.0 | 6,000 |

**Interpretation and data-quality limitation:** The receiver log contains more interval observations and accumulated packet counts than can be reconciled directly with the individual sender totals. In particular, the h2 and h4 receiver sums are 6,000 each, while their respective sender logs report 3,000 packets each. The complete receiver log is therefore not a clean, run-aligned packet-delivery record for this experiment.

The receiver means are descriptive log statistics, not proof of a steady-state rate or an end-to-end delivery ratio. The attack-source observations also do not demonstrate enforcement at a 200 PPS cap. No per-source delivery percentage should be calculated from these aggregate totals.

### 9.3 Live legitimate-service feedback instrumentation

The V2 controller was extended to collect source-specific offered and forwarded packet counters:

- Low-priority source-observation rules are installed in OpenFlow table 0.
- Higher-priority source meter rules take precedence over the observation rules.
- A flow-statistics request collects counters from all tables.
- Table 0 counters are used to estimate offered packets.
- Table 1 counters are used to estimate packets forwarded through the learning-switch pipeline.
- The receiver host h5 (10.0.0.5) is excluded from legitimate-client service calculations.

For eligible legitimate sources, the controller calculates:

\[
\text{Legitimate service ratio}
=
\frac{\text{forwarded packets}}{\text{offered packets}}
\]

Controller console excerpts captured during the development session showed h2 and h4 legitimate-service feedback at a ratio of 1.000 in the observed reporting intervals.

This demonstrates that the controller's feedback path can produce legitimate-service measurements in the lab. The excerpts are not archived as a complete controller log aligned by timestamp with the four sender logs above.

### 9.4 Adaptive cap feedback observations

Previously shared controller console excerpts showed adaptive relaxation decisions when the logged conditions indicated available capacity, legitimate service at or above its target, and material source-meter drops.

Examples included:
- h1 cap increasing from 200 to 240 PPS, then to 288 PPS.
- h3 cap increasing from 200 to 240 PPS.
- A logged legitimate-service ratio of 1.000 and low reported utilization during relaxation observations.

These are controller console observations from the development session. They should not be presented as measurements from the archived four-source high-load run because a complete, timestamp-aligned controller log for that run is not included in the archive.

**Important limitation:** A valid live demonstration of adaptive cap tightening under genuine congestion, with trustworthy and complete legitimate-service feedback, has not been conclusively established. An earlier startup observation with incomplete or zero legitimate-service data produced a misleading tightening event and is not accepted as evidence of successful congestion control.

### 9.5 Software verification

The latest recorded software verification before the final archive included:

- 27 automated unit tests passing.
- Python syntax compilation of the live controller and adaptive-policy modules.
- A successful OS-Ken controller startup using OpenFlow 1.3.
- A six-host Mininet topology used for live traffic experiments.

Automated test success demonstrates software-level checks; it does not independently establish the correctness of every live OpenFlow event-handler or congestion-control behavior.

### 9.6 Updated evidence boundaries

The combined V2 evidence supports the following claims:

1. The original single-source Mininet test demonstrated live source detection, meter installation, meter-drop counters, meter removal, and normal UDP recovery after forwarding-state refresh.
2. The later V2 controller includes table-based offered/forwarded counter collection and legitimate-service feedback.
3. Controller console excerpts demonstrated legitimate-service feedback and adaptive cap relaxation under the reported headroom conditions.
4. Four-source sender and receiver logs were preserved for further analysis.
5. The saved four-source receiver log is not sufficiently aligned with sender totals to support exact end-to-end delivery percentages.
6. Live congestion-driven adaptive cap tightening has not been conclusively validated.
7. The synthetic simulator results remain separate from all live Mininet measurements.

The project remains an educational research prototype. The live results do not establish production readiness or generalization to real Internet traffic.
