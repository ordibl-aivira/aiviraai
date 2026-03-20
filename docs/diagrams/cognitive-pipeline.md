# Cognitive → Execution Stack — Pipeline Diagrams

## Full Pipeline Sequence

```mermaid
sequenceDiagram
    participant T as Trigger
    participant GW as API Gateway
    participant RA as Research Agent
    participant CA as Content Agent
    participant ME as Motion Engine
    participant EE as Execution Engine
    participant OA as Ordibl Adapter
    participant NS as Notification Svc
    participant MS as Memory Service

    T->>GW: POST /v1/pipeline/run
    GW->>EE: POST /internal/execution/pipeline

    Note over EE: Stage 1 — Intelligence
    EE->>RA: POST /internal/research/investigate
    RA->>MS: Query semantic memory
    MS-->>RA: Past interactions, facts
    RA-->>EE: LeadIntelligence (pain points, signals, pitch)

    Note over EE: Stage 2 — Content
    EE->>CA: POST /internal/content/generate
    CA-->>EE: PersonalizedContent (email, script, proposal)

    Note over EE: Stage 3 — Decision
    EE->>ME: POST /internal/motion/decide
    ME-->>EE: Decision (channel=email, timing=immediate)

    Note over EE: Stage 4 — Execution
    alt Channel = email
        EE->>NS: POST /internal/notifications/send
        NS-->>EE: Email sent
    else Channel = voice
        EE->>OA: POST /internal/ordibl/outbound-call
        OA-->>EE: Call placed
    else Channel = SMS
        EE->>NS: POST /internal/notifications/send (sms)
        NS-->>EE: SMS sent
    end

    Note over EE: Stage 5 — Memory
    EE->>MS: POST /internal/memory/episodic
    MS-->>EE: Stored

    EE-->>GW: PipelineResult (all stages)
    GW-->>T: 200 OK
```

## Sales Outreach Motion Sequence

```mermaid
sequenceDiagram
    participant U as User / CRM
    participant GW as API Gateway
    participant ME as Motion Engine
    participant EE as Execution Engine
    participant NS as Notification Svc
    participant OA as Ordibl Adapter

    U->>GW: POST /v1/motion/sequences (sales_outreach)
    GW->>ME: Create sequence

    Note over ME: Step 1 — Day 0
    ME-->>EE: Execute: send_email
    EE->>NS: Send outreach email
    NS-->>EE: Sent

    Note over ME: Step 2 — Day 2 (no reply)
    ME->>ME: Evaluate condition: no_reply ✓
    ME-->>EE: Execute: send_follow_up
    EE->>NS: Send follow-up email
    NS-->>EE: Sent

    Note over ME: Step 3 — Day 3 (no reply)
    ME->>ME: Evaluate condition: no_reply ✓
    ME-->>EE: Execute: make_call
    EE->>OA: Place outbound call
    OA-->>EE: Call completed

    Note over ME: Step 4 — Day 5 (no reply)
    ME->>ME: Evaluate condition: no_reply ✓
    ME-->>EE: Execute: send_sms
    EE->>NS: Send SMS
    NS-->>EE: Sent

    Note over ME: Step 5 — Day 7
    ME->>ME: Evaluate: escalate_or_close
    ME-->>GW: Sequence completed
```

## Research Agent Intelligence Flow

```mermaid
sequenceDiagram
    participant C as Caller
    participant RA as Research Agent
    participant IS as Integration Svc
    participant MS as Memory Service

    C->>RA: POST /internal/research/investigate
    Note over RA: ResearchType: lead_enrichment

    par Query data sources
        RA->>IS: CRM lookup (crm.get_lead)
        IS-->>RA: Company data, history
    and
        RA->>MS: Semantic memory search
        MS-->>RA: Past interactions, facts
    end

    Note over RA: Merge intelligence
    RA->>RA: Build LeadIntelligence object
    Note over RA: {lead, size, pain_points,<br/>decision_maker, pitch,<br/>urgency_score, signals}

    RA-->>C: ResearchResponse (structured intelligence)
```

## Content Generation Flow

```mermaid
sequenceDiagram
    participant EE as Execution Engine
    participant CA as Content Agent

    EE->>CA: POST /internal/content/generate
    Note over CA: Input: LeadIntelligence +<br/>ContentType + context

    CA->>CA: Select template (sales_outreach_email)
    CA->>CA: Build variables from intelligence
    CA->>CA: Render personalized content
    CA->>CA: Generate variants (A/B)

    CA-->>EE: GeneratedContent
    Note over EE: {subject, body,<br/>call_to_action,<br/>personalization_fields}

    alt Sequence requested
        EE->>CA: POST /internal/content/generate-sequence
        CA-->>EE: [email, follow_up, sms, call_script]
    end
```

## Architecture Layers

```
┌─────────────────────────────────────────────────────────┐
│                   THINKING LAYER                         │
│                                                          │
│  ┌─────────────────┐    ┌─────────────────┐             │
│  │ Research Agent   │───>│ Content Agent    │             │
│  │ :8010            │    │ :8011            │             │
│  │                  │    │                  │             │
│  │ • Lead enrich    │    │ • Email gen      │             │
│  │ • Market research│    │ • Call scripts   │             │
│  │ • Competitors    │    │ • Proposals      │             │
│  │ • Signal detect  │    │ • SMS / follow-up│             │
│  └─────────────────┘    └────────┬─────────┘             │
├──────────────────────────────────┼───────────────────────┤
│              DECISION & PLANNING LAYER                   │
│                                  │                       │
│              ┌───────────────────▼──────────┐            │
│              │     Motion Engine :8012       │            │
│              │                              │            │
│              │  • When to act               │            │
│              │  • Which channel             │            │
│              │  • Sequence steps            │            │
│              │  • SLA + retry rules         │            │
│              └──────────────┬───────────────┘            │
├─────────────────────────────┼────────────────────────────┤
│                   EXECUTION LAYER                        │
│                             │                            │
│              ┌──────────────▼───────────────┐            │
│              │   Execution Engine :8013      │            │
│              │                              │            │
│              │  • Send email                │            │
│              │  • Make call (Ordibl)        │            │
│              │  • Update CRM               │            │
│              │  • Create invoice            │            │
│              │  • Schedule meeting          │            │
│              └──────────────┬───────────────┘            │
├─────────────────────────────┼────────────────────────────┤
│                INFRASTRUCTURE LAYER                      │
│                             │                            │
│  ┌──────────┐  ┌───────────▼──┐  ┌───────────┐          │
│  │ Memory   │  │ Ordibl Voice │  │ CRM /     │          │
│  │ Service  │  │ Infrastructure│  │ Payments  │          │
│  └──────────┘  └──────────────┘  └───────────┘          │
└─────────────────────────────────────────────────────────┘
```
