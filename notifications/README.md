# FlashMarket Notifications Service

Persists notifications and publishes delivery events.

## Notification states

- `PENDING`
- `SENT`
- `FAILED`

## API

- `POST /api/v1/notifications` — create a notification
- `GET /api/v1/notifications/{notification_id}` — get notification
- `GET /api/v1/notifications/users/{user_id}` — list user notifications
- `POST /api/v1/notifications/{notification_id}/send` — mark notification as sent
- `POST /api/v1/notifications/{notification_id}/fail?reason=...` — mark notification as failed
- `GET /health/ready` — readiness probe

## Events

Published via transactional outbox:

- `NotificationSent`

## Run locally

```bash
cd notifications
docker compose up --build
```

## Run tests

```bash
cd notifications
uv sync --all-groups
uv run pytest
```
