"""Domain-level exceptions for the catalog bounded context."""


class CatalogError(Exception):
    """Base exception for all catalog domain errors."""

    code = "catalog_error"
    message = "The operation could not be completed"

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.message)
        self.public_message = message or self.message


class ProductNotFound(CatalogError):
    """Raised when a product cannot be located or is not visible."""

    code = "product_not_found"
    message = "Product not found"


class CategoryNotFound(CatalogError):
    """Raised when a category cannot be located."""

    code = "category_not_found"
    message = "Category not found"


class DuplicateSlug(CatalogError):
    """Raised when a slug collision cannot be resolved."""

    code = "duplicate_slug"
    message = "A product with this slug already exists"


class InvalidProductData(CatalogError):
    """Raised when business-rule validation fails."""

    code = "invalid_product_data"
    message = "Product data validation failed"
