import { Injectable, UnauthorizedException } from "@nestjs/common";
import { db } from "@workspace/db";
import { businessProfileTable, memoryTable, activityTable, usersTable } from "@workspace/db/schema";
import { eq } from "drizzle-orm";
import { randomUUID } from "crypto";

@Injectable()
export class ProfileService {
  async getSessionUser(req: any) {
    const userId = req.session?.userId;
    if (!userId) return null;
    const [user] = await db.select().from(usersTable).where(eq(usersTable.id, userId));
    return user ?? null;
  }

  async getProfile(req: any) {
    const user = await this.getSessionUser(req);
    if (!user) throw new UnauthorizedException();
    const [profile] = await db.select().from(businessProfileTable).where(eq(businessProfileTable.userId, user.id));
    return profile ?? null;
  }

  async saveProfile(req: any, body: any) {
    const user = await this.getSessionUser(req);
    if (!user) throw new UnauthorizedException();

    const existing = await db.select().from(businessProfileTable).where(eq(businessProfileTable.userId, user.id));

    if (existing.length > 0) {
      const [updated] = await db.update(businessProfileTable)
        .set({
          companyName: body.companyName,
          industry: body.industry,
          brandTone: body.brandTone,
          targetAudience: body.targetAudience,
          description: body.description,
          primaryMarkets: body.primaryMarkets ?? [],
          policiesJson: body.policiesJson ?? null,
          updatedAt: new Date(),
        })
        .where(eq(businessProfileTable.userId, user.id))
        .returning();
      return updated;
    }

    const [created] = await db.insert(businessProfileTable).values({
      id: randomUUID(),
      userId: user.id,
      companyName: body.companyName,
      industry: body.industry,
      brandTone: body.brandTone,
      targetAudience: body.targetAudience,
      description: body.description,
      primaryMarkets: body.primaryMarkets ?? [],
      policiesJson: body.policiesJson ?? null,
    }).returning();

    await db.insert(memoryTable).values([
      {
        id: randomUUID(),
        category: "business_profile",
        title: `${body.companyName} — Company Overview`,
        content: `${body.description} Industry: ${body.industry}. Target audience: ${body.targetAudience}. Primary markets: ${(body.primaryMarkets ?? []).join(", ") || "Global"}.`,
        source: "Business onboarding",
      },
      {
        id: randomUUID(),
        category: "user_tone",
        title: "Brand Voice & Tone",
        content: `Brand tone: ${body.brandTone}. All agent communications should reflect this style consistently across email, voice, and social channels.`,
        source: "Business onboarding",
      },
    ]);

    await db.insert(activityTable).values({
      id: randomUUID(),
      type: "agent_completed",
      title: "Business profile created",
      description: `${body.companyName} workspace configured — agents now have business context`,
      status: "success",
    });

    return created;
  }
}
