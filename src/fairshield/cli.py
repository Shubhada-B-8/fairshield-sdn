from __future__ import annotations

import argparse
import json
from pathlib import Path

from .reporting import write_outputs
from .simulator import POLICIES, SCENARIOS, run_experiment, run_suite
from .adaptive_simulator import run_adaptive_suite, write_adaptive_outputs


def _print_table(results) -> None:
    headers = ("SCENARIO", "POLICY", "LEGIT PRES.", "ATTACK MIT.", "FAIRNESS", "F1", "DELIVERED PPS")
    print("\n" + " | ".join(headers))
    print("-" * 104)
    for r in results:
        print(
            f"{r.scenario:12} | {r.policy:16} | {100*r.legitimate_preservation:8.1f}% | "
            f"{100*r.attack_mitigation:8.1f}% | {r.jain_satisfaction_fairness:8.3f} | "
            f"{r.f1:5.3f} | {r.delivered_pps:12.1f}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="fairshield",
        description="Fairness-aware SDN DDoS detection and mitigation research prototype",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    demo = sub.add_parser("demo", help="run all scenarios and all baseline policies")
    demo.add_argument("--windows", type=int, default=30)
    demo.add_argument("--seed", type=int, default=7)
    demo.add_argument("--capacity", type=float, default=500.0)
    demo.add_argument("--out", default="outputs")

    sim = sub.add_parser("simulate", help="run one scenario with all three policies")
    sim.add_argument("--scenario", choices=SCENARIOS, default="mixed")
    sim.add_argument("--windows", type=int, default=30)
    sim.add_argument("--seed", type=int, default=7)
    sim.add_argument("--capacity", type=float, default=500.0)
    sim.add_argument("--out", default="outputs")

    adaptive = sub.add_parser("adaptive-demo", help="run V2 feedback-driven adaptive experiments")
    adaptive.add_argument("--scenario", choices=("all", *SCENARIOS), default="all")
    adaptive.add_argument("--windows", type=int, default=30)
    adaptive.add_argument("--seed", type=int, default=7)
    adaptive.add_argument("--capacity", type=float, default=500.0)
    adaptive.add_argument("--out", default="outputs_v2")

    dashboard = sub.add_parser("dashboard", help="start the local dashboard")
    dashboard.add_argument("--host", default="127.0.0.1")
    dashboard.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()

    if args.command == "dashboard":
        from .dashboard import main as dashboard_main
        dashboard_main(args.host, args.port)
        return

    if args.command == "adaptive-demo":
        scenarios = SCENARIOS if args.scenario == "all" else (args.scenario,)
        results, traces = run_adaptive_suite(scenarios, args.windows, args.seed, args.capacity)
        write_adaptive_outputs(results, traces, args.out)
        print("SCENARIO | LEGIT PRESERVED | ATTACK MITIGATED | FAIRNESS | F1 | MEAN ATTACK CAP PPS")
        for r in results:
            print(f"{r.scenario:12} | {100*r.legitimate_preservation:15.1f}% | "
                  f"{100*r.attack_mitigation:16.1f}% | {r.jain_satisfaction_fairness:8.3f} | "
                  f"{r.f1:5.3f} | {r.mean_attack_cap_pps:19.2f}")
        print(f"\nSaved V2 feedback experiment outputs to: {Path(args.out).resolve()}")
        return

    if args.command == "demo":
        results, traces = run_suite(windows=args.windows, seed=args.seed,
                                    link_capacity_pps=args.capacity)
    else:
        results, traces = run_suite([args.scenario], windows=args.windows,
                                    seed=args.seed, link_capacity_pps=args.capacity)
    write_outputs(results, traces, args.out)
    _print_table(results)
    print(f"\nSaved: {Path(args.out).resolve()}/summary.csv")
    print(f"Saved: {Path(args.out).resolve()}/summary.json")
    print(f"Saved: {Path(args.out).resolve()}/traffic_trace.csv")


if __name__ == "__main__":
    main()
