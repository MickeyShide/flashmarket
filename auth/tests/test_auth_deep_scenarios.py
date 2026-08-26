"""Deep security, token replay detection, and maintenance tests for auth service."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from auth_service.maintenance import cleanup_expired_data
from auth_service.models import LoginSession, RefreshToken, User
from auth_service.security import hash_password
from tests.test_auth import register_user


@pytest.mark.asyncio
async def test_refresh_token_replay_within_grace_keeps_session_active(
    client: AsyncClient,
) -> None:
    """A concurrent replay is rejected without revoking the rotated session."""
    email = "replay-victim@example.com"
    password = "SecurePassword123!"

    # 1. Register and login
    await register_user(client, email=email, password=password)
    login_resp = await client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )
    assert login_resp.status_code == 200
    tokens_1 = login_resp.json()["tokens"]
    refresh_token_1 = tokens_1["refresh_token"]

    # 2. Legitimate refresh: consumes refresh_token_1, issues refresh_token_2
    refresh_resp_1 = await client.post(
        "/auth/refresh",
        json={"refresh_token": refresh_token_1},
    )
    assert refresh_resp_1.status_code == 200
    tokens_2 = refresh_resp_1.json()["tokens"]
    refresh_token_2 = tokens_2["refresh_token"]
    assert refresh_token_2 != refresh_token_1

    # 3. A concurrent request replays refresh_token_1 and is rejected.
    replay_resp = await client.post(
        "/auth/refresh",
        json={"refresh_token": refresh_token_1},
    )
    assert replay_resp.status_code == 401

    # 4. The legitimate rotated token remains usable during the grace window.
    subsequent_resp = await client.post(
        "/auth/refresh",
        json={"refresh_token": refresh_token_2},
    )
    assert subsequent_resp.status_code == 200


@pytest.mark.asyncio
async def test_cleanup_expired_data_purges_only_expired_records(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """cleanup_expired_data removes only expired sessions/tokens while preserving active ones."""
    now = datetime.now(UTC)
    user_id = uuid.uuid7()

    async with session_factory() as db:
        user = User(
            id=user_id,
            email="cleanup-test@example.com",
            password_hash=hash_password("password-for-cleanup"),
            is_active=True,
        )
        db.add(user)

        # Expired session & token (beyond retention window)
        expired_session = LoginSession(
            id=uuid.uuid7(),
            user_id=user_id,
            created_at=now - timedelta(days=120),
            expires_at=now - timedelta(days=100),
        )
        db.add(expired_session)
        expired_token = RefreshToken(
            id=uuid.uuid7(),
            session_id=expired_session.id,
            token_hash="expired-hash",
            created_at=now - timedelta(days=120),
            expires_at=now - timedelta(days=100),
        )
        db.add(expired_token)

        # Active session & token
        active_session = LoginSession(
            id=uuid.uuid7(),
            user_id=user_id,
            created_at=now,
            expires_at=now + timedelta(days=7),
        )
        db.add(active_session)
        active_token = RefreshToken(
            id=uuid.uuid7(),
            session_id=active_session.id,
            token_hash="active-hash",
            created_at=now,
            expires_at=now + timedelta(days=7),
        )
        db.add(active_token)

        await db.commit()

    # Run maintenance cleanup
    counts = await cleanup_expired_data(session_factory=session_factory, now=now)
    assert counts.sessions >= 1
    assert counts.refresh_tokens >= 1

    # Verify database: active session remains, expired is deleted
    async with session_factory() as db:
        remaining_sessions = (
            await db.scalars(select(LoginSession).where(LoginSession.user_id == user_id))
        ).all()
        assert len(remaining_sessions) == 1
        assert remaining_sessions[0].id == active_session.id
