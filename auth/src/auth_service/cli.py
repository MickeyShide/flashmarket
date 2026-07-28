import argparse
import asyncio
import uuid
from datetime import timedelta

from email_validator import EmailNotValidError, validate_email
from sqlalchemy import delete, or_

from auth_service.application.contracts import RequestContext
from auth_service.cache import redis_client
from auth_service.config import get_settings
from auth_service.database import SessionFactory, engine
from auth_service.domain.events import DomainEvent, EventType
from auth_service.identity import normalize_email
from auth_service.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork
from auth_service.infrastructure.redis_session_store import RedisSessionStore
from auth_service.models import (
    AuditEvent,
    LoginSession,
    OutboxEvent,
    RefreshToken,
    User,
    UserRole,
)
from auth_service.security import hash_password, verify_password
from auth_service.time import utc_now


async def create_admin(
    email: str,
    password: str,
    full_name: str | None,
    *,
    promote_existing: bool,
) -> None:
    """Create an administrator account from CLI input."""
    try:
        normalized_email = validate_email(
            email,
            check_deliverability=False,
        ).normalized
        normalized_email = normalize_email(normalized_email)
    except EmailNotValidError as exc:
        raise ValueError("A valid admin email is required") from exc
    if len(password) < 12:
        raise ValueError("Password must contain at least 12 characters")
    if full_name is not None:
        full_name = " ".join(full_name.split())
        if not full_name or len(full_name) > 120:
            raise ValueError("Full name must contain between 1 and 120 characters")

    async with SessionFactory() as db:
        uow = SqlAlchemyUnitOfWork(db)
        user = await uow.users.get_by_email_for_update(normalized_email)
        if user is None:
            user = User(
                id=uuid.uuid7(),
                email=normalized_email,
                password_hash=hash_password(password),
                full_name=full_name,
                role=UserRole.ADMIN,
            )
            await uow.users.add_new(user)
            action = "created"
            previous_role = None
        else:
            if not promote_existing:
                raise ValueError("User already exists; pass --promote-existing explicitly")
            if not verify_password(password, user.password_hash):
                raise ValueError("The supplied password does not match the existing user")
            previous_role = user.role
            user.role = UserRole.ADMIN
            session_ids = await uow.sessions.revoke_all_for_user(
                user.id,
                reason="admin_promoted_by_cli",
            )
            await RedisSessionStore(redis_client).deactivate_many(session_ids)
            action = "promoted"
        uow.audit.add(
            RequestContext(request_id=None, ip_address=None, user_agent=None),
            event_type=f"admin_{action}_by_cli",
            subject_user_id=user.id,
        )
        if action == "created":
            uow.add_event(
                DomainEvent(
                    event_type=EventType.USER_REGISTERED,
                    aggregate_type="user",
                    aggregate_id=user.id,
                    payload={
                        "email": user.email,
                        "role": user.role.value,
                        "source": "admin_cli",
                    },
                )
            )
        elif previous_role != UserRole.ADMIN:
            uow.add_event(
                DomainEvent(
                    event_type=EventType.USER_ROLE_CHANGED,
                    aggregate_type="user",
                    aggregate_id=user.id,
                    payload={
                        "previous_role": previous_role.value,
                        "new_role": UserRole.ADMIN.value,
                        "source": "admin_cli",
                    },
                )
            )
        await uow.commit()
        print(f"Admin {normalized_email} {action}.")
    await redis_client.aclose()
    await engine.dispose()


async def cleanup_expired_data() -> None:
    """Remove expired refresh tokens and audit records."""
    settings = get_settings()
    now = utc_now()
    expired_cutoff = now - timedelta(days=settings.expired_data_retention_days)
    audit_cutoff = now - timedelta(days=settings.audit_retention_days)

    async with SessionFactory() as db:
        session_result = await db.execute(
            delete(LoginSession).where(
                or_(
                    LoginSession.expires_at < expired_cutoff,
                    LoginSession.revoked_at < expired_cutoff,
                )
            )
        )
        refresh_result = await db.execute(
            delete(RefreshToken).where(RefreshToken.expires_at < expired_cutoff)
        )
        audit_result = await db.execute(
            delete(AuditEvent).where(AuditEvent.created_at < audit_cutoff)
        )
        outbox_result = await db.execute(
            delete(OutboxEvent).where(OutboxEvent.published_at < expired_cutoff)
        )
        await db.commit()
        print(
            "Cleanup complete: "
            f"sessions={session_result.rowcount}, "
            f"refresh_tokens={refresh_result.rowcount}, "
            f"audit_events={audit_result.rowcount}, "
            f"outbox_events={outbox_result.rowcount}."
        )
    await engine.dispose()


def main() -> None:
    """Run this module as a command-line entry point."""
    parser = argparse.ArgumentParser(description="FlashMarket auth administration")
    subparsers = parser.add_subparsers(dest="command", required=True)
    create_admin_parser = subparsers.add_parser("create-admin")
    create_admin_parser.add_argument("--email", required=True)
    create_admin_parser.add_argument("--password", required=True)
    create_admin_parser.add_argument("--full-name")
    create_admin_parser.add_argument("--promote-existing", action="store_true")
    subparsers.add_parser("cleanup-expired")
    args = parser.parse_args()

    if args.command == "create-admin":
        asyncio.run(
            create_admin(
                args.email,
                args.password,
                args.full_name,
                promote_existing=args.promote_existing,
            )
        )
    elif args.command == "cleanup-expired":
        asyncio.run(cleanup_expired_data())


if __name__ == "__main__":
    main()
