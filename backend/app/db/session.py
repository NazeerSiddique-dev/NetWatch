"""
Database Session Management
============================
Provides an async SQLAlchemy engine and session factory.
Supports SQLite (development) and PostgreSQL (production) via DATABASE_URL.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool, StaticPool

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def _build_engine(settings=None) -> AsyncEngine:
    """Build an async SQLAlchemy engine from settings."""
    if settings is None:
        settings = get_settings()

    url = settings.database_url
    kwargs: dict = {
        "echo": settings.debug,
        "future": True,
    }

    if settings.is_sqlite:
        # SQLite needs special pooling for async
        kwargs["connect_args"] = {"check_same_thread": False}
        if settings.is_testing:
            kwargs["poolclass"] = StaticPool
        else:
            kwargs["poolclass"] = NullPool
    else:
        # PostgreSQL connection pool
        kwargs["pool_size"] = 10
        kwargs["max_overflow"] = 20
        kwargs["pool_pre_ping"] = True

    return create_async_engine(url, **kwargs)


def get_engine() -> AsyncEngine:
    """Return the singleton engine, creating it on first call."""
    global _engine
    if _engine is None:
        _engine = _build_engine()
        logger.info("database_engine_created", url=get_settings().database_url.split("@")[-1])
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the singleton session factory."""
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
    return _session_factory


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Async context manager for a database session. Auto-commits or rolls back."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a database session per request."""
    async with get_db_session() as session:
        yield session


async def close_engine() -> None:
    """Dispose the engine (called on app shutdown)."""
    global _engine, _session_factory
    if _engine:
        await _engine.dispose()
        _engine = None
        _session_factory = None
        logger.info("database_engine_closed")
