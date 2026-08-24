"""Payment provider construction."""

from payments.application.contracts import PaymentProvider
from payments.config import Settings, get_settings
from payments.infrastructure.providers.mock import MockPaymentProvider
from payments.infrastructure.providers.yookassa import YooKassaPaymentProvider


def build_payment_provider(settings: Settings | None = None) -> PaymentProvider:
    """Build the provider selected by application settings."""
    current = settings or get_settings()
    if current.payment_provider == "mock":
        return MockPaymentProvider()

    assert current.yookassa_shop_id is not None
    assert current.yookassa_secret_key is not None
    assert current.yookassa_return_url is not None
    return YooKassaPaymentProvider(
        shop_id=current.yookassa_shop_id,
        secret_key=current.yookassa_secret_key.get_secret_value(),
        api_url=current.yookassa_api_url,
        connect_timeout=current.yookassa_connect_timeout_seconds,
        read_timeout=current.yookassa_read_timeout_seconds,
    )
