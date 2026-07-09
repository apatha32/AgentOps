"""Traces router — retrieve agent events and Server-Sent Events stream."""
from __future__ import annotations

import asyncio
import json
import uuid

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models import AgentEventResponse
from db.postgres import AgentEvent, Task, get_session
from db.redis_client import get_redis

router = APIRouter(prefix="/traces", tags=["traces"])


@router.get("/{task_id}", response_model=list[AgentEventResponse])
async def get_trace(task_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    """Return the full ordered trace for a given task."""
    task = await session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    result = await session.execute(
        select(AgentEvent)
        .where(AgentEvent.task_id == task_id)
        .order_by(AgentEvent.created_at.asc())
    )
    events = result.scalars().all()
    # Deserialize payload JSON string for the response
    out = []
    for e in events:
        d = {
            "id": e.id,
            "task_id": e.task_id,
            "agent_name": e.agent_name,
            "event_type": e.event_type,
            "payload": json.loads(e.payload),
            "latency_ms": e.latency_ms,
            "created_at": e.created_at,
        }
        out.append(d)
    return out


@router.get("/{task_id}/stream")
async def stream_trace(task_id: uuid.UUID):
    """Server-Sent Events stream for live agent trace updates."""

    async def event_generator():
        r: aioredis.Redis = get_redis()
        pubsub = r.pubsub()
        await pubsub.subscribe(f"task:{task_id}")

        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    data = message["data"]
                    yield f"data: {data}\n\n"
                await asyncio.sleep(0)
        except asyncio.CancelledError:
            pass
        finally:
            await pubsub.unsubscribe(f"task:{task_id}")
            await pubsub.aclose()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
