"""
1-Minute Metric Aggregator
===========================
Background task that rolls up Metric1s rows into Metric1m summaries.
Runs every 60 seconds and aggregates the previous completed minute.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone, timedelta

from app.core.logging import get_logger
from app.db.session import get_db_session

logger = get_logger(__name__)
_running = False


async def run_metric_aggregator() -> None:
    """Roll up 1-second metrics into 1-minute aggregates indefinitely."""
    global _running
    _running = True
    logger.info("metric_aggregator_starting")

    while _running:
        try:
            # Sleep until the top of the next minute
            now = datetime.now(timezone.utc)
            next_minute = now.replace(second=0, microsecond=0) + timedelta(minutes=1)
            sleep_secs = (next_minute - now).total_seconds()
            await asyncio.sleep(max(sleep_secs, 1))

            # Aggregate the minute that just completed
            minute_start = next_minute - timedelta(minutes=1)
            minute_end = next_minute
            await _aggregate_minute(minute_start, minute_end)

        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.error("metric_aggregator_error", error=str(exc))
            await asyncio.sleep(10)  # back off on error

    logger.info("metric_aggregator_stopped")


async def _aggregate_minute(start: datetime, end: datetime) -> None:
    """Aggregate all Metric1s rows in [start, end) into one Metric1m row per interface."""
    from sqlalchemy import select, func
    from app.models.metric import Metric1s, Metric1m

    async with get_db_session() as session:
        # Get all 1-second rows in this window
        result = await session.execute(
            select(Metric1s).where(
                Metric1s.timestamp >= start,
                Metric1s.timestamp < end,
            )
        )
        rows = result.scalars().all()

    if not rows:
        return

    # Group by interface
    by_iface: dict[str, list] = {}
    for row in rows:
        by_iface.setdefault(row.interface, []).append(row)

    for iface, iface_rows in by_iface.items():
        n = len(iface_rows)

        def avg(attr: str) -> float:
            vals = [getattr(r, attr) for r in iface_rows if getattr(r, attr) is not None]
            return sum(vals) / len(vals) if vals else 0.0

        def total(attr: str) -> float:
            return sum(getattr(r, attr) or 0 for r in iface_rows)

        anomaly_count = sum(1 for r in iface_rows if r.is_anomalous)
        total_pkt = total("tcp_packets") + total("udp_packets") + total("icmp_packets") + \
                    total("dns_packets") + total("http_packets") + total("https_packets") + \
                    total("other_packets")

        def proto_pct(attr: str) -> float:
            return (total(attr) / total_pkt * 100) if total_pkt > 0 else 0.0

        async with get_db_session() as session:
            # Upsert: delete existing row for this minute+iface if present
            existing = await session.execute(
                select(Metric1m).where(
                    Metric1m.timestamp == start,
                    Metric1m.interface == iface,
                )
            )
            ex = existing.scalar_one_or_none()
            if ex:
                await session.delete(ex)

            agg = Metric1m(
                timestamp=start,
                interface=iface,
                data_source=iface_rows[-1].data_source,
                total_flows=int(total("active_flows")),
                avg_rx_mbps=avg("rx_mbps"),
                avg_tx_mbps=avg("tx_mbps"),
                max_rx_mbps=max(r.rx_mbps for r in iface_rows),
                max_tx_mbps=max(r.tx_mbps for r in iface_rows),
                avg_packets_per_sec=avg("total_packets_per_sec"),
                avg_latency_ms=avg("avg_latency_ms"),
                avg_packet_loss_pct=avg("packet_loss_pct"),
                total_bytes=int(total("rx_bytes_per_sec") + total("tx_bytes_per_sec")),
                total_packets=int(total("total_packets_per_sec")),
                anomaly_count=anomaly_count,
                tcp_pct=proto_pct("tcp_packets"),
                udp_pct=proto_pct("udp_packets"),
                icmp_pct=proto_pct("icmp_packets"),
                dns_pct=proto_pct("dns_packets"),
                http_pct=proto_pct("http_packets"),
                https_pct=proto_pct("https_packets"),
                other_pct=proto_pct("other_packets"),
            )
            session.add(agg)

    logger.info("metrics_aggregated", minute=start.isoformat(), interfaces=list(by_iface.keys()))
