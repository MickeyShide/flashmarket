"""Production configuration hardening tests."""

import pytest
from pydantic import ValidationError

from media_service.config import Settings


def test_production_rejects_default_database_and_s3_credentials() -> None:
    with pytest.raises(ValidationError) as error:
        Settings(
            _env_file=None,
            environment="production",
            docs_enabled=False,
            database_url="postgresql+asyncpg://shide:shide@shide-postgres:5432/media",
            s3_internal_endpoint="http://shide-minio:9000",
            s3_public_endpoint="https://uploads.example.com",
            public_base_url="https://media.example.com/flashmarket-public",
            s3_access_key="shide",
            s3_secret_key="shide",
            allow_insecure_internal_services=True,
        )
    message = str(error.value)
    assert "default S3 credentials are forbidden" in message
    assert "default database credentials are forbidden" in message
