"""Product application service."""

from uuid import UUID

from slugify import slugify
from sqlalchemy.ext.asyncio import AsyncSession

from catalog.application.schemas import (
    CreateProductRequest,
    ProductListParams,
    UpdateProductRequest,
)
from catalog.domain.entities import ProductStatus
from catalog.domain.exceptions import CategoryNotFound, DuplicateSlug, ProductNotFound
from catalog.infrastructure.database import utc_now
from catalog.infrastructure.models import ProductImageModel, ProductModel
from catalog.infrastructure.repositories.category import CategoryRepository
from catalog.infrastructure.repositories.product import (
    ProductPage,
    ProductRepository,
    ProductSearchQuery,
)


class ProductService:
    """Orchestrates product business logic."""

    def __init__(
        self,
        session: AsyncSession,
        product_repo: ProductRepository,
        category_repo: CategoryRepository,
    ) -> None:
        self._session = session
        self._product_repo = product_repo
        self._category_repo = category_repo

    async def generate_unique_slug(self, name: str) -> str:
        """Derive a URL-safe slug from *name*, appending a counter on collision."""
        base_slug: str = slugify(name)
        if not base_slug:
            base_slug = "product"

        if not await self._product_repo.slug_exists(base_slug):
            return base_slug

        for counter in range(2, 101):
            candidate = f"{base_slug}-{counter}"
            if not await self._product_repo.slug_exists(candidate):
                return candidate

        raise DuplicateSlug

    async def create_product(self, data: CreateProductRequest) -> ProductModel:
        """Validate inputs, generate a slug, and persist a new product."""
        category = await self._category_repo.get_by_id(data.category_id)
        if category is None:
            raise CategoryNotFound

        slug = await self.generate_unique_slug(data.name)

        now = utc_now()
        published_at = now if data.status == ProductStatus.ACTIVE else None

        product = ProductModel(
            slug=slug,
            name=data.name,
            description=data.description,
            price=data.price,
            currency=data.currency,
            status=data.status,
            category_id=data.category_id,
            cover_image=data.cover_image,
            published_at=published_at,
        )

        await self._product_repo.create(product)

        if data.images:
            image_models = [
                ProductImageModel(
                    product_id=product.id,
                    url=img.url,
                    sort_order=img.sort_order,
                )
                for img in data.images
            ]
            await self._product_repo.replace_images(product.id, image_models)

        await self._session.commit()
        await self._session.refresh(product)
        return product

    async def get_by_slug(self, slug: str) -> ProductModel:
        """Return an ACTIVE product or raise ProductNotFound."""
        product = await self._product_repo.get_by_slug(slug)
        if product is None or product.status != ProductStatus.ACTIVE:
            raise ProductNotFound
        return product

    async def get_by_id(self, product_id: UUID) -> ProductModel:
        """Return a product by id regardless of status (for internal use)."""
        product = await self._product_repo.get_by_id(product_id)
        if product is None:
            raise ProductNotFound
        return product

    async def search(self, params: ProductListParams) -> ProductPage:
        """Execute a filtered, sorted, and paginated product search."""
        query = ProductSearchQuery(
            limit=params.limit,
            offset=params.offset,
            category_id=params.category_id,
            status=params.status if params.status is not None else ProductStatus.ACTIVE,
            price_from=params.price_from,
            price_to=params.price_to,
            search=params.search,
            sort_by=params.sort_by,
            sort_order=params.sort_order,
        )
        return await self._product_repo.search(query)

    async def update_product(self, product_id: UUID, data: UpdateProductRequest) -> ProductModel:
        """Apply a partial update to an existing product."""
        product = await self._product_repo.get_by_id(product_id)
        if product is None:
            raise ProductNotFound

        if data.category_id is not None:
            category = await self._category_repo.get_by_id(data.category_id)
            if category is None:
                raise CategoryNotFound

        if data.name is not None:
            product.name = data.name
        if data.description is not None:
            product.description = data.description
        if data.price is not None:
            product.price = data.price
        if data.currency is not None:
            product.currency = data.currency
        if data.category_id is not None:
            product.category_id = data.category_id
        if data.cover_image is not None:
            product.cover_image = data.cover_image

        if data.status is not None:
            was_active = product.status == ProductStatus.ACTIVE
            product.status = data.status
            if data.status == ProductStatus.ACTIVE and not was_active:
                product.published_at = utc_now()

        if data.images is not None:
            image_models = [
                ProductImageModel(
                    product_id=product.id,
                    url=img.url,
                    sort_order=img.sort_order,
                )
                for img in data.images
            ]
            await self._product_repo.replace_images(product.id, image_models)

        await self._product_repo.update(product)
        await self._session.commit()
        await self._session.refresh(product)
        return product

    async def archive_product(self, product_id: UUID) -> ProductModel:
        """Soft-delete a product by setting its status to ARCHIVED."""
        product = await self._product_repo.get_by_id(product_id)
        if product is None:
            raise ProductNotFound

        if product.status == ProductStatus.ARCHIVED:
            raise ProductNotFound("Product is already archived")

        product.status = ProductStatus.ARCHIVED
        await self._product_repo.update(product)
        await self._session.commit()
        await self._session.refresh(product)
        return product
