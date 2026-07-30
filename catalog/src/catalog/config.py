from functools import lru_cache
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="CATALOG_",
        extra="ignore",
    )

    app_name: str = "FlashMarket Catalog"
    environment: Literal["development", "test", "production"] = "development"
    debug: bool = False
    database_url: str = "postgresql+asyncpg://shide:shide@shide-postgres:5432/catalog"
    log_file_path: str | None = None
    prometheus_multiproc_dir: str | None = None
    docs_enabled: bool = True
    trusted_hosts: list[str] = Field(default_factory=lambda: ["localhost", "127.0.0.1"])
    cors_origins: list[str] = Field(default_factory=list)
    allow_insecure_internal_services: bool = False

    @model_validator(mode="after")
    def validate_production_settings(self) -> Settings:
        """Enforce strict settings in production."""
        if self.environment != "production":
            return self

        errors: list[str] = []
        if self.debug:
            errors.append("CATALOG_DEBUG must be false")
        if self.docs_enabled:
            errors.append("CATALOG_DOCS_ENABLED must be false")
        if "flashmarket:flashmarket@" in self.database_url or (":shide@" in self.database_url and "shide-postgres" in self.database_url):
            errors.append("default database credentials are forbidden")
        if "localhost" in self.database_url or "127.0.0.1" in self.database_url:
            errors.append("CATALOG_DATABASE_URL must point to production database")
        db_is_internal = (
            self.allow_insecure_internal_services
            and urlsplit(self.database_url).hostname in {"db", "shide-postgres"}
        )
        if "sslmode" not in self.database_url and not db_is_internal:
            errors.append("CATALOG_DATABASE_URL must use TLS (sslmode)")
        if errors:
            raise ValueError("Invalid production configuration: " + "; ".join(errors))
        return self


@lru_cache
def get_settings() -> Settings:
    """Return the cached application settings."""
    return Settings()
