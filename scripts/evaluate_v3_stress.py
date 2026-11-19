"""Out-of-distribution synthetic stress test for the V3 detector."""

import random

from dataclasses import replace

from fairshield.v3_ai import AIRiskDetector
from fairshield.simulator import generate_window


TRAIN_SEED = 41
TEST_SEED = 3031
TEST_WINDOWS = 100


def main():
    print("Training original V3 detector...")
    detector = AIRiskDetector.train_synthetic(
        seed=TRAIN_SEED,
        windows_per_scenario=80,
    )

    rng = random.Random(TEST_SEED)

    groups = {
        "benign_mimicking_attack": [],
        "attack_mimicking_benign": [],
    }

    for window in range(TEST_WINDOWS):
        samples = generate_window(window, "mixed", rng)

        for sample in samples:
            if sample.label == "benign":
                packets = rng.randint(300, 450)
                syn_ratio = rng.uniform(0.55, 0.85)
                ports = rng.randint(8, 18)
                avg_bytes = rng.randint(80, 180)

                modified = replace(
                    sample,
                    packets=packets,
                    byte_count=packets * avg_bytes,
                    syn_packets=int(packets * syn_ratio),
                    unique_dst_ports=ports,
                )

                groups["benign_mimicking_attack"].append(modified)

            else:
                packets = rng.randint(45, 120)
                syn_ratio = rng.uniform(0.02, 0.10)
                ports = rng.randint(1, 2)
                avg_bytes = rng.randint(600, 1000)

                modified = replace(
                    sample,
                    packets=packets,
                    byte_count=packets * avg_bytes,
                    syn_packets=int(packets * syn_ratio),
                    unique_dst_ports=ports,
                )

                groups["attack_mimicking_benign"].append(modified)

    print("\nEvaluating deliberately overlapping traffic profiles")

    for group_name, samples in groups.items():
        tp = fp = tn = fn = 0

        # Evaluate in batches so window-level traffic volume is consistent.
        for start in range(0, len(samples), 14):
            batch = samples[start:start + 14]
            total_pps = sum(sample.pps for sample in batch)

            for sample in batch:
                predicted, score = detector.predict(sample, total_pps)
                actual = sample.label == "attack"

                if actual and predicted:
                    tp += 1
                elif actual and not predicted:
                    fn += 1
                elif not actual and predicted:
                    fp += 1
                else:
                    tn += 1

        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = (
            2 * precision * recall / (precision + recall)
            if precision + recall else 0.0
        )
        fpr = fp / (fp + tn) if fp + tn else 0.0

        print(f"\n{'=' * 50}")
        print("Test:", group_name)
        print("TP:", tp, "FP:", fp, "TN:", tn, "FN:", fn)
        print(f"Precision: {precision:.4f}")
        print(f"Recall:    {recall:.4f}")
        print(f"F1:        {f1:.4f}")
        print(f"FPR:       {fpr:.4f}")


if __name__ == "__main__":
    main()
