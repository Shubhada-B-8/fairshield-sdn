import unittest

from fairshield.models import FlowSample
from fairshield.sdn_policy import SdnPolicyConfig, SdnSourcePolicy


def sample(src, packets, byte_count, duration=1.0, ports=1):
    return FlowSample(
        window_id=1,
        src_ip=src,
        dst_ip="10.0.0.5",
        packets=packets,
        byte_count=byte_count,
        syn_packets=0,
        unique_dst_ports=ports,
        duration_s=duration,
        label="unknown",
    )


class LiveSdnPolicyTests(unittest.TestCase):
    def test_high_rate_small_packet_source_is_detected_and_capped(self):
        policy = SdnSourcePolicy()
        result = policy.decide([sample("10.0.0.3", 2500, 2500 * 128)])[0]
        self.assertTrue(result.suspicious)
        self.assertLessEqual(result.admitted_kbps, 1500.0)
        self.assertEqual(result.action, "RATE_LIMIT")

    def test_large_packet_flash_crowd_source_is_not_detected(self):
        policy = SdnSourcePolicy()
        result = policy.decide([sample("10.0.0.1", 500, 500 * 1000)])[0]
        self.assertFalse(result.suspicious)
        self.assertEqual(result.action, "ALLOW")

    def test_weighted_max_min_respects_live_capacity(self):
        policy = SdnSourcePolicy(SdnPolicyConfig(capacity_kbps=5000.0))
        results = policy.decide([
            sample("10.0.0.1", 1000, 1000 * 1000),
            sample("10.0.0.2", 1000, 1000 * 1000),
            sample("10.0.0.3", 1000, 1000 * 1000),
        ])
        self.assertLessEqual(sum(r.allocated_kbps for r in results), 5000.001)

    def test_attack_cap_is_applied_before_fair_share(self):
        policy = SdnSourcePolicy(SdnPolicyConfig(capacity_kbps=5000.0))
        results = policy.decide([
            sample("10.0.0.3", 2500, 2500 * 128),
            sample("10.0.0.4", 2500, 2500 * 128),
            sample("10.0.0.1", 700, 700 * 1000),
        ])
        by_ip = {r.src_ip: r for r in results}
        self.assertTrue(by_ip["10.0.0.3"].suspicious)
        self.assertTrue(by_ip["10.0.0.4"].suspicious)
        self.assertLessEqual(by_ip["10.0.0.3"].admitted_kbps, 1500.0)
        self.assertGreater(by_ip["10.0.0.1"].allocated_kbps,
                           by_ip["10.0.0.3"].allocated_kbps)

    def test_source_recovers_when_traffic_returns_to_normal(self):
        policy = SdnSourcePolicy()

        attack = sample("10.0.0.3", 2500, 2500 * 128)
        normal = sample("10.0.0.3", 100, 100 * 1000)

        attack_result = policy.decide([attack])[0]
        normal_result = policy.decide([normal])[0]

        self.assertTrue(attack_result.suspicious)
        self.assertEqual(attack_result.action, "RATE_LIMIT")

        self.assertFalse(normal_result.suspicious)
        self.assertEqual(normal_result.action, "ALLOW")

if __name__ == "__main__":
    unittest.main()
