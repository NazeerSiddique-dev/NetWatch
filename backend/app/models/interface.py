"""
Interface ORM Model
====================
Stores discovered network interfaces and their monitoring state.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class Interface(Base, UUIDMixin, TimestampMixin):
    """Represents a network interface discovered on the host."""

    __tablename__ = "interfaces"

    name: Mapped[str] = mapped_column(String(64), nullable=False, index=True, unique=True)
    display_name: Mapped[str | None] = mapped_column(String(128))
    description: Mapped[str | None] = mapped_column(Text)

    # Physical attributes
    mac_address: Mapped[str | None] = mapped_column(String(17))  # AA:BB:CC:DD:EE:FF
    ip_address: Mapped[str | None] = mapped_column(String(45))   # IPv4 or IPv6
    ip_prefix_len: Mapped[int | None] = mapped_column(Integer)
    mtu: Mapped[int | None] = mapped_column(Integer)

    # State
    is_up: Mapped[bool] = mapped_column(Boolean, default=False)
    is_monitored: Mapped[bool] = mapped_column(Boolean, default=False)
    monitoring_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Traffic counters (snapshot, not cumulative for all time)
    rx_bytes: Mapped[int] = mapped_column(Integer, default=0)
    tx_bytes: Mapped[int] = mapped_column(Integer, default=0)
    rx_packets: Mapped[int] = mapped_column(Integer, default=0)
    tx_packets: Mapped[int] = mapped_column(Integer, default=0)
    rx_errors: Mapped[int] = mapped_column(Integer, default=0)
    tx_errors: Mapped[int] = mapped_column(Integer, default=0)
    rx_dropped: Mapped[int] = mapped_column(Integer, default=0)
    tx_dropped: Mapped[int] = mapped_column(Integer, default=0)

    # Rates (updated periodically)
    rx_bandwidth_mbps: Mapped[float] = mapped_column(Float, default=0.0)
    tx_bandwidth_mbps: Mapped[float] = mapped_column(Float, default=0.0)
    packets_per_sec: Mapped[float] = mapped_column(Float, default=0.0)

    # Last polled
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    def __repr__(self) -> str:
        return f"<Interface {self.name} {'UP' if self.is_up else 'DOWN'}>"
