"""Repository for managing wishlist items in database."""

import json
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from wishlist.infrastructure.models import OutboxEventModel, WishlistItemModel


@dataclass(frozen=True, slots=True)
class WishlistPage:
    """Paginated result for wishlist items."""

    items: list[WishlistItemModel]
    total: int


class WishlistRepository:
    """Handles CRUD database operations for WishlistItemModel."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, item: WishlistItemModel) -> WishlistItemModel:
        self._session.add(item)
        await self._session.flush()
        return item

    async def remove(self, user_id: UUID, product_id: UUID) -> bool:
        stmt = delete(WishlistItemModel).where(
            WishlistItemModel.user_id == user_id,
            WishlistItemModel.product_id == product_id,
        )
        result = await self._session.execute(stmt)
        return bool(result.rowcount > 0)

    async def get_by_user(self, user_id: UUID, limit: int, offset: int) -> WishlistPage:
        count_stmt = (
            select(func.count())
            .select_from(WishlistItemModel)
            .where(WishlistItemModel.user_id == user_id)
        )
        total_result = await self._session.execute(count_stmt)
        total = total_result.scalar_one()

        stmt = (
            select(WishlistItemModel)
            .where(WishlistItemModel.user_id == user_id)
            .order_by(WishlistItemModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        items_result = await self._session.execute(stmt)
        items = list(items_result.scalars().all())

        return WishlistPage(items=items, total=total)

    async def exists(self, user_id: UUID, product_id: UUID) -> bool:
        stmt = (
            select(1)
            .where(
                WishlistItemModel.user_id == user_id,
                WishlistItemModel.product_id == product_id,
            )
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def count_by_user(self, user_id: UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(WishlistItemModel)
            .where(WishlistItemModel.user_id == user_id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def get_product_ids_for_user(self, user_id: UUID, product_ids: list[UUID]) -> set[UUID]:
        if not product_ids:
            return set()
        stmt = select(WishlistItemModel.product_id).where(
            WishlistItemModel.user_id == user_id,
            WishlistItemModel.product_id.in_(product_ids),
        )
        result = await self._session.execute(stmt)
        return set(result.scalars().all())

    async def get_users_for_products(self, product_ids: list[UUID]) -> list[UUID]:
        """Return distinct users watching any of the supplied products."""
        if not product_ids:
            return []
        result = await self._session.scalars(
            select(WishlistItemModel.user_id)
            .where(WishlistItemModel.product_id.in_(product_ids))
            .distinct()
        )
        return list(result.all())

    async def stage_drop_notifications(
        self,
        *,
        drop_id: str,
        drop_name: str,
        drop_slug: str,
        user_ids: list[UUID],
    ) -> int:
        """Stage idempotent per-user notification events in the current transaction."""
        staged = 0
        for user_id in user_ids:
            event_key = f"drop:{drop_id}:user:{user_id}"
            exists = await self._session.scalar(
                select(OutboxEventModel.id).where(OutboxEventModel.event_key == event_key)
            )
            if exists is not None:
                continue
            payload = {
                "event_key": event_key,
                "user_id": str(user_id),
                "drop_id": drop_id,
                "drop_name": drop_name,
                "drop_slug": drop_slug,
            }
            self._session.add(
                OutboxEventModel(
                    event_key=event_key,
                    event_type="DropAvailable",
                    payload=json.dumps(payload, separators=(",", ":")),
                )
            )
            staged += 1
        await self._session.flush()
        return staged
