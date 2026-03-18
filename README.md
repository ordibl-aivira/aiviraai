# Aivira Workforce OS

**Autonomous AI Workers Platform** — powered by Ordibl voice infrastructure.

```
Aivira Technologies (Parent)
├── Ordibl — AI voice & communications infrastructure
└── Workforce OS — Autonomous AI workers platform
```

## Architecture Overview

Workforce OS deploys AI agents that perform real work: answering calls,
following up on leads, scheduling appointments, managing billing, and
coordinating multi-step workflows — all orchestrated through an
event-driven microservice platform.

### Core Design Principles

| Principle | Implementation |
|-----------|---------------|
| Agents reason locally | LangGraph state-machine reasoning loop |
| Memory is layered | Working (Redis) · Episodic (Postgres) · Semantic (Qdrant) · Procedural (JSON playbooks) |
| Coordination is event-driven | Task DAGs + event bus (Redis Streams MVP → Kafka at scale) |
| Multi-tenant isolation | Organization-scoped data, RBAC, audit logging |

### Platform Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     User Dashboard                          │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                    API Gateway :8000                         │
└──┬──────────┬──────────┬──────────┬──────────┬──────────────┘
   │          │          │          │          │
   ▼          ▼          ▼          ▼          ▼
Agent      Workflow   Memory    Org       Auth
Runtime    Engine     Service   Service   Service
:8001      :8003      :8004     :8007     :8006
   │          │          │
   ▼          │          ▼
Integration   │     ┌────────────────────┐
Service       │     │  Redis   Postgres  │
:8005         │     │  Qdrant            │
   │          │     └────────────────────┘
   ▼          ▼
Ordibl     Analytics  Notification  Worker
Adapter    :8008      :8009         (queue)
:8002
   │
   ▼
Ordibl Voice Infrastructure
```

## Services

| Service | Port | Description |
|---------|------|-------------|
| **api-gateway** | 8000 | Tenant-facing unified entry point |
| **agent-runtime** | 8001 | LangGraph multi-agent reasoning engine |
| **ordibl-adapter** | 8002 | Voice infrastructure bridge (Ordibl ↔ Workforce OS) |
| **workflow-engine** | 8003 | DAG-based multi-agent orchestration |
| **memory-service** | 8004 | 4-layer memory architecture |
| **integration-service** | 8005 | External system adapters (CRM, calendar, email) |
| **auth-service** | 8006 | JWT authentication & tenant RBAC |
| **organization-service** | 8007 | Tenant & agent lifecycle management |
| **analytics-service** | 8008 | Metrics & observability |
| **notification-service** | 8009 | Email / SMS / push notifications |
| **worker** | — | Async queue consumer for background tasks |

## Agent Reasoning Loop

Every agent runs a LangGraph state machine:

```
Goal → Context → Plan → Execute → Observe → Evaluate → Memory → Done
```

States: `IDLE → CONTEXT_LOADING → PLANNING → EXECUTING → WAITING_FOR_RESULT → EVALUATING → COMPLETED | ESCALATED | FAILED`

See [`docs/langgraph/agent-flow.md`](docs/langgraph/agent-flow.md) for the
full graph definition with node implementations.

## 4-Layer Memory Architecture

| Layer | Store | Purpose | Lifecycle |
|-------|-------|---------|-----------|
| **Working** | Redis | Current session state, recent events | Ephemeral |
| **Episodic** | Postgres | What happened in past tasks | Append-only |
| **Semantic** | Qdrant + Postgres | General facts & knowledge | Long-lived |
| **Procedural** | Postgres | Playbooks, SOPs, process templates | Versioned |

## Multi-Agent Coordination

```
Goal received
  → Orchestrator creates task DAG
  → Specialist agents receive scoped tasks
  → Results returned as events
  → Orchestrator evaluates progress
  → More tasks delegated or workflow closed
```

Agents **never** talk to each other directly. All coordination flows
through the Workflow Engine's task graph.

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.12+

### Local Development

```bash
# Start all services + infrastructure
docker compose -f infrastructure/docker/docker-compose.yaml up --build

# Health check
curl http://localhost:8000/health
```

### Run a Single Service

```bash
pip install -r requirements.txt
PYTHONPATH=. uvicorn apps.api_gateway.app.main:app --port 8000
```

## Project Structure

```
aiviraai/
├── apps/
│   ├── api_gateway/          # Tenant-facing gateway
│   ├── agent_runtime/        # LangGraph reasoning engine
│   ├── ordibl_adapter/       # Voice infrastructure bridge
│   ├── workflow_engine/      # DAG-based orchestration
│   ├── memory_service/       # 4-layer memory
│   ├── integration_service/  # External adapters
│   ├── auth_service/         # Authentication & RBAC
│   ├── organization_service/ # Tenant management
│   ├── analytics_service/    # Metrics
│   ├── notification_service/ # Outbound notifications
│   └── worker/               # Async queue consumer
├── packages/
│   └── shared/               # Shared models, schemas, settings, events
├── infrastructure/
│   ├── docker/               # Docker Compose for local dev
│   ├── k8s/                  # Kubernetes manifests
│   └── helm/                 # Helm chart
├── docs/
│   ├── openapi.yaml          # Full OpenAPI 3.0 specification
│   ├── diagrams/             # Mermaid sequence diagrams
│   ├── schemas/              # Database schema documentation
│   └── langgraph/            # Agent flow definitions
└── requirements.txt
```

## Documentation

| Document | Description |
|----------|-------------|
| [`docs/openapi.yaml`](docs/openapi.yaml) | Complete OpenAPI 3.0 spec for all APIs |
| [`docs/diagrams/sequence-diagrams.md`](docs/diagrams/sequence-diagrams.md) | Mermaid sequence diagrams (voice call, sales follow-up, multi-agent orchestration) |
| [`docs/schemas/database-schema.md`](docs/schemas/database-schema.md) | Full database schema with ER diagram |
| [`docs/langgraph/agent-flow.md`](docs/langgraph/agent-flow.md) | LangGraph state graph definition |

## Deployment

### Kubernetes

```bash
kubectl apply -f infrastructure/k8s/namespace.yaml
kubectl apply -f infrastructure/k8s/
```

### Helm

```bash
helm install workforce-os infrastructure/helm/workforce-os/
```

## Example End-to-End Flow

A customer calls a plumbing company using Workforce OS:

1. **Ordibl** receives call, streams transcript
2. **Receptionist Agent** identifies intent (booking)
3. **Orchestrator** creates service-request workflow
4. **Scheduling Agent** checks calendar availability
5. **Billing Agent** verifies payment method
6. **Support Agent** sends confirmation SMS
7. **Memory** updated with customer preferences
8. Workflow closed

## Generative AI Culture

Aivira is built **AI-native**. Generative AI is not bolted on — it is the
foundation of every agent, workflow, and decision in the platform.

### AI-First Development

| Principle | How |
|-----------|-----|
| Deterministic by default | Low temperature (0.3), structured JSON output, explicit tool schemas |
| Every prompt is versioned | All prompts in `packages/shared/prompts.py` with version strings |
| Guardrails are mandatory | Scoped authority, bounded runtime, escalation rules per agent |
| Agents never freelance | All coordination flows through workflow DAGs, never agent-to-agent chat |
| Observability built-in | Every LLM call gets a trace ID via the shared AI client |

### Shared AI Infrastructure

```
packages/shared/
├── ai_client.py    # Provider-agnostic LLM client (OpenAI, Anthropic, Azure, local)
├── ai_config.py    # Per-agent/org AI config resolution with role presets
├── prompts.py      # Versioned prompt templates (identity, roles, tasks)
└── settings.py     # Platform-wide AI defaults (model, temperature, guardrails)
```

### Supported AI Providers

| Provider | Config Key | Notes |
|----------|-----------|-------|
| OpenAI | `AI_PROVIDER=openai` | Default — GPT-4o for reasoning, GPT-4o-mini for classification |
| Anthropic | `AI_PROVIDER=anthropic` | Claude models |
| Azure OpenAI | `AI_PROVIDER=azure_openai` | Enterprise deployments |
| Local (Ollama) | `AI_PROVIDER=local` | Development / air-gapped environments |

### Agent Role Presets

Each agent role ships with tuned AI configuration:

| Role | Temperature | Max Steps | Key Tools |
|------|------------|-----------|-----------|
| Receptionist | 0.3 | 10 | calendar, voice.transfer, crm |
| Sales | 0.4 | 15 | crm, email, calendar |
| Scheduling | 0.1 | 8 | calendar, notifications |
| Support | 0.3 | 15 | crm, email, notifications |
| Operations | 0.2 | 25 | crm, calendar, workflow.delegate |
| Compliance | 0.0 | 10 | Read-only (blocks billing, voice) |
| Orchestrator | 0.2 | 30 | workflow.delegate only |

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the full AI development guide and
[`docs/guides/agent-development.md`](docs/guides/agent-development.md) for
step-by-step instructions on building new agents.

## Technology Stack

| Component | Technology |
|-----------|-----------|
| Runtime | Python 3.12, FastAPI, Uvicorn |
| Agent framework | LangGraph, LangChain Core |
| Generative AI | OpenAI GPT-4o (default), Anthropic, Azure OpenAI, Ollama |
| Database | PostgreSQL 16 (SQLAlchemy + Alembic) |
| Cache / Queue | Redis 7 |
| Vector DB | Qdrant |
| Auth | JWT (python-jose), bcrypt |
| Containers | Docker, Kubernetes, Helm |
| IPC | REST (httpx), Event bus (NATS JetStream) |
| Observability | OpenTelemetry Collector |
