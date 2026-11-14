# FairShield-SDN V2.0.0

**Feedback-driven adaptive admission control for fairness-aware SDN DDoS mitigation.**

V2 is a research extension of the preserved V1 prototype. It adds a stateful adaptive policy engine that adjusts suspicious-source admission caps using preceding-window network feedback, while retaining the interpretable detector and weighted max-min allocator.

> **Scope and validation:** V2 includes a deterministic adaptive simulator and a live OS-Ken/OpenFlow adapter with source-specific offered/forwarded counter collection and legitimate-service feedback. Controller excerpts show service measurements and cap-relaxation decisions under reported headroom conditions. Live congestion-driven cap tightening has not been conclusively validated. Synthetic results, live Mininet measurements and development-session controller observations are reported separately.

## V2 additions

- `src/fairshield/adaptive_policy.py`: stateful feedback-driven source admission controller.
- `src/fairshield/adaptive_simulator.py`: deterministic closed-loop simulator with previous-window feedback.
- `fairshield adaptive-demo`: CLI command to run V2 in one or all traffic scenarios.
- Dashboard mode selector: run V1 baselines or compare the V1 policies with V2 adaptive FairShield.
- `streamlit_app.py`: V2 research dashboard with simulation, archived live evidence and an illustrative adaptive-policy sandbox.
- V2 policy tests for tightening, relaxation, bounded caps, benign recovery, invalid feedback and reproducibility.
- `docs/V2_ADAPTIVE_ALGORITHM.md`: control logic, parameters and limitations.
- `docs/V2_EXPERIMENTS.md`: reproducible setup, metrics and initial V1/V2 comparison.

## Quick start

Python 3.10+ is required. The core simulator and adaptive engine use only the Python standard library.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

Run existing V1 comparisons:

```bash
fairshield demo --windows 30 --seed 7 --capacity 500 --out outputs_v1
```

Run V2 adaptive experiments across all scenarios:

```bash
fairshield adaptive-demo --scenario all --windows 30 --seed 7 --capacity 500 --out outputs_v2
```

Run a single V2 scenario:

```bash
fairshield adaptive-demo --scenario mixed --windows 30 --seed 7 --capacity 500 --out outputs_v2_mixed
```

Start the local browser dashboard:

```bash
fairshield dashboard --host 127.0.0.1 --port 8080
```

Open `http://127.0.0.1:8080`, choose `V2 adaptive feedback`, select a scenario and run the experiment. V2 dashboard values are synthetic simulator output.

### Streamlit research dashboard

Create a separate environment and install the dashboard dependencies:

```bash
python3 -m venv .venv-dashboard
source .venv-dashboard/bin/activate
python -m pip install --upgrade pip
python -m pip install streamlit pandas
```

From the project root, run:

```bash
PYTHONPATH="$PWD/src" streamlit run streamlit_app.py
```

Open `http://localhost:8501`. The adaptive-policy sandbox is illustrative and is not a live controller connection.

Run tests:

```bash
python -m unittest discover -s tests -v
```

Latest recorded verification: **27 tests passed**. These are automated software tests, not 27 live network experiments.

## How V2 works

1. The existing rule-based detector evaluates each source's flow sample.
2. Each source has a stored admission cap, initially 5 pps.
3. Feedback from the preceding observation window is evaluated.
4. The cap tightens when link utilization is at least 90% or legitimate service falls below 95%.
5. The cap relaxes when utilization is at most 75%, legitimate service is at least 95%, and source meter-drop feedback is at least 10%.
6. A benign source gradually recovers its stored cap after two consecutive benign observations.
7. Admitted demands are passed to weighted max-min allocation.

The complete rules and defaults are documented in [`docs/V2_ADAPTIVE_ALGORITHM.md`](docs/V2_ADAPTIVE_ALGORITHM.md). The reproducible comparison is in [`docs/V2_EXPERIMENTS.md`](docs/V2_EXPERIMENTS.md). For evaluation, use [`docs/V2_DEMO_RUNBOOK.md`](docs/V2_DEMO_RUNBOOK.md) and [`docs/V2_VIVA_PREPARATION.md`](docs/V2_VIVA_PREPARATION.md).

## Initial V1/V2 synthetic comparison

| Scenario | Policy | Legitimate preserved | Attack mitigated | Jain fairness |
|---|---|---:|---:|---:|
| DDoS | V1 FairShield | 98.99% | 99.38% | 1.0000 |
| DDoS | V2 adaptive FairShield | 99.50% | 99.80% | 1.0000 |
| Mixed | V1 FairShield | 36.73% | 99.36% | 0.8266 |
| Mixed | V2 adaptive FairShield | 38.44% | 99.83% | 0.8284 |

V2's pure DDoS total delivered throughput is lower than V1 (448.21 versus 466.27 pps), reflecting more aggressive attack suppression. Mixed-scenario delivered throughput is 500 pps for both. These results are synthetic, deterministic, seed 7, 30 windows and capacity 500 pps; they do not establish production performance or superiority over published state of the art.

## Multi-seed robustness run

```bash
python scripts/run_v2_multiseed.py --seeds 1,2,3,4,5,6,7,8,9,10 --windows 30 --capacity 500 --out outputs_v2/multiseed
```

This runs 10 paired seeds across four scenarios and exports raw results and mean/standard-deviation summaries. Results remain synthetic.

## Live SDN validation status

The original single-source Mininet experiment verified source-meter installation, Open vSwitch drop-band counters, meter cleanup and normal UDP delivery after forwarding-state refresh. A 1,000-PPS source was observed near the configured 200-PPS cap while the meter was active.

Later V2 work added low-priority table-0 source-observation rules, table-0 offered-packet counters, table-1 forwarded-packet counters, receiver-host exclusion from legitimate-client feedback, and a legitimate-service ratio supplied to the adaptive policy. Controller excerpts showed legitimate-service measurements and cap-relaxation decisions under reported headroom conditions.

A later four-source high-load run was archived. However, its receiver interval packet totals do not reconcile with sender totals, and a complete timestamp-aligned controller log is unavailable. That run does not establish exact delivery ratios or successful enforcement at the configured 200-PPS cap. Live congestion-driven cap tightening remains unverified.

See [`docs/LIVE_DEMO_EVIDENCE.md`](docs/LIVE_DEMO_EVIDENCE.md) for the evidence and limitations. Do not describe the Streamlit sandbox as live telemetry.

## Project structure

```text
src/fairshield/       V1 and V2 policy, simulator, dashboard and controller
  adaptive_policy.py  V2 stateful adaptive feedback policy
  adaptive_simulator.py V2 closed-loop synthetic evaluation
mininet/              V1 Mininet topology and UDP traffic tools
scripts/              setup, preflight and startup scripts
tests/                V1 and V2 automated tests
outputs/              V1 reference experiment outputs
outputs_v2/           V2 adaptive experiment results and traces
docs/                 V1 docs plus V2 algorithm and evaluation
paper/                V1 research-paper draft for history/reference
```

## Limitations and responsible claims

- Synthetic traffic is not representative real-world packet data.
- Live congestion-driven cap tightening has not been conclusively validated.
- Controller excerpts are not fully timestamp-aligned with the archived four-source sender and receiver logs.
- Four-source receiver totals do not reconcile with sender totals; exact end-to-end delivery percentages must not be inferred.
- No controlled live V1-versus-V2 comparison has been completed under identical workloads.
- Physical link goodput, latency, jitter, controller CPU overhead and rule-installation latency require further measurement.
- Sensitivity analysis, ablation studies and external dataset validation remain future work.
- The project does not claim production readiness, state-of-the-art superiority or patent novelty.

## Version policy

V1.1.0 is preserved as the previous release. V2.0.0 adds a separate adaptive simulation/policy module and does not overwrite V1 source archives. Use Git tags and branches to preserve both versions.
