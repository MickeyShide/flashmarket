import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from auth_service.application.contracts import (
    SessionStore,
    SessionStoreError,
    UnitOfWork,
)
from auth_service.cache import (
    Cache,
    CacheUnavailableError,
    should_touch_session,
)
from auth_service.config import get_settings
from auth_service.database import get_db
from auth_service.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork
from auth_service.infrastructure.redis_session_store import RedisSessionStore
from auth_service.models import UserRole
from auth_service.security import decode_access_token

DbSession = Annotated[AsyncSession, Depends(get_db)]


def get_uow(db: DbSession) -> SqlAlchemyUnitOfWork:
    """Build a unit of work for the current database session."""
    return SqlAlchemyUnitOfWork(db)


Uow = Annotated[UnitOfWork, Depends(get_uow)]
bearer_scheme = HTTPBearer(auto_error=False)


def get_session_store(cache: Cache) -> SessionStore:
    """Build the Redis-backed session store."""
    return RedisSessionStore(cache)


SessionStoreDep = Annotated[SessionStore, Depends(get_session_store)]


@dataclass(frozen=True)
class Principal:
    user_id: uuid.UUID
    session_id: uuid.UUID
    role: UserRole
    token_id: uuid.UUID
    expires_at: datetime


async def get_current_principal(
    uow: Uow,
    cache: Cache,
    session_store: SessionStoreDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> Principal:
    """Authenticate the bearer token and load its principal."""
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired access token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise unauthorized

    try:
        claims = decode_access_token(credentials.credentials)
    except jwt.PyJWTError as exc:
        raise unauthorized from exc

    try:
        active = await session_store.is_active(
            session_id=claims.session_id,
            user_id=claims.user_id,
        )
    except SessionStoreError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Session store is unavailable",
        ) from exc
    if not active:
        raise unauthorized
    try:
        touch_session = await should_touch_session(
            cache,
            session_id=claims.session_id,
            interval_seconds=get_settings().session_touch_interval_minutes * 60,
        )
    except CacheUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Session store is unavailable",
        ) from exc
    if touch_session:
        await uow.sessions.touch_active(
            claims.session_id,
            claims.user_id,
        )
        await uow.commit()
    return Principal(
        user_id=claims.user_id,
        session_id=claims.session_id,
        role=claims.role,
        token_id=claims.token_id,
        expires_at=claims.expires_at,
    )


CurrentPrincipal = Annotated[Principal, Depends(get_current_principal)]


async def require_admin(principal: CurrentPrincipal) -> Principal:
    """Reject a request unless its principal is an administrator."""
    if principal.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator role required",
        )
    return principal


AdminPrincipal = Annotated[Principal, Depends(require_admin)]
