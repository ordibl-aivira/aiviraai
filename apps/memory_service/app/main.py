"""Memory Service — 4-layer memory architecture for autonomous agents.

Layers
------
1. Working Memory   — short-lived session state (Redis)
2. Episodic Memory  — past task/event records (Postgres)
3. Semantic Memory  — generalised facts & knowledge (Postgres + Qdrant vectors)
4. Procedural Memory — reusable playbooks / SOPs (Postgres)

The service exposes a unified retrieval endpoint that assembles a
*context packet* by querying all relevant layers and ranking results.

Endpoints
---------
GET   /health

POST  /internal/memory/working           — upsert working memory
GET   /internal/memory/working/{session}  — get working memory
DELETE /internal/memory/working/{session} — clear working memory

POST  /internal/memory/episodes           — store episodic memory
GET   /internal/memory/episodes           — list episodes for agent

POST  /internal/memory/knowledge          — store semantic fact
GET   /internal/memory/knowledge          — search semantic facts

POST  /internal/memory/procedures         — store procedure
GET   /internal/memory/procedures         — list procedures

POST  /internal/memory/retrieve           — unified context retrieval
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List
from uuid import uuid4

from fastapi import FastAPI, HTTPException

from packages.shared.models import (
    EpisodicMemoryCreate,
    MemoryRetrievalRequest,
    ProceduralMemoryCreate,
    SemanticMemoryCreate,
    WorkingMemoryEntry,
)

app = FastAPI(title="Memory Service", version="0.1.0")

# ── In-memory stores (replaced by Redis / Postgres / Qdrant) ───
_working: Dict[str, dict] = {}
_episodes: List[dict] = []
_knowledge: List[dict] = []
_procedures: List[dict] = []


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "memory-service"}


# ── Working Memory (Redis in production) ────────────────────────

@app.post("/internal/memory/working")
def upsert_working_memory(entry: WorkingMemoryEntry) -> dict:
    """Store or update working memory for a session."""
    _working[entry.session_id] = entry.model_dump()
    return {"status": "stored", "session_id": entry.session_id}


@app.get("/internal/memory/working/{session_id}")
def get_working_memory(session_id: str) -> dict:
    """Retrieve working memory for a session."""
    data = _working.get(session_id)
    if not data:
        raise HTTPException(status_code=404, detail="Working memory not found")
    return data


@app.delete("/internal/memory/working/{session_id}")
def clear_working_memory(session_id: str) -> dict:
    """Clear working memory for a session (session ended)."""
    _working.pop(session_id, None)
    return {"status": "cleared", "session_id": session_id}


# ── Episodic Memory (Postgres in production) ────────────────────

@app.post("/internal/memory/episodes")
def store_episode(entry: EpisodicMemoryCreate) -> dict:
    """Store an episodic memory entry."""
    episode_id = f"ep_{uuid4().hex[:12]}"
    record = {
        "id": episode_id,
        **entry.model_dump(),
        "created_at": datetime.utcnow().isoformat(),
    }
    _episodes.append(record)
    return {"status": "stored", "id": episode_id}


@app.get("/internal/memory/episodes")
def list_episodes(
    agent_id: str,
    organization_id: str,
    limit: int = 20,
) -> dict:
    """List recent episodes for an agent."""
    results = [
        e for e in _episodes
        if e["agent_id"] == agent_id and e["organization_id"] == organization_id
    ]
    return {"episodes": results[-limit:], "total": len(results)}


# ── Semantic / Knowledge Memory (Postgres + Qdrant in production)

@app.post("/internal/memory/knowledge")
def store_knowledge(entry: SemanticMemoryCreate) -> dict:
    """Store a semantic fact with optional vector embedding."""
    knowledge_id = f"ki_{uuid4().hex[:12]}"
    record = {
        "id": knowledge_id,
        **entry.model_dump(),
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }
    _knowledge.append(record)
    return {"status": "stored", "id": knowledge_id}


@app.get("/internal/memory/knowledge")
def search_knowledge(
    organization_id: str,
    query: str = "",
    entity_type: str = "",
    limit: int = 10,
) -> dict:
    """Search semantic knowledge (text match stub — Qdrant vector search in production)."""
    results = []
    for item in _knowledge:
        if item["organization_id"] != organization_id:
            continue
        if entity_type and item.get("entity_type") != entity_type:
            continue
        if query and query.lower() not in item.get("fact_text", "").lower():
            continue
        results.append({**item, "relevance_score": 0.85})  # stub score

    return {"knowledge": results[:limit], "total": len(results)}


# ── Procedural Memory (Postgres in production) ──────────────────

@app.post("/internal/memory/procedures")
def store_procedure(entry: ProceduralMemoryCreate) -> dict:
    """Store a procedural memory (playbook / SOP)."""
    proc_id = f"proc_{uuid4().hex[:12]}"
    now = datetime.utcnow().isoformat()
    record = {
        "id": proc_id,
        **entry.model_dump(),
        "created_at": now,
        "updated_at": now,
    }
    _procedures.append(record)
    return {"status": "stored", "id": proc_id}


@app.get("/internal/memory/procedures")
def list_procedures(
    organization_id: str,
    trigger: str = "",
) -> dict:
    """List procedures, optionally filtered by trigger event."""
    results = [
        p for p in _procedures
        if p["organization_id"] == organization_id
        and (not trigger or p.get("trigger") == trigger)
    ]
    return {"procedures": results}


# ── Unified Context Retrieval ───────────────────────────────────

@app.post("/internal/memory/retrieve")
def retrieve_context(request: MemoryRetrievalRequest) -> dict:
    """Assemble a context packet from all memory layers.

    This is the primary endpoint called by the agent runtime before
    each reasoning step.  It queries working, episodic, semantic,
    and procedural memory and returns a ranked context packet.
    """
    org = request.organization_id
    agent = request.agent_id
    query = request.query
    max_results = request.max_results

    # Working memory (latest session)
    working = None
    for session_data in _working.values():
        if session_data.get("agent_id") == agent:
            working = session_data
            break

    if not working:
        working = {
            "session_id": f"sess_{uuid4().hex[:8]}",
            "agent_id": agent,
            "current_step": None,
            "recent_events": [],
            "temporary_context": {},
            "ttl_seconds": 3600,
        }

    # Episodic
    episodes = [
        e for e in _episodes
        if e.get("agent_id") == agent and e.get("organization_id") == org
    ][-max_results:]

    # Semantic
    facts = []
    for item in _knowledge:
        if item["organization_id"] != org:
            continue
        if query and query.lower() in item.get("fact_text", "").lower():
            facts.append({**item, "relevance_score": 0.9})
        elif not query:
            facts.append({**item, "relevance_score": 0.5})
    facts = facts[:max_results]

    # Procedural
    procedures = [
        p for p in _procedures
        if p["organization_id"] == org
    ]

    return {
        "working": working,
        "episodes": episodes,
        "facts": facts,
        "procedures": procedures,
    }
