"""Pydantic schemas for Metrics API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ProtocolDistribution(BaseModel):
    tcp: float = 0.0
    udp: float = 0.0
    icmp: float = 0.0
    dns: float = 0.0
    http: float = 0.0
    https: float = 0.0
    other: float = 0.0


class RealtimeMetric(BaseModel):
    """Real-time snapshot of current network metrics (pushed via WebSocket)."""
    timestamp: datetime
    interface: str
    data_source: str  # REAL | SYNTHETIC | LAB

    # Bandwidth
    rx_mbps: float = 0.0
    tx_mbps: float = 0.0
    total_mbps: float = 0.0

    # Packets
    rx_packets_per_sec: float = 0.0
    tx_packets_per_sec: float = 0.0
    total_packets_per_sec: float = 0.0

    # Latency
    avg_latency_ms: float | None = None
    min_latency_ms: float | None = None
    max_latency_ms: float | None = None
    p95_latency_ms: float | None = None

    # Packet loss
    packet_loss_pct: float = 0.0

    # Flows
    active_flows: int = 0
    new_flows: int = 0

    # Protocol distribution
    protocols: ProtocolDistribution = ProtocolDistribution()

    # Anomaly
    anomaly_score: float | None = None
    is_anomalous: bool = False


class MetricHistory(BaseModel):
    """Historical metric data point."""
    timestamp: datetime
    rx_mbps: float = 0.0
    tx_mbps: float = 0.0
    total_packets_per_sec: float = 0.0
    avg_latency_ms: float | None = None
    packet_loss_pct: float = 0.0
    active_flows: int = 0
    anomaly_score: float | None = None


class MetricHistoryResponse(BaseModel):
    interface: str
    granularity: str  # 1s | 1m
    start_time: datetime
    end_time: datetime
    data: list[MetricHistory]


class NetworkStatus(BaseModel):
    """Summary shown at the top of the dashboard."""
    status: str  # HEALTHY | DEGRADED | CRITICAL
    interface: str
    data_source: str
    interfaces_total: int = 0
    interfaces_active: int = 0
    active_flows: int = 0
    packets_per_sec: float = 0.0
    bandwidth_mbps: float = 0.0
    packet_loss_pct: float = 0.0
    avg_latency_ms: float | None = None
    anomalies_active: int = 0
    critical_alerts: int = 0
    timestamp: datetime
