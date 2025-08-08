"""
Flow Tracker
=============
Aggregates raw packets into network flows using the 5-tuple key:
  (src_ip, dst_ip, src_port, dst_port, protocol)

Flows are maintained in memory and flushed to the database when:
  - The flow is inactive for flow_timeout seconds
  - The flow is explicitly closed (FIN/RST)
  - The tracker is shut down
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable

from app.core.config import get_settings
from app.core.logging import get_logger
from app.services.collector.base import RawPacket

logger = get_logger(__name__)


@dataclass
class FlowRecord:
    """In-memory flow accumulator."""

    flow_key: tuple
    src_ip: str
    dst_ip: str
    src_port: int | None
    dst_port: int | None
    protocol: str
    interface: str
    data_source: str

    flow_start: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_seen: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    packet_count: int = 0
    byte_count: int = 0

    # TCP-specific
    tcp_flags_seen: set = field(default_factory=set)
    tcp_syn_count: int = 0
    tcp_fin_count: int = 0
    tcp_rst_count: int = 0

    def update(self, packet: RawPacket) -> None:
        """Apply a packet to this flow."""
        self.packet_count += 1
        self.byte_count += packet.length
        self.last_seen = packet.timestamp

        if packet.tcp_flags:
            self.tcp_flags_seen.add(packet.tcp_flags)
            if "SYN" in packet.tcp_flags:
                self.tcp_syn_count += 1
            if "FIN" in packet.tcp_flags:
                self.tcp_fin_count += 1
            if "RST" in packet.tcp_flags:
                self.tcp_rst_count += 1

    @property
    def duration_sec(self) -> float:
        return (self.last_seen - self.flow_start).total_seconds()

    @property
    def packets_per_sec(self) -> float:
        d = max(self.duration_sec, 0.001)
        return self.packet_count / d

    @property
    def bytes_per_sec(self) -> float:
        d = max(self.duration_sec, 0.001)
        return self.byte_count / d

    @property
    def avg_packet_size(self) -> float:
        if self.packet_count == 0:
            return 0.0
        return self.byte_count / self.packet_count

    def to_dict(self) -> dict:
        return {
            "src_ip": self.src_ip,
            "dst_ip": self.dst_ip,
            "src_port": self.src_port,
            "dst_port": self.dst_port,
            "protocol": self.protocol,
            "interface": self.interface,
            "data_source": self.data_source,
            "flow_start": self.flow_start,        # datetime object (not ISO string)
            "flow_end": self.last_seen,            # datetime object (not ISO string)
            "duration_sec": self.duration_sec,
            "packet_count": self.packet_count,
            "byte_count": self.byte_count,
            "packets_per_sec": self.packets_per_sec,
            "bytes_per_sec": self.bytes_per_sec,
            "avg_packet_size": self.avg_packet_size,
            "tcp_flags": "|".join(sorted(self.tcp_flags_seen)) if self.tcp_flags_seen else None,
            "tcp_syn_count": self.tcp_syn_count,
            "tcp_fin_count": self.tcp_fin_count,
            "tcp_rst_count": self.tcp_rst_count,
        }


class FlowTracker:
    """
    Tracks active flows and expires them based on timeout.
    Thread-safe via asyncio.

    On flow expiry, calls the registered on_flow_expired callback.
    """

    def __init__(
        self,
        flow_timeout: int | None = None,
        on_flow_expired: Callable[[FlowRecord], None] | None = None,
    ):
        settings = get_settings()
        self.flow_timeout = flow_timeout or settings.flow_timeout
        self.on_flow_expired = on_flow_expired
        self._flows: dict[tuple, FlowRecord] = {}
        self._new_flows_this_second: int = 0
        self._lock = asyncio.Lock()

    @property
    def active_flow_count(self) -> int:
        return len(self._flows)

    def _make_key(self, packet: RawPacket) -> tuple:
        """Create a canonical 5-tuple flow key (bidrectional for TCP)."""
        src = (packet.src_ip, packet.src_port or 0)
        dst = (packet.dst_ip, packet.dst_port or 0)
        # Normalise direction: always use lexically smaller endpoint first
        # This merges forward and return traffic into one flow
        if packet.protocol in ("TCP", "UDP"):
            if src > dst:
                src, dst = dst, src
        return (*src, *dst, packet.protocol)

    async def process_packet(self, packet: RawPacket) -> FlowRecord | None:
        """
        Process a packet and update the matching flow.
        Returns the FlowRecord if the flow was just created.
        """
        key = self._make_key(packet)
        async with self._lock:
            if key not in self._flows:
                self._flows[key] = FlowRecord(
                    flow_key=key,
                    src_ip=packet.src_ip,
                    dst_ip=packet.dst_ip,
                    src_port=packet.src_port,
                    dst_port=packet.dst_port,
                    protocol=packet.protocol,
                    interface=packet.interface,
                    data_source=packet.data_source,
                )
                self._new_flows_this_second += 1
                return self._flows[key]

            self._flows[key].update(packet)

            # Close TCP flows on FIN or RST
            if packet.tcp_flags and ("FIN" in packet.tcp_flags or "RST" in packet.tcp_flags):
                expired = self._flows.pop(key)
                if self.on_flow_expired:
                    self.on_flow_expired(expired)

        return None

    async def expire_stale_flows(self) -> list[FlowRecord]:
        """Remove and return flows that have been inactive for flow_timeout seconds."""
        now = datetime.now(timezone.utc)
        expired = []
        async with self._lock:
            stale_keys = [
                k for k, f in self._flows.items()
                if (now - f.last_seen).total_seconds() > self.flow_timeout
            ]
            for key in stale_keys:
                flow = self._flows.pop(key)
                expired.append(flow)
                if self.on_flow_expired:
                    self.on_flow_expired(flow)

        if expired:
            logger.debug("flows_expired", count=len(expired))
        return expired

    def reset_new_flow_counter(self) -> int:
        """Return and reset the new-flow counter (call every second)."""
        count = self._new_flows_this_second
        self._new_flows_this_second = 0
        return count

    async def flush_all(self) -> list[FlowRecord]:
        """Flush all active flows (called on shutdown)."""
        async with self._lock:
            flows = list(self._flows.values())
            self._flows.clear()
        return flows
