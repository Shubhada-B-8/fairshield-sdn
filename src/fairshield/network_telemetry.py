"""Network health telemetry for FairShield SDN V3."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from statistics import mean


@dataclass(frozen=True)
class NetworkMetrics:
    latency_ms: float | None
    jitter_ms: float | None
    probe_loss_ratio: float | None
    reliability: float | None
    rx_throughput_mbps: float
    tx_throughput_mbps: float
    link_utilization: float | None
    cpu_percent: float | None
    memory_percent: float | None

    def to_dict(self) -> dict:
        return asdict(self)


class NetworkTelemetry:
    """Collect active-probe and interface-counter network measurements.

    Probe loss/reliability describe only the probes recorded here.
    They are not estimates of all application packet loss.
    """

    def __init__(self, link_capacity_mbps: float | None = None):
        if link_capacity_mbps is not None and link_capacity_mbps <= 0:
            raise ValueError("link_capacity_mbps must be positive")

        self.link_capacity_mbps = link_capacity_mbps
        self._probe_total = 0
        self._probe_success = 0
        self._rtts: list[float] = []
        self._last_rtt: float | None = None

        self._last_counters: tuple[int, int, float] | None = None
        self._has_throughput_sample = False
        self._rx_mbps = 0.0
        self._tx_mbps = 0.0

        self._cpu_percent: float | None = None
        self._memory_percent: float | None = None

    def record_probe(self, success: bool, rtt_ms: float | None = None) -> None:
        """Record one probe result and its RTT when successful."""
        self._probe_total += 1

        if not success:
            return

        if rtt_ms is None or rtt_ms < 0:
            raise ValueError("successful probes require a non-negative RTT")

        self._probe_success += 1
        self._rtts.append(float(rtt_ms))

    def update_interface_counters(
        self, rx_bytes: int, tx_bytes: int, timestamp: float
    ) -> None:
        """Calculate throughput from cumulative interface byte counters."""
        if rx_bytes < 0 or tx_bytes < 0:
            raise ValueError("byte counters cannot be negative")

        current = (int(rx_bytes), int(tx_bytes), float(timestamp))

        if self._last_counters is not None:
            old_rx, old_tx, old_time = self._last_counters
            elapsed = current[2] - old_time

            if elapsed <= 0:
                raise ValueError("timestamp must increase")

            rx_delta = current[0] - old_rx
            tx_delta = current[1] - old_tx

            # A counter reset establishes a new baseline.
            if rx_delta < 0:
                rx_delta = current[0]
            if tx_delta < 0:
                tx_delta = current[1]

            self._rx_mbps = rx_delta * 8 / elapsed / 1_000_000
            self._has_throughput_sample = True
            self._tx_mbps = tx_delta * 8 / elapsed / 1_000_000

        self._last_counters = current

    def update_system_metrics(
        self,
        cpu_percent: float | None = None,
        memory_percent: float | None = None,
    ) -> None:
        """Store optional CPU and memory utilization percentages."""
        for name, value in (
            ("cpu_percent", cpu_percent),
            ("memory_percent", memory_percent),
        ):
            if value is not None and not 0 <= value <= 100:
                raise ValueError(f"{name} must be between 0 and 100")

        self._cpu_percent = cpu_percent
        self._memory_percent = memory_percent

    @property
    def has_throughput_sample(self) -> bool:
        """Whether at least one real counter interval was measured."""
        return self._has_throughput_sample

    def snapshot(self) -> NetworkMetrics:
        """Return current metrics and consume the current probe window."""
        latency = mean(self._rtts) if self._rtts else None

        jitter = None
        if len(self._rtts) >= 2:
            jitter = mean(
                abs(b - a)
                for a, b in zip(self._rtts, self._rtts[1:])
            )

        reliability = None
        loss = None
        if self._probe_total:
            reliability = self._probe_success / self._probe_total
            loss = 1.0 - reliability

        utilization = None
        if self.link_capacity_mbps is not None:
            utilization = min(
                1.0,
                max(self._rx_mbps, self._tx_mbps)
                / self.link_capacity_mbps,
            )

        result = NetworkMetrics(
            latency_ms=latency,
            jitter_ms=jitter,
            probe_loss_ratio=loss,
            reliability=reliability,
            rx_throughput_mbps=self._rx_mbps,
            tx_throughput_mbps=self._tx_mbps,
            link_utilization=utilization,
            cpu_percent=self._cpu_percent,
            memory_percent=self._memory_percent,
        )

        self._probe_total = 0
        self._probe_success = 0
        self._rtts.clear()

        return result
