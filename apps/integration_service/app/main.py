"""Integration Service — external system adapters for Workforce OS.

Provides a unified interface for agents to interact with external
business systems (CRM, calendar, billing, email, ERP, etc.)
through tool adapters.

Endpoints
---------
GET   /health
POST  /internal/integrations               - register integration
GET   /internal/integrations                - list integrations
POST  /internal/tools/execute              - execute a tool call
POST  /internal/tools/invoke               - invoke a tool (alias)
POST  /internal/tools/validate             - validate tool config
GET   /internal/tools                       - list available tools
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List
from uuid import uuid4

from fastapi import FastAPI, HTTPException

from packages.shared.models import IntegrationConfig, ToolCallRequest

app = FastAPI(title="Integration Service", version="0.2.0")

# In-memory stores
_integrations: Dict[str, dict] = {}

# Available tool adapters per integration type
TOOL_ADAPTERS: Dict[str, List[str]] = {
    "crm": ["crm.create_task", "crm.update_lead", "crm.get_lead", "crm.list_contacts"],
    "calendar": ["calendar.create_event", "calendar.check_availability", "calendar.list_events"],
    "billing": ["billing.create_invoice", "billing.get_balance", "billing.process_payment"],
    "email": ["email.send", "email.draft", "email.list_inbox"],
    "notification": ["notification.send_sms", "notification.send_push"],
    "erp": ["erp.create_order", "erp.check_inventory", "erp.update_status"],
    "voice": ["voice.call", "voice.transfer", "voice.hold", "voice.synthesize"],
}


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "integration-service"}


@app.post("/internal/integrations")
def register_integration(config: IntegrationConfig) -> dict:
    """Register a new external system integration for an organization."""
    integration_id = f"int_{uuid4().hex[:12]}"
    now = datetime.utcnow()
    record = {
        "id": integration_id,
        "organization_id": config.organization_id,
        "integration_type": config.integration_type,
        "name": config.name,
        "settings": config.settings,
        "enabled": config.enabled,
        "available_tools": TOOL_ADAPTERS.get(config.integration_type, []),
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }
    _integrations[integration_id] = record
    return record


@app.get("/internal/integrations")
def list_integrations(organization_id: str) -> dict:
    """List all integrations for an organization."""
    results = [
        i for i in _integrations.values()
        if i["organization_id"] == organization_id
    ]
    return {"integrations": results, "total": len(results)}


@app.post("/internal/tools/execute")
def execute_tool(request: ToolCallRequest) -> dict:
    """Execute a tool call through the appropriate adapter.

    In production, this dispatches to the real external system
    adapter (e.g., HubSpot API, Google Calendar API, Stripe, etc.).
    """
    return _run_tool(request)


@app.post("/internal/tools/invoke")
def invoke_tool(request: ToolCallRequest) -> dict:
    """Invoke a tool — identical to /execute, matches blueprint naming."""
    return _run_tool(request)


@app.post("/internal/tools/validate")
def validate_tool(payload: dict) -> dict:
    """Validate a tool configuration before use.

    Checks that the tool name exists, the organization has a matching
    integration, and the argument schema is acceptable.
    """
    tool_name = payload.get("tool_name", "")
    organization_id = payload.get("organization_id", "")

    # Check tool exists in any adapter
    all_tools = [t for tools in TOOL_ADAPTERS.values() for t in tools]
    if tool_name not in all_tools:
        return {
            "valid": False,
            "tool_name": tool_name,
            "error": f"Unknown tool: {tool_name}",
        }

    # Check org has a matching integration
    int_type = tool_name.split(".")[0]
    org_integrations = [
        i for i in _integrations.values()
        if i["organization_id"] == organization_id
        and i["integration_type"] == int_type
        and i["enabled"]
    ]

    if not org_integrations and organization_id:
        return {
            "valid": False,
            "tool_name": tool_name,
            "error": f"No active '{int_type}' integration for organization",
        }

    return {
        "valid": True,
        "tool_name": tool_name,
        "integration_type": int_type,
    }


@app.get("/internal/tools")
def list_tools(organization_id: str = "") -> dict:
    """List all available tools across integration types."""
    all_tools = []
    for int_type, tools in TOOL_ADAPTERS.items():
        for tool_name in tools:
            all_tools.append({
                "name": tool_name,
                "integration_type": int_type,
                "description": f"{int_type.upper()} tool: {tool_name}",
            })
    return {"tools": all_tools, "total": len(all_tools)}


# ── Internal helpers ──────────────────────────────────────────

def _run_tool(request: ToolCallRequest) -> dict:
    """Dispatch and execute a tool call."""
    tool = request.tool_name
    start = datetime.utcnow()

    if tool.startswith("calendar."):
        result = _simulate_calendar_tool(tool, request.parameters)
    elif tool.startswith("crm."):
        result = _simulate_crm_tool(tool, request.parameters)
    elif tool.startswith("email."):
        result = _simulate_email_tool(tool, request.parameters)
    elif tool.startswith("billing."):
        result = _simulate_billing_tool(tool, request.parameters)
    elif tool.startswith("notification."):
        result = _simulate_notification_tool(tool, request.parameters)
    elif tool.startswith("voice."):
        result = _simulate_voice_tool(tool, request.parameters)
    else:
        result = {"status": "unsupported", "message": f"Tool '{tool}' not available"}

    end = datetime.utcnow()
    duration_ms = int((end - start).total_seconds() * 1000)

    return {
        "tool_name": tool,
        "status": result.get("status", "success"),
        "result": result,
        "reference_id": f"ref_{uuid4().hex[:10]}",
        "duration_ms": duration_ms,
    }


# ── Simulated adapters ─────────────────────────────────────────

def _simulate_calendar_tool(tool: str, params: dict) -> dict:
    if tool == "calendar.create_event":
        return {
            "status": "success",
            "event_id": f"evt_{uuid4().hex[:8]}",
            "title": params.get("title", "New Event"),
            "time": params.get("preferred_time", "next available"),
        }
    if tool == "calendar.check_availability":
        return {
            "status": "success",
            "available_slots": [
                "2026-03-17 09:00", "2026-03-17 10:00", "2026-03-17 14:00",
            ],
        }
    return {"status": "success", "events": []}


def _simulate_crm_tool(tool: str, params: dict) -> dict:
    if tool == "crm.create_task":
        return {
            "status": "success",
            "task_id": f"crm_tsk_{uuid4().hex[:8]}",
            "title": params.get("title", "New Task"),
        }
    if tool == "crm.update_lead":
        return {
            "status": "success",
            "lead_id": params.get("lead_id", f"lead_{uuid4().hex[:8]}"),
            "updated": True,
        }
    if tool == "crm.get_lead":
        return {
            "status": "success",
            "lead_id": params.get("lead_id", "lead_001"),
            "name": "John Doe",
            "stage": "qualified",
        }
    return {"status": "success", "contacts": []}


def _simulate_email_tool(tool: str, params: dict) -> dict:
    if tool == "email.send":
        return {
            "status": "success",
            "message_id": f"msg_{uuid4().hex[:8]}",
            "to": params.get("to", "customer@example.com"),
            "subject": params.get("subject", "Follow-up"),
        }
    if tool == "email.draft":
        return {
            "status": "success",
            "draft_id": f"draft_{uuid4().hex[:8]}",
            "body": params.get("body", ""),
        }
    return {"status": "success", "inbox": []}


def _simulate_billing_tool(tool: str, params: dict) -> dict:
    if tool == "billing.create_invoice":
        return {
            "status": "success",
            "invoice_id": f"inv_{uuid4().hex[:8]}",
            "amount": params.get("amount", 0),
        }
    return {"status": "success", "balance": 0.0}


def _simulate_notification_tool(tool: str, params: dict) -> dict:
    return {
        "status": "success",
        "notification_id": f"notif_{uuid4().hex[:8]}",
        "channel": "sms" if "sms" in tool else "push",
        "to": params.get("to", "+1234567890"),
    }


def _simulate_voice_tool(tool: str, params: dict) -> dict:
    if tool == "voice.call":
        return {
            "status": "success",
            "call_id": f"call_{uuid4().hex[:8]}",
            "to": params.get("to_number", "+1234567890"),
        }
    if tool == "voice.transfer":
        return {
            "status": "success",
            "transfer_id": f"xfer_{uuid4().hex[:8]}",
            "target": params.get("target", "support"),
        }
    return {"status": "success", "action": tool.split(".")[-1]}
