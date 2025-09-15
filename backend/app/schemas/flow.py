"""Pydantic schemas for Flow API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class FlowRead(BaseModel):
    id: str
    src_ip: str
    dst_ip: str
    src_port: int | None = None
    dst_port: int | None = None
    protocol: str
    flow_start: datetime
    flow_end: datetime | None = None
    duration_sec: float = 0.0
    packet_count: int = 0
    byte_count: int = 0
    packets_per_sec: float = 0.0
    bytes_per_sec: float = 0.0
    avg_packet_size: float = 0.0
    tcp_flags: str | None = None
    interface: str | None = None
    data_source: str = "SYNTHETIC"
    anomaly_score: float | None = None
    is_anomalous: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}


class FlowFilter(BaseModel):
    src_ip: str | None = None
    dst_ip: str | None = None
    src_port: int | None = None
    dst_port: int | None = None
    protocol: str | None = None
    interface: str | None = None
    data_source: str | None = None
    is_anomalous: bool | None = None
    min_bytes: int | None = None
    min_packets: int | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=500)


class FlowList(BaseModel):
    flows: list[FlowRead]
    total: int
    page: int
    page_size: int
    total_pages: int


class TopTalker(BaseModel):
    ip: str
    total_bytes: int
    total_packets: int
    connection_count: int


class TopPort(BaseModel):
    port: int
    protocol: str
    connection_count: int
    total_bytes: int
