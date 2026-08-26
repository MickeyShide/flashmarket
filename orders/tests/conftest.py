"""Shared test fixtures for the orders service."""

import os
from collections.abc import AsyncIterator, Iterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

os.environ.setdefault("ORDERS_ENVIRONMENT", "test")

from pathlib import Path

from jwt_verifier.testing import TestKeyStore

from orders.api.dependencies import get_catalog_client, get_verifier
from orders.config import get_settings
from orders.infrastructure.database import Base, get_db  # noqa: E402
from orders.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def jwt_keystore(tmp_path: Path) -> Iterator[TestKeyStore]:
    keystore = TestKeyStore(tmp_path / "keys" / "public")
    settings = get_settings()
    previous_catalog_base_url = settings.catalog_base_url
    settings.jwt_public_key_dir = keystore.key_dir
    settings.catalog_base_url = None
    get_verifier.cache_clear()
    get_catalog_client.cache_clear()
    try:
        yield keystore
    finally:
        settings.catalog_base_url = previous_catalog_base_url
        get_catalog_client.cache_clear()


@pytest.fixture
async def session_factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    """Create an in-memory SQLite database and override the app dependency."""
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
    yield factory
    app.dependency_overrides.clear()
    await test_engine.dispose()


@pytest.fixture
async def client(
    session_factory: async_sessionmaker[AsyncSession],
    jwt_keystore: TestKeyStore,
) -> AsyncIterator[AsyncClient]:
    """Provide an async HTTP client wired to the test app with admin auth header."""
    del session_factory  # consumed only to ensure DB is ready
    admin_token = jwt_keystore.create_token(role="ADMIN")
    headers = {"Authorization": f"Bearer {admin_token}"}
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://localhost", headers=headers
    ) as test_client:
        yield test_client


@pytest.fixture
async def db_session(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    """Provide a standalone database session for direct DB assertions."""
    async with session_factory() as session:
        yield session
