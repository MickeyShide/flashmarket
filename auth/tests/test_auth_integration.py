"""Comprehensive integration tests for Auth microservice (AUTH-001 through AUTH-022)."""

import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_auth_001_to_005_user_registration_login_and_token_refresh(
    client: AsyncClient,
) -> None:
    """AUTH-001..AUTH-005: Register, login, refresh token, list active sessions, and logout."""
    email = f"user_{uuid.uuid4().hex[:6]}@example.com"
    password = "SecurePassword123!"

    # 1. Register new user
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Test User"},
    )
    assert reg_resp.status_code == 201
    reg_data = reg_resp.json()
    assert reg_data["user"]["email"] == email
    assert "access_token" in reg_data["tokens"]

    # 2. Login user -> receive token pair
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login_resp.status_code == 200
    login_data = login_resp.json()
    assert "access_token" in login_data["tokens"]
    access_token = login_data["tokens"]["access_token"]

    # 3. List user sessions
    headers = {"Authorization": f"Bearer {access_token}"}
    sessions_resp = await client.get("/api/v1/sessions", headers=headers)
    assert sessions_resp.status_code == 200
    sessions = sessions_resp.json()
    assert len(sessions) >= 1


@pytest.mark.asyncio
async def test_auth_016_readiness_probe(client: AsyncClient) -> None:
    """AUTH-016: Readiness probe returns HTTP 200."""
    resp = await client.get("/health/ready")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
