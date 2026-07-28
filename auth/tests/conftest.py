import os
import tempfile
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from fakeredis.aioredis import FakeRedis
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

os.environ.setdefault("AUTH_ENVIRONMENT", "test")
os.environ.setdefault("AUTH_REFRESH_TOKEN_TRANSPORT", "body")

from auth_service.key_management import generate_jwt_key_pair  # noqa: E402

test_key_directory = tempfile.TemporaryDirectory()
test_key_id = "flashmarket-auth-test-key"
generate_jwt_key_pair(Path(test_key_directory.name), key_id=test_key_id)
os.environ["AUTH_JWT_KEYS_DIRECTORY"] = test_key_directory.name
os.environ["AUTH_JWT_KEY_ID"] = test_key_id

from auth_service.cache import get_cache  # noqa: E402
from auth_service.database import Base, get_db  # noqa: E402
from auth_service.main import app  # noqa: E402


@pytest.fixture
async def fake_cache() -> AsyncIterator[FakeRedis]:
    cache = FakeRedis(decode_responses=True)
    yield cache
    await cache.aclose()


@pytest.fixture
async def session_factory(
    fake_cache: FakeRedis,
) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    test_engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
    )
    async with test_engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(test_engine, expire_on_commit=False)

    async def override_get_db() -> AsyncIterator[AsyncSession]:
        async with factory() as session:
            try:
                yield session
            finally:
                await session.rollback()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_cache] = lambda: fake_cache
    yield factory
    app.dependency_overrides.clear()
    await test_engine.dispose()


@pytest.fixture
async def client(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncClient]:
    del session_factory
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client
