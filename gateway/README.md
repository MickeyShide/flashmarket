# FlashMarket API Gateway

Nginx reverse proxy that routes public traffic to backend services.

## Routes

| Path                         | Service       |
| ---------------------------- | ------------- |
| `/api/v1/auth/*`             | auth          |
| `/api/v1/users/*`            | auth          |
| `/api/v1/sessions/*`         | auth          |
| `/api/v1/admin/*`            | auth          |
| `/api/v1/products/*`         | catalog       |
| `/api/v1/categories/*`       | catalog       |
| `/api/v1/internal/*`         | catalog       |
| `/api/v1/stocks/*`           | inventory     |
| `/api/v1/orders/*`           | orders        |
| `/api/v1/payments/*`         | payments      |
| `/api/v1/notifications/*`    | notifications |
| `/api/v1/wishlist/*`         | wishlist      |
| `/api/v1/drops/*`            | drops         |
| `/api/v1/admin/drops/*`      | drops         |
| `/api/v1/media/*`            | media         |
| `/*`                         | frontend      |

## Rate limiting

Nginx applies per-IP limits to public APIs on both the main domain and service
subdomains. Requests through both entry points share the same quota for their
profile.

| Profile | Services and routes | Rate | Burst |
| --- | --- | ---: | ---: |
| `auth` | Auth, users, sessions, identity administration | 5 req/s | 10 |
| `transaction` | Orders, payments, promocodes, wishlist, media | 10 req/s | 20 |
| `catalog` | Products, categories, brands, drops | 50 req/s | 100 |
| `general` | Inventory, notifications | 20 req/s | 40 |

Bursts use `nodelay`: requests inside the burst are forwarded immediately.
Requests beyond it receive HTTP 429 with a JSON error and `Retry-After: 1`.

Frontend assets and `/health`, `/health/*`, `/metrics`, `/prometheus/*`, and
`/nginx_status` are excluded. The counters live in Nginx shared memory and are
therefore local to the current single gateway instance. With multiple gateway
replicas, a distributed limiting design is required to preserve global quotas.

Rates and bursts are explicit in `nginx.conf`; change them through a reviewed
configuration update and restart the gateway.

## Run

```bash
cd gateway
docker compose up -d
```

All services must be attached to the external `shide-observability` Docker network.
