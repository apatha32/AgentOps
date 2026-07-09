"""FastAPI application entry point."""
from __future__ import annotations

import secrets
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator

from api.routes import tasks_router, traces_router
from db.postgres import create_tables
from observability.tracing import init_tracing
from config import settings

_EXEMPT_PATHS = {"/health", "/metrics", "/openapi.json", "/docs", "/redoc"}


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


@app.middleware("http")
async def api_key_middleware(request: Request, call_next):
    """Reject requests missing a valid X-API-Key header when API_KEY is configured."""
    configured_key = settings.api_key
    if configured_key and request.url.path not in _EXEMPT_PATHS:
        provided = request.headers.get("X-API-Key", "")
        if not secrets.compare_digest(provided, configured_key):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid or missing X-API-Key header"},
            )
    return await call_next(request)

# Prometheus /metrics endpoint
Instrumentator().instrument(app).expose(app)

app.include_router(tasks_router)
app.include_router(traces_router)


@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok"}
