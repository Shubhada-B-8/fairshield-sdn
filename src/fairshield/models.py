from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class FlowSample:
    """One source-level flow observation over a fixed measurement window."""
    window_id: int
    src_ip: str
    dst_ip: str
    packets: int
    byte_count: int
    syn_packets: int
    unique_dst_ports: int
    duration_s: float = 1.0
    label: str = "unknown"  # Simulation ground truth only; never used by the detector.

    @property
    def pps(self) -> float:
        return self.packets / max(self.duration_s, 1e-9)

    @property
    def bps(self) -> float:
        return (self.byte_count * 8) / max(self.duration_s, 1e-9)

    @property
    def syn_ratio(self) -> float:
        return self.syn_packets / max(self.packets, 1)

    @property
    def avg_packet_bytes(self) -> float:
        return self.byte_count / max(self.packets, 1)

    def features(self) -> dict[str, float]:
        return {
            "pps": self.pps,
            "bps": self.bps,
            "syn_ratio": self.syn_ratio,
            "unique_dst_ports": float(self.unique_dst_ports),
            "avg_packet_bytes": self.avg_packet_bytes,
        }

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result.update(self.features())
        return result


@dataclass(frozen=True)
class Detection:
    suspicious: bool
    score: float
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class Decision:
    src_ip: str
    action: str
    offered_pps: float
    admitted_demand_pps: float
    allocated_pps: float
    reason: str
