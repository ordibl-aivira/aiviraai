"""Per-agent and per-organization AI configuration.

This module provides the configuration layer that allows each organization
to customize how generative AI behaves for their agents.  It sits between
the platform-level defaults in ``settings.py`` and the per-request
overrides in the AI client.

Configuration hierarchy (highest priority wins):
    1. Per-request overrides (passed to ``ai_client.complete()``)
    2. Per-agent config (stored in ``agents.config`` JSONB column)
    3. Per-organization config (stored in ``organizations`` table)
    4. Platform defaults (``settings.py``)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from packages.shared.settings import settings


@dataclass
class AgentAIConfig:
    """Resolved AI configuration for a specific agent execution."""

    # Model selection
    model: str = ""
    fallback_model: str = ""
    embedding_model: str = ""
    provider: str = ""

    # Behaviour
    temperature: float = 0.3
    max_completion_tokens: int = 4096
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0

    # Guardrails
    max_steps: int = 20
    max_tokens_per_task: int = 32_000
    max_tool_calls_per_step: int = 5
    timeout_seconds: int = 300
    max_retries: int = 3

    # Features
    enable_chain_of_thought: bool = True
    enable_structured_output: bool = True
    enable_tool_use: bool = True
    enable_memory_retrieval: bool = True
    enable_content_filter: bool = True

    # Permissions
    allowed_tools: List[str] = field(default_factory=list)
    blocked_tools: List[str] = field(default_factory=list)

    def is_tool_allowed(self, tool_name: str) -> bool:
        """Check if a tool is allowed for this agent."""
        if self.blocked_tools and tool_name in self.blocked_tools:
            return False
        if self.allowed_tools:
            return tool_name in self.allowed_tools
        return True  # no allow-list means all tools are allowed


def resolve_ai_config(
    agent_config: Optional[Dict[str, Any] | str] = None,
    org_config: Optional[Dict[str, Any]] = None,
) -> AgentAIConfig:
    """Resolve the effective AI configuration by merging layers.

    Parameters
    ----------
    agent_config:
        The ``config`` JSONB from the agent record, or a role name
        string (e.g. ``"receptionist"``) to load the role preset.
    org_config:
        Organization-level AI overrides (if any).

    Returns
    -------
    AgentAIConfig with all layers merged.
    """
    # If agent_config is a role name string, resolve to the preset dict
    if isinstance(agent_config, str):
        agent_config = ROLE_PRESETS.get(agent_config, {})

    # Start with platform defaults
    cfg = AgentAIConfig(
        model=settings.ai_primary_model,
        fallback_model=settings.ai_fallback_model,
        embedding_model=settings.ai_embedding_model,
        provider=settings.ai_provider,
        temperature=settings.ai_temperature,
        max_completion_tokens=settings.ai_max_completion_tokens,
        max_tokens_per_task=settings.ai_max_tokens_per_task,
        max_tool_calls_per_step=settings.ai_max_tool_calls_per_step,
        max_retries=settings.ai_max_retries,
        timeout_seconds=settings.default_agent_timeout_seconds,
        max_steps=settings.default_max_agent_steps,
        enable_chain_of_thought=settings.ai_enable_chain_of_thought,
        enable_structured_output=settings.ai_enable_structured_output,
        enable_tool_use=settings.ai_enable_tool_use,
        enable_content_filter=settings.ai_enable_content_filter,
    )

    # Layer 2: org-level overrides
    if org_config:
        _apply_overrides(cfg, org_config)

    # Layer 3: agent-level overrides (highest priority)
    if agent_config:
        _apply_overrides(cfg, agent_config)

    return cfg


def _apply_overrides(cfg: AgentAIConfig, overrides: Dict[str, Any]) -> None:
    """Apply a dict of overrides onto an AgentAIConfig."""
    field_names = {f for f in cfg.__dataclass_fields__}
    for key, value in overrides.items():
        if key in field_names and value is not None:
            setattr(cfg, key, value)


# ── Preset configurations for common agent roles ────────────────

ROLE_PRESETS: Dict[str, Dict[str, Any]] = {
    "receptionist": {
        "temperature": 0.3,
        "max_steps": 10,
        "max_tokens_per_task": 16_000,
        "enable_chain_of_thought": True,
        "allowed_tools": [
            "calendar.check_availability",
            "calendar.create_event",
            "voice.transfer",
            "crm.create_task",
            "notification.send_sms",
        ],
    },
    "sales": {
        "temperature": 0.4,
        "max_steps": 15,
        "max_tokens_per_task": 24_000,
        "enable_chain_of_thought": True,
        "allowed_tools": [
            "crm.get_lead",
            "crm.update_lead",
            "crm.create_task",
            "email.send",
            "email.draft",
            "calendar.check_availability",
            "calendar.create_event",
        ],
    },
    "scheduling": {
        "temperature": 0.1,
        "max_steps": 8,
        "max_tokens_per_task": 12_000,
        "enable_chain_of_thought": False,
        "allowed_tools": [
            "calendar.check_availability",
            "calendar.create_event",
            "notification.send_sms",
        ],
    },
    "support": {
        "temperature": 0.3,
        "max_steps": 15,
        "max_tokens_per_task": 24_000,
        "enable_chain_of_thought": True,
        "allowed_tools": [
            "crm.get_lead",
            "crm.create_task",
            "email.send",
            "notification.send_sms",
        ],
    },
    "operations": {
        "temperature": 0.2,
        "max_steps": 25,
        "max_tokens_per_task": 32_000,
        "enable_chain_of_thought": True,
        "allowed_tools": [
            "crm.get_lead",
            "crm.update_lead",
            "calendar.check_availability",
            "workflow.delegate",
        ],
    },
    "compliance": {
        "temperature": 0.0,  # maximally deterministic
        "max_steps": 10,
        "max_tokens_per_task": 16_000,
        "enable_chain_of_thought": True,
        "blocked_tools": [
            "billing.create_invoice",
            "voice.call",
        ],
    },
    "orchestrator": {
        "temperature": 0.2,
        "max_steps": 30,
        "max_tokens_per_task": 48_000,
        "enable_chain_of_thought": True,
        "allowed_tools": [
            "workflow.delegate",
        ],
    },
}


def get_role_preset(role: str) -> AgentAIConfig:
    """Get the AI configuration preset for a given agent role.

    Returns a fully resolved ``AgentAIConfig`` with the role's
    preset values merged on top of platform defaults.
    """
    return resolve_ai_config(agent_config=ROLE_PRESETS.get(role, {}))
