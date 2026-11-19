"""Per-source TCP SYN telemetry accounting for FairShield V3."""

from __future__ import annotations


class SynTelemetry:
    """Aggregate packet-in observations and per-flow SYN counter deltas."""

    def __init__(self):
        self._pending: dict[tuple[int, str], int] = {}
        self._previous: dict[tuple[int, str, str], int] = {}

    def record_packet_in(
        self, dpid: int, src_ip: str, count: int = 1
    ) -> None:
        """Record initial SYN packets observed by the controller."""
        if count < 0:
            raise ValueError("count cannot be negative")

        key = (int(dpid), str(src_ip))
        self._pending[key] = self._pending.get(key, 0) + int(count)

    def prime_flow_counter(
        self, dpid: int, src_ip: str, flow_id: str
    ) -> None:
        """Initialize a newly installed OpenFlow counter at zero."""
        key = (int(dpid), str(src_ip), str(flow_id))
        self._previous.setdefault(key, 0)

    def update_flow_counter(
        self,
        dpid: int,
        src_ip: str,
        flow_id: str,
        cumulative_packets: int,
    ) -> int:
        """Convert an individual OpenFlow counter into a packet delta."""
        if cumulative_packets < 0:
            raise ValueError("cumulative_packets cannot be negative")

        source_key = (int(dpid), str(src_ip))
        flow_key = (int(dpid), str(src_ip), str(flow_id))
        current = int(cumulative_packets)

        previous = self._previous.get(flow_key)
        self._previous[flow_key] = current

        # First observation establishes a baseline. Packet-in telemetry
        # separately records the initial SYN.
        if previous is None:
            return 0

        # Handle a counter reset or flow recreation.
        delta = current - previous
        if delta < 0:
            delta = current

        self._pending[source_key] = (
            self._pending.get(source_key, 0) + delta
        )
        return delta

    def consume_window(self, dpid: int, src_ip: str) -> int:
        """Return and clear the pending SYN count for one source."""
        return self._pending.pop((int(dpid), str(src_ip)), 0)

    def remove_flow(
        self, dpid: int, src_ip: str, flow_id: str
    ) -> None:
        """Remove one expired OpenFlow counter."""
        self._previous.pop(
            (int(dpid), str(src_ip), str(flow_id)), None
        )

    def remove_source(self, dpid: int, src_ip: str) -> None:
        """Remove all telemetry state belonging to a source."""
        source_key = (int(dpid), str(src_ip))
        self._pending.pop(source_key, None)

        for key in list(self._previous):
            if key[:2] == source_key:
                self._previous.pop(key, None)
