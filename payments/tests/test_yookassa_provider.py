"""Pure conversion tests for the YooKassa adapter."""

import pytest

from payments.domain.exceptions import PaymentProviderRejected
from payments.infrastructure.providers.yookassa import kopecks_to_value, value_to_kopecks


def test_money_conversion_uses_exact_decimal_values() -> None:
    assert kopecks_to_value(1) == "0.01"
    assert kopecks_to_value(12_990) == "129.90"
    assert value_to_kopecks("129.90") == 12_990


def test_provider_amount_rejects_fractional_kopecks() -> None:
    with pytest.raises(PaymentProviderRejected):
        value_to_kopecks("1.001")
