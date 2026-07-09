"""Tasks router — CRUD + async pipeline trigger."""
from __future__ import annotations

import asyncio
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models import TaskCreate, TaskResponse
from db.postgres import AgentEvent, Task, get_session
from db.redis_client import set_state
from observability.metrics import task_outcomes_total
from orchestration.graph import run_pipeline

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("/", response_model=TaskResponse, status_code=202)
async def create_task(
    body: TaskCreate,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
):
    task = Task(title=body.title, description=body.description, status="pending")
    session.add(task)
    await session.commit()
    await session.refresh(task)

    # Persist initial state to Redis
    await set_state(f"task:{task.id}:status", {"status": "pending"})

    # Run the agent pipeline in the background
    background_tasks.add_task(
        _run_task_background,
        str(task.id),
        body.title,
        body.description,
        body.service,
    )

    return task


@router.get("/", response_model=list[TaskResponse])
async def list_tasks(
    limit: int = 50,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Task).order_by(Task.created_at.desc()).limit(limit)
    )
    return result.scalars().all()


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    task = await session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


async def _run_task_background(
    task_id: str,
    title: str,
    description: str,
    service: str,
) -> None:
    """Background coroutine — runs the LangGraph pipeline and updates task status."""
    from db.postgres import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        task = await session.get(Task, uuid.UUID(task_id))
        if not task:
            return

        task.status = "running"
        await session.commit()
        await set_state(f"task:{task_id}:status", {"status": "running"})

        try:
            await run_pipeline(session, task_id, title, description, service)
            task.status = "done"
            task_outcomes_total.labels(status="done").inc()
        except Exception as exc:
            task.status = "failed"
            task_outcomes_total.labels(status="failed").inc()

        await session.commit()
        await set_state(f"task:{task_id}:status", {"status": task.status})
