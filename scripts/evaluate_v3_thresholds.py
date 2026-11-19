"""Threshold sensitivity evaluation on independently generated synthetic traffic."""

import random

from fairshield.v3_ai import AIRiskDetector, feature_vector
from fairshield.simulator import generate_window


TRAIN_SEED = 41
TEST_SEED = 2027
TEST_WINDOWS = 100
THRESHOLDS = [0.30, 0.50, 0.70, 0.90]
SCENARIOS = ["ddos", "mixed"]


def main():
    print("Training synthetic Random Forest detector...")

    detector = AIRiskDetector.train_synthetic(
        seed=TRAIN_SEED,
        windows_per_scenario=80,
    )

    # Generate the test samples once so every threshold sees identical data.
    rng = random.Random(TEST_SEED)
    test_data = []

    for scenario in SCENARIOS:
        for window in range(TEST_WINDOWS):
            samples = generate_window(window, scenario, rng)
            total_pps = sum(sample.pps for sample in samples)

            for sample in samples:
                actual = sample.label == "attack"
                features = feature_vector(sample, total_pps)
                test_data.append((scenario, actual, features))

    # Obtain probabilities once; only the decision threshold changes.
    classes = list(detector.model.classes_)
    attack_index = classes.index(1)

    probabilities = detector.model.predict_proba(
        [item[2] for item in test_data]
    )[:, attack_index]

    print("\nIndependent synthetic test set:", len(test_data), "samples")
    print("Threshold sensitivity results")

    for threshold in THRESHOLDS:
        print(f"\n{'=' * 55}")
        print(f"THRESHOLD: {threshold:.2f}")

        for scenario in SCENARIOS:
            tp = fp = tn = fn = 0

            for (sample_scenario, actual, _), probability in zip(
                test_data, probabilities
            ):
                if sample_scenario != scenario:
                    continue

                predicted = float(probability) >= threshold

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
                if precision + recall
                else 0.0
            )
            fpr = fp / (fp + tn) if fp + tn else 0.0

            print(
                f"{scenario:8s} "
                f"TP={tp:4d} FP={fp:4d} "
                f"TN={tn:4d} FN={fn:4d} "
                f"Precision={precision:.4f} "
                f"Recall={recall:.4f} "
                f"F1={f1:.4f} "
                f"FPR={fpr:.4f}"
            )


if __name__ == "__main__":
    main()
