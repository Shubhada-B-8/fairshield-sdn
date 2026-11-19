"""Explainable QoS assessment based on measured network telemetry."""

from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class QoSConfig:
    latency_watch_ms: float = 20.0
    latency_critical_ms: float = 100.0
    jitter_watch_ms: float = 10.0
    jitter_critical_ms: float = 30.0
    loss_watch_ratio: float = 0.01
    loss_critical_ratio: float = 0.05
    utilization_watch: float = 0.75
    utilization_critical: float = 0.90
    cpu_watch_percent: float = 80.0
    cpu_critical_percent: float = 95.0
    memory_watch_percent: float = 85.0
    memory_critical_percent: float = 95.0


@dataclass(frozen=True)
class QoSAssessment:
    status: str
    score: float
    recommendation: str
    reasons: tuple[str, ...]

    def to_dict(self):
        return asdict(self)


class QoSOptimizer:
    """Rule-based QoS advisor; recommendations do not enforce network changes."""

    def __init__(self, config: QoSConfig | None = None):
        self.config = config or QoSConfig()

    def evaluate(self, metrics: dict) -> QoSAssessment:
        c = self.config
        watch = []
        critical = []
        score = 100.0
        measured = 0

        checks = (
            ("latency_ms", c.latency_watch_ms, c.latency_critical_ms,
             "Latency", "ms", False),
            ("jitter_ms", c.jitter_watch_ms, c.jitter_critical_ms,
             "Jitter", "ms", False),
            ("probe_loss_ratio", c.loss_watch_ratio, c.loss_critical_ratio,
             "Probe loss", "%", True),
            ("link_utilization", c.utilization_watch, c.utilization_critical,
             "Link utilization", "%", True),
            ("cpu_percent", c.cpu_watch_percent, c.cpu_critical_percent,
             "CPU usage", "%", False),
            ("memory_percent", c.memory_watch_percent, c.memory_critical_percent,
             "Memory usage", "%", False),
        )

        for key, warning, severe, label, unit, ratio in checks:
            value = metrics.get(key)
            if value is None:
                continue

            value = float(value)
            measured += 1
            shown = value * 100 if ratio else value
            suffix = "%" if ratio or unit == "%" else " ms"

            if value >= severe:
                critical.append(f"{label} critical ({shown:.2f}{suffix})")
                score -= 25
            elif value >= warning:
                watch.append(f"{label} elevated ({shown:.2f}{suffix})")
                score -= 10

        score = max(0.0, score)

        if measured == 0:
            return QoSAssessment(
                status="INSUFFICIENT_DATA",
                score=0.0,
                recommendation="No usable QoS measurements are available. Verify controller telemetry and active probes.",
                reasons=("Waiting for measured network data.",),
            )

        if critical:
            status = "CRITICAL"
            recommendation = (
                "Investigate the bottleneck immediately; prioritize essential "
                "traffic and review admission limits before increasing capacity."
            )
            reasons = tuple(critical + watch)
        elif len(watch) >= 2:
            status = "CONGESTED"
            recommendation = (
                "Apply QoS prioritization to essential traffic and inspect "
                "the busiest links and sources."
            )
            reasons = tuple(watch)
        elif watch:
            status = "WATCH"
            recommendation = (
                "Monitor the affected metric and prepare traffic prioritization "
                "if degradation continues."
            )
            reasons = tuple(watch)
        else:
            status = "NORMAL"
            recommendation = (
                "Maintain the current policy; continue monitoring latency, "
                "loss, utilization, and resource usage."
            )
            reasons = ("No configured QoS warning threshold exceeded.",)

        return QoSAssessment(
            status=status,
            score=score,
            recommendation=recommendation,
            reasons=reasons,
        )
