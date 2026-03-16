# Sequence Diagrams — Aivira Workforce OS

## A. Inbound Voice Call → Receptionist Agent → Scheduling

```mermaid
sequenceDiagram
    participant Customer
    participant Ordibl as Ordibl Telephony
    participant STT as Ordibl Speech Recognition
    participant Adapter as Ordibl Adapter
    participant Runtime as Agent Runtime
    participant Memory as Memory Service
    participant Calendar as Calendar Integration
    participant TTS as Ordibl Speech Synthesis

    Customer->>Ordibl: Places phone call
    Ordibl->>STT: Audio stream
    STT->>Adapter: POST /webhooks/transcript<br/>{call_id, utterance, speaker}

    Adapter->>Runtime: POST /internal/agent-runtime/tasks/execute<br/>{task_type: receptionist.voice_turn}

    Note over Runtime: Agent Reasoning Loop Begins

    Runtime->>Runtime: Step 1: Load Context<br/>Phase: CONTEXT_LOADING
    Runtime->>Memory: POST /internal/memory/retrieve<br/>{agent_id, query}
    Memory-->>Runtime: Context packet<br/>(working + episodic + semantic + procedural)

    Runtime->>Runtime: Step 2: Build Plan<br/>Phase: PLANNING<br/>[classify_intent, collect_slots, check_availability, confirm]

    Runtime->>Runtime: Step 3: Choose Action<br/>Intent detected: booking
    Runtime->>Calendar: POST /internal/tools/execute<br/>{tool: calendar.create_event}
    Calendar-->>Runtime: {status: success, event_id}

    Runtime->>Runtime: Step 4: Observe Result<br/>Phase: WAITING_FOR_RESULT
    Runtime->>Runtime: Step 5: Evaluate Progress<br/>Phase: EVALUATING → COMPLETED

    Runtime->>Memory: Store episodic memory<br/>"Booking captured for customer"
    Runtime->>Memory: Store semantic memory<br/>"Customer prefers morning appointments"

    Note over Runtime: Agent Reasoning Loop Ends

    Runtime-->>Adapter: TaskResponse<br/>{status: completed, recommended_reply}
    Adapter->>TTS: POST /internal/voice/synthesize<br/>{text: recommended_reply}
    TTS-->>Adapter: Audio URL
    Adapter-->>Ordibl: Speak response to caller
    Ordibl-->>Customer: AI voice response
```

## B. Sales Lead Follow-Up Agent

```mermaid
sequenceDiagram
    participant Trigger as Event Bus
    participant Orchestrator as Orchestrator Agent
    participant Runtime as Agent Runtime
    participant Memory as Memory Service
    participant CRM as CRM Integration
    participant Email as Email Integration
    participant Calendar as Calendar Integration

    Trigger->>Orchestrator: event: customer.reply.received<br/>{lead_id, channel: email}

    Orchestrator->>Runtime: POST /internal/agent-runtime/tasks/execute<br/>{task_type: sales.follow_up, agent_id: sales_agent}

    Note over Runtime: Sales Agent Reasoning Loop

    Runtime->>Runtime: Step 1: Load Context
    Runtime->>Memory: Retrieve lead history
    Memory-->>Runtime: Episodes: "Lead opened previous email"<br/>Facts: "Lead prefers phone calls"

    Runtime->>Runtime: Step 2: Build Plan<br/>[review_lead, identify_channel, draft_outreach,<br/>send_message, update_crm]

    Runtime->>CRM: GET lead details<br/>{tool: crm.get_lead}
    CRM-->>Runtime: {name: "Jane Smith", stage: "qualified"}

    Runtime->>Runtime: Step 3: Choose channel → email
    Runtime->>Email: POST send email<br/>{tool: email.send, subject: "Follow-up"}
    Email-->>Runtime: {status: success, message_id}

    Runtime->>Runtime: Evaluate: step completed, continue
    Runtime->>CRM: POST update lead stage<br/>{tool: crm.update_lead, stage: "contacted"}
    CRM-->>Runtime: {status: success}

    Runtime->>Runtime: Evaluate: goal achieved

    Runtime->>Memory: Store episode<br/>"Follow-up email sent to Jane Smith"

    Note over Runtime: Reasoning Loop Ends

    Runtime-->>Orchestrator: TaskResponse<br/>{status: completed, summary}
```

## C. Multi-Agent Orchestration — Customer Onboarding Workflow

```mermaid
sequenceDiagram
    participant API as API Gateway
    participant WF as Workflow Engine
    participant Runtime as Agent Runtime
    participant Receptionist as Receptionist Agent
    participant Sales as Sales Agent
    participant Billing as Billing Agent
    participant Support as Support Agent
    participant Compliance as Compliance Agent
    participant Human as Human Approver

    API->>WF: POST /v1/workflows/{id}/execute

    Note over WF: Resolve DAG — Step 1: No dependencies

    par Parallel: intake + compliance_check
        WF->>Runtime: Execute "Collect customer intake"<br/>{agent_role: receptionist}
        Runtime->>Receptionist: Run reasoning loop
        Receptionist-->>Runtime: {status: completed, customer_data}
        Runtime-->>WF: Step "intake" completed

        WF->>Runtime: Execute "Verify documents"<br/>{agent_role: compliance}
        Runtime->>Compliance: Run reasoning loop
        Compliance-->>Runtime: {status: completed, docs_verified}
        Runtime-->>WF: Step "compliance_check" completed
    end

    Note over WF: Resolve DAG — Step 2: depends_on [intake]

    WF->>Runtime: Execute "Qualify account"<br/>{agent_role: sales}
    Runtime->>Sales: Run reasoning loop
    Sales-->>Runtime: {status: completed, qualified: true}
    Runtime-->>WF: Step "qualify" completed

    Note over WF: Resolve DAG — Step 3: depends_on [qualify]

    par Parallel: billing_setup + onboard_session
        WF->>Runtime: Execute "Set up payment"<br/>{agent_role: billing, requires_approval: true}
        Runtime->>Billing: Run reasoning loop
        Billing->>Billing: Tool requires approval
        Billing-->>Runtime: {status: pending_approval}
        Runtime->>Human: Request approval for billing setup
        Human-->>Runtime: Approved
        Runtime->>Billing: Resume with approval
        Billing-->>Runtime: {status: completed}
        Runtime-->>WF: Step "billing_setup" completed

        WF->>Runtime: Execute "Create onboarding session"<br/>{agent_role: support}
        Runtime->>Support: Run reasoning loop
        Support-->>Runtime: {status: completed, session_link}
        Runtime-->>WF: Step "onboard_session" completed
    end

    Note over WF: All DAG steps completed

    WF-->>API: WorkflowExecutionResponse<br/>{status: completed, all step_results}
```

## D. Agent Reasoning Loop — Internal State Machine

```mermaid
stateDiagram-v2
    [*] --> IDLE
    IDLE --> CONTEXT_LOADING: Task received

    CONTEXT_LOADING --> PLANNING: Context + memory assembled
    note right of CONTEXT_LOADING
        Load working context
        Retrieve episodic memory
        Retrieve semantic facts
        Load procedural memory
        Assemble context packet
    end note

    PLANNING --> EXECUTING: Plan generated
    note right of PLANNING
        Break goal into substeps
        Use procedural memory if available
        Store plan as execution graph
    end note

    EXECUTING --> WAITING_FOR_RESULT: Tool selected & executed
    note right of EXECUTING
        Select tool from registry
        Check permissions/policies
        Execute tool call
    end note

    WAITING_FOR_RESULT --> EVALUATING: Result observed
    note right of WAITING_FOR_RESULT
        Inspect tool output
        Record observation
        Update step history
    end note

    EVALUATING --> EXECUTING: More steps needed
    EVALUATING --> COMPLETED: Goal achieved
    EVALUATING --> ESCALATED: Needs human approval
    EVALUATING --> FAILED: Budget exceeded / error
    note right of EVALUATING
        Did action move closer to goal?
        Should retry or change strategy?
        Is human approval needed?
        Check step budget
    end note

    COMPLETED --> [*]: Write memory & return result
    ESCALATED --> [*]: Flag for human review
    FAILED --> [*]: Return failure reason
```

## E. Memory Retrieval Pipeline

```mermaid
flowchart TB
    A[Task Starts] --> B[Load Working Memory<br/>Redis]
    B --> C[Retrieve Episodic History<br/>Postgres]
    C --> D[Retrieve Semantic Facts<br/>Qdrant Vector Search]
    D --> E[Load Relevant Procedures<br/>Postgres]
    E --> F[Rank & Filter Results]
    F --> G[Assemble Context Packet]
    G --> H[Send to Reasoning Engine]

    subgraph Memory Write Policy
        I{Should store?}
        I -->|Fact matters later| J[Store Semantic]
        I -->|Preference discovered| J
        I -->|Task outcome| K[Store Episodic]
        I -->|Compliance event| K
        I -->|Temporary data| L[Update Working Memory]
    end
```

## F. End-to-End Flow — Plumbing Company Example

```mermaid
sequenceDiagram
    participant Customer
    participant Ordibl as Ordibl Infrastructure
    participant WOS as Workforce OS
    participant Receptionist as Receptionist Agent
    participant Orchestrator as Orchestrator
    participant Scheduler as Scheduling Agent
    participant Billing as Billing Agent
    participant Support as Support Agent
    participant Memory as Memory Service

    Customer->>Ordibl: Calls plumbing company
    Ordibl->>WOS: Transcript: "I need a plumber tomorrow morning"

    WOS->>Receptionist: Handle inbound call
    Receptionist->>Receptionist: Classify intent → service_booking
    Receptionist->>Receptionist: Extract slots → tomorrow, morning, plumbing
    Receptionist-->>WOS: {intent: booking, service: plumbing}

    WOS->>Orchestrator: Create service-request workflow

    Orchestrator->>Scheduler: Check calendar availability
    Scheduler-->>Orchestrator: Available: 9 AM, 10 AM

    Orchestrator->>Billing: Verify payment method
    Billing-->>Orchestrator: Payment on file ✓

    Orchestrator->>Support: Send confirmation
    Support->>Customer: SMS: "Plumber booked for tomorrow 9 AM"

    Orchestrator->>Memory: Store customer preference<br/>"Prefers morning appointments"
    Orchestrator->>Memory: Store episode<br/>"Service booked for plumbing, March 17"

    Note over WOS: Workflow complete ✓
```
