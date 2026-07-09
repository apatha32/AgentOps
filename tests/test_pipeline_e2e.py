"""End-to-end smoke test for the LangGraph pipeline.

Uses a mocked ChatOpenAI so no real OpenAI key is required in CI.
Spins up an in-memory SQLite database so no Postgres or Redis is needed.
"""
from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from db.postgres import Base


# ---------------------------------------------------------------------------
# In-memory async SQLite engine for the test
# ---------------------------------------------------------------------------

@pytest.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as session:
        yield session
    await engine.dispose()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_llm_mock(response_json: dict):
    """Return a ChatOpenAI mock whose ainvoke returns the given dict as JSON."""
    msg = AIMessage(content=json.dumps(response_json))
    mock = MagicMock()
    mock.ainvoke = AsyncMock(return_value=msg)
    return mock


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_pipeline_routes_to_resolver(db_session: AsyncSession):
    """Triage classifies as infra + resolver_agent; pipeline completes without error."""

    triage_response = {
        "category": "infra",
        "priority": "high",
        "summary": "High CPU detected",
        "next_agent": "resolver_agent",
    }
    resolver_response = {
        "resolution": "Restart the offending process.",
        "actions": ["SSH to host", "kill -9 <PID>"],
        "confidence": 0.9,
        "escalate": False,
    }

    triage_llm = _make_llm_mock(triage_response)
    resolver_llm = _make_llm_mock(resolver_response)

    with (
        patch("agents.triage_agent.ChatOpenAI", return_value=triage_llm),
        patch("agents.resolver_agent.ChatOpenAI", return_value=resolver_llm),
        patch("db.redis_client.publish_event", new_callable=AsyncMock),
        patch("agents.tools.check_system_status._check_system_status_impl", new_callable=AsyncMock,
              return_value={"service": "api", "status": "healthy"}),
        patch("agents.tools.search_runbook._search_runbook_impl", new_callable=AsyncMock,
              return_value="Runbook: check CPU"),
    ):
        from orchestration.graph import run_pipeline

        task_id = str(uuid.uuid4())
        state = await run_pipeline(
            db_session,
            task_id,
            title="High CPU on api-server-01",
            description="CPU at 98% for 10 minutes",
            service="api",
        )

    assert state.get("category") == "infra"
    assert state.get("resolved") is True
    assert state.get("confidence") == pytest.approx(0.9)


@pytest.mark.asyncio
async def test_pipeline_routes_through_research(db_session: AsyncSession):
    """Triage routes to research_agent first, then resolver receives enriched state."""

    triage_response = {
        "category": "app",
        "priority": "medium",
        "summary": "Unknown latency spike",
        "next_agent": "research_agent",
    }
    research_response = {
        "system_status": {"status": "degraded"},
        "runbook": "Check deployment logs",
        "root_cause_hypothesis": "Recent deploy introduced regression",
        "recommended_action": "Roll back the last deploy",
    }
    resolver_response = {
        "resolution": "Roll back deployment v1.4.2.",
        "actions": ["kubectl rollout undo deployment/api"],
        "confidence": 0.85,
        "escalate": False,
    }

    triage_llm = _make_llm_mock(triage_response)
    research_llm = _make_llm_mock(research_response)
    resolver_llm = _make_llm_mock(resolver_response)

    with (
        patch("agents.triage_agent.ChatOpenAI", return_value=triage_llm),
        patch("agents.research_agent.ChatOpenAI", return_value=research_llm),
        patch("agents.resolver_agent.ChatOpenAI", return_value=resolver_llm),
        patch("db.redis_client.publish_event", new_callable=AsyncMock),
        patch("agents.tools.check_system_status._check_system_status_impl", new_callable=AsyncMock,
              return_value={"service": "api", "status": "degraded"}),
        patch("agents.tools.search_runbook._search_runbook_impl", new_callable=AsyncMock,
              return_value="Check deployment logs"),
    ):
        from orchestration.graph import run_pipeline

        task_id = str(uuid.uuid4())
        state = await run_pipeline(
            db_session,
            task_id,
            title="Unknown latency spike in checkout",
            description="P99 jumped from 200ms to 4s. No recent deploys visible.",
            service="api",
        )

    assert state.get("research_done") is True
    assert state.get("resolved") is True
    assert state.get("category") == "app"
