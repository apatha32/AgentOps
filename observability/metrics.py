"""Prometheus metrics definitions shared across the app."""
from prometheus_client import Counter, Histogram, Summary

# Agent step counters
agent_steps_total = Counter(
    "agentops_agent_steps_total",
    "Total agent steps executed",
    ["agent_name", "event_type"],
)

# Per-agent latency (p50/p95/p99 via histogram)
agent_latency_seconds = Histogram(
    "agentops_agent_latency_seconds",
    "Agent step latency in seconds",
    ["agent_name"],
    buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

# Task outcomes
task_outcomes_total = Counter(
    "agentops_task_outcomes_total",
    "Task completion outcomes",
    ["status"],  # done | failed | fallback
)

# Circuit breaker state changes
circuit_breaker_trips_total = Counter(
    "agentops_circuit_breaker_trips_total",
    "Number of times a circuit breaker tripped OPEN",
    ["breaker_name"],
)

# Tool call results
tool_calls_total = Counter(
    "agentops_tool_calls_total",
    "Agent tool call outcomes",
    ["tool_name", "result"],  # result: success | error | cb_open
)
