from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Iterable

from .controller import FairShieldController
from .detector import RuleBasedDetector
from .fairness import jains_fairness, weighted_max_min
from .models import Decision, FlowSample

SCENARIOS = ("normal", "ddos", "flash_crowd", "mixed")
POLICIES = ("no_defense", "static_threshold", "fairshield")


@dataclass
class ExperimentResult:
    scenario: str
    policy: str
    windows: int
    offered_pps: float
    delivered_pps: float
    legitimate_offered_pps: float
    legitimate_delivered_pps: float
    attack_offered_pps: float
    attack_admitted_pps: float
    attack_delivered_pps: float
    legitimate_preservation: float
    attack_mitigation: float
    jain_satisfaction_fairness: float
    precision: float
    recall: float
    f1: float
    tp: int
    fp: int
    tn: int
    fn: int

    def to_dict(self) -> dict:
        return self.__dict__.copy()


def generate_window(window_id: int, scenario: str, rng: random.Random) -> list[FlowSample]:
    if scenario not in SCENARIOS:
        raise ValueError(f"unknown scenario {scenario!r}; choose from {SCENARIOS}")

    hosts: list[tuple[str, str, float]] = []
    normal_n = 12 if scenario == "normal" else 10
    if scenario == "flash_crowd":
        normal_n = 8
    if scenario == "mixed":
        normal_n = 10
    for i in range(normal_n):
        hosts.append((f"10.0.0.{10+i}", "normal", rng.uniform(25, 65)))

    if scenario in ("ddos", "mixed"):
        for i in range(6):
            hosts.append((f"10.0.1.{10+i}", "attack", rng.uniform(650, 950)))

    if scenario in ("flash_crowd", "mixed"):
        crowd_n = 8 if scenario == "flash_crowd" else 4
        for i in range(crowd_n):
            hosts.append((f"10.0.2.{10+i}", "flash", rng.uniform(175, 235)))

    samples: list[FlowSample] = []
    for src_ip, kind, base_pps in hosts:
        pps = max(1, int(base_pps * rng.uniform(0.88, 1.12)))
        if kind == "attack":
            syn_packets = int(pps * rng.uniform(0.92, 0.99))
            ports = rng.randint(12, 24)
            avg_bytes = rng.randint(60, 160)
            label = "attack"
        elif kind == "flash":
            syn_packets = int(pps * rng.uniform(0.01, 0.07))
            ports = 1
            avg_bytes = rng.randint(650, 1000)
            label = "benign"
        else:
            syn_packets = int(pps * rng.uniform(0.01, 0.08))
            ports = 1
            avg_bytes = rng.randint(500, 1100)
            label = "benign"
        samples.append(FlowSample(
            window_id=window_id,
            src_ip=src_ip,
            dst_ip="10.0.0.100",
            packets=pps,
            byte_count=pps * avg_bytes,
            syn_packets=syn_packets,
            unique_dst_ports=ports,
            duration_s=1.0,
            label=label,
        ))
    return samples


def _metric_ratio(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator > 0 else 1.0


def run_experiment(scenario: str, policy: str, windows: int = 30,
                   seed: int = 7, link_capacity_pps: float = 500.0) -> tuple[ExperimentResult, list[dict]]:
    if policy not in POLICIES:
        raise ValueError(f"unknown policy {policy!r}; choose from {POLICIES}")
    if windows < 1:
        raise ValueError("windows must be at least 1")

    rng = random.Random(seed)
    detector = RuleBasedDetector()
    controller = FairShieldController(link_capacity_pps=link_capacity_pps, detector=detector)
    totals = {k: 0.0 for k in (
        "offered", "delivered", "legit_offered", "legit_delivered",
        "attack_offered", "attack_admitted", "attack_delivered",
    )}
    tp = fp = tn = fn = 0
    satisfaction_by_source: dict[str, list[float]] = {}
    trace: list[dict] = []

    for window in range(windows):
        samples = generate_window(window, scenario, rng)
        detections = {s.src_ip: detector.detect(s) for s in samples}
        if policy == "fairshield":
            decisions = controller.decide(samples)
        else:
            demands: dict[str, float] = {}
            for s in samples:
                if policy == "static_threshold" and s.pps >= 150.0:
                    demands[s.src_ip] = 0.0
                else:
                    demands[s.src_ip] = s.pps
            allocations = weighted_max_min(demands, link_capacity_pps)
            decisions = []
            for s in samples:
                action = "DROP" if demands[s.src_ip] == 0.0 else "ALLOW"
                decisions.append(Decision(
                    src_ip=s.src_ip,
                    action=action,
                    offered_pps=s.pps,
                    admitted_demand_pps=demands[s.src_ip],
                    allocated_pps=allocations[s.src_ip],
                    reason="static threshold >= 150 pps" if action == "DROP" else "no mitigation rule",
                ))

        decision_by_source = {d.src_ip: d for d in decisions}
        for sample in samples:
            d = decision_by_source[sample.src_ip]
            delivered = min(sample.pps, d.allocated_pps)
            totals["offered"] += sample.pps
            totals["delivered"] += delivered
            if sample.label == "attack":
                totals["attack_offered"] += sample.pps
                totals["attack_admitted"] += d.admitted_demand_pps
                totals["attack_delivered"] += delivered
            else:
                totals["legit_offered"] += sample.pps
                totals["legit_delivered"] += delivered
                satisfaction_by_source.setdefault(sample.src_ip, []).append(
                    delivered / max(sample.pps, 1e-9)
                )

            # The detector is evaluated consistently for each policy; F1 is a
            # detector metric, not a property of the allocation baseline.
            predicted = detections[sample.src_ip].suspicious
            actual = sample.label == "attack"
            if predicted and actual:
                tp += 1
            elif predicted and not actual:
                fp += 1
            elif not predicted and actual:
                fn += 1
            else:
                tn += 1

            trace.append({
                "window": window,
                "scenario": scenario,
                "policy": policy,
                "src_ip": sample.src_ip,
                "ground_truth": sample.label,
                "pps": round(sample.pps, 3),
                "syn_ratio": round(sample.syn_ratio, 4),
                "unique_dst_ports": sample.unique_dst_ports,
                "detector_score": round(detections[sample.src_ip].score, 4),
                "detector_flag": detections[sample.src_ip].suspicious,
                "action": d.action,
                "admitted_demand_pps": round(d.admitted_demand_pps, 3),
                "allocated_pps": round(d.allocated_pps, 3),
                "delivered_pps": round(delivered, 3),
            })

    # Detection scores are computed independently of the mitigation policy.
    # In a scenario with no positive class (normal traffic only), precision and
    # recall are reported as 0 rather than misleadingly displaying perfect 1.0.
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)
          if (precision + recall) else 0.0)
    result = ExperimentResult(
        scenario=scenario,
        policy=policy,
        windows=windows,
        offered_pps=totals["offered"] / windows,
        delivered_pps=totals["delivered"] / windows,
        legitimate_offered_pps=totals["legit_offered"] / windows,
        legitimate_delivered_pps=totals["legit_delivered"] / windows,
        attack_offered_pps=totals["attack_offered"] / windows,
        attack_admitted_pps=totals["attack_admitted"] / windows,
        attack_delivered_pps=totals["attack_delivered"] / windows,
        legitimate_preservation=_metric_ratio(totals["legit_delivered"], totals["legit_offered"]),
        # Policy-level suppression is measured before shared-link contention.
        # Delivery loss remains separately visible in attack_delivered_pps.
        attack_mitigation=(1.0 - _metric_ratio(totals["attack_admitted"], totals["attack_offered"])
                           if totals["attack_offered"] > 0 else 0.0),
        jain_satisfaction_fairness=jains_fairness([
            sum(values) / len(values) for values in satisfaction_by_source.values()
        ]),
        precision=precision,
        recall=recall,
        f1=f1,
        tp=tp, fp=fp, tn=tn, fn=fn,
    )
    return result, trace


def run_suite(scenarios: Iterable[str] = SCENARIOS, windows: int = 30,
              seed: int = 7, link_capacity_pps: float = 500.0) -> tuple[list[ExperimentResult], list[dict]]:
    results: list[ExperimentResult] = []
    traces: list[dict] = []
    for scenario in scenarios:
        for policy in POLICIES:
            # Same deterministic seed per scenario makes policy comparisons paired.
            result, trace = run_experiment(
                scenario, policy, windows=windows, seed=seed,
                link_capacity_pps=link_capacity_pps,
            )
            results.append(result)
            traces.extend(trace)
    return results, traces
