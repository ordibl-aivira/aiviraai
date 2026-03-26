import { Controller, Get, Post, Param, Body, Query, Req, UseGuards } from "@nestjs/common";
import { ApprovalsService } from "./approvals.service";
import { SessionGuard } from "../common/guards/session.guard";

@Controller("approvals")
@UseGuards(SessionGuard)
export class ApprovalsController {
  constructor(private readonly approvalsService: ApprovalsService) {}

  @Get()
  findAll(@Query("status") status?: string) {
    return this.approvalsService.findAll(status);
  }

  @Post()
  create(@Body() body: any) {
    return this.approvalsService.create(body);
  }

  @Post(":id/approve")
  approve(@Param("id") id: string, @Req() req: any) {
    const resolvedBy = req.session?.user?.name ?? "Admin";
    return this.approvalsService.approve(id, resolvedBy);
  }

  @Post(":id/reject")
  reject(@Param("id") id: string, @Req() req: any) {
    const resolvedBy = req.session?.user?.name ?? "Admin";
    return this.approvalsService.reject(id, resolvedBy);
  }
}
