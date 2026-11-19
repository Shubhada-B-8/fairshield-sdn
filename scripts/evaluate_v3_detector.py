"""Evaluate the V3 detector on independently generated synthetic traffic."""

import random

from fairshield.v3_ai import AIRiskDetector
from fairshield.simulator import SCENARIOS, generate_window


TRAIN_SEED = 41
TEST_SEED = 2026
TEST_WINDOWS = 100


def evaluate():
    print("Training detector on synthetic training data...")
    detector = AIRiskDetector.train_synthetic(
        seed=TRAIN_SEED,
        windows_per_scenario=80,
    )

    print(f"Evaluating on independent generated data (seed={TEST_SEED})")

    rng = random.Random(TEST_SEED)

    for scenario in SCENARIOS:
        tp = fp = tn = fn = 0

        for window in range(TEST_WINDOWS):
            samples = generate_window(window, scenario, rng)
            total_pps = sum(sample.pps for sample in samples)

            for sample in samples:
                predicted, probability = detector.predict(
                    sample, total_pps
                )

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
        recall = tp / (tp + fn) if tp + fn else None
        f1 = (
            2 * precision * recall / (precision + recall)
            if recall is not None and precision + recall
            else None
        )
        fpr = fp / (fp + tn) if fp + tn else 0.0

        print(f"\n{'=' * 45}")
        print(f"Scenario: {scenario}")
        print(f"TP: {tp} | FP: {fp} | TN: {tn} | FN: {fn}")
        print(f"False-positive rate: {fpr:.4f}")
        print(f"Precision: {precision:.4f}")

        if recall is None:
            print("Recall: N/A (no attack samples)")
            print("F1: N/A (no attack samples)")
        else:
            print(f"Recall: {recall:.4f}")
            print(f"F1: {f1:.4f}")


if __name__ == "__main__":
    evaluate()
