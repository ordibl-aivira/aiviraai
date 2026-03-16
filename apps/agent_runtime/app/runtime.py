"""LangGraph-based agent reasoning loop for Workforce OS.

Implements the full 9-step reasoning cycle:

    Goal intake
    -> Context assembly
    -> Planning
    -> Tool selection
    -> Action execution
    -> Observation
    -> Reflection / evaluation
    -> Memory write
    -> Continue or terminate

The graph compiles to a LangGraph StateGraph when the library is
available, and falls back to a plain sequential executor otherwise.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, TypedDict
from uuid import uuid4

try:
    from langgraph.graph import END, StateGraph
except Exception:  # pragma: no cover – optional dependency
    StateGraph = None  # type: ignore[assignment, misc]
    END = None


# ────────────────────────────────────────────────────────────────
# Agent State
# ────────────────────────────────────────────────────────────────

class AgentState(TypedDict, total=False):
    # identifiers
    task_id: str
    organization_id: str
    agent_id: str
    task_type: str
    goal: str
    input: Dict[str, Any]
    constraints: Dict[str, Any]
    success_criteria: List[str]

    # runtime state-machine phase
    phase: str  # IDLE → CONTEXT_LOADING → PLANNING → EXECUTING → ...

    # context assembly
    working_context: Dict[str, Any]
    retrieved_memories: List[Dict[str, Any]]
    procedures: List[Dict[str, Any]]

    # planning
    plan: List[Dict[str, Any]]
    current_step_index: int

    # action
    selected_tool: Optional[str]
    tool_input: Optional[Dict[str, Any]]
    tool_result: Optional[Dict[str, Any]]

    # observation & reflection
    observations: List[Dict[str, Any]]
    evaluation: Dict[str, Any]
    step_history: List[Dict[str, Any]]

    # termination
    completed: bool
    failure_reason: Optional[str]
    result: Dict[str, Any]
    steps_executed: int
    max_steps: int


# ────────────────────────────────────────────────────────────────
# Step 1 – Goal intake (already in state from caller)
# ────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────
# Step 2 – Context assembly
# ────────────────────────────────────────────────────────────────

def load_context(state: AgentState) -> AgentState:
    """Assemble working context from task input and org profile."""
    state["phase"] = "CONTEXT_LOADING"
    state["working_context"] = {
        "organization_id": state["organization_id"],
        "agent_id": state["agent_id"],
        "customer_name": state.get("input", {}).get("customer_name", "Customer"),
        "utterance": state.get("input", {}).get("utterance", ""),
        "call_id": state.get("input", {}).get("call_id"),
        "channel": state.get("input", {}).get("channel", "voice"),
        "timestamp": datetime.utcnow().isoformat(),
    }
    state["steps_executed"] = 0
    state["step_history"] = []
    state["max_steps"] = state.get("max_steps", 20)
    return state


# ────────────────────────────────────────────────────────────────
# Step 2b – Memory retrieval
# ────────────────────────────────────────────────────────────────

def retrieve_memory(state: AgentState) -> AgentState:
    """Retrieve episodic, semantic and procedural memory.

    In production this calls the memory-service; the stub here
    demonstrates pattern-based retrieval.
    """
    utterance = state.get("working_context", {}).get("utterance", "")
    facts: List[Dict[str, Any]] = []

    # Simulated semantic recall
    if "morning" in utterance.lower():
        facts.append({"type": "semantic", "fact": "Customer prefers morning schedule when possible."})
    if "tomorrow" in utterance.lower():
        facts.append({"type": "semantic", "fact": "User requested next-day availability."})
    if "afternoon" in utterance.lower():
        facts.append({"type": "semantic", "fact": "Customer prefers afternoon appointments."})

    # Simulated episodic recall
    customer = state.get("working_context", {}).get("customer_name", "")
    if customer and customer != "Customer":
        facts.append({
            "type": "episodic",
            "fact": f"Previous interaction with {customer} on record.",
        })

    # Simulated procedural recall
    task_type = state.get("task_type", "")
    procedures: List[Dict[str, Any]] = []
    if task_type.startswith("receptionist"):
        procedures.append({
            "procedure_id": "receptionist_sop_v1",
            "steps": ["classify_intent", "collect_slots", "confirm_next_step"],
        })
    elif task_type.startswith("sales"):
        procedures.append({
            "procedure_id": "sales_followup_v1",
            "steps": ["score_lead", "send_intro_email", "wait_24h", "call_if_no_reply", "offer_booking_link"],
        })

    state["retrieved_memories"] = facts
    state["procedures"] = procedures
    return state


# ────────────────────────────────────────────────────────────────
# Step 3 – Planning
# ────────────────────────────────────────────────────────────────

def build_plan(state: AgentState) -> AgentState:
    """Generate an execution plan based on task type and procedures."""
    state["phase"] = "PLANNING"
    task_type = state["task_type"]
    procedures = state.get("procedures", [])

    # Use procedural memory if available
    if procedures:
        proc = procedures[0]
        state["plan"] = [
            {"step": s, "description": f"Execute procedure step: {s}"}
            for s in proc["steps"]
        ]
    elif task_type.startswith("receptionist"):
        state["plan"] = [
            {"step": "classify_intent", "description": "Detect booking / support / transfer intent"},
            {"step": "collect_slots", "description": "Extract requested time and service type"},
            {"step": "check_availability", "description": "Query calendar for open slots"},
            {"step": "confirm_next_step", "description": "Offer booking confirmation or transfer"},
        ]
    elif task_type.startswith("sales"):
        state["plan"] = [
            {"step": "review_lead", "description": "Review lead history and CRM data"},
            {"step": "identify_channel", "description": "Identify best contact channel"},
            {"step": "draft_outreach", "description": "Draft personalized outreach message"},
            {"step": "send_message", "description": "Send message via selected channel"},
            {"step": "update_crm", "description": "Update CRM with action taken"},
        ]
    elif task_type.startswith("scheduling"):
        state["plan"] = [
            {"step": "parse_request", "description": "Parse scheduling parameters"},
            {"step": "check_calendar", "description": "Check calendar availability"},
            {"step": "propose_slots", "description": "Propose available time slots"},
            {"step": "confirm_booking", "description": "Confirm and create calendar event"},
        ]
    else:
        state["plan"] = [
            {"step": "analyze_goal", "description": "Break goal into executable actions"},
            {"step": "take_action", "description": "Execute selected tool call"},
            {"step": "summarize_outcome", "description": "Return structured result"},
        ]

    state["current_step_index"] = 0
    return state


# ────────────────────────────────────────────────────────────────
# Step 4 – Tool selection
# ────────────────────────────────────────────────────────────────

# Tool registry (simulated — production version reads from agent config)
TOOL_REGISTRY = {
    "calendar.create_event": {"category": "calendar", "requires_approval": False},
    "calendar.check_availability": {"category": "calendar", "requires_approval": False},
    "crm.create_task": {"category": "crm", "requires_approval": False},
    "crm.update_lead": {"category": "crm", "requires_approval": False},
    "crm.get_lead": {"category": "crm", "requires_approval": False},
    "email.send": {"category": "email", "requires_approval": False},
    "email.draft": {"category": "email", "requires_approval": False},
    "voice.call": {"category": "voice", "requires_approval": True},
    "voice.transfer": {"category": "voice", "requires_approval": False},
    "billing.create_invoice": {"category": "billing", "requires_approval": True},
    "notification.send_sms": {"category": "notification", "requires_approval": False},
    "workflow.delegate": {"category": "workflow", "requires_approval": False},
}


def choose_action(state: AgentState) -> AgentState:
    """Select the appropriate tool for the current plan step."""
    state["phase"] = "EXECUTING"
    utterance = state.get("working_context", {}).get("utterance", "")
    plan = state.get("plan", [])
    step_idx = state.get("current_step_index", 0)
    current_step = plan[step_idx]["step"] if step_idx < len(plan) else "unknown"

    # Intent-based tool selection
    utterance_lower = utterance.lower()
    if any(w in utterance_lower for w in ["book", "appointment", "schedule"]):
        state["selected_tool"] = "calendar.create_event"
        state["tool_input"] = {
            "service_type": "service_booking",
            "preferred_time": "tomorrow morning" if "tomorrow" in utterance_lower else "next available",
            "customer_name": state["working_context"].get("customer_name", "Customer"),
        }
    elif any(w in utterance_lower for w in ["call", "phone", "ring"]):
        state["selected_tool"] = "voice.call"
        state["tool_input"] = {
            "purpose": state["goal"],
            "customer_name": state["working_context"].get("customer_name", "Customer"),
        }
    elif any(w in utterance_lower for w in ["email", "send", "message"]):
        state["selected_tool"] = "email.send"
        state["tool_input"] = {
            "subject": state["goal"],
            "body": f"Follow-up regarding: {utterance}",
        }
    elif any(w in utterance_lower for w in ["transfer", "connect", "speak to"]):
        state["selected_tool"] = "voice.transfer"
        state["tool_input"] = {
            "transfer_to": "human_agent",
            "reason": utterance,
        }
    elif current_step in ("update_crm", "review_lead"):
        state["selected_tool"] = "crm.update_lead"
        state["tool_input"] = {"action": current_step, "goal": state["goal"]}
    else:
        state["selected_tool"] = "crm.create_task"
        state["tool_input"] = {"title": state["goal"], "step": current_step}

    return state


# ────────────────────────────────────────────────────────────────
# Step 5 – Action execution
# ────────────────────────────────────────────────────────────────

def execute_action(state: AgentState) -> AgentState:
    """Execute the selected tool (simulated in MVP)."""
    tool = state.get("selected_tool", "unknown")
    tool_input = state.get("tool_input", {})

    # Check if tool requires approval
    tool_meta = TOOL_REGISTRY.get(tool, {})
    if tool_meta.get("requires_approval"):
        state["tool_result"] = {
            "tool": tool,
            "status": "pending_approval",
            "reference_id": f"ref_{uuid4().hex[:10]}",
            "message": f"Tool '{tool}' requires human approval before execution.",
        }
    else:
        state["tool_result"] = {
            "tool": tool,
            "status": "success",
            "reference_id": f"ref_{uuid4().hex[:10]}",
            "input": tool_input,
            "executed_at": datetime.utcnow().isoformat(),
        }
    return state


# ────────────────────────────────────────────────────────────────
# Step 6 – Observation
# ────────────────────────────────────────────────────────────────

def observe_result(state: AgentState) -> AgentState:
    """Inspect the tool result and update world state."""
    state["phase"] = "WAITING_FOR_RESULT"
    result = state.get("tool_result", {})
    step_idx = state.get("current_step_index", 0)
    plan = state.get("plan", [])
    current_step_name = plan[step_idx]["step"] if step_idx < len(plan) else "unknown"

    observation = {
        "step_index": step_idx,
        "step_name": current_step_name,
        "tool": result.get("tool"),
        "status": result.get("status"),
        "message": f"Tool {result.get('tool')} executed with status {result.get('status')}",
        "timestamp": datetime.utcnow().isoformat(),
    }

    observations = state.get("observations", [])
    observations.append(observation)
    state["observations"] = observations

    # Record in step history
    step_history = state.get("step_history", [])
    step_history.append({
        "step_index": step_idx,
        "step_name": current_step_name,
        "tool_used": result.get("tool"),
        "tool_input": state.get("tool_input", {}),
        "tool_output": result,
        "observation": observation["message"],
    })
    state["step_history"] = step_history
    state["steps_executed"] = len(step_history)

    return state


# ────────────────────────────────────────────────────────────────
# Step 7 – Reflection / evaluation
# ────────────────────────────────────────────────────────────────

def evaluate_progress(state: AgentState) -> AgentState:
    """Evaluate whether the goal has been achieved or the agent should continue."""
    state["phase"] = "EVALUATING"
    tool_result = state.get("tool_result", {})
    step_idx = state.get("current_step_index", 0)
    plan = state.get("plan", [])
    max_steps = state.get("max_steps", 20)

    tool_status = tool_result.get("status", "unknown")
    is_last_step = step_idx >= len(plan) - 1
    exceeded_budget = state.get("steps_executed", 0) >= max_steps

    if tool_status == "pending_approval":
        # Escalate — cannot proceed without human approval
        state["completed"] = False
        state["evaluation"] = {
            "success": False,
            "reason": "awaiting_human_approval",
            "should_continue": False,
        }
        state["result"] = {
            "summary": "Action requires human approval before proceeding.",
            "recommended_reply": "This action needs approval from a team member. I've flagged it for review.",
            "pending_tool": tool_result.get("tool"),
        }
        return state

    if exceeded_budget:
        state["completed"] = False
        state["failure_reason"] = "max_steps_exceeded"
        state["evaluation"] = {"success": False, "reason": "budget_exceeded", "should_continue": False}
        state["result"] = {
            "summary": "Agent reached maximum step budget without completing the goal.",
            "recommended_reply": "I was unable to complete this request within the allowed steps. A team member will follow up.",
        }
        return state

    if is_last_step or tool_status == "success":
        state["completed"] = True
        utterance = state.get("working_context", {}).get("utterance", "")
        customer = state.get("working_context", {}).get("customer_name", "customer")

        if state.get("selected_tool") == "calendar.create_event":
            state["result"] = {
                "summary": f"Booking request captured for {customer}",
                "recommended_reply": (
                    "I can help you with that. I've captured your request "
                    "and will confirm the next available slot."
                ),
                "utterance": utterance,
                "tool_used": "calendar.create_event",
                "reference_id": tool_result.get("reference_id"),
            }
        elif state.get("selected_tool") == "voice.transfer":
            state["result"] = {
                "summary": f"Call transfer initiated for {customer}",
                "recommended_reply": "Let me connect you with the right person. One moment please.",
                "tool_used": "voice.transfer",
            }
        elif state.get("selected_tool", "").startswith("email"):
            state["result"] = {
                "summary": "Email action completed",
                "recommended_reply": "Your message has been sent. You should receive a response shortly.",
                "tool_used": state.get("selected_tool"),
            }
        else:
            state["result"] = {
                "summary": "Task analyzed and follow-up action prepared.",
                "recommended_reply": "Your request has been captured and routed to the appropriate workflow.",
                "tool_used": state.get("selected_tool"),
            }

        state["evaluation"] = {"success": True, "reason": "goal_achieved"}
    else:
        # More steps to go
        state["current_step_index"] = step_idx + 1
        state["completed"] = False
        state["evaluation"] = {"success": True, "reason": "step_completed", "should_continue": True}

    return state


# ────────────────────────────────────────────────────────────────
# Step 8 – Memory write
# ────────────────────────────────────────────────────────────────

def write_memory(state: AgentState) -> AgentState:
    """Persist important outcomes to memory store.

    In production this writes to:
    - Redis (working memory update)
    - Postgres (episodic entry)
    - Qdrant (semantic fact if new knowledge discovered)

    Only store memory when:
    - A fact will likely matter later
    - A preference was discovered
    - A task outcome changed future behavior
    - A policy/compliance event occurred
    """
    state["phase"] = "COMPLETED" if state.get("completed") else "EXECUTING"

    # Build memory entries (stub — would POST to memory-service)
    memory_entries = []
    result = state.get("result", {})
    if result.get("summary"):
        memory_entries.append({
            "type": "episodic",
            "agent_id": state.get("agent_id"),
            "organization_id": state.get("organization_id"),
            "task_id": state.get("task_id"),
            "summary": result["summary"],
            "timestamp": datetime.utcnow().isoformat(),
        })

    # Detect preference-worthy facts
    utterance = state.get("working_context", {}).get("utterance", "")
    if "morning" in utterance.lower() or "afternoon" in utterance.lower():
        time_pref = "morning" if "morning" in utterance.lower() else "afternoon"
        customer = state.get("working_context", {}).get("customer_name", "customer")
        memory_entries.append({
            "type": "semantic",
            "fact": f"{customer} prefers {time_pref} appointments",
            "entity_type": "customer",
            "entity_id": customer,
        })

    state["_memory_writes"] = memory_entries  # type: ignore[typeddict-unknown-key]
    return state


# ────────────────────────────────────────────────────────────────
# Step 9 – Continue or terminate (routing)
# ────────────────────────────────────────────────────────────────

def should_continue(state: AgentState) -> Literal["choose_action", "__end__"]:
    """LangGraph conditional edge: loop back or terminate."""
    evaluation = state.get("evaluation", {})
    if evaluation.get("should_continue") and not state.get("completed"):
        return "choose_action"
    return "__end__"


# ────────────────────────────────────────────────────────────────
# Graph compilation
# ────────────────────────────────────────────────────────────────

def compile_graph():
    """Compile the LangGraph agent reasoning loop."""
    if StateGraph is None:
        return None

    graph = StateGraph(AgentState)

    # Add nodes (each maps to one reasoning step)
    graph.add_node("load_context", load_context)
    graph.add_node("retrieve_memory", retrieve_memory)
    graph.add_node("build_plan", build_plan)
    graph.add_node("choose_action", choose_action)
    graph.add_node("execute_action", execute_action)
    graph.add_node("observe_result", observe_result)
    graph.add_node("evaluate_progress", evaluate_progress)
    graph.add_node("write_memory", write_memory)

    # Linear edges for context → plan
    graph.set_entry_point("load_context")
    graph.add_edge("load_context", "retrieve_memory")
    graph.add_edge("retrieve_memory", "build_plan")
    graph.add_edge("build_plan", "choose_action")

    # Execution loop
    graph.add_edge("choose_action", "execute_action")
    graph.add_edge("execute_action", "observe_result")
    graph.add_edge("observe_result", "evaluate_progress")
    graph.add_edge("evaluate_progress", "write_memory")

    # Conditional: loop back or terminate
    graph.add_conditional_edges(
        "write_memory",
        should_continue,
        {
            "choose_action": "choose_action",
            "__end__": END,
        },
    )

    return graph.compile()


# ────────────────────────────────────────────────────────────────
# Public API
# ────────────────────────────────────────────────────────────────

def run_agent(state: AgentState) -> AgentState:
    """Execute the full agent reasoning loop.

    Uses the compiled LangGraph when available, otherwise falls
    back to a sequential executor with a manual continue-loop.
    """
    graph = compile_graph()
    if graph is not None:
        return graph.invoke(state)

    # Fallback: manual loop
    state = load_context(state)
    state = retrieve_memory(state)
    state = build_plan(state)

    while True:
        state = choose_action(state)
        state = execute_action(state)
        state = observe_result(state)
        state = evaluate_progress(state)
        state = write_memory(state)

        if state.get("completed") or should_continue(state) == "__end__":
            break

    return state
