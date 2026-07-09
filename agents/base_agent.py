"""Base agent class: wraps an LLM chain and emits structured events to Postgres + Redis pub/sub."""
from __future__ import annotations

import json
import time
import uuid
from abc import ABC, abstractmethod
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from db.postgres import AgentEvent
from db.redis_client import publish_event
from observability.metrics import agent_latency_seconds, agent_steps_total
from observability.tracing import get_tracer


class BaseAgent(ABC):
    name: str = "base"

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._tracer = get_tracer()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def run(self, task_id: uuid.UUID, input_data: dict[str, Any]) -> dict[str, Any]:
        """Entry point called by the orchestration graph."""
        await self._emit_event(task_id, "start", {"input": input_data})
        start = time.perf_counter()
        try:
            result = await self._execute(task_id, input_data)
            latency_ms = (time.perf_counter() - start) * 1000
            agent_latency_seconds.labels(agent_name=self.name).observe(latency_ms / 1000)
            await self._emit_event(task_id, "complete", {"output": result, "latency_ms": latency_ms})
            return result
        except Exception as exc:
            latency_ms = (time.perf_counter() - start) * 1000
            await self._emit_event(task_id, "error", {"error": str(exc), "latency_ms": latency_ms})
            raise

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @abstractmethod
    async def _execute(self, task_id: uuid.UUID, input_data: dict[str, Any]) -> dict[str, Any]:
        """Subclasses implement the actual agent logic here."""

    async def _emit_event(
        self,
        task_id: uuid.UUID,
        event_type: str,
        payload: dict[str, Any],
        latency_ms: float | None = None,
    ) -> None:
        agent_steps_total.labels(agent_name=self.name, event_type=event_type).inc()

        event = AgentEvent(
            task_id=task_id,
            agent_name=self.name,
            event_type=event_type,
            payload=json.dumps(payload, default=str),
            latency_ms=latency_ms,
        )
        self._session.add(event)
        await self._session.commit()

        # Publish to Redis for real-time SSE streaming
        await publish_event(
            channel=f"task:{task_id}",
            event={
                "agent": self.name,
                "event_type": event_type,
                "payload": payload,
                "task_id": str(task_id),
            },
        )

    async def _emit_tool_call(
        self,
        task_id: uuid.UUID,
        tool_name: str,
        tool_input: Any,
        tool_output: Any,
        latency_ms: float,
    ) -> None:
        await self._emit_event(
            task_id,
            "tool_call",
            {
                "tool": tool_name,
                "input": tool_input,
                "output": tool_output,
                "latency_ms": latency_ms,
            },
            latency_ms=latency_ms,
        )
