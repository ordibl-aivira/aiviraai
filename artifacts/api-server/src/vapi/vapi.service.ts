import { Injectable, UnauthorizedException } from "@nestjs/common";
import { db } from "@workspace/db";
import { vapiCallLogsTable, businessProfileTable } from "@workspace/db/schema";
import { eq, desc } from "drizzle-orm";
import { randomUUID } from "crypto";

const VAPI_BASE = "https://api.vapi.ai";

function getPrivateKey(): string {
  const key = process.env["VAPI_PRIVATE_KEY"];
  if (!key) throw new Error("VAPI_PRIVATE_KEY environment variable is not set");
  return key;
}

async function vapiRequest<T>(method: "GET" | "POST" | "PATCH" | "DELETE", path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${VAPI_BASE}${path}`, {
    method,
    headers: { Authorization: `Bearer ${getPrivateKey()}`, "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Vapi API ${method} ${path} → ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

@Injectable()
export class VapiService {
  getSessionUserId(req: any): string {
    const userId = req.session?.userId;
    if (!userId) throw new UnauthorizedException();
    return userId;
  }

  async listAssistants() {
    return vapiRequest<any[]>("GET", "/assistant");
  }

  async getAssistant(id: string) {
    return vapiRequest<any>("GET", `/assistant/${id}`);
  }

  async createAssistant(payload: any) {
    return vapiRequest<any>("POST", "/assistant", payload);
  }

  async updateAssistant(id: string, payload: any) {
    return vapiRequest<any>("PATCH", `/assistant/${id}`, payload);
  }

  async deleteAssistant(id: string) {
    return vapiRequest<any>("DELETE", `/assistant/${id}`);
  }

  async listCalls(limit = 20) {
    return vapiRequest<any[]>("GET", `/call?limit=${limit}`);
  }

  async getCallLogs(userId: string) {
    const logs = await db.select().from(vapiCallLogsTable)
      .where(eq(vapiCallLogsTable.userId, userId))
      .orderBy(desc(vapiCallLogsTable.createdAt))
      .limit(50);
    return logs;
  }

  async handleWebhook(req: any) {
    const event = req.body;
    const type: string = event?.message?.type ?? event?.type ?? "";

    if (type === "end-of-call-report" || type === "call-ended") {
      const msg = event?.message ?? event;
      await db.insert(vapiCallLogsTable).values({
        id: randomUUID(),
        userId: "system",
        vapiCallId: msg?.call?.id ?? randomUUID(),
        assistantId: msg?.call?.assistantId ?? null,
        direction: msg?.call?.type === "inboundPhoneCall" ? "inbound" : "outbound",
        status: msg?.call?.status ?? "unknown",
        durationSeconds: msg?.durationSeconds ?? 0,
        transcript: msg?.transcript ?? null,
        summary: msg?.summary ?? null,
        recordingUrl: msg?.recordingUrl ?? null,
        endedReason: msg?.endedReason ?? null,
        costUsd: msg?.cost ?? null,
        metadata: msg ?? null,
      });
    }

    return { received: true };
  }
}
