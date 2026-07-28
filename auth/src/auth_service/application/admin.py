import uuid
from dataclasses import dataclass

from auth_service.application.contracts import (
    AuditEventPage,
    AuditEventSearch,
    RequestContext,
    SessionStore,
    SessionStoreError,
    UnitOfWork,
    UserPage,
    UserSearch,
)
from auth_service.application.errors import (
    OwnAccountDisableForbidden,
    OwnRoleChangeForbidden,
    SessionStoreUnavailable,
    UserNotFound,
)
from auth_service.domain.events import DomainEvent, EventType
from auth_service.models import User, UserRole


class ListUsers:
    async def execute(
        self,
        query: UserSearch,
        *,
        uow: UnitOfWork,
    ) -> UserPage:
        """Return the requested administrator user page."""
        return await uow.users.search(query)


class ListAuditEvents:
    async def execute(
        self,
        query: AuditEventSearch,
        *,
        uow: UnitOfWork,
    ) -> AuditEventPage:
        """Return the requested administrator audit-event page."""
        return await uow.audit.search(query)


async def _load_user_for_update(
    uow: UnitOfWork,
    user_id: uuid.UUID,
) -> User:
    """Lock a user row before an administrator changes it."""
    user = await uow.users.get_for_update(user_id)
    if user is None:
        raise UserNotFound
    return user


async def _revoke_sessions(
    uow: UnitOfWork,
    session_store: SessionStore,
    user_id: uuid.UUID,
    *,
    reason: str,
) -> list[uuid.UUID]:
    """Revoke a user’s sessions in SQL and Redis."""
    session_ids = await uow.sessions.revoke_all_for_user(user_id, reason=reason)
    try:
        await session_store.deactivate_many(session_ids)
    except SessionStoreError as exc:
        raise SessionStoreUnavailable from exc
    return session_ids


@dataclass(frozen=True, slots=True)
class UpdateUserRoleCommand:
    user_id: uuid.UUID
    actor_user_id: uuid.UUID
    role: UserRole
    context: RequestContext


class UpdateUserRole:
    async def execute(
        self,
        command: UpdateUserRoleCommand,
        *,
        uow: UnitOfWork,
        session_store: SessionStore,
    ) -> User:
        """Change a role and revoke sessions when privileges change."""
        user = await _load_user_for_update(uow, command.user_id)
        if user.id == command.actor_user_id and user.role != command.role:
            raise OwnRoleChangeForbidden
        if user.role == command.role:
            return user

        previous_role = user.role
        user.role = command.role
        session_ids = await _revoke_sessions(
            uow,
            session_store,
            user.id,
            reason="role_changed",
        )
        event_data = {
            "previous_role": previous_role.value,
            "new_role": command.role.value,
            "revoked_session_count": len(session_ids),
        }
        uow.audit.add(
            command.context,
            event_type=EventType.USER_ROLE_CHANGED.value,
            actor_user_id=command.actor_user_id,
            subject_user_id=user.id,
            event_data=event_data,
        )
        uow.add_event(
            DomainEvent(
                event_type=EventType.USER_ROLE_CHANGED,
                aggregate_type="user",
                aggregate_id=user.id,
                payload=event_data,
            )
        )
        await uow.commit()
        return user


@dataclass(frozen=True, slots=True)
class UpdateUserStatusCommand:
    user_id: uuid.UUID
    actor_user_id: uuid.UUID
    is_active: bool
    context: RequestContext


class UpdateUserStatus:
    async def execute(
        self,
        command: UpdateUserStatusCommand,
        *,
        uow: UnitOfWork,
        session_store: SessionStore,
    ) -> User:
        """Change account status and revoke sessions when disabling."""
        user = await _load_user_for_update(uow, command.user_id)
        if user.id == command.actor_user_id and not command.is_active:
            raise OwnAccountDisableForbidden
        if user.is_active == command.is_active:
            return user

        previous_status = user.is_active
        user.is_active = command.is_active
        session_ids: list[uuid.UUID] = []
        if not command.is_active:
            session_ids = await _revoke_sessions(
                uow,
                session_store,
                user.id,
                reason="account_disabled",
            )
        event_data = {
            "previous_is_active": previous_status,
            "new_is_active": command.is_active,
            "revoked_session_count": len(session_ids),
        }
        uow.audit.add(
            command.context,
            event_type=EventType.USER_STATUS_CHANGED.value,
            actor_user_id=command.actor_user_id,
            subject_user_id=user.id,
            event_data=event_data,
        )
        uow.add_event(
            DomainEvent(
                event_type=EventType.USER_STATUS_CHANGED,
                aggregate_type="user",
                aggregate_id=user.id,
                payload=event_data,
            )
        )
        await uow.commit()
        return user
