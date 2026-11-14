from __future__ import annotations

from dataclasses import dataclass
from .models import Detection, FlowSample


@dataclass(frozen=True)
class DetectorConfig:
    pps_threshold: float = 180.0
    high_pps_threshold: float = 450.0
    syn_ratio_threshold: float = 0.75
    port_scan_threshold: int = 10
    bps_threshold: float = 1_000_000.0
    score_threshold: float = 0.55


class RuleBasedDetector:
    """Interpretable baseline detector; simulation labels are not consulted."""

    def __init__(self, config: DetectorConfig | None = None) -> None:
        self.config = config or DetectorConfig()

    def detect(self, sample: FlowSample) -> Detection:
        c = self.config
        score = 0.0
        reasons: list[str] = []

        if sample.pps >= c.high_pps_threshold:
            score += 0.50
            reasons.append(f"very high packet rate ({sample.pps:.1f} pps)")
        elif sample.pps >= c.pps_threshold:
            score += 0.30
            reasons.append(f"high packet rate ({sample.pps:.1f} pps)")

        if sample.syn_ratio >= c.syn_ratio_threshold:
            score += 0.30
            reasons.append(f"high SYN ratio ({sample.syn_ratio:.2f})")

        if sample.unique_dst_ports >= c.port_scan_threshold:
            score += 0.25
            reasons.append(f"destination-port fan-out ({sample.unique_dst_ports})")

        if sample.bps >= c.bps_threshold:
            score += 0.15
            reasons.append(f"high bit rate ({sample.bps:.0f} bit/s)")

        score = min(score, 1.0)
        return Detection(score >= c.score_threshold, score, tuple(reasons))
