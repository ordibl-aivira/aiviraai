import { Injectable, NotFoundException } from "@nestjs/common";
import { db } from "@workspace/db";
import { tasksTable, agentsTable, activityTable } from "@workspace/db/schema";
import { eq } from "drizzle-orm";
import { randomUUID } from "crypto";
import { CreateTaskBody, UpdateTaskBody } from "@workspace/api-zod";
import type { z } from "zod";

async function withAgentName(task: typeof tasksTable.$inferSelect) {
  let agentName: string | undefined;
  if (task.agentId) {
    const [agent] = await db.select({ name: agentsTable.name }).from(agentsTable).where(eq(agentsTable.id, task.agentId));
    agentName = agent?.name;
  }
  return {
    ...task,
    agentName: agentName ?? null,
    dueAt: task.dueAt?.toISOString() ?? null,
    completedAt: task.completedAt?.toISOString() ?? null,
    createdAt: task.createdAt.toISOString(),
  };
}

@Injectable()
export class TasksService {
  async findAll() {
    const tasks = await db.select().from(tasksTable).orderBy(tasksTable.createdAt);
    return Promise.all(tasks.map(withAgentName));
  }

  async create(body: z.infer<typeof CreateTaskBody>) {
    const [task] = await db.insert(tasksTable).values({
      id: randomUUID(),
      title: body.title,
      description: body.description ?? null,
      status: "pending",
      priority: body.priority,
      agentId: body.agentId ?? null,
      dueAt: body.dueAt ? new Date(body.dueAt) : null,
    }).returning();

    await db.insert(activityTable).values({
      id: randomUUID(),
      type: "task_created",
      title: `Task "${task.title}" created`,
      status: "info",
    });

    return withAgentName(task);
  }

  async update(id: string, body: z.infer<typeof UpdateTaskBody>) {
    const completedAt = body.status === "completed" ? new Date() : undefined;
    const [task] = await db.update(tasksTable).set({
      ...(body.title !== undefined && { title: body.title }),
      ...(body.status !== undefined && { status: body.status }),
      ...(body.priority !== undefined && { priority: body.priority }),
      ...(body.agentId !== undefined && { agentId: body.agentId }),
      ...(completedAt !== undefined && { completedAt }),
    }).where(eq(tasksTable.id, id)).returning();
    if (!task) throw new NotFoundException("Task not found");
    return withAgentName(task);
  }

  async remove(id: string) {
    await db.delete(tasksTable).where(eq(tasksTable.id, id));
  }
}
