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

    # Auth
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 60

    # Agent runtime
    default_max_agent_steps: int = 20
    default_max_tokens_per_step: int = 4096
    default_agent_timeout_seconds: int = 300

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
