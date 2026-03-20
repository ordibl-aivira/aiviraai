# Testing the Cognitive Execution Stack

## Services

| Service | Port | Directory |
|---------|------|-----------|
| Research Agent | 8010 | apps/research_agent |
| Content Agent | 8011 | apps/content_agent |
| Motion Engine | 8012 | apps/motion_engine |
| Execution Engine | 8013 | apps/execution_engine |

## Starting Services Locally

All services must be started from the repo root with `PYTHONPATH=.`:

```bash
# Each in a separate terminal
PYTHONPATH=. uvicorn apps.research_agent.app.main:app --port 8010 --host 0.0.0.0
PYTHONPATH=. uvicorn apps.content_agent.app.main:app --port 8011 --host 0.0.0.0
PYTHONPATH=. uvicorn apps.motion_engine.app.main:app --port 8012 --host 0.0.0.0
```

**IMPORTANT**: The execution engine needs localhost URLs for inter-service calls (defaults point to Docker hostnames):

```bash
PYTHONPATH=. \
  RESEARCH_AGENT_URL=http://localhost:8010 \
  CONTENT_AGENT_URL=http://localhost:8011 \
  MOTION_ENGINE_URL=http://localhost:8012 \
  MEMORY_SERVICE_URL=http://localhost:8004 \
  uvicorn apps.execution_engine.app.main:app --port 8013 --host 0.0.0.0
```

## Health Check

```bash
curl http://localhost:8010/health  # {"status":"ok","service":"research-agent"}
curl http://localhost:8011/health  # {"status":"ok","service":"content-agent"}
curl http://localhost:8012/health  # {"status":"ok","service":"motion-engine"}
curl http://localhost:8013/health  # {"status":"ok","service":"execution-engine"}
```

## Key Test Endpoints

### Full Pipeline (requires all 4 services running)
```bash
curl -X POST http://localhost:8013/internal/execution/pipeline \
  -H "Content-Type: application/json" \
  -d '{"organization_id":"org_001","trigger_type":"new_lead","trigger_data":{"lead_id":"acme_plumbing","company":"Acme Plumbing"},"lead_id":"acme_plumbing"}'
```

Key assertions for real inter-service calls (not fallbacks):
- `stages.research.result.status` should be `"completed"` (not `"partial"`)
- `stages.research.result.confidence_score` should be `0.85` (not `0.3`)
- `stages.content.result.status` should be `"generated"` (not `"partial"`)
- `stages.motion.result.decision.reasoning` should exist (fallback has no reasoning)

### Research Agent
```bash
curl -X POST http://localhost:8010/internal/research/investigate \
  -H "Content-Type: application/json" \
  -d '{"organization_id":"org_001","research_type":"lead_enrichment","query":"acme_plumbing","target":"Acme Plumbing"}'
```
Simulated leads available: `acme_plumbing`, `bright_dental`

### Content Agent
```bash
curl -X POST http://localhost:8011/internal/content/generate \
  -H "Content-Type: application/json" \
  -d '{"organization_id":"org_001","content_type":"email","purpose":"sales outreach","intelligence":{"lead_name":"Acme","company":"Acme Co.","pain_points":["missed calls"]}}'
```
Note: `purpose` field is required or you'll get 422.

### Motion Engine
```bash
# Create sequence
curl -X POST http://localhost:8012/internal/motion/sequences \
  -H "Content-Type: application/json" \
  -d '{"organization_id":"org_001","lead_id":"lead_1","steps":[{"step_order":1,"channel":"email","action":"send_email","delay_hours":0}]}'

# Advance sequence
curl -X POST http://localhost:8012/internal/motion/sequences/{sequence_id}/advance?outcome=no_reply
```

## Lint

```bash
ruff check . --fix
```

## Notes

- All state is in-memory — data is lost on service restart
- No auth required on any endpoint
- The `settings.py` service URL defaults use Docker hostnames (e.g. `http://research-agent:8010`), so local testing MUST override via env vars
- The pipeline silently falls back to hardcoded data if downstream services are unreachable — always check for `"partial"` status to detect fallback
