import { Module } from "@nestjs/common";
import { ElevenLabsController } from "./elevenlabs.controller";
import { ElevenLabsService } from "./elevenlabs.service";

@Module({
  controllers: [ElevenLabsController],
  providers: [ElevenLabsService],
})
export class ElevenLabsModule {}
