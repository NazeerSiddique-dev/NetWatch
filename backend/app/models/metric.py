"""
Metric ORM Models
==================
Time-series network metrics at 1-second and 1-minute granularity.
Designed for TimescaleDB hypertables when using PostgreSQL.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Metric1s(Base):
    """
    1-second granularity metrics per interface.
    High-volume table — retained for 24 hours only.
    """

    __tablename__ = "metrics_1s"

    # Composite primary key: timestamp + interface
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True, nullable=False
    )
    interface: Mapped[str] = mapped_column(String(64), primary_key=True, nullable=False)

    # Bandwidth
    rx_bytes_per_sec: Mapped[float] = mapped_column(Float, default=0.0)
    tx_bytes_per_sec: Mapped[float] = mapped_column(Float, default=0.0)
    total_bytes_per_sec: Mapped[float] = mapped_column(Float, default=0.0)
    rx_mbps: Mapped[float] = mapped_column(Float, default=0.0)
    tx_mbps: Mapped[float] = mapped_column(Float, default=0.0)

    # Packet rates
    rx_packets_per_sec: Mapped[float] = mapped_column(Float, default=0.0)
    tx_packets_per_sec: Mapped[float] = mapped_column(Float, default=0.0)
    total_packets_per_sec: Mapped[float] = mapped_column(Float, default=0.0)

    # Latency (ms) — estimated from RTT where available
    avg_latency_ms: Mapped[float | None] = mapped_column(Float)
    min_latency_ms: Mapped[float | None] = mapped_column(Float)
    max_latency_ms: Mapped[float | None] = mapped_column(Float)
    p95_latency_ms: Mapped[float | None] = mapped_column(Float)

    # Packet loss (percentage)
    packet_loss_pct: Mapped[float] = mapped_column(Float, default=0.0)

    # Protocol distribution (packet counts)
    tcp_packets: Mapped[int] = mapped_column(Integer, default=0)
    udp_packets: Mapped[int] = mapped_column(Integer, default=0)
    icmp_packets: Mapped[int] = mapped_column(Integer, default=0)
    dns_packets: Mapped[int] = mapped_column(Integer, default=0)
    http_packets: Mapped[int] = mapped_column(Integer, default=0)
    https_packets: Mapped[int] = mapped_column(Integer, default=0)
    other_packets: Mapped[int] = mapped_column(Integer, default=0)

    # Active flows
    active_flows: Mapped[int] = mapped_column(Integer, default=0)
    new_flows: Mapped[int] = mapped_column(Integer, default=0)

    # Anomaly
    anomaly_score: Mapped[float | None] = mapped_column(Float)
    is_anomalous: Mapped[bool] = mapped_column(Integer, default=0)

    # Data source
    data_source: Mapped[str] = mapped_column(String(16), default="SYNTHETIC")


class Metric1m(Base):
    """
    1-minute aggregate metrics.
    Retained for 30 days.
    """

    __tablename__ = "metrics_1m"

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True, nullable=False
    )
    interface: Mapped[str] = mapped_column(String(64), primary_key=True, nullable=False)

    # Averages over the minute
    avg_rx_mbps: Mapped[float] = mapped_column(Float, default=0.0)
    avg_tx_mbps: Mapped[float] = mapped_column(Float, default=0.0)
    max_rx_mbps: Mapped[float] = mapped_column(Float, default=0.0)
    max_tx_mbps: Mapped[float] = mapped_column(Float, default=0.0)
    avg_packets_per_sec: Mapped[float] = mapped_column(Float, default=0.0)
    max_packets_per_sec: Mapped[float] = mapped_column(Float, default=0.0)

    avg_latency_ms: Mapped[float | None] = mapped_column(Float)
    avg_packet_loss_pct: Mapped[float] = mapped_column(Float, default=0.0)
    total_bytes: Mapped[int] = mapped_column(Integer, default=0)
    total_packets: Mapped[int] = mapped_column(Integer, default=0)

    # Protocol distribution (percentages)
    tcp_pct: Mapped[float] = mapped_column(Float, default=0.0)
    udp_pct: Mapped[float] = mapped_column(Float, default=0.0)
    icmp_pct: Mapped[float] = mapped_column(Float, default=0.0)
    dns_pct: Mapped[float] = mapped_column(Float, default=0.0)
    http_pct: Mapped[float] = mapped_column(Float, default=0.0)
    https_pct: Mapped[float] = mapped_column(Float, default=0.0)
    other_pct: Mapped[float] = mapped_column(Float, default=0.0)

    total_flows: Mapped[int] = mapped_column(Integer, default=0)
    anomaly_count: Mapped[int] = mapped_column(Integer, default=0)
    data_source: Mapped[str] = mapped_column(String(16), default="SYNTHETIC")
