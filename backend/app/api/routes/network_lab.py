"""
Network Lab API
================
Creates and manages Linux network namespaces, veth pairs, and bridges.
All operations require CAP_NET_ADMIN (or root).

Security: All inputs are validated and passed as subprocess argument arrays.
No shell string interpolation is used.
"""

from __future__ import annotations

import asyncio
import ipaddress
import re
import subprocess
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.session import get_db_session
from app.models.experiment import NetworkLabNode

logger = get_logger(__name__)
router = APIRouter(prefix="/api/network-lab", tags=["network-lab"])

# Validation pattern for namespace names
_NAME_RE = re.compile(r"^[a-z][a-z0-9-]{0,30}$")


def _validate_name(name: str) -> str:
    if not _NAME_RE.match(name):
        raise HTTPException(status_code=400, detail=f"Invalid namespace name: '{name}'")
    return name


async def _run(cmd: list[str], check: bool = True) -> tuple[int, str, str]:
    """Run a subprocess command safely (no shell=True)."""
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30.0)
        rc = proc.returncode
        if check and rc != 0:
            raise HTTPException(status_code=500, detail=f"Command failed: {stderr.decode()[:256]}")
        return rc, stdout.decode(), stderr.decode()
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Network operation timed out")
    except PermissionError:
        raise HTTPException(
            status_code=403,
            detail="Permission denied. Network Lab requires CAP_NET_ADMIN or root privileges.",
        )


@router.get("")
async def get_lab_status():
    """Return current lab topology."""
    async with get_db_session() as session:
        result = await session.execute(
            select(NetworkLabNode).where(NetworkLabNode.is_active == True)
        )
        nodes = result.scalars().all()
        return {
            "active": len(nodes) > 0,
            "bridge": get_settings().lab_bridge_name if nodes else None,
            "nodes": [_node_to_dict(n) for n in nodes],
            "node_count": len(nodes),
        }


@router.post("")
async def create_lab(body: dict):
    """Create the virtual network lab with specified nodes."""
    settings = get_settings()
    node_names = body.get("nodes", ["ns-a", "ns-b", "ns-c"])
    subnet_str = body.get("subnet", settings.lab_default_subnet)
    bridge = body.get("bridge_name", settings.lab_bridge_name)

    if len(node_names) > settings.lab_max_namespaces:
        raise HTTPException(status_code=400, detail=f"Maximum {settings.lab_max_namespaces} namespaces")

    # Validate all names before any operations
    for name in node_names:
        _validate_name(name)

    # Parse subnet
    try:
        network = ipaddress.IPv4Network(subnet_str, strict=False)
        hosts = list(network.hosts())
        if len(hosts) < len(node_names):
            raise HTTPException(status_code=400, detail="Subnet too small for requested nodes")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid subnet: {e}")

    # Create bridge
    await _run(["ip", "link", "add", bridge, "type", "bridge"], check=False)
    await _run(["ip", "link", "set", bridge, "up"])

    created_nodes = []
    for i, name in enumerate(node_names):
        ns_name = f"netwatch-{name}"
        veth_host = f"veth-{name}-h"
        veth_ns = f"veth-{name}-ns"
        ip_addr = str(hosts[i])
        prefix = network.prefixlen

        try:
            # Create namespace
            await _run(["ip", "netns", "add", ns_name])
            # Create veth pair
            await _run(["ip", "link", "add", veth_host, "type", "veth", "peer", "name", veth_ns])
            # Move ns-side into namespace
            await _run(["ip", "link", "set", veth_ns, "netns", ns_name])
            # Add host-side to bridge
            await _run(["ip", "link", "set", veth_host, "master", bridge])
            await _run(["ip", "link", "set", veth_host, "up"])
            # Configure IP inside namespace
            await _run(["ip", "netns", "exec", ns_name, "ip", "addr", "add",
                        f"{ip_addr}/{prefix}", "dev", veth_ns])
            await _run(["ip", "netns", "exec", ns_name, "ip", "link", "set", veth_ns, "up"])
            await _run(["ip", "netns", "exec", ns_name, "ip", "link", "set", "lo", "up"])

            node_data = {
                "name": name,
                "namespace": ns_name,
                "ip_address": ip_addr,
                "veth_host": veth_host,
                "veth_ns": veth_ns,
                "bridge": bridge,
                "is_active": True,
            }
            created_nodes.append(node_data)

            async with get_db_session() as session:
                node = NetworkLabNode(**node_data)
                session.add(node)

            logger.info("lab_node_created", name=name, namespace=ns_name, ip=ip_addr)

        except Exception as exc:
            logger.error("lab_node_create_failed", name=name, error=str(exc))
            # Continue creating remaining nodes

    return {"message": f"Lab created with {len(created_nodes)} nodes", "nodes": created_nodes}


@router.delete("")
async def destroy_lab():
    """Destroy all lab namespaces and interfaces. Cleanup is idempotent."""
    settings = get_settings()
    bridge = settings.lab_bridge_name
    errors = []

    async with get_db_session() as session:
        result = await session.execute(
            select(NetworkLabNode).where(NetworkLabNode.is_active == True)
        )
        nodes = result.scalars().all()

        for node in nodes:
            try:
                await _run(["ip", "link", "del", node.veth_host], check=False)
                await _run(["ip", "netns", "del", node.namespace], check=False)
                node.is_active = False
                logger.info("lab_node_deleted", name=node.name)
            except Exception as exc:
                errors.append(str(exc))
                logger.error("lab_node_delete_error", name=node.name, error=str(exc))

    # Remove bridge
    await _run(["ip", "link", "del", bridge], check=False)

    return {
        "message": "Lab destroyed",
        "errors": errors if errors else None,
    }


def _node_to_dict(n: NetworkLabNode) -> dict:
    return {
        "id": n.id, "name": n.name, "namespace": n.namespace,
        "ip_address": n.ip_address, "veth_host": n.veth_host,
        "veth_ns": n.veth_ns, "bridge": n.bridge, "is_active": bool(n.is_active),
        "rx_bytes_per_sec": n.rx_bytes_per_sec, "tx_bytes_per_sec": n.tx_bytes_per_sec,
        "packets_per_sec": n.packets_per_sec, "created_at": n.created_at.isoformat(),
    }
