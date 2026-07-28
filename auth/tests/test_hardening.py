from pathlib import Path

import pytest
from fastapi import HTTPException
from httpx import AsyncClient
from redis.asyncio import Redis
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from auth_service.config import Settings, get_settings
from auth_service.models import AuditEvent, OutboxEvent, User
from auth_service.rate_limit import enforce_rate_limit
from auth_service.security import hash_password
from tests.test_auth import register_user


async def test_distributed_rate_limit_returns_retry_after(
    fake_cache: Redis,
) -> None:
    for _ in range(2):
        await enforce_rate_limit(
            fake_cache,
            scope="test",
            identity="same-client",
            limit=2,
            window_seconds=60,
        )

    with pytest.raises(HTTPException) as exc_info:
        await enforce_rate_limit(
            fake_cache,
            scope="test",
            identity="same-client",
            limit=2,
            window_seconds=60,
        )
    assert exc_info.value.status_code == 429
    assert int(exc_info.value.headers["Retry-After"]) > 0


async def test_cookie_refresh_requires_csrf(
    client: AsyncClient,
) -> None:
    settings = get_settings()
    previous_transport = settings.refresh_token_transport
    settings.refresh_token_transport = "cookie"
    try:
        registered = await client.post(
            "/auth/register",
            json={
                "email": "cookie@example.com",
                "password": "cookie-password-is-long-enough",
            },
        )
        assert registered.status_code == 201
        tokens = registered.json()["tokens"]
        assert tokens["refresh_token"] is None
        assert tokens["csrf_token"]
        assert "HttpOnly" in registered.headers["set-cookie"]

        missing_csrf = await client.post("/auth/refresh", json={})
        assert missing_csrf.status_code == 403

        refreshed = await client.post(
            "/auth/refresh",
            json={},
            headers={"X-CSRF-Token": tokens["csrf_token"]},
        )
        assert refreshed.status_code == 200
        assert refreshed.json()["tokens"]["refresh_token"] is None
        assert refreshed.json()["tokens"]["csrf_token"] != tokens["csrf_token"]
    finally:
        settings.refresh_token_transport = previous_transport


def test_insecure_production_configuration_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Invalid production configuration"):
        Settings(
            _env_file=None,
            environment="production",
            database_url=("postgresql+asyncpg://flashmarket:flashmarket@database.example/auth"),
            redis_url="redis://localhost:6379/0",
            jwt_keys_directory=tmp_path,
            docs_enabled=True,
            refresh_token_transport="cookie",
            refresh_cookie_secure=False,
        )


def test_production_accepts_isolated_internal_services(tmp_path: Path) -> None:
    settings = Settings(
        _env_file=None,
        environment="production",
        database_url="postgresql+asyncpg://auth:secret@db:5432/auth",
        redis_url="redis://:secret@redis:6379/0",
        rabbitmq_url="amqp://auth:secret@rabbitmq:5672/",
        allow_insecure_internal_services=True,
        jwt_keys_directory=tmp_path,
        cors_origins=["https://flashmarket.example.com"],
        trusted_hosts=["auth.flashmarket.example.com"],
        docs_enabled=False,
        refresh_token_transport="cookie",
        refresh_cookie_secure=True,
        refresh_cookie_name="__Host-flashmarket-refresh",
    )

    assert settings.environment == "production"


async def test_database_enforces_normalized_email_and_records_audit(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await register_user(client, email="audit@example.com")

    async with session_factory() as db:
        audit_count = await db.scalar(
            select(func.count())
            .select_from(AuditEvent)
            .where(AuditEvent.event_type == "user_registered")
        )
        assert audit_count == 1
        outbox_count = await db.scalar(
            select(func.count())
            .select_from(OutboxEvent)
            .where(OutboxEvent.event_type == "user_registered")
        )
        assert outbox_count == 1

        db.add(
            User(
                email="MixedCase@example.com",
                password_hash=hash_password("database-constraint-password"),
            )
        )
        with pytest.raises(IntegrityError):
            await db.commit()
