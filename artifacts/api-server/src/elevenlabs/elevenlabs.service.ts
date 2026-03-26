import { Injectable, UnauthorizedException } from "@nestjs/common";
import { ElevenLabsClient } from "@elevenlabs/elevenlabs-js";

function getClient(): ElevenLabsClient {
  const apiKey = process.env["ELEVENLABS_API_KEY"];
  if (!apiKey) throw new Error("ELEVENLABS_API_KEY is not configured");
  return new ElevenLabsClient({ apiKey });
}

@Injectable()
export class ElevenLabsService {
  getSessionUserId(req: any): string {
    const userId = req.session?.userId;
    if (!userId) throw new UnauthorizedException();
    return userId;
  }

  async listVoices() {
    const client = getClient();
    const res = await client.voices.getAll();
    return res.voices;
  }

  async getVoice(voiceId: string) {
    const client = getClient();
    return client.voices.get(voiceId);
  }

  async listModels() {
    const client = getClient();
    return client.models.getAll();
  }

  async textToSpeech(voiceId: string, text: string, modelId?: string) {
    const client = getClient();
    const audio = await client.textToSpeech.convert(voiceId, {
      text,
      model_id: modelId ?? "eleven_multilingual_v2",
      output_format: "mp3_44100_128",
    });
    const chunks: Buffer[] = [];
    for await (const chunk of audio as AsyncIterable<Buffer>) {
      chunks.push(chunk);
    }
    return Buffer.concat(chunks);
  }

  async getConvaiSignedUrl(agentId: string) {
    const client = getClient();
    const res = await (client as any).conversationalAi.getSignedUrl({ agentId });
    return res;
  }

  async listConvaiAgents() {
    const client = getClient();
    const res = await (client as any).conversationalAi.getAgents({});
    return res?.agents ?? [];
  }

  async getConvaiAgent(agentId: string) {
    const client = getClient();
    return (client as any).conversationalAi.getAgent(agentId);
  }

  async getUserSubscription() {
    const client = getClient();
    return (client as any).user.getSubscription();
  }
}
