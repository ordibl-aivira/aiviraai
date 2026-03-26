import "reflect-metadata";
import { NestFactory } from "@nestjs/core";
import { AppModule } from "./app.module";
import session from "express-session";
import connectPgSimple from "connect-pg-simple";
import { pool } from "@workspace/db";

async function bootstrap() {
  const port = Number(process.env["PORT"]);
  if (!port || Number.isNaN(port)) {
    throw new Error("PORT environment variable is required");
  }

  const app = await NestFactory.create(AppModule, { logger: ["error", "warn", "log"] });

  app.enableCors({ origin: true, credentials: true });

  const PgSession = connectPgSimple(session as any);
  const isProd = process.env["NODE_ENV"] === "production";

  app.use(
    session({
      store: new PgSession({
        pool,
        tableName: "session",
        pruneSessionInterval: 60 * 15,
      }),
      secret: process.env["SESSION_SECRET"] || "aivira-os-dev-secret-change-in-prod",
      resave: false,
      saveUninitialized: false,
      name: "aivira.sid",
      cookie: {
        httpOnly: true,
        secure: isProd,
        sameSite: isProd ? "none" : "lax",
        maxAge: 7 * 24 * 60 * 60 * 1000,
      },
    } as any),
  );

  app.setGlobalPrefix("api");

  await app.listen(port);
  console.log(`[NestJS] Aivira OS API running on port ${port}`);
}

bootstrap();
