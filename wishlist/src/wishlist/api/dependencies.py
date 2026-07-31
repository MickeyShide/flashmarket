"""FastAPI dependencies for dependency injection."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from wishlist.application.services.wishlist import WishlistService
from wishlist.config import get_settings
from wishlist.infrastructure.database import get_db
from wishlist.infrastructure.repositories.wishlist import WishlistRepository

DbSession = Annotated[AsyncSession, Depends(get_db)]


def get_wishlist_service(db: DbSession) -> WishlistService:
    """Instantiate and provide WishlistService with repository."""
    repo = WishlistRepository(db)
    settings = get_settings()
    return WishlistService(session=db, repo=repo, max_items=settings.max_items_per_user)


WishlistServiceDep = Annotated[WishlistService, Depends(get_wishlist_service)]
