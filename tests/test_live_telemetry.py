import tempfile
import unittest
from pathlib import Path

from fairshield.live_telemetry import (
    read_controller_telemetry,
    aggregate_port_metrics,
)


class LiveTelemetryTests(unittest.TestCase):
    def test_reads_port_and_probe_metrics(self):
        content = """
PORT_METRICS dpid=1 port=2 rx_mbps=5.250 tx_mbps=1.200 utilization=0.263
PROBE_METRICS latency_ms=0.12 jitter_ms=0.03 probe_loss_pct=0.0 reliability_pct=100.0
"""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "controller.log"
            path.write_text(content)
            data = read_controller_telemetry(path)

        self.assertEqual(data["ports"]["1:2"]["rx_mbps"], 5.25)
        self.assertEqual(data["probe"]["latency_ms"], 0.12)
        self.assertEqual(data["probe"]["probe_loss_ratio"], 0.0)

    def test_missing_probe_is_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "controller.log"
            path.write_text(
                "PORT_METRICS dpid=1 port=2 rx_mbps=0.004 "
                "tx_mbps=0.004 utilization=0.000\n"
            )
            data = read_controller_telemetry(path)

        self.assertIsNone(data["probe"]["latency_ms"])
        self.assertIsNone(data["probe"]["probe_loss_ratio"])

    def test_aggregates_port_metrics(self):
        data = {
            "ports": {
                "1:2": {
                    "rx_mbps": 2.0, "tx_mbps": 1.0,
                    "link_utilization": 0.2,
                },
                "1:5": {
                    "rx_mbps": 3.0, "tx_mbps": 2.0,
                    "link_utilization": 0.3,
                },
            }
        }
        aggregate = aggregate_port_metrics(data)
        self.assertEqual(aggregate["rx_throughput_mbps"], 5.0)
        self.assertEqual(aggregate["tx_throughput_mbps"], 3.0)
        self.assertEqual(aggregate["link_utilization"], 0.3)


if __name__ == "__main__":
    unittest.main()
