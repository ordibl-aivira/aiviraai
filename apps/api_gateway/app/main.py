"""API Gateway — tenant-facing entry point for Workforce OS.

All external requests flow through the gateway, which handles:
- routing to internal services
- request validation
- rate limiting (future)
- authentication verification (future)

Endpoints
---------
GET   /health
POST  /v1/tasks/execute
POST  /v1/agents
GET   /v1/agents
POST  /v1/workflows
GET   /v1/workflows
POST  /v1/workflows/{workflow_id}/execute
POST  /v1/memory/retrieve
POST  /v1/voice/call
GET   /v1/organizations/{org_id}
"""

from fastapi import FastAPI, HTTPException
import httpx

from packages.shared.models import (
    AgentCreate,
    MemoryRetrievalRequest,
    TaskRequest,
    VoiceCallRequest,
    WorkflowCreate,
)
from packages.shared.settings import settings

app = FastAPI(
    title="Ordibl Workforce OS API Gateway",
    version="0.1.0",
    description="Unified entry point for the Aivira Workforce OS platform.",
)

TIMEOUT = httpx.Timeout(60.0, connect=10.0)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "api-gateway"}


# ── Tasks ───────────────────────────────────────────────────────

@app.post("/v1/tasks/execute")
async def execute_task(request: TaskRequest) -> dict:
    """Execute a task through the agent runtime."""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            response = await client.post(
                f"{settings.agent_runtime_url}/internal/agent-runtime/tasks/execute",
                json=request.model_dump(),
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"Agent runtime unavailable: {exc}")


# ── Agents ──────────────────────────────────────────────────────

@app.post("/v1/agents")
async def create_agent(request: AgentCreate) -> dict:
    """Register a new AI agent for an organization."""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            response = await client.post(
                f"{settings.organization_service_url}/internal/agents",
                json=request.model_dump(),
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"Organization service unavailable: {exc}")


@app.get("/v1/agents")
async def list_agents(organization_id: str) -> dict:
    """List all agents for an organization."""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            response = await client.get(
                f"{settings.organization_service_url}/internal/agents",
                params={"organization_id": organization_id},
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"Organization service unavailable: {exc}")


# ── Workflows ───────────────────────────────────────────────────

@app.post("/v1/workflows")
async def create_workflow(request: WorkflowCreate) -> dict:
    """Create a new multi-agent workflow."""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            response = await client.post(
                f"{settings.workflow_engine_url}/internal/workflows",
                json=request.model_dump(),
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"Workflow engine unavailable: {exc}")


@app.get("/v1/workflows")
async def list_workflows(organization_id: str) -> dict:
    """List workflows for an organization."""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            response = await client.get(
                f"{settings.workflow_engine_url}/internal/workflows",
                params={"organization_id": organization_id},
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"Workflow engine unavailable: {exc}")


@app.post("/v1/workflows/{workflow_id}/execute")
async def execute_workflow(workflow_id: str) -> dict:
    """Start execution of a workflow."""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            response = await client.post(
                f"{settings.workflow_engine_url}/internal/workflows/{workflow_id}/execute",
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"Workflow engine unavailable: {exc}")


# ── Memory ──────────────────────────────────────────────────────

@app.post("/v1/memory/retrieve")
async def retrieve_memory(request: MemoryRetrievalRequest) -> dict:
    """Query the memory service for relevant context."""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            response = await client.post(
                f"{settings.memory_service_url}/internal/memory/retrieve",
                json=request.model_dump(),
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"Memory service unavailable: {exc}")


# ── Voice (Ordibl) ──────────────────────────────────────────────

@app.post("/v1/voice/call")
async def initiate_voice_call(request: VoiceCallRequest) -> dict:
    """Initiate an outbound voice call via Ordibl."""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            response = await client.post(
                f"{settings.ordibl_adapter_url}/internal/voice/call",
                json=request.model_dump(),
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"Ordibl adapter unavailable: {exc}")


# ── Organizations ───────────────────────────────────────────────

@app.get("/v1/organizations/{org_id}")
async def get_organization(org_id: str) -> dict:
    """Retrieve organization details."""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            response = await client.get(
                f"{settings.organization_service_url}/internal/organizations/{org_id}",
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"Organization service unavailable: {exc}")
