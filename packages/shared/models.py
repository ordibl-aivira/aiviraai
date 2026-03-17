"""Pydantic models shared across all Workforce OS services.

These models define the API contracts between services and serve as the
source of truth for request/response shapes throughout the platform.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


# ── Enums ───────────────────────────────────────────────────────

class AgentStatus(str, Enum):
    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"
    DISABLED = "disabled"


class TaskStatus(str, Enum):
    PENDING = "pending"
    CONTEXT_LOADING = "context_loading"
    PLANNING = "planning"
    EXECUTING = "executing"
    WAITING_FOR_RESULT = "waiting_for_result"
    EVALUATING = "evaluating"
    COMPLETED = "completed"
    ESCALATED = "escalated"
    FAILED = "failed"


class WorkflowStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


class MemoryType(str, Enum):
    WORKING = "working"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"


class EpisodeType(str, Enum):
    TASK_EXECUTION = "task_execution"
    CUSTOMER_INTERACTION = "customer_interaction"
    TOOL_CALL = "tool_call"
    ESCALATION = "escalation"
    APPROVAL = "approval"


class MemorySensitivity(str, Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class RetentionPolicy(str, Enum):
    SESSION = "session"
    THIRTY_DAYS = "30_days"
    NINETY_DAYS = "90_days"
    TWELVE_MONTHS = "12_months"
    PERMANENT = "permanent"


# ── Organization ────────────────────────────────────────────────

class OrganizationCreate(BaseModel):
    name: str
    slug: str
    industry: Optional[str] = None
    timezone: str = "UTC"
    settings: Dict[str, Any] = Field(default_factory=dict)


class OrganizationResponse(BaseModel):
    id: str
    name: str
    slug: str
    industry: Optional[str] = None
    timezone: str
    settings: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


# ── Agent ───────────────────────────────────────────────────────

class AgentCreate(BaseModel):
    organization_id: str
    name: str
    role: str
    description: Optional[str] = None
    capabilities: List[str] = Field(default_factory=list)
    tools: List[str] = Field(default_factory=list)
    policies: Dict[str, Any] = Field(default_factory=dict)
    max_steps: int = 20
    max_tokens_per_step: int = 4096
    timeout_seconds: int = 300


class AgentResponse(BaseModel):
    id: str
    organization_id: str
    name: str
    role: str
    description: Optional[str] = None
    status: AgentStatus
    capabilities: List[str]
    tools: List[str]
    policies: Dict[str, Any]
    max_steps: int
    max_tokens_per_step: int
    timeout_seconds: int
    created_at: datetime
    updated_at: datetime


# ── Task ────────────────────────────────────────────────────────

class TaskRequest(BaseModel):
    organization_id: str
    agent_id: str
    task_type: str
    goal: str
    input: Dict[str, Any] = Field(default_factory=dict)
    constraints: Dict[str, Any] = Field(default_factory=dict)
    success_criteria: List[str] = Field(default_factory=list)
    parent_task_id: Optional[str] = None
    depends_on: List[str] = Field(default_factory=list)
    deadline: Optional[datetime] = None
    priority: int = 5


class TaskResponse(BaseModel):
    task_id: str
    status: TaskStatus
    result: Dict[str, Any] = Field(default_factory=dict)
    plan: List[Dict[str, Any]] = Field(default_factory=list)
    steps_executed: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class TaskStepResult(BaseModel):
    step_index: int
    step_name: str
    tool_used: Optional[str] = None
    tool_input: Dict[str, Any] = Field(default_factory=dict)
    tool_output: Dict[str, Any] = Field(default_factory=dict)
    observation: str = ""
    evaluation: Dict[str, Any] = Field(default_factory=dict)
    duration_ms: int = 0


# ── Workflow ────────────────────────────────────────────────────

class WorkflowStepDefinition(BaseModel):
    step_id: str
    name: str
    assigned_agent_role: str
    depends_on: List[str] = Field(default_factory=list)
    input_schema: Dict[str, Any] = Field(default_factory=dict)
    expected_output: Dict[str, Any] = Field(default_factory=dict)
    timeout_seconds: int = 300
    requires_approval: bool = False


class WorkflowCreate(BaseModel):
    organization_id: str
    name: str
    description: Optional[str] = None
    trigger_event: Optional[str] = None
    steps: List[WorkflowStepDefinition]


class WorkflowResponse(BaseModel):
    id: str
    organization_id: str
    name: str
    description: Optional[str] = None
    trigger_event: Optional[str] = None
    status: WorkflowStatus
    steps: List[WorkflowStepDefinition]
    created_at: datetime
    updated_at: datetime


class WorkflowExecutionResponse(BaseModel):
    execution_id: str
    workflow_id: str
    status: WorkflowStatus
    current_step: Optional[str] = None
    step_results: Dict[str, Any] = Field(default_factory=dict)
    started_at: datetime
    completed_at: Optional[datetime] = None


# ── Memory ──────────────────────────────────────────────────────

class WorkingMemoryEntry(BaseModel):
    session_id: str
    agent_id: str
    current_step: Optional[str] = None
    recent_events: List[Dict[str, Any]] = Field(default_factory=list)
    temporary_context: Dict[str, Any] = Field(default_factory=dict)
    ttl_seconds: int = 3600


class EpisodicMemoryCreate(BaseModel):
    agent_id: str
    organization_id: str
    task_id: Optional[str] = None
    episode_type: EpisodeType
    summary: str
    raw_event: Dict[str, Any] = Field(default_factory=dict)
    participants: List[str] = Field(default_factory=list)


class EpisodicMemoryResponse(BaseModel):
    id: str
    agent_id: str
    organization_id: str
    task_id: Optional[str] = None
    episode_type: EpisodeType
    summary: str
    raw_event: Dict[str, Any]
    participants: List[str]
    created_at: datetime


class SemanticMemoryCreate(BaseModel):
    organization_id: str
    entity_type: str
    entity_id: Optional[str] = None
    fact_text: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    sensitivity: MemorySensitivity = MemorySensitivity.INTERNAL
    retention_policy: RetentionPolicy = RetentionPolicy.TWELVE_MONTHS
    visibility: str = "all"


class SemanticMemoryResponse(BaseModel):
    id: str
    organization_id: str
    entity_type: str
    entity_id: Optional[str] = None
    fact_text: str
    metadata: Dict[str, Any]
    sensitivity: MemorySensitivity
    retention_policy: RetentionPolicy
    visibility: str
    relevance_score: Optional[float] = None
    created_at: datetime


class ProceduralMemoryCreate(BaseModel):
    organization_id: str
    procedure_id: str
    name: str
    trigger: str
    steps: List[str]
    description: Optional[str] = None
    version: int = 1


class ProceduralMemoryResponse(BaseModel):
    id: str
    organization_id: str
    procedure_id: str
    name: str
    trigger: str
    steps: List[str]
    description: Optional[str] = None
    version: int
    created_at: datetime
    updated_at: datetime


class MemoryContextPacket(BaseModel):
    """Assembled context sent to the reasoning engine before each step."""
    working: WorkingMemoryEntry
    episodes: List[EpisodicMemoryResponse] = Field(default_factory=list)
    facts: List[SemanticMemoryResponse] = Field(default_factory=list)
    procedures: List[ProceduralMemoryResponse] = Field(default_factory=list)


class MemoryRetrievalRequest(BaseModel):
    organization_id: str
    agent_id: str
    query: str
    memory_types: List[MemoryType] = Field(
        default_factory=lambda: [MemoryType.EPISODIC, MemoryType.SEMANTIC]
    )
    max_results: int = 10
    filters: Dict[str, Any] = Field(default_factory=dict)


# ── Voice / Ordibl ──────────────────────────────────────────────

class TranscriptWebhook(BaseModel):
    call_id: str
    organization_id: str
    speaker: str
    utterance: str
    timestamp: Optional[str] = None


class VoiceCallRequest(BaseModel):
    organization_id: str
    to_number: str
    from_number: Optional[str] = None
    agent_id: str
    purpose: str
    context: Dict[str, Any] = Field(default_factory=dict)


class VoiceCallResponse(BaseModel):
    call_id: str
    status: str
    organization_id: str
    agent_id: str
    started_at: datetime


class VoiceSynthesizeRequest(BaseModel):
    text: str
    voice_id: Optional[str] = None
    language: str = "en-US"
    speed: float = 1.0


class VoiceStreamEvent(BaseModel):
    call_id: str
    event_type: str
    data: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime


# ── Integration ─────────────────────────────────────────────────

class IntegrationConfig(BaseModel):
    organization_id: str
    integration_type: str
    name: str
    credentials: Dict[str, Any] = Field(default_factory=dict)
    settings: Dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True


class ToolCallRequest(BaseModel):
    tool_name: str
    organization_id: str
    agent_id: str
    parameters: Dict[str, Any] = Field(default_factory=dict)


class ToolCallResponse(BaseModel):
    tool_name: str
    status: str
    result: Dict[str, Any] = Field(default_factory=dict)
    reference_id: Optional[str] = None
    duration_ms: int = 0


# ── Auth ────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    email: str
    password: str
    full_name: str
    organization_id: str
    role: str = "member"


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    organization_id: str
    role: str
    is_active: bool
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class LoginRequest(BaseModel):
    email: str
    password: str


# ── Customer ───────────────────────────────────────────────────

class CustomerCreate(BaseModel):
    organization_id: str
    external_ref: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    preferences: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CustomerResponse(BaseModel):
    id: str
    organization_id: str
    external_ref: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    preferences: Dict[str, Any]
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


class CustomerUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


# ── Conversation ───────────────────────────────────────────────

class ConversationCreate(BaseModel):
    organization_id: str
    customer_id: Optional[str] = None
    channel: str  # voice | chat | email | api
    external_id: Optional[str] = None


class ConversationResponse(BaseModel):
    id: str
    organization_id: str
    customer_id: Optional[str] = None
    channel: str
    external_id: Optional[str] = None
    status: str
    started_at: datetime
    ended_at: Optional[datetime] = None


class MessageCreate(BaseModel):
    conversation_id: str
    sender_type: str  # customer | agent | system
    sender_id: Optional[str] = None
    content: Optional[str] = None
    content_json: Optional[Dict[str, Any]] = None


class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    sender_type: str
    sender_id: Optional[str] = None
    content: Optional[str] = None
    content_json: Optional[Dict[str, Any]] = None
    created_at: datetime


# ── Approval ───────────────────────────────────────────────────

class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ApprovalCreate(BaseModel):
    organization_id: str
    task_id: str
    requested_by_agent_id: Optional[str] = None
    reason: Optional[str] = None


class ApprovalResponse(BaseModel):
    id: str
    organization_id: str
    task_id: str
    requested_by_agent_id: Optional[str] = None
    approver_user_id: Optional[str] = None
    status: ApprovalStatus
    reason: Optional[str] = None
    decision_note: Optional[str] = None
    created_at: datetime
    decided_at: Optional[datetime] = None


class ApprovalDecision(BaseModel):
    status: ApprovalStatus  # approved | rejected
    approver_user_id: str
    decision_note: Optional[str] = None


# ── Notification ───────────────────────────────────────────────

class NotificationSendRequest(BaseModel):
    organization_id: str
    channel: str  # email | sms | push | whatsapp
    to: str
    subject: Optional[str] = None
    body: str
    template_id: Optional[str] = None
    template_vars: Dict[str, Any] = Field(default_factory=dict)


class NotificationResponse(BaseModel):
    id: str
    channel: str
    to: str
    status: str
    created_at: datetime


class TemplateRenderRequest(BaseModel):
    template_id: str
    variables: Dict[str, Any] = Field(default_factory=dict)


# ── Event Bus ───────────────────────────────────────────────────

class EventEnvelope(BaseModel):
    event_id: str = Field(default_factory=lambda: f"evt_{uuid4().hex[:12]}")
    event_type: str
    organization_id: str
    source: str
    payload: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    correlation_id: Optional[str] = None
    trace_id: Optional[str] = None


# ── Analytics ───────────────────────────────────────────────────

class AgentMetricsSummary(BaseModel):
    agent_id: str
    organization_id: str
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    average_duration_ms: float = 0.0
    success_rate: float = 0.0
    period_start: datetime
    period_end: datetime
