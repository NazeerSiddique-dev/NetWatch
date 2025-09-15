"""Pydantic schemas for Alert API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class AlertRead(BaseModel):
    id: str
    severity: str
    alert_type: str
    status: str
    title: str
    message: str
    interface: str | None = None
    src_ip: str | None = None
    dst_ip: str | None = None
    src_port: int | None = None
    dst_port: int | None = None
    protocol: str | None = None
    anomaly_score: float | None = None
    detector: str | None = None
    observed_value: float | None = None
    baseline_value: float | None = None
    deviation_sigma: float | None = None
    metric_name: str | None = None
    acknowledged_at: datetime | None = None
    resolved_at: datetime | None = None
    acknowledged_by: str | None = None
    experiment_id: str | None = None
    data_source: str = "SYNTHETIC"
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AlertFilter(BaseModel):
    severity: str | None = None
    alert_type: str | None = None
    status: str | None = None
    interface: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    page: int = 1
    page_size: int = 50


class AlertList(BaseModel):
    alerts: list[AlertRead]
    total: int
    page: int
    page_size: int


class AlertUpdate(BaseModel):
    status: str | None = None  # ACKNOWLEDGED | RESOLVED
    acknowledged_by: str | None = None


class AlertCreate(BaseModel):
    severity: str
    alert_type: str
    title: str
    message: str
    interface: str | None = None
    src_ip: str | None = None
    dst_ip: str | None = None
    anomaly_score: float | None = None
    detector: str | None = None
    observed_value: float | None = None
    baseline_value: float | None = None
    deviation_sigma: float | None = None
    metric_name: str | None = None
    experiment_id: str | None = None
    data_source: str = "SYNTHETIC"
