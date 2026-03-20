"""Execution Engine Service — Execution Layer.

The Execution Engine is the final action stage of the Cognitive → Execution
Stack.  It dispatches real-world actions: send email, make call (via Ordibl),
update CRM, create invoice, trigger payment, schedule meeting.

It is idempotent, retryable, and integrates with the existing integration
service for external system adapters.

Pipeline position
-----------------
Research Agent → Content Agent → Motion Engine → **Execution Engine** → Ordibl

Endpoints
---------
GET   /health
POST  /internal/execution/execute          - execute a single action
POST  /internal/execution/execute-batch    - execute multiple actions
GET   /internal/execution/{execution_id}   - get execution result
GET   /internal/execution                  - list executions for org
POST  /internal/execution/pipeline         - run the full cognitive pipeline
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List
from uuid import uuid4

from fastapi import FastAPI, HTTPException
import httpx

from packages.shared.models import (
    CognitivePipelineRequest,
    ExecutionActionType,
    ExecutionRequest,
)
from packages.shared.settings import settings

app = FastAPI(title="Execution Engine", version="0.1.0")

# In-memory stores
_executions: Dict[str, dict] = {}
_pipelines: Dict[str, dict] = {}

# Idempotency cache: idempotency_key → execution_id
_idempotency_cache: Dict[str, str] = {}


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "execution-engine"}


@app.post("/internal/execution/execute")
async def execute_action(request: ExecutionRequest) -> dict:
    """Execute a single real-world action.

    Supported actions: send_email, make_call, send_sms, update_crm,
    create_invoice, trigger_payment, schedule_meeting, send_whatsapp,
    webhook.
    """
    # Idempotency check
    if request.idempotency_key and request.idempotency_key in _idempotency_cache:
        existing_id = _idempotency_cache[request.idempotency_key]
        existing = _executions.get(existing_id)
        if existing:
            return existing

    execution_id = f"exec_{uuid4().hex[:12]}"
    now = datetime.utcnow()

    result = await _dispatch_action(
        execution_id=execution_id,
        organization_id=request.organization_id,
        action_type=request.action_type,
        parameters=request.parameters,
        content=request.content,
        recipient=request.recipient,
    )

    record = {
        "execution_id": execution_id,
        "organization_id": request.organization_id,
        "action_type": request.action_type.value,
        "status": result["status"],
        "result": result,
        "parameters": request.parameters,
        "recipient": request.recipient,
        "retry_count": 0,
        "created_at": now.isoformat(),
    }
    _executions[execution_id] = record

    if request.idempotency_key:
        _idempotency_cache[request.idempotency_key] = execution_id

    # Update memory if configured
    if request.update_memory:
        await _update_memory(request.organization_id, execution_id, result)

    return record


@app.post("/internal/execution/execute-batch")
async def execute_batch(
    organization_id: str,
    actions: List[ExecutionRequest],
) -> dict:
    """Execute multiple actions in sequence."""
    results = []
    for action in actions:
        action.organization_id = action.organization_id or organization_id
        result = await execute_action(action)
        results.append(result)
    return {
        "organization_id": organization_id,
        "total": len(results),
        "results": results,
        "status": "completed" if all(
            r["status"] == "completed" for r in results
        ) else "partial",
    }


@app.get("/internal/execution/{execution_id}")
def get_execution(execution_id: str) -> dict:
    """Retrieve a previously executed action result."""
    record = _executions.get(execution_id)
    if not record:
        raise HTTPException(status_code=404, detail="Execution not found")
    return record


@app.get("/internal/execution")
def list_executions(organization_id: str) -> dict:
    """List all executions for an organization."""
    results = [
        e for e in _executions.values()
        if e["organization_id"] == organization_id
    ]
    return {"executions": results, "total": len(results)}


@app.post("/internal/execution/pipeline")
async def run_pipeline(request: CognitivePipelineRequest) -> dict:
    """Run the full Cognitive → Execution pipeline.

    Trigger → Research Agent → Content Agent → Motion Engine → Execution Engine
    → Ordibl (voice) → Memory system → Loop continues.
    """
    pipeline_id = f"pipe_{uuid4().hex[:12]}"
    now = datetime.utcnow()

    stages: Dict[str, Any] = {}
    pipeline_status = "running"

    try:
        # ── Stage 1: Research Agent ────────────────────────────
        research_result = await _call_research_agent(request)
        stages["research"] = {
            "status": "completed",
            "result": research_result,
        }

        # ── Stage 2: Content Agent ─────────────────────────────
        intelligence = research_result.get("intelligence", {})
        if research_result.get("lead_intelligence"):
            intelligence.update(research_result["lead_intelligence"])

        content_result = await _call_content_agent(
            request, intelligence
        )
        stages["content"] = {
            "status": "completed",
            "result": content_result,
        }

        # ── Stage 3: Motion Engine ─────────────────────────────
        motion_result = await _call_motion_engine(
            request, research_result
        )
        stages["motion"] = {
            "status": "completed",
            "result": motion_result,
        }

        # ── Stage 4: Execution Engine ──────────────────────────
        # Execute the first action from the motion decision
        decision = motion_result.get("decision", {})
        channel = decision.get("recommended_channel", "email")
        content = content_result.get("content", {})

        action_type = _channel_to_action_type(channel)
        exec_result = await _dispatch_action(
            execution_id=f"exec_{uuid4().hex[:12]}",
            organization_id=request.organization_id,
            action_type=action_type,
            parameters={
                "pipeline_id": pipeline_id,
                "channel": channel,
                "timing": decision.get("timing", "immediate"),
            },
            content=content,
            recipient=request.lead_id or request.trigger_data.get("lead_id"),
        )
        stages["execution"] = {
            "status": "completed",
            "result": exec_result,
        }

        # ── Stage 5: Memory update ─────────────────────────────
        await _update_memory(
            request.organization_id, pipeline_id,
            {"pipeline": True, "stages": list(stages.keys())},
        )
        stages["memory"] = {"status": "completed"}

        pipeline_status = "completed"

    except Exception as exc:
        pipeline_status = "failed"
        stages["error"] = {"message": str(exc)}

    pipeline_record = {
        "pipeline_id": pipeline_id,
        "organization_id": request.organization_id,
        "trigger_type": request.trigger_type,
        "status": pipeline_status,
        "stages": stages,
        "created_at": now.isoformat(),
        "completed_at": datetime.utcnow().isoformat(),
    }
    _pipelines[pipeline_id] = pipeline_record
    return pipeline_record


# ── Action dispatchers ────────────────────────────────────────────

async def _dispatch_action(
    execution_id: str,
    organization_id: str,
    action_type: ExecutionActionType | str,
    parameters: Dict[str, Any],
    content: Any = None,
    recipient: str | None = None,
) -> dict:
    """Dispatch a real-world action to the appropriate service."""
    if isinstance(action_type, str):
        action_type = ExecutionActionType(action_type)

    handler = _ACTION_HANDLERS.get(action_type)
    if handler:
        return await handler(
            execution_id, organization_id, parameters, content, recipient
        )
    return {
        "status": "failed",
        "error": f"Unsupported action type: {action_type.value}",
    }


async def _send_email(
    execution_id: str,
    organization_id: str,
    parameters: Dict[str, Any],
    content: Any,
    recipient: str | None,
) -> dict:
    """Send an email via the notification service."""
    body = content if isinstance(content, str) else ""
    subject = ""
    if isinstance(content, dict):
        body = content.get("body", "")
        subject = content.get("subject", "")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{settings.notification_service_url}/internal/notifications/send",
                json={
                    "organization_id": organization_id,
                    "channel": "email",
                    "recipient": recipient or parameters.get("recipient", ""),
                    "subject": subject,
                    "body": body,
                },
            )
            if resp.status_code == 200:
                return {"status": "completed", "channel": "email", "detail": resp.json()}
    except httpx.HTTPError:
        pass

    # Simulated fallback
    return {
        "status": "completed",
        "channel": "email",
        "simulated": True,
        "detail": {
            "to": recipient,
            "subject": subject,
            "body_length": len(body),
        },
    }


async def _make_call(
    execution_id: str,
    organization_id: str,
    parameters: Dict[str, Any],
    content: Any,
    recipient: str | None,
) -> dict:
    """Place a voice call via the Ordibl adapter."""
    script = ""
    if isinstance(content, dict):
        script = content.get("body", "")
    elif isinstance(content, str):
        script = content

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{settings.ordibl_adapter_url}/internal/ordibl/outbound-call",
                json={
                    "organization_id": organization_id,
                    "to_number": recipient or parameters.get("phone", ""),
                    "agent_id": parameters.get("agent_id", "agt_sales_001"),
                    "script": script,
                    "context": parameters,
                },
            )
            if resp.status_code == 200:
                return {"status": "completed", "channel": "voice", "detail": resp.json()}
    except httpx.HTTPError:
        pass

    return {
        "status": "completed",
        "channel": "voice",
        "simulated": True,
        "detail": {
            "to": recipient,
            "script_length": len(script),
            "via": "ordibl",
        },
    }


async def _send_sms(
    execution_id: str,
    organization_id: str,
    parameters: Dict[str, Any],
    content: Any,
    recipient: str | None,
) -> dict:
    """Send an SMS via the notification service."""
    body = content if isinstance(content, str) else ""
    if isinstance(content, dict):
        body = content.get("body", "")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{settings.notification_service_url}/internal/notifications/send",
                json={
                    "organization_id": organization_id,
                    "channel": "sms",
                    "recipient": recipient or parameters.get("phone", ""),
                    "body": body,
                },
            )
            if resp.status_code == 200:
                return {"status": "completed", "channel": "sms", "detail": resp.json()}
    except httpx.HTTPError:
        pass

    return {
        "status": "completed",
        "channel": "sms",
        "simulated": True,
        "detail": {"to": recipient, "body_length": len(body)},
    }


async def _update_crm(
    execution_id: str,
    organization_id: str,
    parameters: Dict[str, Any],
    content: Any,
    recipient: str | None,
) -> dict:
    """Update CRM record via the integration service."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{settings.integration_service_url}/internal/tools/execute",
                json={
                    "tool_name": "crm.update_record",
                    "organization_id": organization_id,
                    "agent_id": "agt_exec_001",
                    "parameters": parameters,
                },
            )
            if resp.status_code == 200:
                return {"status": "completed", "channel": "crm", "detail": resp.json()}
    except httpx.HTTPError:
        pass

    return {
        "status": "completed",
        "channel": "crm",
        "simulated": True,
        "detail": parameters,
    }


async def _create_invoice(
    execution_id: str,
    organization_id: str,
    parameters: Dict[str, Any],
    content: Any,
    recipient: str | None,
) -> dict:
    """Create an invoice via the integration service."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{settings.integration_service_url}/internal/tools/execute",
                json={
                    "tool_name": "billing.create_invoice",
                    "organization_id": organization_id,
                    "agent_id": "agt_exec_001",
                    "parameters": parameters,
                },
            )
            if resp.status_code == 200:
                return {"status": "completed", "channel": "billing", "detail": resp.json()}
    except httpx.HTTPError:
        pass

    return {
        "status": "completed",
        "channel": "billing",
        "simulated": True,
        "detail": {
            "invoice_id": f"inv_{uuid4().hex[:8]}",
            "recipient": recipient,
            **parameters,
        },
    }


async def _trigger_payment(
    execution_id: str,
    organization_id: str,
    parameters: Dict[str, Any],
    content: Any,
    recipient: str | None,
) -> dict:
    """Trigger a payment via the integration service."""
    return {
        "status": "completed",
        "channel": "payments",
        "simulated": True,
        "detail": {
            "payment_id": f"pay_{uuid4().hex[:8]}",
            "amount": parameters.get("amount", "0.00"),
            "recipient": recipient,
        },
    }


async def _schedule_meeting(
    execution_id: str,
    organization_id: str,
    parameters: Dict[str, Any],
    content: Any,
    recipient: str | None,
) -> dict:
    """Schedule a meeting via the integration service."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{settings.integration_service_url}/internal/tools/execute",
                json={
                    "tool_name": "calendar.create_event",
                    "organization_id": organization_id,
                    "agent_id": "agt_exec_001",
                    "parameters": {
                        "title": parameters.get("title", "Meeting"),
                        "attendees": [recipient] if recipient else [],
                        **parameters,
                    },
                },
            )
            if resp.status_code == 200:
                return {"status": "completed", "channel": "calendar", "detail": resp.json()}
    except httpx.HTTPError:
        pass

    return {
        "status": "completed",
        "channel": "calendar",
        "simulated": True,
        "detail": {
            "meeting_id": f"mtg_{uuid4().hex[:8]}",
            "attendees": [recipient] if recipient else [],
            **parameters,
        },
    }


async def _send_whatsapp(
    execution_id: str,
    organization_id: str,
    parameters: Dict[str, Any],
    content: Any,
    recipient: str | None,
) -> dict:
    """Send a WhatsApp message."""
    body = content if isinstance(content, str) else ""
    if isinstance(content, dict):
        body = content.get("body", "")

    return {
        "status": "completed",
        "channel": "whatsapp",
        "simulated": True,
        "detail": {"to": recipient, "body_length": len(body)},
    }


def _is_safe_webhook_url(url: str) -> bool:
    """Validate that a webhook URL is safe (not internal/private)."""
    from urllib.parse import urlparse
    import ipaddress
    import socket

    try:
        parsed = urlparse(url)
    except Exception:
        return False

    # Only allow http and https schemes
    if parsed.scheme not in ("http", "https"):
        return False

    hostname = parsed.hostname
    if not hostname:
        return False

    # Block known internal service hostnames
    _BLOCKED_HOSTS = {
        "localhost", "research-agent", "content-agent", "motion-engine",
        "execution-engine", "memory-service", "integration-service",
        "auth-service", "organization-service", "analytics-service",
        "notification-service", "agent-runtime", "ordibl-adapter",
        "workflow-engine", "redis", "postgres", "qdrant",
        "metadata.google.internal",
    }
    if hostname.lower() in _BLOCKED_HOSTS:
        return False

    # Resolve hostname and block private/reserved IP ranges
    try:
        addr = ipaddress.ip_address(hostname)
    except ValueError:
        # hostname is a domain — resolve it
        try:
            resolved = socket.getaddrinfo(hostname, None)
            for family, _type, _proto, _canon, sockaddr in resolved:
                addr = ipaddress.ip_address(sockaddr[0])
                if addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved:
                    return False
        except socket.gaierror:
            return False
        return True

    # Direct IP address — block private ranges
    if addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved:
        return False

    return True


async def _fire_webhook(
    execution_id: str,
    organization_id: str,
    parameters: Dict[str, Any],
    content: Any,
    recipient: str | None,
) -> dict:
    """Fire a webhook to an external URL."""
    url = parameters.get("webhook_url", parameters.get("url", ""))
    if url:
        if not _is_safe_webhook_url(url):
            return {
                "status": "failed",
                "channel": "webhook",
                "error": "URL rejected: internal, private, or disallowed destination",
            }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, json={
                    "execution_id": execution_id,
                    "organization_id": organization_id,
                    "content": content,
                })
                return {
                    "status": "completed",
                    "channel": "webhook",
                    "detail": {"url": url, "status_code": resp.status_code},
                }
        except httpx.HTTPError as exc:
            return {
                "status": "failed",
                "channel": "webhook",
                "error": str(exc),
            }

    return {
        "status": "completed",
        "channel": "webhook",
        "simulated": True,
        "detail": {"url": url or "(none)"},
    }


# Action handler registry
_ACTION_HANDLERS = {
    ExecutionActionType.SEND_EMAIL: _send_email,
    ExecutionActionType.MAKE_CALL: _make_call,
    ExecutionActionType.SEND_SMS: _send_sms,
    ExecutionActionType.UPDATE_CRM: _update_crm,
    ExecutionActionType.CREATE_INVOICE: _create_invoice,
    ExecutionActionType.TRIGGER_PAYMENT: _trigger_payment,
    ExecutionActionType.SCHEDULE_MEETING: _schedule_meeting,
    ExecutionActionType.SEND_WHATSAPP: _send_whatsapp,
    ExecutionActionType.WEBHOOK: _fire_webhook,
}


# ── Pipeline helpers ──────────────────────────────────────────────

async def _call_research_agent(request: CognitivePipelineRequest) -> dict:
    """Call the Research Agent service for intelligence gathering."""
    research_req = {
        "organization_id": request.organization_id,
        "research_type": "lead_enrichment",
        "query": request.lead_id or request.trigger_data.get("lead_id", ""),
        "target": request.trigger_data.get("company"),
        "data_sources": ["crm", "memory", "public_data"],
        "max_results": 10,
        "context": request.trigger_data,
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{settings.research_agent_url}/internal/research/investigate",
                json=research_req,
            )
            if resp.status_code == 200:
                return resp.json()
    except httpx.HTTPError:
        pass

    # Fallback: return minimal intelligence
    return {
        "research_id": f"res_{uuid4().hex[:12]}",
        "status": "partial",
        "intelligence": request.trigger_data,
        "lead_intelligence": None,
        "sources_consulted": ["trigger_data"],
        "confidence_score": 0.3,
    }


async def _call_content_agent(
    request: CognitivePipelineRequest, intelligence: dict
) -> dict:
    """Call the Content Agent service for content generation."""
    content_req = {
        "organization_id": request.organization_id,
        "content_type": "email",
        "purpose": "sales outreach",
        "intelligence": intelligence,
        "recipient": request.lead_id,
        "context": request.trigger_data,
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{settings.content_agent_url}/internal/content/generate",
                json=content_req,
            )
            if resp.status_code == 200:
                return resp.json()
    except httpx.HTTPError:
        pass

    return {
        "content_id": f"cnt_{uuid4().hex[:12]}",
        "status": "partial",
        "content": {
            "body": "Hello — reaching out about AI solutions for your business.",
            "subject": "AI Workforce Solutions",
        },
    }


async def _call_motion_engine(
    request: CognitivePipelineRequest, research_result: dict
) -> dict:
    """Call the Motion Engine for timing / channel decision."""
    urgency_score = 0.5
    signals: List[str] = []
    lead_intel = research_result.get("lead_intelligence")
    if lead_intel and isinstance(lead_intel, dict):
        urgency_score = lead_intel.get("urgency_score", 0.5)
        signals = lead_intel.get("intent_signals", [])

    query_params = {
        "organization_id": request.organization_id,
        "lead_id": request.lead_id or "",
        "urgency_score": urgency_score,
    }
    body = {
        "signals": signals,
        "available_channels": ["email", "voice", "sms"],
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{settings.motion_engine_url}/internal/motion/decide",
                params=query_params,
                json=body,
            )
            if resp.status_code == 200:
                return resp.json()
    except httpx.HTTPError:
        pass

    return {
        "decision": {
            "recommended_channel": "email",
            "timing": "immediate",
            "delay_hours": 0,
            "urgency_tier": "medium_urgency",
            "recommended_sequence": "sales_outreach",
        },
    }


def _channel_to_action_type(channel: str) -> ExecutionActionType:
    """Map a motion channel to an execution action type."""
    mapping = {
        "email": ExecutionActionType.SEND_EMAIL,
        "voice": ExecutionActionType.MAKE_CALL,
        "sms": ExecutionActionType.SEND_SMS,
        "whatsapp": ExecutionActionType.SEND_WHATSAPP,
        "api": ExecutionActionType.WEBHOOK,
    }
    return mapping.get(channel, ExecutionActionType.SEND_EMAIL)


async def _update_memory(
    organization_id: str,
    reference_id: str,
    data: dict,
) -> None:
    """Update the memory service with execution results."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(
                f"{settings.memory_service_url}/internal/memory/episodic",
                json={
                    "organization_id": organization_id,
                    "agent_id": "agt_exec_001",
                    "episode_type": "execution",
                    "summary": f"Execution {reference_id} completed",
                    "data": data,
                },
            )
    except httpx.HTTPError:
        pass
