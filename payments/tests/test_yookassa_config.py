"""Safety checks for the test-only YooKassa configuration."""

import pytest
from pydantic import ValidationError

from payments.config import Settings


def test_yookassa_requires_complete_credentials() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, payment_provider="yookassa")


def test_yookassa_accepts_complete_test_configuration() -> None:
    settings = Settings(
        _env_file=None,
        payment_provider="yookassa",
        yookassa_shop_id="test-shop",
        yookassa_secret_key="test-secret",
        yookassa_return_url="https://shop.test/payment/return",
    )
    assert settings.payment_provider == "yookassa"
    assert settings.yookassa_test_mode_required is True


def test_real_yookassa_mode_cannot_be_enabled() -> None:
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            payment_provider="yookassa",
            yookassa_shop_id="shop",
            yookassa_secret_key="secret",
            yookassa_return_url="https://shop.test/payment/return",
            yookassa_test_mode_required=False,
        )
