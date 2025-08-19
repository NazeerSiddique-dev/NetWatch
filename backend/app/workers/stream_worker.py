"""
Stream Worker
==============
Background worker that runs the full pipeline:
  Collector → Flow Tracker → Metric Aggregator → Anomaly Detector → DB + WebSocket

Runs as a long-running asyncio task, started alongside the FastAPI app.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from app.core.config import CollectorMode, get_settings
from app.core.logging import get_logger
from app.db.redis_client import publish_flow
from app.services.anomaly.detector_factory import get_detector
from app.services.alert_service import create_alert_from_anomaly
from app.services.collector.base import RawPacket
from app.services.flow_processor.flow_tracker import FlowRecord, FlowTracker
from app.services.flow_processor.metric_aggregator import MetricAggregator

logger = get_logger(__name__)

_worker_running = False
_stats = {
    "flows_processed": 0,
    "metrics_published": 0,
    "anomalies_detected": 0,
    "packets_processed": 0,
}

# Alert cooldown tracking: (interface, alert_type) -> last alert timestamp
_last_alert: dict[tuple, datetime] = {}


def get_worker_stats() -> dict:
    return dict(_stats)


async def _persist_flow(flow: FlowRecord) -> None:
    """Persist an expired flow to the database."""
    _stats["flows_processed"] += 1
    try:
        from app.db.session import get_db_session
        from app.models.flow import Flow
        async with get_db_session() as session:
            db_flow = Flow(**{k: v for k, v in flow.to_dict().items()})
            session.add(db_flow)
    except Exception as exc:
        logger.error("flow_persist_error", error=str(exc))

    # Also broadcast via WebSocket
    try:
        from app.api.websocket import broadcast_flow
        await broadcast_flow(flow.to_dict())
    except Exception:
        pass


async def _persist_metric(metric) -> None:
    """Persist a 1-second metric snapshot to the database."""
    _stats["metrics_published"] += 1
    try:
        from app.db.session import get_db_session
        from app.models.metric import Metric1s
        async with get_db_session() as session:
            db_metric = Metric1s(
                timestamp=metric.timestamp,
                interface=metric.interface,
                rx_bytes_per_sec=metric.rx_mbps * 125_000,
                tx_bytes_per_sec=metric.tx_mbps * 125_000,
                total_bytes_per_sec=(metric.rx_mbps + metric.tx_mbps) * 125_000,
                rx_mbps=metric.rx_mbps,
                tx_mbps=metric.tx_mbps,
                rx_packets_per_sec=metric.rx_packets_per_sec,
                tx_packets_per_sec=metric.tx_packets_per_sec,
                total_packets_per_sec=metric.total_packets_per_sec,
                avg_latency_ms=metric.avg_latency_ms,
                min_latency_ms=metric.min_latency_ms,
                max_latency_ms=metric.max_latency_ms,
                packet_loss_pct=metric.packet_loss_pct,
                tcp_packets=int(metric.protocols.tcp),
                udp_packets=int(metric.protocols.udp),
                icmp_packets=int(metric.protocols.icmp),
                dns_packets=int(metric.protocols.dns),
                http_packets=int(metric.protocols.http),
                https_packets=int(metric.protocols.https),
                other_packets=int(metric.protocols.other),
                active_flows=metric.active_flows,
                new_flows=metric.new_flows,
                anomaly_score=metric.anomaly_score,
                is_anomalous=metric.is_anomalous,
                data_source=metric.data_source,
            )
            session.add(db_metric)
    except Exception as exc:
        logger.error("metric_persist_error", error=str(exc))


def _build_collector(target_interface: str):
    """Build the appropriate collector based on settings."""
    settings = get_settings()
    mode = settings.collector_mode

    if mode == CollectorMode.SYNTHETIC:
        from app.services.collector.synthetic_collector import SyntheticCollector
        return SyntheticCollector(interface=target_interface, base_pps=150.0)

    elif mode == CollectorMode.PCAP:
        from app.services.collector.pcap_collector import PcapCollector
        return PcapCollector(interface=target_interface)

    else:  # AUTO: try pcap, fall back to synthetic
        try:
            from app.services.collector.pcap_collector import PcapCollector
            import os
            if os.geteuid() == 0:
                return PcapCollector(interface=target_interface)
        except Exception:
            pass
        from app.services.collector.synthetic_collector import SyntheticCollector
        logger.warning("collector_mode_fallback", reason="pcap unavailable, using synthetic")
        return SyntheticCollector(interface=target_interface, base_pps=150.0)


async def _run_pipeline_iteration(target_interface: str) -> str:
    """Run one iteration of the pipeline. Returns new interface string if it changed, else empty."""
    settings = get_settings()
    collector = _build_collector(target_interface)
    tracker = FlowTracker()
    aggregator = MetricAggregator(
        interface=target_interface,
        data_source=collector.data_source,
    )
    detector = get_detector()

    logger.info("pipeline_iteration_starting", interface=target_interface, mode=collector.data_source)
    await collector.start()

    interface_changed = asyncio.Event()
    next_interface = ""

    async def expire_flows_loop():
        while _worker_running and not interface_changed.is_set():
            await asyncio.sleep(10)
            expired = await tracker.expire_stale_flows()
            for flow in expired:
                await _persist_flow(flow)

    async def metric_flush_loop():
        nonlocal next_interface
        from app.api.websocket import broadcast_metric
        from app.db.session import get_db_session
        from sqlalchemy import select
        from app.models.settings import SystemSettings

        while _worker_running and not interface_changed.is_set():
            await asyncio.sleep(settings.metric_interval)
            
            # Check if interface has changed dynamically
            try:
                async with get_db_session() as session:
                    res = await session.execute(select(SystemSettings.active_interface).where(SystemSettings.id == 1))
                    db_iface = res.scalar_one_or_none()
                    check_iface = db_iface or settings.default_interface
                    if check_iface != target_interface:
                        next_interface = check_iface
                        interface_changed.set()
                        break
            except Exception as e:
                logger.debug("interface_check_failed", error=str(e))

            aggregator.active_flows = tracker.active_flow_count
            aggregator.new_flows = tracker.reset_new_flow_counter()

            metric = await aggregator.flush()
            features = aggregator.get_feature_vector(metric)

            # Anomaly detection
            result = detector.update(features)
            metric.anomaly_score = result.score
            metric.is_anomalous = result.is_anomalous

            if result.is_anomalous:
                _stats["anomalies_detected"] += 1
                key = (metric.interface, result.anomaly_type or "unknown")
                now = datetime.now(timezone.utc)
                last = _last_alert.get(key)
                if last is None or (now - last).total_seconds() > settings.alert_cooldown_seconds:
                    _last_alert[key] = now
                    await create_alert_from_anomaly(result, metric)

            await broadcast_metric(metric.model_dump())
            await _persist_metric(metric)

    async def consume_packets():
        async for pkt in collector.packets():
            if not _worker_running or interface_changed.is_set():
                break
            _stats["packets_processed"] += 1
            await aggregator.record_packet(pkt)
            await tracker.process_packet(pkt)

    t1 = asyncio.create_task(consume_packets())
    t2 = asyncio.create_task(expire_flows_loop())
    t3 = asyncio.create_task(metric_flush_loop())

    try:
        while _worker_running and not interface_changed.is_set():
            await asyncio.sleep(0.5)
    except asyncio.CancelledError:
        pass
    finally:
        t1.cancel()
        t2.cancel()
        t3.cancel()
        await collector.stop()
        
        logger.info("pipeline_iteration_flushing")
        try:
            async def fast_flush():
                remaining = await tracker.flush_all()
                if remaining:
                    logger.info("flushing_stale_flows", count=len(remaining))
                    limit = min(len(remaining), 100)
                    for flow in remaining[:limit]:
                        await _persist_flow(flow)
            await asyncio.wait_for(fast_flush(), timeout=3.0)
        except asyncio.TimeoutError:
            logger.warning("pipeline_shutdown_timeout")
        except Exception as e:
            logger.error("pipeline_shutdown_error", error=str(e))

    return next_interface


async def run_worker() -> None:
    """Main worker loop with dynamic interface hot-swapping."""
    global _worker_running
    settings = get_settings()
    _worker_running = True
    
    target_iface = settings.default_interface
    
    try:
        from app.db.session import get_db_session
        from sqlalchemy import select
        from app.models.settings import SystemSettings
        async with get_db_session() as session:
            res = await session.execute(select(SystemSettings.active_interface).where(SystemSettings.id == 1))
            db_iface = res.scalar_one_or_none()
            if db_iface:
                target_iface = db_iface
    except Exception:
        pass

    try:
        while _worker_running:
            next_iface = await _run_pipeline_iteration(target_iface)
            if next_iface:
                logger.info("hot_swapping_interface", old=target_iface, new=next_iface)
                target_iface = next_iface
            else:
                break
    except asyncio.CancelledError:
        logger.info("stream_worker_cancelled")
    except Exception as exc:
        logger.error("stream_worker_error", error=str(exc))
    finally:
        _worker_running = False
        logger.info("stream_worker_stopped", **_stats)
