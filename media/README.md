# FlashMarket Media Service

Backend-only service for public avatars, product images, brand logos, review images,
drop images, and other public assets. It stores metadata in PostgreSQL and gives clients
short-lived presigned POST forms for the existing S3-compatible MinIO deployment.

The service deliberately does **not** create or run MinIO, create buckets, change bucket
policies, or own S3 volumes. Its containers join the external `shide-observability`
network. The configured bucket and its public-read/no-list/CORS policy are infrastructure
prerequisites.

## Upload flow

1. `POST /api/v1/media/uploads` with a JWT and declared metadata.
2. Submit the returned form directly to `upload.url`.
3. `POST /api/v1/media/assets/{id}/complete`.
4. Store the returned `public_url` in Catalog/Auth/Reviews as appropriate.

Supported v1 content is JPEG, PNG, WebP, GIF, and PDF. Purpose policies control roles,
bindings, and maximum sizes. Unsafe or mismatched bytes are rejected during completion.

## Development

```bash
uv sync
uv run alembic upgrade head
uv run uvicorn media_service.main:app --reload
```

The PostgreSQL database, `shide-observability` network, `shide-minio` endpoint, bucket,
credentials, public endpoint, and bucket CORS/policy must already exist.

## Quality gates

```bash
uv run ruff check src tests
uv run ruff format --check src tests
uv run mypy
uv run pytest
docker compose config --quiet
```
