import { Controller, Get, Post, Body, Query, HttpCode, UseGuards } from "@nestjs/common";
import { ActionLogsService } from "./action-logs.service";
import { SessionGuard } from "../common/guards/session.guard";

@Controller("action-logs")
@UseGuards(SessionGuard)
export class ActionLogsController {
  constructor(private readonly actionLogsService: ActionLogsService) {}

  @Get()
  findByTask(@Query("taskId") taskId: string) {
    return this.actionLogsService.findByTask(taskId);
  }

  @Post()
  @HttpCode(201)
  create(@Body() body: any) {
    return this.actionLogsService.create(body);
  }
}
