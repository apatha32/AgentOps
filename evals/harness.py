"""Evaluation harness for AgentOps.

Runs all 20 sample tasks through the pipeline and measures:
  - Category accuracy (did triage assign the right category?)
  - Agent routing accuracy (did triage route to the right agent?)
  - Resolution confidence distribution
  - Escalation rate
  - Per-task latency

Usage:
    python -m evals.harness [--limit N] [--output results.json]
"""
from __future__ import annotations

import asyncio
import json
import time
import uuid
import argparse
from pathlib import Path
from typing import Any

from db.postgres import AsyncSessionLocal, create_tables
from orchestration.graph import run_pipeline


SAMPLE_TASKS_PATH = Path(__file__).parent / "sample_tasks.json"


async def run_eval(limit: int | None = None) -> dict[str, Any]:
    await create_tables()

    tasks = json.loads(SAMPLE_TASKS_PATH.read_text())
    if limit:
        tasks = tasks[:limit]

    results = []
    category_correct = 0
    agent_correct = 0
    total_latency_ms = 0.0

    print(f"\nRunning eval on {len(tasks)} tasks...\n{'─' * 60}")

    for i, task in enumerate(tasks, 1):
        task_id = str(uuid.uuid4())
        t0 = time.perf_counter()

        try:
            async with AsyncSessionLocal() as session:
                final_state = await run_pipeline(
                    session,
                    task_id,
                    task["title"],
                    task["description"],
                    service="eval",
                )
        except Exception as exc:
            print(f"[{i:02d}] FAILED — {task['title'][:60]}: {exc}")
            results.append(
                {
                    "task": task["title"],
                    "error": str(exc),
                    "category_match": False,
                    "agent_match": False,
                }
            )
            continue

        latency_ms = (time.perf_counter() - t0) * 1000
        total_latency_ms += latency_ms

        predicted_category = final_state.get("category", "")
        predicted_agent = final_state.get("next_agent", "")
        cat_match = predicted_category == task["expected_category"]
        agent_match = predicted_agent == task["expected_agent"]

        if cat_match:
            category_correct += 1
        if agent_match:
            agent_correct += 1

        result = {
            "task": task["title"],
            "expected_category": task["expected_category"],
            "predicted_category": predicted_category,
            "category_match": cat_match,
            "expected_agent": task["expected_agent"],
            "predicted_agent": predicted_agent,
            "agent_match": agent_match,
            "confidence": final_state.get("confidence"),
            "escalate": final_state.get("escalate"),
            "latency_ms": round(latency_ms, 1),
        }
        results.append(result)

        mark = "✓" if cat_match and agent_match else "✗"
        print(
            f"[{i:02d}] {mark} cat={predicted_category:8s} agent={predicted_agent:15s} "
            f"lat={latency_ms:.0f}ms — {task['title'][:50]}"
        )

    n = len(tasks)
    summary = {
        "total": n,
        "category_accuracy": round(category_correct / n, 3),
        "agent_routing_accuracy": round(agent_correct / n, 3),
        "avg_latency_ms": round(total_latency_ms / n, 1) if n else 0,
        "results": results,
    }

    print(f"\n{'─' * 60}")
    print(f"Category accuracy:      {summary['category_accuracy']:.1%}")
    print(f"Agent routing accuracy: {summary['agent_routing_accuracy']:.1%}")
    print(f"Avg latency:            {summary['avg_latency_ms']} ms")

    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="AgentOps eval harness")
    parser.add_argument("--limit", type=int, default=None, help="Evaluate only first N tasks")
    parser.add_argument("--output", type=str, default=None, help="Write JSON results to file")
    args = parser.parse_args()

    summary = asyncio.run(run_eval(limit=args.limit))

    if args.output:
        Path(args.output).write_text(json.dumps(summary, indent=2))
        print(f"\nResults written to {args.output}")


if __name__ == "__main__":
    main()
