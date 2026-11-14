# FairShield-SDN V2.0.0

V2 is a separate project release copied from V1.1.0. The prior V1 archive remains in `releases/`.

New V2 code:
- `src/fairshield/adaptive_policy.py`
- `src/fairshield/adaptive_simulator.py`
- `tests/test_adaptive_policy.py`
- `tests/test_dashboard_v2.py`
- `streamlit_app.py`: Streamlit research dashboard for simulation, archived live evidence, architecture, and adaptive-policy illustration
- Updated `src/fairshield/ryu_app.py`: table-based offered/forwarded counters and legitimate-service feedback instrumentation

Run the V2 simulator:

```bash
python -m fairshield.cli adaptive-demo --scenario all --windows 30 --seed 7 --capacity 500 --out outputs_v2
```

Run tests:

```bash
python -m unittest discover -s tests -v
```

## Current verification status — 14 November 2026

- Python syntax validation passed for the Streamlit app, OS-Ken adapter, adaptive policy, and original dashboard.
- All 27 automated tests passed.
- The original single-source Mininet test demonstrated meter enforcement, drop counters, meter cleanup, and normal traffic recovery after forwarding-state refresh.
- Later controller excerpts demonstrated legitimate-service feedback and cap-relaxation decisions under reported headroom conditions.
- A four-source sender/receiver log archive is included, but receiver packet sums do not reconcile with sender totals.
- Live congestion-driven cap tightening remains unverified.

## Streamlit research dashboard

Install and launch from the project root:

```bash
python3 -m venv .venv-dashboard
source .venv-dashboard/bin/activate
python -m pip install streamlit pandas
PYTHONPATH="$PWD/src" streamlit run streamlit_app.py
```

Open `http://localhost:8501`. The adaptive policy sandbox is illustrative and is not a live controller connection.

See `V2_RELEASE_STATUS.md`, `docs/PROJECT_REPORT.md`, and `docs/LIVE_DEMO_EVIDENCE.md` for exact validation boundaries.
