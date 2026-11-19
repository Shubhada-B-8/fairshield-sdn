import random
import numpy as np

from fairshield.v3_ai import AIRiskDetector
from fairshield.simulator import SCENARIOS, generate_window

detector = AIRiskDetector.train_synthetic(seed=41, windows_per_scenario=80)
rng = random.Random(3030)

for scenario in SCENARIOS:
    benign_scores = []
    attack_scores = []

    for window in range(100):
        samples = generate_window(window, scenario, rng)
        total = sum(s.pps for s in samples)

        for sample in samples:
            _, score = detector.predict(sample, total)

            if sample.label == "attack":
                attack_scores.append(score)
            else:
                benign_scores.append(score)

    print(f"\n{scenario.upper()}")

    if benign_scores:
        print(
            "Benign probabilities:",
            "min =", round(min(benign_scores), 5),
            "median =", round(float(np.median(benign_scores)), 5),
            "max =", round(max(benign_scores), 5),
        )

    if attack_scores:
        print(
            "Attack probabilities:",
            "min =", round(min(attack_scores), 5),
            "median =", round(float(np.median(attack_scores)), 5),
            "max =", round(max(attack_scores), 5),
        )
