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
    try:
        await create_tables()
    except Exception as exc:
        import logging
        logging.getLogger(__name__).error("DB table init failed: %s", exc)
    yield


app = FastAPI(
    title="AgentOps API",
    version="1.0.0",
    description="Multi-agent ops platform with live observability",
    lifespan=lifespan,
)

_origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import logging
    logging.getLogger(__name__).exception("Unhandled error: %s", exc)
    origin = request.headers.get("origin", "")
    headers = {}
    if origin in _origins or "*" in _origins:
        headers["Access-Control-Allow-Origin"] = origin or "*"
        headers["Access-Control-Allow-Credentials"] = "true"
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)},
        headers=headers,
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
try:
    Instrumentator().instrument(app).expose(app)
except Exception:
    pass  # Prometheus instrumentation is optional

app.include_router(tasks_router)
app.include_router(traces_router)


@app.get("/health", tags=["health"])
async def health():
    import os
    dsn = settings.postgres_dsn
    import re
    masked = re.sub(r"://[^:]+:[^@]+@", "://***:***@", dsn)
    return {"status": "ok", "v": "6", "dsn": masked, "redis": settings.redis_url[:30]}


@app.get("/debug-config", include_in_schema=False)
async def debug_config():
    """Temporary: shows DSN host only to verify config."""
    import re
    dsn = settings.postgres_dsn
    masked = re.sub(r"://[^:]+:[^@]+@", "://***:***@", dsn)
    return {"postgres_dsn_masked": masked, "redis_url": settings.redis_url[:40]}


@app.get("/", include_in_schema=False)
async def root():
    return {"status": "ok", "service": "AgentOps API"}
