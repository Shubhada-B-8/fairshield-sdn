import unittest

from fairshield.models import FlowSample
from fairshield.v3_ai_sdn import (
    V3AIDetectionAdapter,
    V3AIDetectorConfig,
)


class FakeAI:
    def __init__(self, suspicious=True, score=0.95, fail=False):
        self.suspicious = suspicious
        self.score = score
        self.fail = fail

    def predict(self, sample, window_total_pps):
        if self.fail:
            raise RuntimeError("test failure")
        return self.suspicious, self.score


def benign_sample():
    return FlowSample(
        1, "10.0.0.1", "10.0.0.100",
        45, 36000, 2, 1, 1.0, "unknown"
    )


def attack_sample():
    return FlowSample(
        1, "10.0.1.1", "10.0.0.100",
        800, 80000, 760, 18, 1.0, "unknown"
    )


class V3AISDNTests(unittest.TestCase):

    def test_shadow_mode_preserves_rule_decision(self):
        adapter = V3AIDetectionAdapter(
            ai_detector=FakeAI(True, 0.99),
            config=V3AIDetectorConfig(mode="shadow"),
        )
        sample = benign_sample()
        result = adapter.detect(sample)

        self.assertFalse(result.suspicious)
        self.assertTrue(any("AI attack probability" in r for r in result.reasons))

    def test_hybrid_any_detects_ai_positive_traffic(self):
        adapter = V3AIDetectionAdapter(
            ai_detector=FakeAI(True, 0.99),
            config=V3AIDetectorConfig(mode="hybrid", fusion="any"),
        )
        result = adapter.detect(benign_sample())
        self.assertTrue(result.suspicious)

    def test_hybrid_both_requires_both_detectors(self):
        adapter = V3AIDetectionAdapter(
            ai_detector=FakeAI(True, 0.99),
            config=V3AIDetectorConfig(mode="hybrid", fusion="both"),
        )
        result = adapter.detect(benign_sample())
        self.assertFalse(result.suspicious)

    def test_ai_only_mode_uses_ai_prediction(self):
        adapter = V3AIDetectionAdapter(
            ai_detector=FakeAI(True, 0.99),
            config=V3AIDetectorConfig(mode="hybrid", fusion="ai"),
        )
        result = adapter.detect(benign_sample())
        self.assertTrue(result.suspicious)

    def test_rule_fallback_when_ai_is_unavailable(self):
        adapter = V3AIDetectionAdapter()
        result = adapter.detect(attack_sample())

        self.assertTrue(result.suspicious)
        self.assertTrue(any("unavailable" in r for r in result.reasons))

    def test_rule_fallback_when_ai_inference_fails(self):
        adapter = V3AIDetectionAdapter(ai_detector=FakeAI(fail=True))
        result = adapter.detect(attack_sample())

        self.assertTrue(result.suspicious)
        self.assertEqual(adapter.ai_errors, 1)
        self.assertFalse(adapter.ai_available)

    def test_window_total_pps_is_validated(self):
        adapter = V3AIDetectionAdapter()
        adapter.set_window_total_pps(1500)
        self.assertEqual(adapter.status()["window_total_pps"], 1500)

        with self.assertRaises(ValueError):
            adapter.set_window_total_pps(-1)

    def test_invalid_fusion_mode_is_rejected(self):
        with self.assertRaises(ValueError):
            V3AIDetectorConfig(fusion="invalid")


if __name__ == "__main__":
    unittest.main()
