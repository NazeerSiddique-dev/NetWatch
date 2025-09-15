"""
Interface Monitor
==================
Discovers network interfaces and polls their statistics using psutil.
Works without elevated privileges.
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from typing import Any

import psutil

from app.core.logging import get_logger

logger = get_logger(__name__)

_prev_stats: dict[str, Any] = {}
_prev_time: float = 0.0


def _get_all_interfaces() -> list[dict[str, Any]]:
    """Return current stats for all interfaces."""
    global _prev_stats, _prev_time

    stats = psutil.net_if_stats()
    addrs = psutil.net_if_addrs()
    io = psutil.net_io_counters(pernic=True)

    now = time.monotonic()
    elapsed = now - _prev_time if _prev_time else 1.0
    _prev_time = now

    interfaces = []
    for name, stat in stats.items():
        addr_info = addrs.get(name, [])
        io_info = io.get(name, None)
        prev_io = _prev_stats.get(name)

        # Extract IP and MAC
        mac = None
        ip = None
        prefix_len = None
        for addr in addr_info:
            if addr.family.name == "AF_PACKET":
                mac = addr.address
            elif addr.family.name == "AF_INET":
                ip = addr.address
                prefix_len = addr.netmask

        rx_bytes = io_info.bytes_recv if io_info else 0
        tx_bytes = io_info.bytes_sent if io_info else 0
        rx_packets = io_info.packets_recv if io_info else 0
        tx_packets = io_info.packets_sent if io_info else 0

        # Compute rates
        rx_bps = 0.0
        tx_bps = 0.0
        pps = 0.0
        if prev_io and elapsed > 0:
            rx_diff = max(rx_bytes - prev_io.get("rx_bytes", 0), 0)
            tx_diff = max(tx_bytes - prev_io.get("tx_bytes", 0), 0)
            pkt_diff = max(
                (rx_packets + tx_packets) - prev_io.get("total_packets", 0), 0
            )
            rx_bps = rx_diff / elapsed
            tx_bps = tx_diff / elapsed
            pps = pkt_diff / elapsed

        _prev_stats[name] = {
            "rx_bytes": rx_bytes,
            "tx_bytes": tx_bytes,
            "total_packets": rx_packets + tx_packets,
        }

        interfaces.append({
            "name": name,
            "mac_address": mac,
            "ip_address": ip,
            "ip_prefix_len": prefix_len,
            "mtu": stat.mtu,
            "is_up": stat.isup,
            "rx_bytes": rx_bytes,
            "tx_bytes": tx_bytes,
            "rx_packets": rx_packets,
            "tx_packets": tx_packets,
            "rx_errors": io_info.errin if io_info else 0,
            "tx_errors": io_info.errout if io_info else 0,
            "rx_dropped": io_info.dropin if io_info else 0,
            "tx_dropped": io_info.dropout if io_info else 0,
            "rx_bandwidth_mbps": round(rx_bps * 8 / 1_000_000, 3),
            "tx_bandwidth_mbps": round(tx_bps * 8 / 1_000_000, 3),
            "packets_per_sec": round(pps, 1),
            "last_seen": datetime.now(timezone.utc).isoformat(),
        })

    return interfaces


async def get_interfaces_async() -> list[dict[str, Any]]:
    """Non-blocking interface discovery (runs psutil in executor)."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _get_all_interfaces)
