"""V3 AI-assisted, QoS-aware 5G-style simulation.

QoS and radio-related values are synthetic simulation proxies, not
measurements from a live 5G RAN or physical network.
"""
from __future__ import annotations

import csv
import json
import random
from dataclasses import asdict, dataclass
from pathlib import Path

from .fairness import jains_fairness, weighted_max_min
from .simulator import SCENARIOS, generate_window
from .v3_ai import AIRiskDetector


@dataclass
class V3Result:
    scenario: str
    policy: str
    windows: int
    seed: int
    capacity_pps: float
    legitimate_preservation: float
    attack_mitigation: float
    jain_fairness: float
    delivered_pps: float
    detection_precision: float
    detection_recall: float
    detection_f1: float
    mean_latency_ms: float
    p95_latency_ms: float
    mean_jitter_ms: float
    packet_loss_ratio: float
    throughput_mbps: float
    connection_reliability: float
    mean_utilization: float
    mean_ai_risk: float
    policy_filtered_pps: float
    congestion_dropped_pps: float
    delivered_bytes: float

    def to_dict(self):
        return asdict(self)


def run_v3_experiment(
    scenario="ddos",
    windows=30,
    seed=7,
    capacity_pps=500.0,
    detector=None,
    flash_weight=1.5,
):
    if scenario not in SCENARIOS:
        raise ValueError(
            f"unknown scenario {scenario!r}; choose from {SCENARIOS}"
        )
    if windows < 1 or capacity_pps <= 0 or flash_weight <= 0:
        raise ValueError("windows, capacity_pps and flash_weight must be positive")

    rng = random.Random(seed)
    detector = detector or AIRiskDetector.train_synthetic(seed=41)

    totals = {
        "legit_offered": 0.0,
        "legit_delivered": 0.0,
        "attack_offered": 0.0,
        "attack_admitted": 0.0,
        "offered": 0.0,
        "admitted": 0.0,
        "delivered": 0.0,
        "policy_filtered": 0.0,
        "congestion_dropped": 0.0,
        "delivered_bytes": 0.0,
        "elapsed_seconds": 0.0,
    }

    tp = fp = fn = 0
    fairness_by_source = {}
    latency_by_window = []
    jitter_by_window = []
    loss_by_window = []
    reliability_by_window = []
    utilization_by_window = []
    risk_values = []
    trace = []

    for window in range(windows):
        samples = generate_window(window, scenario, rng)
        window_total_offered = sum(s.pps for s in samples)

        predictions = {
            s.src_ip: detector.predict(s, window_total_offered)
            for s in samples
        }

                # AI-positive sources are restricted to a maximum of 5 PPS.
        # Service-aware weights prioritize bursty legitimate traffic.
        demands = {}
        allocation_weights = {}

        for s in samples:
            flagged, risk = predictions[s.src_ip]

            demands[s.src_ip] = min(s.pps, 5.0) if flagged else s.pps
            risk_values.append(risk)

            if flagged:
                allocation_weights[s.src_ip] = 0.25
            elif s.service_class == "bursty":
               allocation_weights[s.src_ip] = flash_weight
            else:
                allocation_weights[s.src_ip] = 1.0

        allocations = weighted_max_min(
            demands,
            capacity_pps,
            allocation_weights,
        )
        # First calculate the complete window's traffic accounting.
        window_admitted = 0.0
        window_delivered = 0.0
        window_policy_filtered = 0.0
        window_congestion_dropped = 0.0
        window_delivered_bytes = 0.0
        window_duration = max((s.duration_s for s in samples), default=1.0)

        source_values = []

        for s in samples:
            flagged, risk = predictions[s.src_ip]
            admitted = demands[s.src_ip]
            delivered = min(admitted, allocations[s.src_ip])

            policy_filtered = max(0.0, s.pps - admitted)
            congestion_dropped = max(0.0, admitted - delivered)

            # Convert the delivered packet rate into delivered bytes using
            # this source's actual average packet size and duration.
            delivered_bytes = (
                delivered * s.duration_s * s.avg_packet_bytes
            )

            window_admitted += admitted
            window_delivered += delivered
            window_policy_filtered += policy_filtered
            window_congestion_dropped += congestion_dropped
            window_delivered_bytes += delivered_bytes

            totals["offered"] += s.pps
            totals["admitted"] += admitted
            totals["delivered"] += delivered
            totals["policy_filtered"] += policy_filtered
            totals["congestion_dropped"] += congestion_dropped
            totals["delivered_bytes"] += delivered_bytes

            actual_attack = s.label == "attack"

            if actual_attack:
                totals["attack_offered"] += s.pps
                totals["attack_admitted"] += admitted
                if flagged:
                    tp += 1
                else:
                    fn += 1
            else:
                totals["legit_offered"] += s.pps
                totals["legit_delivered"] += delivered
                if flagged:
                    fp += 1

                fairness_by_source.setdefault(s.src_ip, []).append(
                    delivered / max(s.pps, 1e-9)
                )

            source_values.append({
                "sample": s,
                "flagged": flagged,
                "risk": risk,
                "admitted": admitted,
                "delivered": delivered,
                "policy_filtered": policy_filtered,
                "congestion_dropped": congestion_dropped,
            })

        totals["elapsed_seconds"] += window_duration

        # Calculate QoS once per complete window, not cumulatively per source.
        utilization = min(1.0, window_delivered / capacity_pps)
        queue_pressure = max(
            0.0, (window_admitted - capacity_pps) / capacity_pps
        )

        # These are illustrative synthetic queueing proxies, not a calibrated
        # physical network or 5G latency model.
        latency_ms = max(
            4.0,
            8.0
            + 34.0 * queue_pressure
            + 12.0 * utilization
            + rng.uniform(-1.5, 1.5),
        )
        jitter_ms = max(
            0.1,
            0.8
            + 3.5 * queue_pressure
            + rng.uniform(0.0, 0.8),
        )

        # This ratio measures congestion-related unmet admitted demand only.
        # AI policy filtering is recorded separately.
        window_loss_ratio = (
            window_congestion_dropped / window_admitted
            if window_admitted > 0
            else 0.0
        )
        window_reliability = max(0.0, min(1.0, 1.0 - window_loss_ratio))

        latency_by_window.append(latency_ms)
        jitter_by_window.append(jitter_ms)
        loss_by_window.append(window_loss_ratio)
        reliability_by_window.append(window_reliability)
        utilization_by_window.append(utilization)

        # Keep one trace row per source, with window-level QoS values repeated
        # so every source row can be interpreted in its window context.
        for item in source_values:
            s = item["sample"]
            admitted = item["admitted"]
            delivered = item["delivered"]
            congestion_dropped = item["congestion_dropped"]

            source_loss_ratio = (
                congestion_dropped / admitted if admitted > 0 else 0.0
            )
            source_reliability = 1.0 - source_loss_ratio

            trace.append({
                "window": window,
                "scenario": scenario,
                "src_ip": s.src_ip,
                "ground_truth": s.label,
                "offered_pps": round(s.pps, 3),
                "ai_attack_probability": round(item["risk"], 5),
                "ai_flag": item["flagged"],
                "admitted_pps": round(admitted, 3),
                "policy_filtered_pps": round(item["policy_filtered"], 3),
                "allocated_pps": round(allocations[s.src_ip], 3),
                "delivered_pps": round(delivered, 3),
                "congestion_dropped_pps": round(congestion_dropped, 3),
                "delivered_bytes_per_window": round(
                    delivered * s.duration_s * s.avg_packet_bytes, 3
                ),
                "latency_ms_synthetic": round(latency_ms, 3),
                "jitter_ms_synthetic": round(jitter_ms, 3),
                "packet_loss_ratio_synthetic": round(source_loss_ratio, 5),
                "connection_reliability_synthetic": round(
                    source_reliability, 5
                ),
                "window_congestion_drop_ratio_synthetic": round(
                    window_loss_ratio, 5
                ),
                "utilization_ratio": round(utilization, 5),
            })

    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision + recall
        else 0.0
    )

    attack_mitigation = (
        1.0 - totals["attack_admitted"] / totals["attack_offered"]
        if totals["attack_offered"]
        else 0.0
    )
    legitimate_preservation = (
        totals["legit_delivered"] / totals["legit_offered"]
        if totals["legit_offered"]
        else 1.0
    )

    result = V3Result(
        scenario=scenario,
        policy="fairshield_v3_ai_5g_sim",
        windows=windows,
        seed=seed,
        capacity_pps=capacity_pps,
        legitimate_preservation=legitimate_preservation,
        attack_mitigation=attack_mitigation,
        jain_fairness=jains_fairness(
            [sum(values) / len(values)
             for values in fairness_by_source.values()]
        ),
        delivered_pps=totals["delivered"] / windows,
        detection_precision=precision,
        detection_recall=recall,
        detection_f1=f1,
        mean_latency_ms=sum(latency_by_window) / len(latency_by_window),
        p95_latency_ms=sorted(latency_by_window)[
            (95 * len(latency_by_window) + 99) // 100 - 1
        ],
        mean_jitter_ms=sum(jitter_by_window) / len(jitter_by_window),
        packet_loss_ratio=sum(loss_by_window) / len(loss_by_window),
        throughput_mbps=(
            totals["delivered_bytes"] * 8
            / max(totals["elapsed_seconds"], 1e-9)
            / 1_000_000
        ),
        connection_reliability=(
            sum(reliability_by_window) / len(reliability_by_window)
        ),
        mean_utilization=(
            sum(utilization_by_window) / len(utilization_by_window)
        ),
        mean_ai_risk=sum(risk_values) / len(risk_values) if risk_values else 0.0,
        policy_filtered_pps=totals["policy_filtered"] / windows,
        congestion_dropped_pps=totals["congestion_dropped"] / windows,
        delivered_bytes=totals["delivered_bytes"],
    )

    return result, trace


def write_v3_outputs(results, trace, out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    records = [result.to_dict() for result in results]
    (out / "v3_summary.json").write_text(
        json.dumps(records, indent=2), encoding="utf-8"
    )

    if records:
        with (out / "v3_summary.csv").open(
            "w", newline="", encoding="utf-8"
        ) as f:
            writer = csv.DictWriter(f, fieldnames=list(records[0]))
            writer.writeheader()
            writer.writerows(records)

    if trace:
        with (out / "v3_trace.csv").open(
            "w", newline="", encoding="utf-8"
        ) as f:
            writer = csv.DictWriter(f, fieldnames=list(trace[0]))
            writer.writeheader()
            writer.writerows(trace)
