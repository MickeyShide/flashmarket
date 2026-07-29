# FlashMarket Frontend

Static single-page demo served by Nginx.

## Run locally

```bash
cd frontend
docker compose up --build
```

The frontend is available at http://localhost:3000 and proxies `/api/*` calls to the gateway.
