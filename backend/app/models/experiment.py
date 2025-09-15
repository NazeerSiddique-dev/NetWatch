"""
Experiment ORM Models
======================
Tracks traffic generation experiments and their detection evaluation results.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class ExperimentStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TrafficType(str, Enum):
    NORMAL_TCP = "normal_tcp"
    NORMAL_UDP = "normal_udp"
    ICMP_PING = "icmp_ping"
    HTTP_LIKE = "http_like"
    TRAFFIC_BURST = "traffic_burst"
    CONNECTION_BURST = "connection_burst"
    PORT_ACTIVITY = "port_activity"


class Experiment(Base, UUIDMixin, TimestampMixin):
    """A controlled traffic generation experiment in the Network Lab."""

    __tablename__ = "experiments"

    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    # Status
    status: Mapped[str] = mapped_column(
        String(16), default=ExperimentStatus.PENDING.value, nullable=False, index=True
    )

    # Configuration
    traffic_type: Mapped[str] = mapped_column(String(32), nullable=False)
    src_namespace: Mapped[str | None] = mapped_column(String(64))
    dst_namespace: Mapped[str | None] = mapped_column(String(64))
    src_ip: Mapped[str | None] = mapped_column(String(45))
    dst_ip: Mapped[str | None] = mapped_column(String(45))
    dst_port: Mapped[int | None] = mapped_column(Integer)
    packet_rate: Mapped[int | None] = mapped_column(Integer)   # packets/sec
    duration_sec: Mapped[int | None] = mapped_column(Integer)
    burst_size: Mapped[int | None] = mapped_column(Integer)

    # Timing
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Expected outcome (ground truth)
    expected_anomaly: Mapped[bool] = mapped_column(Integer, default=0)
    expected_anomaly_type: Mapped[str | None] = mapped_column(String(64))

    # Detection result
    anomaly_detected: Mapped[bool | None] = mapped_column(Integer)
    detection_time_ms: Mapped[float | None] = mapped_column(Float)
    detected_alert_id: Mapped[str | None] = mapped_column(String(36))

    # Error info
    error_message: Mapped[str | None] = mapped_column(Text)

    def __repr__(self) -> str:
        return f"<Experiment {self.name} [{self.status}]>"


class DetectionResult(Base, UUIDMixin, TimestampMixin):
    """
    Stores TP/FP/TN/FN evaluation per experiment for computing
    Precision, Recall, F1 across all experiments.
    """

    __tablename__ = "detection_results"

    experiment_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)

    # Ground truth vs detected
    expected_anomaly: Mapped[bool] = mapped_column(Integer, nullable=False)
    detected_anomaly: Mapped[bool] = mapped_column(Integer, nullable=False)

    # Derived classification
    true_positive: Mapped[bool] = mapped_column(Integer, default=0)
    false_positive: Mapped[bool] = mapped_column(Integer, default=0)
    true_negative: Mapped[bool] = mapped_column(Integer, default=0)
    false_negative: Mapped[bool] = mapped_column(Integer, default=0)

    # Performance
    detection_latency_ms: Mapped[float | None] = mapped_column(Float)
    anomaly_score: Mapped[float | None] = mapped_column(Float)
    detector_used: Mapped[str | None] = mapped_column(String(64))


class NetworkLabNode(Base, UUIDMixin, TimestampMixin):
    """A virtual network node (Linux network namespace) in the lab."""

    __tablename__ = "network_lab_nodes"

    name: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    namespace: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    ip_address: Mapped[str] = mapped_column(String(45), nullable=False)
    veth_host: Mapped[str] = mapped_column(String(64), nullable=False)
    veth_ns: Mapped[str] = mapped_column(String(64), nullable=False)
    bridge: Mapped[str] = mapped_column(String(64), nullable=False)
    is_active: Mapped[bool] = mapped_column(Integer, default=1)

    # Current traffic (updated periodically)
    rx_bytes_per_sec: Mapped[float] = mapped_column(Float, default=0.0)
    tx_bytes_per_sec: Mapped[float] = mapped_column(Float, default=0.0)
    packets_per_sec: Mapped[float] = mapped_column(Float, default=0.0)
