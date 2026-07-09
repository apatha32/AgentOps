"""LangGraph multi-agent orchestration graph.

Flow:
  START → triage_node → [research_node OR resolver_node] → END

The edge from triage → next is a conditional edge driven by
the `next_agent` field populated by TriageAgent.
"""
from __future__ import annotations

import uuid
from typing import Any

from langgraph.graph import END, START, StateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from agents import ResearchAgent, ResolverAgent, TriageAgent
from orchestration.state import AgentState


# ---------------------------------------------------------------------------
# Node factories
# ---------------------------------------------------------------------------

def _make_triage_node(session: AsyncSession):
    agent = TriageAgent(session)

    async def triage_node(state: AgentState) -> AgentState:
        task_id = uuid.UUID(state["task_id"])
        result = await agent.run(task_id, dict(state))
        return {**state, **result}

    return triage_node


def _make_research_node(session: AsyncSession):
    agent = ResearchAgent(session)

    async def research_node(state: AgentState) -> AgentState:
        task_id = uuid.UUID(state["task_id"])
        result = await agent.run(task_id, dict(state))
        return {**state, **result}

    return research_node


def _make_resolver_node(session: AsyncSession):
    agent = ResolverAgent(session)

    async def resolver_node(state: AgentState) -> AgentState:
        task_id = uuid.UUID(state["task_id"])
        result = await agent.run(task_id, dict(state))
        return {**state, **result}

    return resolver_node


# ---------------------------------------------------------------------------
# Conditional routing
# ---------------------------------------------------------------------------

def _route_after_triage(state: AgentState) -> str:
    """Return the name of the next graph node based on triage output."""
    return state.get("next_agent", "resolver_agent")


def _route_after_research(state: AgentState) -> str:
    return "resolver_agent"


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------

def build_graph(session: AsyncSession) -> Any:
    """Compile and return the LangGraph runnable."""
    graph = StateGraph(AgentState)

    graph.add_node("triage_agent", _make_triage_node(session))
    graph.add_node("research_agent", _make_research_node(session))
    graph.add_node("resolver_agent", _make_resolver_node(session))

    graph.add_edge(START, "triage_agent")

    graph.add_conditional_edges(
        "triage_agent",
        _route_after_triage,
        {
            "research_agent": "research_agent",
            "resolver_agent": "resolver_agent",
        },
    )

    graph.add_edge("research_agent", "resolver_agent")
    graph.add_edge("resolver_agent", END)

    return graph.compile()


async def run_pipeline(session: AsyncSession, task_id: str, title: str, description: str, service: str = "api") -> AgentState:
    """Convenience function: build the graph and invoke it for one task."""
    app = build_graph(session)
    initial_state: AgentState = {
        "task_id": task_id,
        "title": title,
        "description": description,
        "service": service,
    }
    final_state: AgentState = await app.ainvoke(initial_state)
    return final_state
