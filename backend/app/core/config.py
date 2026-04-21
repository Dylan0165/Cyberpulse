"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # General
    app_env: str = "development"
    app_name: str = "AutoPentest AI"
    secret_key: str = "CHANGE-ME"
    backend_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:3000"

    # PostgreSQL
    postgres_user: str = "autopentest"
    postgres_password: str = ""
    postgres_db: str = "autopentest"
    postgres_host: str = "postgres"
    postgres_port: int = 5432

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def database_url_sync(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    # Redis
    redis_password: str = ""
    redis_url: str = "redis://:@redis:6379/0"
    celery_broker_url: str = "redis://:@redis:6379/1"
    celery_result_backend: str = "redis://:@redis:6379/2"

    # Clerk
    clerk_secret_key: str = ""
    clerk_webhook_secret: str = ""

    # Stripe
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_starter_price_id: str = ""
    stripe_professional_price_id: str = ""
    stripe_business_price_id: str = ""
    stripe_single_scan_price_id: str = ""

    # Anthropic
    anthropic_api_key: str = ""
    claude_model: str = "claude-opus-4-20250514"

    # Scanner
    scanner_image: str = "autopentest-scanner:latest"
    scanner_network: str = "scanner-isolated"
    max_scan_duration_seconds: int = 28800
    scan_container_memory_limit: str = "2g"
    scan_container_cpu_limit: float = 2.0

    # CyberPulse engine (separate container on port 7823)
    cyberpulse_url: str = "http://cyberpulse-web:7823"

    # External APIs
    shodan_api_key: str = ""
    haveibeenpwned_api_key: str = ""
    virustotal_api_key: str = ""

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache()
def get_settings() -> Settings:
    return Settings()
