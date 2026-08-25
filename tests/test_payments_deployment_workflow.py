"""Contracts for test-only YooKassa production deployment wiring."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
WORKFLOW_PATH = PROJECT_ROOT / ".github" / "workflows" / "payments-deploy.yml"
DEPLOY_COMPOSE_PATH = PROJECT_ROOT / "payments" / "docker-compose.deploy.yml"


def _workflow() -> str:
    return WORKFLOW_PATH.read_text(encoding="utf-8")


def test_payments_deploy_reads_yookassa_actions_configuration() -> None:
    workflow = _workflow()

    for binding in (
        "PAYMENTS_PAYMENT_PROVIDER: ${{ vars.PAYMENTS_PAYMENT_PROVIDER || 'mock' }}",
        "PAYMENTS_YOOKASSA_SHOP_ID: ${{ secrets.PAYMENTS_YOOKASSA_SHOP_ID }}",
        "PAYMENTS_YOOKASSA_SECRET_KEY: ${{ secrets.PAYMENTS_YOOKASSA_SECRET_KEY }}",
        "PAYMENTS_YOOKASSA_RETURN_URL: ${{ vars.PAYMENTS_YOOKASSA_RETURN_URL }}",
        "PAYMENTS_YOOKASSA_WEBHOOK_REQUIRE_HTTPS: ${{ vars.PAYMENTS_YOOKASSA_WEBHOOK_REQUIRE_HTTPS || 'true' }}",
    ):
        assert binding in workflow


def test_payments_deploy_fails_closed_for_invalid_yookassa_configuration() -> None:
    workflow = _workflow()

    for validation in (
        "PAYMENTS_PAYMENT_PROVIDER must be mock or yookassa",
        "PAYMENTS_YOOKASSA_SHOP_ID is required",
        "PAYMENTS_YOOKASSA_SECRET_KEY is required",
        "PAYMENTS_YOOKASSA_RETURN_URL is required",
        "PAYMENTS_YOOKASSA_SHOP_ID must contain only digits",
        'expected_return_url="https://${GATEWAY_DOMAIN}/payment/return"',
        "PAYMENTS_YOOKASSA_WEBHOOK_REQUIRE_HTTPS must be true",
    ):
        assert validation in workflow


def test_payments_deploy_renders_test_only_yookassa_environment() -> None:
    workflow = _workflow()

    for setting in (
        "PAYMENTS_PAYMENT_PROVIDER=%s",
        "PAYMENTS_YOOKASSA_SHOP_ID=%s",
        "PAYMENTS_YOOKASSA_SECRET_KEY=%s",
        "PAYMENTS_YOOKASSA_RETURN_URL=%s",
        "PAYMENTS_YOOKASSA_TEST_MODE_REQUIRED=true",
        "PAYMENTS_YOOKASSA_WEBHOOK_REQUIRE_HTTPS=%s",
    ):
        assert setting in workflow

    compose = DEPLOY_COMPOSE_PATH.read_text(encoding="utf-8")
    assert "PAYMENTS_YOOKASSA_TEST_MODE_REQUIRED: 'true'" in compose
    assert (
        "PAYMENTS_YOOKASSA_WEBHOOK_REQUIRE_HTTPS: "
        "${PAYMENTS_YOOKASSA_WEBHOOK_REQUIRE_HTTPS:-true}"
    ) in compose
