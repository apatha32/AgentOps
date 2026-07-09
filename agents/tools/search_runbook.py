"""Tool: search_runbook — looks up operational runbooks from an in-memory store.

In production this would hit a vector DB (e.g., pgvector) over your runbook corpus.
The circuit breaker demo simulates transient failures via an env flag.
"""
from __future__ import annotations

import os
import random

from circuit_breaker import circuit_breaker
from observability.metrics import tool_calls_total

# Simulated runbook store
_RUNBOOKS: dict[str, str] = {
    "high_cpu": "Runbook: SSH to host → run `top` → identify PID → `kill -9 <PID>` → alert on-call.",
    "disk_full": "Runbook: `du -sh /*` → identify large dirs → prune old logs → resize volume if needed.",
    "db_slow_query": "Runbook: check pg_stat_activity → EXPLAIN ANALYZE → add missing index → VACUUM.",
    "service_crash": "Runbook: `systemctl status <svc>` → check journalctl → restart → page team if loop-crashing.",
    "default": "No specific runbook found. Escalate to on-call engineer.",
}

SIMULATE_FAILURES = os.getenv("SIMULATE_TOOL_FAILURES", "false").lower() == "true"


async def _search_runbook_impl(keyword: str) -> str:
    """Inner implementation — wrapped by circuit breaker."""
    if SIMULATE_FAILURES and random.random() < 0.4:
        raise RuntimeError("Simulated runbook service timeout")

    keyword_lower = keyword.lower()
    for key, runbook in _RUNBOOKS.items():
        if key in keyword_lower:
            return runbook
    return _RUNBOOKS["default"]


async def _search_runbook_fallback(keyword: str) -> str:
    tool_calls_total.labels(tool_name="search_runbook", result="cb_open").inc()
    return "⚠️ Runbook service unavailable (circuit open). Escalate to on-call immediately."


@circuit_breaker(
    name="search_runbook",
    failure_threshold=3,
    recovery_timeout=20.0,
    fallback=_search_runbook_fallback,
)
async def search_runbook(keyword: str) -> str:
    """Search operational runbooks by keyword. Returns the most relevant runbook."""
    result = await _search_runbook_impl(keyword)
    tool_calls_total.labels(tool_name="search_runbook", result="success").inc()
    return result
