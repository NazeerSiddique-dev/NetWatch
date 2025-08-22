"""
WebSocket Connection Manager + Broadcaster
==========================================
Manages WebSocket connections and broadcasts real-time events to all subscribers.
"""

from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

from app.core.logging import get_logger

logger = get_logger(__name__)


class ConnectionManager:
    """Manages active WebSocket connections, grouped by topic."""

    def __init__(self):
        # topic -> set of WebSocket connections
        self._connections: dict[str, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, topic: str) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections[topic].add(websocket)
        logger.info("ws_client_connected", topic=topic, total=self.client_count(topic))

    async def disconnect(self, websocket: WebSocket, topic: str) -> None:
        async with self._lock:
            self._connections[topic].discard(websocket)
        logger.info("ws_client_disconnected", topic=topic, total=self.client_count(topic))

    def client_count(self, topic: str | None = None) -> int:
        if topic:
            return len(self._connections.get(topic, set()))
        return sum(len(conns) for conns in self._connections.values())

    async def broadcast(self, topic: str, data: dict[str, Any]) -> None:
        """Send data to all clients subscribed to a topic."""
        payload = json.dumps(data, default=str)
        dead: list[WebSocket] = []

        async with self._lock:
            conns = list(self._connections.get(topic, set()))

        for ws in conns:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)

        if dead:
            async with self._lock:
                for ws in dead:
                    self._connections[topic].discard(ws)


# Global singleton
manager = ConnectionManager()


async def ws_metrics_handler(websocket: WebSocket) -> None:
    """Handle /ws/metrics WebSocket connection."""
    await manager.connect(websocket, "metrics")
    try:
        while True:
            # Keep connection alive (client sends pings)
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
            except asyncio.TimeoutError:
                await websocket.send_text(json.dumps({"type": "ping"}))
    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(websocket, "metrics")


async def ws_alerts_handler(websocket: WebSocket) -> None:
    """Handle /ws/alerts WebSocket connection."""
    await manager.connect(websocket, "alerts")
    try:
        while True:
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
            except asyncio.TimeoutError:
                await websocket.send_text(json.dumps({"type": "ping"}))
    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(websocket, "alerts")


async def ws_flows_handler(websocket: WebSocket) -> None:
    """Handle /ws/flows WebSocket connection."""
    await manager.connect(websocket, "flows")
    try:
        while True:
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
            except asyncio.TimeoutError:
                await websocket.send_text(json.dumps({"type": "ping"}))
    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(websocket, "flows")


async def broadcast_metric(metric_dict: dict[str, Any]) -> None:
    """Broadcast a metrics update to all /ws/metrics subscribers."""
    await manager.broadcast("metrics", {"type": "metric", "data": metric_dict})


async def broadcast_alert(alert_dict: dict[str, Any]) -> None:
    """Broadcast an alert to all /ws/alerts subscribers."""
    await manager.broadcast("alerts", {"type": "alert", "data": alert_dict})


async def broadcast_flow(flow_dict: dict[str, Any]) -> None:
    """Broadcast a new flow to all /ws/flows subscribers."""
    await manager.broadcast("flows", {"type": "flow", "data": flow_dict})
