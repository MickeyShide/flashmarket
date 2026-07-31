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


class PromocodeError(Exception):
    """Base exception for all promocode domain errors."""

    code = "promocode_error"
    message = "Promocode operation failed"

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.message)
        self.public_message = message or self.message


class PromocodeNotFound(PromocodeError):
    """Raised when a promocode cannot be located."""

    code = "promocode_not_found"
    message = "Promocode not found"


class PromocodeExpired(PromocodeError):
    """Raised when a promocode is expired."""

    code = "promocode_expired"
    message = "Promocode has expired"


class PromocodeDisabled(PromocodeError):
    """Raised when a promocode is disabled."""

    code = "promocode_disabled"
    message = "Promocode is disabled"


class PromocodeLimitReached(PromocodeError):
    """Raised when a promocode's max usage limit is reached."""

    code = "promocode_limit_reached"
    message = "Promocode usage limit reached"


class PromocodeAlreadyUsed(PromocodeError):
    """Raised when a user has exceeded max uses for a promocode."""

    code = "promocode_already_used"
    message = "You have already used this promocode"


class PromocodeMinAmountNotMet(PromocodeError):
    """Raised when order amount is less than min_order_amount."""

    code = "promocode_min_amount"
    message = "Order amount is below minimum for this promocode"


class DuplicatePromocodeCode(PromocodeError):
    """Raised when creating a promocode with an existing code."""

    code = "duplicate_promocode_code"
    message = "A promocode with this code already exists"

