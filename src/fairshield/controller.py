from __future__ import annotations

from .detector import RuleBasedDetector
from .fairness import weighted_max_min
from .models import Decision, FlowSample


class FairShieldController:
    """Policy engine that caps detected attack sources before fair allocation."""

    def __init__(self, link_capacity_pps: float = 500.0,
                 attacker_cap_pps: float = 5.0,
                 detector: RuleBasedDetector | None = None) -> None:
        if link_capacity_pps <= 0 or attacker_cap_pps < 0:
            raise ValueError("capacity must be > 0 and attacker cap must be >= 0")
        self.link_capacity_pps = float(link_capacity_pps)
        self.attacker_cap_pps = float(attacker_cap_pps)
        self.detector = detector or RuleBasedDetector()

    def decide(self, samples: list[FlowSample]) -> list[Decision]:
        detections = {s.src_ip: self.detector.detect(s) for s in samples}
        admitted: dict[str, float] = {}
        actions: dict[str, tuple[str, str]] = {}
        for sample in samples:
            detection = detections[sample.src_ip]
            if detection.suspicious:
                admitted[sample.src_ip] = min(sample.pps, self.attacker_cap_pps)
                actions[sample.src_ip] = (
                    "RATE_LIMIT",
                    "; ".join(detection.reasons) or "anomalous traffic",
                )
            else:
                admitted[sample.src_ip] = sample.pps
                actions[sample.src_ip] = ("ALLOW", "within detector policy")

        allocations = weighted_max_min(admitted, self.link_capacity_pps)
        return [
            Decision(
                src_ip=s.src_ip,
                action=actions[s.src_ip][0],
                offered_pps=s.pps,
                admitted_demand_pps=admitted[s.src_ip],
                allocated_pps=allocations[s.src_ip],
                reason=actions[s.src_ip][1],
            )
            for s in samples
        ]
