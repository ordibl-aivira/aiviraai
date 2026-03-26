import { Controller, Get, Post, Patch, Delete, Param, Body, HttpCode, UseGuards } from "@nestjs/common";
import { TasksService } from "./tasks.service";
import { SessionGuard } from "../common/guards/session.guard";
import { CreateTaskBody, UpdateTaskBody } from "@workspace/api-zod";

@Controller("tasks")
@UseGuards(SessionGuard)
export class TasksController {
  constructor(private readonly tasksService: TasksService) {}

  @Get()
  findAll() {
    return this.tasksService.findAll();
  }

  @Post()
  create(@Body() body: unknown) {
    return this.tasksService.create(CreateTaskBody.parse(body));
  }

  @Patch(":id")
  update(@Param("id") id: string, @Body() body: unknown) {
    return this.tasksService.update(id, UpdateTaskBody.parse(body));
  }

  @Delete(":id")
  @HttpCode(204)
  remove(@Param("id") id: string) {
    return this.tasksService.remove(id);
  }
}
