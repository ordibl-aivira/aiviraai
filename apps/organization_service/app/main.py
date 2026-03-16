"""Organization Service — tenant and agent management for Workforce OS.

Endpoints
---------
GET   /health
POST  /internal/organizations
GET   /internal/organizations/{org_id}
POST  /internal/agents
GET   /internal/agents
GET   /internal/agents/{agent_id}
PATCH /internal/agents/{agent_id}/status
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict
from uuid import uuid4

from fastapi import FastAPI, HTTPException

from packages.shared.models import AgentCreate, AgentStatus, OrganizationCreate

app = FastAPI(title="Organization Service", version="0.1.0")

# In-memory stores (replaced by Postgres in production)
_organizations: Dict[str, dict] = {}
_agents: Dict[str, dict] = {}


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
        "is_active": True,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }
    _organizations[org_id] = org
    return org


@app.get("/internal/organizations/{org_id}")
def get_organization(org_id: str) -> dict:
    """Retrieve organization details."""
    org = _organizations.get(org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
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
