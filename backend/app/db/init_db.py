"""
Database Initialization
========================
Creates all tables and seeds default data (admin user, default interface record).
Run with: python3 -m app.db.init_db
"""

from __future__ import annotations

import asyncio
import sys

from sqlalchemy import text

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.db.session import get_engine, get_db_session

configure_logging()
logger = get_logger(__name__)


async def init_db() -> None:
    """Create all tables and seed initial data."""
    settings = get_settings()
    engine = get_engine()

    # Import all models so SQLAlchemy knows about them
    from app.models.base import Base
    from app.models.user import User
    from app.models.interface import Interface
    from app.models.flow import Flow
    from app.models.metric import Metric1s, Metric1m
    from app.models.alert import Alert
    from app.models.experiment import Experiment, DetectionResult, NetworkLabNode
    from app.models.settings import SystemSettings

    logger.info("creating_tables", database=settings.database_url.split("@")[-1])
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # TimescaleDB hypertables (only if using PostgreSQL with TimescaleDB extension)
    if settings.is_postgres:
        async with engine.begin() as conn:
            try:
                await conn.execute(text(
                    "SELECT create_hypertable('metrics_1s', 'timestamp', if_not_exists => TRUE)"
                ))
                await conn.execute(text(
                    "SELECT create_hypertable('metrics_1m', 'timestamp', if_not_exists => TRUE)"
                ))
                logger.info("timescaledb_hypertables_created")
            except Exception as exc:
                logger.warning("timescaledb_not_available", detail=str(exc))

    # Seed default admin user
    from app.core.security import hash_password
    async with get_db_session() as session:
        from sqlalchemy import select
        existing = (await session.execute(
            select(User).where(User.username == "admin")
        )).scalar_one_or_none()

        if not existing:
            admin = User(
                username="admin",
                email="admin@netwatch.local",
                hashed_password=hash_password("netwatch123"),
                is_admin=True,
            )
            session.add(admin)
            logger.info("default_admin_created", username="admin", note="Change password in production!")

        # Seed default system settings
        existing_settings = (await session.execute(
            select(SystemSettings).where(SystemSettings.id == 1)
        )).scalar_one_or_none()

        if not existing_settings:
            default_settings = SystemSettings(
                id=1,
                anomaly_threshold=settings.anomaly_threshold,
                alert_cooldown_seconds=settings.alert_cooldown_seconds,
                retention_raw_flows_hours=settings.retention_raw_flows_hours,
                retention_metrics_1s_hours=settings.retention_metrics_1s_hours,
                retention_metrics_1m_days=settings.retention_metrics_1m_days,
                retention_alerts_days=settings.retention_alerts_days,
                detector_type=settings.anomaly_method.value,
            )
            session.add(default_settings)
            logger.info("default_system_settings_created")

    await engine.dispose()
    logger.info("database_initialized")


if __name__ == "__main__":
    asyncio.run(init_db())
