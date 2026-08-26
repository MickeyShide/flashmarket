import socket
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit, urlunsplit

from pydantic import Field, SecretStr, model_validator
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
    database_url: str = "postgresql+asyncpg://shide:shide@shide-postgres:5432/payments"
    database_api_pool_size: int = Field(default=3, ge=1, le=20)
    database_api_max_overflow: int = Field(default=2, ge=0, le=20)
    database_worker_pool_size: int = Field(default=1, ge=1, le=10)
    database_worker_max_overflow: int = Field(default=1, ge=0, le=10)
    database_pool_timeout_seconds: float = Field(default=5.0, gt=0, le=60)
    database_pool_recycle_seconds: int = Field(default=1800, ge=60, le=86400)
    log_file_path: str | None = None
    prometheus_multiproc_dir: str | None = None
    docs_enabled: bool = True
    trusted_hosts: list[str] = Field(default_factory=lambda: ["localhost", "127.0.0.1"])
    cors_origins: list[str] = Field(default_factory=list)
    rabbitmq_url: str = "amqp://shide:shide@shide-rabbitmq:5672/flashmarket"
    rabbitmq_exchange: str = "flashmarket.events"
    allow_insecure_internal_services: bool = False
    payment_timeout_seconds: int = 300
    payment_provider: Literal["mock", "yookassa"] = "mock"
    yookassa_shop_id: str | None = None
    yookassa_secret_key: SecretStr | None = None
    yookassa_api_url: str = "https://api.yookassa.ru/v3"
    yookassa_return_url: str | None = None
    # Keep this as a bool so pydantic-settings can parse the string value
    # supplied by environment variables. A model validator below still makes
    # disabling the guard impossible.
    yookassa_test_mode_required: bool = True
    yookassa_connect_timeout_seconds: float = Field(default=5.0, gt=0, le=30)
    yookassa_read_timeout_seconds: float = Field(default=15.0, gt=0, le=60)
    yookassa_http_max_connections: int = Field(default=20, ge=1, le=200)
    yookassa_http_max_keepalive_connections: int = Field(default=10, ge=0, le=200)
    yookassa_http_keepalive_expiry_seconds: float = Field(default=30.0, gt=0, le=300)
    yookassa_read_concurrency: int = Field(default=16, ge=1, le=200)
    yookassa_write_concurrency: int = Field(default=8, ge=1, le=100)
    yookassa_interactive_max_attempts: int = Field(default=2, ge=1, le=3)
    yookassa_retry_base_seconds: float = Field(default=0.25, ge=0.01, le=5)
    yookassa_retry_max_seconds: float = Field(default=2.0, ge=0.1, le=30)
    yookassa_circuit_failure_threshold: int = Field(default=5, ge=1, le=100)
    yookassa_circuit_recovery_seconds: float = Field(default=15.0, ge=1, le=300)
    reconciliation_batch_size: int = Field(default=20, ge=1, le=100)
    reconciliation_poll_interval_seconds: float = Field(default=5.0, ge=0.5, le=300)
    webhook_max_body_bytes: int = Field(default=32_768, ge=1024, le=1_048_576)
    webhook_batch_size: int = Field(default=50, ge=1, le=500)
    webhook_max_attempts: int = Field(default=12, ge=1, le=100)
    yookassa_webhook_require_https: bool = False
    yookassa_webhook_ip_filter_enabled: bool = False
    yookassa_trusted_ips: list[str] = Field(
        default_factory=lambda: [
            "185.71.76.0/27",
            "185.71.77.0/27",
            "77.75.153.0/25",
            "77.75.156.11",
            "77.75.156.35",
            "77.75.154.128/25",
            "2a02:5180::/32",
            "127.0.0.1",
            "::1",
        ]
    )
    payment_attempt_ttl_seconds: int = Field(default=1800, ge=60, le=86_400)
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
            errors.append("PAYMENTS_DEBUG must be false")
        if self.docs_enabled:
            errors.append("PAYMENTS_DOCS_ENABLED must be false")
        if "flashmarket:flashmarket@" in self.database_url or (
            ":shide@" in self.database_url and "shide-postgres" in self.database_url
        ):
            errors.append("default database credentials are forbidden")
        if "localhost" in self.database_url or "127.0.0.1" in self.database_url:
            errors.append("PAYMENTS_DATABASE_URL must point to production database")
        db_is_internal = self.allow_insecure_internal_services
        if "sslmode" not in self.database_url and not db_is_internal:
            errors.append("PAYMENTS_DATABASE_URL must use TLS (sslmode)")
        if "localhost" in self.rabbitmq_url or "127.0.0.1" in self.rabbitmq_url:
            errors.append("PAYMENTS_RABBITMQ_URL must point to production RabbitMQ")
        rabbitmq_is_internal = self.allow_insecure_internal_services and urlsplit(
            self.rabbitmq_url
        ).hostname in {"rabbitmq", "shide-rabbitmq"}
        if not self.rabbitmq_url.startswith("amqps://") and not rabbitmq_is_internal:
            errors.append("PAYMENTS_RABBITMQ_URL must use TLS (amqps://)")
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
    def validate_payment_provider_settings(self) -> Settings:
        """Require complete, test-only YooKassa configuration when enabled."""
        if not self.yookassa_test_mode_required:
            raise ValueError("PAYMENTS_YOOKASSA_TEST_MODE_REQUIRED must be true")
        if self.payment_provider != "yookassa":
            return self

        errors: list[str] = []
        if not self.yookassa_shop_id:
            errors.append("PAYMENTS_YOOKASSA_SHOP_ID is required")
        if self.yookassa_secret_key is None or not self.yookassa_secret_key.get_secret_value():
            errors.append("PAYMENTS_YOOKASSA_SECRET_KEY is required")
        if not self.yookassa_return_url:
            errors.append("PAYMENTS_YOOKASSA_RETURN_URL is required")
        elif not self.yookassa_return_url.startswith(("http://", "https://")):
            errors.append("PAYMENTS_YOOKASSA_RETURN_URL must be an absolute HTTP(S) URL")
        if not self.yookassa_api_url.startswith("https://"):
            errors.append("PAYMENTS_YOOKASSA_API_URL must use HTTPS")
        if self.environment == "production" and not self.yookassa_webhook_require_https:
            errors.append("PAYMENTS_YOOKASSA_WEBHOOK_REQUIRE_HTTPS must be true in production")
        if errors:
            raise ValueError("Invalid YooKassa configuration: " + "; ".join(errors))
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
