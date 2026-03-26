import { Injectable, NotFoundException } from "@nestjs/common";
import { db } from "@workspace/db";
import { agentsTable } from "@workspace/db/schema";
import { eq } from "drizzle-orm";
import { randomUUID } from "crypto";
import { CreateAgentBody, UpdateAgentBody } from "@workspace/api-zod";
import type { z } from "zod";

const AVATAR_COLORS = [
  "#6366f1", "#8b5cf6", "#ec4899", "#f59e0b", "#10b981", "#3b82f6",
  "#ef4444", "#14b8a6", "#f97316", "#84cc16",
];

function serializeAgent(agent: typeof agentsTable.$inferSelect) {
  return {
    ...agent,
    lastActive: agent.lastActive?.toISOString() ?? null,
    createdAt: agent.createdAt.toISOString(),
  };
}

@Injectable()
export class AgentsService {
  async findAll() {
    const agents = await db.select().from(agentsTable).orderBy(agentsTable.createdAt);
    return agents.map(serializeAgent);
  }

  async findOne(id: string) {
    const [agent] = await db.select().from(agentsTable).where(eq(agentsTable.id, id));
    if (!agent) throw new NotFoundException("Agent not found");
    return serializeAgent(agent);
  }

  async create(body: z.infer<typeof CreateAgentBody>) {
    const color = AVATAR_COLORS[Math.floor(Math.random() * AVATAR_COLORS.length)];
    const [agent] = await db.insert(agentsTable).values({
      id: randomUUID(),
      name: body.name,
      description: body.description ?? null,
      type: body.type,
      status: "inactive",
      tasksCompleted: 0,
      successRate: 0,
      avatarColor: color,
      capabilities: body.capabilities ?? [],
    }).returning();
    return serializeAgent(agent);
  }

  async update(id: string, body: z.infer<typeof UpdateAgentBody>) {
    const [agent] = await db.update(agentsTable).set({
      ...(body.name !== undefined && { name: body.name }),
      ...(body.description !== undefined && { description: body.description }),
      ...(body.status !== undefined && { status: body.status }),
    }).where(eq(agentsTable.id, id)).returning();
    if (!agent) throw new NotFoundException("Agent not found");
    return serializeAgent(agent);
  }

  async remove(id: string) {
    await db.delete(agentsTable).where(eq(agentsTable.id, id));
  }

  async toggle(id: string) {
    const [existing] = await db.select().from(agentsTable).where(eq(agentsTable.id, id));
    if (!existing) throw new NotFoundException("Agent not found");
    const newStatus = existing.status === "active" ? "inactive" : "active";
    const [agent] = await db.update(agentsTable).set({ status: newStatus, lastActive: new Date() })
      .where(eq(agentsTable.id, id)).returning();
    return serializeAgent(agent);
  }
}
