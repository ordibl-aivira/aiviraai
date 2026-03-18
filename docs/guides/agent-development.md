# Agent Development Guide

How to build, test, and deploy new AI agents in Workforce OS.

## Architecture

Every agent in Workforce OS follows the same reasoning loop:

```
Goal → Context → Plan → Execute → Observe → Evaluate → Memory → Done
```

This loop is implemented as a LangGraph state machine in
`apps/agent_runtime/app/runtime.py`. Each node in the graph is a pure
function that transforms the agent state.

## Creating a New Agent

### 1. Define the Role Prompt

Add a new entry to `ROLE_PROMPTS` in `packages/shared/prompts.py`:

```python
ROLE_PROMPTS["procurement"] = PromptFragment(
    name="role_procurement",
    version="v1",
    role="system",
    content=(
        "You are the AI Procurement Manager. Your job is to:\n"
        "- Source suppliers based on requirements.\n"
        "- Compare quotes and recommend the best option.\n"
        "- Submit purchase orders for approval.\n"
        "- Track delivery timelines.\n"
        "Tone: professional, detail-oriented."
    ),
    tags=("role", "procurement"),
)
```

### 2. Define Task Templates

Add task-specific prompt templates in `TASK_TEMPLATES`:

```python
TASK_TEMPLATES["supplier_search"] = PromptFragment(
    name="task_supplier_search",
    version="v1",
    role="user",
    content=(
        "Find suppliers for the following requirement:\n\n"
        "Item: {item_description}\n"
        "Quantity: {quantity}\n"
        "Budget: {budget}\n"
        "Deadline: {deadline}\n\n"
        "Return JSON with:\n"
        "- \"suppliers\": list of matching suppliers\n"
        "- \"recommendation\": your top pick and why\n"
        "- \"tool_calls\": any searches or lookups performed"
    ),
    tags=("task", "procurement"),
)
```

### 3. Register Tools

Add any new tools the agent needs in `TOOL_REGISTRY`
(`apps/agent_runtime/app/runtime.py`):

```python
TOOL_REGISTRY["procurement.search_suppliers"] = {
    "category": "procurement",
    "requires_approval": False,
}
TOOL_REGISTRY["procurement.submit_po"] = {
    "category": "procurement",
    "requires_approval": True,  # POs need human approval
}
```

### 4. Add Integration Adapters

If the agent needs to call external systems, add adapters in
`apps/integration_service/app/main.py`:

```python
elif tool_name.startswith("procurement."):
    result = _handle_procurement(tool_name, arguments)
```

### 5. Write Procedures

Add standard operating procedures to the procedural memory layer.
These are reusable playbooks that guide the agent:

```json
{
    "procedure_id": "procurement_rfq_v1",
    "name": "Request for Quote",
    "trigger": "procurement.rfq_needed",
    "steps": [
        "identify_requirements",
        "search_approved_suppliers",
        "send_rfq_to_top_3",
        "collect_quotes",
        "compare_and_recommend",
        "submit_for_approval"
    ]
}
```

## Testing Agents

### Simulation Endpoint

Test your agent without persisting results:

```bash
curl -X POST http://localhost:8001/internal/agent-runtime/agents/agt_procurement_01/simulate \
  -H "Content-Type: application/json" \
  -d '{
    "organization_id": "org_001",
    "goal": "Find suppliers for 100 office chairs under $50 each",
    "task_type": "procurement.supplier_search",
    "input": {
      "item_description": "Ergonomic office chair",
      "quantity": 100,
      "budget": "$5,000"
    }
  }'
```

### Prompt Testing

Assemble and inspect prompts before sending to a model:

```python
from packages.shared.prompts import build_agent_prompt

prompt = build_agent_prompt(
    role="procurement",
    task_type="supplier_search",
    task_variables={
        "item_description": "Ergonomic office chair",
        "quantity": "100",
        "budget": "$5,000",
        "deadline": "2026-04-01",
    },
)

# Inspect the assembled messages
for msg in prompt.to_messages():
    print(f"[{msg['role']}] {msg['content'][:80]}...")
```

### AI Client Usage

Always use the shared client for model calls:

```python
from packages.shared.ai_client import ai_client
from packages.shared.prompts import build_agent_prompt

prompt = build_agent_prompt(role="sales", task_type="email_followup", ...)

response = await ai_client.complete(
    messages=prompt.to_messages(),
    organization_id="org_001",
    agent_id="agt_sales_01",
    task_id="tsk_123",
)

print(response.content)           # The model's response
print(response.estimated_cost_usd) # Cost tracking
print(response.trace_id)           # For debugging
```

## Agent Configuration

Agents are configured per-organization with:

```json
{
    "id": "agt_001",
    "organization_id": "org_001",
    "name": "Sales Agent",
    "role": "sales",
    "model": "gpt-4o",
    "config": {
        "temperature": 0.3,
        "max_steps": 15,
        "max_tokens_per_step": 4096,
        "enable_chain_of_thought": true,
        "enable_memory_retrieval": true,
        "allowed_tools": [
            "crm.read",
            "crm.write",
            "email.send",
            "calendar.read"
        ]
    },
    "permissions": {
        "crm.read": true,
        "crm.write": true,
        "email.send": true,
        "calendar.read": true,
        "billing.write": false,
        "discount.approval.request": true
    }
}
```

## Model Selection Guide

| Use Case | Recommended Model | Temperature | Why |
|---|---|---|---|
| Customer-facing voice | gpt-4o | 0.3 | Best quality, low latency |
| Email drafting | gpt-4o | 0.5 | Slightly more creative |
| Data extraction | gpt-4o-mini | 0.1 | Cheap, deterministic |
| Intent classification | gpt-4o-mini | 0.0 | Pure classification |
| Document summarisation | gpt-4o | 0.3 | Quality matters |
| Code generation | gpt-4o | 0.2 | Precision needed |
| Embedding / search | text-embedding-3-small | N/A | Best cost/quality ratio |

## Guardrails Checklist

Before deploying any agent, verify:

- [ ] Role prompt is defined and versioned
- [ ] Tool permissions are scoped (no wildcard access)
- [ ] Max steps and token budget are set
- [ ] Escalation rules are configured
- [ ] Approval gates exist for high-risk actions
- [ ] Procedures are defined for regulated workflows
- [ ] The agent discloses it is AI when asked
- [ ] PII handling complies with privacy policy
- [ ] Cost budget alerts are configured
- [ ] The `/simulate` endpoint produces expected results
