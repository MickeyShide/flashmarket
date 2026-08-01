"""FastAPI dependencies for Media."""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from jwt_verifier import JWTVerifier, Principal, create_auth_dependencies
from sqlalchemy.ext.asyncio import AsyncSession

from media_service.application.contracts import ObjectStorage
from media_service.application.services.assets import MediaAssetService
from media_service.config import get_settings
from media_service.infrastructure.database import get_db
from media_service.infrastructure.repositories import MediaAssetRepository
from media_service.infrastructure.s3_storage import S3ObjectStorage

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


get_optional_principal, get_current_principal, require_admin = create_auth_dependencies(
    get_verifier
)

OptionalPrincipal = Annotated[Principal | None, Depends(get_optional_principal)]
CurrentPrincipal = Annotated[Principal, Depends(get_current_principal)]
AdminPrincipal = Annotated[Principal, Depends(require_admin)]


@lru_cache
def get_storage() -> ObjectStorage:
    """Return the process-wide S3 adapter."""
    return S3ObjectStorage(get_settings())


def get_media_service(
    db: DbSession,
    storage: Annotated[ObjectStorage, Depends(get_storage)],
) -> MediaAssetService:
    """Build a request-scoped Media application service."""
    return MediaAssetService(db, MediaAssetRepository(db), storage, get_settings())


MediaServiceDep = Annotated[MediaAssetService, Depends(get_media_service)]
StorageDep = Annotated[ObjectStorage, Depends(get_storage)]
