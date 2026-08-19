import socket
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
                ip = infos[0][4][0]
                netloc = parsed.netloc.replace(parsed.hostname, str(ip), 1)
                return urlunsplit(parsed._replace(netloc=netloc))
    except Exception:
        pass
    return url_str


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
    database_url: str = "postgresql+asyncpg://shide:shide@shide-postgres:5432/auth"
    database_api_pool_size: int = Field(default=3, ge=1, le=20)
    database_api_max_overflow: int = Field(default=2, ge=0, le=20)
    database_worker_pool_size: int = Field(default=1, ge=1, le=10)
    database_worker_max_overflow: int = Field(default=1, ge=0, le=10)
    database_pool_timeout_seconds: float = Field(default=5.0, gt=0, le=60)
    database_pool_recycle_seconds: int = Field(default=1800, ge=60, le=86400)
    redis_url: str = "redis://shide-redis:6379/0"
    rabbitmq_url: str = "amqp://shide:shide@shide-rabbitmq:5672/flashmarket"
    allow_insecure_internal_services: bool = False
    rabbitmq_exchange: str = "flashmarket.events"
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
    password_work_concurrency: int = Field(default=2, ge=1, le=8)
    password_work_acquire_timeout_seconds: float = Field(default=5.0, gt=0, le=60)

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
    refresh_cookie_secure: bool = True
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
        if "flashmarket:flashmarket@" in self.database_url or (
            ":shide@" in self.database_url and "shide-postgres" in self.database_url
        ):
            errors.append("default database credentials are forbidden")
        db_is_internal = self.allow_insecure_internal_services
        if "localhost" in self.database_url or "127.0.0.1" in self.database_url:
            errors.append("AUTH_DATABASE_URL must point to production database")
        if "sslmode" not in self.database_url and not db_is_internal:
            errors.append("AUTH_DATABASE_URL must use TLS (sslmode)")
        if "localhost" in self.redis_url or "127.0.0.1" in self.redis_url:
            errors.append("AUTH_REDIS_URL must point to production Redis")
        redis_is_internal = self.allow_insecure_internal_services and urlsplit(
            self.redis_url
        ).hostname in {"redis", "shide-redis", "192.168.64.4"}
        if not self.redis_url.startswith("rediss://") and not redis_is_internal:
            errors.append("AUTH_REDIS_URL must use TLS (rediss://)")
        if "localhost" in self.rabbitmq_url or "127.0.0.1" in self.rabbitmq_url:
            errors.append("AUTH_RABBITMQ_URL must point to production RabbitMQ")
        rabbitmq_is_internal = self.allow_insecure_internal_services and urlsplit(
            self.rabbitmq_url
        ).hostname in {"rabbitmq", "shide-rabbitmq", "192.168.64.4"}
        if not self.rabbitmq_url.startswith("amqps://") and not rabbitmq_is_internal:
            errors.append("AUTH_RABBITMQ_URL must use TLS (amqps://)")
        if "flashmarket:flashmarket@" in self.rabbitmq_url or (
            ":shide@" in self.rabbitmq_url and "shide-rabbitmq" in self.rabbitmq_url
        ):
            errors.append("default RabbitMQ credentials are forbidden")

        if self.refresh_token_transport == "cookie" and not self.refresh_cookie_secure:
            errors.append("AUTH_REFRESH_COOKIE_SECURE must be true")
        if self.refresh_token_transport == "cookie" and not self.refresh_cookie_name.startswith(
            "__Host-"
        ):
            errors.append("AUTH_REFRESH_COOKIE_NAME must use the __Host- prefix")

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
    return Settings()  # type: ignore[call-arg]
