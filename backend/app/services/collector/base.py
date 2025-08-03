"""
Traffic Collector Abstract Base
=================================
All collector implementations must inherit from TrafficCollector.
This abstraction allows swapping pcap, synthetic, or other backends
without touching the processing layer.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import AsyncIterator


@dataclass
class RawPacket:
    """
    A minimal representation of a captured packet.
    Contains only the metadata needed for flow aggregation.
    Full payload is intentionally NOT stored.
    """

    timestamp: datetime
    src_ip: str
    dst_ip: str
    src_port: int | None
    dst_port: int | None
    protocol: str          # TCP | UDP | ICMP | DNS | HTTP | HTTPS | OTHER
    length: int            # bytes
    tcp_flags: str | None  # e.g. "SYN", "FIN|ACK"
    interface: str
    data_source: str = "REAL"  # REAL | SYNTHETIC | LAB

    @classmethod
    def from_dict(cls, d: dict) -> "RawPacket":
        return cls(
            timestamp=datetime.fromisoformat(d["timestamp"]) if isinstance(d["timestamp"], str) else d["timestamp"],
            src_ip=d["src_ip"],
            dst_ip=d["dst_ip"],
            src_port=d.get("src_port"),
            dst_port=d.get("dst_port"),
            protocol=d.get("protocol", "OTHER"),
            length=d.get("length", 0),
            tcp_flags=d.get("tcp_flags"),
            interface=d.get("interface", "unknown"),
            data_source=d.get("data_source", "REAL"),
        )

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "src_ip": self.src_ip,
            "dst_ip": self.dst_ip,
            "src_port": self.src_port,
            "dst_port": self.dst_port,
            "protocol": self.protocol,
            "length": self.length,
            "tcp_flags": self.tcp_flags,
            "interface": self.interface,
            "data_source": self.data_source,
        }


class TrafficCollector(abc.ABC):
    """
    Abstract base class for all traffic collectors.

    A collector captures packets from a source (real interface or synthetic
    generator) and makes them available to the processing layer.
    """

    def __init__(self, interface: str, data_source: str = "REAL"):
        self.interface = interface
        self.data_source = data_source
        self._running = False
        self._packets_captured = 0
        self._packets_dropped = 0
        self._started_at: datetime | None = None

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def packets_captured(self) -> int:
        return self._packets_captured

    @property
    def packets_dropped(self) -> int:
        return self._packets_dropped

    @property
    def uptime_seconds(self) -> float:
        if self._started_at is None:
            return 0.0
        return (datetime.now(timezone.utc) - self._started_at).total_seconds()

    @abc.abstractmethod
    async def start(self) -> None:
        """Start the collector. Should set self._running = True."""
        ...

    @abc.abstractmethod
    async def stop(self) -> None:
        """Stop the collector. Should set self._running = False."""
        ...

    @abc.abstractmethod
    async def packets(self) -> AsyncIterator[RawPacket]:
        """
        Async generator that yields RawPacket objects.
        Implementations should yield continuously while self._running is True.
        """
        ...

    def get_stats(self) -> dict:
        return {
            "mode": self.data_source,
            "interface": self.interface,
            "running": self._running,
            "packets_captured": self._packets_captured,
            "packets_dropped": self._packets_dropped,
            "uptime_seconds": self.uptime_seconds,
        }
