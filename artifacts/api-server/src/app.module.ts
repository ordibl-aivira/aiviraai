import { Module } from "@nestjs/common";
import { AuthModule } from "./auth/auth.module";
import { AgentsModule } from "./agents/agents.module";
import { WorkflowsModule } from "./workflows/workflows.module";
import { TasksModule } from "./tasks/tasks.module";
import { IntegrationsModule } from "./integrations/integrations.module";
import { ApprovalsModule } from "./approvals/approvals.module";
import { MemoryModule } from "./memory/memory.module";
import { AnalyticsModule } from "./analytics/analytics.module";
import { ProfileModule } from "./profile/profile.module";
import { ActionLogsModule } from "./action-logs/action-logs.module";
import { SeedModule } from "./seed/seed.module";
import { VapiModule } from "./vapi/vapi.module";
import { ElevenLabsModule } from "./elevenlabs/elevenlabs.module";
import { HealthModule } from "./health/health.module";

@Module({
  imports: [
    AuthModule,
    AgentsModule,
    WorkflowsModule,
    TasksModule,
    IntegrationsModule,
    ApprovalsModule,
    MemoryModule,
    AnalyticsModule,
    ProfileModule,
    ActionLogsModule,
    SeedModule,
    VapiModule,
    ElevenLabsModule,
    HealthModule,
  ],
})
export class AppModule {}
