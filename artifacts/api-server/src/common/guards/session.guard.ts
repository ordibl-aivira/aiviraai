import { CanActivate, ExecutionContext, Injectable, UnauthorizedException } from "@nestjs/common";

@Injectable()
export class SessionGuard implements CanActivate {
  canActivate(context: ExecutionContext): boolean {
    const req = context.switchToHttp().getRequest();
    const userId = req.session?.userId;
    if (!userId) {
      throw new UnauthorizedException("Not authenticated");
    }
    return true;
  }
}
