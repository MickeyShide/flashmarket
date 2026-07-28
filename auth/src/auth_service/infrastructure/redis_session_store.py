import uuid
from datetime import datetime

from redis.asyncio import Redis

from auth_service.application.contracts import SessionStore, SessionStoreError
from auth_service.cache import (
    CacheUnavailableError,
    activate_session,
    deactivate_session,
    deactivate_sessions,
    is_session_active,
)


class RedisSessionStore(SessionStore):
    def __init__(self, client: Redis) -> None:
        """Initialize RedisSessionStore."""
        self._client = client

    async def activate(
        self,
        *,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        expires_at: datetime,
    ) -> None:
        """Store the active-session marker until its expiry."""
        try:
            await activate_session(
                self._client,
                session_id=session_id,
                user_id=user_id,
                expires_at=expires_at,
            )
        except CacheUnavailableError as exc:
            raise SessionStoreError from exc

    async def is_active(
        self,
        *,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> bool:
        """Return whether the active-session marker still exists."""
        try:
            return await is_session_active(
                self._client,
                session_id=session_id,
                user_id=user_id,
            )
        except CacheUnavailableError as exc:
            raise SessionStoreError from exc

    async def deactivate(self, session_id: uuid.UUID) -> None:
        """Remove one active-session marker immediately."""
        try:
            await deactivate_session(self._client, session_id)
        except CacheUnavailableError as exc:
            raise SessionStoreError from exc

    async def deactivate_many(self, session_ids: list[uuid.UUID]) -> None:
        """Remove multiple active-session markers immediately."""
        try:
            await deactivate_sessions(self._client, session_ids)
        except CacheUnavailableError as exc:
            raise SessionStoreError from exc
