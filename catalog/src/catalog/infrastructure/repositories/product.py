"""Product persistence operations."""

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from sqlalchemy import ColumnElement, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy.orm.strategy_options import _AbstractLoad

from catalog.domain.entities import ProductStatus
from catalog.infrastructure.models import ProductImageModel, ProductModel


@dataclass(frozen=True, slots=True)
class ProductSearchQuery:
    """Encapsulates search, filter, sort, and pagination parameters."""

    limit: int
    offset: int
    category_id: UUID | None = None
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
        ]

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

        if query.category_id is not None:
            filters.append(ProductModel.category_id == query.category_id)
        if query.status is not None:
            filters.append(ProductModel.status == query.status)
        if query.price_from is not None:
            filters.append(ProductModel.price >= query.price_from)
        if query.price_to is not None:
            filters.append(ProductModel.price <= query.price_to)
        if query.search:
            pattern = f"%{query.search}%"
            filters.append(
                or_(
                    ProductModel.name.ilike(pattern),
                    ProductModel.description.ilike(pattern),
                )
            )

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
