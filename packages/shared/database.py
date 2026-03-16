"""SQLAlchemy ORM models — full Postgres schema for Workforce OS.

Tables
------
organizations       Multi-tenant root entity
users               Platform users (dashboard / API consumers)
agents              Deployed AI worker definitions
tasks               Individual units of work assigned to agents
task_steps           Step-level execution log for each task
workflows           Multi-agent workflow definitions
workflow_steps      Steps within a workflow (DAG nodes)
workflow_executions Running instances of workflows
agent_episodes      Episodic memory — what happened
knowledge_items     Semantic memory — generalised facts (vector-indexed)
procedures          Procedural memory — reusable playbooks
integrations        External system connections per org
audit_log           Immutable compliance / observability trail
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


# ── Organizations ───────────────────────────────────────────────

class Organization(Base):
    __tablename__ = "organizations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(256), nullable=False)
    slug = Column(String(128), nullable=False, unique=True, index=True)
    industry = Column(String(128), nullable=True)
    timezone = Column(String(64), nullable=False, default="UTC")
    settings = Column(JSONB, nullable=False, default=dict)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    users = relationship("User", back_populates="organization")
    agents = relationship("Agent", back_populates="organization")
    workflows = relationship("Workflow", back_populates="organization")


# ── Users ───────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True)
    email = Column(String(320), nullable=False, unique=True, index=True)
    hashed_password = Column(String(256), nullable=False)
    full_name = Column(String(256), nullable=False)
    role = Column(String(64), nullable=False, default="member")  # admin | member | viewer
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    organization = relationship("Organization", back_populates="users")


# ── Agents ──────────────────────────────────────────────────────

class Agent(Base):
    __tablename__ = "agents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True)
    name = Column(String(256), nullable=False)
    role = Column(String(128), nullable=False)  # receptionist | sales | support | billing | ...
    description = Column(Text, nullable=True)
    status = Column(
        Enum("idle", "busy", "error", "disabled", name="agent_status"),
        nullable=False,
        default="idle",
    )
    capabilities = Column(ARRAY(String), nullable=False, default=list)
    tools = Column(ARRAY(String), nullable=False, default=list)
    policies = Column(JSONB, nullable=False, default=dict)
    max_steps = Column(Integer, nullable=False, default=20)
    max_tokens_per_step = Column(Integer, nullable=False, default=4096)
    timeout_seconds = Column(Integer, nullable=False, default=300)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    organization = relationship("Organization", back_populates="agents")
    tasks = relationship("Task", back_populates="agent")
    episodes = relationship("AgentEpisode", back_populates="agent")

    __table_args__ = (
        Index("ix_agents_org_role", "organization_id", "role"),
    )


# ── Tasks ───────────────────────────────────────────────────────

class Task(Base):
    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False, index=True)
    parent_task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=True)
    task_type = Column(String(128), nullable=False)
    goal = Column(Text, nullable=False)
    input = Column(JSONB, nullable=False, default=dict)
    constraints = Column(JSONB, nullable=False, default=dict)
    success_criteria = Column(ARRAY(String), nullable=False, default=list)
    status = Column(
        Enum(
            "pending", "context_loading", "planning", "executing",
            "waiting_for_result", "evaluating", "completed",
            "escalated", "failed",
            name="task_status",
        ),
        nullable=False,
        default="pending",
    )
    result = Column(JSONB, nullable=False, default=dict)
    plan = Column(JSONB, nullable=False, default=list)
    steps_executed = Column(Integer, nullable=False, default=0)
    priority = Column(Integer, nullable=False, default=5)
    deadline = Column(DateTime, nullable=True)
    failure_reason = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    agent = relationship("Agent", back_populates="tasks")
    parent_task = relationship("Task", remote_side=[id])
    steps = relationship("TaskStep", back_populates="task", order_by="TaskStep.step_index")

    __table_args__ = (
        Index("ix_tasks_org_status", "organization_id", "status"),
        Index("ix_tasks_agent_status", "agent_id", "status"),
    )


class TaskStep(Base):
    __tablename__ = "task_steps"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False, index=True)
    step_index = Column(Integer, nullable=False)
    step_name = Column(String(256), nullable=False)
    tool_used = Column(String(256), nullable=True)
    tool_input = Column(JSONB, nullable=False, default=dict)
    tool_output = Column(JSONB, nullable=False, default=dict)
    observation = Column(Text, nullable=False, default="")
    evaluation = Column(JSONB, nullable=False, default=dict)
    duration_ms = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    task = relationship("Task", back_populates="steps")

    __table_args__ = (
        UniqueConstraint("task_id", "step_index", name="uq_task_step_index"),
    )


# ── Workflows ───────────────────────────────────────────────────

class Workflow(Base):
    __tablename__ = "workflows"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True)
    name = Column(String(256), nullable=False)
    description = Column(Text, nullable=True)
    trigger_event = Column(String(128), nullable=True)
    status = Column(
        Enum("pending", "running", "completed", "failed", "paused", name="workflow_status"),
        nullable=False,
        default="pending",
    )
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    organization = relationship("Organization", back_populates="workflows")
    steps = relationship("WorkflowStep", back_populates="workflow", order_by="WorkflowStep.step_id")
    executions = relationship("WorkflowExecution", back_populates="workflow")


class WorkflowStep(Base):
    __tablename__ = "workflow_steps"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id = Column(UUID(as_uuid=True), ForeignKey("workflows.id"), nullable=False, index=True)
    step_id = Column(String(128), nullable=False)
    name = Column(String(256), nullable=False)
    assigned_agent_role = Column(String(128), nullable=False)
    depends_on = Column(ARRAY(String), nullable=False, default=list)
    input_schema = Column(JSONB, nullable=False, default=dict)
    expected_output = Column(JSONB, nullable=False, default=dict)
    timeout_seconds = Column(Integer, nullable=False, default=300)
    requires_approval = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    workflow = relationship("Workflow", back_populates="steps")

    __table_args__ = (
        UniqueConstraint("workflow_id", "step_id", name="uq_workflow_step_id"),
    )


class WorkflowExecution(Base):
    __tablename__ = "workflow_executions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id = Column(UUID(as_uuid=True), ForeignKey("workflows.id"), nullable=False, index=True)
    status = Column(
        Enum("pending", "running", "completed", "failed", "paused", name="wf_exec_status"),
        nullable=False,
        default="pending",
    )
    current_step = Column(String(128), nullable=True)
    step_results = Column(JSONB, nullable=False, default=dict)
    trigger_event = Column(JSONB, nullable=True)
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    workflow = relationship("Workflow", back_populates="executions")

    __table_args__ = (
        Index("ix_wf_exec_workflow_status", "workflow_id", "status"),
    )


# ── Memory: Episodic ────────────────────────────────────────────

class AgentEpisode(Base):
    __tablename__ = "agent_episodes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False, index=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=True, index=True)
    episode_type = Column(
        Enum(
            "task_execution", "customer_interaction", "tool_call",
            "escalation", "approval",
            name="episode_type",
        ),
        nullable=False,
    )
    summary = Column(Text, nullable=False)
    raw_event = Column(JSONB, nullable=False, default=dict)
    participants = Column(ARRAY(String), nullable=False, default=list)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    agent = relationship("Agent", back_populates="episodes")

    __table_args__ = (
        Index("ix_episodes_org_agent", "organization_id", "agent_id"),
        Index("ix_episodes_created", "created_at"),
    )


# ── Memory: Semantic / Knowledge ────────────────────────────────

class KnowledgeItem(Base):
    """Semantic memory stored with vector embedding for retrieval."""
    __tablename__ = "knowledge_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True)
    entity_type = Column(String(128), nullable=False)      # customer | product | policy | ...
    entity_id = Column(String(256), nullable=True)
    fact_text = Column(Text, nullable=False)
    metadata = Column(JSONB, nullable=False, default=dict)
    sensitivity = Column(
        Enum("public", "internal", "confidential", "restricted", name="memory_sensitivity"),
        nullable=False,
        default="internal",
    )
    retention_policy = Column(
        Enum("session", "30_days", "90_days", "12_months", "permanent", name="retention_policy"),
        nullable=False,
        default="12_months",
    )
    visibility = Column(String(128), nullable=False, default="all")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_knowledge_org_entity", "organization_id", "entity_type"),
    )


# ── Memory: Procedural ─────────────────────────────────────────

class Procedure(Base):
    """Reusable playbooks / SOPs that agents follow."""
    __tablename__ = "procedures"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True)
    procedure_id = Column(String(256), nullable=False)
    name = Column(String(256), nullable=False)
    trigger = Column(String(256), nullable=False)
    steps = Column(ARRAY(String), nullable=False, default=list)
    description = Column(Text, nullable=True)
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("organization_id", "procedure_id", "version", name="uq_procedure_version"),
        Index("ix_procedures_trigger", "trigger"),
    )


# ── Integrations ────────────────────────────────────────────────

class Integration(Base):
    __tablename__ = "integrations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True)
    integration_type = Column(String(128), nullable=False)  # crm | calendar | billing | email | ...
    name = Column(String(256), nullable=False)
    credentials_encrypted = Column(Text, nullable=True)     # encrypted at rest
    settings = Column(JSONB, nullable=False, default=dict)
    enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_integrations_org_type", "organization_id", "integration_type"),
    )


# ── Audit Log ───────────────────────────────────────────────────

class AuditLog(Base):
    """Immutable append-only audit trail for compliance."""
    __tablename__ = "audit_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True)
    actor_type = Column(String(64), nullable=False)         # user | agent | system
    actor_id = Column(String(256), nullable=False)
    action = Column(String(256), nullable=False)
    resource_type = Column(String(128), nullable=False)
    resource_id = Column(String(256), nullable=False)
    details = Column(JSONB, nullable=False, default=dict)
    ip_address = Column(String(64), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_audit_org_created", "organization_id", "created_at"),
        Index("ix_audit_resource", "resource_type", "resource_id"),
    )
