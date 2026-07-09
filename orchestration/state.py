"""LangGraph shared state schema for the AgentOps pipeline."""
from __future__ import annotations

import uuid
from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    # Task identity
    task_id: str
    title: str
    description: str
    service: str

    # Triage outputs
    category: str
    priority: str
    summary: str
    next_agent: str
    triage_done: bool

    # Research outputs
    system_status: dict[str, Any]
    runbook: str
    research: dict[str, Any]
    research_done: bool

    # Resolution outputs
    resolution: str
    actions: list[str]
    confidence: float
    escalate: bool
    resolved: bool

    # Pipeline metadata
    error: str
