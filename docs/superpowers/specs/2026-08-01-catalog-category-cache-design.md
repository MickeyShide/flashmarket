# Catalog Category Cache Design

## Goal

Add Redis-backed caching for the Catalog category tree so repeated
`GET /api/v1/categories` requests avoid rebuilding an infrequently changing
hierarchy from PostgreSQL. Redis remains an optional accelerator: Catalog must
continue serving correct API responses from PostgreSQL when Redis is
unavailable.

## Scope

This change caches only the complete category tree returned by
`GET /api/v1/categories`. It does not cache individual categories, brands,
products, search results, inventory, or HTTP responses at the Gateway. The
existing request and response contracts remain unchanged.

## Architecture

The application layer depends on a small `CategoryTreeCache` contract rather
than on the Redis client. The contract supports reading the current tree,
storing a tree with a bounded lifetime, and invalidating the tree after a
category mutation.

The infrastructure layer provides a Redis implementation. Dependency wiring
constructs `CategoryService` with the repository and cache. A single async
Redis client is shared by the Catalog process and closed during application
shutdown.

Cache data is JSON produced from validated `CategoryTreeNode` models. The key
is namespaced and schema-versioned so later serialization changes cannot be
mistaken for the current format. The initial key is
`catalog:categories:tree:v1` and its TTL is 60 seconds.

## Read Flow

For `GET /api/v1/categories`:

1. `CategoryService` asks the cache for the category tree.
2. A valid cache hit is returned without querying PostgreSQL.
3. On a miss, malformed value, timeout, connection error, or other Redis
   failure, the service loads all categories from PostgreSQL and builds the
   hierarchy exactly as it does today.
4. The service attempts to cache the validated hierarchy for 60 seconds.
5. A failed cache write is logged but does not change the API response.

Malformed cached JSON is treated as a miss. The implementation makes a
best-effort attempt to delete the malformed value before continuing.

## Mutation and Invalidation Flow

For `POST /api/v1/categories`, database validation and persistence retain their
current behavior. Cache invalidation occurs only after the database commit
succeeds. A failed transaction therefore cannot evict a valid tree.

After a successful commit, `CategoryService` makes a best-effort deletion of
the category-tree key. Invalidation failure is logged but does not turn the
successful category creation into an HTTP error. If Redis becomes available
again while the old entry still exists, that entry can remain visible only
until the 60-second TTL expires. This bounded staleness is the accepted
trade-off for fail-open behavior.

## Configuration and Runtime

Catalog gains the following settings:

- `CATALOG_REDIS_URL`, defaulting to `redis://shide-redis:6379/1` so Catalog is
  isolated from Auth's default Redis database;
- `CATALOG_CATEGORY_CACHE_TTL_SECONDS`, defaulting to `60` and validated as a
  positive integer;
- `CATALOG_REDIS_SOCKET_TIMEOUT_SECONDS`, defaulting to `0.2` and validated as
  a positive number so cache failures do not significantly delay PostgreSQL
  fallback.

Development and production Compose configurations pass the Redis URL to the
Catalog container. Redis is not added as a hard readiness dependency and a
failed Redis connection does not make `/health/ready` fail, because the cache
is explicitly optional.

The Catalog package adds the async Redis client dependency. Tests use a fake
cache through dependency injection and do not require a live Redis server for
the fast suite.

## Observability and Error Handling

Cache failures are caught only at the cache boundary. Database errors and
existing Catalog domain errors continue through their current handlers.

Redis failures emit structured warning logs without cache payloads or
credentials. Cache hit, miss, and error counters are exposed through the
existing Catalog Prometheus endpoint. Metrics use a fixed `operation` label
(`read`, `write`, or `invalidate`) and do not include category IDs, Redis keys,
or other unbounded labels.

## Components

- `CategoryTreeCache`: application-facing async contract.
- Redis category-tree cache: JSON serialization, TTL, malformed-value handling,
  Redis exception translation, logging, and metrics.
- `CategoryService`: cache-aside read flow and post-commit invalidation.
- Catalog dependency wiring: shared client and injected cache implementation.
- Catalog lifespan: graceful Redis client shutdown.
- Catalog settings and Compose environment: Redis URL, TTL, and socket timeout.

Each component has one responsibility. Repository behavior and API routes do
not need to know whether a response came from Redis or PostgreSQL.

## Testing

Fast tests cover:

- cache miss loads PostgreSQL, returns the tree, and stores it with the
  configured TTL;
- cache hit returns the stored tree without calling `list_all`;
- cache write failure still returns the PostgreSQL result;
- cache read failure falls back to PostgreSQL;
- malformed cached JSON is discarded and rebuilt;
- successful category creation invalidates after commit;
- failed category creation does not invalidate;
- invalidation failure does not change the successful API response;
- Redis resources are closed during application shutdown;
- invalid TTL and socket-timeout configuration is rejected.

Existing Catalog category tests remain unchanged and green. Focused cache
tests use `fakeredis` to verify key naming, JSON round trips, TTL assignment,
and Redis error handling without requiring a live Redis process. `fakeredis`
is added only to Catalog's development dependency group.

## Acceptance Criteria

- Repeated category-tree reads within 60 seconds produce a cache hit and no
  category-list SQL query.
- Creating a category makes the next successful cached read rebuild the tree.
- Redis unavailability never prevents reading or creating categories.
- Cache-induced staleness is bounded to 60 seconds when invalidation cannot
  reach Redis.
- The public API schema and status codes do not change.
- Cache behavior is observable through bounded-cardinality metrics and safe
  warning logs.
- Catalog lint, type checking, and tests pass.

## Out of Scope

- Caching product, brand, search, or inventory responses;
- Gateway or Nginx response caching;
- write-through caching;
- distributed locks or stale-while-revalidate workers;
- making Redis part of Catalog readiness;
- frontend changes.
