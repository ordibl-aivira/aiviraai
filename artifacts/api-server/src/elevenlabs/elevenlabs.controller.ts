import { Controller, Get, Post, Param, Body, Req, Res, UseGuards } from "@nestjs/common";
import type { Response } from "express";
import { ElevenLabsService } from "./elevenlabs.service";
import { SessionGuard } from "../common/guards/session.guard";

@Controller("elevenlabs")
@UseGuards(SessionGuard)
export class ElevenLabsController {
  constructor(private readonly elevenLabsService: ElevenLabsService) {}

  @Get("voices")
  listVoices(@Req() req: any) {
    this.elevenLabsService.getSessionUserId(req);
    return this.elevenLabsService.listVoices();
  }

  @Get("voices/:voiceId")
  getVoice(@Req() req: any, @Param("voiceId") voiceId: string) {
    this.elevenLabsService.getSessionUserId(req);
    return this.elevenLabsService.getVoice(voiceId);
  }

  @Get("models")
  listModels(@Req() req: any) {
    this.elevenLabsService.getSessionUserId(req);
    return this.elevenLabsService.listModels();
  }

  @Post("tts/:voiceId")
  async textToSpeech(
    @Req() req: any,
    @Res() res: Response,
    @Param("voiceId") voiceId: string,
    @Body() body: { text: string; modelId?: string },
  ) {
    this.elevenLabsService.getSessionUserId(req);
    const audio = await this.elevenLabsService.textToSpeech(voiceId, body.text, body.modelId);
    res.set({ "Content-Type": "audio/mpeg", "Content-Length": audio.length });
    return res.send(audio);
  }

  @Get("convai/signed-url")
  getSignedUrl(@Req() req: any) {
    this.elevenLabsService.getSessionUserId(req);
    const agentId = req.query.agentId as string;
    return this.elevenLabsService.getConvaiSignedUrl(agentId);
  }

  @Get("convai/agents")
  listConvaiAgents(@Req() req: any) {
    this.elevenLabsService.getSessionUserId(req);
    return this.elevenLabsService.listConvaiAgents();
  }

  @Get("convai/agents/:agentId")
  getConvaiAgent(@Req() req: any, @Param("agentId") agentId: string) {
    this.elevenLabsService.getSessionUserId(req);
    return this.elevenLabsService.getConvaiAgent(agentId);
  }

  @Get("subscription")
  getUserSubscription(@Req() req: any) {
    this.elevenLabsService.getSessionUserId(req);
    return this.elevenLabsService.getUserSubscription();
  }
}
