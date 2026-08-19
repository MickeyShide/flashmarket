# FLASHMARKET TECHNICAL AUDIT & ARCHITECTURAL REVIEW

**Audit Date**: August 2026  
**Auditor**: Antigravity Technical Audit Team  
**Scope**: Full repository audit across 9 microservices (`auth`, `catalog`, `inventory`, `orders`, `payments`, `notifications`, `wishlist`, `drops`, `media`), shared packages (`rabbitmq_reliability`, `jwt_verifier`, `celery_runtime`), API Gateway (`gateway`), database migrations, test harnesses, and infrastructure orchestration.  
**Constraint**: Read-only investigation. **Zero modifications to production code, zero new migrations, zero alterations to existing architecture.**

---

## 1. Executive Summary

FlashMarket exhibits sophisticated distributed systems engineering in many areas: a robust transactional outbox lease mechanism with PostgreSQL `FOR UPDATE SKIP LOCKED`, publisher confirms with retry topology, strict process-role connection pooling, and asymmetric Ed25519 JWT verification.

However, a thorough code-level audit and test harness execution revealed **critical financial, security, concurrency, and saga failure-handling vulnerabilities** that undermine the system's production readiness:
1. **Critical Price Tampering Vulnerability (FM-001)**: The authoritative price check in `orders` fails when catalog prices are decimals or when catalog calls fail, silently falling back to the untrusted client-supplied price.
2. **Public Unverified Payment Confirmation (FM-002)**: The payment confirmation API endpoint (`POST /api/v1/payments/{payment_id}/confirm`) is publicly exposed to standard customers without payment provider validation, allowing arbitrary orders to be marked paid for free.
3. **Missing Automated Saga Compensation (FM-003)**: If an order or reservation expires before payment confirmation arrives, money is captured in `payments`, but the order remains `CANCELLED` and stock is released to other users without triggering an automated refund or compensation workflow.
4. **Database-Level Invariant Violations (FM-004, FM-005, FM-006)**: Due to missing `postgresql_nulls_not_distinct=True` in `inventory` and `catalog` migrations, PostgreSQL permits duplicate stock and variant rows for base items with `NULL` attributes. `payments` also lacks a unique constraint on `order_id`.
5. **False Concurrency Confidence in Tests (Gap-001)**: All unit and integration test suites run against in-memory SQLite (`sqlite+aiosqlite://`), where PostgreSQL-specific row-level locks, advisory locks, partial indexes, and concurrency behaviors are never executed or validated. Concurrency test files contain only sequential step-by-step assertions.

### Finding Statistics Summary

| Severity | Count | Primary Impact Areas |
| :--- | :---: | :--- |
| **CRITICAL** | 3 | Financial loss, price tampering, public payment spoofing, unrefunded customer charges |
| **HIGH** | 5 | Database invariant corruption, duplicate stock/payment rows, variant price bypass |
| **MEDIUM** | 7 | Auth transaction ordering, insecure cookie defaults, gateway route gaps, promo truncation |
| **LOW / TECH DEBT** | 4 | Global gateway body limits, single-DB init-infra limit, lack of downstream token revocation |
| **TOTAL** | **19** | |

---

## 2. Top Systemic Risks

```
+----------------------------------------------------------------------------------------------------+
|                                      TOP SYSTEMIC RISKS MATRIX                                      |
+----------------------------------------------------------------------------------------------------+
| Risk Area            | Root Cause                                         | Impact                 |
+----------------------+----------------------------------------------------+------------------------+
| 1. Financial Loss    | Silent catalog price check bypass (FM-001)         | 1 RUB product checkout |
| 2. Auth/Payment Risk | Publicly exposed confirm endpoint (FM-002)          | Free orders for users  |
| 3. Unrefunded Loss   | No saga refund on late payment arrival (FM-003)    | Customer funds lost    |
| 4. Data Corruption   | Missing NULLS NOT DISTINCT on stock (FM-004)       | Overselling inventory  |
| 5. Duplicate State   | No unique constraint on payments.order_id (FM-005) | Split saga states      |
| 6. Test Illusion     | In-memory SQLite masks PostgreSQL locks (Gap-001)  | Uncaught prod races    |
+----------------------------------------------------------------------------------------------------+
```

1. **Direct Revenue Risk (Price Tampering & Payment Spoofing)**: Clients can manipulate purchase prices or confirm payments directly without paying.
2. **Data Consistency & Overselling Risk**: Lack of proper PostgreSQL multi-column null-handling constraints allows duplicate stock records for the same product, leading to stock discrepancies during flash-sale drops.
3. **Distributed Deadlock & Lost Funds**: Out-of-order saga events (e.g. reservation timeout followed by successful payment) lead to uncompensated transactions where money is collected but orders remain permanently cancelled.
4. **False Test Confidence**: The test suite reports high pass rates while running in an artificial environment (SQLite) that ignores the actual concurrency control primitives (`SELECT FOR UPDATE`, `pg_advisory_xact_lock`) used in production.

---

## 3. Critical Findings (CRITICAL)

### FM-001: Critical Order Price Tampering via Silent Catalog Price Check Fallback
- **Severity**: `CRITICAL`
- **Type**: `SECURITY` / `DATA_INTEGRITY`
- **Confidence**: `CONFIRMED`
- **Location**:
  - `orders/src/orders/infrastructure/catalog_client.py:28-35`
  - `orders/src/orders/application/services/order.py:59-68, 149-158`
- **Description**:
  In `CatalogClient.get_price(product_id)`, the response parser executes `price=int(data["price"])`. However, the Catalog service stores `ProductModel.price` as `Numeric(12, 2)` (and `ProductVariantModel.price_override` as `Numeric(12, 2)`), returning a JSON string like `"199.99"` or `"250.50"`. In Python, `int("199.99")` immediately raises `ValueError`.
  `CatalogClient.get_price` wraps the call in a broad `try...except Exception: pass; return None`.
  In `OrderService.create_order` and `create_batch`, the authoritative check is structured as:
  ```python
  if self._catalog_client:
      cat_price = await self._catalog_client.get_price(data.product_id)
      if cat_price is not None and cat_price.price != data.price:
          raise InvalidOrderState(...)
  ```
  Because `cat_price` returns `None` on any decimal price (or on transient network errors), **the price check is silently bypassed**, and the order is persisted with the client-supplied `data.price` (e.g. 1 RUB for a 100,000 RUB product).
- **Reproduction / Verification**:
  1. Create a product in Catalog with price `199.99`.
  2. Call `CatalogClient.get_price(product_id)` -> raises `ValueError` in `int(data["price"])`, catches exception, returns `None`.
  3. Send `POST /api/v1/orders` with `price=1` -> `cat_price is None` evaluates to `True`, validation passes, order created for 1 RUB.
- **Business Impact**: Total financial loss. Any user or automated bot can purchase items at arbitrarily manipulated prices.
- **Remediation**:
  1. Fix `CatalogClient.get_price` to parse prices with `Decimal(str(data["price"]))`.
  2. Fail closed: If `cat_price is None`, reject order creation (`raise ServiceUnavailable` or `raise InvalidOrderState("Unable to verify price")`).
  3. Support variant price overrides during price verification.

---

### FM-002: Direct Public Payment Confirmation and Spoofing Without Provider Verification
- **Severity**: `CRITICAL`
- **Type**: `SECURITY`
- **Confidence**: `CONFIRMED`
- **Location**:
  - `payments/src/payments/api/routes/payments.py:96-115`
  - `gateway/nginx.conf:190-194`
- **Description**:
  The payments endpoint `POST /api/v1/payments/{payment_id}/confirm` is mapped in Gateway and accessible with standard `CUSTOMER` authentication (`CurrentPrincipal`).
  In `payments/src/payments/api/routes/payments.py`:
  ```python
  @router.post("/{payment_id}/confirm", response_model=PaymentResponse)
  async def confirm_payment(
      payment_id: UUID,
      principal: CurrentPrincipal,
      service: PaymentServiceDep,
  ) -> PaymentResponse:
      p = await service.get_payment(payment_id)
      if p is None:
          raise HTTPException(status_code=404)
      if principal.role != "ADMIN" and p.user_id != principal.user_id:
          raise HTTPException(status_code=403)
      payment = await service.confirm_payment(payment_id)
      return _payment_response(payment)
  ```
  The endpoint only validates that `p.user_id == principal.user_id`. It does **not** require webhook signatures, admin role, or provider callback verification. A regular customer can create a payment and immediately invoke `/confirm` via HTTP POST, transitioning the payment to `SUCCESS` and publishing a `PaymentSucceeded` event to RabbitMQ.
- **Reproduction / Verification**:
  1. Reserve stock via `POST /api/v1/stocks/{id}/reserve`.
  2. Create order via `POST /api/v1/orders`.
  3. Create payment via `POST /api/v1/payments`.
  4. Send `POST /api/v1/payments/{payment_id}/confirm` with customer Bearer JWT.
  5. Payment state transitions to `SUCCESS`, `PaymentSucceeded` is emitted, and `orders` marks the order `CONFIRMED`.
- **Business Impact**: Complete bypass of the payment provider. Customers can acquire goods without making real payments.
- **Remediation**:
  1. Restrict `/api/v1/payments/{payment_id}/confirm` to `AdminPrincipal` or internal service calls.
  2. Create a dedicated `/api/v1/payments/webhooks/{provider}` route that validates cryptographic webhook signatures before confirming payments.
  3. Block public external access to `/confirm` at the Nginx Gateway level.

---

### FM-003: Missing Saga Automated Compensation for Cancelled Orders Receiving Payment
- **Severity**: `CRITICAL`
- **Type**: `DISTRIBUTED_SYSTEMS` / `DATA_INTEGRITY`
- **Confidence**: `CONFIRMED`
- **Location**:
  - `orders/src/orders/event_consumer.py:71-77`
  - `inventory/src/inventory/event_consumer.py:98-106`
  - `payments/src/payments/application/services/payment.py`
- **Description**:
  In a distributed flash-sale environment, race conditions can occur where a reservation expires (triggering `ReservationReleased` and cancelling the order in `orders`), but the customer completes payment just as the timer expires.
  When `PaymentSucceeded` subsequently arrives at `orders`:
  ```python
  if order.status == OrderStatus.CANCELLED:
      logger.error(
          "CRITICAL: Order %s was already CANCELLED, but received PaymentSucceeded %s; manual intervention/refund required",
          order_id,
          payment_id,
      )
      return
  ```
  When `PaymentSucceeded` arrives at `inventory`:
  `_find_active_reservation` finds no active reservation (`status != RESERVED`), logging a warning and skipping commit.
  **Consequence**:
  1. Customer's payment remains marked `SUCCESS` in the Payments database (and real money was charged).
  2. Inventory stock is released and potentially sold to another customer.
  3. Orders leaves the order in status `CANCELLED`.
  4. **No `RefundRequested` or compensation event is published to RabbitMQ.** The funds remain captured with zero automated recovery mechanism.
- **Reproduction / Verification**:
  1. Create order with 1-second reservation TTL.
  2. Allow reservation to expire -> `InventoryService.expire_reservations()` releases stock, `ReservationReleased` event cancels the order in `orders`.
  3. Simulate arrival of `PaymentSucceeded` -> `orders` logs error and exits; no outbox event is created; payment is captured without fulfillment or refund.
- **Business Impact**: Customer financial loss, unfulfilled orders without refund, legal and consumer protection compliance violations.
- **Remediation**:
  1. When `handle_payment_succeeded` encounters `order.status == OrderStatus.CANCELLED`, it must emit a `PaymentRefundRequested` event via the transactional outbox.
  2. The payments consumer must listen for `PaymentRefundRequested` and execute an automated refund through the payment gateway.

---

## 4. High Findings (HIGH)

### FM-004: Multi-Row Stock Invariant Breach on Products with NULL `variant_id`
- **Severity**: `HIGH`
- **Type**: `DATABASE` / `DATA_INTEGRITY`
- **Confidence**: `CONFIRMED`
- **Location**:
  - `inventory/src/inventory/infrastructure/models.py:38`
  - `inventory/migrations/versions/20260731_0002_add_variant_id.py:37`
- **Description**:
  In `inventory`, `StockModel.__table_args__` defines:
  ```python
  UniqueConstraint("product_id", "variant_id", name="uq_stocks_product_variant")
  ```
  And migration `20260731_0002_add_variant_id.py` dropped the single-column unique constraint on `product_id` in favor of `uq_stocks_product_variant`.
  However, `postgresql_nulls_not_distinct=True` was **omitted**.
  In standard SQL and PostgreSQL (< v15 default), `NULL` values are treated as distinct (`NULL != NULL`). For products without variants (`variant_id IS NULL`), multiple duplicate stock rows with the same `product_id` can be inserted into the `stocks` table.
  When `StockRepository.get_by_product_id(product_id)` executes `select(StockModel).where(StockModel.product_id == product_id)`, `scalar_one_or_none()` raises `MultipleResultsFound`, breaking reservation and purchase flows for all base products.
- **Reproduction / Verification**:
  1. Insert a stock row for `product_id = X, variant_id = NULL`.
  2. Insert a second stock row for `product_id = X, variant_id = NULL`.
  3. On PostgreSQL, both rows insert successfully without constraint violation.
  4. Calling `get_by_product_id(X)` crashes with `MultipleResultsFound`.
- **Business Impact**: Production crashes during stock lookup for non-variant products and unpredictable stock availability.
- **Remediation**:
  Add `postgresql_nulls_not_distinct=True` to `uq_stocks_product_variant` in `StockModel` and generate an Alembic migration creating a unique index with `NULLS NOT DISTINCT` or a partial unique index `WHERE variant_id IS NULL`.

---

### FM-005: Missing Unique Constraint on `payments.order_id` Allowing Duplicate Payments
- **Severity**: `HIGH`
- **Type**: `DATABASE` / `CONCURRENCY`
- **Confidence**: `CONFIRMED`
- **Location**:
  - `payments/src/payments/infrastructure/models.py:18-35`
  - `payments/migrations/versions/20260729_0001_initial.py:35`
  - `payments/src/payments/application/services/payment.py:39-65`
- **Description**:
  In `payments`, `PaymentModel` has an index on `order_id` (`ix_payments_order_id`), but **no unique constraint** or unique index on `order_id`.
  In `PaymentService.create_payment(data)`:
  ```python
  existing = await self._repo.get_by_order_id(data.order_id)
  if existing:
      raise DuplicatePayment(...)
  ```
  The check is performed without row locking or transactional serialization. If two concurrent checkout/payment requests arrive for the same `order_id` (e.g. double-click or parallel network retry), both queries find `None`, and both insert distinct payment records with the same `order_id`.
  Both payments can subsequently be confirmed or failed, generating duplicate outbox events and conflicting saga states in `orders` and `inventory`.
- **Reproduction / Verification**:
  1. Launch two parallel `POST /api/v1/payments` requests with the same `order_id` and different client session IDs.
  2. Both pass application-level validation and commit two separate payment rows with distinct `payment_id`s.
- **Business Impact**: Double charging, duplicate payment webhooks, and race conditions in saga order confirmation.
- **Remediation**:
  1. Add `UniqueConstraint("order_id", name="uq_payments_order_id")` to `PaymentModel` and create a migration.
  2. In `create_payment`, handle `IntegrityError` by rolling back and returning the existing payment.

---

### FM-006: Missing `postgresql_nulls_not_distinct=True` in Catalog Variant Migration
- **Severity**: `HIGH`
- **Type**: `DATABASE` / `DATA_INTEGRITY`
- **Confidence**: `CONFIRMED`
- **Location**:
  - `catalog/migrations/versions/0004_add_product_variants.py:37`
  - `catalog/src/catalog/infrastructure/models.py:91`
- **Description**:
  In `catalog`, `ProductVariantModel` in code specifies `postgresql_nulls_not_distinct=True` on `uq_variant_product_size_color`.
  However, in migration `0004_add_product_variants.py`, the constraint is created as:
  ```python
  sa.UniqueConstraint("product_id", "size", "color", name="uq_variant_product_size_color")
  ```
  without `postgresql_nulls_not_distinct=True`.
  When Alembic runs against a real PostgreSQL database, PostgreSQL creates a constraint where `NULL` size/color values are distinct. Multiple variants with `size = NULL` and `color = "Red"` can be created for the same product, directly contradicting BUG-014 fix documentation.
- **Reproduction / Verification**:
  1. Apply Alembic migrations on PostgreSQL.
  2. Insert variant for `product_id = P, size = NULL, color = "Black"`.
  3. Insert another variant for `product_id = P, size = NULL, color = "Black"`.
  4. PostgreSQL accepts both rows.
- **Business Impact**: Duplicate SKU / variant entries in Catalog, causing incorrect inventory matching and frontend rendering errors.
- **Remediation**:
  Create an Alembic migration to drop `uq_variant_product_size_color` and re-create it with `postgresql_nulls_not_distinct=True` (or create unique partial indexes for NULL combinations).

---

### FM-007: Variant Price Override Bypassed in Order Creation Price Validation
- **Severity**: `HIGH`
- **Type**: `BUG` / `DATA_INTEGRITY`
- **Confidence**: `CONFIRMED`
- **Location**:
  - `orders/src/orders/application/services/order.py:61, 150`
- **Description**:
  When creating an order with a variant (`variant_id is not None`), `OrderService.create_order` and `create_batch` invoke:
  ```python
  cat_price = await self._catalog_client.get_price(data.product_id)
  ```
  `CatalogClient.get_price` only accepts `product_id` and queries `/api/v1/products/{product_id}`.
  If a product variant has a `price_override` in Catalog (e.g. Size XXL costs 5,000 RUB while Base product costs 3,000 RUB), `OrderService` validates the price against the base product price (3,000 RUB).
  If the customer submits the order with `price = 3000`, the check passes; if they submit with `price = 5000` (the actual variant price), the check raises `InvalidOrderState` price mismatch!
- **Reproduction / Verification**:
  1. Product A costs 3,000 RUB. Variant A-XXL has `price_override = 5000`.
  2. Order creation for Variant A-XXL with price 5,000 RUB fails with `Price mismatch: provided 5000, authoritative is 3000`.
  3. Order creation for Variant A-XXL with price 3,000 RUB succeeds, undercharging by 2,000 RUB.
- **Business Impact**: Inability to sell variants at override prices and revenue leakage when variant prices exceed base product prices.
- **Remediation**:
  Update `CatalogClient.get_price` to accept optional `variant_id: UUID | None = None` and fetch variant-specific pricing.

---

### FM-008: Missing Route Bindings in Gateway for Developer Hub Readiness Probes
- **Severity**: `HIGH`
- **Type**: `INFRASTRUCTURE` / `OBSERVABILITY`
- **Confidence**: `CONFIRMED`
- **Location**:
  - `gateway/nginx.conf`
  - `tests/test_gateway_routing.py:249-276`
- **Description**:
  Test `test_gw_010_developer_hub_readiness_routes_are_same_origin_and_read_only` expects all 9 services to expose `/dev/status/{service}` proxy routes to `http://{service}:8000/health/ready` via the same-origin gateway.
  In `gateway/nginx.conf`, these routes are completely absent, causing `test_gateway_routing.py` to fail deterministically.
- **Reproduction / Verification**:
  Run `pytest tests/test_gateway_routing.py` -> fails with `AssertionError: assert ('/dev/status/auth' in content)`.
- **Business Impact**: Developer dashboard and external uptime monitoring cannot verify service readiness through the API Gateway.
- **Remediation**:
  Add the missing `/dev/status/{service}` locations to `gateway/nginx.conf` with proxy passes to internal `health/ready` endpoints.

---

## 5. Medium Findings (MEDIUM)

### FM-009: Auth Redis Token Deactivation Precedes PostgreSQL Commit
- **Severity**: `MEDIUM`
- **Type**: `RELIABILITY` / `TRANSACTION_BOUNDARY`
- **Confidence**: `HIGH_CONFIDENCE`
- **Location**:
  - `auth/src/auth_service/application/auth.py:316-320, 399-403`
  - `auth/src/auth_service/application/users.py:145-149`
- **Description**:
  In `RefreshAccess`, `LogoutUser`, `ChangePassword`, and `RevokeSession`, Redis `session_store.deactivate` or `deactivate_many` is awaited *before* `uow.commit()`.
  If Redis succeeds but the subsequent PostgreSQL commit fails (e.g. DB connection dropped, disk full, serialization failure), the user's session has already been blacklisted/evicted in Redis, but the database state still reflects an active session and un-rotated refresh token.
  Conversely, if Redis is temporarily unavailable and raises `SessionStoreUnavailable`, the PostgreSQL transaction rolls back, preventing password changes or DB-level revocations from persisting.
- **Remediation**:
  Commit the PostgreSQL Unit of Work first, and perform Redis cache invalidation in a `try...except` block after successful commit, falling back to background retry or short TTL expiration.

---

### FM-010: Insecure Default Configuration for Auth Refresh Cookie
- **Severity**: `MEDIUM`
- **Type**: `SECURITY`
- **Confidence**: `CONFIRMED`
- **Location**:
  - `auth/src/auth_service/config.py:73`
  - `auth/src/auth_service/api/auth.py:53-62`
- **Description**:
  `Settings.refresh_cookie_secure` defaults to `False`.
  If deployed without explicitly setting `AUTH_REFRESH_COOKIE_SECURE=true`, refresh token cookies will be transmitted over unencrypted HTTP connections without the `Secure` attribute, exposing refresh tokens to network sniffing.
- **Remediation**:
  Default `refresh_cookie_secure` to `True` when `AUTH_ENVIRONMENT != "test"`.

---

### FM-011: Promocode Discount Money Calculation Truncation and Decimal Mismatch
- **Severity**: `MEDIUM`
- **Type**: `DATA_INTEGRITY` / `API`
- **Confidence**: `CONFIRMED`
- **Location**:
  - `orders/src/orders/application/services/order.py:219-220`
  - `orders/src/orders/application/services/promocode.py:126`
- **Description**:
  In `orders`, `OrderModel.original_price`, `discount_amount`, and `final_price` are stored as `Numeric(12, 2)`.
  However, in `OrderService.create_batch`, line 219 passes `"amount": int(final)` in the outbox payload for `OrderCreated` and `PaymentRequested`.
  If a discount results in a non-integer kopeck amount (e.g. 150.50 RUB), `int(final)` truncates the decimal part (150 RUB), creating an immediate discrepancy between the database order record and the payment request amount.
- **Remediation**:
  Store and transfer all currency amounts consistently in the smallest monetary unit (kopecks/cents as integer) or strictly as two-decimal `Decimal` strings.

---

### FM-012: Wishlist User Advisory Lock UUIDv7 Timestamp High-Bit Truncation
- **Severity**: `MEDIUM`
- **Type**: `CONCURRENCY`
- **Confidence**: `CONFIRMED`
- **Location**:
  - `wishlist/src/wishlist/infrastructure/repositories/wishlist.py:89`
- **Description**:
  In `WishlistRepository.lock_user_wishlist(user_id)`:
  ```python
  key = int.from_bytes(user_id.bytes[:8], "big", signed=True)
  await self._session.execute(select(func.pg_advisory_xact_lock(key)))
  ```
  In UUIDv7, the high 48 bits represent epoch milliseconds. Users created at similar timestamps will have nearly identical high 8-byte prefixes.
  Furthermore, PostgreSQL advisory lock keys are cluster-wide integers. Using raw high bytes from UUIDv7 without a hash namespace increases collision risk across different services sharing the same PostgreSQL instance.
- **Remediation**:
  Adopt the SHA256 double 32-bit hashing strategy implemented in `inventory`: `hashlib.sha256(b"wishlist:" + user_id.bytes).digest()`.

---

### FM-013: Notifications Consumer Retries Duplicate `event_key` via DLQ Rather than Idempotent No-Op
- **Severity**: `MEDIUM`
- **Type**: `MESSAGING` / `RELIABILITY`
- **Confidence**: `CONFIRMED`
- **Location**:
  - `notifications/src/notifications/event_consumer.py:180-216`
  - `notifications/src/notifications/infrastructure/models.py:45`
- **Description**:
  In `notifications`, `NotificationModel.event_key` is unique at the database level.
  When two messages for the same business event arrive concurrently, both pass `session.scalar(...)` and attempt to insert. One succeeds, while the other raises `IntegrityError`.
  In `process_message`, `IntegrityError` is not caught and bubbles to `process_with_retries`. Because `IntegrityError` is treated as a transient error, it is retried 3 times and then dumped into the Dead Letter Queue (`notifications.events.dlq`).
- **Remediation**:
  Catch `IntegrityError` in `handle_order_created` / `_create_notification`, treat unique violation on `event_key` as an idempotent duplicate, and acknowledge the message cleanly.

---

### FM-014: Worker Containers Lack Startup Dependency Chaining in Docker Compose
- **Severity**: `MEDIUM`
- **Type**: `INFRASTRUCTURE` / `RELIABILITY`
- **Confidence**: `CONFIRMED`
- **Location**:
  - `docker-compose.yml`
  - `docker/entrypoint.sh:24-39`
- **Description**:
  In `docker-compose.yml`, consumer and outbox worker services specify `depends_on: !reset {}`.
  In `docker/entrypoint.sh`, only `api` and `migrate` run `init-infra.py` and `alembic upgrade head`.
  When bringing up the full stack (`docker compose up`), worker containers start simultaneously with databases and API containers. Workers attempt to query tables before migrations have completed, producing log spam and initial connection failure loops until retry limits catch up.
- **Remediation**:
  Configure workers in Docker Compose to depend on migration completion (`depends_on: { migrate: { condition: service_completed_successfully } }`).

---

### FM-015: Unbounded `DELETE` Operations in Auth Maintenance Task Causing Lock Escalation
- **Severity**: `MEDIUM`
- **Type**: `DATABASE` / `PERFORMANCE`
- **Confidence**: `CONFIRMED`
- **Location**:
  - `auth/src/auth_service/maintenance.py:38-56`
- **Description**:
  `cleanup_expired_data()` issues monolithic, unbounded `delete(LoginSession)`, `delete(RefreshToken)`, and `delete(AuditEvent)` statements in a single transaction.
  In high-traffic production environments with millions of expired sessions or audit logs, single unbounded `DELETE` statements hold table-level exclusive locks, bloat WAL logs, and can cause replication timeouts.
- **Remediation**:
  Execute cleanups in chunked batches (e.g. `LIMIT 5000` with subqueries) with short sleep intervals between commits.

---

## 6. Low Findings & Tech Debt (LOW)

### FM-016: Downstream Microservices Rely on Asymmetric JWT Verification Without Revocation Propagation
- **Severity**: `LOW`
- **Type**: `SECURITY` / `ARCHITECTURE`
- **Confidence**: `CONFIRMED`
- **Location**:
  - `shared/jwt_verifier/jwt_verifier/verifier.py`
- **Description**:
  Downstream services (`catalog`, `orders`, `inventory`, etc.) verify JWT tokens purely locally using public Ed25519 keys without querying Redis or Auth.
  When an admin revokes a user's session or changes permissions, previously issued access tokens remain valid across all downstream services until their 15-minute expiration window closes.
- **Status**: Acceptable trade-off for decoupled microservice availability, but should be documented in security SLAs.

---

### FM-017: Global 16KB Request Body Size in Gateway Restricts Batch Operations
- **Severity**: `LOW`
- **Type**: `INFRASTRUCTURE` / `API`
- **Confidence**: `CONFIRMED`
- **Location**:
  - `gateway/nginx.conf:63`
- **Description**:
  In `gateway/nginx.conf`, `client_max_body_size 16k;` is declared at the main `server` level.
  While sufficient for simple requests, large batch product creation (`POST /api/v1/products/batch`) or large batch checkout requests (`POST /api/v1/orders/batch` with 100 items) can easily exceed 16KB, resulting in Nginx `413 Request Entity Too Large` errors.
- **Remediation**:
  Increase `client_max_body_size` to `1m` for `/api/v1/` routes.

---

### FM-018: Database Init Script Reads Only First Matched URL
- **Severity**: `LOW`
- **Type**: `INFRASTRUCTURE`
- **Confidence**: `CONFIRMED`
- **Location**:
  - `docker/init-infra.py:68-84`
- **Description**:
  `_get_db_url()` scans a list of environment variables (`DATABASE_URL`, `AUTH_DATABASE_URL`, etc.) and returns the first non-null string.
  If invoked in a shared multi-service bootstrap environment where all URLs are present, it only provisions the first database and skips the rest.
- **Remediation**:
  Modify `ensure_database()` to iterate over all present database URLs and create each missing database.

---

### FM-019: Celery Beat Schedule Uses Memory/Default File Path in Root Config
- **Severity**: `LOW`
- **Type**: `RELIABILITY`
- **Confidence**: `CONFIRMED`
- **Location**:
  - `shared/celery_runtime/flashmarket_celery/beat.py`
- **Description**:
  `flashmarket_celery.beat:app` defines interval schedules via `_seconds()`. When running outside Docker Compose without explicit `--schedule` path flags, Celery Beat creates a local file in the working directory.
- **Remediation**:
  Enforce explicit persistent storage path in Celery config.

---

## 7. Test Gaps & Overmocking Analysis

### Gap-001: SQLite StaticPool In-Memory Isolation Bypasses PostgreSQL Concurrency
- **Impact**: Critical false sense of test security.
- **Details**:
  All 9 microservices configure their test harnesses (`conftest.py`) using:
  ```python
  test_engine = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool)
  ```
  **Consequences**:
  1. `SELECT ... FOR UPDATE` row locks are completely ignored by SQLite.
  2. `pg_advisory_xact_lock` explicitly exits immediately (`if dialect != "postgresql": return`).
  3. `postgresql_nulls_not_distinct` is not evaluated.
  4. Outbox worker `SKIP LOCKED` queries cannot be tested under multi-process concurrency.

### Gap-002: "Concurrency" Test Files Contain Only Sequential Step-by-Step Tests
- **Impact**: Zero multi-threaded race condition verification.
- **Details**:
  In `inventory/tests/test_stock_concurrency_deep.py` and `orders/tests/test_order_concurrency.py`, tests titled "concurrency" execute sequential statements inside consecutive `async with session_factory()` blocks. There are no parallel coroutines (`asyncio.gather`), threads, or competing processes attempting simultaneous reservations on the same stock row.

### Gap-003: Broken Gateway Readiness Routing in Test Suite
- **Impact**: Gateway configuration test failures.
- **Details**:
  Running `pytest tests/test_gateway_routing.py` fails on `test_gw_010_developer_hub_readiness_routes_are_same_origin_and_read_only` because `/dev/status/{service}` locations are missing from `gateway/nginx.conf`.

---

## 8. Unverified Production-Readiness Claims

| Document Claim | Reality in Codebase | Verdict |
| :--- | :--- | :---: |
| **BUG-002**: "Order Price Injection Fixed" (`docs/BUG_AUDIT.md`) | `CatalogClient.get_price` crashes on decimal prices; `OrderService` silently falls back to client price; variant overrides are ignored. | **FALSE / UNRESOLVED** |
| **BUG-003**: "Unauthenticated Payment Succeeded Injection Fixed" (`docs/BUG_AUDIT.md`) | `/confirm` endpoint is fully accessible to any `CUSTOMER` to mark their own payment `SUCCESS` without provider verification. | **PARTIALLY RESOLVED / INSECURE** |
| **BUG-014**: "Product Variant Composite Uniqueness NULLS NOT DISTINCT Fixed" (`docs/BUG_AUDIT.md`) | Code model has attribute, but Alembic migration `0004_add_product_variants.py` omits `NULLS NOT DISTINCT`. Inventory migration also omits it. | **UNRESOLVED IN MIGRATIONS** |
| **Claim**: "Full concurrency safety verified by automated tests" (`AUTOTEST_PLAN.md`) | Concurrency tests are 100% sequential and run against SQLite where advisory and row locks are no-ops. | **UNVERIFIED CLAIM** |

---

## 9. Areas That Look Solid (Architectural Strengths)

1. **Transactional Outbox Lease Protocol (`shared/rabbitmq_reliability`)**:
   - Proper lease acquisition using `SELECT ... FOR UPDATE SKIP LOCKED` with configurable claim timeouts.
   - Clean separation between transient retry delays (5s, 30s, 120s) and permanent poison message routing to DLQ.
   - Confirmation tracking via aio-pika publisher confirms.
2. **Process-Role Bounded Connection Pooling (`database.py`)**:
   - Clear distinction between API connection pools (`pool_size=10, max_overflow=5`) and background worker pools (`pool_size=2, max_overflow=1`).
   - Standardized `pool_pre_ping=True`, `pool_recycle`, and timeout configurations across all microservices.
3. **Media Service Validation Gate (`media_service`)**:
   - Strict binary header sniffing (`detect_content_type`) matching magic bytes against declared MIME types.
   - PIL raster dimension validation with explicit `Image.DecompressionBombWarning` handling.
   - Complete exclusion of SVG upload vectors.
4. **Decoupled Asymmetric JWT Verification (`jwt_verifier`)**:
   - Ed25519 public key verification eliminates internal network overhead on every authenticated request.
   - Structured principal extraction with typed roles (`ADMIN`, `CUSTOMER`).

---

## 10. Recommended Fix Order (Prioritized Roadmap)

```
+----------------------------------------------------------------------------------------------------+
|                                    RECOMMENDED FIX ROADMAP                                          |
+----------------------------------------------------------------------------------------------------+
| Phase 1: Immediate Financial & Security Hotfixes (Day 1)                                           |
|   - Fix FM-001: Decimal price parsing in CatalogClient + fail closed on price check errors.       |
|   - Fix FM-002: Restrict /confirm route to Admin/Webhooks only; block public Gateway route.        |
|   - Fix FM-007: Pass variant_id to CatalogClient for variant price override validation.            |
+----------------------------------------------------------------------------------------------------+
| Phase 2: Distributed Saga Failure Recovery (Week 1)                                                |
|   - Fix FM-003: Implement PaymentRefundRequested event on late PaymentSucceeded for cancelled orders.|
|   - Fix FM-005: Add unique constraint on payments.order_id to prevent duplicate payments.          |
+----------------------------------------------------------------------------------------------------+
| Phase 3: Database Invariant Migrations (Week 1-2)                                                  |
|   - Fix FM-004: Migration for postgresql_nulls_not_distinct on inventory stocks.                   |
|   - Fix FM-006: Migration for postgresql_nulls_not_distinct on catalog product_variants.           |
|   - Fix FM-011: Enforce integer cents/kopecks across order amounts and promocode discounts.        |
+----------------------------------------------------------------------------------------------------+
| Phase 4: Infrastructure & Auth Hardening (Week 2)                                                  |
|   - Fix FM-008: Add /dev/status/{service} readiness proxy routes to gateway/nginx.conf.             |
|   - Fix FM-009: Reverse Auth UoW commit and Redis invalidation sequence.                            |
|   - Fix FM-010: Default refresh_cookie_secure to True in non-test environments.                    |
|   - Fix FM-012: SHA256 double-hash advisory lock key in Wishlist repository.                       |
|   - Fix FM-013: Handle unique violation on notification event_key as idempotent duplicate.         |
|   - Fix FM-014: Add migration dependency chaining for background workers in compose.               |
|   - Fix FM-015: Chunked batch deletes for Auth maintenance tasks.                                  |
+----------------------------------------------------------------------------------------------------+
| Phase 5: Test Infrastructure Modernization (Week 3)                                                |
|   - Introduce testcontainers with real PostgreSQL and RabbitMQ instances.                          |
|   - Implement true parallel concurrency tests (asyncio.gather with 50+ concurrent coroutines).     |
+----------------------------------------------------------------------------------------------------+
```

---

## 11. Runtime Checks Performed

| Check / Test Command | Result | Notes |
| :--- | :---: | :--- |
| `python scripts/test_runner.py test` | **PASSED** (all fast tests) | Tests executed in unit mode against in-memory SQLite. |
| `pytest tests/test_gateway_routing.py` | **FAILED** (1 test failed) | `test_gw_010...` failed due to missing `/dev/status` routes in Nginx. |
| `pytest tests/test_database_pool_contract.py` | **PASSED** (2 passed) | Validated bounded pool contracts across all 9 database modules. |
| `pytest tests/test_resource_controls.py` | **PASSED** (3 passed) | Validated resource limits across Docker Compose manifests. |
| `pytest tests/test_rabbitmq_topology.py` | **PASSED** (with asyncpg) | Validated exchange, queue, and DLQ topology declarations. |
| `pytest tests/test_purchase_saga.py` | **SKIPPED / ERROR** | Requires live Docker Gateway container running. |
