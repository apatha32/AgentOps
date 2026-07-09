"""FastAPI application entry point."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from api.routes import tasks_router, traces_router
from db.postgres import create_tables
from observability.tracing import init_tracing


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_tracing("agentops-api")
    await create_tables()
    yield


app = FastAPI(
    title="AgentOps API",
    version="1.0.0",
    description="Multi-agent ops platform with live observability",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus /metrics endpoint
Instrumentator().instrument(app).expose(app)

app.include_router(tasks_router)
app.include_router(traces_router)


@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok"}
