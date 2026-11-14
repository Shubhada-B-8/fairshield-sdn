# FairShield-SDN — Faculty Demonstration Checklist

Use this page during the evaluation. Tick each item only after it is visibly demonstrated or captured.

## Before the demonstration

- [ ] Laptop connected to power; Ubuntu/WSL opens successfully.
- [ ] Project extracted at `~/projects/fairshield_sdn` (or update all paths to the actual folder).
- [ ] `.venv` exists and dependencies are installed.
- [ ] `./scripts/preflight_sdn_lab.sh` has no failed checks.
- [ ] OVS service is active.
- [ ] No duplicate OS-Ken controller is running.
- [ ] Previous Mininet sessions are closed before running cleanup.
- [ ] Three terminals are ready: controller, Mininet, and OVS inspection.

## Live demonstration checklist

- [ ] Controller starts and reports `FairShield OS-Ken/Ryu adapter started (OpenFlow 1.3)`.
- [ ] Controller listens on TCP port 6653.
- [ ] Mininet lists `c0 h1 h2 h3 h4 h5 h6 s1`.
- [ ] OVS `tcp:127.0.0.1:6653` controller entry reports `is_connected: true`.
- [ ] `pingall` reports 0% dropped (30/30 received).
- [ ] UDP sink on `h5` reports listening at `10.0.0.5:9000`.
- [ ] Normal test sends 1,000 packets at 100 PPS / 800 kbps.
- [ ] Receiver shows approximately 100 PPS / 800 kbps during the normal test.
- [ ] High-rate source runs only inside Mininet at 1,000 PPS for 60 seconds.
- [ ] Controller logs `RATE_LIMIT`, `METER_REQUEST`, and `METER_RULE_REQUEST`.
- [ ] OVS shows a source meter with a drop band around 1,500 kbps.
- [ ] OVS meter stats show a positive drop-band packet count.
- [ ] Controller logs `METER_DELETE_REQUEST` after traffic subsides.
- [ ] OVS meter list is empty after cleanup.
- [ ] Table-0 source meter rule is gone after cleanup.
- [ ] `pingall` refreshes forwarding state before recovery traffic.
- [ ] Recovery UDP sender and receiver show approximately 100 PPS / 800 kbps.

## Screenshots to capture (actual terminal screenshots only)

Create a folder such as `~/fairshield_faculty_evidence/` and save:

1. `01_controller_connected.png` — controller startup and switch connection.
2. `02_mininet_topology_pingall.png` — nodes and 30/30 ping result.
3. `03_normal_udp_baseline.png` — sender and receiver baseline.
4. `04_controller_rate_limit.png` — controller decision and meter request logs.
5. `05_ovs_meter_config.png` — meter drop-band configuration during traffic.
6. `06_ovs_meter_stats.png` — packet-in and drop-band counters during traffic.
7. `07_meter_cleanup.png` — empty meter list after cleanup.
8. `08_udp_recovery.png` — receiver output after forwarding refresh.

Do not create screenshots from retyped terminal transcripts. The previously shared 12 November 2026 outputs are recorded in `LIVE_DEMO_EVIDENCE.md`; they are evidence transcripts, not screenshots.

## What to explain to faculty

- The live SDN adapter uses a transparent source-level heuristic based on packet rate, average packet size, bit rate, and destination-port fan-out.
- The controller requests a per-source OpenFlow meter in OVS; the switch enforces a drop band.
- The live test is one controlled high-rate UDP source in an isolated six-host Mininet topology.
- The offline simulator separately compares no defense, static threshold, and FairShield across normal, DDoS-like, flash-crowd, and mixed synthetic scenarios.
- The live aggregate flow counters do not expose TCP SYN flags; the live adapter is intentionally narrower than the offline detector.
- Normal recovery in the demonstrated sequence was confirmed after running `pingall` to refresh an expired learned forwarding entry.

## Automated test evidence

From the project root after activating `.venv`:

```bash
.venv/bin/python -m unittest discover -s tests -v
```

The latest recorded project validation reports 27 passing automated tests. Rerun this command on the demonstration machine and retain the fresh output. This test count is separate from the live Mininet demonstration.
