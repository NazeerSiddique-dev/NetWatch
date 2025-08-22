"""
Runtime Settings API
====================
Manages dynamic system configuration via the database.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.db.session import get_db_session
from app.models.settings import SystemSettings
from app.services.anomaly.detector_factory import update_detector_threshold

router = APIRouter(prefix="/api/settings", tags=["settings"])


class SettingsUpdateSchema(BaseModel):
    anomaly_threshold: float = Field(None, ge=1.0, le=10.0)
    alert_cooldown_seconds: int = Field(None, ge=10, le=3600)
    active_interface: str = Field(None, description="The network interface to sniff")


@router.get("")
async def get_settings():
    """Retrieve the current runtime system configuration."""
    from sqlalchemy import select
    async with get_db_session() as session:
        result = await session.execute(select(SystemSettings).where(SystemSettings.id == 1))
        settings = result.scalar_one_or_none()
        if not settings:
            return {}
        
        return {
            "anomaly_threshold": settings.anomaly_threshold,
            "alert_cooldown_seconds": settings.alert_cooldown_seconds,
            "retention_raw_flows_hours": settings.retention_raw_flows_hours,
            "retention_metrics_1s_hours": settings.retention_metrics_1s_hours,
            "retention_metrics_1m_days": settings.retention_metrics_1m_days,
            "retention_alerts_days": settings.retention_alerts_days,
            "detector_type": settings.detector_type,
            "active_interface": settings.active_interface,
        }


@router.patch("")
async def update_settings(payload: SettingsUpdateSchema):
    """Update runtime system configuration."""
    from sqlalchemy import select
    async with get_db_session() as session:
        result = await session.execute(select(SystemSettings).where(SystemSettings.id == 1))
        settings = result.scalar_one_or_none()
        
        if payload.anomaly_threshold is not None:
            settings.anomaly_threshold = payload.anomaly_threshold
            update_detector_threshold(payload.anomaly_threshold)
            
        if payload.alert_cooldown_seconds is not None:
            settings.alert_cooldown_seconds = payload.alert_cooldown_seconds
            
        if payload.active_interface is not None:
            settings.active_interface = payload.active_interface
            
        session.add(settings)
        return {"status": "success"}
