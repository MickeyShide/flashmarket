from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from auth_service.models import User


async def register_user(
    client: AsyncClient,
    *,
    email: str = "customer@example.com",
    password: str = "correct-horse-battery-staple",
) -> dict:
    response = await client.post(
        "/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": "Test Customer",
        },
        headers={"User-Agent": "pytest-browser"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def bearer(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


async def test_register_profile_sessions_and_logout(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    registered = await register_user(client)
    access_token = registered["tokens"]["access_token"]
    headers = bearer(access_token)

    assert registered["user"]["role"] == "CUSTOMER"
    assert registered["user"]["email"] == "customer@example.com"

    async with session_factory() as db:
        user = await db.scalar(select(User).where(User.email == "customer@example.com"))
        assert user is not None
        assert user.password_hash.startswith("$argon2id$")
        assert "correct-horse" not in user.password_hash

    profile = await client.get("/users/me", headers=headers)
    assert profile.status_code == 200
    assert profile.json()["full_name"] == "Test Customer"

    updated = await client.patch(
        "/users/me",
        headers=headers,
        json={"full_name": "Updated Customer"},
    )
    assert updated.status_code == 200
    assert updated.json()["full_name"] == "Updated Customer"

    unchanged = await client.patch("/users/me", headers=headers, json={})
    assert unchanged.status_code == 200
    assert unchanged.json()["full_name"] == "Updated Customer"

    sessions = await client.get("/sessions", headers=headers)
    assert sessions.status_code == 200
    assert len(sessions.json()) == 1
    assert sessions.json()[0]["current"] is True
    assert sessions.json()[0]["active"] is True
    assert sessions.json()[0]["user_agent"] == "pytest-browser"

    logged_out = await client.post("/auth/logout", headers=headers)
    assert logged_out.status_code == 200

    rejected = await client.get("/users/me", headers=headers)
    assert rejected.status_code == 401

    refresh_rejected = await client.post(
        "/auth/refresh",
        json={"refresh_token": registered["tokens"]["refresh_token"]},
    )
    assert refresh_rejected.status_code == 401


async def test_introspection_reflects_immediate_logout(client: AsyncClient) -> None:
    registered = await register_user(client, email="introspection@example.com")
    access_token = registered["tokens"]["access_token"]

    active = await client.post("/auth/introspect", json={"token": access_token})
    assert active.status_code == 200
    assert active.json()["active"] is True
    assert active.json()["sub"] == registered["user"]["id"]

    logged_out = await client.post("/auth/logout", headers=bearer(access_token))
    assert logged_out.status_code == 200

    inactive = await client.post("/auth/introspect", json={"token": access_token})
    assert inactive.status_code == 200
    assert inactive.json() == {
        "active": False,
        "sub": None,
        "sid": None,
        "role": None,
        "exp": None,
        "iss": None,
        "aud": None,
    }


async def test_duplicate_email_and_weak_password_are_rejected(
    client: AsyncClient,
) -> None:
    await register_user(client)

    duplicate = await client.post(
        "/auth/register",
        json={
            "email": "CUSTOMER@example.com",
            "password": "another-secure-password",
        },
    )
    assert duplicate.status_code == 409

    weak = await client.post(
        "/auth/register",
        json={
            "email": "other@example.com",
            "password": "short",
        },
    )
    assert weak.status_code == 422


async def test_refresh_rotation_and_reuse_detection(client: AsyncClient) -> None:
    registered = await register_user(client)
    original_refresh = registered["tokens"]["refresh_token"]

    refreshed = await client.post(
        "/auth/refresh",
        json={"refresh_token": original_refresh},
    )
    assert refreshed.status_code == 200, refreshed.text
    rotated_tokens = refreshed.json()["tokens"]
    assert rotated_tokens["refresh_token"] != original_refresh

    profile = await client.get(
        "/users/me",
        headers=bearer(rotated_tokens["access_token"]),
    )
    assert profile.status_code == 200

    replay = await client.post(
        "/auth/refresh",
        json={"refresh_token": original_refresh},
    )
    assert replay.status_code == 401

    session_was_revoked = await client.get(
        "/users/me",
        headers=bearer(rotated_tokens["access_token"]),
    )
    assert session_was_revoked.status_code == 401


async def test_user_can_close_another_session(client: AsyncClient) -> None:
    registered = await register_user(client)
    first_access = registered["tokens"]["access_token"]

    second_login = await client.post(
        "/auth/login",
        json={
            "email": "customer@example.com",
            "password": "correct-horse-battery-staple",
        },
        headers={"User-Agent": "second-device"},
    )
    assert second_login.status_code == 200
    second_access = second_login.json()["tokens"]["access_token"]

    sessions = await client.get("/sessions", headers=bearer(first_access))
    assert sessions.status_code == 200
    other_session = next(item for item in sessions.json() if not item["current"])

    closed = await client.delete(
        f"/sessions/{other_session['id']}",
        headers=bearer(first_access),
    )
    assert closed.status_code == 200

    rejected = await client.get("/users/me", headers=bearer(second_access))
    assert rejected.status_code == 401


async def test_password_change_revokes_sessions(client: AsyncClient) -> None:
    registered = await register_user(client, email="password@example.com")
    access_token = registered["tokens"]["access_token"]

    changed = await client.post(
        "/users/me/password",
        headers=bearer(access_token),
        json={
            "current_password": "correct-horse-battery-staple",
            "new_password": "new-correct-horse-battery-staple",
        },
    )
    assert changed.status_code == 200

    revoked = await client.get("/users/me", headers=bearer(access_token))
    assert revoked.status_code == 401

    old_login = await client.post(
        "/auth/login",
        json={
            "email": "password@example.com",
            "password": "correct-horse-battery-staple",
        },
    )
    assert old_login.status_code == 401

    new_login = await client.post(
        "/auth/login",
        json={
            "email": "password@example.com",
            "password": "new-correct-horse-battery-staple",
        },
    )
    assert new_login.status_code == 200
