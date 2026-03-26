import { Injectable, NotFoundException } from "@nestjs/common";
import { db } from "@workspace/db";
import { workflowsTable, agentsTable, activityTable } from "@workspace/db/schema";
import { eq } from "drizzle-orm";
import { randomUUID } from "crypto";
import { CreateWorkflowBody } from "@workspace/api-zod";
import type { z } from "zod";

async function withAgentName(workflow: typeof workflowsTable.$inferSelect) {
  let agentName: string | undefined;
  if (workflow.agentId) {
    const [agent] = await db.select({ name: agentsTable.name }).from(agentsTable).where(eq(agentsTable.id, workflow.agentId));
    agentName = agent?.name;
  }
  return {
    ...workflow,
    agentName: agentName ?? null,
    lastRun: workflow.lastRun?.toISOString() ?? null,
    nextRun: workflow.nextRun?.toISOString() ?? null,
    createdAt: workflow.createdAt.toISOString(),
  };
}

@Injectable()
export class WorkflowsService {
  async findAll() {
    const workflows = await db.select().from(workflowsTable).orderBy(workflowsTable.createdAt);
    return Promise.all(workflows.map(withAgentName));
  }

  async findOne(id: string) {
    const [workflow] = await db.select().from(workflowsTable).where(eq(workflowsTable.id, id));
    if (!workflow) throw new NotFoundException("Workflow not found");
    return withAgentName(workflow);
  }

  async create(body: z.infer<typeof CreateWorkflowBody>) {
    const [workflow] = await db.insert(workflowsTable).values({
      id: randomUUID(),
      name: body.name,
      description: body.description ?? null,
      trigger: body.trigger,
      status: "inactive",
      agentId: body.agentId ?? null,
      schedule: body.schedule ?? null,
      runsTotal: 0,
      runsSuccess: 0,
    }).returning();
    return withAgentName(workflow);
  }

  async remove(id: string) {
    await db.delete(workflowsTable).where(eq(workflowsTable.id, id));
  }

  async run(id: string) {
    const [workflow] = await db.select().from(workflowsTable).where(eq(workflowsTable.id, id));
    if (!workflow) throw new NotFoundException("Workflow not found");

    await db.update(workflowsTable).set({
      runsTotal: workflow.runsTotal + 1,
      runsSuccess: workflow.runsSuccess + 1,
      lastRun: new Date(),
      status: "active",
    }).where(eq(workflowsTable.id, id));

    await db.insert(activityTable).values({
      id: randomUUID(),
      type: "workflow_ran",
      title: `Workflow "${workflow.name}" ran`,
      description: "Triggered manually",
      status: "success",
    });

    return {
      id: randomUUID(),
      workflowId: workflow.id,
      status: "running",
      startedAt: new Date().toISOString(),
    };
  }
}
