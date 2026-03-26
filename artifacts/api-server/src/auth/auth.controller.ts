import { Controller, Get, Post, Req, Res, Body, Query } from "@nestjs/common";
import type { Request, Response } from "express";
import { AuthService } from "./auth.service";
import axios from "axios";

function getBaseUrl(req: Request): string {
  if (process.env["APP_URL"]) return process.env["APP_URL"];
  const proto = req.get("x-forwarded-proto") || req.protocol || "https";
  const host = req.get("x-forwarded-host") || req.get("host") || "localhost";
  return `${proto}://${host}`;
}

function getFrontendUrl(req: Request): string {
  if (process.env["FRONTEND_URL"]) return process.env["FRONTEND_URL"];
  return getBaseUrl(req);
}

@Controller("auth")
export class AuthController {
  constructor(private readonly authService: AuthService) {}

  @Get("me")
  async getMe(@Req() req: Request, @Res() res: Response) {
    const userId = (req as any).session?.userId;
    if (!userId) return res.status(401).json({ user: null });
    const user = await this.authService.findById(userId);
    if (!user) return res.status(401).json({ user: null });
    return res.json({
      user: { id: user.id, email: user.email, name: user.name, avatarUrl: user.avatarUrl, provider: user.provider },
    });
  }

  @Post("logout")
  logout(@Req() req: Request, @Res() res: Response) {
    (req as any).session?.destroy(() => {
      res.clearCookie("aivira.sid");
      res.json({ ok: true });
    });
  }

  @Post("demo")
  async demoLogin(@Body() body: any, @Req() req: Request, @Res() res: Response) {
    const { name = "Demo User", email = "demo@aivira.co" } = body;
    const user = await this.authService.upsertUser({ email, name, provider: "email", providerId: null });
    (req as any).session.userId = user.id;
    return res.json({ user: { id: user.id, email: user.email, name: user.name, avatarUrl: user.avatarUrl } });
  }

  @Get("google")
  googleAuth(@Req() req: Request, @Res() res: Response) {
    const clientId = process.env["GOOGLE_CLIENT_ID"];
    if (!clientId) return res.redirect(`${getFrontendUrl(req)}/login?error=not_configured`);
    const redirectUri = `${getBaseUrl(req)}/api/auth/google/callback`;
    const url = `https://accounts.google.com/o/oauth2/v2/auth?client_id=${clientId}&redirect_uri=${encodeURIComponent(redirectUri)}&response_type=code&scope=openid%20email%20profile&prompt=select_account`;
    return res.redirect(url);
  }

  @Get("google/callback")
  async googleCallback(@Query("code") code: string, @Req() req: Request, @Res() res: Response) {
    const clientId = process.env["GOOGLE_CLIENT_ID"];
    const clientSecret = process.env["GOOGLE_CLIENT_SECRET"];
    const frontendUrl = getFrontendUrl(req);
    if (!clientId || !clientSecret) return res.redirect(`${frontendUrl}/login?error=not_configured`);
    try {
      const redirectUri = `${getBaseUrl(req)}/api/auth/google/callback`;
      const tokenRes = await axios.post("https://oauth2.googleapis.com/token", {
        code, client_id: clientId, client_secret: clientSecret, redirect_uri: redirectUri, grant_type: "authorization_code",
      });
      const { access_token } = tokenRes.data;
      const profileRes = await axios.get("https://www.googleapis.com/oauth2/v3/userinfo", {
        headers: { Authorization: `Bearer ${access_token}` },
      });
      const { sub, email, name, picture } = profileRes.data;
      const user = await this.authService.upsertUser({ email, name, avatarUrl: picture, provider: "google", providerId: sub });
      (req as any).session.userId = user.id;
      return res.redirect(`${frontendUrl}/app`);
    } catch {
      return res.redirect(`${frontendUrl}/login?error=google_failed`);
    }
  }

  @Get("github")
  githubAuth(@Req() req: Request, @Res() res: Response) {
    const clientId = process.env["GITHUB_CLIENT_ID"];
    if (!clientId) return res.redirect(`${getFrontendUrl(req)}/login?error=not_configured`);
    const url = `https://github.com/login/oauth/authorize?client_id=${clientId}&scope=user:email`;
    return res.redirect(url);
  }

  @Get("github/callback")
  async githubCallback(@Query("code") code: string, @Req() req: Request, @Res() res: Response) {
    const clientId = process.env["GITHUB_CLIENT_ID"];
    const clientSecret = process.env["GITHUB_CLIENT_SECRET"];
    const frontendUrl = getFrontendUrl(req);
    if (!clientId || !clientSecret) return res.redirect(`${frontendUrl}/login?error=not_configured`);
    try {
      const tokenRes = await axios.post(
        "https://github.com/login/oauth/access_token",
        { client_id: clientId, client_secret: clientSecret, code },
        { headers: { Accept: "application/json" } },
      );
      const { access_token } = tokenRes.data;
      const profileRes = await axios.get("https://api.github.com/user", {
        headers: { Authorization: `Bearer ${access_token}`, "User-Agent": "Aivira-OS" },
      });
      const { id, email, name, login, avatar_url } = profileRes.data;
      const user = await this.authService.upsertUser({
        email: email || `${login}@github.com`, name: name || login, avatarUrl: avatar_url, provider: "github", providerId: String(id),
      });
      (req as any).session.userId = user.id;
      return res.redirect(`${frontendUrl}/app`);
    } catch {
      return res.redirect(`${frontendUrl}/login?error=github_failed`);
    }
  }

  @Get("discord")
  discordAuth(@Req() req: Request, @Res() res: Response) {
    const clientId = process.env["DISCORD_CLIENT_ID"];
    if (!clientId) return res.redirect(`${getFrontendUrl(req)}/login?error=not_configured`);
    const redirectUri = `${getBaseUrl(req)}/api/auth/discord/callback`;
    const url = `https://discord.com/api/oauth2/authorize?client_id=${clientId}&redirect_uri=${encodeURIComponent(redirectUri)}&response_type=code&scope=identify%20email`;
    return res.redirect(url);
  }

  @Get("discord/callback")
  async discordCallback(@Query("code") code: string, @Req() req: Request, @Res() res: Response) {
    const clientId = process.env["DISCORD_CLIENT_ID"];
    const clientSecret = process.env["DISCORD_CLIENT_SECRET"];
    const frontendUrl = getFrontendUrl(req);
    if (!clientId || !clientSecret) return res.redirect(`${frontendUrl}/login?error=not_configured`);
    try {
      const redirectUri = `${getBaseUrl(req)}/api/auth/discord/callback`;
      const tokenRes = await axios.post(
        "https://discord.com/api/oauth2/token",
        new URLSearchParams({ client_id: clientId, client_secret: clientSecret, grant_type: "authorization_code", code: String(code), redirect_uri: redirectUri }),
        { headers: { "Content-Type": "application/x-www-form-urlencoded" } },
      );
      const { access_token } = tokenRes.data;
      const profileRes = await axios.get("https://discord.com/api/users/@me", {
        headers: { Authorization: `Bearer ${access_token}` },
      });
      const { id, email, username, avatar } = profileRes.data;
      const avatarUrl = avatar ? `https://cdn.discordapp.com/avatars/${id}/${avatar}.png` : null;
      const user = await this.authService.upsertUser({ email, name: username, avatarUrl, provider: "discord", providerId: id });
      (req as any).session.userId = user.id;
      return res.redirect(`${frontendUrl}/app`);
    } catch {
      return res.redirect(`${frontendUrl}/login?error=discord_failed`);
    }
  }
}
