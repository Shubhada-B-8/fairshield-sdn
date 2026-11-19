import unittest

from fairshield.v3_ai import AIRiskDetector
from fairshield.models import FlowSample
from fairshield.v3_simulator import run_v3_experiment


class V3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.detector = AIRiskDetector.train_synthetic(
            seed=41, windows_per_scenario=12
        )

    def test_model_returns_probability_and_class(self):
        from fairshield.simulator import generate_window
        import random

        samples = generate_window(0, "ddos", random.Random(7))
        total = sum(s.pps for s in samples)
        flagged, score = self.detector.predict(samples[-1], total)

        self.assertIsInstance(flagged, bool)
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)

    def test_detects_live_like_udp_flood_without_flagging_bulk_traffic(self):
        udp_flood = FlowSample(
            1, "10.0.0.2", "10.0.0.5",
            4478, 4478 * 1512, 0, 1, 1.0, "unknown"
        )
        legitimate_bulk = FlowSample(
            1, "10.0.0.3", "10.0.0.5",
            1000, 1000 * 1400, 0, 1, 1.0, "unknown"
        )

        attack_flag, attack_score = self.detector.predict(
            udp_flood, udp_flood.pps
        )
        benign_flag, benign_score = self.detector.predict(
            legitimate_bulk, legitimate_bulk.pps
        )

        self.assertTrue(
            attack_flag,
            f"UDP flood not detected: probability={attack_score:.3f}"
        )
        self.assertFalse(
            benign_flag,
            f"Legitimate bulk traffic flagged: probability={benign_score:.3f}"
        )

    def test_v3_simulation_outputs_qos_metrics(self):
        result, trace = run_v3_experiment(
            "mixed", windows=3, seed=7, detector=self.detector
        )

        self.assertGreaterEqual(result.mean_latency_ms, 0.0)
        self.assertGreaterEqual(result.connection_reliability, 0.0)
        self.assertLessEqual(result.connection_reliability, 1.0)
        self.assertTrue(trace)
        self.assertIn("latency_ms_synthetic", trace[0])

    def test_new_traffic_accounting_metrics(self):
        result, trace = run_v3_experiment(
            "ddos", windows=3, seed=7, detector=self.detector
        )

        self.assertGreater(result.delivered_bytes, 0.0)
        self.assertGreater(result.throughput_mbps, 0.0)
        self.assertGreaterEqual(result.policy_filtered_pps, 0.0)
        self.assertGreaterEqual(result.congestion_dropped_pps, 0.0)

        self.assertGreaterEqual(result.packet_loss_ratio, 0.0)
        self.assertLessEqual(result.packet_loss_ratio, 1.0)

        self.assertGreaterEqual(result.mean_utilization, 0.0)
        self.assertLessEqual(result.mean_utilization, 1.0)

        self.assertAlmostEqual(
            result.connection_reliability,
            1.0 - result.packet_loss_ratio,
            places=10,
        )

        self.assertGreaterEqual(
            result.p95_latency_ms, result.mean_latency_ms
        )

        self.assertIn("policy_filtered_pps", trace[0])
        self.assertIn("congestion_dropped_pps", trace[0])
        self.assertIn("window_congestion_drop_ratio_synthetic", trace[0])
        self.assertIn("delivered_bytes_per_window", trace[0])

    def test_window_utilization_is_consistent_across_sources(self):
        _, trace = run_v3_experiment(
            "ddos", windows=3, seed=7, detector=self.detector
        )

        utilization_by_window = {}

        for row in trace:
            window = row["window"]
            utilization = row["utilization_ratio"]

            if window in utilization_by_window:
                self.assertEqual(
                    utilization_by_window[window], utilization
                )
            else:
                utilization_by_window[window] = utilization


if __name__ == "__main__":
    unittest.main()
