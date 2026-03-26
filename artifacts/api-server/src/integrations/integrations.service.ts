import { Injectable, NotFoundException } from "@nestjs/common";
import { db } from "@workspace/db";
import { integrationsTable, activityTable } from "@workspace/db/schema";
import { eq } from "drizzle-orm";
import { randomUUID } from "crypto";

@Injectable()
export class IntegrationsService {
  async findAll() {
    const integrations = await db.select().from(integrationsTable);
    return integrations.map((i) => ({
      ...i,
      connectedAt: i.connectedAt?.toISOString() ?? null,
    }));
  }

  async toggle(id: string) {
    const [existing] = await db.select().from(integrationsTable).where(eq(integrationsTable.id, id));
    if (!existing) throw new NotFoundException("Integration not found");

    const [integration] = await db.update(integrationsTable).set({
      connected: !existing.connected,
      connectedAt: !existing.connected ? new Date() : null,
    }).where(eq(integrationsTable.id, id)).returning();

    if (!existing.connected) {
      await db.insert(activityTable).values({
        id: randomUUID(),
        type: "integration_connected",
        title: `${existing.name} connected`,
        description: "Integration successfully linked",
        status: "success",
      });
    }

    return {
      ...integration,
      connectedAt: integration.connectedAt?.toISOString() ?? null,
    };
  }
}
