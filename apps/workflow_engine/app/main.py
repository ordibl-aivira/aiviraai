"""Workflow Engine — DAG-based multi-agent orchestration.

Manages workflow definitions and executions.  Each workflow is a
directed acyclic graph (DAG) of steps, where each step is assigned
to a specialist agent role.  The engine resolves dependencies,
dispatches tasks, and tracks completion.

Endpoints
---------
GET   /health
POST  /internal/workflows
GET   /internal/workflows
GET   /internal/workflows/{workflow_id}
POST  /internal/workflows/{workflow_id}/execute
GET   /internal/workflows/executions/{execution_id}
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List
from uuid import uuid4

from fastapi import FastAPI, HTTPException
import httpx

from packages.shared.models import (
    TaskRequest,
    WorkflowCreate,
    WorkflowStatus,
)
from packages.shared.settings import settings

app = FastAPI(title="Workflow Engine", version="0.1.0")

# ── In-memory stores (replaced by Postgres in production) ───────
_workflows: Dict[str, dict] = {}
_executions: Dict[str, dict] = {}


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "workflow-engine"}


# ── Workflow CRUD ───────────────────────────────────────────────

@app.post("/internal/workflows")
def create_workflow(request: WorkflowCreate) -> dict:
    """Register a new multi-agent workflow definition."""
    wf_id = f"wf_{uuid4().hex[:12]}"
    now = datetime.utcnow()
    workflow = {
        "id": wf_id,
        "organization_id": request.organization_id,
        "name": request.name,
        "description": request.description,
        "trigger_event": request.trigger_event,
        "status": WorkflowStatus.PENDING.value,
        "steps": [s.model_dump() for s in request.steps],
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }
    _workflows[wf_id] = workflow
    return workflow


@app.get("/internal/workflows")
def list_workflows(organization_id: str) -> dict:
    """List all workflows for an organization."""
    results = [
        w for w in _workflows.values()
        if w["organization_id"] == organization_id
    ]
    return {"workflows": results, "total": len(results)}


@app.get("/internal/workflows/{workflow_id}")
def get_workflow(workflow_id: str) -> dict:
    """Retrieve a single workflow definition."""
    wf = _workflows.get(workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return wf


# ── Workflow Execution ──────────────────────────────────────────

def _resolve_ready_steps(steps: List[dict], completed: set) -> List[dict]:
    """Find steps whose dependencies are all satisfied."""
    ready = []
    for step in steps:
        deps = set(step.get("depends_on", []))
        if step["step_id"] not in completed and deps.issubset(completed):
            ready.append(step)
    return ready


@app.post("/internal/workflows/{workflow_id}/execute")
async def execute_workflow(workflow_id: str) -> dict:
    """Start executing a workflow — dispatches tasks to agents via the runtime."""
    wf = _workflows.get(workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")

    exec_id = f"wfx_{uuid4().hex[:12]}"
    now = datetime.utcnow()
    execution = {
        "execution_id": exec_id,
        "workflow_id": workflow_id,
        "status": WorkflowStatus.RUNNING.value,
        "current_step": None,
        "step_results": {},
        "started_at": now.isoformat(),
        "completed_at": None,
    }

    steps = wf["steps"]
    completed_steps: set = set()
    step_results: Dict[str, dict] = {}

    # Walk the DAG
    while True:
        ready = _resolve_ready_steps(steps, completed_steps)
        if not ready:
            break

        for step in ready:
            execution["current_step"] = step["step_id"]

            # Dispatch task to agent runtime
            task_payload = TaskRequest(
                organization_id=wf["organization_id"],
                agent_id=f"agt_{step['assigned_agent_role']}_001",
                task_type=f"{step['assigned_agent_role']}.workflow_step",
                goal=step["name"],
                input=step.get("input_schema", {}),
                constraints={},
                success_criteria=[],
            )

            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    resp = await client.post(
                        f"{settings.agent_runtime_url}/internal/agent-runtime/tasks/execute",
                        json=task_payload.model_dump(),
                    )
                    resp.raise_for_status()
                    result = resp.json()
            except httpx.HTTPError:
                result = {"status": "failed", "error": "Agent runtime unavailable"}

            step_results[step["step_id"]] = result
            completed_steps.add(step["step_id"])

    all_done = len(completed_steps) == len(steps)
    execution["status"] = WorkflowStatus.COMPLETED.value if all_done else WorkflowStatus.FAILED.value
    execution["step_results"] = step_results
    if all_done:
        execution["completed_at"] = datetime.utcnow().isoformat()

    _executions[exec_id] = execution
    _workflows[workflow_id]["status"] = execution["status"]
    return execution


@app.get("/internal/workflows/executions/{execution_id}")
def get_execution(execution_id: str) -> dict:
    """Retrieve the status of a workflow execution."""
    ex = _executions.get(execution_id)
    if not ex:
        raise HTTPException(status_code=404, detail="Execution not found")
    return ex
