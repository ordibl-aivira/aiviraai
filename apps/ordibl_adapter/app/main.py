"""Ordibl Adapter — bridge between Ordibl voice infrastructure and Workforce OS.

Ordibl provides the communication infrastructure (telephony, speech
recognition, synthesis, streaming).  This adapter translates Ordibl
events into Workforce OS tasks and routes agent responses back to
Ordibl for speech synthesis.

Endpoints
---------
GET   /health
POST  /webhooks/transcript         — receive real-time transcript from Ordibl
POST  /webhooks/call-status        — receive call lifecycle events
POST  /internal/voice/call         — initiate outbound call via Ordibl
POST  /internal/voice/synthesize   — request speech synthesis
POST  /internal/voice/stream       — open streaming connection
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from fastapi import FastAPI
import httpx

from packages.shared.models import (
    TranscriptWebhook,
    VoiceCallRequest,
    VoiceSynthesizeRequest,
)
from packages.shared.settings import settings

app = FastAPI(title="Ordibl Adapter", version="0.1.0")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "ordibl-adapter"}


# ── Inbound webhooks from Ordibl ────────────────────────────────

@app.post("/webhooks/transcript")
async def transcript_webhook(payload: TranscriptWebhook) -> dict:
    """Receive a real-time transcript chunk from Ordibl.

    Flow:
        Ordibl Telephony → Speech Recognition → This webhook
        → Agent Runtime → AI Response → Speech Synthesis → Call continues
    """
    task_payload = {
        "organization_id": payload.organization_id,
        "agent_id": "agt_receptionist_001",
        "task_type": "receptionist.voice_turn",
        "goal": "Handle inbound voice request and determine next step",
        "input": {
            "call_id": payload.call_id,
            "speaker": payload.speaker,
            "utterance": payload.utterance,
            "customer_name": "Caller",
            "channel": "voice",
        },
        "constraints": {},
        "success_criteria": ["customer intent understood", "next action proposed"],
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{settings.agent_runtime_url}/internal/agent-runtime/tasks/execute",
            json=task_payload,
        )
        response.raise_for_status()
        data = response.json()

    return {
        "status": "processed",
        "call_id": payload.call_id,
        "agent_result": data,
        "speak_text": data.get("result", {}).get(
            "recommended_reply", "Your request has been received."
        ),
    }


@app.post("/webhooks/call-status")
async def call_status_webhook(payload: dict) -> dict:
    """Receive call lifecycle events (ringing, answered, ended, etc.)."""
    return {
        "status": "acknowledged",
        "call_id": payload.get("call_id"),
        "event": payload.get("event"),
    }


# ── Outbound voice operations ──────────────────────────────────

@app.post("/internal/voice/call")
async def initiate_call(request: VoiceCallRequest) -> dict:
    """Initiate an outbound voice call via Ordibl telephony API.

    In production this calls the Ordibl POST /voice/call endpoint.
    """
    call_id = f"call_{uuid4().hex[:12]}"
    return {
        "call_id": call_id,
        "status": "initiated",
        "organization_id": request.organization_id,
        "agent_id": request.agent_id,
        "to_number": request.to_number,
        "purpose": request.purpose,
        "started_at": datetime.utcnow().isoformat(),
    }


@app.post("/internal/voice/synthesize")
async def synthesize_speech(request: VoiceSynthesizeRequest) -> dict:
    """Request speech synthesis from Ordibl.

    In production this calls the Ordibl POST /voice/synthesize endpoint
    and returns an audio stream URL.
    """
    return {
        "status": "synthesized",
        "text": request.text,
        "voice_id": request.voice_id or "default",
        "language": request.language,
        "audio_url": f"https://ordibl.ai/audio/{uuid4().hex[:12]}.wav",
        "duration_ms": len(request.text) * 60,  # rough estimate
    }


@app.post("/internal/voice/stream")
async def open_stream(payload: dict) -> dict:
    """Open a bidirectional voice stream (stub).

    In production this establishes a WebSocket connection to Ordibl's
    POST /voice/stream endpoint for real-time audio streaming.
    """
    stream_id = f"stream_{uuid4().hex[:12]}"
    return {
        "stream_id": stream_id,
        "status": "ready",
        "call_id": payload.get("call_id"),
        "websocket_url": f"wss://ordibl.ai/stream/{stream_id}",
    }
