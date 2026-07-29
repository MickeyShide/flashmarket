"""Domain-level exceptions for the payments bounded context."""


class PaymentError(Exception):
    """Base exception for all payments domain errors."""

    code = "payment_error"
    message = "The operation could not be completed"

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.message)
        self.public_message = message or self.message


class PaymentNotFound(PaymentError):
    """Raised when a payment cannot be located."""

    code = "payment_not_found"
    message = "Payment not found"


class InvalidPaymentState(PaymentError):
    """Raised when a payment transition is not allowed."""

    code = "invalid_payment_state"
    message = "Invalid payment state"
