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


class PaymentNotReady(PaymentError):
    """Raised while the order payment event has not been consumed yet."""

    code = "payment_not_ready"
    message = "Payment is still being prepared"


class PaymentProviderUnavailable(PaymentError):
    """Raised when a provider result is temporarily unknown."""

    code = "payment_provider_unavailable"
    message = "Payment provider is temporarily unavailable"


class PaymentProviderRejected(PaymentError):
    """Raised when the provider rejects a request."""

    code = "payment_provider_rejected"
    message = "Payment provider rejected the operation"


class PaymentVerificationFailed(PaymentError):
    """Raised when provider data does not match the local payment."""

    code = "payment_verification_failed"
    message = "Payment verification failed"
