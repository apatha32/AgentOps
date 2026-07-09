"""Async Redis client wrapper for agent state and task queue."""
from __future__ import annotations

import json
from typing import Any

import redis.asyncio as aioredis

from config import settings

_pool: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    global _pool
    if _pool is None:
        _pool = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _pool


async def push_task(queue: str, payload: dict[str, Any]) -> None:
    r = get_redis()
    await r.rpush(queue, json.dumps(payload))


async def pop_task(queue: str, timeout: int = 5) -> dict[str, Any] | None:
    r = get_redis()
    result = await r.blpop(queue, timeout=timeout)
    if result is None:
        return None
    _, raw = result
    return json.loads(raw)


async def set_state(key: str, value: dict[str, Any], ttl: int = 3600) -> None:
    r = get_redis()
    await r.set(key, json.dumps(value), ex=ttl)


async def get_state(key: str) -> dict[str, Any] | None:
    r = get_redis()
    raw = await r.get(key)
    return json.loads(raw) if raw else None


async def publish_event(channel: str, event: dict[str, Any]) -> None:
    """Publish an agent event on a pub/sub channel (used by the SSE stream)."""
    r = get_redis()
    await r.publish(channel, json.dumps(event))
