# FlashMarket Media Service

Backend-only service for public avatars, product images, brand logos, review images,
drop images, and other public assets. It stores metadata in PostgreSQL and gives clients
short-lived presigned POST forms for the existing S3-compatible MinIO deployment.

The service deliberately does **not** create or run MinIO, change production bucket
policies, or own S3 volumes. Its containers join the external `shide-observability`
network. The configured production bucket and its public-read/no-list/CORS policy are
infrastructure prerequisites.

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

The PostgreSQL database, `shide-observability` network, `shide-minio` endpoint, and
credentials must already exist.

The root `make up` command creates the local bucket, enables anonymous reads, and
publishes the shared MinIO API through the FlashMarket gateway on
`http://localhost:9000`. That listener supplies an explicit CORS allowlist for both
`localhost` and `127.0.0.1` development origins without changing the global policy of
the shared MinIO cluster.

## Production storage CORS

Direct browser uploads require CORS on the browser-visible object-storage endpoint in
addition to `MEDIA_CORS_ORIGINS` on the Media API. For S3-compatible providers that
support bucket CORS, copy `media/cors/production.example.xml`, replace the example
origins with every HTTPS storefront/admin origin, and apply it with the provider's
administration tool.

MinIO Community does not implement per-bucket `PutBucketCors`. Configure its global API
CORS allowlist with every origin used by every application sharing the cluster, then
restart MinIO during an approved maintenance window:

```bash
mc admin config set <alias> api cors_allow_origin="https://shop.example.com,https://admin.example.com"
mc admin service restart <alias>
```

The default FlashMarket deployment avoids cross-origin storage entirely. Its public
endpoint is `https://<gateway-domain>/media-storage`, which the gateway streams directly
to MinIO after removing the prefix. Configure both `MEDIA_S3_PUBLIC_ENDPOINT` and
`MEDIA_PUBLIC_BASE_URL` with this HTTPS route as shown in `.env.deploy.example`.

`MEDIA_S3_PUBLIC_ENDPOINT` must be reachable by browsers, while
`MEDIA_S3_INTERNAL_ENDPOINT` remains the private endpoint used for validation and
cleanup. Do not use the internal Docker hostname in a browser-visible signed URL.

## Quality gates

```bash
uv run ruff check src tests
uv run ruff format --check src tests
uv run mypy
uv run pytest
docker compose config --quiet
```
