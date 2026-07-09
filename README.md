# AgentOps: Multi-Agent Ops Platform with Live Observability

A flagship portfolio project demonstrating multi-agent orchestration, real-time observability, circuit breakers, and distributed systems design in one end-to-end demoable platform.

---

## What It Is

AgentOps is an operations platform where multiple specialized AI agents collaborate on incoming tasks (infrastructure alerts, application incidents, database issues). Each agent has a defined role in the pipeline. Every reasoning step, tool call, handoff, and failure is logged to Postgres and streamed live to a React dashboard.

The project simultaneously covers AI Engineer interviews (multi-agent orchestration, tool calling, evals), FDE interviews (ambiguous problem decomposed end to end), and SDE interviews (distributed message passing, circuit breakers, observability, Kubernetes).

---

## Architecture

```
User / Alert
    |
    v
FastAPI (REST + SSE)
    |
    +-- POST /tasks/  -->  LangGraph Pipeline
    |                           |
    |                       TriageAgent (GPT-4o-mini)
    |                           |
    |              +------------+-----------+
    |         ResearchAgent           ResolverAgent
    |              |                       |
    |        check_system_status     search_runbook
    |        search_runbook          check_system_status
    |              |  (circuit breaker on each tool)
    |              +------------+-----------+
    |                       ResolverAgent
    |                           |
    |               Postgres (audit log of every agent decision)
    |               Redis pub/sub (live event broadcast)
    |
    +-- GET /traces/{id}/stream  -->  SSE  -->  React Dashboard
```

### Agent Roles

- **TriageAgent**: classifies the incident category (infra, db, app, security) and priority, then decides whether to route to ResearchAgent (unclear root cause) or ResolverAgent (known pattern).
- **ResearchAgent**: calls `check_system_status` and `search_runbook` tools, then asks the LLM to synthesize a root cause hypothesis.
- **ResolverAgent**: produces an ordered action plan, confidence score, and escalation flag.

---

## Stack

| Layer | Technology |
|---|---|
| Agent Orchestration | LangGraph StateGraph |
| LLM | OpenAI GPT-4o-mini |
| API | FastAPI + Uvicorn |
| Task Queue / State | Redis (pub/sub + key-value) |
| Audit Log | PostgreSQL via SQLAlchemy async |
| Resilience | Circuit Breaker (CLOSED / OPEN / HALF_OPEN) |
| Observability | OpenTelemetry traces + Prometheus metrics |
| Dashboard | React 18 + Vite + Tailwind + Recharts |
| Containers | Docker Compose (dev) / Kubernetes (prod) |
| Autoscaling | HPA on CPU 60% and Memory 70% |

---

## Quick Start with Docker Compose

```bash
# Copy the example env file and add your OpenAI key
cp .env.example .env

# Start all services
docker compose up --build

# Dashboard
open http://localhost:3000

# API docs (Swagger)
open http://localhost:8000/docs

# Prometheus
open http://localhost:9090

# Grafana (login: admin / agentops)
open http://localhost:3001
```

---

## Local Development (no Docker)

```bash
# Python environment
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Start only Postgres and Redis via Docker
docker compose up postgres redis -d

# Run the API
uvicorn api.main:app --reload

# Run the dashboard (separate terminal)
cd dashboard && npm install && npm run dev
```

---

## Running the Eval Harness

Runs 20 sample incidents through the full pipeline and measures category accuracy and agent routing accuracy.

```bash
python -m evals.harness --output results.json
```

Sample output:

```
Running eval on 20 tasks...
------------------------------------------------------------
[01] category=infra    agent=resolver_agent    lat=1340ms -- High CPU on api-server-01
[02] category=db       agent=resolver_agent    lat=1120ms -- Database slow queries detected
...
------------------------------------------------------------
Category accuracy:       85.0%
Agent routing accuracy:  80.0%
Avg latency:             1240 ms

Results written to results.json
```

---

## Circuit Breaker Simulation

To observe the circuit breaker in action, enable simulated failures:

```bash
SIMULATE_TOOL_FAILURES=true uvicorn api.main:app --reload
```

With this flag, `search_runbook` fails roughly 40% of the time and `check_system_status` fails roughly 30% of the time. After 3 consecutive failures the breaker trips to OPEN and the fallback response is returned immediately. After 20 seconds the breaker enters HALF_OPEN and probes with a single call. Two successive successes close the circuit again.

State machine: CLOSED -> OPEN -> HALF_OPEN -> CLOSED.

---

## Kubernetes Deploy

```bash
# Build images
docker build -f docker/Dockerfile.api -t agentops-api:latest .
docker build -f docker/Dockerfile.dashboard -t agentops-dashboard:latest .

# Update k8s/secrets.yaml with real values, then apply
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/hpa.yaml

# Watch HPA scale
kubectl get hpa agentops-api-hpa --watch
```

The HPA scales the API deployment from 2 to 10 replicas based on CPU utilization (target 60%) and memory utilization (target 70%).

---

## Running Tests

```bash
pytest
```

Tests cover the circuit breaker state machine (unit) and the FastAPI health and task creation endpoints (integration).

---

## Project Structure

```
AgentOps/
├── agents/
│   ├── base_agent.py               # Emits every step to Postgres + Redis with latency tracking
│   ├── triage_agent.py             # Category classification and agent routing
│   ├── research_agent.py           # Tool-calling agent for root cause investigation
│   ├── resolver_agent.py           # Final action plan with confidence score
│   └── tools/
│       ├── search_runbook.py       # Runbook lookup (circuit breaker protected)
│       └── check_system_status.py  # System health check (circuit breaker protected)
├── orchestration/
│   ├── graph.py                    # LangGraph StateGraph pipeline definition
│   └── state.py                    # Shared TypedDict state schema
├── api/
│   ├── main.py                     # FastAPI app with CORS, Prometheus, lifespan
│   ├── models.py                   # Pydantic request/response schemas
│   └── routes/
│       ├── tasks.py                # POST /tasks, GET /tasks, GET /tasks/{id}
│       └── traces.py               # GET /traces/{id}, GET /traces/{id}/stream (SSE)
├── db/
│   ├── postgres.py                 # SQLAlchemy models: Task, AgentEvent
│   └── redis_client.py             # Async Redis wrapper for state, queue, pub/sub
├── circuit_breaker/
│   └── breaker.py                  # CircuitBreaker class + circuit_breaker decorator
├── observability/
│   ├── tracing.py                  # OpenTelemetry tracer init
│   └── metrics.py                  # Prometheus counters and histograms
├── evals/
│   ├── harness.py                  # 20-task eval runner
│   └── sample_tasks.json           # Sample incidents with expected category and agent
├── dashboard/
│   └── src/
│       ├── App.tsx                 # Main layout: sidebar task list + trace/metrics tabs
│       ├── api.ts                  # fetch wrappers + EventSource for SSE
│       ├── types.ts                # Task and AgentEvent TypeScript interfaces
│       ├── components/
│       │   ├── AgentTrace.tsx          # Live event timeline with color per agent
│       │   ├── MetricsDashboard.tsx    # Latency bar chart + step/tool/error counts
│       │   ├── TaskList.tsx            # Sidebar task list with status badges
│       │   └── NewTaskModal.tsx        # Form to submit a new task
│       └── hooks/
│           └── useLiveTrace.ts         # SSE hook merging historic + live events
├── k8s/
│   ├── deployment.yaml             # API + dashboard deployments with health probes
│   ├── service.yaml                # ClusterIP for API, LoadBalancer for dashboard
│   ├── hpa.yaml                    # HPA targeting 60% CPU and 70% memory
│   └── secrets.yaml                # Secret template for env vars
├── docker/
│   ├── Dockerfile.api              # Python 3.12 slim image for the FastAPI server
│   ├── Dockerfile.dashboard        # Nginx serving the Vite production build
│   └── nginx.conf                  # Nginx config with SSE proxy pass settings
├── docker-compose.yml              # Full local stack
├── prometheus.yml                  # Scrape config for API and OTel collector
├── otel-collector-config.yaml      # OTLP receiver, batch processor, Prometheus exporter
├── config.py                       # Pydantic settings loaded from .env
├── requirements.txt
└── tests/
    ├── test_circuit_breaker.py     # Unit tests for CB state transitions
    └── test_api.py                 # Integration tests for FastAPI endpoints
```

---

## Observability Details

**Prometheus metrics exposed at `/metrics`:**

- `agentops_agent_steps_total` - counter, labels: agent_name, event_type
- `agentops_agent_latency_seconds` - histogram with p50/p95/p99 buckets, label: agent_name
- `agentops_task_outcomes_total` - counter, labels: status (done, failed, fallback)
- `agentops_circuit_breaker_trips_total` - counter, label: breaker_name
- `agentops_tool_calls_total` - counter, labels: tool_name, result

**OpenTelemetry traces** are exported via OTLP gRPC to the collector, which forwards to the Prometheus metrics endpoint and logs for local development. In production, swap the exporter for Jaeger or a cloud trace backend.

**Redis pub/sub** channels follow the pattern `task:{task_id}`. Every agent step published to this channel is forwarded to connected SSE clients via the `/traces/{id}/stream` endpoint.

---

## Interview Talking Points

**AI Engineer**: Multi-agent orchestration with LangGraph StateGraph. Conditional routing based on triage output. Tool calling with circuit breaker protection for graceful degradation. Eval harness measuring routing accuracy analogous to RAGAS agent evals.

**FDE**: Ambiguous ops problem decomposed end to end. Shipped iteratively with each stage independently demoable: two agents first, then third agent, then circuit breaker, then live dashboard.

**SDE**: Distributed message passing between agents via Redis pub/sub. Circuit breaker pattern with configurable thresholds and recovery probes. Async SQLAlchemy audit log capturing every agent decision. Prometheus histograms for p50/p95/p99 per agent. Kubernetes HPA scaling on CPU and memory.
