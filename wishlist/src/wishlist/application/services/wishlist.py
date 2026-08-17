"""Application service for handling wishlist business logic."""

from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from wishlist.application.schemas import AddToWishlistRequest, WishlistListParams
from wishlist.domain.exceptions import (
    ItemAlreadyInWishlist,
    ItemNotInWishlist,
    WishlistLimitReached,
)
from wishlist.infrastructure.models import WishlistItemModel
from wishlist.infrastructure.repositories.wishlist import WishlistPage, WishlistRepository


class WishlistService:
    """Orchestrates wishlist domain logic and persistence."""

    def __init__(
        self,
        session: AsyncSession,
        repo: WishlistRepository,
        max_items: int,
    ) -> None:
        self._session = session
        self._repo = repo
        self._max_items = max_items

    async def add_item(self, user_id: UUID, data: AddToWishlistRequest) -> WishlistItemModel:
        """Add a product to user's wishlist."""
        await self._repo.lock_user_wishlist(user_id)

        if await self._repo.exists(user_id, data.product_id):
            raise ItemAlreadyInWishlist()

        count = await self._repo.count_by_user(user_id)
        if count >= self._max_items:
            raise WishlistLimitReached()

        item = WishlistItemModel(user_id=user_id, product_id=data.product_id)
        try:
            await self._repo.add(item)
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            raise ItemAlreadyInWishlist() from exc

        return item

    async def remove_item(self, user_id: UUID, product_id: UUID) -> None:
        """Remove a product from user's wishlist."""
        removed = await self._repo.remove(user_id, product_id)
        if not removed:
            raise ItemNotInWishlist()

        await self._session.commit()

    async def list_items(self, user_id: UUID, params: WishlistListParams) -> WishlistPage:
        """Fetch paginated wishlist items for user."""
        return await self._repo.get_by_user(user_id, params.limit, params.offset)

    async def check_items(self, user_id: UUID, product_ids: list[UUID]) -> set[UUID]:
        """Check which of the provided product IDs are in user's wishlist."""
        return await self._repo.get_product_ids_for_user(user_id, product_ids)
