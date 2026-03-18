# Contributing to Aivira Workforce OS

## Generative AI Culture

Aivira is an **AI-native** platform. Every contributor — human or AI — should
follow these principles when writing code, designing features, or reviewing
pull requests.

### Core Principles

1. **AI-first, not AI-added.** Features should be designed around what
   autonomous agents can do, not as afterthoughts bolted onto human workflows.

2. **Deterministic by default.** Agent behaviour must be predictable and
   reproducible. Use low temperature (`0.3`), structured output schemas, and
   explicit tool definitions. Creativity is opt-in per task type.

3. **Every prompt is versioned.** All system prompts live in
   `packages/shared/prompts.py` with a `version` field. When you change a
   prompt, bump the version so regressions can be traced in logs.

4. **Guardrails are mandatory.** Every agent must operate with:
   - Scoped authority (what it can do)
   - Scoped context (what data it can see)
   - Bounded runtime (max steps, max tokens, timeout)
   - Escalation rules (when to ask for human help)

5. **Memory is layered, not monolithic.** Use the right memory layer:
   - **Working** (Redis) — current session state, ephemeral
   - **Episodic** (Postgres) — what happened, append-only
   - **Semantic** (Qdrant) — facts and knowledge, long-lived
   - **Procedural** (Postgres) — playbooks and SOPs, versioned

6. **Agents never talk to each other directly.** All coordination flows
   through the Workflow Engine's task DAGs and event bus. This keeps the
   system auditable and prevents runaway agent-to-agent loops.

7. **Observability is not optional.** Every LLM call, tool invocation, and
   agent decision must be traceable. Use the shared `ai_client` which
   automatically generates trace IDs.

### Code Standards

#### Adding a New Agent Role

1. Define the role prompt in `packages/shared/prompts.py` under `ROLE_PROMPTS`.
2. Add task templates for the role in `TASK_TEMPLATES`.
3. Register any new tools in `apps/agent_runtime/app/runtime.py` → `TOOL_REGISTRY`.
4. Add integration adapters in `apps/integration_service/` if the role needs
   external system access.
5. Write the agent's procedures as entries in the procedural memory layer.

#### Adding a New Tool

1. Define the tool metadata in `TOOL_REGISTRY` (category, requires_approval).
2. Implement the adapter in `apps/integration_service/app/main.py`.
3. If the tool has side effects (writes data, sends messages, costs money),
   set `requires_approval: True` and document the approval policy.
4. Add the tool to the agent's permission schema.

#### Prompt Engineering Guidelines

- **System prompts** define identity, constraints, and output format.
- **User prompts** provide the task context and expected output schema.
- Never put PII in system prompts — it should come from the task context.
- Use `{variable}` placeholders in templates; never hard-code customer data.
- Test prompts with `POST /internal/agent-runtime/agents/{id}/simulate` before
  deploying.
- Document expected input/output schemas for every prompt template.

#### AI Client Usage

Always use the shared AI client (`packages/shared/ai_client.py`):

```python
from packages.shared.ai_client import ai_client

response = await ai_client.complete(
    messages=prompt.to_messages(),
    organization_id=org_id,
    agent_id=agent_id,
    task_id=task_id,
)
```

Never call provider SDKs (OpenAI, Anthropic) directly from service code.
The shared client enforces retries, cost tracking, token budgets, and tracing.

### Anti-Patterns

These patterns are **not allowed** in the Aivira codebase:

| Anti-Pattern | Why | Do Instead |
|---|---|---|
| Unrestricted agent-to-agent chat loops | Can spiral infinitely, no audit trail | Use workflow DAGs with bounded steps |
| Unlimited retries on LLM calls | Cost explosion, no convergence guarantee | Use `ai_max_retries` (default 3) |
| Raw string prompts in service code | Not versioned, not testable, not auditable | Use `packages/shared/prompts.py` |
| Storing PII in prompt logs | Privacy/compliance violation | Set `ai_log_prompts=False` in production |
| Every agent accessing every tool | Security risk, blast radius too large | Scope permissions per agent role |
| Hard-coded model names in services | Cannot switch providers or upgrade | Use `settings.ai_primary_model` |
| Freeform planning for regulated workflows | Compliance risk | Use procedural memory with approved SOPs |

### Development Workflow

1. **Branch** from `main` using `devin/<timestamp>-<description>`.
2. **Implement** following the patterns in this guide.
3. **Lint** with `ruff check .` and type-check changes.
4. **Test** agent changes with the `/simulate` endpoint.
5. **PR** with a clear description of what changed and why.
6. **Review** — every PR touching prompts or agent behaviour requires review
   from someone familiar with the agent architecture.

### Environment Variables for AI

| Variable | Default | Description |
|---|---|---|
| `AI_PRIMARY_MODEL` | `gpt-4o` | Default model for reasoning |
| `AI_FALLBACK_MODEL` | `gpt-4o-mini` | Fallback when primary is unavailable |
| `AI_EMBEDDING_MODEL` | `text-embedding-3-small` | Model for vector embeddings |
| `AI_PROVIDER` | `openai` | Provider: openai, anthropic, azure_openai, local |
| `AI_TEMPERATURE` | `0.3` | Default temperature for completions |
| `AI_ENABLE_CHAIN_OF_THOUGHT` | `true` | Include CoT instruction in prompts |
| `AI_ENABLE_STRUCTURED_OUTPUT` | `true` | Require JSON output from models |
| `AI_MAX_TOKENS_PER_TASK` | `32000` | Token budget per agent task |
| `AI_LOG_PROMPTS` | `false` | Log full prompts (disable in prod) |
| `AI_TRACE_LLM_CALLS` | `true` | Generate trace IDs for LLM calls |
| `OPENAI_API_KEY` | — | OpenAI API key |
| `ANTHROPIC_API_KEY` | — | Anthropic API key |
