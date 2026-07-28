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
    ) -> None:
        """Store the active-session marker until its expiry."""
        ...

    async def is_active(
        self,
        *,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> bool:
        """Return whether the active-session marker still exists."""
        ...

    async def deactivate(self, session_id: uuid.UUID) -> None:
        """Remove one active-session marker immediately."""
        ...

    async def deactivate_many(self, session_ids: list[uuid.UUID]) -> None:
        """Remove multiple active-session markers immediately."""
        ...


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
    async def add_new(self, user: User) -> None:
        """Stage a newly registered user for insertion."""
        ...

    async def get_by_email(self, email: str) -> User | None:
        """Find a user by normalized email address."""
        ...

    async def get_by_email_for_update(self, email: str) -> User | None:
        """Lock a user found by normalized email address."""
        ...

    async def get_active(self, user_id: uuid.UUID) -> User | None:
        """Find an enabled user by ID."""
        ...

    async def get_active_for_update(self, user_id: uuid.UUID) -> User | None:
        """Lock an enabled user by ID."""
        ...

    async def get_for_update(self, user_id: uuid.UUID) -> User | None:
        """Lock a user by ID, including disabled accounts."""
        ...

    async def search(self, query: UserSearch) -> UserPage:
        """Search records using the supplied filters."""
        ...


class SessionRepository(Protocol):
    async def persist_new(
        self,
        login_session: LoginSession,
        refresh_token: RefreshToken,
    ) -> None:
        """Store a new login session with its initial refresh token."""
        ...

    async def persist_replacement(self, refresh_token: RefreshToken) -> None:
        """Store a rotated refresh token for an existing session."""
        ...

    async def get_owned_for_update(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> LoginSession | None:
        """Lock a session only when it belongs to the user."""
        ...

    async def get_refresh_context_for_rotation(
        self,
        token_hash: str,
    ) -> RefreshContext | None:
        """Lock and load the state needed to rotate a refresh token."""
        ...

    async def list_for_user(self, user_id: uuid.UUID) -> list[LoginSession]:
        """List all sessions belonging to a user."""
        ...

    async def revoke(self, login_session: LoginSession, *, reason: str) -> None:
        """Mark one login session as revoked."""
        ...

    async def revoke_all_for_user(
        self,
        user_id: uuid.UUID,
        *,
        reason: str,
    ) -> list[uuid.UUID]:
        """Revoke all active sessions owned by a user."""
        ...

    async def touch_active(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        """Update the last-seen timestamp of an active session."""
        ...


class AuditRepository(Protocol):
    def add(
        self,
        context: RequestContext,
        *,
        event_type: str,
        actor_user_id: uuid.UUID | None = None,
        subject_user_id: uuid.UUID | None = None,
        event_data: dict[str, object] | None = None,
    ) -> None:
        """Append an audit event to the current transaction."""
        ...

    async def search(self, query: AuditEventSearch) -> AuditEventPage:
        """Search records using the supplied filters."""
        ...


class UnitOfWork(Protocol):
    users: UserRepository
    sessions: SessionRepository
    audit: AuditRepository

    def add_event(self, event: DomainEvent) -> None:
        """Queue a domain event for transactional outbox delivery."""
        ...

    async def commit(self) -> None:
        """Commit database changes and persist queued outbox events."""
        ...

    async def rollback(self) -> None:
        """Discard uncommitted database changes."""
        ...
