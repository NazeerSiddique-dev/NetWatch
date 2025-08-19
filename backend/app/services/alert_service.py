"""
Alert Service
==============
Creates, persists, and broadcasts anomaly alerts.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from app.core.logging import get_logger
from app.db.redis_client import publish_alert
from app.models.alert import Alert, AlertSeverity, AlertType
from app.schemas.alert import AlertCreate
from app.services.anomaly.base import AnomalyResult
from app.schemas.metric import RealtimeMetric

logger = get_logger(__name__)

# In-memory store for alerts (used when DB session unavailable in worker context)
_alert_queue: asyncio.Queue = asyncio.Queue(maxsize=1000)


def _score_to_severity(score: float, deviation: float | None) -> str:
    """Map anomaly score to alert severity."""
    sigma = deviation or 0.0
    if sigma > 6.0 or score > 0.9:
        return AlertSeverity.CRITICAL.value
    elif sigma > 5.0 or score > 0.75:
        return AlertSeverity.HIGH.value
    elif sigma > 4.0 or score > 0.5:
        return AlertSeverity.MEDIUM.value
    elif sigma > 3.0 or score > 0.3:
        return AlertSeverity.LOW.value
    return AlertSeverity.INFO.value


async def create_alert_from_anomaly(
    result: AnomalyResult,
    metric: RealtimeMetric,
    experiment_id: str | None = None,
) -> dict:
    """Build an alert, persist it to the database, and broadcast it."""
    from app.db.session import get_db_session

    severity = _score_to_severity(result.score, result.deviation_sigma)

    # Human-readable title
    type_titles = {
        "traffic_spike": "Traffic Spike Detected",
        "packet_rate_spike": "Packet Rate Spike",
        "connection_spike": "Connection Surge",
        "port_anomaly": "Unusual Port Activity",
        "destination_anomaly": "Unexpected Destinations",
        "protocol_anomaly": "Protocol Distribution Anomaly",
        "statistical_anomaly": "Statistical Anomaly",
    }
    alert_type = result.anomaly_type or "statistical_anomaly"
    title = type_titles.get(alert_type, "Anomaly Detected")

    obs = result.observed_value
    base = result.baseline_value
    sigma = result.deviation_sigma
    msg_parts = [f"Anomaly detected on {metric.interface}."]
    if result.metric_name:
        msg_parts.append(f"Metric: {result.metric_name}.")
    if obs is not None and base is not None:
        msg_parts.append(f"Observed: {obs:.1f}, Baseline: {base:.1f}.")
    if sigma:
        msg_parts.append(f"Deviation: {sigma:.2f}σ.")
    message = " ".join(msg_parts)

    now = datetime.now(timezone.utc)

    # ── Persist to database ───────────────────────────────────────────────────
    alert_id = None
    try:
        async with get_db_session() as session:
            alert_row = Alert(
                severity=severity,
                alert_type=alert_type,
                status="ACTIVE",
                title=title,
                message=message,
                interface=metric.interface,
                anomaly_score=result.score,
                detector=result.details.get("detector", "unknown") if result.details else "unknown",
                observed_value=result.observed_value,
                baseline_value=result.baseline_value,
                deviation_sigma=result.deviation_sigma,
                metric_name=result.metric_name,
                experiment_id=experiment_id,
                data_source=metric.data_source,
            )
            session.add(alert_row)
            await session.flush()
            alert_id = str(alert_row.id)
    except Exception as db_err:
        logger.error("alert_db_persist_failed", error=str(db_err))

    alert_dict = {
        "id": alert_id,
        "severity": severity,
        "alert_type": alert_type,
        "status": "ACTIVE",
        "title": title,
        "message": message,
        "interface": metric.interface,
        "anomaly_score": result.score,
        "detector": result.details.get("detector", "unknown") if result.details else "unknown",
        "observed_value": result.observed_value,
        "baseline_value": result.baseline_value,
        "deviation_sigma": result.deviation_sigma,
        "metric_name": result.metric_name,
        "experiment_id": experiment_id,
        "data_source": metric.data_source,
        "created_at": now.isoformat(),
    }

    # Publish to Redis stream for WebSocket broadcasting
    await publish_alert(alert_dict)
    _alert_queue.put_nowait(alert_dict)

    logger.info(
        "alert_created",
        severity=severity,
        type=alert_type,
        interface=metric.interface,
        score=result.score,
    )

    return alert_dict


async def get_pending_alerts() -> list[dict]:
    """Drain the in-memory alert queue."""
    alerts = []
    while not _alert_queue.empty():
        try:
            alerts.append(_alert_queue.get_nowait())
        except asyncio.QueueEmpty:
            break
    return alerts
