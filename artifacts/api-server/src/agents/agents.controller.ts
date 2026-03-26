import { Controller, Get, Post, Patch, Delete, Param, Body, HttpCode, UseGuards } from "@nestjs/common";
import { AgentsService } from "./agents.service";
import { SessionGuard } from "../common/guards/session.guard";
import { CreateAgentBody, UpdateAgentBody } from "@workspace/api-zod";

@Controller("agents")
@UseGuards(SessionGuard)
export class AgentsController {
  constructor(private readonly agentsService: AgentsService) {}

  @Get()
  findAll() {
    return this.agentsService.findAll();
  }

  @Get(":id")
  findOne(@Param("id") id: string) {
    return this.agentsService.findOne(id);
  }

  @Post()
  create(@Body() body: unknown) {
    return this.agentsService.create(CreateAgentBody.parse(body));
  }

  @Patch(":id")
  update(@Param("id") id: string, @Body() body: unknown) {
    return this.agentsService.update(id, UpdateAgentBody.parse(body));
  }

  @Delete(":id")
  @HttpCode(204)
  remove(@Param("id") id: string) {
    return this.agentsService.remove(id);
  }

  @Post(":id/toggle")
  toggle(@Param("id") id: string) {
    return this.agentsService.toggle(id);
  }
}
