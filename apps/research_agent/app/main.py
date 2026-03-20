"""Research Agent Service — Thinking Layer (Intelligence Ingestion).

The Research Agent is the first stage of the Cognitive → Execution Stack.
It gathers intelligence from multiple data sources (CRM, memory, public
data) and produces structured intelligence objects that feed downstream
into the Content Agent and Motion Engine.

Capabilities
------------
- Lead enrichment
- Market research
- Competitor analysis
- Customer profiling
- Signal detection (intent, urgency, interest)

Endpoints
---------
GET   /health
POST  /internal/research/investigate        - run a research task
POST  /internal/research/enrich-lead        - enrich a lead with intelligence
GET   /internal/research/{research_id}      - get research result
GET   /internal/research                    - list research results
POST  /internal/research/signals            - detect intent/urgency signals
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List
from uuid import uuid4

from fastapi import FastAPI, HTTPException
import httpx

from packages.shared.models import (
    LeadIntelligence,
    ResearchRequest,
    ResearchType,
)
from packages.shared.settings import settings

app = FastAPI(title="Research Agent", version="0.1.0")

# In-memory stores
_research_results: Dict[str, dict] = {}

# ── Simulated data sources ────────────────────────────────────────

_SIMULATED_LEADS: Dict[str, Dict[str, Any]] = {
    "acme_plumbing": {
        "lead_name": "Acme Plumbing",
        "company": "Acme Plumbing Co.",
        "size": "10 employees",
        "industry": "Home Services",
        "pain_points": ["missed calls", "manual booking", "no after-hours coverage"],
        "decision_maker": "Owner — James Mitchell",
        "recommended_pitch": "AI receptionist + automated scheduling",
        "contact_channels": ["phone", "email"],
        "urgency_score": 0.8,
        "intent_signals": ["searched for answering service", "high call volume"],
    },
    "bright_dental": {
        "lead_name": "Bright Dental",
        "company": "Bright Dental Clinic",
        "size": "25 employees",
        "industry": "Healthcare",
        "pain_points": ["appointment no-shows", "manual reminders", "billing follow-up"],
        "decision_maker": "Office Manager — Sarah Chen",
        "recommended_pitch": "AI scheduling + automated reminders + billing agent",
        "contact_channels": ["email", "phone", "sms"],
        "urgency_score": 0.6,
        "intent_signals": ["high no-show rate", "looking for automation"],
    },
}

_SIMULATED_MARKET_DATA: Dict[str, Dict[str, Any]] = {
    "ai_receptionist": {
        "market_size": "$2.1B",
        "growth_rate": "34% CAGR",
        "key_players": ["Smith.ai", "Ruby Receptionists", "Nexa"],
        "trends": ["AI-first solutions replacing human answering services"],
        "opportunity": "SMBs underserved — most solutions target enterprise",
    },
    "ai_workforce": {
        "market_size": "$15.7B",
        "growth_rate": "42% CAGR",
        "key_players": ["ServiceNow", "UiPath", "Automation Anywhere"],
        "trends": ["Autonomous agents replacing RPA bots"],
        "opportunity": "Vertical-specific AI workers for SMB market",
    },
}

_SIMULATED_COMPETITORS: Dict[str, List[Dict[str, str]]] = {
    "voice_ai": [
        {"name": "Smith.ai", "strength": "Human + AI hybrid", "weakness": "Expensive"},
        {"name": "Dialpad AI", "strength": "Enterprise features", "weakness": "Complex setup"},
        {"name": "Bland.ai", "strength": "API-first", "weakness": "No workflow engine"},
    ],
}


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "research-agent"}


@app.post("/internal/research/investigate")
async def investigate(request: ResearchRequest) -> dict:
    """Run a research investigation across configured data sources."""
    research_id = f"res_{uuid4().hex[:12]}"
    now = datetime.utcnow()

    intelligence: Dict[str, Any] = {}
    sources_consulted: List[str] = []
    confidence = 0.0
    lead_intel = None

    if request.research_type == ResearchType.LEAD_ENRICHMENT:
        lead_intel, intelligence, sources_consulted, confidence = await _enrich_lead(
            request.query, request.target, request.data_sources
        )
    elif request.research_type == ResearchType.MARKET_RESEARCH:
        intelligence, sources_consulted, confidence = _do_market_research(request.query)
    elif request.research_type == ResearchType.COMPETITOR_ANALYSIS:
        intelligence, sources_consulted, confidence = _do_competitor_analysis(request.query)
    elif request.research_type == ResearchType.CUSTOMER_PROFILING:
        lead_intel, intelligence, sources_consulted, confidence = await _profile_customer(
            request.query, request.target, request.data_sources
        )
    elif request.research_type == ResearchType.SIGNAL_DETECTION:
        intelligence, sources_consulted, confidence = _detect_signals(
            request.query, request.context
        )

    status = "completed" if confidence >= settings.research_confidence_threshold else "partial"

    result = {
        "research_id": research_id,
        "organization_id": request.organization_id,
        "research_type": request.research_type.value,
        "status": status,
        "intelligence": intelligence,
        "lead_intelligence": lead_intel.model_dump() if lead_intel else None,
        "sources_consulted": sources_consulted,
        "confidence_score": confidence,
        "created_at": now.isoformat(),
    }
    _research_results[research_id] = result
    return result


@app.post("/internal/research/enrich-lead")
async def enrich_lead(request: ResearchRequest) -> dict:
    """Specialized endpoint for lead enrichment — convenience wrapper."""
    request.research_type = ResearchType.LEAD_ENRICHMENT
    return await investigate(request)


@app.get("/internal/research/{research_id}")
def get_research(research_id: str) -> dict:
    """Retrieve a previously completed research result."""
    result = _research_results.get(research_id)
    if not result:
        raise HTTPException(status_code=404, detail="Research result not found")
    return result


@app.get("/internal/research")
def list_research(organization_id: str) -> dict:
    """List all research results for an organization."""
    results = [
        r for r in _research_results.values()
        if r["organization_id"] == organization_id
    ]
    return {"results": results, "total": len(results)}


@app.post("/internal/research/signals")
async def detect_signals_endpoint(request: ResearchRequest) -> dict:
    """Detect intent, urgency, and interest signals from available data."""
    request.research_type = ResearchType.SIGNAL_DETECTION
    return await investigate(request)


# ── Internal helpers ──────────────────────────────────────────────

async def _enrich_lead(
    query: str, target: str | None, data_sources: List[str]
) -> tuple:
    """Enrich a lead by consulting CRM, memory, and public data."""
    sources: List[str] = []
    combined: Dict[str, Any] = {}
    confidence = 0.0

    # Normalize query for lookup
    key = query.lower().replace(" ", "_")

    # Check simulated data
    if key in _SIMULATED_LEADS:
        data = _SIMULATED_LEADS[key]
        sources.append("internal_database")
        combined.update(data)
        confidence = 0.85
        lead_intel = LeadIntelligence(**data)
    else:
        # Try CRM lookup via integration service
        if "crm" in data_sources:
            crm_data = await _query_crm(target or query)
            if crm_data:
                sources.append("crm")
                combined.update(crm_data)
                confidence += 0.3

        # Try memory service
        if "memory" in data_sources:
            memory_data = await _query_memory(query)
            if memory_data:
                sources.append("memory_service")
                combined.update(memory_data)
                confidence += 0.2

        # Generate lead intelligence from whatever we gathered
        lead_intel = LeadIntelligence(
            lead_name=target or query,
            company=combined.get("company"),
            size=combined.get("size"),
            industry=combined.get("industry"),
            pain_points=combined.get("pain_points", []),
            decision_maker=combined.get("decision_maker"),
            recommended_pitch=combined.get("recommended_pitch",
                                            "AI-powered business automation"),
            contact_channels=combined.get("contact_channels", ["email"]),
            urgency_score=combined.get("urgency_score", 0.5),
            intent_signals=combined.get("intent_signals", []),
        )

        if not sources:
            sources.append("generated")
            confidence = max(confidence, 0.4)

    return lead_intel, combined, sources, min(confidence, 1.0)


async def _profile_customer(
    query: str, target: str | None, data_sources: List[str]
) -> tuple:
    """Profile a customer from CRM and memory data."""
    return await _enrich_lead(query, target, data_sources)


def _do_market_research(query: str) -> tuple:
    """Return market research intelligence."""
    key = query.lower().replace(" ", "_")
    if key in _SIMULATED_MARKET_DATA:
        return _SIMULATED_MARKET_DATA[key], ["market_database"], 0.75
    return {
        "market_size": "Unknown",
        "note": f"No detailed data for '{query}' — general research recommended",
    }, ["generated"], 0.3


def _do_competitor_analysis(query: str) -> tuple:
    """Return competitor analysis intelligence."""
    key = query.lower().replace(" ", "_")
    if key in _SIMULATED_COMPETITORS:
        return {
            "competitors": _SIMULATED_COMPETITORS[key],
            "total": len(_SIMULATED_COMPETITORS[key]),
        }, ["competitor_database"], 0.7
    return {
        "competitors": [],
        "note": f"No competitor data for '{query}'",
    }, ["generated"], 0.3


def _detect_signals(query: str, context: Dict[str, Any]) -> tuple:
    """Detect intent and urgency signals from context."""
    signals: List[str] = []
    urgency = 0.5

    text = (query + " " + str(context)).lower()

    if any(w in text for w in ["urgent", "asap", "immediately", "now"]):
        signals.append("high_urgency")
        urgency = 0.9
    if any(w in text for w in ["pricing", "cost", "quote", "budget"]):
        signals.append("purchase_intent")
        urgency = max(urgency, 0.7)
    if any(w in text for w in ["demo", "trial", "test"]):
        signals.append("evaluation_stage")
        urgency = max(urgency, 0.6)
    if any(w in text for w in ["competitor", "alternative", "switch"]):
        signals.append("competitive_evaluation")
        urgency = max(urgency, 0.7)
    if any(w in text for w in ["cancel", "unhappy", "frustrated"]):
        signals.append("churn_risk")
        urgency = max(urgency, 0.85)

    if not signals:
        signals.append("general_inquiry")

    return {
        "signals": signals,
        "urgency_score": urgency,
        "recommended_action": _recommend_action(signals),
    }, ["signal_engine"], 0.8


def _recommend_action(signals: List[str]) -> str:
    """Recommend next action based on detected signals."""
    if "churn_risk" in signals:
        return "immediate_outreach_call"
    if "high_urgency" in signals:
        return "priority_response"
    if "purchase_intent" in signals:
        return "send_proposal"
    if "competitive_evaluation" in signals:
        return "schedule_demo"
    if "evaluation_stage" in signals:
        return "send_demo_link"
    return "standard_follow_up"


async def _query_crm(target: str) -> Dict[str, Any]:
    """Query CRM via integration service for lead data."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{settings.integration_service_url}/internal/tools/execute",
                json={
                    "tool_name": "crm.get_lead",
                    "organization_id": "org_001",
                    "agent_id": "agt_research_001",
                    "parameters": {"lead_id": target},
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("result", {})
    except httpx.HTTPError:
        pass
    return {}


async def _query_memory(query: str) -> Dict[str, Any]:
    """Query memory service for relevant facts/episodes."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{settings.memory_service_url}/internal/memory/retrieve",
                json={
                    "organization_id": "org_001",
                    "agent_id": "agt_research_001",
                    "query": query,
                    "memory_types": ["semantic", "episodic"],
                    "max_results": 5,
                },
            )
            if resp.status_code == 200:
                return resp.json()
    except httpx.HTTPError:
        pass
    return {}
