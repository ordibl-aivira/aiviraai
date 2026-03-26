import { Controller, Get, Post, Delete, Param, Body, HttpCode, UseGuards } from "@nestjs/common";
import { WorkflowsService } from "./workflows.service";
import { SessionGuard } from "../common/guards/session.guard";
import { CreateWorkflowBody } from "@workspace/api-zod";

@Controller("workflows")
@UseGuards(SessionGuard)
export class WorkflowsController {
  constructor(private readonly workflowsService: WorkflowsService) {}

  @Get()
  findAll() {
    return this.workflowsService.findAll();
  }

  @Get(":id")
  findOne(@Param("id") id: string) {
    return this.workflowsService.findOne(id);
  }

  @Post()
  create(@Body() body: unknown) {
    return this.workflowsService.create(CreateWorkflowBody.parse(body));
  }

  @Delete(":id")
  @HttpCode(204)
  remove(@Param("id") id: string) {
    return this.workflowsService.remove(id);
  }

  @Post(":id/run")
  run(@Param("id") id: string) {
    return this.workflowsService.run(id);
  }
}
