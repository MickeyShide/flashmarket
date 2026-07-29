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
| `/*`                         | frontend      |

## Run

```bash
cd gateway
docker compose up -d
```

All services must be attached to the `flashmarket` Docker network.
