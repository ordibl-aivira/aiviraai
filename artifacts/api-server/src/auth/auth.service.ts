import { Injectable } from "@nestjs/common";
import { db } from "@workspace/db";
import { usersTable } from "@workspace/db/schema";
import { eq } from "drizzle-orm";
import { randomUUID } from "crypto";

export type OAuthProvider = "google" | "github" | "discord" | "email";

@Injectable()
export class AuthService {
  async upsertUser(data: {
    email: string;
    name: string;
    avatarUrl?: string | null;
    provider: OAuthProvider;
    providerId?: string | null;
  }) {
    const existing = await db.select().from(usersTable).where(eq(usersTable.email, data.email));

    if (existing.length > 0) {
      const [updated] = await db
        .update(usersTable)
        .set({ name: data.name, avatarUrl: data.avatarUrl ?? existing[0].avatarUrl, lastLoginAt: new Date() })
        .where(eq(usersTable.email, data.email))
        .returning();
      return updated;
    }

    const [created] = await db
      .insert(usersTable)
      .values({
        id: randomUUID(),
        email: data.email,
        name: data.name,
        avatarUrl: data.avatarUrl,
        provider: data.provider,
        providerId: data.providerId,
        lastLoginAt: new Date(),
      })
      .returning();
    return created;
  }

  async findById(id: string) {
    const [user] = await db.select().from(usersTable).where(eq(usersTable.id, id));
    return user ?? null;
  }
}
