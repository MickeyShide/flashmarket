"""FastAPI dependencies for dependency injection."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from drops.application.services.drop import DropService
from drops.infrastructure.database import get_db
from drops.infrastructure.repositories.drop import DropRepository
from drops.infrastructure.repositories.outbox import OutboxRepository

from functools import lru_cache
from jwt_verifier import JWTVerifier, Principal, create_auth_dependencies
from drops.config import get_settings

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


def get_drop_service(db: DbSession) -> DropService:
    """Instantiate and provide DropService with repositories."""
    repo = DropRepository(db)
    outbox_repo = OutboxRepository(db)
    return DropService(session=db, repo=repo, outbox_repo=outbox_repo)


DropServiceDep = Annotated[DropService, Depends(get_drop_service)]
