"""Agent Runtime Service — executes AI agent reasoning loops.

Endpoints
---------
GET  /health
POST /internal/agent-runtime/tasks/execute
GET  /internal/agent-runtime/tools
"""

from uuid import uuid4

from fastapi import FastAPI

from packages.shared.models import TaskRequest, TaskResponse, TaskStatus

from .runtime import run_agent

app = FastAPI(title="Agent Runtime", version="0.1.0")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "agent-runtime"}


@app.get("/internal/agent-runtime/tools")
def list_tools() -> dict:
    """Return the tool registry available to agents."""
    from .runtime import TOOL_REGISTRY

    return {"tools": TOOL_REGISTRY}


@app.post("/internal/agent-runtime/tasks/execute", response_model=TaskResponse)
def execute_task(request: TaskRequest) -> TaskResponse:
    """Run the full agent reasoning loop for a single task."""
    task_id = f"tsk_{uuid4().hex[:12]}"
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
    return TaskResponse(
        task_id=task_id,
        status=TaskStatus.COMPLETED if state.get("completed") else TaskStatus.FAILED,
        result=state.get("result", {}),
        plan=state.get("plan", []),
        steps_executed=state.get("steps_executed", 0),
    )
