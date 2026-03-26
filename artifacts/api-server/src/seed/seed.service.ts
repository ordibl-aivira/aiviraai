import { Injectable } from "@nestjs/common";
import { eq } from "drizzle-orm";
import { db } from "@workspace/db";
import {
  agentsTable, workflowsTable, tasksTable, integrationsTable, activityTable,
  approvalsTable, memoryTable, actionLogsTable,
} from "@workspace/db/schema";
import { randomUUID } from "crypto";

@Injectable()
export class SeedService {
  async seed() {
    const existingAgents = await db.select().from(agentsTable);
    const seededAgents = existingAgents.length > 0;
    let agents = existingAgents;

    if (!seededAgents) {
      agents = await db.insert(agentsTable).values([
        {
          id: randomUUID(), name: "Vera",
          description: "AI Receptionist — answers every inbound call via Ordibl, qualifies callers, routes intelligently",
          type: "customer_support", status: "active", tasksCompleted: 312, successRate: 97.4,
          avatarColor: "#6366f1", capabilities: ["inbound_calls", "qualification", "routing", "ACTIVE"],
          autonomyLevel: "autopilot", channels: ["voice", "crm"], lastActive: new Date(),
        },
        {
          id: randomUUID(), name: "Max",
          description: "AI Sales Agent — follows up leads, books demos, sends proposals, updates CRM automatically",
          type: "sales", status: "active", tasksCompleted: 218, successRate: 94.1,
          avatarColor: "#10b981", capabilities: ["lead_followup", "proposals", "crm_updates", "EXECUTING"],
          autonomyLevel: "approval_required", channels: ["email", "crm", "social"], lastActive: new Date(),
        },
        {
          id: randomUUID(), name: "Sage",
          description: "AI Scheduler — manages calendars, books appointments, handles rescheduling and reminders",
          type: "scheduler", status: "active", tasksCompleted: 407, successRate: 98.8,
          avatarColor: "#3b82f6", capabilities: ["calendar_management", "booking", "reminders", "IDLE"],
          autonomyLevel: "autopilot", channels: ["email", "calendar"], lastActive: new Date(),
        },
        {
          id: randomUUID(), name: "Aria",
          description: "AI Support Agent — handles tier-1 customer support, resolves tickets, escalates intelligently",
          type: "customer_support", status: "active", tasksCompleted: 531, successRate: 96.2,
          avatarColor: "#ec4899", capabilities: ["ticket_resolution", "escalation", "kb_search", "IDLE"],
          autonomyLevel: "autopilot", channels: ["email", "voice", "social"], lastActive: new Date(),
        },
        {
          id: randomUUID(), name: "Nova",
          description: "AI Operations Manager — monitors workflows, detects anomalies, optimizes resource allocation",
          type: "operations", status: "active", tasksCompleted: 189, successRate: 91.7,
          avatarColor: "#f59e0b", capabilities: ["monitoring", "anomaly_detection", "reporting", "IDLE"],
          autonomyLevel: "draft", channels: ["internal", "email"], lastActive: new Date(),
        },
        {
          id: randomUUID(), name: "Lex",
          description: "AI Compliance & Finance Agent — reviews contracts, flags risks, tracks budgets and expenses",
          type: "compliance", status: "active", tasksCompleted: 94, successRate: 99.1,
          avatarColor: "#8b5cf6", capabilities: ["contract_review", "risk_flagging", "budget_tracking", "IDLE"],
          autonomyLevel: "approval_required", channels: ["internal", "email"], lastActive: new Date(),
        },
        {
          id: randomUUID(), name: "Atlas",
          description: "AI Orchestrator — coordinates all agents, manages task routing, optimizes agent performance",
          type: "orchestrator", status: "active", tasksCompleted: 847, successRate: 95.3,
          avatarColor: "#ef4444", capabilities: ["agent_coordination", "task_routing", "performance_optimization", "ORCHESTRATING"],
          autonomyLevel: "autopilot", channels: ["internal"], lastActive: new Date(),
        },
      ]).returning();
    }

    const existingWorkflows = await db.select().from(workflowsTable);
    if (existingWorkflows.length === 0 && agents.length > 0) {
      const vera = agents.find((a) => a.name === "Vera");
      const max = agents.find((a) => a.name === "Max");
      const sage = agents.find((a) => a.name === "Sage");
      const aria = agents.find((a) => a.name === "Aria");
      const nova = agents.find((a) => a.name === "Nova");
      const lex = agents.find((a) => a.name === "Lex");

      await db.insert(workflowsTable).values([
        {
          id: randomUUID(), name: "Inbound Call Handling", trigger: "voice_call",
          description: "Vera answers, qualifies, and routes every inbound call", status: "active",
          agentId: vera?.id ?? null, runsTotal: 312, runsSuccess: 304, lastRun: new Date(),
        },
        {
          id: randomUUID(), name: "Lead Follow-Up Sequence", trigger: "crm_event",
          description: "Max follows up new CRM leads within 5 minutes via email and SMS", status: "active",
          agentId: max?.id ?? null, runsTotal: 218, runsSuccess: 205, lastRun: new Date(),
        },
        {
          id: randomUUID(), name: "Smart Scheduling", trigger: "calendar_request",
          description: "Sage auto-schedules meetings and sends confirmation + reminders", status: "active",
          agentId: sage?.id ?? null, runsTotal: 407, runsSuccess: 402, lastRun: new Date(),
        },
        {
          id: randomUUID(), name: "Tier-1 Support Resolution", trigger: "support_ticket",
          description: "Aria resolves common issues using knowledge base and escalates edge cases", status: "active",
          agentId: aria?.id ?? null, runsTotal: 531, runsSuccess: 511, lastRun: new Date(),
        },
        {
          id: randomUUID(), name: "Daily Operations Report", trigger: "schedule",
          description: "Nova compiles and emails daily performance metrics every morning", status: "active",
          agentId: nova?.id ?? null, schedule: "0 8 * * *", runsTotal: 89, runsSuccess: 87, lastRun: new Date(),
        },
        {
          id: randomUUID(), name: "Contract Risk Review", trigger: "document_upload",
          description: "Lex scans uploaded contracts for red flags and compliance issues", status: "active",
          agentId: lex?.id ?? null, runsTotal: 34, runsSuccess: 34, lastRun: new Date(),
        },
      ]);
    }

    const existingTasks = await db.select().from(tasksTable);
    if (existingTasks.length === 0 && agents.length > 0) {
      const vera = agents.find((a) => a.name === "Vera");
      const max = agents.find((a) => a.name === "Max");
      const aria = agents.find((a) => a.name === "Aria");
      const lex = agents.find((a) => a.name === "Lex");

      const taskId1 = randomUUID();
      const taskId2 = randomUUID();
      const taskId3 = randomUUID();

      await db.insert(tasksTable).values([
        {
          id: taskId1, title: "Qualify inbound call from TechCorp", status: "completed", priority: "high",
          agentId: vera?.id ?? null, completedAt: new Date(Date.now() - 1000 * 60 * 30),
          description: "Caller inquired about enterprise pricing. Qualified as high-value lead.",
        },
        {
          id: taskId2, title: "Send proposal to Acme Industries", status: "in_progress", priority: "high",
          agentId: max?.id ?? null, description: "Preparing custom proposal for 50-seat enterprise deal.",
        },
        {
          id: taskId3, title: "Resolve billing dispute — Customer #4821", status: "pending", priority: "medium",
          agentId: aria?.id ?? null, description: "Customer reports double charge on last invoice.",
        },
        {
          id: randomUUID(), title: "Review Q4 vendor contracts", status: "pending", priority: "high",
          agentId: lex?.id ?? null, description: "Five contracts pending compliance review before renewal.",
        },
        {
          id: randomUUID(), title: "Schedule onboarding for new client", status: "completed", priority: "medium",
          agentId: agents.find((a) => a.name === "Sage")?.id ?? null,
          completedAt: new Date(Date.now() - 1000 * 60 * 60 * 2),
          description: "Booked 3-session onboarding series with Riverdale Healthcare.",
        },
      ]);

      await db.insert(actionLogsTable).values([
        { id: randomUUID(), taskId: taskId1, actionType: "call_started", message: "Inbound call received from +1 (555) 293-4821" },
        { id: randomUUID(), taskId: taskId1, actionType: "caller_identified", message: "Caller identified as David Chen, VP Engineering at TechCorp" },
        { id: randomUUID(), taskId: taskId1, actionType: "needs_assessed", message: "Needs assessment complete — interested in voice AI for 200-seat support team" },
        { id: randomUUID(), taskId: taskId1, actionType: "lead_qualified", message: "Lead qualified: HIGH VALUE — forwarded to Max for follow-up" },
        { id: randomUUID(), taskId: taskId1, actionType: "call_ended", message: "Call ended after 4m 12s. Satisfaction: 4.8/5" },
        { id: randomUUID(), taskId: taskId2, actionType: "lead_received", message: "New lead from CRM: Acme Industries, $180K ARR opportunity" },
        { id: randomUUID(), taskId: taskId2, actionType: "research_started", message: "Researching Acme Industries — 450 employees, manufacturing sector" },
        { id: randomUUID(), taskId: taskId2, actionType: "proposal_drafted", message: "Proposal drafted: Enterprise plan with custom SLA and dedicated CSM" },
      ]);
    }

    const existingIntegrations = await db.select().from(integrationsTable);
    if (existingIntegrations.length === 0) {
      await db.insert(integrationsTable).values([
        { id: randomUUID(), name: "Salesforce CRM", category: "crm", connected: true, connectedAt: new Date(), status: "active", description: "Bi-directional CRM sync for leads, contacts, and deals", icon: "salesforce" },
        { id: randomUUID(), name: "HubSpot", category: "crm", connected: false, status: "inactive", description: "Marketing automation and CRM platform integration", icon: "hubspot" },
        { id: randomUUID(), name: "Slack", category: "communication", connected: true, connectedAt: new Date(), status: "active", description: "Real-time agent notifications and escalation alerts", icon: "slack" },
        { id: randomUUID(), name: "Google Calendar", category: "productivity", connected: true, connectedAt: new Date(), status: "active", description: "Calendar sync for Sage scheduling workflows", icon: "google-calendar" },
        { id: randomUUID(), name: "Stripe", category: "payments", connected: true, connectedAt: new Date(), status: "active", description: "Payment processing and subscription management", icon: "stripe" },
        { id: randomUUID(), name: "Zendesk", category: "support", connected: false, status: "inactive", description: "Support ticketing system for Aria escalations", icon: "zendesk" },
        { id: randomUUID(), name: "Twilio", category: "communication", connected: true, connectedAt: new Date(), status: "active", description: "SMS and voice communication infrastructure", icon: "twilio" },
        { id: randomUUID(), name: "OpenAI GPT-4", category: "ai", connected: true, connectedAt: new Date(), status: "active", description: "Primary LLM for agent reasoning and generation", icon: "openai" },
      ]);
    }

    const existingApprovals = await db.select().from(approvalsTable);
    if (existingApprovals.length === 0 && agents.length > 0) {
      const max = agents.find((a) => a.name === "Max");
      const lex = agents.find((a) => a.name === "Lex");
      const nova = agents.find((a) => a.name === "Nova");

      await db.insert(approvalsTable).values([
        {
          id: randomUUID(), agentId: max?.id ?? "max", agentName: "Max", action: "Send enterprise proposal to TechCorp",
          description: "Max has prepared a $180K enterprise proposal. Review and approve before sending.",
          channel: "email", autonomyLevel: "approval_required", status: "pending",
          context: { dealSize: "$180K", contact: "David Chen, VP Engineering", company: "TechCorp" },
        },
        {
          id: randomUUID(), agentId: lex?.id ?? "lex", agentName: "Lex", action: "Flag non-standard indemnification clause",
          description: "Lex identified an unusual indemnification clause in the Riverside contract that exceeds standard limits.",
          channel: "internal", autonomyLevel: "approval_required", status: "pending",
          context: { contract: "Riverside Healthcare — Master Services Agreement", clause: "Section 12.4", risk: "High" },
        },
        {
          id: randomUUID(), agentId: nova?.id ?? "nova", agentName: "Nova", action: "Scale support queue processing",
          description: "Nova recommends spinning up 2 additional Aria instances to handle 40% spike in support volume.",
          channel: "internal", autonomyLevel: "draft", status: "pending",
          context: { currentLoad: "142%", recommendation: "Add 2 Aria instances for 4 hours" },
        },
      ]);
    }

    const existingMemory = await db.select().from(memoryTable);
    if (existingMemory.length === 0) {
      await db.insert(memoryTable).values([
        { id: randomUUID(), category: "business_profile", title: "Core Business Identity", content: "Aivira OS is the operating system for autonomous businesses. We replace entire departments with AI agent teams that work 24/7, never take breaks, and scale infinitely.", source: "System" },
        { id: randomUUID(), category: "user_tone", title: "Brand Voice", content: "Professional yet approachable. Confident and forward-thinking. Use clear, direct language. Avoid jargon. Focus on outcomes and business value.", source: "System" },
        { id: randomUUID(), category: "policy", title: "Escalation Policy", content: "Escalate to human if: (1) Deal value >$50K, (2) Legal or compliance risk, (3) Customer expresses frustration 2+ times, (4) Technical issue beyond tier-1 KB.", source: "System" },
        { id: randomUUID(), category: "context", title: "Top Customer Segments", content: "Primary: SMBs 10-200 employees in professional services, healthcare, real estate. Secondary: Enterprise sales teams and customer success orgs.", source: "System" },
        { id: randomUUID(), category: "context", title: "Pricing Guidelines", content: "Starter: $299/mo (3 agents). Growth: $799/mo (7 agents). Enterprise: Custom. Always emphasize ROI — average customer saves 40+ hours/week.", source: "System" },
      ]);
    }

    const existingActivity = await db.select().from(activityTable);
    if (existingActivity.length === 0) {
      await db.insert(activityTable).values([
        { id: randomUUID(), type: "agent_activated", title: "Vera went live", description: "AI Receptionist handling all inbound calls", status: "success" },
        { id: randomUUID(), type: "task_completed", title: "Max closed TechCorp deal", description: "$180K enterprise deal signed", status: "success" },
        { id: randomUUID(), type: "workflow_ran", title: "Daily ops report generated", description: "Nova compiled 47-page performance report", status: "success" },
        { id: randomUUID(), type: "agent_completed", title: "Aria resolved 24 tickets", description: "100% resolution rate in the last 4 hours", status: "success" },
        { id: randomUUID(), type: "approval_requested", title: "Lex flagged contract risk", description: "Non-standard indemnification clause requires review", status: "warning" },
      ]);
    }

    return { seeded: true, agents: agents.length };
  }
}
