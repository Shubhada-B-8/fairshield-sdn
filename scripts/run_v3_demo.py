#!/usr/bin/env python3
"""Run the FairShield V3 AI/5G-style simulation from the repository root."""
from __future__ import annotations
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fairshield.simulator import SCENARIOS
from fairshield.v3_ai import AIRiskDetector
from fairshield.v3_simulator import run_v3_experiment, write_v3_outputs


def main():
    parser = argparse.ArgumentParser(description="FairShield V3 AI-driven 5G-style simulation")
    parser.add_argument("--scenario", choices=("all", *SCENARIOS), default="all")
    parser.add_argument("--windows", type=int, default=30)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--capacity", type=float, default=500.0)
    parser.add_argument("--flash-weight", type=float, default=1.5)
    parser.add_argument("--out", default="outputs_v3")
    args = parser.parse_args()

    print("Training AI traffic-risk model on generated, labelled simulator samples...")
    detector = AIRiskDetector.train_synthetic(seed=41)
    scenarios = SCENARIOS if args.scenario == "all" else (args.scenario,)
    results, traces = [], []
    for scenario in scenarios:
        result, trace = run_v3_experiment(
            scenario=scenario, windows=args.windows, seed=args.seed,
            capacity_pps=args.capacity, detector=detector,
            flash_weight=args.flash_weight,
        )
        results.append(result)
        traces.extend(trace)
        print(
            f"{scenario:12} legit={100*result.legitimate_preservation:6.2f}% "
            f"attack_mitigated={100*result.attack_mitigation:6.2f}% "
            f"F1={result.detection_f1:.3f} latency_mean={result.mean_latency_ms:.2f}ms "
            f"p95={result.p95_latency_ms:.2f}ms throughput={result.throughput_mbps:.4f}Mbps "
            f"reliability={100*result.connection_reliability:.2f}%"
        )
    write_v3_outputs(results, traces, args.out)
    print(f"\nSaved V3 outputs to: {Path(args.out).resolve()}")
    print("NOTE: latency, jitter, packet loss, reliability and radio-independent QoS values are synthetic simulation proxies.")


if __name__ == "__main__":
    main()
