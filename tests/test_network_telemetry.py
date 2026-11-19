import unittest

from fairshield.network_telemetry import NetworkTelemetry


class NetworkTelemetryTests(unittest.TestCase):

    def test_latency_and_jitter(self):
        telemetry = NetworkTelemetry()
        telemetry.record_probe(True, 10)
        telemetry.record_probe(True, 20)
        telemetry.record_probe(True, 15)

        metrics = telemetry.snapshot()

        self.assertAlmostEqual(metrics.latency_ms, 15)
        self.assertAlmostEqual(metrics.jitter_ms, 7.5)

    def test_probe_loss_and_reliability(self):
        telemetry = NetworkTelemetry()
        telemetry.record_probe(True, 10)
        telemetry.record_probe(False)
        telemetry.record_probe(True, 12)
        telemetry.record_probe(False)

        metrics = telemetry.snapshot()

        self.assertAlmostEqual(metrics.reliability, 0.5)
        self.assertAlmostEqual(metrics.probe_loss_ratio, 0.5)

    def test_probe_window_resets(self):
        telemetry = NetworkTelemetry()
        telemetry.record_probe(True, 10)

        telemetry.snapshot()
        metrics = telemetry.snapshot()

        self.assertIsNone(metrics.latency_ms)
        self.assertIsNone(metrics.reliability)

    def test_throughput_calculation(self):
        telemetry = NetworkTelemetry()
        telemetry.update_interface_counters(0, 0, 1.0)
        telemetry.update_interface_counters(
            1_000_000, 2_000_000, 3.0
        )

        metrics = telemetry.snapshot()

        self.assertAlmostEqual(metrics.rx_throughput_mbps, 4.0)
        self.assertAlmostEqual(metrics.tx_throughput_mbps, 8.0)

    def test_link_utilization(self):
        telemetry = NetworkTelemetry(link_capacity_mbps=20)
        telemetry.update_interface_counters(0, 0, 1)
        telemetry.update_interface_counters(
            1_000_000, 1_000_000, 2
        )

        self.assertAlmostEqual(
            telemetry.snapshot().link_utilization, 0.4
        )

    def test_link_utilization_is_capped(self):
        telemetry = NetworkTelemetry(link_capacity_mbps=10)
        telemetry.update_interface_counters(0, 0, 1)
        telemetry.update_interface_counters(
            10_000_000, 10_000_000, 2
        )

        self.assertEqual(telemetry.snapshot().link_utilization, 1.0)

    def test_system_metrics(self):
        telemetry = NetworkTelemetry()
        telemetry.update_system_metrics(45, 70)

        metrics = telemetry.snapshot()

        self.assertEqual(metrics.cpu_percent, 45)
        self.assertEqual(metrics.memory_percent, 70)

    def test_invalid_values(self):
        with self.assertRaises(ValueError):
            NetworkTelemetry(link_capacity_mbps=0)

        telemetry = NetworkTelemetry()

        with self.assertRaises(ValueError):
            telemetry.record_probe(True, -1)

        with self.assertRaises(ValueError):
            telemetry.update_system_metrics(cpu_percent=120)

    def test_counter_reset(self):
        telemetry = NetworkTelemetry()
        telemetry.update_interface_counters(1000, 1000, 1)
        telemetry.update_interface_counters(100, 200, 2)

        metrics = telemetry.snapshot()

        self.assertAlmostEqual(metrics.rx_throughput_mbps, 0.0008)
        self.assertAlmostEqual(metrics.tx_throughput_mbps, 0.0016)


if __name__ == "__main__":
    unittest.main()
