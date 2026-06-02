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

    # DeepSeek AI
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    deepseek_model: str = "deepseek-chat"

    # Scanner
    scanner_image: str = "autopentest-scanner:latest"
    scanner_network: str = "scanner-isolated"
    max_scan_duration_seconds: int = 28800
    scan_container_memory_limit: str = "2g"
    scan_container_cpu_limit: float = 2.0

    # CyberPulse engine (separate container on port 7823)
    cyberpulse_url: str = "http://cyberpulse-web:7823"

    # Kali VM scanner
    kali_vm_host: str = "192.168.121.28"
    kali_vm_port: int = 5001
    scanner_api_key: str = ""

    # External APIs
    shodan_api_key: str = ""
    haveibeenpwned_api_key: str = ""
    virustotal_api_key: str = ""

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache()
def get_settings() -> Settings:
    return Settings()
