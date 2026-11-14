# Changelog

## 2.0.0 - 2026-11-13

### Added
- Stateful feedback-driven adaptive admission policy in `adaptive_policy.py`.
- Per-source bounded cap state with congestion tightening, headroom/drop-feedback relaxation and gradual benign recovery.
- Previous-window feedback simulator in `adaptive_simulator.py`.
- `fairshield adaptive-demo` command for all scenarios or one selected scenario.
- Dashboard mode selector for V1 baseline comparison and V2 adaptive feedback.
- V2 tests for tightening, relaxation, cap bounds, benign recovery, input validation and deterministic simulation.
- V2 algorithm and experimental evaluation documentation.

### Validation
- Latest recorded verification on 14 November 2026: 27 automated unit tests passed.
- Python compile check passed.
- Four-scenario V2 simulation completed at seed 7, 30 windows, 500 pps capacity.

### Important scope note
- V2 adaptive policy behavior is evaluated in the deterministic simulator; the live feedback path is documented separately below.
- Follow-up live work added table-based offered/forwarded counters, source meter feedback and legitimate-service feedback to the OS-Ken adapter.
- Simulation values are synthetic and not production network measurements.


### V2 live feedback follow-up — 14 November 2026

- Added low-priority table-0 source-observation counters and table-1 forwarded counters.
- Added receiver-host exclusion and legitimate-service feedback to the live adaptive controller.
- Controller excerpts showed service measurements and cap-relaxation decisions under reported headroom conditions.
- Archived a four-source high-load run; receiver interval totals do not reconcile with sender totals.
- Live congestion-driven cap tightening remains unverified.
- Updated research reports, Word and Markdown drafts, Streamlit dashboard and submission evidence.
- Latest recorded automated test result: 27 tests passed.

## 1.1.0
- Preserved source-level traffic policy, Mininet/OVS live adapter, offline simulator, dashboard, experiment outputs and documentation from V1.1.0.
