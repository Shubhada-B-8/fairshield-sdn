from __future__ import annotations

import csv
import json
from pathlib import Path
from .simulator import ExperimentResult


def write_outputs(results: list[ExperimentResult], traces: list[dict], out_dir: str | Path) -> None:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    with (out / "summary.json").open("w", encoding="utf-8") as f:
        json.dump([r.to_dict() for r in results], f, indent=2)
    if traces:
        with (out / "traffic_trace.csv").open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(traces[0].keys()))
            writer.writeheader()
            writer.writerows(traces)
    with (out / "summary.csv").open("w", newline="", encoding="utf-8") as f:
        rows = [r.to_dict() for r in results]
        if rows:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
