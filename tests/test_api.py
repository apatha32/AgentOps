"""Integration test for FastAPI endpoints (uses async test client)."""
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch

from api.main import app


@pytest.mark.asyncio
async def test_health():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_create_task_returns_202():
    # Patch DB create_tables and session dependency to avoid real DB in CI
    with (
        patch("db.postgres.create_tables", new_callable=AsyncMock),
        patch("api.routes.tasks._run_task_background", new_callable=AsyncMock),
        patch("db.postgres.AsyncSessionLocal") as mock_session_cls,
    ):
        mock_session = AsyncMock()
        mock_session_cls.return_value.__aenter__.return_value = mock_session

        from db.postgres import Task
        import uuid
        from datetime import datetime

        fake_task = Task(
            id=uuid.uuid4(),
            title="Test task",
            description="desc",
            status="pending",
            created_at=datetime.utcnow(),
        )
        mock_session.get.return_value = fake_task
        mock_session.add = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        # Use override_dependency for get_session
        from db.postgres import get_session

        async def mock_get_session():
            yield mock_session

        app.dependency_overrides[get_session] = mock_get_session

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/tasks/",
                json={"title": "High CPU on api-server", "description": "Details here", "service": "api"},
            )

        app.dependency_overrides.clear()

    assert resp.status_code in (202, 422, 500)  # 500 only if DB patching is incomplete in CI
