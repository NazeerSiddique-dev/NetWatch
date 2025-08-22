"""Alerts API routes."""

from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select, func

from app.db.session import get_db_session
from app.models.alert import Alert

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.get("")
async def list_alerts(
    severity: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    alert_type: Optional[str] = Query(None),
    interface: Optional[str] = Query(None),
    hours: int = Query(default=24, ge=1, le=720),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
):
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    async with get_db_session() as session:
        stmt = select(Alert).where(Alert.created_at >= since)
        if severity:
            stmt = stmt.where(Alert.severity == severity.upper())
        if status:
            stmt = stmt.where(Alert.status == status.upper())
        if alert_type:
            stmt = stmt.where(Alert.alert_type == alert_type)
        if interface:
            stmt = stmt.where(Alert.interface == interface)

        total = (await session.execute(
            select(func.count()).select_from(stmt.subquery())
        )).scalar() or 0

        stmt = stmt.order_by(Alert.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        result = await session.execute(stmt)
        alerts = result.scalars().all()

        return {
            "alerts": [_alert_to_dict(a) for a in alerts],
            "total": total,
            "page": page,
            "page_size": page_size,
        }


@router.get("/{alert_id}")
async def get_alert(alert_id: str):
    async with get_db_session() as session:
        result = await session.execute(select(Alert).where(Alert.id == alert_id))
        alert = result.scalar_one_or_none()
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")
        return _alert_to_dict(alert)


@router.post("/resolve-all")
async def resolve_all_alerts():
    async with get_db_session() as session:
        # Find all active alerts
        result = await session.execute(select(Alert).where(Alert.status == "ACTIVE"))
        alerts = result.scalars().all()
        
        now = datetime.now(timezone.utc)
        resolved_count = 0
        for alert in alerts:
            alert.status = "RESOLVED"
            alert.resolved_at = now
            resolved_count += 1
            
        return {"message": f"Resolved {resolved_count} active alerts", "count": resolved_count}


@router.patch("/{alert_id}")
async def update_alert(alert_id: str, body: dict):
    async with get_db_session() as session:
        result = await session.execute(select(Alert).where(Alert.id == alert_id))
        alert = result.scalar_one_or_none()
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")

        new_status = body.get("status", "").upper()
        if new_status in ("ACKNOWLEDGED", "RESOLVED"):
            alert.status = new_status
            if new_status == "ACKNOWLEDGED":
                alert.acknowledged_at = datetime.now(timezone.utc)
                alert.acknowledged_by = body.get("acknowledged_by", "user")
            elif new_status == "RESOLVED":
                alert.resolved_at = datetime.now(timezone.utc)
        return _alert_to_dict(alert)


def _alert_to_dict(a: Alert) -> dict:
    return {
        "id": a.id, "severity": a.severity, "alert_type": a.alert_type,
        "status": a.status, "title": a.title, "message": a.message,
        "interface": a.interface, "src_ip": a.src_ip, "dst_ip": a.dst_ip,
        "anomaly_score": a.anomaly_score, "detector": a.detector,
        "observed_value": a.observed_value, "baseline_value": a.baseline_value,
        "deviation_sigma": a.deviation_sigma, "metric_name": a.metric_name,
        "acknowledged_at": a.acknowledged_at.isoformat() if a.acknowledged_at else None,
        "resolved_at": a.resolved_at.isoformat() if a.resolved_at else None,
        "acknowledged_by": a.acknowledged_by,
        "experiment_id": a.experiment_id, "data_source": a.data_source,
        "created_at": a.created_at.isoformat(), "updated_at": a.updated_at.isoformat(),
    }
