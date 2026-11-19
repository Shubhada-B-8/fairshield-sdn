"""V3 AI-to-SDN detection adapter.

Shadow mode is the default: AI predictions are evaluated, but the existing
rule-based detector remains authoritative for network decisions.
"""
from __future__ import annotations

from dataclasses import dataclass

from .detector import RuleBasedDetector
from .models import Detection, FlowSample
from .v3_ai import AIRiskDetector


@dataclass(frozen=True)
class V3AIDetectorConfig:
    mode: str = "shadow"
    fusion: str = "any"
    fail_open: bool = True

    def __post_init__(self):
        if self.mode not in {"shadow", "hybrid"}:
            raise ValueError("mode must be 'shadow' or 'hybrid'")
        if self.fusion not in {"any", "both", "ai"}:
            raise ValueError("fusion must be 'any', 'both', or 'ai'")


class V3AIDetectionAdapter:
    """Combine AI risk predictions with the existing rule-based detector."""

    def __init__(
        self,
        ai_detector: AIRiskDetector | None = None,
        rule_detector: RuleBasedDetector | None = None,
        config: V3AIDetectorConfig | None = None,
    ):
        self.ai_detector = ai_detector
        self.rule_detector = rule_detector or RuleBasedDetector()
        self.config = config or V3AIDetectorConfig()
        self.window_total_pps = 0.0
        self.ai_available = ai_detector is not None
        self.ai_errors = 0
        self.prediction_count = 0

    def set_window_total_pps(self, total_pps: float) -> None:
        if total_pps < 0:
            raise ValueError("window_total_pps cannot be negative")
        self.window_total_pps = float(total_pps)

    def detect(self, sample: FlowSample) -> Detection:
        rule_result = self.rule_detector.detect(sample)

        if self.ai_detector is None:
            return self._fallback(rule_result, "AI model unavailable")

        try:
            ai_suspicious, ai_score = self.ai_detector.predict(
                sample, self.window_total_pps
            )
            self.prediction_count += 1
            self.ai_available = True
        except Exception as exc:
            self.ai_errors += 1
            self.ai_available = False
            if self.config.fail_open:
                return self._fallback(
                    rule_result, f"AI inference failed: {type(exc).__name__}"
                )
            raise

        ai_reason = f"AI attack probability ({ai_score:.3f})"
        reasons = tuple(rule_result.reasons) + (ai_reason,)

        # Shadow mode never changes the existing V2 decision.
        if self.config.mode == "shadow":
            return Detection(
                suspicious=rule_result.suspicious,
                score=rule_result.score,
                reasons=reasons,
            )

        # Hybrid mode is explicitly configurable.
        if self.config.fusion == "any":
            suspicious = rule_result.suspicious or ai_suspicious
        elif self.config.fusion == "both":
            suspicious = rule_result.suspicious and ai_suspicious
        else:
            suspicious = ai_suspicious

        return Detection(
            suspicious=suspicious,
            score=max(rule_result.score, ai_score),
            reasons=reasons,
        )

    @staticmethod
    def _fallback(rule_result: Detection, reason: str) -> Detection:
        return Detection(
            suspicious=rule_result.suspicious,
            score=rule_result.score,
            reasons=tuple(rule_result.reasons) + (reason,),
        )

    def status(self) -> dict:
        return {
            "mode": self.config.mode,
            "fusion": self.config.fusion,
            "ai_available": self.ai_available,
            "ai_errors": self.ai_errors,
            "prediction_count": self.prediction_count,
            "window_total_pps": self.window_total_pps,
        }
