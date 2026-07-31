"""Domain-level exceptions for the drops bounded context."""


class DropError(Exception):
    """Base exception for all drops domain errors."""

    code = "drop_error"
    message = "The operation could not be completed"

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.message)
        self.public_message = message or self.message


class DropNotFound(DropError):
    """Raised when a requested drop cannot be located."""

    code = "drop_not_found"
    message = "Drop not found"


class InvalidDropState(DropError):
    """Raised when an invalid state transition is requested on a drop."""

    code = "invalid_drop_state"
    message = "Invalid drop state transition"


class DropTimeConflict(DropError):
    """Raised when start or end timestamps for a drop are invalid."""

    code = "drop_time_conflict"
    message = "Drop time range is invalid"


class DuplicateDropSlug(DropError):
    """Raised when creating or updating a drop with an existing slug."""

    code = "duplicate_drop_slug"
    message = "A drop with this slug already exists"


class ProductAlreadyInDrop(DropError):
    """Raised when attempting to add a product that is already in the drop."""

    code = "product_already_in_drop"
    message = "Product is already in this drop"
