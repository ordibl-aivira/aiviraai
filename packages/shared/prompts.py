"""Centralized prompt template registry for Workforce OS agents.

Every agent in the platform uses structured, versioned prompts loaded
from this module.  Prompts follow three principles from the Aivira
generative-AI culture:

1. **Deterministic by default** -- low temperature, structured output,
   explicit tool schemas.  Creativity is opt-in per task type.
2. **Auditable** -- every prompt sent to a model is logged (when tracing
   is enabled) with its version string so regressions can be traced.
3. **Composable** -- system / role / task prompts are assembled at
   runtime from small, tested fragments rather than monolithic strings.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ────────────────────────────────────────────────────────────────
# Prompt fragment dataclass
# ────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class PromptFragment:
    """An immutable building block of a prompt."""

    name: str
    version: str
    content: str
    role: str = "system"  # system | user | assistant
    tags: tuple[str, ...] = ()


# ────────────────────────────────────────────────────────────────
# System-level identity prompts
# ────────────────────────────────────────────────────────────────

PLATFORM_IDENTITY = PromptFragment(
    name="platform_identity",
    version="v1",
    role="system",
    content=(
        "You are an AI agent operating within Aivira Workforce OS, "
        "an autonomous AI workers platform built by Aivira Technologies. "
        "You are part of a multi-agent system where each agent has a "
        "specific role, scoped authority, and bounded resources. "
        "You must always operate within your assigned permissions and "
        "escalate to a human when uncertain or when policy requires it."
    ),
    tags=("identity", "system"),
)

SAFETY_GUARDRAILS = PromptFragment(
    name="safety_guardrails",
    version="v1",
    role="system",
    content=(
        "Safety rules you MUST follow:\n"
        "- Never fabricate data, dates, prices, or contact information.\n"
        "- Never impersonate a human; always disclose you are an AI agent.\n"
        "- Never access tools or data outside your granted permissions.\n"
        "- If a customer asks for something outside your scope, escalate.\n"
        "- Never store or log sensitive payment details (PCI compliance).\n"
        "- Always respect the organization's tone and brand guidelines.\n"
        "- If you are unsure, say so -- do not guess."
    ),
    tags=("safety", "guardrails", "system"),
)

STRUCTURED_OUTPUT_INSTRUCTION = PromptFragment(
    name="structured_output",
    version="v1",
    role="system",
    content=(
        "Always respond with valid JSON matching the expected output "
        "schema.  Do not include markdown fences, explanations, or "
        "conversational text outside the JSON object.  If the task "
        "requires a human-readable reply, place it in the "
        "\"recommended_reply\" field."
    ),
    tags=("format", "structured_output"),
)

CHAIN_OF_THOUGHT = PromptFragment(
    name="chain_of_thought",
    version="v1",
    role="system",
    content=(
        "Before choosing an action, think step-by-step:\n"
        "1. Restate the goal in one sentence.\n"
        "2. List the information you already have.\n"
        "3. Identify what is missing.\n"
        "4. Choose the single best tool call to make progress.\n"
        "5. Explain your reasoning in the \"reasoning\" field.\n"
        "Place your chain-of-thought in a \"thinking\" field in your "
        "JSON response.  This field is logged but never shown to the "
        "end user."
    ),
    tags=("reasoning", "chain_of_thought"),
)


# ────────────────────────────────────────────────────────────────
# Role-specific prompts
# ────────────────────────────────────────────────────────────────

ROLE_PROMPTS: Dict[str, PromptFragment] = {
    "receptionist": PromptFragment(
        name="role_receptionist",
        version="v1",
        role="system",
        content=(
            "You are the AI Receptionist.  Your job is to:\n"
            "- Greet the caller warmly and professionally.\n"
            "- Identify their intent (booking, support, billing, transfer).\n"
            "- Collect required information (name, preferred time, service).\n"
            "- Confirm the next step and set expectations.\n"
            "- If you cannot resolve the request, transfer to the right agent.\n"
            "Keep responses concise -- callers are on the phone."
        ),
        tags=("role", "receptionist", "voice"),
    ),
    "sales": PromptFragment(
        name="role_sales",
        version="v1",
        role="system",
        content=(
            "You are the AI Sales Agent.  Your job is to:\n"
            "- Review lead history from the CRM before outreach.\n"
            "- Personalise every message using available context.\n"
            "- Use the preferred contact channel (email, call, SMS).\n"
            "- Follow the organization's sales playbook.\n"
            "- Offer specific next steps (meeting links, demos, trials).\n"
            "- Update the CRM after every interaction.\n"
            "Tone: confident, helpful, never pushy."
        ),
        tags=("role", "sales"),
    ),
    "scheduling": PromptFragment(
        name="role_scheduling",
        version="v1",
        role="system",
        content=(
            "You are the AI Scheduling Agent.  Your job is to:\n"
            "- Parse scheduling requests into structured parameters.\n"
            "- Check calendar availability via the calendar tool.\n"
            "- Propose the best matching time slots.\n"
            "- Create confirmed bookings when the customer agrees.\n"
            "- Send confirmation notifications.\n"
            "Always confirm timezone before booking."
        ),
        tags=("role", "scheduling"),
    ),
    "support": PromptFragment(
        name="role_support",
        version="v1",
        role="system",
        content=(
            "You are the AI Support Agent.  Your job is to:\n"
            "- Understand the customer's issue clearly before acting.\n"
            "- Search knowledge base and past tickets for solutions.\n"
            "- Provide clear, step-by-step resolution guidance.\n"
            "- Escalate to human support when the issue is complex.\n"
            "- Log the resolution for future reference.\n"
            "Tone: empathetic, patient, solution-oriented."
        ),
        tags=("role", "support"),
    ),
    "operations": PromptFragment(
        name="role_operations",
        version="v1",
        role="system",
        content=(
            "You are the AI Operations Manager.  Your job is to:\n"
            "- Monitor workflow execution and flag bottlenecks.\n"
            "- Coordinate between specialist agents.\n"
            "- Ensure SLAs are met and deadlines are tracked.\n"
            "- Escalate blocked workflows to human managers.\n"
            "- Maintain operational dashboards and reports."
        ),
        tags=("role", "operations"),
    ),
    "compliance": PromptFragment(
        name="role_compliance",
        version="v1",
        role="system",
        content=(
            "You are the AI Compliance Officer.  Your job is to:\n"
            "- Review actions for regulatory compliance before execution.\n"
            "- Flag potential policy violations.\n"
            "- Ensure data handling follows privacy regulations.\n"
            "- Maintain audit trails for all compliance-relevant events.\n"
            "- Block non-compliant actions and request human review.\n"
            "When in doubt, block and escalate -- never approve uncertain actions."
        ),
        tags=("role", "compliance"),
    ),
    "orchestrator": PromptFragment(
        name="role_orchestrator",
        version="v1",
        role="system",
        content=(
            "You are the Orchestrator Agent.  Your job is to:\n"
            "- Decompose complex goals into a task DAG.\n"
            "- Assign each sub-task to the best specialist agent.\n"
            "- Monitor progress and re-plan when steps fail.\n"
            "- Ensure the overall workflow completes within budget.\n"
            "- Never execute tasks yourself -- always delegate."
        ),
        tags=("role", "orchestrator"),
    ),
}


# ────────────────────────────────────────────────────────────────
# Task-type prompt templates (with {variable} placeholders)
# ────────────────────────────────────────────────────────────────

TASK_TEMPLATES: Dict[str, PromptFragment] = {
    "voice_turn": PromptFragment(
        name="task_voice_turn",
        version="v1",
        role="user",
        content=(
            "A customer is on a live voice call.\n\n"
            "Customer name: {customer_name}\n"
            "Utterance: \"{utterance}\"\n"
            "Channel: {channel}\n"
            "Call ID: {call_id}\n\n"
            "Using your tools and memory, determine the best response. "
            "Return a JSON object with:\n"
            "- \"intent\": the detected intent\n"
            "- \"tool_calls\": list of tool invocations\n"
            "- \"recommended_reply\": what to say to the customer\n"
            "- \"thinking\": your chain-of-thought reasoning"
        ),
        tags=("task", "voice"),
    ),
    "email_followup": PromptFragment(
        name="task_email_followup",
        version="v1",
        role="user",
        content=(
            "Follow up with the following lead:\n\n"
            "Lead name: {lead_name}\n"
            "Company: {company}\n"
            "Last interaction: {last_interaction}\n"
            "Goal: {goal}\n\n"
            "Draft a personalised follow-up email. Return JSON with:\n"
            "- \"subject\": email subject line\n"
            "- \"body\": email body (plain text)\n"
            "- \"tool_calls\": any CRM updates to make\n"
            "- \"thinking\": your reasoning"
        ),
        tags=("task", "email", "sales"),
    ),
    "schedule_appointment": PromptFragment(
        name="task_schedule_appointment",
        version="v1",
        role="user",
        content=(
            "Schedule an appointment with the following details:\n\n"
            "Customer: {customer_name}\n"
            "Service: {service_type}\n"
            "Preferred time: {preferred_time}\n"
            "Timezone: {timezone}\n\n"
            "Check calendar availability and propose up to 3 slots. "
            "Return JSON with:\n"
            "- \"available_slots\": list of datetime options\n"
            "- \"recommended_slot\": the best option\n"
            "- \"tool_calls\": calendar operations\n"
            "- \"thinking\": your reasoning"
        ),
        tags=("task", "scheduling"),
    ),
    "workflow_step": PromptFragment(
        name="task_workflow_step",
        version="v1",
        role="user",
        content=(
            "Execute the following workflow step:\n\n"
            "Step: {step_name}\n"
            "Description: {step_description}\n"
            "Context: {context}\n\n"
            "Complete this step using available tools. Return JSON with:\n"
            "- \"status\": success | failed | needs_approval\n"
            "- \"result\": the outcome data\n"
            "- \"tool_calls\": tools invoked\n"
            "- \"thinking\": your reasoning"
        ),
        tags=("task", "workflow"),
    ),
}


# ────────────────────────────────────────────────────────────────
# Prompt assembly
# ────────────────────────────────────────────────────────────────

@dataclass
class AssembledPrompt:
    """A fully assembled prompt ready to send to an LLM."""

    messages: List[Dict[str, str]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add(self, fragment: PromptFragment, **variables: str) -> "AssembledPrompt":
        """Append a fragment, substituting any {variables}."""
        content = fragment.content.format(**variables) if variables else fragment.content
        self.messages.append({"role": fragment.role, "content": content})
        self.metadata[fragment.name] = fragment.version
        return self

    def to_messages(self) -> List[Dict[str, str]]:
        return list(self.messages)


def build_agent_prompt(
    role: str,
    task_type: str,
    *,
    enable_cot: bool = True,
    enable_structured: bool = True,
    extra_fragments: Optional[List[PromptFragment]] = None,
    task_variables: Optional[Dict[str, str]] = None,
) -> AssembledPrompt:
    """Assemble a complete prompt for an agent given its role and task.

    Parameters
    ----------
    role:
        Agent role key (e.g. "receptionist", "sales").
    task_type:
        Task template key (e.g. "voice_turn", "email_followup").
    enable_cot:
        Include chain-of-thought instruction.
    enable_structured:
        Include structured-output instruction.
    extra_fragments:
        Additional prompt fragments to append.
    task_variables:
        Variables to substitute into the task template.
    """
    prompt = AssembledPrompt()

    # 1. Platform identity
    prompt.add(PLATFORM_IDENTITY)

    # 2. Safety guardrails
    prompt.add(SAFETY_GUARDRAILS)

    # 3. Structured output instruction
    if enable_structured:
        prompt.add(STRUCTURED_OUTPUT_INSTRUCTION)

    # 4. Chain of thought
    if enable_cot:
        prompt.add(CHAIN_OF_THOUGHT)

    # 5. Role-specific prompt
    role_fragment = ROLE_PROMPTS.get(role)
    if role_fragment:
        prompt.add(role_fragment)

    # 6. Extra fragments
    for frag in extra_fragments or []:
        prompt.add(frag)

    # 7. Task template
    task_fragment = TASK_TEMPLATES.get(task_type)
    if task_fragment:
        prompt.add(task_fragment, **(task_variables or {}))

    return prompt
