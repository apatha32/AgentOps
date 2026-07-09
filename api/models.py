"""Pydantic request/response schemas for the API layer."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=512)
    description: str = Field(default="", max_length=4096)
    service: str = Field(default="api", max_length=128)


class TaskResponse(BaseModel):
    id: uuid.UUID
    title: str
    description: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class AgentEventResponse(BaseModel):
    id: uuid.UUID
    task_id: uuid.UUID
    agent_name: str
    event_type: str
    payload: Any
    latency_ms: float | None
    created_at: datetime

    model_config = {"from_attributes": True}
