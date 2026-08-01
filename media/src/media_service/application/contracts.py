"""Ports used by Media application services."""

from typing import Protocol

from media_service.domain.entities import PresignedPost, StoredObject


class ObjectStorage(Protocol):
    """Provider-neutral asynchronous object-storage interface."""

    async def create_presigned_post(
        self,
        *,
        key: str,
        content_type: str,
        size: int,
        asset_id: str,
        expires_in: int,
        inline: bool,
    ) -> PresignedPost: ...

    async def head_object(self, key: str) -> StoredObject: ...

    async def read_object(self, key: str, max_bytes: int) -> bytes: ...

    async def delete_object(self, key: str) -> None: ...

    async def check_bucket(self) -> None: ...
