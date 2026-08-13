import uuid
from dataclasses import dataclass

from auth_service.application.contracts import (
    AuthenticatedIdentity,
    RequestContext,
    SessionStore,
    SessionStoreError,
    UnitOfWork,
)
from auth_service.application.errors import (
    AccountUnavailable,
    CurrentPasswordIncorrect,
    PasswordUnchanged,
    SessionStoreUnavailable,
)
from auth_service.domain.events import DomainEvent, EventType
from auth_service.models import User
from auth_service.password_work import run_password_work
from auth_service.security import hash_password, verify_password


async def _load_active_user(
    uow: UnitOfWork,
    user_id: uuid.UUID,
    *,
    for_update: bool = False,
) -> User:
    """Load an enabled user or raise a not-found error."""
    user = (
        await uow.users.get_active_for_update(user_id)
        if for_update
        else await uow.users.get_active(user_id)
    )
    if user is None:
        raise AccountUnavailable
    return user


class GetProfile:
    async def execute(
        self,
        user_id: uuid.UUID,
        *,
        uow: UnitOfWork,
    ) -> User:
        """Return the current user’s profile."""
        return await _load_active_user(uow, user_id)


@dataclass(frozen=True, slots=True)
class UpdateProfileCommand:
    identity: AuthenticatedIdentity
    context: RequestContext
    update_full_name: bool
    full_name: str | None


class UpdateProfile:
    async def execute(
        self,
        command: UpdateProfileCommand,
        *,
        uow: UnitOfWork,
    ) -> User:
        """Update the current user’s profile."""
        user = await _load_active_user(uow, command.identity.user_id)
        if not command.update_full_name:
            return user

        user.full_name = command.full_name
        changed_fields = ["full_name"]
        uow.audit.add(
            command.context,
            event_type=EventType.PROFILE_UPDATED.value,
            actor_user_id=user.id,
            subject_user_id=user.id,
            event_data={"changed_fields": changed_fields},
        )
        uow.add_event(
            DomainEvent(
                event_type=EventType.PROFILE_UPDATED,
                aggregate_type="user",
                aggregate_id=user.id,
                payload={"changed_fields": changed_fields},
            )
        )
        await uow.commit()
        return user


@dataclass(frozen=True, slots=True)
class ChangePasswordCommand:
    identity: AuthenticatedIdentity
    context: RequestContext
    current_password: str
    new_password: str


class ChangePassword:
    async def execute(
        self,
        command: ChangePasswordCommand,
        *,
        uow: UnitOfWork,
        session_store: SessionStore,
    ) -> int:
        """Replace the password and revoke all user sessions."""
        user = await _load_active_user(
            uow,
            command.identity.user_id,
            for_update=True,
        )
        current_password_valid = await run_password_work(
            verify_password,
            command.current_password,
            user.password_hash,
        )
        if not current_password_valid:
            uow.audit.add(
                command.context,
                event_type="password_change_failed",
                actor_user_id=user.id,
                subject_user_id=user.id,
                event_data={"reason": "invalid_current_password"},
            )
            await uow.commit()
            raise CurrentPasswordIncorrect

        if await run_password_work(
            verify_password,
            command.new_password,
            user.password_hash,
        ):
            raise PasswordUnchanged

        user.password_hash = await run_password_work(
            hash_password,
            command.new_password,
        )
        session_ids = await uow.sessions.revoke_all_for_user(
            user.id,
            reason="password_changed",
        )
        try:
            await session_store.deactivate_many(session_ids)
        except SessionStoreError as exc:
            raise SessionStoreUnavailable from exc

        uow.audit.add(
            command.context,
            event_type=EventType.PASSWORD_CHANGED.value,
            actor_user_id=user.id,
            subject_user_id=user.id,
        )
        uow.add_event(
            DomainEvent(
                event_type=EventType.PASSWORD_CHANGED,
                aggregate_type="user",
                aggregate_id=user.id,
                payload={"revoked_session_count": len(session_ids)},
            )
        )
        await uow.commit()
        return len(session_ids)
