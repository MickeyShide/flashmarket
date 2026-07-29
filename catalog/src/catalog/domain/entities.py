"""Domain value objects and enumerations."""

from enum import StrEnum


class ProductStatus(StrEnum):
    """Lifecycle status of a product in the catalog."""

    ACTIVE = "ACTIVE"
    HIDDEN = "HIDDEN"
    ARCHIVED = "ARCHIVED"


class Currency(StrEnum):
    """Supported currency codes."""

    RUB = "RUB"
    USD = "USD"
    EUR = "EUR"
