"""
NetWatch — FastAPI Application Entry Point
==========================================
Configures middleware, mounts routers, and manages application lifecycle.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi import WebSocket

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage startup and shutdown lifecycle."""
    settings = get_settings()
    logger.info("netwatch_starting", version=settings.app_version, env=settings.app_env.value)

    # Initialize database
    from app.db.init_db import init_db
    await init_db()

    # Connect to Redis (optional — falls back gracefully)
    from app.db.redis_client import init_redis
    await init_redis()

    # Start the stream worker (collector → processor → WS broadcaster)
    from app.workers.stream_worker import run_worker
    from app.workers.metric_aggregator import run_metric_aggregator
    worker_task = asyncio.create_task(run_worker(), name="stream_worker")
    aggregator_task = asyncio.create_task(run_metric_aggregator(), name="metric_aggregator")

    logger.info("netwatch_ready", port=settings.backend_port, mode=settings.collector_mode.value)

    yield  # Application is running

    # Shutdown
    logger.info("netwatch_shutting_down")
    worker_task.cancel()
    aggregator_task.cancel()
    try:
        await asyncio.gather(worker_task, aggregator_task, return_exceptions=True)
    except Exception:
        pass

    from app.db.redis_client import close_redis
    from app.db.session import close_engine
    await close_redis()
    await close_engine()
    logger.info("netwatch_stopped")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="NetWatch API",
        description="Real-Time Network Monitoring & Anomaly Detection Platform",
        version=settings.app_version,
        docs_url="/docs" if settings.is_development else None,
        redoc_url="/redoc" if settings.is_development else None,
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins + ["*"] if settings.is_development else settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Prometheus metrics
    if settings.prometheus_enabled:
        try:
            from prometheus_fastapi_instrumentator import Instrumentator
            Instrumentator().instrument(app).expose(app, endpoint="/metrics")
            logger.info("prometheus_enabled")
        except ImportError:
            logger.warning("prometheus_not_installed")

    # ── REST Routers ──────────────────────────────────────────────────────────
    from app.api.routes.system import router as system_router
    from app.api.routes.interfaces import router as interfaces_router
    from app.api.routes.flows import router as flows_router
    from app.api.routes.metrics import router as metrics_router
    from app.api.routes.alerts import router as alerts_router
    from app.api.routes.experiments import router as experiments_router
    from app.api.routes.network_lab import router as lab_router
    from app.api.routes.auth import router as auth_router
    from app.api.routes.settings import router as settings_router

    for router in [
        system_router, interfaces_router, flows_router, metrics_router,
        alerts_router, experiments_router, lab_router, auth_router,
        settings_router,
    ]:
        app.include_router(router)

    # ── WebSocket Endpoints ───────────────────────────────────────────────────
    from app.api.websocket import (
        ws_metrics_handler,
        ws_alerts_handler,
        ws_flows_handler,
    )

    @app.websocket("/ws/metrics")
    async def ws_metrics(websocket: WebSocket):
        await ws_metrics_handler(websocket)

    @app.websocket("/ws/alerts")
    async def ws_alerts(websocket: WebSocket):
        await ws_alerts_handler(websocket)

    @app.websocket("/ws/flows")
    async def ws_flows(websocket: WebSocket):
        await ws_flows_handler(websocket)

    # ── Root ──────────────────────────────────────────────────────────────────
    @app.get("/")
    async def root():
        return {
            "name": "NetWatch API",
            "version": settings.app_version,
            "mode": settings.collector_mode.value,
            "docs": "/docs",
            "health": "/api/system/health",
        }

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=settings.is_development,
        log_level=settings.log_level.lower(),
    )
