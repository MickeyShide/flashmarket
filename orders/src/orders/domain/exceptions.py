"""Domain-level exceptions for the orders bounded context."""


class OrderError(Exception):
    """Base exception for all orders domain errors."""

    code = "order_error"
    message = "The operation could not be completed"

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.message)
        self.public_message = message or self.message


class OrderNotFound(OrderError):
    """Raised when an order cannot be located."""

    code = "order_not_found"
    message = "Order not found"


class InvalidOrderState(OrderError):
    """Raised when an order transition is not allowed."""

    code = "invalid_order_state"
    message = "Invalid order state"


class DuplicateOrder(OrderError):
    """Raised when an order already exists for a reservation."""

    code = "duplicate_order"
    message = "Order already exists for this reservation"
