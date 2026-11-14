# FairShield-SDN V2.0.0 — Demonstration Runbook

## Demonstration scope

Show V2 adaptive feedback in the offline CLI and browser dashboard. If faculty also request a live switch demonstration, show the existing V1 Mininet/OVS deployment separately and explicitly label it V1. Do not describe V2 adaptive feedback as live OpenFlow behavior in this release.

## A. Prepare environment

```bash
python3 --version
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

## B. Run automated tests

```bash
python -m unittest discover -s tests -v
```

Expected release-environment result: 27 tests pass. Re-run locally; dependency and Python versions may differ.

## C. Run V2 adaptive experiments

```bash
fairshield adaptive-demo --scenario all --windows 30 --seed 7 --capacity 500 --out outputs_v2_demo
```

Explain that this command runs normal, DDoS-like, flash-crowd and mixed synthetic traffic. It writes `adaptive_summary.csv`, `adaptive_summary.json` and `adaptive_trace.csv`.

## D. Run 10-seed comparison

```bash
python scripts/run_v2_multiseed.py --seeds 1,2,3,4,5,6,7,8,9,10 --windows 30 --capacity 500 --out outputs_v2/multiseed_demo
```

This compares no defense, static threshold, V1 fixed-cap FairShield and V2 adaptive FairShield across four generated scenarios.

## E. Start dashboard

```bash
fairshield dashboard --host 127.0.0.1 --port 8080
```

Open `http://127.0.0.1:8080`. Select `V2 adaptive feedback`, choose a scenario, select 30 windows and click Run experiment. Explain that the dashboard runs the synthetic simulator locally.

## F. Optional V1 live deployment demonstration

Use `docs/FACULTY_DEPLOYMENT_GUIDE.md` and `docs/FACULTY_DEMO_CHECKLIST.md`. The previously tested sequence showed:

1. Six Mininet hosts and one OVS switch.
2. Controller connection on OpenFlow TCP 6653.
3. `pingall` connectivity.
4. Normal UDP receiver traffic.
5. High-rate UDP traffic from h1 to h5.
6. V1 source meter installation and OVS drop-band counters.
7. Meter cleanup and normal UDP recovery after forwarding-state refresh.

V1 live meter-drop evidence is recorded in `docs/LIVE_DEMO_EVIDENCE.md`. The 10,515 drop-band packet count out of 47,031 meter-input packets is from the earlier V1 lab run, not a V2 test.

## G. Claims to avoid

- Do not say V2 feedback used real meter counters; it used a simulator suppression proxy.
- Do not say V2 is live-validated on OVS.
- Do not describe synthetic F1=1.0 as real-world detection accuracy.
- Do not claim patent novelty or superiority over state of the art.


## V2 live feedback status — 14 November 2026

The live adapter now collects table-0 offered-packet counters, table-1 forwarded-packet counters, per-source meter-drop feedback and legitimate-service feedback. Controller excerpts showed legitimate-service ratios of 1.000 in observed intervals and cap-relaxation decisions under reported headroom conditions.

The four-source run used h1/h3 at 4,000 PPS with 500-byte payloads and h2/h4 at 100 PPS with 1,000-byte payloads. Receiver means were h1 2,362.8 PPS, h2 96.1 PPS, h3 2,254.2 PPS and h4 95.9 PPS. Receiver interval packet sums do not reconcile with sender totals; these are descriptive log statistics, not delivery ratios. The run does not prove 200-PPS enforcement. Live congestion-driven cap tightening remains unverified.

The Streamlit adaptive-policy sandbox is illustrative, not a live controller connection. The latest recorded automated test run passed 27 tests.
