"""Tool: check_system_status — returns simulated system health metrics.

In production this would query Prometheus / Datadog / your monitoring stack.
"""
from __future__ import annotations

import os
import random

from circuit_breaker import circuit_breaker
from observability.metrics import tool_calls_total

SIMULATE_FAILURES = os.getenv("SIMULATE_TOOL_FAILURES", "false").lower() == "true"


async def _check_system_status_impl(service_name: str) -> dict:
    if SIMULATE_FAILURES and random.random() < 0.3:
        raise RuntimeError("Simulated monitoring endpoint timeout")

    # Simulated system status response
    return {
        "service": service_name,
        "status": random.choice(["healthy", "degraded", "healthy", "healthy"]),
        "cpu_pct": round(random.uniform(10, 95), 1),
        "mem_pct": round(random.uniform(20, 90), 1),
        "p99_latency_ms": round(random.uniform(50, 800), 1),
        "error_rate_pct": round(random.uniform(0, 5), 2),
    }


async def _check_system_status_fallback(service_name: str) -> dict:
    tool_calls_total.labels(tool_name="check_system_status", result="cb_open").inc()
    return {
        "service": service_name,
        "status": "unknown",
        "error": "Monitoring service unavailable (circuit open).",
    }


@circuit_breaker(
    name="check_system_status",
    failure_threshold=3,
    recovery_timeout=20.0,
    fallback=_check_system_status_fallback,
)
async def check_system_status(service_name: str) -> dict:
    """Return current health metrics for a named service."""
    result = await _check_system_status_impl(service_name)
    tool_calls_total.labels(tool_name="check_system_status", result="success").inc()
    return result
