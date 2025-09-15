"""Pydantic schemas for System Health API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ServiceStatus(BaseModel):
    name: str
    status: str  # healthy | degraded | unavailable
    detail: str | None = None
    latency_ms: float | None = None


class SystemResources(BaseModel):
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_total_mb: float
    disk_percent: float
    disk_used_gb: float
    disk_total_gb: float


class CollectorStats(BaseModel):
    mode: str  # REAL | SYNTHETIC
    interface: str
    packets_processed: int
    packets_dropped: int
    processing_latency_ms: float
    uptime_seconds: float


class WorkerStats(BaseModel):
    flows_processed: int
    metrics_published: int
    anomalies_detected: int
    db_insert_rate: float
    redis_queue_size: int
    websocket_clients: int


class SystemHealth(BaseModel):
    """Complete system health snapshot."""
    timestamp: datetime
    overall_status: str  # healthy | degraded | critical

    services: list[ServiceStatus]
    resources: SystemResources
    collector: CollectorStats | None = None
    worker: WorkerStats | None = None

    # Self-monitoring
    netwatch_version: str
    uptime_seconds: float
    data_source: str
