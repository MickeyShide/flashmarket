# FlashMarket Orders Service

Manages the order lifecycle and publishes saga events.

## Order states

- `PENDING`
- `AWAITING_PAYMENT`
- `PAID`
- `CONFIRMED`
- `PAYMENT_FAILED`
- `CANCELLED`

## API

- `POST /api/v1/orders` — create an order from a reservation
- `GET /api/v1/orders/{order_id}` — get order
- `GET /api/v1/orders?user_id=...` — list user orders
- `POST /api/v1/orders/{order_id}/confirm?payment_id=...` — confirm payment
- `POST /api/v1/orders/{order_id}/fail?payment_id=...` — fail payment
- `GET /health/ready` — readiness probe

Order creation accepts an optional normalized `receipt_email`. When present, the
immutable `PaymentRequested.receipt_snapshot` carries it as the fiscal receipt
contact. Batch requests must use one contact for every order line.

## Events

Published via transactional outbox:

- `OrderCreated`
- `PaymentRequested`
- `OrderConfirmed`
- `OrderCancelled`

## Run locally

```bash
cd orders
docker compose up --build
```

## Run tests

```bash
cd orders
uv sync --all-groups
uv run pytest
```
