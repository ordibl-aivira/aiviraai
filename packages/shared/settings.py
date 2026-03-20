from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for all Workforce OS services."""

    app_name: str = "ordibl-workforce-os"
    environment: str = "development"

    # Service ports
    api_gateway_port: int = 8000
    agent_runtime_port: int = 8001
    ordibl_adapter_port: int = 8002
    workflow_engine_port: int = 8003
    memory_service_port: int = 8004
    integration_service_port: int = 8005
    auth_service_port: int = 8006
    organization_service_port: int = 8007
    analytics_service_port: int = 8008
    notification_service_port: int = 8009

    # Research Agent settings
    research_default_sources: str = "crm,memory,public_data"
    research_max_results: int = 10
    research_confidence_threshold: float = 0.3

    # Content Agent settings
    content_default_tone: str = "professional"
    content_default_language: str = "en"
    content_max_variants: int = 3

    # Motion Engine settings
    motion_default_sla_hours: int = 48
    motion_max_sequence_steps: int = 20
    motion_retry_delay_hours: int = 24

    # Execution Engine settings
    execution_max_retries: int = 3
    execution_retry_backoff_seconds: float = 5.0
    execution_idempotency_ttl_hours: int = 24

    # Infrastructure
    redis_url: str = "redis://redis:6379/0"
    postgres_dsn: str = "postgresql://postgres:postgres@postgres:5432/ordibl"
    qdrant_url: str = "http://qdrant:6333"
    qdrant_collection: str = "workforce_knowledge"

    # Internal service URLs
    agent_runtime_url: str = "http://agent-runtime:8001"
    ordibl_adapter_url: str = "http://ordibl-adapter:8002"
    workflow_engine_url: str = "http://workflow-engine:8003"
    memory_service_url: str = "http://memory-service:8004"
    integration_service_url: str = "http://integration-service:8005"
    auth_service_url: str = "http://auth-service:8006"
    organization_service_url: str = "http://organization-service:8007"
    analytics_service_url: str = "http://analytics-service:8008"
    notification_service_url: str = "http://notification-service:8009"

    # Cognitive → Execution Stack service URLs
    research_agent_url: str = "http://research-agent:8010"
    content_agent_url: str = "http://content-agent:8011"
    motion_engine_url: str = "http://motion-engine:8012"
    execution_engine_url: str = "http://execution-engine:8013"

    # Cognitive Stack service ports
    research_agent_port: int = 8010
    content_agent_port: int = 8011
    motion_engine_port: int = 8012
    execution_engine_port: int = 8013

    # Auth
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 60

    # Agent runtime
    default_max_agent_steps: int = 20
    default_max_tokens_per_step: int = 4096
    default_agent_timeout_seconds: int = 300

    # ── Generative AI Configuration ─────────────────────────────
    # Primary model for agent reasoning
    ai_primary_model: str = "gpt-4o"
    ai_fallback_model: str = "gpt-4o-mini"
    ai_embedding_model: str = "text-embedding-3-small"
    ai_provider: str = "openai"  # openai | anthropic | azure_openai | local

    # Model behaviour defaults
    ai_temperature: float = 0.3  # low temperature for deterministic agent behaviour
    ai_max_completion_tokens: int = 4096
    ai_top_p: float = 1.0
    ai_frequency_penalty: float = 0.0
    ai_presence_penalty: float = 0.0

    # Guardrails
    ai_enable_content_filter: bool = True
    ai_max_retries: int = 3
    ai_retry_delay_seconds: float = 1.0
    ai_request_timeout_seconds: int = 60

    # Cost controls
    ai_max_tokens_per_task: int = 32_000
    ai_max_tool_calls_per_step: int = 5
    ai_budget_alert_threshold_usd: float = 10.0

    # Prompt engineering
    ai_system_prompt_version: str = "v1"
    ai_enable_chain_of_thought: bool = True
    ai_enable_structured_output: bool = True
    ai_enable_tool_use: bool = True

    # Observability
    ai_log_prompts: bool = False  # never enable in production with PII
    ai_log_completions: bool = False
    ai_trace_llm_calls: bool = True

    # Provider endpoints (override for Azure OpenAI or local models)
    openai_api_key: str = ""
    openai_api_base: str = "https://api.openai.com/v1"
    anthropic_api_key: str = ""
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_deployment: str = ""
    local_model_url: str = "http://localhost:11434"  # Ollama default

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
