import { Controller, Get, Post, Delete, Param, Body, Query, UseGuards } from "@nestjs/common";
import { MemoryService } from "./memory.service";
import { SessionGuard } from "../common/guards/session.guard";

@Controller("memory")
@UseGuards(SessionGuard)
export class MemoryController {
  constructor(private readonly memoryService: MemoryService) {}

  @Get()
  findAll(@Query("category") category?: string) {
    return this.memoryService.findAll(category);
  }

  @Post("search")
  search(@Body("query") query: string) {
    return this.memoryService.search(query);
  }

  @Post()
  create(@Body() body: any) {
    return this.memoryService.create(body);
  }

  @Delete(":id")
  remove(@Param("id") id: string) {
    return this.memoryService.remove(id);
  }
}
