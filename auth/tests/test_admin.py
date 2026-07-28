from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from auth_service.models import User, UserRole
from auth_service.security import hash_password
from tests.test_auth import bearer, register_user


async def test_admin_can_list_users_and_change_role(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    customer = await register_user(client)

    async with session_factory() as db:
        admin = User(
            email="admin@example.com",
            password_hash=hash_password("admin-password-is-long-enough"),
            full_name="Admin",
            role=UserRole.ADMIN,
        )
        db.add(admin)
        await db.commit()

    login = await client.post(
        "/auth/login",
        json={
            "email": "admin@example.com",
            "password": "admin-password-is-long-enough",
        },
    )
    assert login.status_code == 200
    admin_headers = bearer(login.json()["tokens"]["access_token"])

    users = await client.get("/admin/users", headers=admin_headers)
    assert users.status_code == 200
    assert users.json()["total"] == 2

    promoted = await client.patch(
        f"/admin/users/{customer['user']['id']}/role",
        headers=admin_headers,
        json={"role": "ADMIN"},
    )
    assert promoted.status_code == 200
    assert promoted.json()["role"] == "ADMIN"

    customer_session_revoked = await client.get(
        "/users/me",
        headers=bearer(customer["tokens"]["access_token"]),
    )
    assert customer_session_revoked.status_code == 401

    self_downgrade = await client.patch(
        f"/admin/users/{login.json()['user']['id']}/role",
        headers=admin_headers,
        json={"role": "CUSTOMER"},
    )
    assert self_downgrade.status_code == 409

    audit_events = await client.get(
        "/admin/audit-events",
        headers=admin_headers,
        params={"event_type": "user_role_changed"},
    )
    assert audit_events.status_code == 200
    assert audit_events.json()["total"] == 1


async def test_customer_cannot_use_admin_api(client: AsyncClient) -> None:
    customer = await register_user(client)
    response = await client.get(
        "/admin/users",
        headers=bearer(customer["tokens"]["access_token"]),
    )
    assert response.status_code == 403


async def test_admin_can_disable_account(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    customer = await register_user(client, email="disabled@example.com")

    async with session_factory() as db:
        db.add(
            User(
                email="status-admin@example.com",
                password_hash=hash_password("status-admin-password-long-enough"),
                role=UserRole.ADMIN,
            )
        )
        await db.commit()

    login = await client.post(
        "/auth/login",
        json={
            "email": "status-admin@example.com",
            "password": "status-admin-password-long-enough",
        },
    )
    admin_headers = bearer(login.json()["tokens"]["access_token"])

    disabled = await client.patch(
        f"/admin/users/{customer['user']['id']}/status",
        headers=admin_headers,
        json={"is_active": False},
    )
    assert disabled.status_code == 200
    assert disabled.json()["is_active"] is False

    revoked = await client.get(
        "/users/me",
        headers=bearer(customer["tokens"]["access_token"]),
    )
    assert revoked.status_code == 401

    filtered = await client.get(
        "/admin/users",
        headers=admin_headers,
        params={"search": "disabled@", "is_active": "false"},
    )
    assert filtered.status_code == 200
    assert filtered.json()["total"] == 1
