import unittest

from fairshield.adaptive_policy import (
    AdaptiveFairnessController, AdaptivePolicyConfig, NetworkFeedback,
)
from fairshield.adaptive_simulator import run_adaptive_experiment
from fairshield.models import FlowSample


def attack_sample(src="10.0.1.1"):
    return FlowSample(1, src, "10.0.0.100", 800, 800 * 100, 760, 18, 1.0, "attack")


def benign_sample(src="10.0.0.1"):
    return FlowSample(1, src, "10.0.0.100", 45, 45 * 800, 2, 1, 1.0, "benign")


class AdaptivePolicyTests(unittest.TestCase):
    def test_congestion_and_poor_legitimate_service_tighten_cap(self):
        policy = AdaptiveFairnessController()
        first = policy.decide([attack_sample()])[0]
        tight = policy.decide([attack_sample()], {"10.0.1.1": NetworkFeedback(
            capacity_utilization=0.98, legitimate_service_ratio=0.70,
            source_meter_drop_ratio=0.30,
        )})[0]
        self.assertLess(tight.adaptive_cap_pps, first.adaptive_cap_pps)
        self.assertEqual(tight.adjustment, "tighten_congestion_or_legitimate_service")

    def test_headroom_and_meter_drops_relax_cap(self):
        policy = AdaptiveFairnessController()
        first = policy.decide([attack_sample()])[0]
        relaxed = policy.decide([attack_sample()], {"10.0.1.1": NetworkFeedback(
            capacity_utilization=0.40, legitimate_service_ratio=0.99,
            source_meter_drop_ratio=0.40,
        )})[0]
        self.assertGreater(relaxed.adaptive_cap_pps, first.adaptive_cap_pps)
        self.assertEqual(relaxed.adjustment, "relax_headroom_with_meter_drops")

    def test_cap_is_bounded(self):
        cfg = AdaptivePolicyConfig(max_attack_cap_pps=6.0)
        policy = AdaptiveFairnessController(cfg)
        feedback = NetworkFeedback(0.10, 1.0, 0.80)
        for _ in range(30):
            result = policy.decide([attack_sample()], {"10.0.1.1": feedback})[0]
        self.assertLessEqual(result.adaptive_cap_pps, 6.0)
        self.assertGreaterEqual(result.adaptive_cap_pps, cfg.min_attack_cap_pps)

    def test_benign_recovery_is_gradual(self):
        policy = AdaptiveFairnessController()
        source = "10.0.1.1"
        policy.decide([attack_sample(source)])
        policy.decide([attack_sample(source)], {source: NetworkFeedback(0.99, 0.60, 0.50)})
        lowered = policy.state_snapshot()[source]["cap_pps"]
        healthy_feedback = NetworkFeedback(
            capacity_utilization=0.40,
            legitimate_service_ratio=0.99,
            source_meter_drop_ratio=0.0,
        )
        policy.decide([benign_sample(source)], {source: healthy_feedback})
        policy.decide([benign_sample(source)], {source: healthy_feedback})
        recovered = policy.state_snapshot()[source]["cap_pps"]
        self.assertGreater(recovered, lowered)
        self.assertLessEqual(recovered, policy.config.initial_attack_cap_pps)

    def test_attack_limit_stays_latched_until_cap_recovers(self):
        policy = AdaptiveFairnessController()
        source = "10.0.1.1"
        attack_feedback = NetworkFeedback(0.99, 0.60, 0.50)
        healthy_feedback = NetworkFeedback(0.40, 0.99, 0.0)

        policy.decide([attack_sample(source)], {source: attack_feedback})
        first_benign = policy.decide(
            [benign_sample(source)], {source: healthy_feedback}
        )[0]

        self.assertTrue(first_benign.suspicious)
        self.assertTrue(policy.state_snapshot()[source]["attack_latched"])

        result = first_benign
        for _ in range(10):
            result = policy.decide(
                [benign_sample(source)], {source: healthy_feedback}
            )[0]
            if not result.suspicious:
                break

        self.assertFalse(result.suspicious)
        self.assertFalse(policy.state_snapshot()[source]["attack_latched"])
        self.assertAlmostEqual(
            policy.state_snapshot()[source]["cap_pps"],
            policy.config.initial_attack_cap_pps,
        )

    def test_weighted_max_min_allocation_respects_capacity_for_multiple_sources(self):
        cfg = AdaptivePolicyConfig(link_capacity_pps=100.0)
        policy = AdaptiveFairnessController(cfg)
        samples = [attack_sample("10.0.1.1"), attack_sample("10.0.1.2"), benign_sample("10.0.0.1")]
        results = policy.decide(samples)
        self.assertLessEqual(sum(x.allocated_pps for x in results), 100.000001)
        self.assertTrue(all(x.allocated_pps <= x.admitted_pps + 1e-9 for x in results))

    def test_hysteresis_band_holds_cap(self):
        policy = AdaptiveFairnessController()
        src = "10.0.1.1"
        first = policy.decide([attack_sample(src)])[0]
        held = policy.decide([attack_sample(src)], {src: NetworkFeedback(
            capacity_utilization=0.82, legitimate_service_ratio=0.97,
            source_meter_drop_ratio=0.05,
        )})[0]
        self.assertAlmostEqual(first.adaptive_cap_pps, held.adaptive_cap_pps)
        self.assertEqual(held.adjustment, "hold_hysteresis_band")

    def test_invalid_feedback_is_rejected(self):
        with self.assertRaises(ValueError):
            NetworkFeedback(capacity_utilization=1.1)

    def test_adaptive_simulator_is_reproducible_and_emits_trace(self):
        result_a, trace_a = run_adaptive_experiment("mixed", windows=5, seed=7)
        result_b, trace_b = run_adaptive_experiment("mixed", windows=5, seed=7)
        self.assertEqual(result_a.to_dict(), result_b.to_dict())
        self.assertEqual(trace_a, trace_b)
        self.assertTrue(trace_a)
        self.assertTrue(all(row["policy"] == "adaptive_fairshield_v2" for row in trace_a))


    def test_missing_feedback_holds_current_cap(self):
        policy = AdaptiveFairnessController()
        src = "10.0.1.1"

        policy.decide([attack_sample(src)])
        policy.decide([attack_sample(src)], {
            src: NetworkFeedback(0.99, 0.60, 0.50)
        })
        lowered = policy.state_snapshot()[src]["cap_pps"]

        result = policy.decide([attack_sample(src)])[0]

        self.assertEqual(result.adaptive_cap_pps, lowered)
        self.assertEqual(result.adjustment, "missing_feedback_hold")

    def test_missing_feedback_does_not_trigger_benign_recovery(self):
        policy = AdaptiveFairnessController()
        src = "10.0.1.1"

        policy.decide([attack_sample(src)])
        policy.decide([attack_sample(src)], {
            src: NetworkFeedback(0.99, 0.60, 0.50)
        })
        lowered = policy.state_snapshot()[src]["cap_pps"]

        for _ in range(4):
            result = policy.decide([benign_sample(src)])[0]

        self.assertEqual(policy.state_snapshot()[src]["cap_pps"], lowered)
        self.assertEqual(result.adjustment, "missing_feedback_hold")


if __name__ == "__main__":
    unittest.main()
