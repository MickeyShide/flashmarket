import uuid

from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from auth_service.application.contracts import (
    AuditEventPage,
    AuditEventSearch,
    RefreshContext,
    RequestContext,
    UserEmailConflictError,
    UserPage,
    UserSearch,
)
from auth_service.models import AuditEvent, LoginSession, RefreshToken, User
from auth_service.privacy import anonymize_ip
from auth_service.time import utc_now


class SqlAlchemyUserRepository:
    def __init__(self, session: AsyncSession) -> None:
        """Initialize SqlAlchemyUserRepository."""
        self._session = session

    async def add_new(self, user: User) -> None:
        """Stage a newly registered user for insertion."""
        self._session.add(user)
        try:
            await self._session.flush()
        except IntegrityError as exc:
            raise UserEmailConflictError from exc

    async def get_by_email(self, email: str) -> User | None:
        """Find a user by normalized email address."""
        return await self._session.scalar(select(User).where(User.email == email))

    async def get_by_email_for_update(self, email: str) -> User | None:
        """Lock a user found by normalized email address."""
        return await self._session.scalar(select(User).where(User.email == email).with_for_update())

    async def get_active(self, user_id: uuid.UUID) -> User | None:
        """Find an enabled user by ID."""
        return await self._session.scalar(
            select(User).where(
                User.id == user_id,
                User.is_active.is_(True),
            )
        )

    async def get_active_for_update(self, user_id: uuid.UUID) -> User | None:
        """Lock an enabled user by ID."""
        return await self._session.scalar(
            select(User)
            .where(
                User.id == user_id,
                User.is_active.is_(True),
            )
            .with_for_update()
        )

    async def get_for_update(self, user_id: uuid.UUID) -> User | None:
        """Lock a user by ID, including disabled accounts."""
        return await self._session.scalar(select(User).where(User.id == user_id).with_for_update())

    async def search(self, query: UserSearch) -> UserPage:
        """Search records using the supplied filters."""
        filters = []
        if query.search:
            pattern = f"%{query.search.lower()}%"
            filters.append(
                or_(
                    func.lower(User.email).like(pattern),
                    func.lower(User.full_name).like(pattern),
                )
            )
        if query.role is not None:
            filters.append(User.role == query.role)
        if query.is_active is not None:
            filters.append(User.is_active.is_(query.is_active))

        statement = select(User).where(*filters)
        users = (
            await self._session.scalars(
                statement.order_by(User.created_at.desc()).limit(query.limit).offset(query.offset)
            )
        ).all()
        total = await self._session.scalar(select(func.count()).select_from(User).where(*filters))
        return UserPage(items=list(users), total=total or 0)


class SqlAlchemySessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        """Initialize SqlAlchemySessionRepository."""
        self._session = session

    async def persist_new(
        self,
        login_session: LoginSession,
        refresh_token: RefreshToken,
    ) -> None:
        """Store a new login session with its initial refresh token."""
        self._session.add_all([login_session, refresh_token])
        await self._session.flush()

    async def persist_replacement(self, refresh_token: RefreshToken) -> None:
        """Store a rotated refresh token for an existing session."""
        self._session.add(refresh_token)
        await self._session.flush()

    async def get_owned_for_update(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> LoginSession | None:
        """Lock a session only when it belongs to the user."""
        return await self._session.scalar(
            select(LoginSession)
            .where(
                LoginSession.id == session_id,
                LoginSession.user_id == user_id,
            )
            .with_for_update()
        )

    async def get_refresh_context_for_rotation(
        self,
        token_hash: str,
    ) -> RefreshContext | None:
        """Lock and load the state needed to rotate a refresh token."""
        row = (
            await self._session.execute(
                select(RefreshToken, LoginSession, User)
                .join(LoginSession, LoginSession.id == RefreshToken.session_id)
                .join(User, User.id == LoginSession.user_id)
                .where(RefreshToken.token_hash == token_hash)
                .with_for_update()
            )
        ).one_or_none()
        if row is None:
            return None
        refresh_token, login_session, user = row
        return RefreshContext(
            refresh_token=refresh_token,
            login_session=login_session,
            user=user,
        )

    async def list_for_user(self, user_id: uuid.UUID) -> list[LoginSession]:
        """List all sessions belonging to a user."""
        sessions = (
            await self._session.scalars(
                select(LoginSession)
                .where(LoginSession.user_id == user_id)
                .order_by(LoginSession.created_at.desc())
            )
        ).all()
        return list(sessions)

    async def revoke(self, login_session: LoginSession, *, reason: str) -> None:
        """Mark one login session as revoked."""
        if login_session.revoked_at is not None:
            return
        now = utc_now()
        login_session.revoked_at = now
        login_session.revocation_reason = reason
        await self._session.execute(
            update(RefreshToken)
            .where(
                RefreshToken.session_id == login_session.id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=now)
        )

    async def revoke_all_for_user(
        self,
        user_id: uuid.UUID,
        *,
        reason: str,
    ) -> list[uuid.UUID]:
        """Revoke all active sessions owned by a user."""
        now = utc_now()
        session_ids = (
            await self._session.scalars(
                update(LoginSession)
                .where(
                    LoginSession.user_id == user_id,
                    LoginSession.revoked_at.is_(None),
                )
                .values(revoked_at=now, revocation_reason=reason)
                .returning(LoginSession.id)
            )
        ).all()
        if session_ids:
            await self._session.execute(
                update(RefreshToken)
                .where(
                    RefreshToken.session_id.in_(session_ids),
                    RefreshToken.revoked_at.is_(None),
                )
                .values(revoked_at=now)
            )
        return list(session_ids)

    async def touch_active(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        """Update the last-seen timestamp of an active session."""
        await self._session.execute(
            update(LoginSession)
            .where(
                LoginSession.id == session_id,
                LoginSession.user_id == user_id,
                LoginSession.revoked_at.is_(None),
            )
            .values(last_seen_at=utc_now())
        )


class SqlAlchemyAuditRepository:
    def __init__(self, session: AsyncSession) -> None:
        """Initialize SqlAlchemyAuditRepository."""
        self._session = session

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
        self._session.add(
            AuditEvent(
                event_type=event_type,
                actor_user_id=actor_user_id,
                subject_user_id=subject_user_id,
                ip_address=anonymize_ip(context.ip_address),
                user_agent=context.user_agent[:512] if context.user_agent else None,
                request_id=context.request_id,
                event_data=event_data,
            )
        )

    async def search(self, query: AuditEventSearch) -> AuditEventPage:
        """Search records using the supplied filters."""
        filters = []
        if query.event_type is not None:
            filters.append(AuditEvent.event_type == query.event_type)
        if query.user_id is not None:
            filters.append(
                or_(
                    AuditEvent.actor_user_id == query.user_id,
                    AuditEvent.subject_user_id == query.user_id,
                )
            )

        statement = select(AuditEvent).where(*filters)
        events = (
            await self._session.scalars(
                statement.order_by(AuditEvent.created_at.desc())
                .limit(query.limit)
                .offset(query.offset)
            )
        ).all()
        total = await self._session.scalar(
            select(func.count()).select_from(AuditEvent).where(*filters)
        )
        return AuditEventPage(items=list(events), total=total or 0)
