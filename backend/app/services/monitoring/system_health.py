"""
System Health Monitor
======================
Gathers system resource usage and service connectivity status.
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone

import psutil

from app.core.config import get_settings
from app.core.logging import get_logger
from app.schemas.system import ServiceStatus, SystemHealth, SystemResources

logger = get_logger(__name__)

_app_start_time = time.monotonic()


async def _check_redis() -> ServiceStatus:
    settings = get_settings()
    try:
        from app.db.redis_client import is_redis_available
        if is_redis_available():
            return ServiceStatus(name="Redis", status="healthy")
        return ServiceStatus(name="Redis", status="unavailable", detail="Not connected — using in-memory fallback")
    except Exception as e:
        return ServiceStatus(name="Redis", status="unavailable", detail=str(e))


async def _check_database() -> ServiceStatus:
    try:
        from app.db.session import get_engine
        from sqlalchemy import text
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return ServiceStatus(name="PostgreSQL/SQLite", status="healthy")
    except Exception as e:
        return ServiceStatus(name="PostgreSQL/SQLite", status="unavailable", detail=str(e))


def _get_resources() -> SystemResources:
    cpu = psutil.cpu_percent(interval=0.1)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    return SystemResources(
        cpu_percent=round(cpu, 1),
        memory_percent=round(mem.percent, 1),
        memory_used_mb=round(mem.used / 1_000_000, 1),
        memory_total_mb=round(mem.total / 1_000_000, 1),
        disk_percent=round(disk.percent, 1),
        disk_used_gb=round(disk.used / 1_000_000_000, 2),
        disk_total_gb=round(disk.total / 1_000_000_000, 2),
    )


async def get_system_health() -> SystemHealth:
    """Collect and return the complete system health snapshot."""
    settings = get_settings()

    db_status, redis_status = await asyncio.gather(
        _check_database(),
        _check_redis(),
    )

    backend_status = ServiceStatus(name="Backend", status="healthy")
    services = [backend_status, db_status, redis_status]

    all_healthy = all(s.status == "healthy" for s in services)
    any_unavailable = any(s.status == "unavailable" for s in services)
    overall = "healthy" if all_healthy else ("critical" if any_unavailable else "degraded")

    loop = asyncio.get_event_loop()
    resources = await loop.run_in_executor(None, _get_resources)

    return SystemHealth(
        timestamp=datetime.now(timezone.utc),
        overall_status=overall,
        services=services,
        resources=resources,
        netwatch_version=settings.app_version,
        uptime_seconds=round(time.monotonic() - _app_start_time, 1),
        data_source=settings.collector_mode.value.upper(),
    )
