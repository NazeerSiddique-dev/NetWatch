"""Metrics API routes."""

from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import APIRouter, Query
from sqlalchemy import select, func

from app.db.session import get_db_session
from app.models.metric import Metric1s, Metric1m
from app.models.alert import Alert
from app.core.config import get_settings
from app.services.anomaly.detector_factory import get_detector
from app.services.monitoring.interface_monitor import get_interfaces_async

router = APIRouter(prefix="/api/metrics", tags=["metrics"])


@router.get("/realtime")
async def realtime_metrics():
    """Current network metrics snapshot."""
    settings = get_settings()
    async with get_db_session() as session:
        result = await session.execute(
            select(Metric1s)
            .order_by(Metric1s.timestamp.desc())
            .limit(1)
        )
        latest = result.scalar_one_or_none()
        if latest:
            return _metric1s_to_dict(latest)

    # No data yet — return zeroed snapshot
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "interface": settings.default_interface,
        "data_source": settings.collector_mode.value.upper(),
        "rx_mbps": 0.0, "tx_mbps": 0.0, "total_mbps": 0.0,
        "total_packets_per_sec": 0.0, "active_flows": 0,
        "packet_loss_pct": 0.0, "avg_latency_ms": None,
        "anomaly_score": None, "is_anomalous": False,
        "protocols": {"tcp": 0, "udp": 0, "icmp": 0, "dns": 0, "http": 0, "https": 0, "other": 0},
    }


@router.get("/history")
async def metric_history(
    interface: Optional[str] = Query(None),
    minutes: int = Query(default=60, ge=1, le=1440),
    granularity: str = Query(default="1m"),
):
    """Historical metric series for charting."""
    settings = get_settings()
    iface = interface or settings.default_interface
    since = datetime.now(timezone.utc) - timedelta(minutes=minutes)

    async with get_db_session() as session:
        if granularity == "1s" and minutes <= 30:
            result = await session.execute(
                select(Metric1s)
                .where(Metric1s.interface == iface, Metric1s.timestamp >= since)
                .order_by(Metric1s.timestamp.asc())
            )
            rows = result.scalars().all()
            return {"interface": iface, "granularity": "1s",
                    "data": [_metric1s_to_dict(r) for r in rows]}
        else:
            result = await session.execute(
                select(Metric1m)
                .where(Metric1m.interface == iface, Metric1m.timestamp >= since)
                .order_by(Metric1m.timestamp.asc())
            )
            rows = result.scalars().all()
            return {"interface": iface, "granularity": "1m",
                    "data": [_metric1m_to_dict(r) for r in rows]}


@router.get("/status")
async def network_status():
    """High-level network status summary for the dashboard header."""
    settings = get_settings()
    interfaces = await get_interfaces_async()
    active = [i for i in interfaces if i["is_up"]]

    async with get_db_session() as session:
        latest_result = await session.execute(
            select(Metric1s).order_by(Metric1s.timestamp.desc()).limit(1)
        )
        latest = latest_result.scalar_one_or_none()

        alert_count_result = await session.execute(
            select(func.count()).select_from(Alert).where(Alert.status.in_(["NEW", "ACTIVE"]))
        )
        anomaly_count = alert_count_result.scalar() or 0

    return {
        "status": "HEALTHY" if anomaly_count == 0 else "DEGRADED",
        "interface": settings.default_interface,
        "data_source": settings.collector_mode.value.upper(),
        "interfaces_total": len(interfaces),
        "interfaces_active": len(active),
        "active_flows": latest.active_flows if latest else 0,
        "packets_per_sec": latest.total_packets_per_sec if latest else 0.0,
        "bandwidth_mbps": (latest.rx_mbps + latest.tx_mbps) if latest else 0.0,
        "packet_loss_pct": latest.packet_loss_pct if latest else 0.0,
        "avg_latency_ms": latest.avg_latency_ms if latest else None,
        "anomalies_active": anomaly_count,
        "critical_alerts": 0,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/detector")
async def detector_info():
    """Return anomaly detector configuration and state."""
    return get_detector().get_info()


def _metric1s_to_dict(m: Metric1s) -> dict:
    return {
        "timestamp": m.timestamp.isoformat(),
        "interface": m.interface,
        "data_source": m.data_source,
        "rx_mbps": m.rx_mbps, "tx_mbps": m.tx_mbps,
        "total_mbps": m.rx_mbps + m.tx_mbps,
        "rx_packets_per_sec": m.rx_packets_per_sec,
        "tx_packets_per_sec": m.tx_packets_per_sec,
        "total_packets_per_sec": m.total_packets_per_sec,
        "avg_latency_ms": m.avg_latency_ms, "min_latency_ms": m.min_latency_ms,
        "max_latency_ms": m.max_latency_ms, "packet_loss_pct": m.packet_loss_pct,
        "active_flows": m.active_flows, "new_flows": m.new_flows,
        "anomaly_score": m.anomaly_score, "is_anomalous": bool(m.is_anomalous),
        "protocols": {
            "tcp": m.tcp_packets, "udp": m.udp_packets, "icmp": m.icmp_packets,
            "dns": m.dns_packets, "http": m.http_packets, "https": m.https_packets,
            "other": m.other_packets,
        },
    }


def _metric1m_to_dict(m: Metric1m) -> dict:
    return {
        "timestamp": m.timestamp.isoformat(),
        "interface": m.interface,
        "data_source": m.data_source,
        "avg_rx_mbps": m.avg_rx_mbps, "avg_tx_mbps": m.avg_tx_mbps,
        "max_rx_mbps": m.max_rx_mbps, "max_tx_mbps": m.max_tx_mbps,
        "avg_packets_per_sec": m.avg_packets_per_sec,
        "avg_latency_ms": m.avg_latency_ms,
        "avg_packet_loss_pct": m.avg_packet_loss_pct,
        "total_bytes": m.total_bytes, "total_packets": m.total_packets,
        "anomaly_count": m.anomaly_count,
        "protocols": {
            "tcp": m.tcp_pct, "udp": m.udp_pct, "icmp": m.icmp_pct,
            "dns": m.dns_pct, "http": m.http_pct, "https": m.https_pct, "other": m.other_pct,
        },
    }
