# FlashMarket Inventory Service

Manages stock levels, flash-sale reservations, and transactional outbox events.

## Domain guarantees

- `available >= 0`
- `reserved + sold <= total`
- No overselling under concurrent load (pessimistic row locking)
- Reservations expire automatically after `INVENTORY_RESERVATION_TTL_SECONDS`

## API

- `POST /api/v1/stocks` — create/reset stock
- `GET /api/v1/stocks/{product_id}` — read stock
- `PATCH /api/v1/stocks/{product_id}` — update total stock
- `POST /api/v1/stocks/{product_id}/reserve` — reserve stock
- `POST /api/v1/stocks/{product_id}/commit` — convert reservation to sale
- `POST /api/v1/stocks/{product_id}/release` — release reservation
- `POST /internal/expire` — expire stale reservations (worker endpoint)
- `GET /health/ready` — readiness probe

## Events

The service writes the following events to the outbox table:

- `InventoryReserved`
- `InventoryCommitted`
- `ReservationReleased`

## Run locally

```bash
cd inventory
docker compose up --build
```

## Run tests

```bash
cd inventory
uv sync --all-groups
uv run pytest
```
