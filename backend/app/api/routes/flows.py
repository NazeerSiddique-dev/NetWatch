"""Flows API routes."""

from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select, func
from app.db.session import get_db_session
from app.models.flow import Flow

router = APIRouter(prefix="/api/flows", tags=["flows"])


@router.get("")
async def list_flows(
    src_ip: Optional[str] = Query(None),
    dst_ip: Optional[str] = Query(None),
    protocol: Optional[str] = Query(None),
    dst_port: Optional[int] = Query(None),
    interface: Optional[str] = Query(None),
    is_anomalous: Optional[bool] = Query(None),
    min_bytes: Optional[int] = Query(None),
    data_source: Optional[str] = Query(None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
):
    """List flows with filtering and pagination."""
    async with get_db_session() as session:
        stmt = select(Flow)
        if src_ip:
            stmt = stmt.where(Flow.src_ip == src_ip)
        if dst_ip:
            stmt = stmt.where(Flow.dst_ip == dst_ip)
        if protocol:
            stmt = stmt.where(Flow.protocol == protocol.upper())
        if dst_port:
            stmt = stmt.where(Flow.dst_port == dst_port)
        if interface:
            stmt = stmt.where(Flow.interface == interface)
        if is_anomalous is not None:
            stmt = stmt.where(Flow.is_anomalous == is_anomalous)
        if min_bytes:
            stmt = stmt.where(Flow.byte_count >= min_bytes)
        if data_source:
            stmt = stmt.where(Flow.data_source == data_source.upper())

        total_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await session.execute(total_stmt)).scalar() or 0

        stmt = stmt.order_by(Flow.flow_start.desc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        result = await session.execute(stmt)
        flows = result.scalars().all()

        return {
            "flows": [_flow_to_dict(f) for f in flows],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": max(1, (total + page_size - 1) // page_size),
        }


@router.get("/top-talkers")
async def top_talkers(limit: int = Query(default=10, ge=1, le=100)):
    """Return top source IPs by bytes."""
    async with get_db_session() as session:
        stmt = (
            select(Flow.src_ip, func.sum(Flow.byte_count).label("total_bytes"),
                   func.sum(Flow.packet_count).label("total_packets"),
                   func.count(Flow.id).label("connections"))
            .group_by(Flow.src_ip)
            .order_by(func.sum(Flow.byte_count).desc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        rows = result.all()
        return [{"ip": r.src_ip, "total_bytes": r.total_bytes or 0,
                 "total_packets": r.total_packets or 0, "connections": r.connections} for r in rows]


@router.get("/top-ports")
async def top_ports(limit: int = Query(default=10, ge=1, le=100)):
    """Return top destination ports."""
    async with get_db_session() as session:
        stmt = (
            select(Flow.dst_port, Flow.protocol,
                   func.count(Flow.id).label("connections"),
                   func.sum(Flow.byte_count).label("total_bytes"))
            .where(Flow.dst_port.isnot(None))
            .group_by(Flow.dst_port, Flow.protocol)
            .order_by(func.count(Flow.id).desc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        rows = result.all()
        return [{"port": r.dst_port, "protocol": r.protocol,
                 "connections": r.connections, "total_bytes": r.total_bytes or 0} for r in rows]


@router.get("/{flow_id}")
async def get_flow(flow_id: str):
    async with get_db_session() as session:
        result = await session.execute(select(Flow).where(Flow.id == flow_id))
        flow = result.scalar_one_or_none()
        if not flow:
            raise HTTPException(status_code=404, detail="Flow not found")
        return _flow_to_dict(flow)


def _flow_to_dict(f: Flow) -> dict:
    return {
        "id": f.id, "src_ip": f.src_ip, "dst_ip": f.dst_ip,
        "src_port": f.src_port, "dst_port": f.dst_port, "protocol": f.protocol,
        "flow_start": f.flow_start.isoformat() if f.flow_start else None,
        "flow_end": f.flow_end.isoformat() if f.flow_end else None,
        "duration_sec": f.duration_sec, "packet_count": f.packet_count,
        "byte_count": f.byte_count, "packets_per_sec": f.packets_per_sec,
        "bytes_per_sec": f.bytes_per_sec, "avg_packet_size": f.avg_packet_size,
        "tcp_flags": f.tcp_flags, "interface": f.interface,
        "data_source": f.data_source, "anomaly_score": f.anomaly_score,
        "is_anomalous": bool(f.is_anomalous), "created_at": f.created_at.isoformat(),
    }
