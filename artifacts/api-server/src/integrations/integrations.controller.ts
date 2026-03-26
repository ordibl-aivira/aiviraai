import { Controller, Get, Post, Param, UseGuards } from "@nestjs/common";
import { IntegrationsService } from "./integrations.service";
import { SessionGuard } from "../common/guards/session.guard";

@Controller("integrations")
@UseGuards(SessionGuard)
export class IntegrationsController {
  constructor(private readonly integrationsService: IntegrationsService) {}

  @Get()
  findAll() {
    return this.integrationsService.findAll();
  }

  @Post(":id/toggle")
  toggle(@Param("id") id: string) {
    return this.integrationsService.toggle(id);
  }
}
