"""Domain-level exceptions for the inventory bounded context."""


class InventoryError(Exception):
    """Base exception for all inventory domain errors."""

    code = "inventory_error"
    message = "The operation could not be completed"

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.message)
        self.public_message = message or self.message


class StockNotFound(InventoryError):
    """Raised when a product stock record cannot be located."""

    code = "stock_not_found"
    message = "Stock not found"


class OutOfStock(InventoryError):
    """Raised when no units are available for reservation."""

    code = "out_of_stock"
    message = "Product is sold out"


class ReservationNotFound(InventoryError):
    """Raised when a reservation cannot be located."""

    code = "reservation_not_found"
    message = "Reservation not found"


class InvalidReservationState(InventoryError):
    """Raised when a reservation transition is not allowed."""

    code = "invalid_reservation_state"
    message = "Invalid reservation state"


class StockInvariantViolation(InventoryError):
    """Raised when database invariants are violated."""

    code = "stock_invariant_violation"
    message = "Stock invariant violation"


class DropPurchaseDenied(InventoryError):
    code = "drop_purchase_denied"
    message = "Drop purchase is not allowed"


class DropServiceUnavailable(InventoryError):
    code = "drop_service_unavailable"
    message = "Drop rules are temporarily unavailable"
