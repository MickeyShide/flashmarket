"""Unit and integration tests for PromocodeService logic."""

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from orders.application.schemas import CreatePromocodeRequest
from orders.application.services.promocode import PromocodeService
from orders.domain.entities import DiscountType, PromocodeStatus
from orders.domain.exceptions import (
    DuplicatePromocodeCode,
    PromocodeAlreadyUsed,
    PromocodeDisabled,
    PromocodeExpired,
    PromocodeLimitReached,
    PromocodeMinAmountNotMet,
)
from orders.infrastructure.repositories.promocode import PromocodeRepository


@pytest.mark.asyncio
async def test_create_promocode(session_factory: async_sessionmaker[AsyncSession]) -> None:
    async with session_factory() as session:
        repo = PromocodeRepository(session)
        service = PromocodeService(session, repo)

        now = datetime.now(UTC)
        req = CreatePromocodeRequest(
            code="SUMMER500",
            discount_type=DiscountType.FIXED,
            discount_value=Decimal("500.00"),
            currency="RUB",
            min_order_amount=Decimal("1000.00"),
            starts_at=now - timedelta(hours=1),
            expires_at=now + timedelta(days=7),
        )

        promo = await service.create_promocode(req)
        assert promo.id is not None
        assert promo.code == "SUMMER500"
        assert promo.discount_type == DiscountType.FIXED
        assert promo.discount_value == Decimal("500.00")
        assert promo.status == PromocodeStatus.ACTIVE


@pytest.mark.asyncio
async def test_create_duplicate_code(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        repo = PromocodeRepository(session)
        service = PromocodeService(session, repo)

        now = datetime.now(UTC)
        req = CreatePromocodeRequest(
            code="dupcode",
            discount_type=DiscountType.FIXED,
            discount_value=Decimal("100.00"),
            starts_at=now - timedelta(hours=1),
            expires_at=now + timedelta(days=7),
        )

        await service.create_promocode(req)

        with pytest.raises(DuplicatePromocodeCode):
            await service.create_promocode(req)


@pytest.mark.asyncio
async def test_validate_fixed_discount(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        repo = PromocodeRepository(session)
        service = PromocodeService(session, repo)

        now = datetime.now(UTC)
        await service.create_promocode(
            CreatePromocodeRequest(
                code="FIXED500",
                discount_type=DiscountType.FIXED,
                discount_value=Decimal("500.00"),
                starts_at=now - timedelta(hours=1),
                expires_at=now + timedelta(days=7),
            )
        )

        user_id = uuid.uuid4()
        res = await service.validate_and_apply(
            "FIXED500", user_id, Decimal("2000.00"), for_update=False
        )

        assert res.discount_amount == Decimal("500.00")
        assert res.final_amount == Decimal("1500.00")


@pytest.mark.asyncio
async def test_validate_percentage_discount(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        repo = PromocodeRepository(session)
        service = PromocodeService(session, repo)

        now = datetime.now(UTC)
        await service.create_promocode(
            CreatePromocodeRequest(
                code="PERCENT10",
                discount_type=DiscountType.PERCENTAGE,
                discount_value=Decimal("10.00"),
                starts_at=now - timedelta(hours=1),
                expires_at=now + timedelta(days=7),
            )
        )

        user_id = uuid.uuid4()
        res = await service.validate_and_apply(
            "PERCENT10", user_id, Decimal("10000.00"), for_update=False
        )

        assert res.discount_amount == Decimal("1000.00")
        assert res.final_amount == Decimal("9000.00")


@pytest.mark.asyncio
async def test_validate_percentage_with_cap(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        repo = PromocodeRepository(session)
        service = PromocodeService(session, repo)

        now = datetime.now(UTC)
        await service.create_promocode(
            CreatePromocodeRequest(
                code="CAP20",
                discount_type=DiscountType.PERCENTAGE,
                discount_value=Decimal("20.00"),
                max_discount_amount=Decimal("500.00"),
                starts_at=now - timedelta(hours=1),
                expires_at=now + timedelta(days=7),
            )
        )

        user_id = uuid.uuid4()
        res = await service.validate_and_apply(
            "CAP20", user_id, Decimal("10000.00"), for_update=False
        )

        assert res.discount_amount == Decimal("500.00")
        assert res.final_amount == Decimal("9500.00")


@pytest.mark.asyncio
async def test_validate_expired(session_factory: async_sessionmaker[AsyncSession]) -> None:
    async with session_factory() as session:
        repo = PromocodeRepository(session)
        service = PromocodeService(session, repo)

        now = datetime.now(UTC)
        await service.create_promocode(
            CreatePromocodeRequest(
                code="EXPIREDPROMO",
                discount_type=DiscountType.FIXED,
                discount_value=Decimal("100.00"),
                starts_at=now - timedelta(days=10),
                expires_at=now - timedelta(days=1),
            )
        )

        user_id = uuid.uuid4()
        with pytest.raises(PromocodeExpired):
            await service.validate_and_apply(
                "EXPIREDPROMO", user_id, Decimal("1000.00"), for_update=False
            )


@pytest.mark.asyncio
async def test_validate_disabled(session_factory: async_sessionmaker[AsyncSession]) -> None:
    async with session_factory() as session:
        repo = PromocodeRepository(session)
        service = PromocodeService(session, repo)

        now = datetime.now(UTC)
        promo = await service.create_promocode(
            CreatePromocodeRequest(
                code="DISABLEME",
                discount_type=DiscountType.FIXED,
                discount_value=Decimal("100.00"),
                starts_at=now - timedelta(hours=1),
                expires_at=now + timedelta(days=7),
            )
        )

        promo.status = PromocodeStatus.DISABLED
        await session.commit()

        user_id = uuid.uuid4()
        with pytest.raises(PromocodeDisabled):
            await service.validate_and_apply(
                "DISABLEME", user_id, Decimal("1000.00"), for_update=False
            )


@pytest.mark.asyncio
async def test_validate_limit_reached(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        repo = PromocodeRepository(session)
        service = PromocodeService(session, repo)

        now = datetime.now(UTC)
        promo = await service.create_promocode(
            CreatePromocodeRequest(
                code="ONETIME",
                discount_type=DiscountType.FIXED,
                discount_value=Decimal("100.00"),
                max_uses=1,
                starts_at=now - timedelta(hours=1),
                expires_at=now + timedelta(days=7),
            )
        )

        user1 = uuid.uuid4()
        await service.record_usage(promo.id, user1, uuid.uuid4(), Decimal("100.00"))
        await session.commit()

        user2 = uuid.uuid4()
        with pytest.raises(PromocodeLimitReached):
            await service.validate_and_apply("ONETIME", user2, Decimal("1000.00"), for_update=False)


@pytest.mark.asyncio
async def test_validate_user_limit(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        repo = PromocodeRepository(session)
        service = PromocodeService(session, repo)

        now = datetime.now(UTC)
        promo = await service.create_promocode(
            CreatePromocodeRequest(
                code="USERONCE",
                discount_type=DiscountType.FIXED,
                discount_value=Decimal("100.00"),
                max_uses_per_user=1,
                starts_at=now - timedelta(hours=1),
                expires_at=now + timedelta(days=7),
            )
        )

        user = uuid.uuid4()
        await service.record_usage(promo.id, user, uuid.uuid4(), Decimal("100.00"))
        await session.commit()

        with pytest.raises(PromocodeAlreadyUsed):
            await service.validate_and_apply("USERONCE", user, Decimal("1000.00"), for_update=False)


@pytest.mark.asyncio
async def test_validate_min_amount(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        repo = PromocodeRepository(session)
        service = PromocodeService(session, repo)

        now = datetime.now(UTC)
        await service.create_promocode(
            CreatePromocodeRequest(
                code="MIN5000",
                discount_type=DiscountType.FIXED,
                discount_value=Decimal("500.00"),
                min_order_amount=Decimal("5000.00"),
                starts_at=now - timedelta(hours=1),
                expires_at=now + timedelta(days=7),
            )
        )

        user_id = uuid.uuid4()
        with pytest.raises(PromocodeMinAmountNotMet):
            await service.validate_and_apply(
                "MIN5000", user_id, Decimal("3000.00"), for_update=False
            )


@pytest.mark.asyncio
async def test_discount_not_exceed_order(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        repo = PromocodeRepository(session)
        service = PromocodeService(session, repo)

        now = datetime.now(UTC)
        await service.create_promocode(
            CreatePromocodeRequest(
                code="HUGE5000",
                discount_type=DiscountType.FIXED,
                discount_value=Decimal("5000.00"),
                starts_at=now - timedelta(hours=1),
                expires_at=now + timedelta(days=7),
            )
        )

        user_id = uuid.uuid4()
        res = await service.validate_and_apply(
            "HUGE5000", user_id, Decimal("3000.00"), for_update=False
        )

        assert res.discount_amount == Decimal("3000.00")
        assert res.final_amount == Decimal("0.00")


@pytest.mark.asyncio
async def test_code_case_insensitive(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        repo = PromocodeRepository(session)
        service = PromocodeService(session, repo)

        now = datetime.now(UTC)
        await service.create_promocode(
            CreatePromocodeRequest(
                code="flash10",
                discount_type=DiscountType.PERCENTAGE,
                discount_value=Decimal("10.00"),
                starts_at=now - timedelta(hours=1),
                expires_at=now + timedelta(days=7),
            )
        )

        user_id = uuid.uuid4()
        res1 = await service.validate_and_apply(
            "flash10", user_id, Decimal("1000.00"), for_update=False
        )
        res2 = await service.validate_and_apply(
            "FLASH10", user_id, Decimal("1000.00"), for_update=False
        )

        assert res1.promocode_id == res2.promocode_id
