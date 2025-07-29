"""
Network Flow ORM Model
=======================
A flow is identified by the 5-tuple:
  (src_ip, dst_ip, src_port, dst_port, protocol)

Flows are aggregated from packets and represent a single network conversation.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class Flow(Base, UUIDMixin, TimestampMixin):
    """Aggregated network flow record."""

    __tablename__ = "flows"

    # 5-tuple (flow key)
    src_ip: Mapped[str] = mapped_column(String(45), nullable=False, index=True)
    dst_ip: Mapped[str] = mapped_column(String(45), nullable=False, index=True)
    src_port: Mapped[int | None] = mapped_column(Integer)
    dst_port: Mapped[int | None] = mapped_column(Integer, index=True)
    protocol: Mapped[str] = mapped_column(String(16), nullable=False, index=True)

    # Timing
    flow_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    flow_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_sec: Mapped[float] = mapped_column(Float, default=0.0)

    # Volume
    packet_count: Mapped[int] = mapped_column(Integer, default=0)
    byte_count: Mapped[int] = mapped_column(Integer, default=0)

    # Rates
    packets_per_sec: Mapped[float] = mapped_column(Float, default=0.0)
    bytes_per_sec: Mapped[float] = mapped_column(Float, default=0.0)
    avg_packet_size: Mapped[float] = mapped_column(Float, default=0.0)

    # TCP-specific
    tcp_flags: Mapped[str | None] = mapped_column(String(32))
    tcp_syn_count: Mapped[int] = mapped_column(Integer, default=0)
    tcp_fin_count: Mapped[int] = mapped_column(Integer, default=0)
    tcp_rst_count: Mapped[int] = mapped_column(Integer, default=0)

    # Interface this flow was captured on
    interface: Mapped[str | None] = mapped_column(String(64), index=True)

    # Data source label
    data_source: Mapped[str] = mapped_column(
        String(16), default="SYNTHETIC"
    )  # REAL | SYNTHETIC | LAB

    # Anomaly score (set by detector)
    anomaly_score: Mapped[float | None] = mapped_column(Float)
    is_anomalous: Mapped[bool] = mapped_column(Integer, default=0)  # SQLite bool compat

    def __repr__(self) -> str:
        return f"<Flow {self.src_ip}:{self.src_port} → {self.dst_ip}:{self.dst_port} {self.protocol}>"
