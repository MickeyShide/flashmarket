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
