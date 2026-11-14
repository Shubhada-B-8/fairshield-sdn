# FairShield-SDN V2.0.0 — Submission Guide

## Included deliverables

- Complete Python source package with V1 baseline modules and V2 adaptive modules.
- V1.1.0 complete release ZIP preserved under `releases/`.
- V2 project report: `docs/FairShield_SDN_V2_Project_Report.docx`.
- V2 research-paper draft: `paper/FairShield_SDN_V2_Research_Paper_Draft.docx` and `.md`.
- V2 presentation and speaker notes under `presentation/`.
- V2 adaptive algorithm and experiments under `docs/`.
- Deterministic results and traces under `outputs_v2/`.
- Mininet/OVS V1 topology and deployment documentation.

## Required before formal academic submission

1. Add the student's name, institution, department, supervisor and date to the report and paper.
2. Verify reference metadata and the required institutional citation format.
3. Run V2 simulation and tests on the final extracted folder.
4. Demonstrate V1 live deployment to faculty, as previously tested.
5. Explain that V2 includes live feedback instrumentation and observed cap-relaxation decisions, but clearly state that live congestion-driven cap tightening remains unverified.
6. Obtain supervisor approval for report, paper and disclosure timing.
7. Confirm institution IP ownership rules before making repository or paper public.

## Version distinction

V1.1.0 remains preserved as the earlier release. V2.0.0 adds the adaptive policy and simulator and extends the live adapter with table-based offered/forwarded counters and legitimate-service feedback. V2 live controller observations are preliminary and do not establish congestion-driven cap tightening or production readiness.
