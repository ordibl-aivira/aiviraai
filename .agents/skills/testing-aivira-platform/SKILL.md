# Testing Aivira Workforce OS Platform

## Overview
The platform consists of 10 FastAPI microservices that communicate via HTTP. All services currently use in-memory data stores (no Postgres/Redis/Qdrant required for local testing).

## Service Ports
| Service | Port | Health Endpoint |
|---------|------|-----------------|
| api-gateway | 8000 | GET /health |
| agent-runtime | 8001 | GET /health |
| ordibl-adapter | 8002 | GET /health |
| workflow-engine | 8003 | GET /health |
| memory-service | 8004 | GET /health |
| integration-service | 8005 | GET /health |
| auth-service | 8006 | GET /health |
| organization-service | 8007 | GET /health |
| analytics-service | 8008 | GET /health |
| notification-service | 8009 | GET /health |

## Starting Services Locally

From repo root (`/home/ubuntu/repos/aiviraai`):

```bash
export PYTHONPATH=.
export AGENT_RUNTIME_URL=http://localhost:8001
export WORKFLOW_ENGINE_URL=http://localhost:8003
export MEMORY_SERVICE_URL=http://localhost:8004
export INTEGRATION_SERVICE_URL=http://localhost:8005
export AUTH_SERVICE_URL=http://localhost:8006
export ORGANIZATION_SERVICE_URL=http://localhost:8007
export ANALYTICS_SERVICE_URL=http://localhost:8008
export NOTIFICATION_SERVICE_URL=http://localhost:8009
export ORDIBL_ADAPTER_URL=http://localhost:8002

# Start each service in background
uvicorn apps.api_gateway.app.main:app --port 8000 --host 0.0.0.0 &
uvicorn apps.agent_runtime.app.main:app --port 8001 --host 0.0.0.0 &
uvicorn apps.ordibl_adapter.app.main:app --port 8002 --host 0.0.0.0 &
uvicorn apps.workflow_engine.app.main:app --port 8003 --host 0.0.0.0 &
uvicorn apps.memory_service.app.main:app --port 8004 --host 0.0.0.0 &
uvicorn apps.integration_service.app.main:app --port 8005 --host 0.0.0.0 &
uvicorn apps.auth_service.app.main:app --port 8006 --host 0.0.0.0 &
uvicorn apps.organization_service.app.main:app --port 8007 --host 0.0.0.0 &
uvicorn apps.analytics_service.app.main:app --port 8008 --host 0.0.0.0 &
uvicorn apps.notification_service.app.main:app --port 8009 --host 0.0.0.0 &
```

To kill a specific service for restart: `fuser -k <port>/tcp`

## Key Testing Patterns

### 1. Task Execution (via API Gateway)
```bash
curl -X POST http://localhost:8000/v1/tasks/execute \
  -H "Content-Type: application/json" \
  -d '{"organization_id": "org_001", "agent_id": "agt_001", "task_type": "receptionist.voice_turn", "goal": "Book appointment", "input": {"utterance": "I need a plumber"}, "constraints": {}, "success_criteria": []}'
```

### 2. Task Execution (direct to Agent Runtime)
```bash
curl -X POST http://localhost:8001/internal/agent-runtime/tasks/execute \
  -H "Content-Type: application/json" \
  -d '{"organization_id": "org_001", "agent_id": "agt_001", "task_type": "receptionist.voice_turn", "goal": "Help customer", "input": {"utterance": "I need help", "call_id": "call_001"}, "constraints": {}, "success_criteria": []}'
```

### 3. Workflow with Approval Flow
This is the most complex test pattern. Steps:
1. Create workflow with `requires_approval: true` on a step
2. Execute workflow → it pauses at the approval step
3. List approvals to get the approval ID
4. Approve via decision endpoint
5. Advance workflow → remaining steps execute

### 4. Notification Service
The notification service uses `organization_id`, `channel`, `to`, and `body` fields (NOT `recipient` or `subject`).

## Known Gotchas

### Escalation Trigger
Escalation is triggered by tools with `requires_approval: True` in the TOOL_REGISTRY (defined in `apps/agent_runtime/app/main.py`). The `voice.call` tool has this flag. To trigger escalation in tests, use utterances with the keyword **"call"** (e.g., "Please call me back"). The keyword "speak" triggers `voice.transfer` which does NOT require approval.

### advance_workflow Approval Pattern
When a workflow pauses at an approval-required step, the step is NOT in `step_results` yet. After approval and `advance_workflow`, the endpoint marks the paused step as `{"status": "approved"}` in step_results before re-walking the DAG. Without this, the DAG walker would re-encounter the approval step and pause again infinitely.

### Pydantic model_dump for HTTP forwarding
When services forward Pydantic models via `httpx.post(json=...)`, always use `model_dump(mode="json")` instead of `model_dump()`. The default `mode='python'` preserves Python datetime objects which cause `TypeError` in `json.dumps()`.

### SQLAlchemy Reserved Attributes
SQLAlchemy's Declarative base reserves `metadata` as an attribute name. If an ORM model needs a `metadata` column, use `metadata_ = Column("metadata", JSONB, ...)` — the DB column stays `metadata` but the Python attribute becomes `metadata_`.

### AI Config Resolution
`resolve_ai_config()` accepts either a dict of overrides or a string role name (e.g., `"receptionist"`). `get_role_preset()` returns a fully resolved `AgentAIConfig` object, not a raw dict.

### Auth is Stub
Auth service uses stub tokens (`jwt_{uuid}`). The `/v1/me` endpoint forwards the upstream 401 status code. No real JWT validation exists.

## Python Module Testing
```bash
# Test ORM models import cleanly
PYTHONPATH=. python3 -c "from packages.shared.database import *; print('OK')"

# Test AI config resolution
PYTHONPATH=. python3 -c "from packages.shared.ai_config import resolve_ai_config; print(resolve_ai_config('receptionist').temperature)"

# Test prompts module
PYTHONPATH=. python3 -c "from packages.shared.prompts import build_agent_prompt; print(build_agent_prompt('receptionist', 'Help customer').system_prompt[:50])"

# Test AI client
PYTHONPATH=. python3 -c "from packages.shared.ai_client import AIClient; c = AIClient(); print(type(c))"
```

## Devin Secrets Needed
No secrets are required for local testing — all services use in-memory stores and stub auth. For production deployment, the following would be needed:
- `OPENAI_API_KEY` — for real LLM calls in agent runtime
- `ANTHROPIC_API_KEY` — for Anthropic provider support
- Database connection strings for Postgres, Redis, Qdrant
