"""Pure policy logic shared by the optional live SDN adapter and its tests.

The live adapter cannot observe TCP SYN flags from ordinary OpenFlow 1.3
aggregate counters.  It therefore uses packet rate, mean packet size, bit rate,
and destination-port fan-out.  These are lab heuristics, not a production IDS.
"""
from __future__ import annotations

from dataclasses import dataclass

from .fairness import weighted_max_min
from .models import FlowSample


@dataclass(frozen=True)
class SdnPolicyConfig:
    capacity_kbps: float = 10_000.0
    attacker_cap_kbps: float = 1_500.0
    poll_seconds: float = 5.0
    medium_pps: float = 400.0
    high_pps: float = 1_000.0
    small_packet_bytes: float = 256.0
    port_fanout_threshold: int = 8
    high_bps_threshold: float = 1_000_000.0
    score_threshold: float = 0.75


@dataclass(frozen=True)
class SdnDecision:
    src_ip: str
    suspicious: bool
    score: float
    reasons: tuple[str, ...]
    offered_kbps: float
    admitted_kbps: float
    allocated_kbps: float
    action: str


class SdnSourcePolicy:
    """Detect high-rate small-packet sources, cap them, then share capacity fairly."""

    def __init__(self, config: SdnPolicyConfig | None = None) -> None:
        self.config = config or SdnPolicyConfig()
        if self.config.capacity_kbps <= 0 or self.config.attacker_cap_kbps < 0:
            raise ValueError("capacity must be positive and attacker cap non-negative")
        if self.config.poll_seconds <= 0:
            raise ValueError("poll_seconds must be positive")

    def classify(self, sample: FlowSample) -> tuple[bool, float, tuple[str, ...]]:
        c = self.config
        score = 0.0
        reasons: list[str] = []
        if sample.pps >= c.high_pps:
            score += 0.45
            reasons.append(f"high packet rate ({sample.pps:.0f} pps)")
        elif sample.pps >= c.medium_pps:
            score += 0.25
            reasons.append(f"elevated packet rate ({sample.pps:.0f} pps)")
        if sample.pps >= c.medium_pps and sample.avg_packet_bytes <= c.small_packet_bytes:
            score += 0.30
            reasons.append(f"small mean packet size ({sample.avg_packet_bytes:.0f} bytes)")
        if sample.unique_dst_ports >= c.port_fanout_threshold:
            score += 0.25
            reasons.append(f"destination-port fan-out ({sample.unique_dst_ports})")
        if sample.bps >= c.high_bps_threshold:
            score += 0.15
            reasons.append(f"high bit rate ({sample.bps / 1_000_000:.2f} Mbit/s)")
        score = min(score, 1.0)
        return score >= c.score_threshold, score, tuple(reasons)

    def decide(self, samples: list[FlowSample]) -> list[SdnDecision]:
        intermediate: dict[str, tuple[float, float, bool, float, tuple[str, ...]]] = {}
        admitted: dict[str, float] = {}
        for sample in samples:
            suspicious, score, reasons = self.classify(sample)
            offered_kbps = sample.bps / 1000.0
            admitted_kbps = (
                min(offered_kbps, self.config.attacker_cap_kbps)
                if suspicious else offered_kbps
            )
            admitted[sample.src_ip] = admitted_kbps
            intermediate[sample.src_ip] = (
                offered_kbps, admitted_kbps, suspicious, score, reasons
            )

        allocations = weighted_max_min(admitted, self.config.capacity_kbps)
        decisions: list[SdnDecision] = []
        for src_ip, (offered, admitted_kbps, suspicious, score, reasons) in intermediate.items():
            allocated = allocations[src_ip]
            limited = allocated < offered * 0.98 if offered > 0 else False
            if suspicious and not limited:
                # This can occur if a configured cap exceeds measured demand.
                action = "DETECTED"
            else:
                action = "RATE_LIMIT" if limited else "ALLOW"
            decisions.append(SdnDecision(
                src_ip=src_ip,
                suspicious=suspicious,
                score=score,
                reasons=reasons,
                offered_kbps=offered,
                admitted_kbps=admitted_kbps,
                allocated_kbps=allocated,
                action=action,
            ))
        return decisions
