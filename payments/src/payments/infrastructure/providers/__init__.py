"""Payment provider construction."""

from functools import lru_cache

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
        max_connections=current.yookassa_http_max_connections,
        max_keepalive_connections=current.yookassa_http_max_keepalive_connections,
        keepalive_expiry=current.yookassa_http_keepalive_expiry_seconds,
        read_concurrency=current.yookassa_read_concurrency,
        write_concurrency=current.yookassa_write_concurrency,
        max_attempts=current.yookassa_interactive_max_attempts,
        retry_base_seconds=current.yookassa_retry_base_seconds,
        retry_max_seconds=current.yookassa_retry_max_seconds,
        circuit_failure_threshold=current.yookassa_circuit_failure_threshold,
        circuit_recovery_seconds=current.yookassa_circuit_recovery_seconds,
    )


@lru_cache
def get_shared_payment_provider() -> PaymentProvider:
    """Return the single provider instance and HTTP pool for this process."""
    return build_payment_provider()


async def close_shared_payment_provider() -> None:
    """Close provider resources during process shutdown."""
    if get_shared_payment_provider.cache_info().currsize == 0:
        return
    provider = get_shared_payment_provider()
    close = getattr(provider, "aclose", None)
    if close is not None:
        await close()
    get_shared_payment_provider.cache_clear()
