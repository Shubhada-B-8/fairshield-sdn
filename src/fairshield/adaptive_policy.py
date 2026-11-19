"""V2 feedback-driven adaptive admission control.

This module is deliberately separate from the V1 policy. It consumes measured
network feedback supplied by its caller; it does not itself query Open vSwitch.
The simulator supplies controlled feedback proxies, while a future live adapter
can supply per-source meter and service counters.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from .detector import RuleBasedDetector
from .fairness import weighted_max_min
from .models import FlowSample


@dataclass(frozen=True)
class AdaptivePolicyConfig:
    link_capacity_pps: float = 500.0
    initial_attack_cap_pps: float = 5.0
    min_attack_cap_pps: float = 1.0
    max_attack_cap_pps: float = 40.0
    congestion_utilization: float = 0.90
    headroom_utilization: float = 0.75
    target_legitimate_service: float = 0.95
    meter_drop_relax_threshold: float = 0.10
    decrease_factor: float = 0.75
    increase_factor: float = 1.20
    recovery_windows: int = 2
    detector: RuleBasedDetector | None = field(default=None, compare=False, repr=False)

    def __post_init__(self) -> None:
        if self.link_capacity_pps <= 0:
            raise ValueError("link_capacity_pps must be positive")
        if not (0 <= self.min_attack_cap_pps <= self.initial_attack_cap_pps <= self.max_attack_cap_pps):
            raise ValueError("attack caps must satisfy 0 <= min <= initial <= max")
        if not (0 < self.decrease_factor < 1):
            raise ValueError("decrease_factor must be between 0 and 1")
        if self.increase_factor <= 1:
            raise ValueError("increase_factor must be greater than 1")
        if self.recovery_windows < 1:
            raise ValueError("recovery_windows must be at least 1")
        for name in ("congestion_utilization", "headroom_utilization", "target_legitimate_service", "meter_drop_relax_threshold"):
            value = getattr(self, name)
            if not 0 <= value <= 1:
                raise ValueError(f"{name} must be between 0 and 1")
        if self.headroom_utilization >= self.congestion_utilization:
            raise ValueError("headroom_utilization must be below congestion_utilization")


@dataclass(frozen=True)
class NetworkFeedback:
    """Feedback for the preceding control interval.

    Ratios are in [0, 1]. source_meter_drop_ratio should come from the source's
    OpenFlow meter band counter in a live deployment. A simulator may provide a
    clearly labelled estimate instead.
    """
    capacity_utilization: float = 0.0
    legitimate_service_ratio: float | None = None
    source_meter_drop_ratio: float = 0.0

    def __post_init__(self) -> None:
        for name in ("capacity_utilization", "source_meter_drop_ratio"):
            value = getattr(self, name)
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be between 0 and 1")
        if self.legitimate_service_ratio is not None:
            if not 0.0 <= self.legitimate_service_ratio <= 1.0:
                raise ValueError("legitimate_service_ratio must be between 0 and 1")


@dataclass
class _SourceState:
    cap_pps: float
    normal_streak: int = 0
    attack_latched: bool = False
    last_reason: str = "initial_cap"


@dataclass(frozen=True)
class AdaptiveDecision:
    src_ip: str
    suspicious: bool
    score: float
    reasons: tuple[str, ...]
    offered_pps: float
    admitted_pps: float
    allocated_pps: float
    adaptive_cap_pps: float
    action: str
    adjustment: str


class AdaptiveFairnessController:
    """Adjust suspicious-source caps from closed-loop service feedback.

    Control rule:
      * tighten the cap when the bottleneck is congested or legitimate service
        falls below its target;
      * relax the cap when there is clear headroom but the source meter is
        dropping a material share of that source's traffic;
      * restore the cap gradually after repeated benign observations;
      * then apply weighted max-min allocation to all admitted demands.

    This is a transparent research baseline, not a claim of patent novelty.
    """

    def __init__(self, config: AdaptivePolicyConfig | None = None) -> None:
        self.config = config or AdaptivePolicyConfig()
        self.detector = self.config.detector or RuleBasedDetector()
        self._states: dict[str, _SourceState] = {}

    def state_snapshot(self) -> dict[str, dict[str, float | int | str]]:
        return {
            ip: {"cap_pps": state.cap_pps, "normal_streak": state.normal_streak,
                 "attack_latched": state.attack_latched, "last_reason": state.last_reason}
            for ip, state in sorted(self._states.items())
        }

    def _state_for(self, src_ip: str) -> _SourceState:
        if src_ip not in self._states:
            self._states[src_ip] = _SourceState(self.config.initial_attack_cap_pps)
        return self._states[src_ip]

    def _adjust(self, state: _SourceState, suspicious: bool,
                feedback: NetworkFeedback) -> str:
        c = self.config
        if suspicious:
            state.normal_streak = 0
            service_ratio = feedback.legitimate_service_ratio
            congestion = (
                feedback.capacity_utilization >= c.congestion_utilization
                or (
                    service_ratio is not None
                    and service_ratio < c.target_legitimate_service
                )
            )
            headroom_with_excessive_drops = (
                feedback.capacity_utilization <= c.headroom_utilization
                and service_ratio is not None
                and service_ratio >= c.target_legitimate_service
                and feedback.source_meter_drop_ratio >= c.meter_drop_relax_threshold
            )
            if congestion:
                state.cap_pps = max(c.min_attack_cap_pps,
                                    state.cap_pps * c.decrease_factor)
                state.last_reason = "tighten_congestion_or_legitimate_service"
            elif headroom_with_excessive_drops:
                state.cap_pps = min(c.max_attack_cap_pps,
                                    state.cap_pps * c.increase_factor)
                state.last_reason = "relax_headroom_with_meter_drops"
            else:
                state.last_reason = "hold_hysteresis_band"
            return state.last_reason

        state.normal_streak += 1
        if state.normal_streak >= c.recovery_windows and state.cap_pps < c.initial_attack_cap_pps:
            state.cap_pps = min(c.initial_attack_cap_pps,
                                state.cap_pps * c.increase_factor)
            state.last_reason = "gradual_benign_recovery"
        else:
            state.last_reason = "benign_observation"
        return state.last_reason

    def decide(self, samples: list[FlowSample],
               feedback_by_source: Mapping[str, NetworkFeedback] | None = None) -> list[AdaptiveDecision]:
        feedback_by_source = feedback_by_source or {}
        admitted: dict[str, float] = {}
        rows: dict[str, tuple[FlowSample, bool, float, tuple[str, ...], float, str]] = {}
        for sample in samples:
            detection = self.detector.detect(sample)
            state = self._state_for(sample.src_ip)

            if detection.suspicious:
                state.attack_latched = True
                state.normal_streak = 0

            feedback = feedback_by_source.get(sample.src_ip)
            if feedback is None:
                adjustment = "missing_feedback_hold"
                state.last_reason = adjustment
            else:
                adjustment = self._adjust(state, detection.suspicious, feedback)

            if (state.attack_latched and not detection.suspicious
                    and feedback is not None
                    and state.normal_streak >= self.config.recovery_windows
                    and state.cap_pps >= self.config.initial_attack_cap_pps - 1e-9):
                state.attack_latched = False
                adjustment = "attack_recovery_complete"

            effective_suspicious = detection.suspicious or state.attack_latched
            admitted_pps = min(sample.pps, state.cap_pps) if effective_suspicious else sample.pps
            admitted[sample.src_ip] = admitted_pps
            rows[sample.src_ip] = (
                sample, effective_suspicious, detection.score, detection.reasons,
                state.cap_pps, adjustment,
            )

        allocations = weighted_max_min(admitted, self.config.link_capacity_pps)
        results: list[AdaptiveDecision] = []
        for src_ip, (sample, suspicious, score, reasons, cap, adjustment) in rows.items():
            allocated = allocations[src_ip]
            limited = allocated < sample.pps * 0.98 if sample.pps > 0 else False
            action = "RATE_LIMIT" if limited else "ALLOW"
            results.append(AdaptiveDecision(
                src_ip=src_ip, suspicious=suspicious, score=score,
                reasons=reasons, offered_pps=sample.pps,
                admitted_pps=admitted[src_ip], allocated_pps=allocated,
                adaptive_cap_pps=cap, action=action, adjustment=adjustment,
            ))
        return results
