"""Pydantic schemas for Interface API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class InterfaceBase(BaseModel):
    name: str
    display_name: str | None = None
    description: str | None = None


class InterfaceStats(BaseModel):
    rx_bytes: int = 0
    tx_bytes: int = 0
    rx_packets: int = 0
    tx_packets: int = 0
    rx_errors: int = 0
    tx_errors: int = 0
    rx_dropped: int = 0
    tx_dropped: int = 0
    rx_bandwidth_mbps: float = 0.0
    tx_bandwidth_mbps: float = 0.0
    packets_per_sec: float = 0.0


class InterfaceRead(InterfaceBase, InterfaceStats):
    id: str
    mac_address: str | None = None
    ip_address: str | None = None
    ip_prefix_len: int | None = None
    mtu: int | None = None
    is_up: bool = False
    is_monitored: bool = False
    monitoring_started_at: datetime | None = None
    last_seen: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class InterfaceList(BaseModel):
    interfaces: list[InterfaceRead]
    total: int


class MonitorStartResponse(BaseModel):
    message: str
    interface: str
    mode: str  # REAL | SYNTHETIC


class TrafficVisibility(BaseModel):
    """Clearly communicates what traffic is observable on this interface."""
    interface: str
    can_see_rx: bool = True
    can_see_tx: bool = True
    can_see_host_traffic: bool = True
    can_see_all_wifi_clients: bool = False
    mode: str  # REAL | SYNTHETIC
    note: str
