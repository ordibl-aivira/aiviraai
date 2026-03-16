"""Analytics Service — metrics and observability for Workforce OS.

Endpoints
---------
GET   /health
POST  /internal/analytics/events          — ingest analytics event
GET   /internal/analytics/agents/{agent_id}/metrics  — agent performance
GET   /internal/analytics/organizations/{org_id}/summary — org dashboard
"""

from __future__ import annotations

from datetime import datetime
from typing import List
from uuid import uuid4

from fastapi import FastAPI

app = FastAPI(title="Analytics Service", version="0.1.0")

# In-memory event store
_events: List[dict] = []


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "analytics-service"}


@app.post("/internal/analytics/events")
def ingest_event(event: dict) -> dict:
    """Ingest a raw analytics event."""
    event_id = f"ae_{uuid4().hex[:12]}"
    record = {
        "id": event_id,
        "event_type": event.get("event_type", "unknown"),
        "organization_id": event.get("organization_id", ""),
        "agent_id": event.get("agent_id"),
        "task_id": event.get("task_id"),
        "data": event.get("data", {}),
        "created_at": datetime.utcnow().isoformat(),
    }
    _events.append(record)
    return {"status": "ingested", "id": event_id}


@app.get("/internal/analytics/agents/{agent_id}/metrics")
def agent_metrics(agent_id: str, organization_id: str = "") -> dict:
    """Return performance metrics for an agent."""
    agent_events = [
        e for e in _events if e.get("agent_id") == agent_id
    ]
    completed = [e for e in agent_events if e.get("event_type") == "task.completed"]
    failed = [e for e in agent_events if e.get("event_type") == "task.failed"]
    total = len(completed) + len(failed)

    return {
        "agent_id": agent_id,
        "organization_id": organization_id,
        "total_tasks": total,
        "completed_tasks": len(completed),
        "failed_tasks": len(failed),
        "success_rate": len(completed) / total if total > 0 else 0.0,
        "total_events": len(agent_events),
    }


@app.get("/internal/analytics/organizations/{org_id}/summary")
def organization_summary(org_id: str) -> dict:
    """Return a summary dashboard for an organization."""
    org_events = [e for e in _events if e.get("organization_id") == org_id]
    task_events = [e for e in org_events if e.get("event_type", "").startswith("task.")]
    voice_events = [e for e in org_events if e.get("event_type", "").startswith("voice.")]

    agent_ids = set(e.get("agent_id") for e in org_events if e.get("agent_id"))

    return {
        "organization_id": org_id,
        "total_events": len(org_events),
        "total_task_events": len(task_events),
        "total_voice_events": len(voice_events),
        "active_agents": len(agent_ids),
        "agent_ids": list(agent_ids),
    }
