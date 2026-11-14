"""Closed-loop V2 simulation using previous-window network feedback."""
from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

from .adaptive_policy import AdaptiveFairnessController, NetworkFeedback
from .fairness import jains_fairness
from .models import FlowSample
from .simulator import SCENARIOS, generate_window


@dataclass
class AdaptiveExperimentResult:
    scenario: str
    policy: str
    windows: int
    seed: int
    capacity_pps: float
    legitimate_preservation: float
    attack_mitigation: float
    jain_satisfaction_fairness: float
    delivered_pps: float
    precision: float
    recall: float
    f1: float
    mean_attack_cap_pps: float
    min_attack_cap_pps: float
    max_attack_cap_pps: float
    def to_dict(self) -> dict:
        return asdict(self)


def run_adaptive_experiment(scenario: str, windows: int = 30, seed: int = 7,
                            capacity_pps: float = 500.0) -> tuple[AdaptiveExperimentResult, list[dict]]:
    if scenario not in SCENARIOS:
        raise ValueError(f"unknown scenario {scenario!r}; choose from {SCENARIOS}")
    if windows < 1 or capacity_pps <= 0:
        raise ValueError("windows and capacity_pps must be positive")

    import random
    rng = random.Random(seed)
    controller = AdaptiveFairnessController()
    feedback: dict[str, NetworkFeedback] = {}
    totals = {key: 0.0 for key in ("legit_offered", "legit_delivered", "attack_offered",
                                    "attack_admitted", "delivered")}
    tp = fp = tn = fn = 0
    satisfaction: dict[str, list[float]] = {}
    caps: list[float] = []
    trace: list[dict] = []

    for window in range(windows):
        samples = generate_window(window, scenario, rng)
        decisions = controller.decide(samples, feedback)
        by_ip = {d.src_ip: d for d in decisions}
        window_offered = window_delivered = legit_offered = legit_delivered = 0.0
        next_feedback: dict[str, NetworkFeedback] = {}
        for sample in samples:
            decision = by_ip[sample.src_ip]
            delivered = min(sample.pps, decision.allocated_pps)
            window_offered += sample.pps
            window_delivered += delivered
            actual_attack = sample.label == "attack"
            if actual_attack:
                caps.append(decision.adaptive_cap_pps)
            if actual_attack:
                totals["attack_offered"] += sample.pps
                totals["attack_admitted"] += decision.admitted_pps
                predicted = decision.suspicious
                if predicted: tp += 1
                else: fn += 1
            else:
                legit_offered += sample.pps
                legit_delivered += delivered
                totals["legit_offered"] += sample.pps
                totals["legit_delivered"] += delivered
                satisfaction.setdefault(sample.src_ip, []).append(delivered / max(sample.pps, 1e-9))
                predicted = decision.suspicious
                if predicted: fp += 1
                else: tn += 1
            # This is a simulator-side suppression proxy, not an OVS meter counter.
            estimated_suppression = max(0.0, min(1.0,
                (sample.pps - decision.admitted_pps) / max(sample.pps, 1e-9)))
            trace.append({
                "window": window, "scenario": scenario, "policy": "adaptive_fairshield_v2",
                "src_ip": sample.src_ip, "ground_truth": sample.label,
                "pps": round(sample.pps, 3), "detector_flag": decision.suspicious,
                "detector_score": round(decision.score, 4),
                "adaptive_cap_pps": round(decision.adaptive_cap_pps, 3),
                "adjustment": decision.adjustment,
                "admitted_pps": round(decision.admitted_pps, 3),
                "allocated_pps": round(decision.allocated_pps, 3),
                "delivered_pps": round(delivered, 3),
                "simulated_meter_drop_proxy": round(estimated_suppression, 4),
            })
            next_feedback[sample.src_ip] = NetworkFeedback(
                capacity_utilization=min(1.0, window_delivered / capacity_pps),
                legitimate_service_ratio=(legit_delivered / legit_offered if legit_offered else 1.0),
                source_meter_drop_ratio=estimated_suppression,
            )
        totals["delivered"] += window_delivered
        # Use one global service/utilization reading for all active sources next window,
        # while retaining each source's suppression proxy.
        global_util = min(1.0, window_delivered / capacity_pps)
        legit_ratio = legit_delivered / legit_offered if legit_offered else 1.0
        feedback = {
            ip: NetworkFeedback(global_util, legit_ratio, fb.source_meter_drop_ratio)
            for ip, fb in next_feedback.items()
        }

    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    attack_mitigation = (1.0 - totals["attack_admitted"] / totals["attack_offered"]
                         if totals["attack_offered"] else 0.0)
    result = AdaptiveExperimentResult(
        scenario=scenario, policy="adaptive_fairshield_v2", windows=windows,
        seed=seed, capacity_pps=capacity_pps,
        legitimate_preservation=(totals["legit_delivered"] / totals["legit_offered"]
                                 if totals["legit_offered"] else 1.0),
        attack_mitigation=attack_mitigation,
        jain_satisfaction_fairness=jains_fairness([
            sum(v) / len(v) for v in satisfaction.values() if v
        ]),
        delivered_pps=totals["delivered"] / windows,
        precision=precision, recall=recall, f1=f1,
        mean_attack_cap_pps=sum(caps) / len(caps) if caps else 0.0,
        min_attack_cap_pps=min(caps) if caps else 0.0,
        max_attack_cap_pps=max(caps) if caps else 0.0,
    )
    return result, trace


def run_adaptive_suite(scenarios: Iterable[str] = SCENARIOS, windows: int = 30,
                       seed: int = 7, capacity_pps: float = 500.0):
    results, traces = [], []
    for scenario in scenarios:
        result, trace = run_adaptive_experiment(scenario, windows, seed, capacity_pps)
        results.append(result)
        traces.extend(trace)
    return results, traces


def write_adaptive_outputs(results: list[AdaptiveExperimentResult], trace: list[dict], out_dir: str) -> None:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    records = [r.to_dict() for r in results]
    (out / "adaptive_summary.json").write_text(json.dumps(records, indent=2), encoding="utf-8")
    if records:
        with (out / "adaptive_summary.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(records[0]))
            writer.writeheader(); writer.writerows(records)
    if trace:
        with (out / "adaptive_trace.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(trace[0]))
            writer.writeheader(); writer.writerows(trace)
