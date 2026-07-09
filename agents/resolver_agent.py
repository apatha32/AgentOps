"""Resolver Agent — produces the final action plan for an incident.

Optionally calls check_system_status and search_runbook if research hasn't been done yet.
Returns { resolution, actions, confidence }.
"""
from __future__ import annotations

import time
import uuid
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from agents.base_agent import BaseAgent
from agents.tools import check_system_status, search_runbook

_SYSTEM_PROMPT = """You are a resolver agent for an operations platform.
Given a triaged (and optionally researched) incident, produce an actionable resolution plan.

Return a JSON object:
  {
    "resolution": <one-paragraph resolution description>,
    "actions": [<ordered list of concrete action strings>],
    "confidence": <float 0-1>,
    "escalate": <bool — true if human escalation is needed>
  }

Respond ONLY with the JSON object."""


class ResolverAgent(BaseAgent):
    name = "resolver_agent"

    def __init__(self, session: Any, llm: ChatOpenAI | None = None) -> None:
        super().__init__(session)
        self._llm = llm or ChatOpenAI(model="gpt-4o-mini", temperature=0)

    async def _execute(self, task_id: uuid.UUID, input_data: dict[str, Any]) -> dict[str, Any]:
        title = input_data.get("title", "")
        category = input_data.get("category", "unknown")
        priority = input_data.get("priority", "medium")
        research = input_data.get("research", {})
        runbook = input_data.get("runbook")
        service = input_data.get("service", category)

        # If research agent didn't run, fetch basics ourselves
        if not runbook:
            t0 = time.perf_counter()
            runbook = await search_runbook(title)
            await self._emit_tool_call(
                task_id, "search_runbook", title, runbook, (time.perf_counter() - t0) * 1000
            )

        status = input_data.get("system_status")
        if not status:
            t0 = time.perf_counter()
            status = await check_system_status(service)
            await self._emit_tool_call(
                task_id, "check_system_status", service, status, (time.perf_counter() - t0) * 1000
            )

        messages = [
            SystemMessage(content=_SYSTEM_PROMPT),
            HumanMessage(
                content=(
                    f"Incident: {title}\n"
                    f"Category: {category} | Priority: {priority}\n"
                    f"System status: {status}\n"
                    f"Runbook: {runbook}\n"
                    f"Research findings: {research}"
                )
            ),
        ]
        response = await self._llm.ainvoke(messages)

        import json

        try:
            resolution = json.loads(response.content)
        except json.JSONDecodeError:
            resolution = {
                "resolution": response.content,
                "actions": [],
                "confidence": 0.5,
                "escalate": True,
            }

        return {**input_data, **resolution, "resolved": True}
