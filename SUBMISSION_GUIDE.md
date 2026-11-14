# Final Evaluation Submission Guide — FairShield-SDN V1

## Required deliverables

1. **Complete project + working deployment + GitHub repository** — source is in this repository; follow `docs/FACULTY_DEPLOYMENT_GUIDE.md`; create a private GitHub repo using `GITHUB_PUSH_GUIDE.md`.
2. **Project report** — `docs/FairShield_SDN_Project_Report.docx` and editable `docs/PROJECT_REPORT.md`.
3. **Research paper** — `paper/FairShield_SDN_Research_Paper_Draft.docx` and editable Markdown source. This is a draft for supervisor review, not a claim of novelty or a camera-ready submission.
4. **PPT** — `presentation/FairShield_SDN_Final_Presentation.pptx` with `presentation/SPEAKER_NOTES.md`.

## Faculty demonstration requirement
The faculty demonstration is still pending. Do not mark it complete merely because the isolated lab was previously tested. Rehearse the exact steps in `docs/FACULTY_DEPLOYMENT_GUIDE.md`, follow `docs/FACULTY_DEMO_CHECKLIST.md`, and capture genuine screenshots from the terminals during the faculty demonstration.

## Recommended sequence
1. Preflight the Ubuntu/WSL environment.
2. Demonstrate controller connection, Mininet reachability, normal UDP, high-rate test, OVS meter config/counters, meter cleanup and normal recovery after forwarding refresh.
3. Record faculty comments and any required corrections.
4. Finalize report, research paper and PPT after supervisor review.
5. Push V1 to a private GitHub repository.
6. Keep Version 2 changes in a separate branch/repository.

## Scope and evidence boundaries
Simulator output is synthetic. Live lab evidence is a one-source UDP stress test. The live controller does not use TCP SYN flags. No live no-defense/static-threshold/FairShield benchmark, physical link measurement, latency, jitter, end-to-end loss, or production evaluation is claimed.
