"""Service for managing and applying promocodes."""

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from orders.application.schemas import (
    CreatePromocodeRequest,
    UpdatePromocodeRequest,
)
from orders.domain.entities import DiscountType, PromocodeStatus
from orders.domain.exceptions import (
    DuplicatePromocodeCode,
    PromocodeAlreadyUsed,
    PromocodeDisabled,
    PromocodeExpired,
    PromocodeLimitReached,
    PromocodeMinAmountNotMet,
    PromocodeNotFound,
)
from orders.infrastructure.database import utc_now
from orders.infrastructure.models import PromocodeModel, PromocodeUsageModel
from orders.infrastructure.repositories.promocode import PromocodePage, PromocodeRepository


@dataclass(frozen=True, slots=True)
class PromocodeResult:
    """Result of applying a promocode."""

    promocode_id: UUID
    discount_amount: Decimal
    final_amount: Decimal


class PromocodeService:
    """Business logic for promocodes validation, application, and tracking."""

    def __init__(
        self,
        session: AsyncSession,
        repo: PromocodeRepository,
    ) -> None:
        self._session = session
        self._repo = repo

    async def create_promocode(self, data: CreatePromocodeRequest) -> PromocodeModel:
        """Create a new promocode."""
        normalized_code = data.code.strip().upper()
        existing = await self._repo.get_by_code(normalized_code, for_update=False)
        if existing is not None:
            raise DuplicatePromocodeCode()

        promo = PromocodeModel(
            code=normalized_code,
            discount_type=data.discount_type,
            discount_value=data.discount_value,
            currency=data.currency,
            min_order_amount=data.min_order_amount,
            max_discount_amount=data.max_discount_amount,
            max_uses=data.max_uses,
            max_uses_per_user=data.max_uses_per_user,
            current_uses=0,
            status=PromocodeStatus.ACTIVE,
            starts_at=data.starts_at,
            expires_at=data.expires_at,
        )

        try:
            await self._repo.create(promo)
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            raise DuplicatePromocodeCode() from exc

        return promo

    async def validate_and_apply(
        self, code: str, user_id: UUID, order_amount: Decimal, for_update: bool = True
    ) -> PromocodeResult:
        """Validate a promocode and calculate discount."""
        normalized_code = code.strip().upper()
        promo = await self._repo.get_by_code(normalized_code, for_update=for_update)
        if not promo:
            raise PromocodeNotFound()

        if promo.status != PromocodeStatus.ACTIVE:
            raise PromocodeDisabled()

        now = utc_now()
        starts_at = promo.starts_at.replace(tzinfo=UTC) if promo.starts_at.tzinfo is None else promo.starts_at
        expires_at = promo.expires_at.replace(tzinfo=UTC) if promo.expires_at.tzinfo is None else promo.expires_at
        if now < starts_at or now > expires_at:
            raise PromocodeExpired()

        if promo.max_uses is not None and promo.current_uses >= promo.max_uses:
            raise PromocodeLimitReached()

        user_usages = await self._repo.count_user_usages(promo.id, user_id)
        if user_usages >= promo.max_uses_per_user:
            raise PromocodeAlreadyUsed()

        if promo.min_order_amount is not None and order_amount < promo.min_order_amount:
            raise PromocodeMinAmountNotMet()

        if promo.discount_type == DiscountType.FIXED:
            discount = min(promo.discount_value, order_amount)
        else:  # PERCENTAGE
            discount = order_amount * promo.discount_value / Decimal("100")
            if promo.max_discount_amount is not None:
                discount = min(discount, promo.max_discount_amount)
            if discount > order_amount:
                discount = order_amount

        discount = discount.quantize(Decimal("0.01"))
        final = (order_amount - discount).quantize(Decimal("0.01"))

        return PromocodeResult(
            promocode_id=promo.id,
            discount_amount=discount,
            final_amount=final,
        )

    async def record_usage(
        self, promo_id: UUID, user_id: UUID, order_id: UUID, discount_amount: Decimal
    ) -> PromocodeUsageModel:
        """Record usage of a promocode by a user for an order."""
        usage = PromocodeUsageModel(
            promocode_id=promo_id,
            user_id=user_id,
            order_id=order_id,
            discount_amount=discount_amount,
        )
        await self._repo.add_usage(usage)

        promo = await self._repo.get_by_id(promo_id)
        if promo:
            promo.current_uses += 1
            await self._repo.update(promo)

        return usage

    async def get_by_id(self, promo_id: UUID) -> PromocodeModel:
        """Fetch promocode by ID."""
        promo = await self._repo.get_by_id(promo_id)
        if not promo:
            raise PromocodeNotFound()
        return promo

    async def list_promocodes(self, limit: int, offset: int) -> PromocodePage:
        """List promocodes with pagination."""
        return await self._repo.list_all(limit, offset)

    async def update_promocode(
        self, promo_id: UUID, data: UpdatePromocodeRequest
    ) -> PromocodeModel:
        """Update fields of an existing promocode."""
        promo = await self._repo.get_by_id(promo_id)
        if not promo:
            raise PromocodeNotFound()

        if data.discount_type is not None:
            promo.discount_type = data.discount_type
        if data.discount_value is not None:
            promo.discount_value = data.discount_value
        if data.currency is not None:
            promo.currency = data.currency
        if data.min_order_amount is not None:
            promo.min_order_amount = data.min_order_amount
        if data.max_discount_amount is not None:
            promo.max_discount_amount = data.max_discount_amount
        if data.max_uses is not None:
            promo.max_uses = data.max_uses
        if data.max_uses_per_user is not None:
            promo.max_uses_per_user = data.max_uses_per_user
        if data.status is not None:
            promo.status = data.status
        if data.starts_at is not None:
            promo.starts_at = data.starts_at
        if data.expires_at is not None:
            promo.expires_at = data.expires_at

        if promo.expires_at <= promo.starts_at:
            raise ValueError("expires_at must be after starts_at")

        await self._repo.update(promo)
        await self._session.commit()
        return promo
