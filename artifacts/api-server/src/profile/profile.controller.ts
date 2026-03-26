import { Controller, Get, Post, Body, Req, UseGuards } from "@nestjs/common";
import { ProfileService } from "./profile.service";
import { SessionGuard } from "../common/guards/session.guard";

@Controller("profile")
@UseGuards(SessionGuard)
export class ProfileController {
  constructor(private readonly profileService: ProfileService) {}

  @Get()
  getProfile(@Req() req: any) {
    return this.profileService.getProfile(req);
  }

  @Post()
  saveProfile(@Req() req: any, @Body() body: any) {
    return this.profileService.saveProfile(req, body);
  }
}
