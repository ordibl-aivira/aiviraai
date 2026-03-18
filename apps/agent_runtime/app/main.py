"""Agent Runtime Service — executes AI agent reasoning loops.

Endpoints
---------
GET   /health
POST  /internal/agent-runtime/tasks/execute
GET   /internal/agent-runtime/tasks
GET   /internal/agent-runtime/tasks/{task_id}/state
POST  /internal/agent-runtime/tasks/{task_id}/resume
GET   /internal/agent-runtime/tools
POST  /internal/agent-runtime/agents/{agent_id}/simulate
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict
from uuid import uuid4

from fastapi import FastAPI, HTTPException

from packages.shared.models import TaskRequest, TaskResponse, TaskStatus

from .runtime import run_agent

app = FastAPI(title="Agent Runtime", version="0.2.0")

# In-memory task store for state retrieval / resume
_tasks: Dict[str, dict] = {}


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "agent-runtime"}


@app.get("/internal/agent-runtime/tools")
def list_tools() -> dict:
    """Return the tool registry available to agents."""
    from .runtime import TOOL_REGISTRY

    return {"tools": TOOL_REGISTRY}


@app.get("/internal/agent-runtime/tasks")
def list_tasks(organization_id: str = "") -> dict:
    """List tasks, optionally filtered by organization."""
    if organization_id:
        results = [
            t for t in _tasks.values()
            if t.get("organization_id") == organization_id
        ]
    else:
        results = list(_tasks.values())
    return {"tasks": results, "total": len(results)}


@app.get("/internal/agent-runtime/tasks/{task_id}/state")
def get_task_state(task_id: str) -> dict:
    """Retrieve full state of a task including plan and step results."""
    task = _tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.post("/internal/agent-runtime/tasks/execute", response_model=TaskResponse)
def execute_task(request: TaskRequest) -> TaskResponse:
    """Run the full agent reasoning loop for a single task."""
    task_id = f"tsk_{uuid4().hex[:12]}"
    now = datetime.utcnow()

    state = run_agent(
        {
            "task_id": task_id,
            "organization_id": request.organization_id,
            "agent_id": request.agent_id,
            "task_type": request.task_type,
            "goal": request.goal,
            "input": request.input,
            "constraints": request.constraints,
            "success_criteria": request.success_criteria,
        }
    )

    completed = state.get("completed", False)
    is_escalated = state.get("evaluation", {}).get("reason") == "awaiting_human_approval"
    if completed:
        status = TaskStatus.COMPLETED
    elif is_escalated:
        status = TaskStatus.ESCALATED
    else:
        status = TaskStatus.FAILED

    task_record = {
        "task_id": task_id,
        "organization_id": request.organization_id,
        "agent_id": request.agent_id,
        "task_type": request.task_type,
        "goal": request.goal,
        "input": request.input,
        "status": status.value,
        "result": state.get("result", {}),
        "plan": state.get("plan", []),
        "steps_executed": state.get("steps_executed", 0),
        "started_at": now.isoformat(),
        "completed_at": datetime.utcnow().isoformat() if completed else None,
    }
    _tasks[task_id] = task_record

    return TaskResponse(
        task_id=task_id,
        status=status,
        result=state.get("result", {}),
        plan=state.get("plan", []),
        steps_executed=state.get("steps_executed", 0),
    )


@app.post("/internal/agent-runtime/tasks/{task_id}/resume")
def resume_task(task_id: str) -> dict:
    """Resume a failed or blocked task from the last checkpoint."""
    task = _tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task["status"] not in (TaskStatus.FAILED.value, "blocked"):
        raise HTTPException(
            status_code=400,
            detail=f"Task in status '{task['status']}' cannot be resumed",
        )

    # Re-run the agent with the original parameters
    state = run_agent(
        {
            "task_id": task_id,
            "organization_id": task["organization_id"],
            "agent_id": task["agent_id"],
            "task_type": task["task_type"],
            "goal": task["goal"],
            "input": task.get("input", {}),
            "constraints": {},
            "success_criteria": [],
        }
    )

    completed = state.get("completed", False)
    is_escalated = state.get("evaluation", {}).get("reason") == "awaiting_human_approval"
    if completed:
        task["status"] = TaskStatus.COMPLETED.value
    elif is_escalated:
        task["status"] = TaskStatus.ESCALATED.value
    else:
        task["status"] = TaskStatus.FAILED.value
    task["result"] = state.get("result", {})
    task["plan"] = state.get("plan", [])
    task["steps_executed"] = state.get("steps_executed", 0)
    if completed:
        task["completed_at"] = datetime.utcnow().isoformat()

    return task


@app.post("/internal/agent-runtime/agents/{agent_id}/simulate")
def simulate_agent(agent_id: str, payload: dict) -> dict:
    """Test an agent with sample input without persisting results.

    Useful for validating agent configuration before deployment.
    """
    goal = payload.get("goal", "Simulate test task")
    task_type = payload.get("task_type", "simulation")
    sample_input = payload.get("input", {})

    state = run_agent(
        {
            "task_id": f"sim_{uuid4().hex[:8]}",
            "organization_id": payload.get("organization_id", "sim_org"),
            "agent_id": agent_id,
            "task_type": task_type,
            "goal": goal,
            "input": sample_input,
            "constraints": payload.get("constraints", {}),
            "success_criteria": payload.get("success_criteria", []),
        }
    )

    return {
        "agent_id": agent_id,
        "simulation": True,
        "completed": state.get("completed", False),
        "result": state.get("result", {}),
        "plan": state.get("plan", []),
        "steps_executed": state.get("steps_executed", 0),
    }
