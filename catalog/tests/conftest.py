"""Shared test fixtures for the catalog service."""

import os
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from jwt_verifier.testing import TestKeyStore
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

os.environ.setdefault("CATALOG_ENVIRONMENT", "test")

from catalog.api.dependencies import get_category_tree_cache, get_verifier  # noqa: E402
from catalog.application.schemas import CategoryTreeNode  # noqa: E402
from catalog.config import get_settings  # noqa: E402
from catalog.infrastructure.database import Base, get_db  # noqa: E402
from catalog.main import app  # noqa: E402


class InMemoryCategoryTreeCache:
    """Isolated cache fake used by the fast API suite."""

    def __init__(self) -> None:
        self.tree: list[CategoryTreeNode] | None = None
        self.reads = 0
        self.writes = 0
        self.invalidations = 0

    async def get_tree(self) -> list[CategoryTreeNode] | None:
        self.reads += 1
        if self.tree is None:
            return None
        return [node.model_copy(deep=True) for node in self.tree]

    async def store_tree(self, tree: list[CategoryTreeNode]) -> None:
        self.writes += 1
        self.tree = [node.model_copy(deep=True) for node in tree]

    async def invalidate_tree(self) -> None:
        self.invalidations += 1
        self.tree = None


@pytest.fixture(autouse=True)
def jwt_keystore(tmp_path: Path) -> TestKeyStore:
    keystore = TestKeyStore(tmp_path / "keys" / "public")
    settings = get_settings()
    settings.jwt_public_key_dir = keystore.key_dir
    get_verifier.cache_clear()
    return keystore


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
def category_cache() -> InMemoryCategoryTreeCache:
    """Provide an empty cache for each test."""
    return InMemoryCategoryTreeCache()


@pytest.fixture
async def client(
    session_factory: async_sessionmaker[AsyncSession],
    jwt_keystore: TestKeyStore,
    category_cache: InMemoryCategoryTreeCache,
) -> AsyncIterator[AsyncClient]:
    """Provide an async HTTP client wired to the test app with admin auth header."""
    del session_factory  # consumed only to ensure DB is ready
    admin_token = jwt_keystore.create_token(role="ADMIN")
    headers = {"Authorization": f"Bearer {admin_token}"}
    app.dependency_overrides[get_category_tree_cache] = lambda: category_cache
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://localhost",
        headers=headers,
    ) as test_client:
        yield test_client
