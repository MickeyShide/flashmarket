"""Unit and integration tests for DropService logic."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from drops.application.schemas import AddDropItemRequest, CreateDropRequest
from drops.application.services.drop import DropService
from drops.domain.entities import DropStatus
from drops.domain.exceptions import (
    DuplicateDropSlug,
    InvalidDropState,
    ProductAlreadyInDrop,
)
from drops.infrastructure.repositories.drop import DropRepository
from drops.infrastructure.repositories.outbox import OutboxRepository


@pytest.mark.asyncio
async def test_create_drop(session_factory: async_sessionmaker[AsyncSession]) -> None:
    async with session_factory() as session:
        repo = DropRepository(session)
        outbox_repo = OutboxRepository(session)
        service = DropService(session, repo, outbox_repo)

        now = datetime.now(UTC)
        req = CreateDropRequest(
            name="Summer Sale Drop",
            slug="summer-sale",
            description="Big summer drop",
            starts_at=now + timedelta(hours=1),
            ends_at=now + timedelta(hours=5),
            max_per_user=2,
            payment_timeout_seconds=600,
        )

        drop = await service.create_drop(req)

        assert drop.id is not None
        assert drop.name == "Summer Sale Drop"
        assert drop.slug == "summer-sale"
        assert drop.status == DropStatus.DRAFT
        assert drop.max_per_user == 2


@pytest.mark.asyncio
async def test_create_duplicate_slug(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        repo = DropRepository(session)
        outbox_repo = OutboxRepository(session)
        service = DropService(session, repo, outbox_repo)

        now = datetime.now(UTC)
        req = CreateDropRequest(
            name="Drop 1",
            slug="duplicate-slug",
            starts_at=now + timedelta(hours=1),
            ends_at=now + timedelta(hours=5),
        )

        await service.create_drop(req)

        with pytest.raises(DuplicateDropSlug):
            await service.create_drop(req)


@pytest.mark.asyncio
async def test_schedule_drop(session_factory: async_sessionmaker[AsyncSession]) -> None:
    async with session_factory() as session:
        repo = DropRepository(session)
        outbox_repo = OutboxRepository(session)
        service = DropService(session, repo, outbox_repo)

        now = datetime.now(UTC)
        drop = await service.create_drop(
            CreateDropRequest(
                name="Drop to schedule",
                slug="sched-slug",
                starts_at=now + timedelta(hours=1),
                ends_at=now + timedelta(hours=5),
            )
        )

        scheduled_drop = await service.schedule_drop(drop.id)
        assert scheduled_drop.status == DropStatus.SCHEDULED


@pytest.mark.asyncio
async def test_start_drop(session_factory: async_sessionmaker[AsyncSession]) -> None:
    async with session_factory() as session:
        repo = DropRepository(session)
        outbox_repo = OutboxRepository(session)
        service = DropService(session, repo, outbox_repo)

        now = datetime.now(UTC)
        drop = await service.create_drop(
            CreateDropRequest(
                name="Drop to start",
                slug="start-slug",
                starts_at=now + timedelta(hours=1),
                ends_at=now + timedelta(hours=5),
            )
        )
        await service.schedule_drop(drop.id)

        started_drop = await service.start_drop(drop.id)
        assert started_drop.status == DropStatus.ACTIVE


@pytest.mark.asyncio
async def test_end_drop(session_factory: async_sessionmaker[AsyncSession]) -> None:
    async with session_factory() as session:
        repo = DropRepository(session)
        outbox_repo = OutboxRepository(session)
        service = DropService(session, repo, outbox_repo)

        now = datetime.now(UTC)
        drop = await service.create_drop(
            CreateDropRequest(
                name="Drop to end",
                slug="end-slug",
                starts_at=now + timedelta(hours=1),
                ends_at=now + timedelta(hours=5),
            )
        )
        await service.schedule_drop(drop.id)
        await service.start_drop(drop.id)

        ended_drop = await service.end_drop(drop.id)
        assert ended_drop.status == DropStatus.ENDED


@pytest.mark.asyncio
async def test_cancel_draft_and_active(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        repo = DropRepository(session)
        outbox_repo = OutboxRepository(session)
        service = DropService(session, repo, outbox_repo)

        now = datetime.now(UTC)
        drop1 = await service.create_drop(
            CreateDropRequest(
                name="Draft cancel",
                slug="cancel-1",
                starts_at=now + timedelta(hours=1),
                ends_at=now + timedelta(hours=5),
            )
        )
        cancelled1 = await service.cancel_drop(drop1.id)
        assert cancelled1.status == DropStatus.CANCELLED

        drop2 = await service.create_drop(
            CreateDropRequest(
                name="Active cancel",
                slug="cancel-2",
                starts_at=now + timedelta(hours=1),
                ends_at=now + timedelta(hours=5),
            )
        )
        await service.schedule_drop(drop2.id)
        await service.start_drop(drop2.id)
        cancelled2 = await service.cancel_drop(drop2.id)
        assert cancelled2.status == DropStatus.CANCELLED


@pytest.mark.asyncio
async def test_invalid_state_transition(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        repo = DropRepository(session)
        outbox_repo = OutboxRepository(session)
        service = DropService(session, repo, outbox_repo)

        now = datetime.now(UTC)
        drop = await service.create_drop(
            CreateDropRequest(
                name="Invalid state drop",
                slug="inv-state",
                starts_at=now + timedelta(hours=1),
                ends_at=now + timedelta(hours=5),
            )
        )
        await service.schedule_drop(drop.id)
        await service.start_drop(drop.id)
        await service.end_drop(drop.id)

        with pytest.raises(InvalidDropState):
            await service.start_drop(drop.id)


@pytest.mark.asyncio
async def test_add_item_to_draft(session_factory: async_sessionmaker[AsyncSession]) -> None:
    async with session_factory() as session:
        repo = DropRepository(session)
        outbox_repo = OutboxRepository(session)
        service = DropService(session, repo, outbox_repo)

        now = datetime.now(UTC)
        drop = await service.create_drop(
            CreateDropRequest(
                name="Drop with items",
                slug="item-drop",
                starts_at=now + timedelta(hours=1),
                ends_at=now + timedelta(hours=5),
            )
        )

        prod_id = uuid.uuid4()
        item = await service.add_item(drop.id, AddDropItemRequest(product_id=prod_id))

        assert item.drop_id == drop.id
        assert item.product_id == prod_id


@pytest.mark.asyncio
async def test_add_item_to_active_fails(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        repo = DropRepository(session)
        outbox_repo = OutboxRepository(session)
        service = DropService(session, repo, outbox_repo)

        now = datetime.now(UTC)
        drop = await service.create_drop(
            CreateDropRequest(
                name="Active drop item fail",
                slug="active-fail",
                starts_at=now + timedelta(hours=1),
                ends_at=now + timedelta(hours=5),
            )
        )
        await service.schedule_drop(drop.id)
        await service.start_drop(drop.id)

        with pytest.raises(InvalidDropState):
            await service.add_item(drop.id, AddDropItemRequest(product_id=uuid.uuid4()))


@pytest.mark.asyncio
async def test_add_duplicate_item(session_factory: async_sessionmaker[AsyncSession]) -> None:
    async with session_factory() as session:
        repo = DropRepository(session)
        outbox_repo = OutboxRepository(session)
        service = DropService(session, repo, outbox_repo)

        now = datetime.now(UTC)
        drop = await service.create_drop(
            CreateDropRequest(
                name="Dup item drop",
                slug="dup-item",
                starts_at=now + timedelta(hours=1),
                ends_at=now + timedelta(hours=5),
            )
        )

        prod_id = uuid.uuid4()
        await service.add_item(drop.id, AddDropItemRequest(product_id=prod_id))

        with pytest.raises(ProductAlreadyInDrop):
            await service.add_item(drop.id, AddDropItemRequest(product_id=prod_id))


@pytest.mark.asyncio
async def test_remove_item(session_factory: async_sessionmaker[AsyncSession]) -> None:
    async with session_factory() as session:
        repo = DropRepository(session)
        outbox_repo = OutboxRepository(session)
        service = DropService(session, repo, outbox_repo)

        now = datetime.now(UTC)
        drop = await service.create_drop(
            CreateDropRequest(
                name="Remove item drop",
                slug="rm-item",
                starts_at=now + timedelta(hours=1),
                ends_at=now + timedelta(hours=5),
            )
        )

        prod_id = uuid.uuid4()
        await service.add_item(drop.id, AddDropItemRequest(product_id=prod_id))
        await service.remove_item(drop.id, prod_id)

        fetched = await service.get_by_id(drop.id)
        assert len(fetched.items) == 0
