"""System health API route."""

from fastapi import APIRouter
from app.services.monitoring.system_health import get_system_health
from app.workers.stream_worker import get_worker_stats
from app.api.websocket import manager

router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("/health")
async def health():
    """Full system health check."""
    health = await get_system_health()
    d = health.model_dump()
    d["worker"] = get_worker_stats()
    d["websocket_clients"] = manager.client_count()
    return d


@router.get("/ping")
async def ping():
    """Simple liveness check."""
    return {"status": "ok"}
