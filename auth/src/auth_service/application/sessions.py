import uuid
from dataclasses import dataclass

from auth_service.application.contracts import (
    AuthenticatedIdentity,
    RequestContext,
    SessionStore,
    SessionStoreError,
    UnitOfWork,
)
from auth_service.application.errors import SessionNotFound, SessionStoreUnavailable
from auth_service.domain.events import DomainEvent, EventType
from auth_service.models import LoginSession


class ListSessions:
    async def execute(
        self,
        user_id: uuid.UUID,
        *,
        uow: UnitOfWork,
    ) -> list[LoginSession]:
        return await uow.sessions.list_for_user(user_id)


@dataclass(frozen=True, slots=True)
class RevokeSessionCommand:
    identity: AuthenticatedIdentity
    context: RequestContext
    session_id: uuid.UUID


class RevokeSession:
    async def execute(
        self,
        command: RevokeSessionCommand,
        *,
        uow: UnitOfWork,
        session_store: SessionStore,
    ) -> None:
        login_session = await uow.sessions.get_owned_for_update(
            command.session_id,
            command.identity.user_id,
        )
        if login_session is None:
            raise SessionNotFound

        await uow.sessions.revoke(login_session, reason="user_revoked")
        try:
            await session_store.deactivate(command.session_id)
        except SessionStoreError as exc:
            raise SessionStoreUnavailable from exc

        event_data = {"session_id": str(command.session_id)}
        uow.audit.add(
            command.context,
            event_type=EventType.SESSION_REVOKED.value,
            actor_user_id=command.identity.user_id,
            subject_user_id=command.identity.user_id,
            event_data=event_data,
        )
        uow.add_event(
            DomainEvent(
                event_type=EventType.SESSION_REVOKED,
                aggregate_type="session",
                aggregate_id=command.session_id,
                payload={"user_id": str(command.identity.user_id)},
            )
        )
        await uow.commit()


@dataclass(frozen=True, slots=True)
class RevokeAllSessionsCommand:
    identity: AuthenticatedIdentity
    context: RequestContext


class RevokeAllSessions:
    async def execute(
        self,
        command: RevokeAllSessionsCommand,
        *,
        uow: UnitOfWork,
        session_store: SessionStore,
    ) -> int:
        session_ids = await uow.sessions.revoke_all_for_user(
            command.identity.user_id,
            reason="logout_all",
        )
        try:
            await session_store.deactivate_many(session_ids)
        except SessionStoreError as exc:
            raise SessionStoreUnavailable from exc

        event_data = {"session_count": len(session_ids)}
        uow.audit.add(
            command.context,
            event_type=EventType.ALL_SESSIONS_REVOKED.value,
            actor_user_id=command.identity.user_id,
            subject_user_id=command.identity.user_id,
            event_data=event_data,
        )
        uow.add_event(
            DomainEvent(
                event_type=EventType.ALL_SESSIONS_REVOKED,
                aggregate_type="user",
                aggregate_id=command.identity.user_id,
                payload=event_data,
            )
        )
        await uow.commit()
        return len(session_ids)
