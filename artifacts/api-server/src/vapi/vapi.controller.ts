import { Controller, Get, Post, Patch, Delete, Param, Body, Req, Res, UseGuards, HttpCode } from "@nestjs/common";
import { Request, Response } from "express";
import { VapiService } from "./vapi.service";
import { SessionGuard } from "../common/guards/session.guard";
import { createHmac, timingSafeEqual } from "crypto";

@Controller("vapi")
export class VapiController {
  constructor(private readonly vapiService: VapiService) {}

  @Post("webhook")
  @HttpCode(200)
  async webhook(@Req() req: Request, @Res() res: Response) {
    const secret = process.env["VAPI_WEBHOOK_SECRET"];
    if (secret) {
      const signature = req.headers["x-vapi-signature"] as string | undefined;
      const rawBody: Buffer = (req as any).rawBody ?? Buffer.from(JSON.stringify(req.body));
      if (!signature) return res.status(401).json({ error: "Missing signature" });
      const expected = createHmac("sha256", secret).update(rawBody).digest("hex");
      try {
        const match = timingSafeEqual(Buffer.from(signature, "hex"), Buffer.from(expected, "hex"));
        if (!match) return res.status(401).json({ error: "Invalid signature" });
      } catch {
        return res.status(401).json({ error: "Invalid signature" });
      }
    }
    const result = await this.vapiService.handleWebhook(req);
    return res.json(result);
  }

  @Get("assistants")
  @UseGuards(SessionGuard)
  listAssistants() {
    return this.vapiService.listAssistants();
  }

  @Get("assistants/:id")
  @UseGuards(SessionGuard)
  getAssistant(@Param("id") id: string) {
    return this.vapiService.getAssistant(id);
  }

  @Post("assistants")
  @UseGuards(SessionGuard)
  createAssistant(@Body() body: any) {
    return this.vapiService.createAssistant(body);
  }

  @Patch("assistants/:id")
  @UseGuards(SessionGuard)
  updateAssistant(@Param("id") id: string, @Body() body: any) {
    return this.vapiService.updateAssistant(id, body);
  }

  @Delete("assistants/:id")
  @UseGuards(SessionGuard)
  deleteAssistant(@Param("id") id: string) {
    return this.vapiService.deleteAssistant(id);
  }

  @Get("calls")
  @UseGuards(SessionGuard)
  listCalls() {
    return this.vapiService.listCalls();
  }

  @Get("call-logs")
  @UseGuards(SessionGuard)
  getCallLogs(@Req() req: any) {
    const userId = this.vapiService.getSessionUserId(req);
    return this.vapiService.getCallLogs(userId);
  }
}
