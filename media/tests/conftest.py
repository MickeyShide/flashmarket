"""Shared API, database, JWT, and fake-S3 fixtures."""

import os
from collections.abc import AsyncIterator
from pathlib import Path

os.environ["MEDIA_ENVIRONMENT"] = "test"
os.environ["MEDIA_DATABASE_URL"] = "sqlite+aiosqlite:///./media-test-bootstrap.db"
os.environ["MEDIA_S3_ACCESS_KEY"] = "test-access"
os.environ["MEDIA_S3_SECRET_KEY"] = "test-secret"
os.environ["MEDIA_S3_BUCKET"] = "test-public"
os.environ["MEDIA_PUBLIC_BASE_URL"] = "https://media.test/test-public"
os.environ["MEDIA_TRUSTED_HOSTS"] = '["test","localhost","testserver"]'

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from jwt_verifier.testing import TestKeyStore
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from media_service.api.dependencies import get_storage
from media_service.application.contracts import ObjectStorage
from media_service.domain.entities import PresignedPost, StoredObject
from media_service.domain.exceptions import StorageObjectNotFound
from media_service.infrastructure.database import Base, get_db
from media_service.main import create_app


class FakeStorage(ObjectStorage):
    """Deterministic in-memory S3 replacement for application tests."""

    def __init__(self) -> None:
        self.objects: dict[str, tuple[bytes, str, dict[str, str]]] = {}
        self.presigns: list[dict[str, object]] = []
        self.available = True

    async def create_presigned_post(
        self,
        *,
        key: str,
        content_type: str,
        size: int,
        asset_id: str,
        expires_in: int,
        inline: bool,
    ) -> PresignedPost:
        self.presigns.append(
            {
                "key": key,
                "content_type": content_type,
                "size": size,
                "asset_id": asset_id,
                "expires_in": expires_in,
                "inline": inline,
            }
        )
        return PresignedPost(
            url="https://uploads.test/test-public",
            fields={"key": key, "Content-Type": content_type, "x-amz-meta-asset-id": asset_id},
        )

    async def head_object(self, key: str) -> StoredObject:
        try:
            content, content_type, metadata = self.objects[key]
        except KeyError as exc:
            raise StorageObjectNotFound() from exc
        return StoredObject(len(content), content_type, metadata)

    async def read_object(self, key: str, max_bytes: int) -> bytes:
        try:
            return self.objects[key][0][: max_bytes + 1]
        except KeyError as exc:
            raise StorageObjectNotFound() from exc

    async def delete_object(self, key: str) -> None:
        self.objects.pop(key, None)

    async def check_bucket(self) -> None:
        if not self.available:
            raise OSError("test storage unavailable")

    def upload(self, key: str, content: bytes, content_type: str, asset_id: str) -> None:
        self.objects[key] = (content, content_type, {"asset-id": asset_id})


@pytest.fixture
def fake_storage() -> FakeStorage:
    return FakeStorage()


@pytest.fixture
def key_store(tmp_path: Path) -> TestKeyStore:
    store = TestKeyStore(tmp_path / "keys")
    os.environ["MEDIA_JWT_PUBLIC_KEY_DIR"] = str(store.key_dir)
    return store


@pytest.fixture
def auth_headers(key_store: TestKeyStore):  # type: ignore[no-untyped-def]
    def build(*, role: str = "CUSTOMER", user_id: object = None) -> dict[str, str]:
        token = key_store.create_token(role=role, user_id=user_id)
        return {"Authorization": f"Bearer {token}"}

    return build


@pytest_asyncio.fixture
async def db_session(tmp_path: Path) -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'media.db'}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest_asyncio.fixture
async def client(
    db_session: AsyncSession,
    fake_storage: FakeStorage,
    key_store: TestKeyStore,
) -> AsyncIterator[AsyncClient]:
    from media_service.api.dependencies import get_verifier
    from media_service.config import get_settings

    get_settings.cache_clear()
    get_verifier.cache_clear()

    async def override_db() -> AsyncIterator[AsyncSession]:
        yield db_session

    app = create_app()
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_storage] = lambda: fake_storage
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client

    get_settings.cache_clear()
    get_verifier.cache_clear()
