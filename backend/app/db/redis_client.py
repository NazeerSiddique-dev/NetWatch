"""
Redis Client
=============
Provides an async Redis client and helper utilities for NetWatch streams.
Gracefully handles Redis being unavailable (falls back to in-memory queues).
"""

from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_redis_client = None
_redis_available = False

# In-memory fallback queues when Redis is unavailable
_fallback_queues: dict[str, asyncio.Queue] = defaultdict(lambda: asyncio.Queue(maxsize=1000))


async def init_redis() -> bool:
    """Initialize the Redis connection. Returns True if connected."""
    global _redis_client, _redis_available
    settings = get_settings()
    try:
        import redis.asyncio as aioredis

        client = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=3,
            socket_timeout=3,
        )
        await client.ping()
        _redis_client = client
        _redis_available = True
        logger.info("redis_connected", url=settings.redis_url)
        return True
    except Exception as exc:
        _redis_available = False
        _redis_client = None
        logger.warning(
            "redis_unavailable",
            error=str(exc),
            fallback="in_memory_queues",
        )
        return False


async def close_redis() -> None:
    """Close the Redis connection."""
    global _redis_client, _redis_available
    if _redis_client:
        await _redis_client.aclose()
        _redis_client = None
        _redis_available = False
        logger.info("redis_closed")


def is_redis_available() -> bool:
    """Return True if Redis is connected and available."""
    return _redis_available


def get_redis():
    """Return the raw Redis client (or None if unavailable)."""
    return _redis_client


async def publish_to_stream(stream: str, data: dict[str, Any]) -> str | None:
    """
    Publish a message to a Redis Stream.
    Falls back to an asyncio queue when Redis is unavailable.
    """
    settings = get_settings()

    if _redis_available and _redis_client:
        try:
            # Redis Stream XADD
            msg_id = await _redis_client.xadd(
                stream,
                {k: json.dumps(v) if not isinstance(v, str) else v for k, v in data.items()},
                maxlen=settings.redis_stream_max_len,
                approximate=True,
            )
            return msg_id
        except Exception as exc:
            logger.error("redis_publish_error", stream=stream, error=str(exc))

    # Fallback: in-memory queue
    queue = _fallback_queues[stream]
    try:
        queue.put_nowait(data)
    except asyncio.QueueFull:
        # Drop oldest item to make room
        try:
            queue.get_nowait()
        except asyncio.QueueEmpty:
            pass
        queue.put_nowait(data)
    return None


async def read_from_stream(
    stream: str,
    consumer_group: str,
    consumer_name: str,
    count: int = 10,
    block_ms: int = 1000,
) -> list[dict[str, Any]]:
    """
    Read messages from a Redis Stream using consumer groups.
    Falls back to asyncio queue when Redis is unavailable.
    """
    if _redis_available and _redis_client:
        try:
            await _ensure_consumer_group(stream, consumer_group)
            entries = await _redis_client.xreadgroup(
                groupname=consumer_group,
                consumername=consumer_name,
                streams={stream: ">"},
                count=count,
                block=block_ms,
            )
            messages = []
            if entries:
                for _, msgs in entries:
                    for msg_id, fields in msgs:
                        try:
                            parsed = {k: json.loads(v) for k, v in fields.items()}
                            parsed["_stream_id"] = msg_id
                            messages.append(parsed)
                        except (json.JSONDecodeError, ValueError):
                            messages.append(dict(fields))
                        # Acknowledge message
                        await _redis_client.xack(stream, consumer_group, msg_id)
            return messages
        except Exception as exc:
            logger.error("redis_read_error", stream=stream, error=str(exc))

    # Fallback: drain in-memory queue
    queue = _fallback_queues[stream]
    messages = []
    for _ in range(min(count, queue.qsize())):
        try:
            messages.append(queue.get_nowait())
        except asyncio.QueueEmpty:
            break
    return messages


async def _ensure_consumer_group(stream: str, group: str) -> None:
    """Create a consumer group if it doesn't exist."""
    try:
        await _redis_client.xgroup_create(stream, group, id="0", mkstream=True)
    except Exception:
        pass  # Group already exists


async def get_stream_info() -> dict[str, Any]:
    """Return information about all NetWatch streams."""
    settings = get_settings()
    streams = [
        settings.stream_raw_packets,
        settings.stream_flows,
        settings.stream_metrics,
        settings.stream_alerts,
    ]
    info = {}
    if _redis_available and _redis_client:
        for stream in streams:
            try:
                length = await _redis_client.xlen(stream)
                info[stream] = {"length": length, "backend": "redis"}
            except Exception:
                info[stream] = {"length": 0, "backend": "redis", "error": True}
    else:
        for stream in streams:
            info[stream] = {
                "length": _fallback_queues[stream].qsize(),
                "backend": "memory",
            }
    return info


async def publish_metrics(metrics: dict[str, Any]) -> None:
    """Convenience wrapper: publish to the metrics stream."""
    await publish_to_stream(get_settings().stream_metrics, metrics)


async def publish_alert(alert: dict[str, Any]) -> None:
    """Convenience wrapper: publish to the alerts stream."""
    await publish_to_stream(get_settings().stream_alerts, alert)


async def publish_flow(flow: dict[str, Any]) -> None:
    """Convenience wrapper: publish to the flows stream."""
    await publish_to_stream(get_settings().stream_flows, flow)
