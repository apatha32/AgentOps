"""Research Agent — called when the triage agent cannot determine root cause.

Uses tool-calling to:
  1. check_system_status for the relevant service
  2. search_runbook for remediation steps

Returns enriched context that gets passed back to the resolver.
"""
from __future__ import annotations

import time
import uuid
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from agents.base_agent import BaseAgent
from agents.tools import check_system_status, search_runbook

_SYSTEM_PROMPT = """You are a research agent for an operations platform.
You have access to:
  - system status for a service (CPU, memory, latency, error rate)
  - runbook lookup by keyword

Given the incident details, investigate and return a JSON object:
  {
    "system_status": <dict from check_system_status>,
    "runbook": <string from search_runbook>,
    "root_cause_hypothesis": <one-sentence hypothesis>,
    "recommended_action": <one-sentence action>
  }

Respond ONLY with the JSON object."""


class ResearchAgent(BaseAgent):
    name = "research_agent"

    def __init__(self, session: Any, llm: ChatOpenAI | None = None) -> None:
        super().__init__(session)
        self._llm = llm or ChatOpenAI(model="gpt-4o-mini", temperature=0)

    async def _execute(self, task_id: uuid.UUID, input_data: dict[str, Any]) -> dict[str, Any]:
        category = input_data.get("category", "unknown")
        title = input_data.get("title", "")
        service = input_data.get("service", category)

        # Tool call 1: system status
        t0 = time.perf_counter()
        status = await check_system_status(service)
        await self._emit_tool_call(
            task_id, "check_system_status", service, status, (time.perf_counter() - t0) * 1000
        )

        # Tool call 2: runbook search
        t0 = time.perf_counter()
        runbook = await search_runbook(title)
        await self._emit_tool_call(
            task_id, "search_runbook", title, runbook, (time.perf_counter() - t0) * 1000
        )

        # LLM synthesis
        messages = [
            SystemMessage(content=_SYSTEM_PROMPT),
            HumanMessage(
                content=(
                    f"Incident: {title}\n"
                    f"System status: {status}\n"
                    f"Runbook: {runbook}"
                )
            ),
        ]
        response = await self._llm.ainvoke(messages)

        import json

        try:
            research_result = json.loads(response.content)
        except json.JSONDecodeError:
            research_result = {"raw": response.content}

        return {
            **input_data,
            "system_status": status,
            "runbook": runbook,
            "research": research_result,
            "research_done": True,
        }
