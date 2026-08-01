"""Brand application service."""

from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from catalog.application.schemas import CreateBrandRequest, UpdateBrandRequest
from catalog.domain.exceptions import BrandNotFound, DuplicateSlug
from catalog.infrastructure.models import BrandModel
from catalog.infrastructure.repositories.brand import BrandRepository


class BrandService:
    """Orchestrates brand business logic."""

    def __init__(
        self,
        session: AsyncSession,
        brand_repo: BrandRepository,
    ) -> None:
        self._session = session
        self._brand_repo = brand_repo

    async def create_brand(self, data: CreateBrandRequest) -> BrandModel:
        """Validate inputs and persist a new brand."""
        if await self._brand_repo.slug_exists(data.slug):
            raise DuplicateSlug("A brand with this slug already exists")

        brand = BrandModel(
            name=data.name,
            slug=data.slug,
            description=data.description,
            logo_url=data.logo_url,
        )

        try:
            await self._brand_repo.create(brand)
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            raise DuplicateSlug("A brand with this slug already exists") from exc

        await self._session.refresh(brand)
        return brand

    async def get_by_id(self, brand_id: UUID) -> BrandModel:
        """Return a brand by its primary key."""
        brand = await self._brand_repo.get_by_id(brand_id)
        if brand is None:
            raise BrandNotFound
        return brand

    async def get_by_slug(self, slug: str) -> BrandModel:
        """Return a brand by its slug."""
        brand = await self._brand_repo.get_by_slug(slug)
        if brand is None:
            raise BrandNotFound
        return brand

    async def list_brands(self) -> list[BrandModel]:
        """Return all brands."""
        return await self._brand_repo.list_all()

    async def update_brand(self, brand_id: UUID, data: UpdateBrandRequest) -> BrandModel:
        """Apply supplied Brand fields and persist them."""
        brand = await self._brand_repo.get_by_id(brand_id)
        if brand is None:
            raise BrandNotFound
        if data.name is not None:
            brand.name = data.name.strip()
        if data.description is not None:
            brand.description = data.description
        if data.logo_url is not None:
            brand.logo_url = data.logo_url
        await self._session.commit()
        await self._session.refresh(brand)
        return brand
