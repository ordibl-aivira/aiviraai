"""Event type constants for the Workforce OS event bus.

All inter-service communication uses typed events routed through
Redis Streams / BullMQ (MVP) or Kafka/NATS (scale-out).

Event envelope schema (see models.EventEnvelope):
    event_id, event_type, organization_id, source, timestamp,
    payload, correlation_id, trace_id

Recommended partitions:
    organization_id for tenant isolation;
    task_id and workflow_id in payload for correlation.

Producer services:
    API Gateway, Ordibl Adapter, Agent Runtime, Workflow Engine

Consumer services:
    Analytics, Task Service, Memory Service, Specialist Workers
"""

# ── Task lifecycle ──────────────────────────────────────────────
TASK_CREATED = "task.created"
TASK_STARTED = "task.started"
TASK_STEP_COMPLETED = "task.step.completed"
TASK_COMPLETED = "task.completed"
TASK_FAILED = "task.failed"
TASK_BLOCKED = "task.blocked"
TASK_ESCALATED = "task.escalated"

# ── Agent lifecycle ─────────────────────────────────────────────
AGENT_DEPLOYED = "agent.deployed"
AGENT_IDLE = "agent.idle"
AGENT_BUSY = "agent.busy"
AGENT_ERROR = "agent.error"

# ── Workflow lifecycle ──────────────────────────────────────────
WORKFLOW_CREATED = "workflow.created"
WORKFLOW_ADVANCED = "workflow.advanced"
WORKFLOW_STEP_COMPLETED = "workflow.step.completed"
WORKFLOW_COMPLETED = "workflow.completed"
WORKFLOW_FAILED = "workflow.failed"

# ── Voice / Ordibl ──────────────────────────────────────────────
VOICE_CALL_STARTED = "voice.call.started"
VOICE_CALL_RECEIVED = "voice.call.received"
VOICE_CALL_ENDED = "voice.call.ended"
VOICE_TRANSCRIPT_RECEIVED = "voice.transcript.received"
VOICE_SYNTHESIS_COMPLETED = "voice.synthesis.completed"

# ── Approval (human-in-the-loop) ───────────────────────────────
APPROVAL_REQUESTED = "approval.requested"
APPROVAL_APPROVED = "approval.approved"
APPROVAL_REJECTED = "approval.rejected"
# Legacy aliases
HUMAN_APPROVAL_REQUESTED = APPROVAL_REQUESTED
HUMAN_APPROVAL_GRANTED = APPROVAL_APPROVED
HUMAN_APPROVAL_DENIED = APPROVAL_REJECTED

# ── Conversation ────────────────────────────────────────────────
CONVERSATION_STARTED = "conversation.started"
CONVERSATION_MESSAGE_RECEIVED = "conversation.message.received"
CONVERSATION_MESSAGE_SENT = "conversation.message.sent"
CONVERSATION_ENDED = "conversation.ended"

# ── Memory ──────────────────────────────────────────────────────
MEMORY_EPISODE_STORED = "memory.episode.stored"
MEMORY_KNOWLEDGE_UPDATED = "memory.knowledge.updated"

# ── Customer / CRM ─────────────────────────────────────────────
CUSTOMER_REPLY_RECEIVED = "customer.reply.received"
CUSTOMER_MEETING_BOOKED = "customer.meeting.booked"

# ── Notifications ───────────────────────────────────────────────
NOTIFICATION_EMAIL_SENT = "notification.email.sent"
NOTIFICATION_SMS_SENT = "notification.sms.sent"
