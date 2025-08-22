"""Interfaces API routes."""

from fastapi import APIRouter, HTTPException
from app.services.monitoring.interface_monitor import get_interfaces_async
from app.core.config import get_settings

router = APIRouter(prefix="/api/interfaces", tags=["interfaces"])


@router.get("")
async def list_interfaces():
    """List all network interfaces with current statistics."""
    interfaces = await get_interfaces_async()
    return {"interfaces": interfaces, "total": len(interfaces)}


@router.get("/{name}")
async def get_interface(name: str):
    """Get a specific interface by name."""
    interfaces = await get_interfaces_async()
    for iface in interfaces:
        if iface["name"] == name:
            return iface
    raise HTTPException(status_code=404, detail=f"Interface '{name}' not found")


@router.get("/{name}/visibility")
async def get_traffic_visibility(name: str):
    """Explain what traffic is observable on this interface."""
    settings = get_settings()
    return {
        "interface": name,
        "mode": settings.collector_mode.value.upper(),
        "visibility": {
            "can_see_rx": True,
            "can_see_tx": True,
            "can_see_host_traffic": True,
            "can_see_all_wifi_clients": False,
        },
        "note": (
            "This system monitors traffic sent and received by this host's interface. "
            "Traffic between other devices on the same network segment is not visible "
            "unless this interface is configured as a monitor port or span port."
        ),
        "data_source": settings.collector_mode.value.upper(),
    }
