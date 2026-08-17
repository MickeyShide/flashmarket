"""Repository for managing promocodes and promocode usage records."""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from orders.infrastructure.models import PromocodeModel, PromocodeUsageModel


@dataclass(frozen=True, slots=True)
class PromocodePage:
    """Paginated result for promocodes."""

    items: list[PromocodeModel]
    total: int


class PromocodeRepository:
    """Data-access operations for PromocodeModel and PromocodeUsageModel."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, promo: PromocodeModel) -> PromocodeModel:
        """Persist a new promocode."""
        self._session.add(promo)
        await self._session.flush()
        return promo

    async def get_by_code(self, code: str, for_update: bool = True) -> PromocodeModel | None:
        """Retrieve a promocode by uppercase code with optional pessimistic lock."""
        normalized_code = code.strip().upper()
        stmt = select(PromocodeModel).where(PromocodeModel.code == normalized_code)
        if for_update:
            stmt = stmt.with_for_update()
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, promo_id: UUID) -> PromocodeModel | None:
        """Retrieve a promocode by ID."""
        stmt = select(PromocodeModel).where(PromocodeModel.id == promo_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id_for_update(self, promo_id: UUID) -> PromocodeModel | None:
        """Retrieve a promocode by ID with row lock."""
        stmt = select(PromocodeModel).where(PromocodeModel.id == promo_id).with_for_update()
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all(self, limit: int, offset: int) -> PromocodePage:
        """List all promocodes with pagination ordered by created_at DESC."""
        count_stmt = select(func.count()).select_from(PromocodeModel)
        total_result = await self._session.execute(count_stmt)
        total = total_result.scalar_one()

        stmt = (
            select(PromocodeModel)
            .order_by(PromocodeModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        items_result = await self._session.execute(stmt)
        items = list(items_result.scalars().all())

        return PromocodePage(items=items, total=total)

    async def update(self, promo: PromocodeModel) -> PromocodeModel:
        """Flush changes to a promocode model."""
        await self._session.flush()
        return promo

    async def count_user_usages(self, promo_id: UUID, user_id: UUID) -> int:
        """Count how many times a user has used a specific promocode."""
        stmt = (
            select(func.count())
            .select_from(PromocodeUsageModel)
            .where(
                PromocodeUsageModel.promocode_id == promo_id,
                PromocodeUsageModel.user_id == user_id,
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def add_usage(self, usage: PromocodeUsageModel) -> PromocodeUsageModel:
        """Persist a promocode usage record."""
        self._session.add(usage)
        await self._session.flush()
        return usage

    async def delete_usage_for_order(self, promo_id: UUID, order_id: UUID) -> bool:
        """Delete a promocode usage record by order_id."""
        result = await self._session.execute(
            select(PromocodeUsageModel).where(
                PromocodeUsageModel.promocode_id == promo_id,
                PromocodeUsageModel.order_id == order_id,
            )
        )
        usage = result.scalar_one_or_none()
        if usage is not None:
            await self._session.delete(usage)
            await self._session.flush()
            return True
        return False
