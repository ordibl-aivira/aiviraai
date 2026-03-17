"""Notification Service — outbound notifications for Workforce OS.

Unified send endpoint + per-channel endpoints + template rendering.

Endpoints
---------
GET   /health
POST  /internal/notifications/send               - unified send
POST  /internal/notifications/email              - send email
POST  /internal/notifications/sms                - send SMS
POST  /internal/notifications/push               - send push
POST  /internal/notifications/template/render    - render template
GET   /internal/notifications                    - list notifications
GET   /internal/notifications/{message_id}       - get by ID
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List
from uuid import uuid4

from fastapi import FastAPI, HTTPException

from packages.shared.models import NotificationSendRequest, TemplateRenderRequest

app = FastAPI(title="Notification Service", version="0.2.0")

_notifications: List[dict] = []
_notifications_by_id: Dict[str, dict] = {}

# Simple template store
_templates: Dict[str, str] = {
    "welcome": "Welcome to {company_name}, {customer_name}!",
    "appointment_confirmation": "Your appointment is confirmed for {date} at {time}.",
    "follow_up": "Hi {customer_name}, just following up on {subject}.",
    "invoice": "Invoice #{invoice_id} for ${amount} is ready for review.",
}


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "notification-service"}


@app.post("/internal/notifications/send")
def unified_send(request: NotificationSendRequest) -> dict:
    """Unified notification send — routes to the appropriate channel."""
    notif_id = f"notif_{uuid4().hex[:12]}"
    now = datetime.utcnow()

    body = request.body
    if request.template_id and request.template_id in _templates:
        body = _templates[request.template_id].format(**request.template_vars)

    record = {
        "id": notif_id,
        "channel": request.channel,
        "to": request.to,
        "subject": request.subject,
        "body": body,
        "organization_id": request.organization_id,
        "template_id": request.template_id,
        "status": "sent",
        "created_at": now.isoformat(),
    }
    _notifications.append(record)
    _notifications_by_id[notif_id] = record
    return record


@app.post("/internal/notifications/email")
def send_email(payload: dict) -> dict:
    """Send an email notification (stub)."""
    notif_id = f"notif_{uuid4().hex[:12]}"
    record = {
        "id": notif_id,
        "channel": "email",
        "to": payload.get("to"),
        "subject": payload.get("subject", ""),
        "body": payload.get("body", ""),
        "organization_id": payload.get("organization_id", ""),
        "status": "sent",
        "created_at": datetime.utcnow().isoformat(),
    }
    _notifications.append(record)
    _notifications_by_id[notif_id] = record
    return record


@app.post("/internal/notifications/sms")
def send_sms(payload: dict) -> dict:
    """Send an SMS notification (stub)."""
    notif_id = f"notif_{uuid4().hex[:12]}"
    record = {
        "id": notif_id,
        "channel": "sms",
        "to": payload.get("to"),
        "message": payload.get("message", ""),
        "organization_id": payload.get("organization_id", ""),
        "status": "sent",
        "created_at": datetime.utcnow().isoformat(),
    }
    _notifications.append(record)
    _notifications_by_id[notif_id] = record
    return record


@app.post("/internal/notifications/push")
def send_push(payload: dict) -> dict:
    """Send a push notification (stub)."""
    notif_id = f"notif_{uuid4().hex[:12]}"
    record = {
        "id": notif_id,
        "channel": "push",
        "user_id": payload.get("user_id"),
        "title": payload.get("title", ""),
        "body": payload.get("body", ""),
        "organization_id": payload.get("organization_id", ""),
        "status": "sent",
        "created_at": datetime.utcnow().isoformat(),
    }
    _notifications.append(record)
    _notifications_by_id[notif_id] = record
    return record


@app.post("/internal/notifications/template/render")
def render_template(request: TemplateRenderRequest) -> dict:
    """Render a notification template with variables."""
    template = _templates.get(request.template_id)
    if not template:
        raise HTTPException(status_code=404, detail=f"Template not found: {request.template_id}")

    try:
        rendered = template.format(**request.variables)
    except KeyError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Missing template variable: {exc}",
        )

    return {
        "template_id": request.template_id,
        "rendered": rendered,
    }


@app.get("/internal/notifications")
def list_notifications(organization_id: str = "", limit: int = 50) -> dict:
    """List recent notifications."""
    results = _notifications
    if organization_id:
        results = [n for n in results if n.get("organization_id") == organization_id]
    return {"notifications": results[-limit:], "total": len(results)}


@app.get("/internal/notifications/{message_id}")
def get_notification(message_id: str) -> dict:
    """Retrieve a single notification by ID."""
    notif = _notifications_by_id.get(message_id)
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    return notif
