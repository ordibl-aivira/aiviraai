"""API Gateway — tenant-facing entry point for Workforce OS.

All external requests flow through the gateway, which handles:
- routing to internal services
- request validation
- rate limiting (future)
- authentication verification (future)

Dependency rules (from Engineering Blueprint):
- Gateway never talks directly to databases
- All tool execution goes through Integration Service
- Ordibl is treated as external communication infrastructure

Endpoints
---------
GET   /health

POST  /v1/auth/login
POST  /v1/auth/register
GET   /v1/me

GET   /v1/organizations/{org_id}
PATCH /v1/organizations/{org_id}

POST  /v1/agents
GET   /v1/agents
GET   /v1/agents/{agent_id}
POST  /v1/agents/{agent_id}/activate
POST  /v1/agents/{agent_id}/deactivate

POST  /v1/tasks/execute
GET   /v1/tasks
GET   /v1/tasks/{task_id}
POST  /v1/tasks/{task_id}/retry

POST  /v1/workflows
GET   /v1/workflows
GET   /v1/workflows/{workflow_id}
POST  /v1/workflows/{workflow_id}/execute

POST  /v1/memory/retrieve

POST  /v1/voice/call

GET   /v1/customers
POST  /v1/customers
GET   /v1/customers/{customer_id}
PATCH /v1/customers/{customer_id}

POST  /v1/approvals/{approval_id}/decision
GET   /v1/approvals
"""

from fastapi import FastAPI, HTTPException
import httpx

from packages.shared.models import (
    AgentCreate,
    ApprovalDecision,
    CustomerCreate,
    CustomerUpdate,
    LoginRequest,
    MemoryRetrievalRequest,
    TaskRequest,
    UserCreate,
    VoiceCallRequest,
    WorkflowCreate,
)
from packages.shared.settings import settings

app = FastAPI(
    title="Ordibl Workforce OS API Gateway",
    version="0.2.0",
    description="Unified entry point for the Aivira Workforce OS platform.",
)

TIMEOUT = httpx.Timeout(60.0, connect=10.0)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "api-gateway"}


# ── Auth ───────────────────────────────────────────────────────

@app.post("/v1/auth/login")
async def login(request: LoginRequest) -> dict:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            response = await client.post(
                f"{settings.auth_service_url}/internal/auth/login",
                json=request.model_dump(),
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(
                status_code=exc.response.status_code, detail=exc.response.text
            )
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=502, detail=f"Auth service unavailable: {exc}"
            )


@app.post("/v1/auth/register")
async def register(request: UserCreate) -> dict:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            response = await client.post(
                f"{settings.auth_service_url}/internal/auth/register",
                json=request.model_dump(),
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(
                status_code=exc.response.status_code, detail=exc.response.text
            )
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=502, detail=f"Auth service unavailable: {exc}"
            )


@app.get("/v1/me")
async def get_current_user(authorization: str = "") -> dict:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            response = await client.get(
                f"{settings.auth_service_url}/internal/auth/verify",
                headers={"Authorization": authorization},
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(
                status_code=exc.response.status_code, detail=exc.response.text
            )
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=502, detail=f"Auth service unavailable: {exc}"
            )


# ── Tasks ───────────────────────────────────────────────────────

@app.post("/v1/tasks/execute")
async def execute_task(request: TaskRequest) -> dict:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            response = await client.post(
                f"{settings.agent_runtime_url}/internal/agent-runtime/tasks/execute",
                json=request.model_dump(),
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=502, detail=f"Agent runtime unavailable: {exc}"
            )


@app.get("/v1/tasks")
async def list_tasks(organization_id: str) -> dict:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            response = await client.get(
                f"{settings.agent_runtime_url}/internal/agent-runtime/tasks",
                params={"organization_id": organization_id},
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=502, detail=f"Agent runtime unavailable: {exc}"
            )


@app.get("/v1/tasks/{task_id}")
async def get_task(task_id: str) -> dict:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            response = await client.get(
                f"{settings.agent_runtime_url}/internal/agent-runtime/tasks/{task_id}/state",
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=502, detail=f"Agent runtime unavailable: {exc}"
            )


@app.post("/v1/tasks/{task_id}/retry")
async def retry_task(task_id: str) -> dict:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            response = await client.post(
                f"{settings.agent_runtime_url}/internal/agent-runtime/tasks/{task_id}/resume",
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=502, detail=f"Agent runtime unavailable: {exc}"
            )


# ── Agents ──────────────────────────────────────────────────────

@app.post("/v1/agents")
async def create_agent(request: AgentCreate) -> dict:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            response = await client.post(
                f"{settings.organization_service_url}/internal/agents",
                json=request.model_dump(),
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Organization service unavailable: {exc}",
            )


@app.get("/v1/agents")
async def list_agents(organization_id: str) -> dict:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            response = await client.get(
                f"{settings.organization_service_url}/internal/agents",
                params={"organization_id": organization_id},
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Organization service unavailable: {exc}",
            )


@app.get("/v1/agents/{agent_id}")
async def get_agent(agent_id: str) -> dict:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            response = await client.get(
                f"{settings.organization_service_url}/internal/agents/{agent_id}",
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Organization service unavailable: {exc}",
            )


@app.post("/v1/agents/{agent_id}/activate")
async def activate_agent(agent_id: str) -> dict:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            response = await client.patch(
                f"{settings.organization_service_url}/internal/agents/{agent_id}/status",
                params={"status": "idle"},
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Organization service unavailable: {exc}",
            )


@app.post("/v1/agents/{agent_id}/deactivate")
async def deactivate_agent(agent_id: str) -> dict:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            response = await client.patch(
                f"{settings.organization_service_url}/internal/agents/{agent_id}/status",
                params={"status": "disabled"},
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Organization service unavailable: {exc}",
            )


# ── Workflows ───────────────────────────────────────────────────

@app.post("/v1/workflows")
async def create_workflow(request: WorkflowCreate) -> dict:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            response = await client.post(
                f"{settings.workflow_engine_url}/internal/workflows",
                json=request.model_dump(),
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=502, detail=f"Workflow engine unavailable: {exc}"
            )


@app.get("/v1/workflows")
async def list_workflows(organization_id: str) -> dict:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            response = await client.get(
                f"{settings.workflow_engine_url}/internal/workflows",
                params={"organization_id": organization_id},
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=502, detail=f"Workflow engine unavailable: {exc}"
            )


@app.get("/v1/workflows/{workflow_id}")
async def get_workflow(workflow_id: str) -> dict:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            response = await client.get(
                f"{settings.workflow_engine_url}/internal/workflows/{workflow_id}",
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=502, detail=f"Workflow engine unavailable: {exc}"
            )


@app.post("/v1/workflows/{workflow_id}/execute")
async def execute_workflow(workflow_id: str) -> dict:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            response = await client.post(
                f"{settings.workflow_engine_url}/internal/workflows/{workflow_id}/execute",
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=502, detail=f"Workflow engine unavailable: {exc}"
            )


# ── Memory ──────────────────────────────────────────────────────

@app.post("/v1/memory/retrieve")
async def retrieve_memory(request: MemoryRetrievalRequest) -> dict:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            response = await client.post(
                f"{settings.memory_service_url}/internal/memory/retrieve",
                json=request.model_dump(),
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=502, detail=f"Memory service unavailable: {exc}"
            )


# ── Voice (Ordibl) ──────────────────────────────────────────────

@app.post("/v1/voice/call")
async def initiate_voice_call(request: VoiceCallRequest) -> dict:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            response = await client.post(
                f"{settings.ordibl_adapter_url}/internal/voice/call",
                json=request.model_dump(),
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=502, detail=f"Ordibl adapter unavailable: {exc}"
            )


# ── Organizations ───────────────────────────────────────────────

@app.get("/v1/organizations/{org_id}")
async def get_organization(org_id: str) -> dict:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            response = await client.get(
                f"{settings.organization_service_url}/internal/organizations/{org_id}",
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Organization service unavailable: {exc}",
            )


@app.patch("/v1/organizations/{org_id}")
async def update_organization(org_id: str, payload: dict) -> dict:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            response = await client.patch(
                f"{settings.organization_service_url}/internal/organizations/{org_id}",
                json=payload,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Organization service unavailable: {exc}",
            )


# ── Customers ───────────────────────────────────────────────────

@app.post("/v1/customers")
async def create_customer(request: CustomerCreate) -> dict:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            response = await client.post(
                f"{settings.organization_service_url}/internal/customers",
                json=request.model_dump(),
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Organization service unavailable: {exc}",
            )


@app.get("/v1/customers")
async def list_customers(organization_id: str) -> dict:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            response = await client.get(
                f"{settings.organization_service_url}/internal/customers",
                params={"organization_id": organization_id},
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Organization service unavailable: {exc}",
            )


@app.get("/v1/customers/{customer_id}")
async def get_customer(customer_id: str) -> dict:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            response = await client.get(
                f"{settings.organization_service_url}/internal/customers/{customer_id}",
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Organization service unavailable: {exc}",
            )


@app.patch("/v1/customers/{customer_id}")
async def update_customer(customer_id: str, request: CustomerUpdate) -> dict:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            response = await client.patch(
                f"{settings.organization_service_url}/internal/customers/{customer_id}",
                json=request.model_dump(exclude_none=True),
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Organization service unavailable: {exc}",
            )


# ── Approvals ───────────────────────────────────────────────────

@app.get("/v1/approvals")
async def list_approvals(organization_id: str) -> dict:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            response = await client.get(
                f"{settings.workflow_engine_url}/internal/approvals",
                params={"organization_id": organization_id},
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=502, detail=f"Workflow engine unavailable: {exc}"
            )


@app.post("/v1/approvals/{approval_id}/decision")
async def decide_approval(approval_id: str, decision: ApprovalDecision) -> dict:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            response = await client.post(
                f"{settings.workflow_engine_url}/internal/approvals/{approval_id}/decision",
                json=decision.model_dump(),
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=502, detail=f"Workflow engine unavailable: {exc}"
            )
