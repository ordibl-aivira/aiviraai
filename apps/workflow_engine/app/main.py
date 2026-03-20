"""Workflow Engine — DAG-based multi-agent orchestration.

Manages workflow definitions, executions, and approval gates.
Each workflow is a directed acyclic graph (DAG) of steps, where
each step is assigned to a specialist agent role.  The engine
resolves dependencies, dispatches tasks, and tracks completion.

Endpoints
---------
GET   /health

POST  /internal/workflows
GET   /internal/workflows
GET   /internal/workflows/{workflow_id}
POST  /internal/workflows/{workflow_id}/execute
POST  /internal/workflows/{workflow_id}/advance
POST  /internal/workflows/{workflow_id}/cancel
GET   /internal/workflows/{workflow_id}/tasks
GET   /internal/workflows/executions/{execution_id}

GET   /internal/approvals
POST  /internal/approvals
POST  /internal/approvals/{approval_id}/decision
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List
from uuid import uuid4

from fastapi import FastAPI, HTTPException
import httpx

from packages.shared.models import (
    ApprovalCreate,
    ApprovalDecision,
    ApprovalStatus,
    TaskRequest,
    WorkflowCreate,
    WorkflowStatus,
)
from packages.shared.settings import settings

app = FastAPI(title="Workflow Engine", version="0.2.0")

# ── In-memory stores (replaced by Postgres in production) ───────
_workflows: Dict[str, dict] = {}
_executions: Dict[str, dict] = {}
_approvals: Dict[str, dict] = {}


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
        "steps": [s.model_dump(mode="json") for s in request.steps],
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


@app.post("/internal/workflows/{workflow_id}/advance")
async def advance_workflow(workflow_id: str) -> dict:
    """Advance a paused or waiting workflow to the next step."""
    wf = _workflows.get(workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")

    # Find the corresponding execution
    execution = None
    for ex in _executions.values():
        if ex["workflow_id"] == workflow_id:
            execution = ex
            break

    if not execution:
        raise HTTPException(status_code=404, detail="No execution found for workflow")

    if execution["status"] != WorkflowStatus.PAUSED.value:
        raise HTTPException(
            status_code=400,
            detail=f"Workflow execution in status '{execution['status']}' cannot be advanced",
        )

    execution["status"] = WorkflowStatus.RUNNING.value

    # Mark the approval-gated step as completed so the DAG walker
    # doesn't re-encounter it and pause again.
    paused_step_id = execution.get("current_step")
    if paused_step_id:
        step_results = execution.get("step_results", {})
        if paused_step_id not in step_results:
            step_results[paused_step_id] = {
                "status": "approved",
                "approved_at": datetime.utcnow().isoformat(),
            }
            execution["step_results"] = step_results

    # Re-execute remaining DAG steps from where we left off
    await _walk_dag(wf, execution)
    return execution


@app.post("/internal/workflows/{workflow_id}/cancel")
def cancel_workflow(workflow_id: str) -> dict:
    """Cancel a running or paused workflow."""
    wf = _workflows.get(workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")

    wf["status"] = WorkflowStatus.FAILED.value
    wf["updated_at"] = datetime.utcnow().isoformat()

    # Also cancel any active executions
    for ex in _executions.values():
        if ex["workflow_id"] == workflow_id and ex["status"] in (
            WorkflowStatus.RUNNING.value,
            WorkflowStatus.PAUSED.value,
        ):
            ex["status"] = WorkflowStatus.FAILED.value
            ex["completed_at"] = datetime.utcnow().isoformat()

    return {"workflow_id": workflow_id, "status": "cancelled"}


@app.get("/internal/workflows/{workflow_id}/tasks")
def get_workflow_tasks(workflow_id: str) -> dict:
    """List all tasks created during workflow execution."""
    execution = None
    for ex in _executions.values():
        if ex["workflow_id"] == workflow_id:
            execution = ex
            break

    if not execution:
        return {"workflow_id": workflow_id, "tasks": [], "total": 0}

    step_results = execution.get("step_results", {})
    tasks = [
        {"step_id": step_id, "result": result}
        for step_id, result in step_results.items()
    ]
    return {"workflow_id": workflow_id, "tasks": tasks, "total": len(tasks)}


# ── Workflow Execution ──────────────────────────────────────────

def _resolve_ready_steps(steps: List[dict], completed: set, failed: set | None = None) -> List[dict]:
    """Find steps whose dependencies are all satisfied and none have failed."""
    failed = failed or set()
    ready = []
    for step in steps:
        deps = set(step.get("depends_on", []))
        if (
            step["step_id"] not in completed
            and step["step_id"] not in failed
            and deps.issubset(completed)
            and not deps.intersection(failed)
        ):
            ready.append(step)
    return ready


async def _walk_dag(wf: dict, execution: dict) -> None:
    """Walk the DAG from the current execution state, dispatching ready steps.

    This helper is shared between ``execute_workflow`` (fresh start) and
    ``advance_workflow`` (resume after approval).
    """
    steps = wf["steps"]
    step_results: Dict[str, dict] = execution.get("step_results", {})
    workflow_id = wf["id"]

    # Derive completed / failed sets from existing step_results
    completed_steps: set = set()
    failed_steps: set = set()
    for step_id, result in step_results.items():
        if result.get("status") == "failed":
            failed_steps.add(step_id)
        else:
            completed_steps.add(step_id)

    while True:
        ready = _resolve_ready_steps(steps, completed_steps, failed_steps)
        if not ready:
            break

        for step in ready:
            execution["current_step"] = step["step_id"]

            # Check if step requires approval
            if step.get("requires_approval", False):
                approval_id = f"apr_{uuid4().hex[:12]}"
                now = datetime.utcnow()
                _approvals[approval_id] = {
                    "id": approval_id,
                    "organization_id": wf["organization_id"],
                    "task_id": f"wf_step_{step['step_id']}",
                    "requested_by_agent_id": f"agt_{step['assigned_agent_role']}_001",
                    "approver_user_id": None,
                    "status": ApprovalStatus.PENDING.value,
                    "reason": f"Approval required for workflow step: {step['name']}",
                    "decision_note": None,
                    "created_at": now.isoformat(),
                    "decided_at": None,
                }
                # Pause the workflow — it will be advanced after approval
                execution["status"] = WorkflowStatus.PAUSED.value
                execution["step_results"] = step_results
                _workflows[workflow_id]["status"] = WorkflowStatus.PAUSED.value
                return

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
                        json=task_payload.model_dump(mode="json"),
                    )
                    resp.raise_for_status()
                    result = resp.json()
            except httpx.HTTPError:
                result = {"status": "failed", "error": "Agent runtime unavailable"}

            step_results[step["step_id"]] = result
            if result.get("status") == "failed":
                failed_steps.add(step["step_id"])
            else:
                completed_steps.add(step["step_id"])

    has_failures = len(failed_steps) > 0
    if has_failures:
        execution["status"] = WorkflowStatus.FAILED.value
    elif len(completed_steps) == len(steps):
        execution["status"] = WorkflowStatus.COMPLETED.value
    else:
        execution["status"] = WorkflowStatus.FAILED.value
    execution["step_results"] = step_results
    if execution["status"] == WorkflowStatus.COMPLETED.value:
        execution["completed_at"] = datetime.utcnow().isoformat()

    _workflows[workflow_id]["status"] = execution["status"]


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
    _executions[exec_id] = execution

    await _walk_dag(wf, execution)
    return execution


@app.get("/internal/workflows/executions/{execution_id}")
def get_execution(execution_id: str) -> dict:
    """Retrieve the status of a workflow execution."""
    ex = _executions.get(execution_id)
    if not ex:
        raise HTTPException(status_code=404, detail="Execution not found")
    return ex


# ── Approvals ───────────────────────────────────────────────────

@app.get("/internal/approvals")
def list_approvals(organization_id: str = "") -> dict:
    """List all pending and resolved approvals."""
    if organization_id:
        results = [
            a for a in _approvals.values()
            if a["organization_id"] == organization_id
        ]
    else:
        results = list(_approvals.values())
    return {"approvals": results, "total": len(results)}


@app.post("/internal/approvals")
def create_approval(request: ApprovalCreate) -> dict:
    """Create a new approval request."""
    approval_id = f"apr_{uuid4().hex[:12]}"
    now = datetime.utcnow()
    approval = {
        "id": approval_id,
        "organization_id": request.organization_id,
        "task_id": request.task_id,
        "requested_by_agent_id": request.requested_by_agent_id,
        "approver_user_id": None,
        "status": ApprovalStatus.PENDING.value,
        "reason": request.reason,
        "decision_note": None,
        "created_at": now.isoformat(),
        "decided_at": None,
    }
    _approvals[approval_id] = approval
    return approval


@app.post("/internal/approvals/{approval_id}/decision")
def decide_approval(approval_id: str, decision: ApprovalDecision) -> dict:
    """Approve or reject an approval request."""
    approval = _approvals.get(approval_id)
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")

    if approval["status"] != ApprovalStatus.PENDING.value:
        raise HTTPException(
            status_code=400,
            detail=f"Approval already resolved: {approval['status']}",
        )

    approval["status"] = decision.status.value
    approval["approver_user_id"] = decision.approver_user_id
    approval["decision_note"] = decision.decision_note
    approval["decided_at"] = datetime.utcnow().isoformat()
    return approval
