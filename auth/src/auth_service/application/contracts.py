import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from auth_service.domain.events import DomainEvent
from auth_service.models import (
    AuditEvent,
    LoginSession,
    RefreshToken,
    User,
    UserRole,
)


@dataclass(frozen=True, slots=True)
class RequestContext:
    request_id: str | None
    ip_address: str | None
    user_agent: str | None


@dataclass(frozen=True, slots=True)
class AuthenticatedIdentity:
    user_id: uuid.UUID
    session_id: uuid.UUID


class SessionStoreError(RuntimeError):
    """The active-session store could not complete an operation."""


class SessionStore(Protocol):
    async def activate(
        self,
        *,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        expires_at: datetime,
    ) -> None: ...

    async def is_active(
        self,
        *,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> bool: ...

    async def deactivate(self, session_id: uuid.UUID) -> None: ...

    async def deactivate_many(self, session_ids: list[uuid.UUID]) -> None: ...


class UserEmailConflictError(RuntimeError):
    """A user with the normalized email already exists."""


@dataclass(frozen=True, slots=True)
class UserSearch:
    limit: int
    offset: int
    search: str | None = None
    role: UserRole | None = None
    is_active: bool | None = None


@dataclass(frozen=True, slots=True)
class AuditEventSearch:
    limit: int
    offset: int
    event_type: str | None = None
    user_id: uuid.UUID | None = None


@dataclass(frozen=True, slots=True)
class UserPage:
    items: list[User]
    total: int


@dataclass(frozen=True, slots=True)
class AuditEventPage:
    items: list[AuditEvent]
    total: int


@dataclass(frozen=True, slots=True)
class RefreshContext:
    refresh_token: RefreshToken
    login_session: LoginSession
    user: User


class UserRepository(Protocol):
    async def add_new(self, user: User) -> None: ...

    async def get_by_email(self, email: str) -> User | None: ...

    async def get_by_email_for_update(self, email: str) -> User | None: ...

    async def get_active(self, user_id: uuid.UUID) -> User | None: ...

    async def get_active_for_update(self, user_id: uuid.UUID) -> User | None: ...

    async def get_for_update(self, user_id: uuid.UUID) -> User | None: ...

    async def search(self, query: UserSearch) -> UserPage: ...


class SessionRepository(Protocol):
    async def persist_new(
        self,
        login_session: LoginSession,
        refresh_token: RefreshToken,
    ) -> None: ...

    async def persist_replacement(self, refresh_token: RefreshToken) -> None: ...

    async def get_owned_for_update(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> LoginSession | None: ...

    async def get_refresh_context_for_rotation(
        self,
        token_hash: str,
    ) -> RefreshContext | None: ...

    async def list_for_user(self, user_id: uuid.UUID) -> list[LoginSession]: ...

    async def revoke(self, login_session: LoginSession, *, reason: str) -> None: ...

    async def revoke_all_for_user(
        self,
        user_id: uuid.UUID,
        *,
        reason: str,
    ) -> list[uuid.UUID]: ...

    async def touch_active(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None: ...


class AuditRepository(Protocol):
    def add(
        self,
        context: RequestContext,
        *,
        event_type: str,
        actor_user_id: uuid.UUID | None = None,
        subject_user_id: uuid.UUID | None = None,
        event_data: dict[str, object] | None = None,
    ) -> None: ...

    async def search(self, query: AuditEventSearch) -> AuditEventPage: ...


class UnitOfWork(Protocol):
    users: UserRepository
    sessions: SessionRepository
    audit: AuditRepository

    def add_event(self, event: DomainEvent) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...
