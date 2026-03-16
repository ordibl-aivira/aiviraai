"""Event type constants for the Workforce OS event bus.

All inter-service communication uses typed events routed through
Redis Streams / BullMQ (MVP) or Kafka/NATS (scale-out).
"""

# ── Task lifecycle ──────────────────────────────────────────────
TASK_CREATED = "task.created"
TASK_STARTED = "task.started"
TASK_STEP_COMPLETED = "task.step.completed"
TASK_COMPLETED = "task.completed"
TASK_FAILED = "task.failed"
TASK_ESCALATED = "task.escalated"

# ── Agent lifecycle ─────────────────────────────────────────────
AGENT_DEPLOYED = "agent.deployed"
AGENT_IDLE = "agent.idle"
AGENT_BUSY = "agent.busy"
AGENT_ERROR = "agent.error"

# ── Workflow lifecycle ──────────────────────────────────────────
WORKFLOW_CREATED = "workflow.created"
WORKFLOW_STEP_COMPLETED = "workflow.step.completed"
WORKFLOW_COMPLETED = "workflow.completed"
WORKFLOW_FAILED = "workflow.failed"

# ── Voice / Ordibl ──────────────────────────────────────────────
VOICE_CALL_RECEIVED = "voice.call.received"
VOICE_CALL_ENDED = "voice.call.ended"
VOICE_TRANSCRIPT_RECEIVED = "voice.transcript.received"
VOICE_SYNTHESIS_COMPLETED = "voice.synthesis.completed"

# ── Human-in-the-loop ──────────────────────────────────────────
HUMAN_APPROVAL_REQUESTED = "human.approval.requested"
HUMAN_APPROVAL_GRANTED = "human.approval.granted"
HUMAN_APPROVAL_DENIED = "human.approval.denied"

# ── Memory ──────────────────────────────────────────────────────
MEMORY_EPISODE_STORED = "memory.episode.stored"
MEMORY_KNOWLEDGE_UPDATED = "memory.knowledge.updated"

# ── Customer / CRM ─────────────────────────────────────────────
CUSTOMER_REPLY_RECEIVED = "customer.reply.received"
CUSTOMER_MEETING_BOOKED = "customer.meeting.booked"

# ── Notifications ───────────────────────────────────────────────
NOTIFICATION_EMAIL_SENT = "notification.email.sent"
NOTIFICATION_SMS_SENT = "notification.sms.sent"
