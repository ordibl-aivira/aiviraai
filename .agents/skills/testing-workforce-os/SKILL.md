# Testing Workforce OS Microservices

## Overview
Workforce OS is a Python/FastAPI monorepo with 11 microservices (10 HTTP + 1 async worker). All services use in-memory stores (no external DB/Redis/Qdrant required for basic testing).

## Prerequisites
- Python 3.12+
- pip install -r requirements.txt

## Dependency Notes
- `langgraph` and `langchain-core` versions must be compatible. As of writing, `langgraph==0.2.16` requires `langchain-core<0.3,>=0.2.27`. If you see `ResolutionImpossible` errors, check this constraint first.
- The `requirements.txt` pins exact versions — always run `pip install -r requirements.txt` to verify resolution works before testing.

## Starting Services Locally

All services run via uvicorn. The API gateway and some services make HTTP calls to other services, so you must override the default Docker-style service URLs to point to localhost.

### Environment Variables
Set these before starting the api-gateway, ordibl-adapter, or workflow-engine:
```bash
export AGENT_RUNTIME_URL=http://localhost:8001
export ORDIBL_ADAPTER_URL=http://localhost:8002
export WORKFLOW_ENGINE_URL=http://localhost:8003
export MEMORY_SERVICE_URL=http://localhost:8004
export INTEGRATION_SERVICE_URL=http://localhost:8005
export AUTH_SERVICE_URL=http://localhost:8006
export ORGANIZATION_SERVICE_URL=http://localhost:8007
export PYTHONPATH=.
```

### Service Ports
| Service | Port | Module |
|---------|------|--------|
| api-gateway | 8000 | apps.api_gateway.app.main:app |
| agent-runtime | 8001 | apps.agent_runtime.app.main:app |
| ordibl-adapter | 8002 | apps.ordibl_adapter.app.main:app |
| workflow-engine | 8003 | apps.workflow_engine.app.main:app |
| memory-service | 8004 | apps.memory_service.app.main:app |
| integration-service | 8005 | apps.integration_service.app.main:app |
| auth-service | 8006 | apps.auth_service.app.main:app |
| organization-service | 8007 | apps.organization_service.app.main:app |
| analytics-service | 8008 | apps.analytics_service.app.main:app |
| notification-service | 8009 | apps.notification_service.app.main:app |

### Start a service
```bash
PYTHONPATH=. uvicorn apps.<service_name>.app.main:app --port <PORT> --host 0.0.0.0
```

## Key Test Flows

### 1. Health checks
```bash
curl http://localhost:<PORT>/health
```
Expect: `{"status": "ok", "service": "<service-name>"}`

### 2. E2E Task Execution (API Gateway → Agent Runtime)
The most important flow. Tests the LangGraph reasoning loop.
```bash
curl -X POST http://localhost:8000/v1/tasks/execute \
  -H 'Content-Type: application/json' \
  -d '{"organization_id": "org_test", "agent_id": "agt_001", "task_type": "receptionist.voice_turn", "goal": "Handle booking", "input": {"utterance": "I want to book an appointment", "customer_name": "Test", "channel": "voice"}}'
```
Expect: `status: completed`, `tool_used: calendar.create_event` (utterance contains "book")

### 3. Ordibl Webhook → Agent Runtime
Tests the voice infrastructure bridge.
```bash
curl -X POST http://localhost:8002/webhooks/transcript \
  -H 'Content-Type: application/json' \
  -d '{"call_id": "call_001", "organization_id": "org_test", "speaker": "customer", "utterance": "transfer me to billing"}'
```
Expect: `tool_used: voice.transfer` (utterance contains "transfer")

### 4. Memory Service CRUD
Test all 4 memory layers: POST/GET to `/internal/memory/working`, `/internal/memory/episodes`, `/internal/memory/knowledge`, `/internal/memory/procedures`, and unified `/internal/memory/retrieve`.

## Agent Runtime Tool Selection Logic
The agent runtime selects tools based on keywords in the utterance (see `apps/agent_runtime/app/runtime.py`):
- "book"/"appointment"/"schedule" → `calendar.create_event`
- "call"/"phone" → `voice.call`
- "email"/"send"/"message" → `email.send`
- "transfer"/"connect"/"speak to" → `voice.transfer`
- Default → `crm.create_task`

## Linting
```bash
ruff check apps/ packages/ --select E,F,W --ignore E501
```

## Devin Secrets Needed
None required for local testing — all services use in-memory stores with no external dependencies.
