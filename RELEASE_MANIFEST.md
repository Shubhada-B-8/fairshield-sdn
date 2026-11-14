# FairShield-SDN V2.0.0 Release Manifest

This is a V2 research-prototype release based on V1.1.0. The original V1.1.0 complete release archive is preserved at `releases/FairShield_SDN_V1.1.0_Complete_Release.zip`.

## V2 additions
- `src/fairshield/adaptive_policy.py`
- `src/fairshield/adaptive_simulator.py`
- V2 CLI command `adaptive-demo`
- V1/V2 mode in the local dashboard
- `tests/test_adaptive_policy.py`
- `tests/test_dashboard_v2.py`
- `docs/V2_ADAPTIVE_ALGORITHM.md`
- `docs/V2_EXPERIMENTS.md`
- `outputs_v2/` deterministic synthetic results
- V2 project report, research drafts (Markdown and Word), Streamlit research dashboard, presentation and speaker notes
- Updated live Mininet evidence and archived four-source sender/receiver logs
- GitHub and submission guides

## Validation boundary
The offline adaptive policy is tested through the deterministic simulator and automated tests. The live OS-Ken adapter includes table-0 offered counters, table-1 forwarded counters, source meter feedback, and legitimate-service feedback. Controller excerpts show service measurements and cap-relaxation decisions under reported headroom conditions. The archived four-source receiver totals do not reconcile with sender totals, and live congestion-driven cap tightening remains unverified.
