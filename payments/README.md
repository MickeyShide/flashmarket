# FlashMarket Payments Service

Manages payment attempts and publishes saga events.

## Payment states

- `PENDING`
- `SUCCESS`
- `FAILED`
- `CANCELLED`

## API

- `POST /api/v1/payments` — create a payment for an order
- `GET /api/v1/payments/{payment_id}` — get payment
- `GET /api/v1/payments/users/{user_id}` — list user payments
- `POST /api/v1/payments/{payment_id}/confirm` — mark payment succeeded
- `POST /api/v1/payments/{payment_id}/fail` — mark payment failed
- `POST /api/v1/payments/{payment_id}/cancel` — cancel payment
- `POST /api/v1/payments/orders/{order_id}/checkout` — start or resume hosted checkout
- `GET /api/v1/payments/orders/{order_id}` — get the authoritative order payment
- `POST /api/v1/payments/webhooks/yookassa` — receive and verify YooKassa notifications
- `GET /health/ready` — readiness probe

## Events

Published via transactional outbox:

- `PaymentSucceeded`
- `PaymentFailed`
- `PaymentCancelled`

## Run locally

```bash
cd payments
docker compose up --build
```

## Run tests

```bash
cd payments
uv sync --all-groups
uv run pytest
```

## YooKassa test mode

Real payments are deliberately disabled. Create a YooKassa test shop, then set:

```dotenv
PAYMENTS_PAYMENT_PROVIDER=yookassa
PAYMENTS_YOOKASSA_SHOP_ID=your-test-shop-id
PAYMENTS_YOOKASSA_SECRET_KEY=your-test-secret
PAYMENTS_YOOKASSA_RETURN_URL=https://your-public-host/payment/return
PAYMENTS_YOOKASSA_TEST_MODE_REQUIRED=true
```

Configure the public HTTPS callback
`https://your-public-host/api/v1/payments/webhooks/yookassa` for
`payment.succeeded`, `payment.canceled`, and `refund.succeeded`. Never commit the
shop secret. The service rejects provider objects where YooKassa returns
`test=false`.
