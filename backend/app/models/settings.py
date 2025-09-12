"""
System Settings ORM Model
=========================
A singleton table for runtime configuration, allowing dynamic updates
without requiring environment variables or backend restarts.
"""

from sqlalchemy import Integer, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class SystemSettings(Base):
    __tablename__ = "system_settings"

    # Enforce singleton by fixing the ID
    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)

    # Anomaly Detection
    anomaly_threshold: Mapped[float] = mapped_column(Float, default=3.0)
    
    # Alerts
    alert_cooldown_seconds: Mapped[int] = mapped_column(Integer, default=60)
    
    # Data Retention
    retention_raw_flows_hours: Mapped[int] = mapped_column(Integer, default=24)
    retention_metrics_1s_hours: Mapped[int] = mapped_column(Integer, default=24)
    retention_metrics_1m_days: Mapped[int] = mapped_column(Integer, default=30)
    retention_alerts_days: Mapped[int] = mapped_column(Integer, default=90)

    # Detector type (for info)
    detector_type: Mapped[str] = mapped_column(String, default="statistical")
    
    # Active sniffing interface (null means use fallback config)
    active_interface: Mapped[str | None] = mapped_column(String, nullable=True)
