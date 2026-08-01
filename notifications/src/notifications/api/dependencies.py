"""FastAPI dependency injection wiring."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from notifications.application.services.notification import NotificationService
from notifications.infrastructure.database import get_db
from notifications.infrastructure.repositories.notification import (
    NotificationRepository,
    OutboxRepository,
)

from functools import lru_cache
from jwt_verifier import JWTVerifier, Principal, create_auth_dependencies
from notifications.config import get_settings

DbSession = Annotated[AsyncSession, Depends(get_db)]


@lru_cache
def get_verifier() -> JWTVerifier:
    settings = get_settings()
    return JWTVerifier(
        public_key_dir=settings.jwt_public_key_dir,
        algorithm=settings.jwt_algorithm,
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
    )


get_optional_principal, get_current_principal, require_admin = create_auth_dependencies(get_verifier)

OptionalPrincipal = Annotated[Principal | None, Depends(get_optional_principal)]
CurrentPrincipal = Annotated[Principal, Depends(get_current_principal)]
AdminPrincipal = Annotated[Principal, Depends(require_admin)]


def get_notification_service(db: DbSession) -> NotificationService:
    """Build a notification service for the current request."""
    return NotificationService(
        session=db,
        notification_repo=NotificationRepository(db),
        outbox_repo=OutboxRepository(db),
    )


NotificationServiceDep = Annotated[NotificationService, Depends(get_notification_service)]
