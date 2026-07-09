"""Triage Agent — classifies incoming tasks and routes them to the correct resolver.

Reasoning:
  - Reads the task title + description
  - Uses an LLM prompt to determine category: infra | db | app | unknown
  - Returns { category, priority, next_agent }
"""
from __future__ import annotations

import uuid
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from agents.base_agent import BaseAgent

_SYSTEM_PROMPT = """You are a triage agent for an operations platform.
Given an incident description, respond with a JSON object containing:
  - "category": one of ["infra", "db", "app", "security", "unknown"]
  - "priority": one of ["critical", "high", "medium", "low"]
  - "summary": one concise sentence describing the issue
  - "next_agent": one of ["resolver_agent", "research_agent"]
    (use research_agent when root cause is unclear, resolver_agent otherwise)

Respond ONLY with the JSON object, no markdown fences."""


class TriageAgent(BaseAgent):
    name = "triage_agent"

    def __init__(self, session: Any, llm: ChatOpenAI | None = None) -> None:
        super().__init__(session)
        self._llm = llm or ChatOpenAI(model="gpt-4o-mini", temperature=0)

    async def _execute(self, task_id: uuid.UUID, input_data: dict[str, Any]) -> dict[str, Any]:
        title = input_data.get("title", "")
        description = input_data.get("description", "")

        messages = [
            SystemMessage(content=_SYSTEM_PROMPT),
            HumanMessage(content=f"Title: {title}\n\nDescription: {description}"),
        ]

        response = await self._llm.ainvoke(messages)
        import json

        try:
            parsed = json.loads(response.content)
        except json.JSONDecodeError:
            parsed = {
                "category": "unknown",
                "priority": "medium",
                "summary": response.content,
                "next_agent": "resolver_agent",
            }

        return {**input_data, **parsed, "triage_done": True}
