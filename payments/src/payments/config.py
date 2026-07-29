from datetime import UTC, datetime
from functools import lru_cache
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def utc_now() -> datetime:
    """Return the current UTC-aware datetime."""
    return datetime.now(UTC)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="PAYMENTS_",
        extra="ignore",
    )

    app_name: str = "FlashMarket Payments"
    environment: Literal["development", "test", "production"] = "development"
    debug: bool = False
    database_url: str = "postgresql+asyncpg://flashmarket:flashmarket@localhost:5436/payments"
    docs_enabled: bool = True
    trusted_hosts: list[str] = Field(default_factory=lambda: ["localhost", "127.0.0.1"])
    cors_origins: list[str] = Field(default_factory=list)
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    rabbitmq_exchange: str = "flashmarket.events"
    allow_insecure_internal_services: bool = False
    payment_timeout_seconds: int = 300
    outbox_batch_size: int = Field(default=100, ge=1, le=1000)
    outbox_poll_interval_seconds: float = Field(default=1.0, ge=0.1, le=60)

    @model_validator(mode="after")
    def validate_production_settings(self) -> Settings:
        """Enforce strict settings in production."""
        if self.environment != "production":
            return self

        errors: list[str] = []
        if self.debug:
            errors.append("PAYMENTS_DEBUG must be false")
        if self.docs_enabled:
            errors.append("PAYMENTS_DOCS_ENABLED must be false")
        if "flashmarket:flashmarket@" in self.database_url:
            errors.append("default database credentials are forbidden")
        if "localhost" in self.database_url or "127.0.0.1" in self.database_url:
            errors.append("PAYMENTS_DATABASE_URL must point to production database")
        db_is_internal = (
            self.allow_insecure_internal_services
            and urlsplit(self.database_url).hostname == "postgres"
        )
        if "sslmode" not in self.database_url and not db_is_internal:
            errors.append("PAYMENTS_DATABASE_URL must use TLS (sslmode)")
        if "localhost" in self.rabbitmq_url or "127.0.0.1" in self.rabbitmq_url:
            errors.append("PAYMENTS_RABBITMQ_URL must point to production RabbitMQ")
        rabbitmq_is_internal = (
            self.allow_insecure_internal_services
            and urlsplit(self.rabbitmq_url).hostname == "rabbitmq"
        )
        if not self.rabbitmq_url.startswith("amqps://") and not rabbitmq_is_internal:
            errors.append("PAYMENTS_RABBITMQ_URL must use TLS (amqps://)")
        if "*" in self.cors_origins:
            errors.append("wildcard CORS origins are forbidden")
        if "*" in self.trusted_hosts:
            errors.append("wildcard trusted hosts are forbidden")
        if errors:
            raise ValueError("Invalid production configuration: " + "; ".join(errors))
        return self


@lru_cache
def get_settings() -> Settings:
    """Return the cached application settings."""
    return Settings()
