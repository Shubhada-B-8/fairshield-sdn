import unittest

from fairshield.qos_optimizer import QoSOptimizer


class QoSOptimizerTests(unittest.TestCase):
    def setUp(self):
        self.optimizer = QoSOptimizer()

    def test_healthy_network(self):
        result = self.optimizer.evaluate({
            "latency_ms": 5,
            "jitter_ms": 1,
            "probe_loss_ratio": 0,
            "link_utilization": 0.3,
            "cpu_percent": 30,
            "memory_percent": 40,
        })
        self.assertEqual(result.status, "NORMAL")
        self.assertEqual(result.score, 100)

    def test_single_warning(self):
        result = self.optimizer.evaluate({"latency_ms": 25})
        self.assertEqual(result.status, "WATCH")

    def test_multiple_warnings(self):
        result = self.optimizer.evaluate({
            "latency_ms": 25,
            "link_utilization": 0.80,
        })
        self.assertEqual(result.status, "CONGESTED")

    def test_critical_loss(self):
        result = self.optimizer.evaluate({"probe_loss_ratio": 0.08})
        self.assertEqual(result.status, "CRITICAL")

    def test_missing_metrics_are_not_assumed_healthy_or_failed(self):
        result = self.optimizer.evaluate({})
        self.assertEqual(result.status, "INSUFFICIENT_DATA")
        self.assertEqual(result.score, 0)


if __name__ == "__main__":
    unittest.main()
