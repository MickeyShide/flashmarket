"""Product persistence operations."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import ColumnElement, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy.orm.strategy_options import _AbstractLoad

from catalog.domain.entities import ProductStatus
from catalog.infrastructure.models import ProductImageModel, ProductModel
from catalog.infrastructure.search import (
    product_search_condition,
    product_search_rank,
    product_similarity_condition,
    product_similarity_rank,
    tokenize_search_phrase,
)


@dataclass(frozen=True, slots=True)
class ProductSearchQuery:
    """Encapsulates search, filter, sort, and pagination parameters."""

    limit: int
    offset: int
    category_id: UUID | None = None
    brand_id: UUID | None = None
    brand_slug: str | None = None
    status: ProductStatus | None = None
    price_from: Decimal | None = None
    price_to: Decimal | None = None
    search: str | None = None
    sort_by: str = "created_at"
    sort_order: str = "desc"


@dataclass(frozen=True, slots=True)
class ProductPage:
    """A page of product results with total count."""

    items: list[ProductModel]
    total: int


_SORT_COLUMNS = {
    "price": ProductModel.price,
    "name": ProductModel.name,
    "created_at": ProductModel.created_at,
}


class ProductRepository:
    """Data-access layer for products and their images."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _eager_options(self) -> list[_AbstractLoad]:
        """Return standard eager-load options to avoid N+1."""
        return [
            selectinload(ProductModel.images),
            joinedload(ProductModel.category),
            joinedload(ProductModel.brand),
        ]

    def _is_postgresql(self) -> bool:
        """Detect whether the bound engine is PostgreSQL.

        Full-text search (``tsvector``/``tsquery``) and ``pg_trgm`` are
        PostgreSQL-only; other dialects (SQLite in tests) fall back to
        ``ILIKE`` substring matching.
        """
        bind = self._session.get_bind()
        return bind.dialect.name == "postgresql"

    async def create(self, product: ProductModel) -> ProductModel:
        """Persist a new product."""
        self._session.add(product)
        await self._session.flush()
        return product

    async def get_by_id(self, product_id: UUID) -> ProductModel | None:
        """Fetch a product by primary key with images and category."""
        result = await self._session.scalars(
            select(ProductModel)
            .where(ProductModel.id == product_id)
            .options(*self._eager_options())
        )
        return result.first()

    async def get_by_slug(self, slug: str) -> ProductModel | None:
        """Fetch a product by its unique slug with images and category."""
        result = await self._session.scalars(
            select(ProductModel).where(ProductModel.slug == slug).options(*self._eager_options())
        )
        return result.first()

    async def slug_exists(self, slug: str) -> bool:
        """Check whether a product slug is already taken."""
        result = await self._session.scalar(
            select(func.count()).select_from(ProductModel).where(ProductModel.slug == slug)
        )
        return (result or 0) > 0

    async def search(self, query: ProductSearchQuery) -> ProductPage:
        """Execute a filtered, sorted, and paginated product search."""
        filters: list[ColumnElement[bool]] = []
        rank: ColumnElement[float] | None = None

        if query.category_id is not None:
            filters.append(ProductModel.category_id == query.category_id)
        if query.brand_id is not None:
            filters.append(ProductModel.brand_id == query.brand_id)
        if query.status is not None:
            filters.append(ProductModel.status == query.status)
        if query.price_from is not None:
            filters.append(ProductModel.price >= query.price_from)
        if query.price_to is not None:
            filters.append(ProductModel.price <= query.price_to)
        if query.search:
            tokens = tokenize_search_phrase(query.search)
            if tokens and self._is_postgresql():
                fts_condition = product_search_condition(
                    ProductModel.name, ProductModel.description, tokens
                )
                trgm_condition = product_similarity_condition(ProductModel.name, query.search)
                filters.append(or_(fts_condition, trgm_condition))
                rank = product_search_rank(
                    ProductModel.name, ProductModel.description, tokens
                ) + product_similarity_rank(ProductModel.name, query.search)
            else:
                pattern = f"%{query.search}%"
                filters.append(
                    or_(
                        ProductModel.name.ilike(pattern),
                        ProductModel.description.ilike(pattern),
                    )
                )

        wants_relevance = query.sort_by in ("relevance", "created_at") and (
            query.sort_by == "relevance" or query.sort_order == "desc"
        )
        order: ColumnElement[Any]
        if rank is not None and wants_relevance:
            order = rank.desc()
        else:
            sort_column = _SORT_COLUMNS.get(query.sort_by, ProductModel.created_at)
            order = sort_column.asc() if query.sort_order == "asc" else sort_column.desc()

        items_result = await self._session.scalars(
            select(ProductModel)
            .where(*filters)
            .options(*self._eager_options())
            .order_by(order)
            .limit(query.limit)
            .offset(query.offset)
        )
        items = list(items_result.unique().all())

        total = await self._session.scalar(
            select(func.count()).select_from(ProductModel).where(*filters)
        )

        return ProductPage(items=items, total=total or 0)

    async def update(self, product: ProductModel) -> ProductModel:
        """Flush pending attribute changes on a product."""
        await self._session.flush()
        return product

    async def replace_images(self, product_id: UUID, images: list[ProductImageModel]) -> None:
        """Delete existing images for a product and insert replacements."""
        await self._session.execute(
            delete(ProductImageModel).where(ProductImageModel.product_id == product_id)
        )
        if images:
            self._session.add_all(images)
        await self._session.flush()
