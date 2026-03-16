"""Notification Service — outbound notifications for Workforce OS.

Endpoints
---------
GET   /health
POST  /internal/notifications/email
POST  /internal/notifications/sms
POST  /internal/notifications/push
GET   /internal/notifications
"""

from __future__ import annotations

from datetime import datetime
from typing import List
from uuid import uuid4

from fastapi import FastAPI

app = FastAPI(title="Notification Service", version="0.1.0")

_notifications: List[dict] = []


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "notification-service"}


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
    return record


@app.get("/internal/notifications")
def list_notifications(organization_id: str = "", limit: int = 50) -> dict:
    """List recent notifications."""
    results = _notifications
    if organization_id:
        results = [n for n in results if n.get("organization_id") == organization_id]
    return {"notifications": results[-limit:], "total": len(results)}
