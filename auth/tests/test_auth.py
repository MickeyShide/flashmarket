import json

from argon2 import PasswordHasher
from argon2.low_level import Type
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from auth_service.models import AuditEvent, RefreshToken, User
from auth_service.security import digest_refresh_token, verify_password


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
        refresh_token = await db.scalar(select(RefreshToken))
        assert refresh_token is not None
        assert refresh_token.token_hash == digest_refresh_token(
            registered["tokens"]["refresh_token"]
        )
        assert refresh_token.token_hash != registered["tokens"]["refresh_token"]

        audit_events = (await db.scalars(select(AuditEvent))).all()
        audit_payload = json.dumps(
            [event.event_data for event in audit_events],
            sort_keys=True,
        )
        assert "correct-horse-battery-staple" not in audit_payload
        assert registered["tokens"]["access_token"] not in audit_payload
        assert registered["tokens"]["refresh_token"] not in audit_payload

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


async def test_login_does_not_reveal_whether_account_exists(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await register_user(client, email="enumeration@example.com")
    wrong_password = await client.post(
        "/auth/login",
        json={
            "email": "enumeration@example.com",
            "password": "definitely-the-wrong-password",
        },
    )
    unknown_account = await client.post(
        "/auth/login",
        json={
            "email": "unknown@example.com",
            "password": "definitely-the-wrong-password",
        },
    )

    assert wrong_password.status_code == unknown_account.status_code == 401
    wrong_error = wrong_password.json()["error"]
    unknown_error = unknown_account.json()["error"]
    assert {
        "code": wrong_error["code"],
        "message": wrong_error["message"],
    } == {
        "code": unknown_error["code"],
        "message": unknown_error["message"],
    }
    async with session_factory() as db:
        failed_logins = (
            await db.scalars(select(AuditEvent).where(AuditEvent.event_type == "login_failed"))
        ).all()
        assert len(failed_logins) == 2
        serialized_events = json.dumps(
            [event.event_data for event in failed_logins],
            sort_keys=True,
        )
        assert "unknown@example.com" not in serialized_events
        assert "email_fingerprint" in serialized_events


async def test_refresh_rotation_and_concurrent_replay_grace(client: AsyncClient) -> None:
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

    session_remains_active_during_grace_period = await client.get(
        "/users/me",
        headers=bearer(rotated_tokens["access_token"]),
    )
    assert session_remains_active_during_grace_period.status_code == 200


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


async def test_user_cannot_close_another_users_session(client: AsyncClient) -> None:
    first_user = await register_user(client, email="owner@example.com")
    second_user = await register_user(client, email="attacker@example.com")

    sessions = await client.get(
        "/sessions",
        headers=bearer(first_user["tokens"]["access_token"]),
    )
    target_session_id = sessions.json()[0]["id"]
    forbidden = await client.delete(
        f"/sessions/{target_session_id}",
        headers=bearer(second_user["tokens"]["access_token"]),
    )

    assert forbidden.status_code == 404
    still_active = await client.get(
        "/users/me",
        headers=bearer(first_user["tokens"]["access_token"]),
    )
    assert still_active.status_code == 200


async def test_logout_all_revokes_every_session(client: AsyncClient) -> None:
    first = await register_user(client, email="logout-all@example.com")
    second_response = await client.post(
        "/auth/login",
        json={
            "email": "logout-all@example.com",
            "password": "correct-horse-battery-staple",
        },
    )
    assert second_response.status_code == 200
    second = second_response.json()

    closed = await client.delete(
        "/sessions",
        headers=bearer(first["tokens"]["access_token"]),
    )
    assert closed.status_code == 200

    for tokens in (first["tokens"], second["tokens"]):
        access_rejected = await client.get(
            "/users/me",
            headers=bearer(tokens["access_token"]),
        )
        refresh_rejected = await client.post(
            "/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]},
        )
        assert access_rejected.status_code == 401
        assert refresh_rejected.status_code == 401


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


async def test_login_upgrades_outdated_argon2_hash(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    password = "rehash-password-is-long-enough"
    outdated_hash = PasswordHasher(
        time_cost=1,
        memory_cost=8_192,
        parallelism=1,
        hash_len=16,
        salt_len=8,
        type=Type.ID,
    ).hash(password)
    async with session_factory() as db:
        db.add(
            User(
                email="rehash@example.com",
                password_hash=outdated_hash,
            )
        )
        await db.commit()

    logged_in = await client.post(
        "/auth/login",
        json={"email": "rehash@example.com", "password": password},
    )
    assert logged_in.status_code == 200

    async with session_factory() as db:
        user = await db.scalar(select(User).where(User.email == "rehash@example.com"))
        assert user is not None
        assert user.password_hash != outdated_hash
        assert verify_password(password, user.password_hash)
