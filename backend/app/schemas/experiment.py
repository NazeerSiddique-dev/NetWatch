"""Pydantic schemas for Experiment API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ExperimentCreate(BaseModel):
    name: str
    description: str | None = None
    traffic_type: str
    src_namespace: str | None = None
    dst_namespace: str | None = None
    src_ip: str | None = None
    dst_ip: str | None = None
    dst_port: int | None = None
    packet_rate: int | None = Field(default=None, ge=1)
    duration_sec: int = Field(default=30, ge=1, le=300)
    burst_size: int | None = None
    expected_anomaly: bool = False
    expected_anomaly_type: str | None = None


class ExperimentRead(BaseModel):
    id: str
    name: str
    description: str | None = None
    status: str
    traffic_type: str
    src_namespace: str | None = None
    dst_namespace: str | None = None
    src_ip: str | None = None
    dst_ip: str | None = None
    dst_port: int | None = None
    packet_rate: int | None = None
    duration_sec: int | None = None
    burst_size: int | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    expected_anomaly: bool = False
    expected_anomaly_type: str | None = None
    anomaly_detected: bool | None = None
    detection_time_ms: float | None = None
    detected_alert_id: str | None = None
    error_message: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class DetectionResultRead(BaseModel):
    id: str
    experiment_id: str
    expected_anomaly: bool
    detected_anomaly: bool
    true_positive: bool
    false_positive: bool
    true_negative: bool
    false_negative: bool
    detection_latency_ms: float | None = None
    anomaly_score: float | None = None
    detector_used: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class EvaluationSummary(BaseModel):
    """Aggregated detection performance metrics across all experiments."""
    total_experiments: int
    true_positives: int
    false_positives: int
    true_negatives: int
    false_negatives: int
    precision: float | None = None
    recall: float | None = None
    f1_score: float | None = None
    avg_detection_latency_ms: float | None = None
    detector_used: str


class NetworkLabNodeRead(BaseModel):
    id: str
    name: str
    namespace: str
    ip_address: str
    veth_host: str
    veth_ns: str
    bridge: str
    is_active: bool
    rx_bytes_per_sec: float = 0.0
    tx_bytes_per_sec: float = 0.0
    packets_per_sec: float = 0.0
    created_at: datetime

    model_config = {"from_attributes": True}


class NetworkLabCreate(BaseModel):
    nodes: list[str] = Field(
        default=["ns-a", "ns-b", "ns-c"],
        description="Names for network namespaces to create",
    )
    subnet: str = "10.99.0.0/24"
    bridge_name: str = "netwatch-br0"


class NetworkLabStatus(BaseModel):
    active: bool
    bridge: str | None = None
    nodes: list[NetworkLabNodeRead] = []
    node_count: int = 0
