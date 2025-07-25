"""
NetWatch Application Settings
==============================
Centralizes all configuration using pydantic-settings.
Values are loaded from environment variables / .env file.
"""

from __future__ import annotations

import os
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppEnv(str, Enum):
    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


class CollectorMode(str, Enum):
    SYNTHETIC = "synthetic"
    PCAP = "pcap"
    AUTO = "auto"


class AnomalyMethod(str, Enum):
    STATISTICAL = "statistical"
    ISOLATION_FOREST = "isolation_forest"


class Settings(BaseSettings):
    """Application-wide settings. All values can be overridden via environment variables."""

    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent.parent.parent / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ───────────────────────────────────────────────────────────
    app_env: AppEnv = AppEnv.DEVELOPMENT
    app_name: str = "NetWatch"
    app_version: str = "1.0.0"
    debug: bool = False

    # ── Backend ───────────────────────────────────────────────────────────────
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    allowed_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # ── Database ──────────────────────────────────────────────────────────────
    database_url: str = "sqlite+aiosqlite:///./netwatch.db"

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def is_postgres(self) -> bool:
        return "postgresql" in self.database_url or "asyncpg" in self.database_url

    # ── Redis ─────────────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379"
    redis_stream_max_len: int = 10_000
    redis_enabled: bool = True

    # Stream names
    stream_raw_packets: str = "netwatch:raw_packets"
    stream_flows: str = "netwatch:flows"
    stream_metrics: str = "netwatch:metrics"
    stream_alerts: str = "netwatch:alerts"

    # ── Network Monitoring ────────────────────────────────────────────────────
    default_interface: str = "enp0s31f6"
    collector_mode: CollectorMode = CollectorMode.SYNTHETIC
    metric_interval: int = 1  # seconds
    flow_timeout: int = 60  # seconds of inactivity

    # ── Anomaly Detection ─────────────────────────────────────────────────────
    anomaly_method: AnomalyMethod = AnomalyMethod.STATISTICAL
    anomaly_threshold: float = 3.0
    anomaly_training_window: int = 300  # seconds
    anomaly_min_samples: int = 30

    # ── Alerts ────────────────────────────────────────────────────────────────
    alert_cooldown_seconds: int = 60

    # ── Authentication ────────────────────────────────────────────────────────
    jwt_secret: str = "CHANGE_THIS_IN_PRODUCTION"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440  # 24 hours

    # ── Data Retention ────────────────────────────────────────────────────────
    retention_raw_flows_hours: int = 24
    retention_metrics_1s_hours: int = 24
    retention_metrics_1m_days: int = 30
    retention_alerts_days: int = 90

    # ── Network Lab ───────────────────────────────────────────────────────────
    lab_default_subnet: str = "10.99.0.0/24"
    lab_bridge_name: str = "netwatch-br0"
    lab_max_namespaces: int = 10
    lab_traffic_max_rate: int = 100_000  # packets/sec

    # ── Prometheus ────────────────────────────────────────────────────────────
    prometheus_enabled: bool = True

    # ── Logging ───────────────────────────────────────────────────────────────
    log_level: str = "INFO"
    log_format: str = "json"

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in valid:
            raise ValueError(f"log_level must be one of {valid}")
        return v.upper()

    @property
    def is_development(self) -> bool:
        return self.app_env == AppEnv.DEVELOPMENT

    @property
    def is_production(self) -> bool:
        return self.app_env == AppEnv.PRODUCTION

    @property
    def is_testing(self) -> bool:
        return self.app_env == AppEnv.TESTING


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached application settings singleton."""
    return Settings()
