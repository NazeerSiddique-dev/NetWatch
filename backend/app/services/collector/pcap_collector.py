"""
PCAP Packet Collector (Scapy/libpcap)
=======================================
Real packet capture from a network interface using Scapy.
Requires CAP_NET_RAW capability or root privileges.

Usage:
  sudo python3 -m app.services.collector.runner
  OR: grant capability to python3 binary
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import AsyncIterator

from app.core.logging import get_logger
from app.services.collector.base import RawPacket, TrafficCollector

logger = get_logger(__name__)

# Port-to-protocol mapping
_PORT_PROTOCOL_MAP = {
    53: "DNS",
    80: "HTTP",
    443: "HTTPS",
    8080: "HTTP",
    8443: "HTTPS",
}


def _classify_protocol(pkt) -> str:
    """Classify a Scapy packet into a human-readable protocol name."""
    try:
        from scapy.layers.inet import IP, TCP, UDP, ICMP
        from scapy.layers.dns import DNS

        if pkt.haslayer(ICMP):
            return "ICMP"
        if pkt.haslayer(DNS):
            return "DNS"
        if pkt.haslayer(TCP):
            tcp = pkt[TCP]
            sport, dport = tcp.sport, tcp.dport
            if dport in _PORT_PROTOCOL_MAP:
                return _PORT_PROTOCOL_MAP[dport]
            if sport in _PORT_PROTOCOL_MAP:
                return _PORT_PROTOCOL_MAP[sport]
            return "TCP"
        if pkt.haslayer(UDP):
            udp = pkt[UDP]
            sport, dport = udp.sport, udp.dport
            if dport in _PORT_PROTOCOL_MAP:
                return _PORT_PROTOCOL_MAP[dport]
            return "UDP"
    except Exception:
        pass
    return "OTHER"


def _extract_tcp_flags(pkt) -> str | None:
    """Extract TCP flags as a human-readable string."""
    try:
        from scapy.layers.inet import TCP
        if pkt.haslayer(TCP):
            flags = pkt[TCP].flags
            flag_names = []
            if flags & 0x02:
                flag_names.append("SYN")
            if flags & 0x10:
                flag_names.append("ACK")
            if flags & 0x01:
                flag_names.append("FIN")
            if flags & 0x04:
                flag_names.append("RST")
            if flags & 0x08:
                flag_names.append("PSH")
            return "|".join(flag_names) if flag_names else "ACK"
    except Exception:
        pass
    return None


class PcapCollector(TrafficCollector):
    """
    Captures real network packets using Scapy/libpcap.
    Requires root or CAP_NET_RAW capability.
    """

    def __init__(self, interface: str, bpf_filter: str = ""):
        super().__init__(interface=interface, data_source="REAL")
        self.bpf_filter = bpf_filter
        self._packet_queue: asyncio.Queue[RawPacket] = asyncio.Queue(maxsize=10_000)
        self._capture_thread = None
        self._loop: asyncio.AbstractEventLoop | None = None

    async def start(self) -> None:
        """Start background thread for Scapy capture."""
        import threading

        try:
            from scapy.all import conf
            conf.verb = 0  # Suppress Scapy output
        except ImportError as exc:
            raise RuntimeError(
                "Scapy is not installed. Install with: pip install scapy"
            ) from exc

        self._loop = asyncio.get_event_loop()
        self._running = True
        self._started_at = datetime.now(timezone.utc)

        self._capture_thread = threading.Thread(
            target=self._capture_loop,
            name=f"pcap-{self.interface}",
            daemon=True,
        )
        self._capture_thread.start()
        logger.info(
            "pcap_collector_started",
            interface=self.interface,
            filter=self.bpf_filter or "none",
        )

    async def stop(self) -> None:
        self._running = False
        if self._capture_thread:
            self._capture_thread.join(timeout=3.0)
        logger.info(
            "pcap_collector_stopped",
            packets_captured=self._packets_captured,
        )

    def _capture_loop(self) -> None:
        """Run in a background thread; feeds packets into the async queue."""
        try:
            from scapy.all import sniff
            sniff(
                iface=self.interface,
                filter=self.bpf_filter or None,
                prn=self._handle_packet,
                stop_filter=lambda _: not self._running,
                store=False,
            )
        except PermissionError:
            logger.error(
                "pcap_permission_denied",
                interface=self.interface,
                hint="Run with sudo or grant CAP_NET_RAW to python3",
            )
            self._running = False
        except Exception as exc:
            logger.error("pcap_capture_error", error=str(exc))
            self._running = False

    def _handle_packet(self, pkt) -> None:
        """Called from Scapy's sniff thread for each packet."""
        try:
            from scapy.layers.inet import IP, TCP, UDP

            if not pkt.haslayer(IP):
                return  # Skip non-IP packets (ARP, etc.)

            ip = pkt[IP]
            sport = pkt[TCP].sport if pkt.haslayer(TCP) else (
                pkt[UDP].sport if pkt.haslayer(UDP) else None
            )
            dport = pkt[TCP].dport if pkt.haslayer(TCP) else (
                pkt[UDP].dport if pkt.haslayer(UDP) else None
            )

            raw = RawPacket(
                timestamp=datetime.now(timezone.utc),
                src_ip=ip.src,
                dst_ip=ip.dst,
                src_port=sport,
                dst_port=dport,
                protocol=_classify_protocol(pkt),
                length=len(pkt),
                tcp_flags=_extract_tcp_flags(pkt),
                interface=self.interface,
                data_source="REAL",
            )
            self._packets_captured += 1

            # Thread-safe enqueue
            if self._loop and self._loop.is_running():
                try:
                    self._packet_queue.put_nowait(raw)
                except asyncio.QueueFull:
                    self._packets_dropped += 1

        except Exception as exc:
            logger.debug("packet_parse_error", error=str(exc))

    async def packets(self) -> AsyncIterator[RawPacket]:
        """Yield captured packets from the queue."""
        while self._running or not self._packet_queue.empty():
            try:
                pkt = await asyncio.wait_for(self._packet_queue.get(), timeout=1.0)
                yield pkt
            except asyncio.TimeoutError:
                continue
            except Exception as exc:
                logger.error("packet_queue_error", error=str(exc))
                break
