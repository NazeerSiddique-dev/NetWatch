"""
Synthetic Traffic Collector
============================
Generates realistic synthetic network traffic for demo / testing mode.
No root privileges required.

Produces realistic-looking traffic with:
  - Background "normal" traffic (web browsing, DNS, HTTPS)
  - Configurable traffic scenarios (spikes, bursts, protocol shifts)
  - Proper timestamp progression
  - Realistic IP distributions
"""

from __future__ import annotations

import asyncio
import math
import random
from datetime import datetime, timezone
from enum import Enum
from typing import AsyncIterator

from app.core.logging import get_logger
from app.services.collector.base import RawPacket, TrafficCollector

logger = get_logger(__name__)


class SyntheticScenario(str, Enum):
    """Selectable traffic scenarios for synthetic mode."""
    NORMAL = "normal"
    TRAFFIC_SPIKE = "traffic_spike"
    PACKET_BURST = "packet_burst"
    CONNECTION_BURST = "connection_burst"
    PROTOCOL_SHIFT = "protocol_shift"


# Common internet IPs to simulate real traffic destinations
_COMMON_DESTINATIONS = [
    "142.250.80.46",   # Google
    "151.101.1.69",    # Reddit CDN
    "104.16.132.229",  # Cloudflare
    "13.225.109.17",   # AWS CloudFront
    "52.86.247.34",    # AWS
    "185.60.216.35",   # Facebook
    "199.232.57.153",  # npm CDN
    "8.8.8.8",         # Google DNS
    "1.1.1.1",         # Cloudflare DNS
]

_LOCAL_IPS = [f"192.168.1.{i}" for i in range(2, 30)]

_PROTOCOL_PROFILES = {
    # (protocol, src_port_range, dst_port, weight)
    SyntheticScenario.NORMAL: [
        ("HTTPS", (1024, 65535), 443, 40),
        ("HTTP",  (1024, 65535), 80,  10),
        ("DNS",   (1024, 65535), 53,  20),
        ("TCP",   (1024, 65535), 22,  5),
        ("UDP",   (1024, 65535), None, 15),
        ("ICMP",  None, None, 10),
    ],
    SyntheticScenario.TRAFFIC_SPIKE: [
        ("HTTPS", (1024, 65535), 443, 60),
        ("HTTP",  (1024, 65535), 80,  30),
        ("TCP",   (1024, 65535), 8080, 10),
    ],
    SyntheticScenario.CONNECTION_BURST: [
        ("TCP",   (1024, 65535), 443,  40),
        ("TCP",   (1024, 65535), 80,   30),
        ("TCP",   (1024, 65535), 22,   20),
        ("TCP",   (1024, 65535), 8080, 10),
    ],
    SyntheticScenario.PROTOCOL_SHIFT: [
        ("UDP",   (1024, 65535), None, 70),
        ("ICMP",  None, None, 20),
        ("TCP",   (1024, 65535), 443, 10),
    ],
}


def _weighted_choice(options: list[tuple]) -> tuple:
    """Choose from weighted options."""
    weights = [o[-1] for o in options]
    return random.choices(options, weights=weights, k=1)[0]


class SyntheticCollector(TrafficCollector):
    """
    Generates synthetic network packets for demo mode.
    Supports multiple traffic scenarios that can be changed at runtime.
    """

    def __init__(
        self,
        interface: str = "lo",
        base_pps: float = 100.0,
        scenario: SyntheticScenario = SyntheticScenario.NORMAL,
    ):
        super().__init__(interface=interface, data_source="SYNTHETIC")
        self.base_pps = base_pps
        self.scenario = scenario
        self._stop_event = asyncio.Event()

    async def start(self) -> None:
        self._running = True
        self._started_at = datetime.now(timezone.utc)
        self._stop_event.clear()
        logger.info(
            "synthetic_collector_started",
            interface=self.interface,
            base_pps=self.base_pps,
            scenario=self.scenario.value,
        )

    async def stop(self) -> None:
        self._running = False
        self._stop_event.set()
        logger.info(
            "synthetic_collector_stopped",
            packets_captured=self._packets_captured,
        )

    def set_scenario(self, scenario: SyntheticScenario) -> None:
        """Switch traffic scenario at runtime."""
        self.scenario = scenario
        logger.info("synthetic_scenario_changed", scenario=scenario.value)

    def _current_pps(self) -> float:
        """Compute packet rate based on scenario and time-based variation."""
        t = datetime.now(timezone.utc).timestamp()

        # Add a slow sinusoidal variation to simulate natural traffic rhythm
        natural_variation = 1.0 + 0.3 * math.sin(t / 60.0) + 0.1 * math.sin(t / 10.0)

        multipliers = {
            SyntheticScenario.NORMAL: 1.0,
            SyntheticScenario.TRAFFIC_SPIKE: 8.0 + random.uniform(-1, 1),
            SyntheticScenario.PACKET_BURST: 15.0 + random.uniform(-2, 2),
            SyntheticScenario.CONNECTION_BURST: 5.0 + random.uniform(-0.5, 0.5),
            SyntheticScenario.PROTOCOL_SHIFT: 1.2,
        }
        return self.base_pps * natural_variation * multipliers.get(self.scenario, 1.0)

    def _generate_packet(self) -> RawPacket:
        """Generate a single synthetic packet."""
        profiles = _PROTOCOL_PROFILES.get(self.scenario, _PROTOCOL_PROFILES[SyntheticScenario.NORMAL])
        proto, src_range, dst_port, _ = _weighted_choice(profiles)

        # Source is always local; destination may be external
        src_ip = random.choice(_LOCAL_IPS)
        if proto in ("DNS",) or random.random() < 0.1:
            dst_ip = random.choice(_COMMON_DESTINATIONS[-3:])  # DNS servers
        elif random.random() < 0.7:
            dst_ip = random.choice(_COMMON_DESTINATIONS)
        else:
            dst_ip = random.choice(_LOCAL_IPS)

        src_port = random.randint(*src_range) if src_range else None
        if dst_port is None and proto not in ("ICMP",):
            dst_port = random.randint(1024, 65535)

        # Packet size depends on protocol
        if proto == "DNS":
            length = random.randint(40, 200)
        elif proto in ("HTTP", "HTTPS"):
            length = random.randint(200, 1500)
        elif proto == "ICMP":
            length = random.randint(28, 64)
        else:
            length = random.randint(64, 1400)

        tcp_flags = None
        if proto == "TCP":
            tcp_flags = random.choice(["SYN", "SYN|ACK", "ACK", "FIN|ACK", "PSH|ACK"])

        return RawPacket(
            timestamp=datetime.now(timezone.utc),
            src_ip=src_ip,
            dst_ip=dst_ip,
            src_port=src_port,
            dst_port=dst_port,
            protocol=proto,
            length=length,
            tcp_flags=tcp_flags,
            interface=self.interface,
            data_source="SYNTHETIC",
        )

    async def packets(self) -> AsyncIterator[RawPacket]:
        """Yield synthetic packets at the current rate."""
        while self._running and not self._stop_event.is_set():
            pps = self._current_pps()
            # Sleep interval between packets
            interval = 1.0 / max(pps, 1.0)

            # Batch packets when rate is high to reduce asyncio overhead
            batch_size = max(1, min(int(pps / 10), 50))
            for _ in range(batch_size):
                if not self._running:
                    return
                packet = self._generate_packet()
                self._packets_captured += 1
                yield packet

            await asyncio.sleep(interval * batch_size)
