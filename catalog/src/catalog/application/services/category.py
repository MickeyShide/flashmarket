"""Category application service."""

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from catalog.application.schemas import CategoryTreeNode, CreateCategoryRequest
from catalog.domain.exceptions import CategoryNotFound, DuplicateSlug
from catalog.infrastructure.models import CategoryModel
from catalog.infrastructure.repositories.category import CategoryRepository


class CategoryService:
    """Orchestrates category business logic."""

    def __init__(
        self,
        session: AsyncSession,
        category_repo: CategoryRepository,
    ) -> None:
        self._session = session
        self._category_repo = category_repo

    async def create_category(self, data: CreateCategoryRequest) -> CategoryModel:
        """Validate inputs and persist a new category."""
        if data.parent_id is not None:
            parent = await self._category_repo.get_by_id(data.parent_id)
            if parent is None:
                raise CategoryNotFound("Parent category not found")

        if await self._category_repo.slug_exists(data.slug):
            raise DuplicateSlug("A category with this slug already exists")

        category = CategoryModel(
            name=data.name,
            slug=data.slug,
            parent_id=data.parent_id,
        )

        try:
            await self._category_repo.create(category)
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            if _is_duplicate_slug_error(exc, "categories"):
                raise DuplicateSlug("A category with this slug already exists") from exc
            raise
        await self._session.refresh(category)
        return category

    async def get_category_tree(self) -> list[CategoryTreeNode]:
        """Build the complete category hierarchy without relationship lazy-loads."""
        categories = await self._category_repo.list_all()
        nodes = {
            category.id: CategoryTreeNode(
                id=category.id,
                name=category.name,
                slug=category.slug,
            )
            for category in categories
        }
        roots: list[CategoryTreeNode] = []

        for category in categories:
            node = nodes[category.id]
            if category.parent_id is None:
                roots.append(node)
                continue

            parent = nodes.get(category.parent_id)
            if parent is None:
                roots.append(node)
                continue
            parent.children.append(node)

        return roots


def _is_duplicate_slug_error(error: IntegrityError, table_name: str) -> bool:
    """Identify a database unique-constraint failure for a slug column."""
    diagnostic = getattr(error.orig, "diag", None)
    constraint_name = getattr(diagnostic, "constraint_name", None)
    if constraint_name == f"{table_name}_slug_key":
        return True
    return f"unique constraint failed: {table_name}.slug" in str(error.orig).lower()
