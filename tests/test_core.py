import unittest
import threading

from fairshield.detector import RuleBasedDetector
from fairshield.fairness import jains_fairness, weighted_max_min
from fairshield.models import FlowSample
from fairshield.simulator import run_experiment
from fairshield.socket_lab import TCPServer, UDPServer, _TCPHandler, _UDPHandler, tcp_request, udp_request


class FairnessTests(unittest.TestCase):
    def test_weighted_max_min_respects_capacity(self):
        allocation = weighted_max_min({"a": 100, "b": 100, "c": 100}, 90)
        self.assertAlmostEqual(sum(allocation.values()), 90.0)
        self.assertAlmostEqual(allocation["a"], 30.0)

    def test_weighted_max_min_respects_demand(self):
        allocation = weighted_max_min({"a": 10, "b": 100}, 80)
        self.assertAlmostEqual(allocation["a"], 10.0)
        self.assertAlmostEqual(allocation["b"], 70.0)

    def test_jain_index(self):
        self.assertAlmostEqual(jains_fairness([10, 10, 10]), 1.0)
        self.assertLess(jains_fairness([1, 10]), 1.0)


class DetectorTests(unittest.TestCase):
    def test_attack_like_flow_is_flagged(self):
        sample = FlowSample(1, "10.0.1.1", "10.0.0.100", 800, 80000,
                            760, 18, 1.0, "attack")
        self.assertTrue(RuleBasedDetector().detect(sample).suspicious)

    def test_normal_flow_is_not_flagged(self):
        sample = FlowSample(1, "10.0.0.2", "10.0.0.100", 45, 36000,
                            2, 1, 1.0, "benign")
        self.assertFalse(RuleBasedDetector().detect(sample).suspicious)

    def test_flash_crowd_not_flagged_by_combined_detector(self):
        sample = FlowSample(1, "10.0.2.2", "10.0.0.100", 210, 180000,
                            8, 1, 1.0, "benign")
        self.assertFalse(RuleBasedDetector().detect(sample).suspicious)


class SocketLabTests(unittest.TestCase):
    def test_tcp_telemetry_round_trip(self):
        server = TCPServer(("127.0.0.1", 0), _TCPHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            response = tcp_request("127.0.0.1", server.server_address[1], {
                "src_ip": "10.0.0.8", "packets": 700, "byte_count": 70000,
                "syn_packets": 665, "unique_dst_ports": 15, "duration_s": 1,
            })
            self.assertTrue(response["ok"])
            self.assertTrue(response["result"]["suspicious"])
        finally:
            server.shutdown()
            server.server_close()

    def test_udp_telemetry_round_trip(self):
        server = UDPServer(("127.0.0.1", 0), _UDPHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            response = udp_request("127.0.0.1", server.server_address[1], {
                "src_ip": "10.0.0.9", "packets": 30, "byte_count": 3000,
                "syn_packets": 1, "unique_dst_ports": 1, "duration_s": 1,
            })
            self.assertTrue(response["ok"])
            self.assertFalse(response["result"]["suspicious"])
        finally:
            server.shutdown()
            server.server_close()


class SimulationTests(unittest.TestCase):
    def test_ddos_scenario_detects_and_mitigates_attack(self):
        result, trace = run_experiment("ddos", "fairshield", windows=5, seed=7)
        self.assertEqual(result.tp, 30)
        self.assertEqual(result.fp, 0)
        self.assertGreater(result.attack_mitigation, 0.9)
        self.assertGreater(result.legitimate_preservation, 0.9)
        self.assertTrue(trace)

    def test_normal_scenario_has_no_attack(self):
        result, _ = run_experiment("normal", "fairshield", windows=3)
        self.assertEqual(result.attack_offered_pps, 0)
        self.assertEqual(result.attack_mitigation, 0)

    def test_attack_mitigation_measures_policy_not_congestion_loss(self):
        baseline, _ = run_experiment("ddos", "no_defense", windows=5, seed=7)
        defended, _ = run_experiment("ddos", "fairshield", windows=5, seed=7)
        self.assertEqual(baseline.attack_mitigation, 0.0)
        self.assertGreater(defended.attack_mitigation, 0.99)
        self.assertGreaterEqual(defended.attack_admitted_pps, 0.0)


if __name__ == "__main__":
    unittest.main()
