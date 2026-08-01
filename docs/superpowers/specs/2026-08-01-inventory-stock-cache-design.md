# Inventory Stock Cache Design

## Summary

Add a fail-open Redis cache for current Inventory stock snapshots. PostgreSQL remains the source of truth for every mutation and availability decision. The cache accelerates `GET /api/v1/stocks/{product_id}` without weakening row-locking or overselling guarantees.

The cache uses revision-aware writes so a delayed operation cannot overwrite a newer stock snapshot during concurrent reservations.

## Goals

- Reduce PostgreSQL reads for frequently requested product and variant stock.
- Preserve the existing Inventory API response and mutation semantics.
- Keep reservation, commit, release, and expiration correctness entirely in PostgreSQL.
- Prevent stale concurrent cache writes from replacing newer values.
- Treat Redis as optional: Redis failure must not fail Inventory requests or completed mutations.
- Expose cache behavior through structured logs and Prometheus metrics.

## Non-goals

- Redis will not participate in stock reservation or distributed locking.
- The cache will not provide stronger consistency than PostgreSQL.
- This change will not add bulk stock endpoints, WebSockets, or stock event broadcasting.
- This change will not alter Catalog, Orders, or frontend behavior.
- Negative caching for unknown stock records is excluded to avoid delaying visibility after creation.

## Data Model

Add a non-null integer `revision` column to `stocks`:

- existing rows start at `1`;
- newly created rows start at `1`;
- every successful stock counter mutation increments the revision once;
- revisions are monotonic per stock row because every update acquires the stock row lock before incrementing it.

The public `StockResponse` remains unchanged. `revision` is an internal consistency value used only by Inventory persistence and cache code.

An Alembic migration adds the column with a server default suitable for existing rows. The ORM also defines an application default.

## Cache Representation

Each product and variant combination has an independent key:

```text
inventory:stock:{product_id}:{variant_id-or-default}:v1
```

The Redis value is a hash with two fields:

- `revision`: decimal integer used for atomic ordering;
- `payload`: JSON representation of the existing `StockResponse` fields.

The payload is validated with Pydantic before being returned. Malformed values are treated as misses and deleted on a best-effort basis.

The default TTL is 30 seconds and is configurable with `INVENTORY_STOCK_CACHE_TTL_SECONDS`. Redis connect and command timeouts are independently configurable and remain short so cache failure cannot dominate request latency.

## Architecture

### `RedisStockCache`

A focused infrastructure adapter owns key construction, serialization, validation, Redis error handling, and revision-aware writes. Its interface exposes:

- `get_stock(product_id, variant_id) -> StockResponse | None`;
- `store_stock(stock, revision) -> StoreResult`;
- `close() -> None` through the underlying shared client lifecycle.

The application service depends on the adapter through a small protocol so unit tests can use mocks without Redis.

### Dependency wiring

The Inventory service dependency receives the shared stock cache instance. The FastAPI lifespan closes the Redis client after serving stops, alongside the SQLAlchemy engine.

Any direct `InventoryService` construction in tests receives an explicit mock or no-op adapter. Cache behavior is not hidden behind an optional untyped argument.

## Read Flow

For `get_stock(product_id, variant_id)`:

1. Read and validate the Redis snapshot.
2. On a hit, return the cached `StockResponse` without querying PostgreSQL.
3. On a miss, malformed value, timeout, or Redis error, query PostgreSQL.
4. If the row does not exist, raise the existing `StockNotFound` error without caching it.
5. Convert the row to `StockResponse`, attempt a revision-aware cache write, and return the response.

The application service returns `StockResponse` for the read path. Routes continue emitting the same JSON contract. Mutation methods may continue returning ORM models where their existing route contract expects them.

## Mutation Flow

All writes preserve the current transaction order:

1. Lock the PostgreSQL stock row for every update. Existing-stock reset and reservation expiration are changed to use the locking repository methods as part of this feature.
2. Apply and validate the mutation.
3. Increment `stock.revision` once.
4. Flush outbox and domain changes in the same transaction where applicable.
5. Commit PostgreSQL.
6. Refresh the stock row when required.
7. Attempt to store the committed snapshot in Redis.
8. Return success regardless of the Redis outcome.

This applies to:

- create or reset stock;
- update total stock;
- reserve stock;
- commit a reservation;
- release a reservation;
- expire reservations.

When one expiration batch updates the same stock more than once, the service writes only its final in-memory snapshot after the transaction commits.

## Concurrent Write Protection

A Redis Lua script performs the write atomically:

1. Read the current cached revision.
2. If no value exists or the candidate revision is greater than or equal to the cached revision, write both hash fields and refresh the TTL.
3. If the candidate revision is lower, leave the cached value and TTL unchanged and report a stale write.

This protects both post-mutation writes and delayed cache-aside population. A database read that began before a concurrent mutation cannot overwrite the later revision after that mutation has populated Redis.

Equal revisions are allowed so a read can repair a malformed or partially missing payload for the same committed state.

## Failure Handling

- Redis connection, timeout, command, and script failures are logged and treated as cache misses or ignored writes.
- A malformed payload is logged, counted, deleted best-effort, and followed by a PostgreSQL fallback.
- PostgreSQL errors retain existing behavior and are never masked by the cache.
- Cache writes occur only after a successful commit. A rolled-back mutation never publishes an uncommitted snapshot.
- Production settings validate Redis TLS unless explicitly allowing an internal trusted service, following the existing Catalog cache policy.

## Configuration and Deployment

Inventory adds:

- the async `redis` package dependency;
- `INVENTORY_REDIS_URL`, defaulting to the shared Redis service on a dedicated logical database;
- `INVENTORY_STOCK_CACHE_TTL_SECONDS`, default `30`;
- `INVENTORY_REDIS_SOCKET_TIMEOUT_SECONDS`, default `0.2`.

Development and deployment Compose files pass the Redis URL to every Inventory process that constructs the application service. Environment examples document all settings. No new container is required because FlashMarket already runs Redis.

## Observability

Add `inventory_stock_cache_operations_total{operation,result}` with bounded labels:

- `read`: `hit`, `miss`, `error`;
- `write`: `success`, `stale`, `error`;
- `invalidate`: `success`, `error` only when deleting malformed data.

Warnings include the operation but never cached payload contents. Normal hits and misses do not emit per-request logs.

## Testing

Unit tests cover:

- product-level and variant-level key isolation;
- serialization round trip and TTL;
- hit behavior skipping the repository;
- miss behavior querying PostgreSQL and populating Redis;
- no negative caching for `StockNotFound`;
- malformed payload deletion and database fallback;
- fail-open reads and writes when Redis raises errors;
- rejection of a lower-revision write;
- acceptance of equal and higher revisions;
- cache update only after a successful database commit;
- cache updates for create, reset, total update, reserve, commit, release, and expiration;
- final-snapshot behavior when an expiration batch touches one stock multiple times;
- product and variant responses remaining unchanged;
- configuration validation and Redis client shutdown in application lifespan.

Existing Inventory API, integration, and PostgreSQL concurrency tests remain part of regression verification. Static checks include Ruff and strict mypy for Inventory.

## Acceptance Criteria

- Repeated stock reads use Redis after the first successful database read.
- Variant and non-variant stock never share cache entries.
- Every successful counter mutation increments the database revision and attempts a post-commit cache update.
- A lower-revision snapshot cannot replace a higher-revision cached snapshot.
- Redis unavailability does not change successful API responses or mutation correctness.
- Reservation decisions continue to use locked PostgreSQL rows and cannot oversell.
- The public Inventory OpenAPI response schema does not expose `revision` or otherwise change.
- Cache metrics and lifecycle cleanup are present and tested.
