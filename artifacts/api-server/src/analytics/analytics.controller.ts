import { Controller, Get, UseGuards } from "@nestjs/common";
import { AnalyticsService } from "./analytics.service";
import { SessionGuard } from "../common/guards/session.guard";

@Controller("analytics")
@UseGuards(SessionGuard)
export class AnalyticsController {
  constructor(private readonly analyticsService: AnalyticsService) {}

  @Get("overview")
  getOverview() {
    return this.analyticsService.getOverview();
  }

  @Get("activity")
  getActivity() {
    return this.analyticsService.getActivity();
  }
}
