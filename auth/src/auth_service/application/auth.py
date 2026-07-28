import uuid
from dataclasses import dataclass
from datetime import timedelta

import jwt
from anyio import to_thread

from auth_service.application.contracts import (
    AuthenticatedIdentity,
    RequestContext,
    SessionStore,
    SessionStoreError,
    UnitOfWork,
    UserEmailConflictError,
)
from auth_service.application.dto import (
    AuthenticationResult,
    IssuedTokens,
    RefreshResult,
)
from auth_service.application.errors import (
    AccountDisabled,
    EmailAlreadyExists,
    InvalidCredentials,
    InvalidRefreshToken,
    RefreshTokenReuseDetected,
    SessionStoreUnavailable,
)
from auth_service.config import get_settings
from auth_service.domain.events import DomainEvent, EventType
from auth_service.models import LoginSession, RefreshToken, User, UserRole
from auth_service.security import (
    AccessTokenClaims,
    burn_password_check,
    create_access_token,
    decode_access_token,
    digest_refresh_token,
    generate_refresh_token,
    hash_password,
    password_needs_rehash,
    verify_password,
)
from auth_service.time import as_utc, utc_now


def _issue_tokens(
    user: User,
    login_session: LoginSession,
) -> tuple[IssuedTokens, RefreshToken]:
    """Create access and refresh tokens for one persisted session."""
    raw_refresh_token, token_hash = generate_refresh_token()
    refresh_token = RefreshToken(
        id=uuid.uuid7(),
        session_id=login_session.id,
        token_hash=token_hash,
        expires_at=login_session.expires_at,
    )
    access_token, expires_in = create_access_token(user, login_session.id)
    return (
        IssuedTokens(
            access_token=access_token,
            refresh_token=raw_refresh_token,
            access_expires_in=expires_in,
        ),
        refresh_token,
    )


def _issue_session(
    user: User,
    *,
    user_agent: str | None,
    ip_address: str | None,
) -> tuple[LoginSession, RefreshToken, IssuedTokens]:
    """Create the database record for a new login session."""
    now = utc_now()
    settings = get_settings()
    login_session = LoginSession(
        id=uuid.uuid7(),
        user_id=user.id,
        user_agent=user_agent[:512] if user_agent else None,
        ip_address=ip_address[:45] if ip_address else None,
        created_at=now,
        last_seen_at=now,
        expires_at=now + timedelta(days=settings.session_ttl_days),
    )
    tokens, refresh_token = _issue_tokens(user, login_session)
    return login_session, refresh_token, tokens


async def _activate_persisted_session(
    uow: UnitOfWork,
    session_store: SessionStore,
    login_session: LoginSession,
) -> None:
    """Activate a committed session in Redis."""
    try:
        await session_store.activate(
            session_id=login_session.id,
            user_id=login_session.user_id,
            expires_at=login_session.expires_at,
        )
    except SessionStoreError as exc:
        await uow.sessions.revoke(
            login_session,
            reason="session_store_unavailable",
        )
        await uow.commit()
        raise SessionStoreUnavailable from exc


@dataclass(frozen=True, slots=True)
class RegisterCommand:
    email: str
    password: str
    full_name: str | None
    context: RequestContext


class RegisterUser:
    async def execute(
        self,
        command: RegisterCommand,
        *,
        uow: UnitOfWork,
        session_store: SessionStore,
    ) -> AuthenticationResult:
        """Register a customer, persist a session, and issue tokens."""
        password_hash = await to_thread.run_sync(hash_password, command.password)
        user = User(
            id=uuid.uuid7(),
            email=command.email.lower(),
            password_hash=password_hash,
            full_name=command.full_name,
            role=UserRole.CUSTOMER,
        )
        try:
            await uow.users.add_new(user)
        except UserEmailConflictError as exc:
            await uow.rollback()
            raise EmailAlreadyExists from exc

        login_session, refresh_token, tokens = _issue_session(
            user,
            user_agent=command.context.user_agent,
            ip_address=command.context.ip_address,
        )
        await uow.sessions.persist_new(login_session, refresh_token)
        uow.audit.add(
            command.context,
            event_type=EventType.USER_REGISTERED.value,
            actor_user_id=user.id,
            subject_user_id=user.id,
        )
        uow.add_event(
            DomainEvent(
                event_type=EventType.USER_REGISTERED,
                aggregate_type="user",
                aggregate_id=user.id,
                payload={
                    "email": user.email,
                    "role": user.role.value,
                },
            )
        )
        await uow.commit()
        await _activate_persisted_session(uow, session_store, login_session)
        return AuthenticationResult(
            user=user,
            session=login_session,
            tokens=tokens,
        )


@dataclass(frozen=True, slots=True)
class LoginCommand:
    email: str
    password: str
    context: RequestContext


class LoginUser:
    async def execute(
        self,
        command: LoginCommand,
        *,
        uow: UnitOfWork,
        session_store: SessionStore,
    ) -> AuthenticationResult:
        """Verify credentials, persist a session, and issue tokens."""
        email = command.email.lower()
        user = await uow.users.get_by_email(email)
        if user is None:
            await to_thread.run_sync(burn_password_check, command.password)
            uow.audit.add(
                command.context,
                event_type="login_failed",
                event_data={"email": email, "reason": "invalid_credentials"},
            )
            await uow.commit()
            raise InvalidCredentials

        password_valid = await to_thread.run_sync(
            verify_password,
            command.password,
            user.password_hash,
        )
        if not password_valid:
            uow.audit.add(
                command.context,
                event_type="login_failed",
                actor_user_id=user.id,
                subject_user_id=user.id,
                event_data={"reason": "invalid_credentials"},
            )
            await uow.commit()
            raise InvalidCredentials
        if not user.is_active:
            uow.audit.add(
                command.context,
                event_type="login_failed",
                actor_user_id=user.id,
                subject_user_id=user.id,
                event_data={"reason": "account_disabled"},
            )
            await uow.commit()
            raise AccountDisabled

        if await to_thread.run_sync(password_needs_rehash, user.password_hash):
            user.password_hash = await to_thread.run_sync(
                hash_password,
                command.password,
            )

        login_session, refresh_token, tokens = _issue_session(
            user,
            user_agent=command.context.user_agent,
            ip_address=command.context.ip_address,
        )
        await uow.sessions.persist_new(login_session, refresh_token)
        event_data = {"session_id": str(login_session.id)}
        uow.audit.add(
            command.context,
            event_type=EventType.USER_LOGGED_IN.value,
            actor_user_id=user.id,
            subject_user_id=user.id,
            event_data=event_data,
        )
        uow.add_event(
            DomainEvent(
                event_type=EventType.USER_LOGGED_IN,
                aggregate_type="user",
                aggregate_id=user.id,
                payload=event_data,
            )
        )
        await uow.commit()
        await _activate_persisted_session(uow, session_store, login_session)
        return AuthenticationResult(
            user=user,
            session=login_session,
            tokens=tokens,
        )


@dataclass(frozen=True, slots=True)
class RefreshCommand:
    refresh_token: str
    context: RequestContext


class RefreshAccess:
    async def execute(
        self,
        command: RefreshCommand,
        *,
        uow: UnitOfWork,
        session_store: SessionStore,
    ) -> RefreshResult:
        """Rotate a refresh token while detecting token replay."""
        token_hash = digest_refresh_token(command.refresh_token)
        refresh_context = await uow.sessions.get_refresh_context_for_rotation(token_hash)
        if refresh_context is None:
            raise InvalidRefreshToken

        refresh_token = refresh_context.refresh_token
        login_session = refresh_context.login_session
        user = refresh_context.user
        now = utc_now()
        if refresh_token.consumed_at is not None:
            await uow.sessions.revoke(
                login_session,
                reason="refresh_token_reuse",
            )
            event_data = {"session_id": str(login_session.id)}
            uow.audit.add(
                command.context,
                event_type=EventType.REFRESH_TOKEN_REUSE.value,
                actor_user_id=user.id,
                subject_user_id=user.id,
                event_data=event_data,
            )
            uow.add_event(
                DomainEvent(
                    event_type=EventType.REFRESH_TOKEN_REUSE,
                    aggregate_type="user",
                    aggregate_id=user.id,
                    payload=event_data,
                )
            )
            try:
                await session_store.deactivate(login_session.id)
            except SessionStoreError as exc:
                raise SessionStoreUnavailable from exc
            await uow.commit()
            raise RefreshTokenReuseDetected

        if (
            refresh_token.revoked_at is not None
            or as_utc(refresh_token.expires_at) <= now
            or login_session.revoked_at is not None
            or as_utc(login_session.expires_at) <= now
            or not user.is_active
        ):
            raise InvalidRefreshToken

        refresh_token.consumed_at = now
        login_session.last_seen_at = now
        tokens, replacement = _issue_tokens(user, login_session)
        await uow.sessions.persist_replacement(replacement)
        refresh_token.replaced_by_token_id = replacement.id
        event_data = {"session_id": str(login_session.id)}
        uow.audit.add(
            command.context,
            event_type=EventType.TOKEN_REFRESHED.value,
            actor_user_id=user.id,
            subject_user_id=user.id,
            event_data=event_data,
        )
        uow.add_event(
            DomainEvent(
                event_type=EventType.TOKEN_REFRESHED,
                aggregate_type="session",
                aggregate_id=login_session.id,
                payload={"user_id": str(user.id)},
            )
        )
        await uow.commit()
        await _activate_persisted_session(uow, session_store, login_session)
        return RefreshResult(
            user=user,
            session=login_session,
            tokens=tokens,
        )


@dataclass(frozen=True, slots=True)
class LogoutCommand:
    identity: AuthenticatedIdentity
    context: RequestContext


class LogoutUser:
    async def execute(
        self,
        command: LogoutCommand,
        *,
        uow: UnitOfWork,
        session_store: SessionStore,
    ) -> None:
        """Revoke the current session and invalidate its cache entry."""
        login_session = await uow.sessions.get_owned_for_update(
            command.identity.session_id,
            command.identity.user_id,
        )
        if login_session is not None:
            await uow.sessions.revoke(login_session, reason="logout")
            event_data = {"session_id": str(command.identity.session_id)}
            uow.audit.add(
                command.context,
                event_type=EventType.USER_LOGGED_OUT.value,
                actor_user_id=command.identity.user_id,
                subject_user_id=command.identity.user_id,
                event_data=event_data,
            )
            uow.add_event(
                DomainEvent(
                    event_type=EventType.USER_LOGGED_OUT,
                    aggregate_type="session",
                    aggregate_id=command.identity.session_id,
                    payload={"user_id": str(command.identity.user_id)},
                )
            )
        try:
            await session_store.deactivate(command.identity.session_id)
        except SessionStoreError as exc:
            raise SessionStoreUnavailable from exc
        await uow.commit()


class IntrospectAccessToken:
    async def execute(
        self,
        token: str,
        *,
        session_store: SessionStore,
    ) -> AccessTokenClaims | None:
        """Check JWT claims and immediate session revocation state."""
        try:
            claims = decode_access_token(token)
            active = await session_store.is_active(
                session_id=claims.session_id,
                user_id=claims.user_id,
            )
        except jwt.PyJWTError:
            return None
        except SessionStoreError as exc:
            raise SessionStoreUnavailable from exc
        return claims if active else None
