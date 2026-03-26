import { Injectable, BadRequestException } from "@nestjs/common";
import { db } from "@workspace/db";
import { actionLogsTable } from "@workspace/db/schema";
import { eq } from "drizzle-orm";
import { randomUUID } from "crypto";

@Injectable()
export class ActionLogsService {
  async findByTask(taskId: string) {
    if (!taskId) throw new BadRequestException("taskId query param required");
    const logs = await db.select().from(actionLogsTable)
      .where(eq(actionLogsTable.taskId, taskId))
      .orderBy(actionLogsTable.createdAt);
    return logs.map((l) => ({ ...l, createdAt: l.createdAt.toISOString() }));
  }

  async create(body: { taskId: string; actionType: string; message: string; payloadJson?: any }) {
    const { taskId, actionType, message, payloadJson } = body;
    if (!taskId || !actionType || !message) {
      throw new BadRequestException("taskId, actionType, and message are required");
    }
    const [log] = await db.insert(actionLogsTable).values({
      id: randomUUID(),
      taskId,
      actionType,
      message,
      payloadJson: payloadJson ?? null,
    }).returning();
    return { ...log, createdAt: log.createdAt.toISOString() };
  }
}
