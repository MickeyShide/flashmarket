"""FastAPI dependencies for dependency injection."""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from jwt_verifier import JWTVerifier, Principal, create_auth_dependencies
from sqlalchemy.ext.asyncio import AsyncSession

from wishlist.application.services.wishlist import WishlistService
from wishlist.config import get_settings
from wishlist.infrastructure.database import get_db
from wishlist.infrastructure.repositories.wishlist import WishlistRepository

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


def get_wishlist_service(db: DbSession) -> WishlistService:
    """Instantiate and provide WishlistService with repository."""
    repo = WishlistRepository(db)
    settings = get_settings()
    return WishlistService(session=db, repo=repo, max_items=settings.max_items_per_user)


WishlistServiceDep = Annotated[WishlistService, Depends(get_wishlist_service)]
