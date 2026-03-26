import { Injectable } from "@nestjs/common";
import { db } from "@workspace/db";
import { memoryTable } from "@workspace/db/schema";
import { eq, desc, like, or } from "drizzle-orm";
import { randomUUID } from "crypto";

@Injectable()
export class MemoryService {
  async findAll(category?: string) {
    const rows = await db.select().from(memoryTable).orderBy(desc(memoryTable.updatedAt));
    return category ? rows.filter((r) => r.category === category) : rows;
  }

  async search(query: string) {
    if (!query) return [];
    const term = `%${query.toLowerCase()}%`;
    return db.select().from(memoryTable)
      .where(or(like(memoryTable.content, term), like(memoryTable.title, term)))
      .orderBy(desc(memoryTable.updatedAt))
      .limit(20);
  }

  async create(body: any) {
    const [entry] = await db.insert(memoryTable).values({
      id: randomUUID(),
      category: body.category,
      title: body.title,
      content: body.content,
      source: body.source ?? null,
      agentId: body.agentId ?? null,
      metadata: body.metadata ?? null,
    }).returning();
    return entry;
  }

  async remove(id: string) {
    await db.delete(memoryTable).where(eq(memoryTable.id, id));
    return { deleted: true };
  }
}
