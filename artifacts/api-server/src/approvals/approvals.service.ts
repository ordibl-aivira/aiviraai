import { Injectable, NotFoundException } from "@nestjs/common";
import { db } from "@workspace/db";
import { approvalsTable } from "@workspace/db/schema";
import { eq, desc } from "drizzle-orm";
import { randomUUID } from "crypto";

@Injectable()
export class ApprovalsService {
  async findAll(status?: string) {
    const rows = await db.select().from(approvalsTable).orderBy(desc(approvalsTable.createdAt));
    return status ? rows.filter((r) => r.status === status) : rows;
  }

  async create(body: any) {
    const [approval] = await db.insert(approvalsTable).values({
      id: randomUUID(),
      agentId: body.agentId,
      agentName: body.agentName,
      action: body.action,
      description: body.description,
      channel: body.channel ?? "internal",
      autonomyLevel: body.autonomyLevel ?? "approval_required",
      context: body.context ?? null,
    }).returning();
    return approval;
  }

  async approve(id: string, resolvedBy: string) {
    const [updated] = await db.update(approvalsTable)
      .set({ status: "approved", resolvedAt: new Date(), resolvedBy })
      .where(eq(approvalsTable.id, id))
      .returning();
    if (!updated) throw new NotFoundException("Approval not found");
    return updated;
  }

  async reject(id: string, resolvedBy: string) {
    const [updated] = await db.update(approvalsTable)
      .set({ status: "rejected", resolvedAt: new Date(), resolvedBy })
      .where(eq(approvalsTable.id, id))
      .returning();
    if (!updated) throw new NotFoundException("Approval not found");
    return updated;
  }
}
