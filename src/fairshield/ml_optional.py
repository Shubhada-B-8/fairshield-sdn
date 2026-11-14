"""Optional Random Forest experiment. Core FairShield runs without this module."""
from __future__ import annotations

import argparse
import random
from pathlib import Path

from .simulator import generate_window


def train(output: str = "models/fairshield_rf.joblib", samples_per_class: int = 1500, seed: int = 17) -> dict:
    try:
        from joblib import dump
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.metrics import classification_report
        from sklearn.model_selection import train_test_split
    except ImportError as exc:
        raise SystemExit("Optional ML packages missing. Run: pip install -e '.[ml]'") from exc

    rng = random.Random(seed)
    features, labels = [], []
    # Synthetic labels are used only to demonstrate the optional ML pipeline.
    for i in range(samples_per_class):
        for scenario in ("normal", "ddos", "flash_crowd"):
            for s in generate_window(i, scenario, rng):
                features.append([
                    s.pps, s.bps, s.syn_ratio,
                    float(s.unique_dst_ports), s.avg_packet_bytes,
                ])
                labels.append(1 if s.label == "attack" else 0)
    x_train, x_test, y_train, y_test = train_test_split(
        features, labels, test_size=0.25, random_state=seed, stratify=labels
    )
    model = RandomForestClassifier(
        n_estimators=160, max_depth=12, class_weight="balanced", random_state=seed
    )
    model.fit(x_train, y_train)
    report = classification_report(y_test, model.predict(x_test), output_dict=True, zero_division=0)
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    dump(model, output_path)
    return {"model": str(output_path), "test_report": report, "features": [
        "pps", "bps", "syn_ratio", "unique_dst_ports", "avg_packet_bytes"
    ]}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="models/fairshield_rf.joblib")
    parser.add_argument("--samples-per-class", type=int, default=500)
    args = parser.parse_args()
    print(train(args.output, args.samples_per_class))


if __name__ == "__main__":
    main()
