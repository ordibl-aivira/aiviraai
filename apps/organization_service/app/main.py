"""Organization Service — tenant, agent, and customer management.

Endpoints
---------
GET   /health

POST  /internal/organizations
GET   /internal/organizations
GET   /internal/organizations/{org_id}
PATCH /internal/organizations/{org_id}

POST  /internal/agents
GET   /internal/agents
GET   /internal/agents/{agent_id}
PATCH /internal/agents/{agent_id}/status

POST  /internal/customers
GET   /internal/customers
GET   /internal/customers/{customer_id}
PATCH /internal/customers/{customer_id}
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict
from uuid import uuid4

from fastapi import FastAPI, HTTPException

from packages.shared.models import (
    AgentCreate,
    AgentStatus,
    CustomerCreate,
    CustomerUpdate,
    OrganizationCreate,
)

app = FastAPI(title="Organization Service", version="0.2.0")

# In-memory stores (replaced by Postgres in production)
_organizations: Dict[str, dict] = {}
_agents: Dict[str, dict] = {}
_customers: Dict[str, dict] = {}


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "organization-service"}


# ── Organizations ───────────────────────────────────────────────

@app.post("/internal/organizations")
def create_organization(request: OrganizationCreate) -> dict:
    """Create a new organization (tenant)."""
    org_id = f"org_{uuid4().hex[:12]}"
    now = datetime.utcnow()
    org = {
        "id": org_id,
        "name": request.name,
        "slug": request.slug,
        "industry": request.industry,
        "timezone": request.timezone,
        "settings": request.settings,
        "plan": "starter",
        "status": "active",
        "is_active": True,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }
    _organizations[org_id] = org
    return org


@app.get("/internal/organizations")
def list_organizations() -> dict:
    """List all organizations."""
    results = list(_organizations.values())
    return {"organizations": results, "total": len(results)}


@app.get("/internal/organizations/{org_id}")
def get_organization(org_id: str) -> dict:
    """Retrieve organization details."""
    org = _organizations.get(org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org


@app.patch("/internal/organizations/{org_id}")
def update_organization(org_id: str, payload: dict) -> dict:
    """Update organization fields."""
    org = _organizations.get(org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    allowed = {"name", "slug", "industry", "timezone", "settings", "plan", "status"}
    for key, value in payload.items():
        if key in allowed:
            org[key] = value
    org["updated_at"] = datetime.utcnow().isoformat()
    return org


# ── Agents ──────────────────────────────────────────────────────

@app.post("/internal/agents")
def create_agent(request: AgentCreate) -> dict:
    """Deploy a new AI agent for an organization."""
    agent_id = f"agt_{uuid4().hex[:12]}"
    now = datetime.utcnow()
    agent = {
        "id": agent_id,
        "organization_id": request.organization_id,
        "name": request.name,
        "role": request.role,
        "description": request.description,
        "status": AgentStatus.IDLE.value,
        "capabilities": request.capabilities,
        "tools": request.tools,
        "policies": request.policies,
        "max_steps": request.max_steps,
        "max_tokens_per_step": request.max_tokens_per_step,
        "timeout_seconds": request.timeout_seconds,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }
    _agents[agent_id] = agent
    return agent


@app.get("/internal/agents")
def list_agents(organization_id: str) -> dict:
    """List all agents for an organization."""
    results = [
        a for a in _agents.values()
        if a["organization_id"] == organization_id
    ]
    return {"agents": results, "total": len(results)}


@app.get("/internal/agents/{agent_id}")
def get_agent(agent_id: str) -> dict:
    """Retrieve a single agent."""
    agent = _agents.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@app.patch("/internal/agents/{agent_id}/status")
def update_agent_status(agent_id: str, status: str) -> dict:
    """Update an agent's operational status."""
    agent = _agents.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    try:
        AgentStatus(status)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    agent["status"] = status
    agent["updated_at"] = datetime.utcnow().isoformat()
    return agent


# ── Customers ───────────────────────────────────────────────────

@app.post("/internal/customers")
def create_customer(request: CustomerCreate) -> dict:
    """Register a new customer for an organization."""
    customer_id = f"cust_{uuid4().hex[:12]}"
    now = datetime.utcnow()
    customer = {
        "id": customer_id,
        "organization_id": request.organization_id,
        "external_ref": request.external_ref,
        "first_name": request.first_name,
        "last_name": request.last_name,
        "email": request.email,
        "phone": request.phone,
        "preferences": request.preferences,
        "metadata": request.metadata,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }
    _customers[customer_id] = customer
    return customer


@app.get("/internal/customers")
def list_customers(organization_id: str) -> dict:
    """List all customers for an organization."""
    results = [
        c for c in _customers.values()
        if c["organization_id"] == organization_id
    ]
    return {"customers": results, "total": len(results)}


@app.get("/internal/customers/{customer_id}")
def get_customer(customer_id: str) -> dict:
    """Retrieve a single customer."""
    customer = _customers.get(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@app.patch("/internal/customers/{customer_id}")
def update_customer(customer_id: str, request: CustomerUpdate) -> dict:
    """Update customer fields."""
    customer = _customers.get(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    update_data = request.model_dump(exclude_none=True)
    for key, value in update_data.items():
        customer[key] = value
    customer["updated_at"] = datetime.utcnow().isoformat()
    return customer
