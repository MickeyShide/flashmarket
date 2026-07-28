import asyncio
import os
import uuid
from collections.abc import AsyncIterator

import pytest
from fakeredis.aioredis import FakeRedis
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from auth_service.cache import get_cache
from auth_service.database import Base, get_db
from auth_service.main import app

pytestmark = pytest.mark.integration


@pytest.fixture
async def postgres_client() -> AsyncIterator[AsyncClient]:
    database_url = os.getenv("AUTH_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("AUTH_TEST_DATABASE_URL is not configured")

    schema = f"auth_test_{uuid.uuid7().hex}"
    admin_engine = create_async_engine(database_url)
    async with admin_engine.begin() as connection:
        await connection.execute(text(f'CREATE SCHEMA "{schema}"'))

    test_engine = create_async_engine(
        database_url,
        connect_args={"server_settings": {"search_path": schema}},
    )
    async with test_engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    fake_cache = FakeRedis(decode_responses=True)

    async def override_get_db() -> AsyncIterator[AsyncSession]:
        async with factory() as session:
            try:
                yield session
            finally:
                await session.rollback()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_cache] = lambda: fake_cache
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(
            transport=transport,
            base_url="http://postgres-test",
        ) as client:
            yield client
    finally:
        app.dependency_overrides.clear()
        await fake_cache.aclose()
        await test_engine.dispose()
        async with admin_engine.begin() as connection:
            await connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        await admin_engine.dispose()


async def test_concurrent_refresh_allows_one_rotation_and_revokes_replay(
    postgres_client: AsyncClient,
) -> None:
    registered = await postgres_client.post(
        "/auth/register",
        json={
            "email": "postgres-concurrency@example.com",
            "password": "postgres-concurrency-password",
        },
    )
    assert registered.status_code == 201
    refresh_token = registered.json()["tokens"]["refresh_token"]

    first, second = await asyncio.gather(
        postgres_client.post(
            "/auth/refresh",
            json={"refresh_token": refresh_token},
        ),
        postgres_client.post(
            "/auth/refresh",
            json={"refresh_token": refresh_token},
        ),
    )
    assert sorted([first.status_code, second.status_code]) == [200, 401]

    successful = first if first.status_code == 200 else second
    access_token = successful.json()["tokens"]["access_token"]
    rejected = await postgres_client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert rejected.status_code == 401
