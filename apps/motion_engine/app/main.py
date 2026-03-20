"""Motion Engine Service — Decision & Planning Layer.

The Motion Engine is the scheduler + decision brain of the Cognitive →
Execution Stack.  It decides WHEN to act, WHICH CHANNEL to use,
sequences actions, and enforces timing / SLA rules.

Example sequence
----------------
Day 0 → send email
Day 2 → if no reply → call
Day 5 → send SMS
Day 7 → escalate or close

Tech concepts
-------------
- State machine + rules engine
- SLA + retry logic
- Priority queues
- Designed to be backed by Temporal / BullMQ in production

Endpoints
---------
GET   /health
POST  /internal/motion/sequences               - create a motion sequence
GET   /internal/motion/sequences/{sequence_id}  - get sequence status
POST  /internal/motion/sequences/{sequence_id}/advance - advance to next step
POST  /internal/motion/sequences/{sequence_id}/cancel  - cancel sequence
GET   /internal/motion/sequences                - list sequences for org
POST  /internal/motion/decide                   - decide next best action
POST  /internal/motion/evaluate-timing          - evaluate optimal timing
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException

from pydantic import BaseModel

from packages.shared.models import (
    MotionChannel,
    MotionSequenceCreate,
    MotionStep,
    MotionStepStatus,
)
from packages.shared.settings import settings


class DecideRequest(BaseModel):
    """Request body for the /decide endpoint."""
    signals: Optional[List[str]] = None
    available_channels: Optional[List[str]] = None

app = FastAPI(title="Motion Engine", version="0.1.0")

# In-memory stores
_sequences: Dict[str, dict] = {}

# ── Default sequence templates ────────────────────────────────────

_DEFAULT_SEQUENCES: Dict[str, List[Dict[str, Any]]] = {
    "sales_outreach": [
        {
            "step_order": 1,
            "channel": MotionChannel.EMAIL.value,
            "action": "send_outreach_email",
            "delay_hours": 0,
            "condition": None,
        },
        {
            "step_order": 2,
            "channel": MotionChannel.EMAIL.value,
            "action": "send_follow_up_email",
            "delay_hours": 48,
            "condition": "no_reply",
        },
        {
            "step_order": 3,
            "channel": MotionChannel.VOICE.value,
            "action": "make_outreach_call",
            "delay_hours": 72,
            "condition": "no_reply",
        },
        {
            "step_order": 4,
            "channel": MotionChannel.SMS.value,
            "action": "send_sms",
            "delay_hours": 120,
            "condition": "no_reply",
        },
        {
            "step_order": 5,
            "channel": MotionChannel.EMAIL.value,
            "action": "escalate_or_close",
            "delay_hours": 168,
            "condition": "no_reply",
        },
    ],
    "customer_follow_up": [
        {
            "step_order": 1,
            "channel": MotionChannel.EMAIL.value,
            "action": "send_thank_you",
            "delay_hours": 0,
            "condition": None,
        },
        {
            "step_order": 2,
            "channel": MotionChannel.SMS.value,
            "action": "send_feedback_request",
            "delay_hours": 24,
            "condition": None,
        },
        {
            "step_order": 3,
            "channel": MotionChannel.EMAIL.value,
            "action": "send_upsell_offer",
            "delay_hours": 168,
            "condition": "positive_sentiment",
        },
    ],
    "urgent_response": [
        {
            "step_order": 1,
            "channel": MotionChannel.VOICE.value,
            "action": "make_immediate_call",
            "delay_hours": 0,
            "condition": None,
        },
        {
            "step_order": 2,
            "channel": MotionChannel.EMAIL.value,
            "action": "send_confirmation_email",
            "delay_hours": 1,
            "condition": None,
        },
    ],
}

# ── Channel priority rules ───────────────────────────────────────

_CHANNEL_PRIORITY: Dict[str, List[str]] = {
    "high_urgency": [
        MotionChannel.VOICE.value,
        MotionChannel.SMS.value,
        MotionChannel.EMAIL.value,
    ],
    "medium_urgency": [
        MotionChannel.EMAIL.value,
        MotionChannel.VOICE.value,
        MotionChannel.SMS.value,
    ],
    "low_urgency": [
        MotionChannel.EMAIL.value,
        MotionChannel.SMS.value,
    ],
    "churn_risk": [
        MotionChannel.VOICE.value,
        MotionChannel.EMAIL.value,
    ],
}


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "motion-engine"}


@app.post("/internal/motion/sequences")
def create_sequence(request: MotionSequenceCreate) -> dict:
    """Create a motion sequence — a timed series of channel actions."""
    sequence_id = f"mseq_{uuid4().hex[:12]}"
    now = datetime.utcnow()

    # Use provided steps or fall back to template
    if request.steps:
        steps = [_step_to_dict(s, now) for s in request.steps]
    elif request.template_id and request.template_id in _DEFAULT_SEQUENCES:
        raw = _DEFAULT_SEQUENCES[request.template_id]
        steps = [_template_step_to_dict(s, now) for s in raw]
    else:
        # Default to sales_outreach
        raw = _DEFAULT_SEQUENCES["sales_outreach"]
        steps = [_template_step_to_dict(s, now) for s in raw]

    # Mark first step as scheduled
    if steps:
        steps[0]["status"] = MotionStepStatus.SCHEDULED.value
        steps[0]["scheduled_at"] = now.isoformat()

    sla_deadline = (
        now + timedelta(hours=request.sla_hours or settings.motion_default_sla_hours)
    )

    seq = {
        "sequence_id": sequence_id,
        "organization_id": request.organization_id,
        "lead_id": request.lead_id,
        "sequence_type": request.template_id or "sales_outreach",
        "status": "active",
        "current_step": 1,
        "total_steps": len(steps),
        "steps": steps,
        "sla_deadline": sla_deadline.isoformat(),
        "priority": request.priority or "normal",
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }
    _sequences[sequence_id] = seq
    return seq


@app.get("/internal/motion/sequences/{sequence_id}")
def get_sequence(sequence_id: str) -> dict:
    """Get the current state of a motion sequence."""
    seq = _sequences.get(sequence_id)
    if not seq:
        raise HTTPException(status_code=404, detail="Sequence not found")
    return seq


@app.post("/internal/motion/sequences/{sequence_id}/advance")
def advance_sequence(sequence_id: str, outcome: Optional[str] = None) -> dict:
    """Advance a motion sequence to the next step.

    The engine evaluates conditions and timing to decide what happens next.
    """
    seq = _sequences.get(sequence_id)
    if not seq:
        raise HTTPException(status_code=404, detail="Sequence not found")

    if seq["status"] in ("completed", "cancelled"):
        raise HTTPException(
            status_code=400,
            detail=f"Sequence is already {seq['status']}",
        )

    now = datetime.utcnow()
    steps = seq["steps"]
    current_idx = seq["current_step"] - 1

    # Mark current step as completed
    if 0 <= current_idx < len(steps):
        steps[current_idx]["status"] = MotionStepStatus.COMPLETED.value
        steps[current_idx]["completed_at"] = now.isoformat()
        if outcome:
            steps[current_idx]["outcome"] = outcome

    # Find next eligible step
    next_idx = current_idx + 1
    if next_idx >= len(steps):
        seq["status"] = "completed"
        seq["updated_at"] = now.isoformat()
        return seq

    next_step = steps[next_idx]

    # Evaluate condition
    if next_step.get("condition"):
        if not _evaluate_condition(next_step["condition"], outcome):
            # Condition not met — skip this step
            next_step["status"] = MotionStepStatus.SKIPPED.value
            next_step["skip_reason"] = (
                f"Condition '{next_step['condition']}' not met "
                f"(outcome: {outcome})"
            )
            # Try to advance further
            seq["current_step"] = next_idx + 1
            seq["updated_at"] = now.isoformat()
            return advance_sequence(sequence_id, outcome)

    # Schedule next step
    next_step["status"] = MotionStepStatus.SCHEDULED.value
    next_step["scheduled_at"] = now.isoformat()
    seq["current_step"] = next_idx + 1
    seq["updated_at"] = now.isoformat()
    return seq


@app.post("/internal/motion/sequences/{sequence_id}/cancel")
def cancel_sequence(sequence_id: str, reason: Optional[str] = None) -> dict:
    """Cancel an active motion sequence."""
    seq = _sequences.get(sequence_id)
    if not seq:
        raise HTTPException(status_code=404, detail="Sequence not found")

    seq["status"] = "cancelled"
    seq["cancel_reason"] = reason
    seq["updated_at"] = datetime.utcnow().isoformat()

    # Mark remaining pending/scheduled steps as cancelled
    for step in seq["steps"]:
        if step["status"] in (
            MotionStepStatus.PENDING.value,
            MotionStepStatus.SCHEDULED.value,
        ):
            step["status"] = MotionStepStatus.SKIPPED.value
            step["skip_reason"] = f"Sequence cancelled: {reason or 'user request'}"

    return seq


@app.get("/internal/motion/sequences")
def list_sequences(organization_id: str) -> dict:
    """List all motion sequences for an organization."""
    results = [
        s for s in _sequences.values()
        if s["organization_id"] == organization_id
    ]
    return {"sequences": results, "total": len(results)}


@app.post("/internal/motion/decide")
def decide_next_action(
    organization_id: str,
    lead_id: str,
    urgency_score: float = 0.5,
    body: Optional[DecideRequest] = None,
) -> dict:
    """Decide the optimal next action, channel, and timing.

    Uses urgency signals and channel availability to recommend the best
    next action for a lead.
    """
    signals = (body.signals if body and body.signals else []) or []
    available = (body.available_channels if body and body.available_channels else None) or [
        MotionChannel.EMAIL.value,
        MotionChannel.VOICE.value,
        MotionChannel.SMS.value,
    ]

    # Determine urgency tier
    if urgency_score >= 0.8 or "high_urgency" in signals or "churn_risk" in signals:
        tier = "high_urgency" if "churn_risk" not in signals else "churn_risk"
    elif urgency_score >= 0.5:
        tier = "medium_urgency"
    else:
        tier = "low_urgency"

    # Select best channel from priority list
    priority_channels = _CHANNEL_PRIORITY.get(tier, _CHANNEL_PRIORITY["medium_urgency"])
    recommended_channel = None
    for ch in priority_channels:
        if ch in available:
            recommended_channel = ch
            break
    if not recommended_channel:
        recommended_channel = available[0] if available else MotionChannel.EMAIL.value

    # Determine timing
    if tier in ("high_urgency", "churn_risk"):
        delay_hours = 0
        timing = "immediate"
    elif tier == "medium_urgency":
        delay_hours = 4
        timing = "within_4_hours"
    else:
        delay_hours = 24
        timing = "next_business_day"

    # Recommend sequence template
    if "churn_risk" in signals:
        recommended_sequence = "urgent_response"
    elif "purchase_intent" in signals or "evaluation_stage" in signals:
        recommended_sequence = "sales_outreach"
    else:
        recommended_sequence = "customer_follow_up"

    return {
        "organization_id": organization_id,
        "lead_id": lead_id,
        "decision": {
            "recommended_channel": recommended_channel,
            "timing": timing,
            "delay_hours": delay_hours,
            "urgency_tier": tier,
            "recommended_sequence": recommended_sequence,
            "reasoning": (
                f"Based on urgency score {urgency_score} and signals "
                f"{signals}, recommending {recommended_channel} "
                f"with {timing} timing."
            ),
        },
    }


@app.post("/internal/motion/evaluate-timing")
def evaluate_timing(
    organization_id: str,
    lead_id: str,
    channel: str,
    timezone: str = "America/Regina",
) -> dict:
    """Evaluate optimal send timing for a specific channel.

    Takes into account business hours, timezone, and channel best practices.
    """
    now = datetime.utcnow()
    hour = now.hour

    # Simple business-hours heuristic
    if channel == MotionChannel.VOICE.value:
        # Best calling windows: 10-11am, 2-4pm local
        if 10 <= hour <= 11 or 14 <= hour <= 16:
            send_at = now
            note = "Within optimal call window"
        else:
            # Schedule for next 10am
            next_window = now.replace(hour=10, minute=0, second=0, microsecond=0)
            if hour >= 10:
                next_window += timedelta(days=1)
            send_at = next_window
            note = "Scheduled for next optimal call window (10:00 AM)"
    elif channel == MotionChannel.EMAIL.value:
        # Best email times: 8-10am, 1-2pm
        if 8 <= hour <= 10 or 13 <= hour <= 14:
            send_at = now
            note = "Within optimal email window"
        else:
            next_window = now.replace(hour=8, minute=30, second=0, microsecond=0)
            if hour >= 8:
                next_window += timedelta(days=1)
            send_at = next_window
            note = "Scheduled for next optimal email window (8:30 AM)"
    elif channel == MotionChannel.SMS.value:
        # SMS: 10am-8pm, avoid early morning
        if 10 <= hour <= 20:
            send_at = now
            note = "Within acceptable SMS window"
        else:
            next_window = now.replace(hour=10, minute=0, second=0, microsecond=0)
            if hour >= 10:
                next_window += timedelta(days=1)
            send_at = next_window
            note = "Scheduled for next acceptable SMS window (10:00 AM)"
    else:
        send_at = now
        note = "No timing restrictions for this channel"

    return {
        "organization_id": organization_id,
        "lead_id": lead_id,
        "channel": channel,
        "timezone": timezone,
        "recommended_send_at": send_at.isoformat(),
        "note": note,
        "is_immediate": send_at == now,
    }


# ── Internal helpers ──────────────────────────────────────────────

def _step_to_dict(step: MotionStep, now: datetime) -> dict:
    """Convert a MotionStep model to an internal dict."""
    return {
        "step_order": step.step_order,
        "channel": step.channel.value,
        "action": step.action,
        "delay_hours": step.delay_hours,
        "condition": step.condition,
        "status": MotionStepStatus.PENDING.value,
        "scheduled_at": None,
        "completed_at": None,
        "outcome": None,
        "skip_reason": None,
    }


def _template_step_to_dict(raw: Dict[str, Any], now: datetime) -> dict:
    """Convert a raw template step to an internal dict."""
    return {
        "step_order": raw["step_order"],
        "channel": raw["channel"],
        "action": raw["action"],
        "delay_hours": raw.get("delay_hours", 0),
        "condition": raw.get("condition"),
        "status": MotionStepStatus.PENDING.value,
        "scheduled_at": None,
        "completed_at": None,
        "outcome": None,
        "skip_reason": None,
    }


def _evaluate_condition(condition: str, outcome: Optional[str]) -> bool:
    """Evaluate whether a step condition is met given the outcome.

    Conditions are simple string tokens evaluated against the outcome
    of the previous step.
    """
    if not condition:
        return True

    # Positive conditions — met when outcome matches
    if condition == "no_reply":
        return outcome in (None, "no_reply", "no_response", "unanswered")
    if condition == "positive_sentiment":
        return outcome in ("positive", "interested", "replied_positive")
    if condition == "negative_sentiment":
        return outcome in ("negative", "declined", "replied_negative")
    if condition == "replied":
        return outcome not in (None, "no_reply", "no_response", "unanswered")

    # Default: treat as met
    return True
