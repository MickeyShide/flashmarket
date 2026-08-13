import socket
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit, urlunsplit

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def resolve_url_ipv4(url_str: str) -> str:
    try:
        parsed = urlsplit(url_str)
        if parsed.hostname and not parsed.hostname.replace(".", "").isdigit():
            port = parsed.port or 5432
            infos = socket.getaddrinfo(
                parsed.hostname, port, family=socket.AF_INET, type=socket.SOCK_STREAM
            )
            if infos:
                ip = str(infos[0][4][0])
                netloc = parsed.netloc.replace(parsed.hostname, str(ip), 1)
                return urlunsplit(parsed._replace(netloc=netloc))
    except Exception:
        pass
    return url_str


def utc_now() -> datetime:
    """Return the current UTC-aware datetime."""
    return datetime.now(UTC)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="INVENTORY_",
        extra="ignore",
    )

    app_name: str = "FlashMarket Inventory"
    environment: Literal["development", "test", "production"] = "development"
    debug: bool = False
    database_url: str = "postgresql+asyncpg://shide:shide@shide-postgres:5432/inventory"
    database_api_pool_size: int = Field(default=3, ge=1, le=20)
    database_api_max_overflow: int = Field(default=2, ge=0, le=20)
    database_worker_pool_size: int = Field(default=1, ge=1, le=10)
    database_worker_max_overflow: int = Field(default=1, ge=0, le=10)
    database_pool_timeout_seconds: float = Field(default=5.0, gt=0, le=60)
    database_pool_recycle_seconds: int = Field(default=1800, ge=60, le=86400)
    redis_url: str = "redis://shide-redis:6379/2"
    stock_cache_ttl_seconds: int = Field(default=30, gt=0)
    redis_socket_timeout_seconds: float = Field(default=0.2, gt=0)
    log_file_path: str | None = None
    prometheus_multiproc_dir: str | None = None
    docs_enabled: bool = True
    trusted_hosts: list[str] = Field(default_factory=lambda: ["localhost", "127.0.0.1"])
    cors_origins: list[str] = Field(default_factory=list)
    reservation_ttl_seconds: int = 300
    drops_base_url: str = "http://drops:8000"
    drops_timeout_seconds: float = Field(default=1.0, gt=0, le=10)
    expiry_poll_interval_seconds: float = Field(default=5.0, ge=1, le=300)
    rabbitmq_url: str = "amqp://shide:shide@shide-rabbitmq:5672/flashmarket"
    rabbitmq_exchange: str = "flashmarket.events"
    allow_insecure_internal_services: bool = False
    outbox_batch_size: int = Field(default=100, ge=1, le=1000)
    outbox_poll_interval_seconds: float = Field(default=1.0, ge=0.1, le=60)
    rabbitmq_publish_timeout_seconds: float = Field(default=5.0, gt=0, le=60)
    rabbitmq_retry_delays_seconds: tuple[int, int, int] = (5, 30, 120)
    rabbitmq_reconnect_initial_seconds: float = Field(default=1.0, gt=0, le=60)
    rabbitmq_reconnect_max_seconds: float = Field(default=30.0, gt=0, le=600)
    outbox_claim_lease_seconds: int = Field(default=30, ge=5, le=600)
    outbox_max_backoff_seconds: float = Field(default=300.0, ge=1, le=3600)
    worker_heartbeat_interval_seconds: float = Field(default=10.0, ge=1, le=60)
    worker_heartbeat_stale_seconds: int = Field(default=45, ge=10, le=600)
    jwt_public_key_dir: Path = Path("keys/public")
    jwt_algorithm: str = "EdDSA"
    jwt_issuer: str = "flashmarket-auth"
    jwt_audience: str = "flashmarket-api"

    @model_validator(mode="after")
    def validate_production_settings(self) -> Settings:
        """Enforce strict settings in production."""
        if self.environment != "production":
            return self

        errors: list[str] = []
        if self.debug:
            errors.append("INVENTORY_DEBUG must be false")
        if self.docs_enabled:
            errors.append("INVENTORY_DOCS_ENABLED must be false")
        if "flashmarket:flashmarket@" in self.database_url or (
            ":shide@" in self.database_url and "shide-postgres" in self.database_url
        ):
            errors.append("default database credentials are forbidden")
        if "localhost" in self.database_url or "127.0.0.1" in self.database_url:
            errors.append("INVENTORY_DATABASE_URL must point to production database")
        db_is_internal = self.allow_insecure_internal_services
        if "sslmode" not in self.database_url and not db_is_internal:
            errors.append("INVENTORY_DATABASE_URL must use TLS (sslmode)")
        if "localhost" in self.redis_url or "127.0.0.1" in self.redis_url:
            errors.append("INVENTORY_REDIS_URL must point to production Redis")
        redis_is_internal = self.allow_insecure_internal_services and urlsplit(
            self.redis_url
        ).hostname in {"redis", "shide-redis"}
        if not self.redis_url.startswith("rediss://") and not redis_is_internal:
            errors.append("INVENTORY_REDIS_URL must use TLS (rediss://)")
        if "localhost" in self.rabbitmq_url or "127.0.0.1" in self.rabbitmq_url:
            errors.append("INVENTORY_RABBITMQ_URL must point to production RabbitMQ")
        rabbitmq_is_internal = self.allow_insecure_internal_services and urlsplit(
            self.rabbitmq_url
        ).hostname in {"rabbitmq", "shide-rabbitmq"}
        if not self.rabbitmq_url.startswith("amqps://") and not rabbitmq_is_internal:
            errors.append("INVENTORY_RABBITMQ_URL must use TLS (amqps://)")
        if "flashmarket:flashmarket@" in self.rabbitmq_url or (
            ":shide@" in self.rabbitmq_url and "shide-rabbitmq" in self.rabbitmq_url
        ):
            errors.append("default RabbitMQ credentials are forbidden")
        if "*" in self.cors_origins:
            errors.append("wildcard CORS origins are forbidden")
        if "*" in self.trusted_hosts:
            errors.append("wildcard trusted hosts are forbidden")
        if errors:
            raise ValueError("Invalid production configuration: " + "; ".join(errors))
        return self

    @model_validator(mode="after")
    def resolve_dns_ipv4(self) -> Settings:
        if self.database_url:
            self.database_url = resolve_url_ipv4(self.database_url)
        return self


@lru_cache
def get_settings() -> Settings:
    """Return the cached application settings."""
    return Settings()
