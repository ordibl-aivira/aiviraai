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


# ══════════════════════════════════════════════════════════════════
# Cognitive → Execution Stack models
# ══════════════════════════════════════════════════════════════════

# ── Research Agent (Thinking Layer) ──────────────────────────────

class ResearchType(str, Enum):
    LEAD_ENRICHMENT = "lead_enrichment"
    MARKET_RESEARCH = "market_research"
    COMPETITOR_ANALYSIS = "competitor_analysis"
    CUSTOMER_PROFILING = "customer_profiling"
    SIGNAL_DETECTION = "signal_detection"


class ResearchRequest(BaseModel):
    """Request to the Research Agent for intelligence gathering."""
    organization_id: str
    research_type: ResearchType
    query: str
    target: Optional[str] = None  # company name, lead name, industry
    data_sources: List[str] = Field(
        default_factory=lambda: ["crm", "memory", "public_data"]
    )
    max_results: int = 10
    context: Dict[str, Any] = Field(default_factory=dict)


class LeadIntelligence(BaseModel):
    """Structured intelligence object produced by the Research Agent."""
    lead_name: str
    company: Optional[str] = None
    size: Optional[str] = None
    industry: Optional[str] = None
    pain_points: List[str] = Field(default_factory=list)
    decision_maker: Optional[str] = None
    recommended_pitch: Optional[str] = None
    contact_channels: List[str] = Field(default_factory=list)
    urgency_score: float = 0.5  # 0.0–1.0
    intent_signals: List[str] = Field(default_factory=list)


class ResearchResponse(BaseModel):
    """Response from the Research Agent."""
    research_id: str
    organization_id: str
    research_type: ResearchType
    status: str  # completed | partial | failed
    intelligence: Dict[str, Any] = Field(default_factory=dict)
    lead_intelligence: Optional[LeadIntelligence] = None
    sources_consulted: List[str] = Field(default_factory=list)
    confidence_score: float = 0.0
    created_at: datetime


# ── Content Agent (Thinking Layer) ───────────────────────────────

class ContentType(str, Enum):
    EMAIL = "email"
    CALL_SCRIPT = "call_script"
    SMS = "sms"
    PROPOSAL = "proposal"
    FOLLOW_UP = "follow_up"
    MARKETING_CAMPAIGN = "marketing_campaign"
    MEETING_AGENDA = "meeting_agenda"


class ContentRequest(BaseModel):
    """Request to the Content Agent for content generation."""
    organization_id: str
    content_type: ContentType
    purpose: str
    recipient: Optional[str] = None
    tone: str = "professional"
    intelligence: Dict[str, Any] = Field(default_factory=dict)  # from Research Agent
    context: Dict[str, Any] = Field(default_factory=dict)
    template_id: Optional[str] = None
    max_length: Optional[int] = None
    language: str = "en"


class GeneratedContent(BaseModel):
    """A single piece of generated content."""
    content_type: ContentType
    subject: Optional[str] = None
    body: str
    call_to_action: Optional[str] = None
    personalization_fields: Dict[str, str] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ContentResponse(BaseModel):
    """Response from the Content Agent."""
    content_id: str
    organization_id: str
    content_type: ContentType
    status: str  # generated | failed
    content: Optional[GeneratedContent] = None
    variants: List[GeneratedContent] = Field(default_factory=list)
    intelligence_used: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


# ── Motion Engine (Decision & Planning Layer) ────────────────────

class MotionChannel(str, Enum):
    EMAIL = "email"
    VOICE = "voice"
    SMS = "sms"
    WHATSAPP = "whatsapp"
    API = "api"


class MotionStepStatus(str, Enum):
    PENDING = "pending"
    SCHEDULED = "scheduled"
    EXECUTING = "executing"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"


class MotionStep(BaseModel):
    """A single step in a motion sequence."""
    step_order: int  # 1, 2, 3, etc.
    channel: MotionChannel
    action: str  # send_email, make_call, send_sms, etc.
    delay_hours: int = 0  # hours to wait before executing (0, 48, 120, etc.)
    condition: Optional[str] = None  # "no_reply", "positive_sentiment", etc.
    content_type: Optional[ContentType] = None
    fallback_action: Optional[str] = None
    max_retries: int = 1
    timeout_hours: int = 24


class MotionSequenceCreate(BaseModel):
    """Create a timed action sequence (the decision brain)."""
    organization_id: str
    name: Optional[str] = None
    description: Optional[str] = None
    lead_id: Optional[str] = None  # target lead for the sequence
    template_id: Optional[str] = None  # e.g. "sales_outreach", "urgent_response"
    steps: Optional[List[MotionStep]] = None  # auto-generated from template if None
    priority: Optional[int] = 5
    sla_hours: Optional[int] = None
    context: Dict[str, Any] = Field(default_factory=dict)


class MotionSequenceResponse(BaseModel):
    """Response for a motion sequence."""
    sequence_id: str
    organization_id: str
    name: str
    status: str  # active | paused | completed | cancelled
    current_step: Optional[str] = None
    steps: List[MotionStep]
    step_results: Dict[str, Any] = Field(default_factory=dict)
    started_at: Optional[datetime] = None
    next_action_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime


# ── Execution Engine (Execution Layer) ───────────────────────────

class ExecutionActionType(str, Enum):
    SEND_EMAIL = "send_email"
    MAKE_CALL = "make_call"
    SEND_SMS = "send_sms"
    UPDATE_CRM = "update_crm"
    CREATE_INVOICE = "create_invoice"
    TRIGGER_PAYMENT = "trigger_payment"
    SCHEDULE_MEETING = "schedule_meeting"
    SEND_WHATSAPP = "send_whatsapp"
    WEBHOOK = "webhook"


class ExecutionRequest(BaseModel):
    """Request to the Execution Engine to perform a real-world action."""
    organization_id: str
    action_type: ExecutionActionType
    parameters: Dict[str, Any] = Field(default_factory=dict)  # action-specific params
    content: Any = None  # content from Content Agent
    recipient: Optional[str] = None  # who to act on
    idempotency_key: Optional[str] = None
    update_memory: bool = False  # whether to persist to memory service
    context: Dict[str, Any] = Field(default_factory=dict)


class ExecutionResult(BaseModel):
    """Result from the Execution Engine after performing an action."""
    execution_id: str
    organization_id: str
    action_type: ExecutionActionType
    status: str  # success | failed | pending | retrying
    result: Dict[str, Any] = Field(default_factory=dict)
    external_ref: Optional[str] = None  # external system reference
    duration_ms: int = 0
    retries: int = 0
    error: Optional[str] = None
    executed_at: datetime


# ── Full Pipeline (Cognitive → Execution) ────────────────────────

class CognitivePipelineRequest(BaseModel):
    """End-to-end pipeline: Research → Content → Motion → Execute."""
    organization_id: str
    trigger_type: str  # e.g. "new_lead", "inbound_call", "form_submission"
    trigger_data: Dict[str, Any] = Field(default_factory=dict)
    lead_id: Optional[str] = None  # target lead
    context: Dict[str, Any] = Field(default_factory=dict)


class CognitivePipelineResponse(BaseModel):
    """Response from the full cognitive pipeline."""
    pipeline_id: str
    organization_id: str
    status: str  # running | completed | failed
    research: Optional[ResearchResponse] = None
    content: List[ContentResponse] = Field(default_factory=list)
    motion_sequence: Optional[MotionSequenceResponse] = None
    executions: List[ExecutionResult] = Field(default_factory=list)
    created_at: datetime
