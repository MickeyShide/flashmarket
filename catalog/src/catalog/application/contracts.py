"""Application-facing interfaces for optional infrastructure."""

from typing import Protocol

from catalog.application.schemas import CategoryTreeNode


class CategoryTreeCache(Protocol):
    """Optional cache used to accelerate reads of the category hierarchy."""

    async def get_tree(self) -> list[CategoryTreeNode] | None:
        """Return the cached tree, or ``None`` when it is unavailable."""
        ...

    async def store_tree(self, tree: list[CategoryTreeNode]) -> None:
        """Store a category tree for the configured lifetime."""
        ...

    async def invalidate_tree(self) -> None:
        """Remove the cached category tree after a successful mutation."""
        ...
