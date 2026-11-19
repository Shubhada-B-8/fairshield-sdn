import unittest

from fairshield.syn_telemetry import SynTelemetry


class TestSynTelemetry(unittest.TestCase):

    def setUp(self):
        self.telemetry = SynTelemetry()

    def test_packet_in_count(self):
        self.telemetry.record_packet_in(1, "10.0.0.1")
        self.telemetry.record_packet_in(1, "10.0.0.1", 2)

        self.assertEqual(
            self.telemetry.consume_window(1, "10.0.0.1"), 3
        )

    def test_primed_counter_counts_first_reading(self):
        self.telemetry.prime_flow_counter(
            1, "10.0.0.1", "flow-a"
        )

        delta = self.telemetry.update_flow_counter(
            1, "10.0.0.1", "flow-a", 5
        )

        self.assertEqual(delta, 5)
        self.assertEqual(
            self.telemetry.consume_window(1, "10.0.0.1"), 5
        )

    def test_repeated_prime_does_not_reset_counter(self):
        self.telemetry.prime_flow_counter(
            1, "10.0.0.1", "flow-a"
        )
        self.telemetry.update_flow_counter(
            1, "10.0.0.1", "flow-a", 5
        )

        self.telemetry.prime_flow_counter(
            1, "10.0.0.1", "flow-a"
        )

        delta = self.telemetry.update_flow_counter(
            1, "10.0.0.1", "flow-a", 8
        )

        self.assertEqual(delta, 3)

    def test_flow_counter_delta(self):
        self.assertEqual(
            self.telemetry.update_flow_counter(
                1, "10.0.0.1", "flow-a", 5
            ), 0
        )
        self.assertEqual(
            self.telemetry.update_flow_counter(
                1, "10.0.0.1", "flow-a", 8
            ), 3
        )
        self.assertEqual(
            self.telemetry.consume_window(1, "10.0.0.1"), 3
        )

    def test_multiple_flows_same_source(self):
        self.telemetry.update_flow_counter(
            1, "10.0.0.1", "flow-a", 0
        )
        self.telemetry.update_flow_counter(
            1, "10.0.0.1", "flow-b", 0
        )

        self.telemetry.update_flow_counter(
            1, "10.0.0.1", "flow-a", 4
        )
        self.telemetry.update_flow_counter(
            1, "10.0.0.1", "flow-b", 6
        )

        self.assertEqual(
            self.telemetry.consume_window(1, "10.0.0.1"), 10
        )

    def test_counter_reset(self):
        self.telemetry.update_flow_counter(
            1, "10.0.0.1", "flow-a", 10
        )
        delta = self.telemetry.update_flow_counter(
            1, "10.0.0.1", "flow-a", 2
        )

        self.assertEqual(delta, 2)
        self.assertEqual(
            self.telemetry.consume_window(1, "10.0.0.1"), 2
        )

    def test_sources_are_isolated(self):
        self.telemetry.record_packet_in(1, "10.0.0.1", 2)
        self.telemetry.record_packet_in(1, "10.0.0.2", 5)

        self.assertEqual(
            self.telemetry.consume_window(1, "10.0.0.1"), 2
        )
        self.assertEqual(
            self.telemetry.consume_window(1, "10.0.0.2"), 5
        )

    def test_remove_flow(self):
        self.telemetry.update_flow_counter(
            1, "10.0.0.1", "flow-a", 5
        )
        self.telemetry.remove_flow(1, "10.0.0.1", "flow-a")

        self.assertEqual(
            self.telemetry.update_flow_counter(
                1, "10.0.0.1", "flow-a", 8
            ), 0
        )

    def test_remove_source(self):
        self.telemetry.record_packet_in(1, "10.0.0.1", 3)
        self.telemetry.update_flow_counter(
            1, "10.0.0.1", "flow-a", 5
        )
        self.telemetry.remove_source(1, "10.0.0.1")

        self.assertEqual(
            self.telemetry.consume_window(1, "10.0.0.1"), 0
        )
        self.assertEqual(
            self.telemetry.update_flow_counter(
                1, "10.0.0.1", "flow-a", 8
            ), 0
        )

    def test_negative_packet_count_rejected(self):
        with self.assertRaises(ValueError):
            self.telemetry.record_packet_in(
                1, "10.0.0.1", -1
            )

    def test_negative_counter_rejected(self):
        with self.assertRaises(ValueError):
            self.telemetry.update_flow_counter(
                1, "10.0.0.1", "flow-a", -1
            )


if __name__ == "__main__":
    unittest.main()
