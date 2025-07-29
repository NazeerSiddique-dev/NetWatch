"""
Alert ORM Model
================
Represents a generated network anomaly alert.
Alerts are created by the anomaly detection service and persisted here.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class AlertSeverity(str, Enum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AlertStatus(str, Enum):
    ACTIVE = "ACTIVE"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"


class AlertType(str, Enum):
    TRAFFIC_SPIKE = "traffic_spike"
    PACKET_RATE_SPIKE = "packet_rate_spike"
    CONNECTION_SPIKE = "connection_spike"
    PORT_ANOMALY = "port_anomaly"
    DESTINATION_ANOMALY = "destination_anomaly"
    PROTOCOL_ANOMALY = "protocol_anomaly"
    STATISTICAL_ANOMALY = "statistical_anomaly"
    SYSTEM_ERROR = "system_error"


class Alert(Base, UUIDMixin, TimestampMixin):
    """Represents a network anomaly alert."""

    __tablename__ = "alerts"

    # Classification
    severity: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    alert_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(16), default=AlertStatus.ACTIVE.value, nullable=False, index=True
    )

    # Human-readable
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)

    # Context
    interface: Mapped[str | None] = mapped_column(String(64))
    src_ip: Mapped[str | None] = mapped_column(String(45))
    dst_ip: Mapped[str | None] = mapped_column(String(45))
    src_port: Mapped[int | None] = mapped_column(Integer)
    dst_port: Mapped[int | None] = mapped_column(Integer)
    protocol: Mapped[str | None] = mapped_column(String(16))

    # Detection data
    anomaly_score: Mapped[float | None] = mapped_column(Float)
    detector: Mapped[str | None] = mapped_column(String(64))

    # Observed value vs baseline
    observed_value: Mapped[float | None] = mapped_column(Float)
    baseline_value: Mapped[float | None] = mapped_column(Float)
    deviation_sigma: Mapped[float | None] = mapped_column(Float)
    metric_name: Mapped[str | None] = mapped_column(String(64))

    # Resolution
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    acknowledged_by: Mapped[str | None] = mapped_column(String(128))

    # Linked experiment
    experiment_id: Mapped[str | None] = mapped_column(String(36))

    # Data source
    data_source: Mapped[str] = mapped_column(String(16), default="SYNTHETIC")

    def __repr__(self) -> str:
        return f"<Alert [{self.severity}] {self.alert_type}: {self.title[:40]}>"
