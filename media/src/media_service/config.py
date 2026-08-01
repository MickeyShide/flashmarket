"""Configuration for the Media service."""

import socket
from functools import lru_cache
from pathlib import Path
from typing import Literal, Self
from urllib.parse import urlsplit, urlunsplit

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def resolve_url_ipv4(url_str: str) -> str:
    """Resolve PostgreSQL host to IPv4 to match the other services."""
    try:
        parsed = urlsplit(url_str)
        if parsed.hostname and not parsed.hostname.replace(".", "").isdigit():
            port = parsed.port or 5432
            infos = socket.getaddrinfo(
                parsed.hostname, port, family=socket.AF_INET, type=socket.SOCK_STREAM
            )
            if infos:
                ip = str(infos[0][4][0])
                netloc = parsed.netloc.replace(parsed.hostname, ip, 1)
                return urlunsplit(parsed._replace(netloc=netloc))
    except Exception:
        pass
    return url_str


class Settings(BaseSettings):
    """Validated Media service settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="MEDIA_",
        extra="ignore",
    )

    app_name: str = "FlashMarket Media"
    environment: Literal["development", "test", "production"] = "development"
    debug: bool = False
    docs_enabled: bool = True
    database_url: str = "postgresql+asyncpg://shide:shide@shide-postgres:5432/media"
    s3_internal_endpoint: str = "http://shide-minio:9000"
    s3_public_endpoint: str = "http://localhost:9000"
    s3_access_key: str = "shide"
    s3_secret_key: str = "shide"
    s3_bucket: str = "flashmarket-public"
    s3_region: str = "us-east-1"
    s3_addressing_style: Literal["path", "virtual"] = "path"
    public_base_url: str = "http://localhost:9000/flashmarket-public"
    upload_ttl_seconds: int = Field(default=600, ge=60, le=3600)
    cleanup_interval_seconds: int = Field(default=30, ge=1, le=3600)
    cleanup_batch_size: int = Field(default=100, ge=1, le=1000)
    max_pending_per_user: int = Field(default=10, ge=1, le=100)
    max_user_assets: int = Field(default=200, ge=1, le=100_000)
    max_user_bytes: int = Field(default=500 * 1024 * 1024, ge=1)
    max_image_pixels: int = Field(default=40_000_000, ge=1_000_000)
    jwt_public_key_dir: Path = Path("keys/public")
    jwt_algorithm: str = "EdDSA"
    jwt_issuer: str = "flashmarket-auth"
    jwt_audience: str = "flashmarket-api"
    trusted_hosts: list[str] = Field(
        default_factory=lambda: ["localhost", "127.0.0.1", "test", "testserver"]
    )
    cors_origins: list[str] = Field(default_factory=list)
    log_level: str = "INFO"
    log_file_path: str | None = None
    prometheus_multiproc_dir: str | None = None
    allow_insecure_internal_services: bool = False

    @model_validator(mode="after")
    def validate_production_settings(self) -> Self:
        """Reject unsafe production configuration."""
        if self.environment != "production":
            return self
        errors: list[str] = []
        if self.debug:
            errors.append("MEDIA_DEBUG must be false")
        if self.docs_enabled:
            errors.append("MEDIA_DOCS_ENABLED must be false")
        if not self.s3_access_key or not self.s3_secret_key:
            errors.append("S3 credentials are required")
        if self.s3_access_key == self.s3_secret_key == "shide":
            errors.append("default S3 credentials are forbidden")
        if urlsplit(self.s3_public_endpoint).scheme != "https":
            errors.append("MEDIA_S3_PUBLIC_ENDPOINT must use HTTPS")
        if urlsplit(self.public_base_url).scheme != "https":
            errors.append("MEDIA_PUBLIC_BASE_URL must use HTTPS")
        db_host = urlsplit(self.database_url).hostname
        if db_host in {"localhost", "127.0.0.1"}:
            errors.append("MEDIA_DATABASE_URL must point to production database")
        if (
            "flashmarket:flashmarket@" in self.database_url
            or "://shide:shide@" in self.database_url
        ):
            errors.append("default database credentials are forbidden")
        if "sslmode" not in self.database_url and not self.allow_insecure_internal_services:
            errors.append("MEDIA_DATABASE_URL must use TLS")
        internal_scheme = urlsplit(self.s3_internal_endpoint).scheme
        if internal_scheme != "https" and not self.allow_insecure_internal_services:
            errors.append("MEDIA_S3_INTERNAL_ENDPOINT must use HTTPS")
        if errors:
            raise ValueError("Invalid production configuration: " + "; ".join(errors))
        return self

    @model_validator(mode="after")
    def resolve_database_dns(self) -> Self:
        """Resolve only the database URL; S3 signing must preserve its configured host."""
        if self.database_url:
            self.database_url = resolve_url_ipv4(self.database_url)
        return self


@lru_cache
def get_settings() -> Settings:
    """Return cached settings."""
    return Settings()
