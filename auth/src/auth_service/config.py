from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="AUTH_",
        extra="ignore",
    )

    app_name: str = "FlashMarket Auth"
    environment: Literal["development", "test", "production"] = "development"
    debug: bool = False
    database_url: str = "postgresql+asyncpg://flashmarket:flashmarket@localhost:5432/auth"
    redis_url: str = "redis://localhost:6379/0"
    rabbitmq_url: str = "amqp://flashmarket:flashmarket@localhost:5672/"
    allow_insecure_internal_services: bool = False
    rabbitmq_exchange: str = "flashmarket.events"
    outbox_batch_size: int = Field(default=100, ge=1, le=1000)
    outbox_poll_interval_seconds: float = Field(default=1.0, ge=0.1, le=60)

    jwt_keys_directory: Path = Path("keys")
    jwt_key_id: str = Field(
        default="flashmarket-auth-ed25519-v1",
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9._-]+$",
    )
    jwt_algorithm: Literal["EdDSA"] = "EdDSA"
    jwt_issuer: str = "flashmarket-auth"
    jwt_audience: str = "flashmarket-api"
    access_token_ttl_minutes: int = Field(default=5, ge=1, le=15)
    session_ttl_days: int = Field(default=30, ge=1, le=365)
    session_touch_interval_minutes: int = Field(default=5, ge=1, le=60)

    cors_origins: list[str] = Field(default_factory=list)
    trusted_proxy_ips: list[str] = Field(default_factory=list)
    trusted_hosts: list[str] = Field(
        default_factory=lambda: ["localhost", "127.0.0.1", "test", "postgres-test"]
    )
    docs_enabled: bool = True

    refresh_token_transport: Literal["cookie", "body"] = "cookie"
    refresh_cookie_name: str = "flashmarket_refresh"
    csrf_cookie_name: str = "flashmarket_csrf"
    refresh_cookie_secure: bool = False
    refresh_cookie_samesite: Literal["strict", "lax"] = "strict"

    rate_limit_enabled: bool = True
    log_file_path: str | None = None
    prometheus_multiproc_dir: str | None = None
    login_ip_rate_limit: int = Field(default=20, ge=1, le=1000)
    login_account_rate_limit: int = Field(default=5, ge=1, le=1000)
    login_rate_window_seconds: int = Field(default=60, ge=1, le=86400)
    register_rate_limit: int = Field(default=5, ge=1, le=1000)
    register_rate_window_seconds: int = Field(default=3600, ge=1, le=86400)
    refresh_rate_limit: int = Field(default=30, ge=1, le=1000)
    refresh_rate_window_seconds: int = Field(default=300, ge=1, le=86400)
    introspection_rate_limit: int = Field(default=300, ge=1, le=10000)
    introspection_rate_window_seconds: int = Field(default=60, ge=1, le=86400)

    expired_data_retention_days: int = Field(default=30, ge=1, le=3650)
    audit_retention_days: int = Field(default=365, ge=30, le=3650)

    @model_validator(mode="after")
    def validate_production_settings(self) -> Settings:
        """Validate production settings."""
        if self.environment != "production":
            return self

        errors: list[str] = []
        if self.debug:
            errors.append("AUTH_DEBUG must be false")
        if self.docs_enabled:
            errors.append("AUTH_DOCS_ENABLED must be false")
        if not self.rate_limit_enabled:
            errors.append("AUTH_RATE_LIMIT_ENABLED must be true")
        if "*" in self.cors_origins:
            errors.append("wildcard CORS origins are forbidden")
        if "*" in self.trusted_hosts:
            errors.append("wildcard trusted hosts are forbidden")
        if "flashmarket:flashmarket@" in self.database_url:
            errors.append("default database credentials are forbidden")
        if "localhost" in self.redis_url or "127.0.0.1" in self.redis_url:
            errors.append("AUTH_REDIS_URL must point to production Redis")
        redis_is_internal = (
            self.allow_insecure_internal_services and urlsplit(self.redis_url).hostname == "redis"
        )
        if not self.redis_url.startswith("rediss://") and not redis_is_internal:
            errors.append("AUTH_REDIS_URL must use TLS (rediss://)")
        if "localhost" in self.rabbitmq_url or "127.0.0.1" in self.rabbitmq_url:
            errors.append("AUTH_RABBITMQ_URL must point to production RabbitMQ")
        rabbitmq_is_internal = (
            self.allow_insecure_internal_services
            and urlsplit(self.rabbitmq_url).hostname == "rabbitmq"
        )
        if not self.rabbitmq_url.startswith("amqps://") and not rabbitmq_is_internal:
            errors.append("AUTH_RABBITMQ_URL must use TLS (amqps://)")
        if self.refresh_token_transport == "cookie" and not self.refresh_cookie_secure:
            errors.append("AUTH_REFRESH_COOKIE_SECURE must be true")
        if self.refresh_token_transport == "cookie" and not self.refresh_cookie_name.startswith(
            "__Host-"
        ):
            errors.append("AUTH_REFRESH_COOKIE_NAME must use the __Host- prefix")
        if errors:
            raise ValueError("Invalid production configuration: " + "; ".join(errors))
        return self


@lru_cache
def get_settings() -> Settings:
    """Return the cached application settings."""
    return Settings()  # type: ignore[call-arg]
