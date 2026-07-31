"""Unit and integration tests for WishlistService logic."""

import uuid
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

import pytest

from wishlist.application.schemas import AddToWishlistRequest, WishlistListParams
from wishlist.application.services.wishlist import WishlistService
from wishlist.domain.exceptions import (
    ItemAlreadyInWishlist,
    ItemNotInWishlist,
    WishlistLimitReached,
)
from wishlist.infrastructure.repositories.wishlist import WishlistRepository


@pytest.mark.asyncio
async def test_add_item(session_factory: async_sessionmaker[AsyncSession]) -> None:
    async with session_factory() as session:
        repo = WishlistRepository(session)
        service = WishlistService(session, repo, max_items=200)

        user_id = uuid.uuid4()
        product_id = uuid.uuid4()
        req = AddToWishlistRequest(product_id=product_id)

        item = await service.add_item(user_id, req)

        assert item.id is not None
        assert item.user_id == user_id
        assert item.product_id == product_id
        assert item.created_at is not None


@pytest.mark.asyncio
async def test_add_duplicate(session_factory: async_sessionmaker[AsyncSession]) -> None:
    async with session_factory() as session:
        repo = WishlistRepository(session)
        service = WishlistService(session, repo, max_items=200)

        user_id = uuid.uuid4()
        product_id = uuid.uuid4()
        req = AddToWishlistRequest(product_id=product_id)

        await service.add_item(user_id, req)

        with pytest.raises(ItemAlreadyInWishlist):
            await service.add_item(user_id, req)


@pytest.mark.asyncio
async def test_remove_item(session_factory: async_sessionmaker[AsyncSession]) -> None:
    async with session_factory() as session:
        repo = WishlistRepository(session)
        service = WishlistService(session, repo, max_items=200)

        user_id = uuid.uuid4()
        product_id = uuid.uuid4()
        req = AddToWishlistRequest(product_id=product_id)

        await service.add_item(user_id, req)
        await service.remove_item(user_id, product_id)

        assert not await repo.exists(user_id, product_id)


@pytest.mark.asyncio
async def test_remove_nonexistent(session_factory: async_sessionmaker[AsyncSession]) -> None:
    async with session_factory() as session:
        repo = WishlistRepository(session)
        service = WishlistService(session, repo, max_items=200)

        user_id = uuid.uuid4()
        product_id = uuid.uuid4()

        with pytest.raises(ItemNotInWishlist):
            await service.remove_item(user_id, product_id)


@pytest.mark.asyncio
async def test_list_items_empty(session_factory: async_sessionmaker[AsyncSession]) -> None:
    async with session_factory() as session:
        repo = WishlistRepository(session)
        service = WishlistService(session, repo, max_items=200)

        user_id = uuid.uuid4()
        page = await service.list_items(user_id, WishlistListParams(limit=20, offset=0))

        assert page.items == []
        assert page.total == 0


@pytest.mark.asyncio
async def test_list_items_pagination(session_factory: async_sessionmaker[AsyncSession]) -> None:
    async with session_factory() as session:
        repo = WishlistRepository(session)
        service = WishlistService(session, repo, max_items=200)

        user_id = uuid.uuid4()
        for _ in range(5):
            await service.add_item(user_id, AddToWishlistRequest(product_id=uuid.uuid4()))

        page = await service.list_items(user_id, WishlistListParams(limit=2, offset=0))

        assert len(page.items) == 2
        assert page.total == 5


@pytest.mark.asyncio
async def test_list_items_order(session_factory: async_sessionmaker[AsyncSession]) -> None:
    async with session_factory() as session:
        repo = WishlistRepository(session)
        service = WishlistService(session, repo, max_items=200)

        user_id = uuid.uuid4()
        item1 = await service.add_item(user_id, AddToWishlistRequest(product_id=uuid.uuid4()))
        item2 = await service.add_item(user_id, AddToWishlistRequest(product_id=uuid.uuid4()))

        page = await service.list_items(user_id, WishlistListParams(limit=20, offset=0))

        # Items should be ordered by created_at DESC (newest first)
        assert page.items[0].id == item2.id
        assert page.items[1].id == item1.id


@pytest.mark.asyncio
async def test_check_items(session_factory: async_sessionmaker[AsyncSession]) -> None:
    async with session_factory() as session:
        repo = WishlistRepository(session)
        service = WishlistService(session, repo, max_items=200)

        user_id = uuid.uuid4()
        prod_a = uuid.uuid4()
        prod_b = uuid.uuid4()
        prod_c = uuid.uuid4()

        await service.add_item(user_id, AddToWishlistRequest(product_id=prod_a))
        await service.add_item(user_id, AddToWishlistRequest(product_id=prod_b))

        found = await service.check_items(user_id, [prod_a, prod_b, prod_c])

        assert found == {prod_a, prod_b}


@pytest.mark.asyncio
async def test_limit_reached(session_factory: async_sessionmaker[AsyncSession]) -> None:
    async with session_factory() as session:
        repo = WishlistRepository(session)
        service = WishlistService(session, repo, max_items=3)

        user_id = uuid.uuid4()
        for _ in range(3):
            await service.add_item(user_id, AddToWishlistRequest(product_id=uuid.uuid4()))

        with pytest.raises(WishlistLimitReached):
            await service.add_item(user_id, AddToWishlistRequest(product_id=uuid.uuid4()))
