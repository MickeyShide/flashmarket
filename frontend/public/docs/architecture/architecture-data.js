/**
 * Source-of-truth content model for the future FlashMarket Architecture Explorer.
 *
 * This module describes audited repository behavior. It has no React or DOM
 * dependency and intentionally keeps references normalized by stable IDs.
 */

const STATUS = Object.freeze({
  IMPLEMENTED: "implemented",
  PARTIAL: "partial",
  PLANNED: "planned",
  UNCLEAR: "unclear",
});

const evidence = [
  { id: "evidence-audit", path: "docs/architecture/FLASHMARKET_ARCHITECTURE_AUDIT.md", symbol: "full document", description: "Audited architecture narrative and cross-service source index." },
  { id: "evidence-root-compose", path: "docker-compose.yml", symbol: "services", description: "Root runtime topology, process roles, volumes and dependencies." },
  { id: "evidence-entrypoint", path: "docker/entrypoint.sh", symbol: "role dispatch", description: "API, consumer, outbox and maintenance process entrypoints." },
  { id: "evidence-init-infra", path: "docker/init-infra.py", symbol: "main", description: "Logical databases, RabbitMQ vhost, exchanges, queues and policies." },
  { id: "evidence-celery-runtime", path: "shared/celery_runtime/flashmarket_celery/app.py", symbol: "create_app / TASK_ROUTES", description: "Shared late-ACK Celery configuration and four isolated maintenance queues." },
  { id: "evidence-celery-async", path: "shared/celery_runtime/flashmarket_celery/async_runner.py", symbol: "AsyncRunner", description: "Persistent child-process asyncio loop used by synchronous Celery tasks." },
  { id: "evidence-celery-beat", path: "shared/celery_runtime/flashmarket_celery/beat.py", symbol: "app", description: "Singleton schedule for all four maintenance commands." },
  { id: "evidence-gateway", path: "gateway/nginx.conf", symbol: "server", description: "Public routing, trusted proxies, limits, timeouts and health behavior." },
  { id: "evidence-openapi", path: "frontend/public/dev/services.json", symbol: "generated service registry", description: "Nine public API services and 103 gateway-reachable OpenAPI operations." },
  { id: "evidence-rabbit-topology", path: "shared/rabbitmq_reliability/rabbitmq_reliability/topology.py", symbol: "declare_consumer_topology", description: "Main, retry and DLQ topology." },
  { id: "evidence-rabbit-delivery", path: "shared/rabbitmq_reliability/rabbitmq_reliability/delivery.py", symbol: "publish_confirmed", description: "Persistent mandatory publishing with confirms and timeout." },
  { id: "evidence-rabbit-consumer", path: "shared/rabbitmq_reliability/rabbitmq_reliability/delivery.py", symbol: "process_with_retries", description: "ACK ordering, failure classification, retry and DLQ transfer." },
  { id: "evidence-rabbit-inbox", path: "shared/rabbitmq_reliability/rabbitmq_reliability/inbox.py", symbol: "begin_event_once", description: "Transactional consumer inbox deduplication." },
  { id: "evidence-outbox-lease", path: "shared/rabbitmq_reliability/rabbitmq_reliability/outbox_lease.py", symbol: "claim_next_event / record_publish_result", description: "Short SQL lease, SKIP LOCKED claim and token-checked publish result." },
  { id: "evidence-heartbeat", path: "shared/rabbitmq_reliability/rabbitmq_reliability/heartbeat.py", symbol: "WorkerHeartbeat", description: "Progress-based worker health signal." },
  { id: "evidence-auth-models", path: "auth/src/auth_service/models.py", symbol: "User / Session / RefreshToken / AuditEvent / OutboxEvent", description: "Auth-owned persistence and constraints." },
  { id: "evidence-auth-security", path: "auth/src/auth_service/security.py", symbol: "password_hasher / create_access_token / generate_refresh_token", description: "Argon2id, EdDSA access JWT and refresh-token generation." },
  { id: "evidence-auth-app", path: "auth/src/auth_service/application/auth.py", symbol: "AuthService", description: "Register, login, refresh rotation, reuse detection and logout transactions." },
  { id: "evidence-auth-cache", path: "auth/src/auth_service/cache.py", symbol: "session_cache_key / activate_session / should_touch_session", description: "Redis active-session and touch-throttle state." },
  { id: "evidence-auth-rate", path: "auth/src/auth_service/rate_limit.py", symbol: "enforce_rate_limit", description: "Redis transactional rate counters and fail-closed behavior." },
  { id: "evidence-auth-keygen", path: "auth/src/auth_service/key_management.py", symbol: "generate_jwt_key_pair", description: "Non-overwriting Ed25519 private/public key generation." },
  { id: "evidence-auth-outbox-worker", path: "auth/src/auth_service/outbox_worker.py", symbol: "run", description: "Auth identity-event relay." },
  { id: "evidence-auth-cli", path: "auth/src/auth_service/maintenance.py", symbol: "cleanup_expired_data", description: "Auth cleanup maintenance operation." },
  { id: "evidence-auth-task", path: "auth/src/auth_service/tasks.py", symbol: "cleanup_expired_data_task", description: "Auth Celery maintenance task." },
  { id: "evidence-jwt-verifier", path: "shared/jwt_verifier/jwt_verifier/verifier.py", symbol: "JWTVerifier", description: "Verification-only Ed25519 JWT boundary for downstream services." },
  { id: "evidence-local-jwt-design", path: "docs/superpowers/specs/2026-07-31-local-jwt-authorization-design.md", symbol: "Verification-only component", description: "Accepted local authorization and revocation-latency decision." },
  { id: "evidence-catalog-models", path: "catalog/src/catalog/infrastructure/models.py", symbol: "CategoryModel / BrandModel / ProductModel / ProductVariantModel", description: "Catalog tables, constraints and indexes." },
  { id: "evidence-catalog-search", path: "catalog/src/catalog/infrastructure/search.py", symbol: "build_tsquery / search", description: "Bounded Russian FTS and trigram fallback query construction." },
  { id: "evidence-category-cache", path: "catalog/src/catalog/infrastructure/category_cache.py", symbol: "RedisCategoryTreeCache", description: "Category-tree read-through cache and invalidation." },
  { id: "evidence-inventory-models", path: "inventory/src/inventory/infrastructure/models.py", symbol: "StockModel / ReservationModel / OutboxEventModel / ProcessedEventModel", description: "Stock invariants, reservations, outbox and inbox." },
  { id: "evidence-stock-service", path: "inventory/src/inventory/application/services/stock.py", symbol: "StockService", description: "Reserve, bind, commit, release and expiry transaction boundaries." },
  { id: "evidence-stock-repo", path: "inventory/src/inventory/infrastructure/repositories/stock.py", symbol: "StockRepository", description: "Row locks, SKIP LOCKED expiry and drop advisory lock." },
  { id: "evidence-stock-cache", path: "inventory/src/inventory/infrastructure/stock_cache.py", symbol: "RedisStockCache", description: "Revision-aware Redis stock cache." },
  { id: "evidence-drop-policy", path: "inventory/src/inventory/infrastructure/drop_client.py", symbol: "DropClient.get_policy", description: "Fail-closed synchronous Drops policy lookup." },
  { id: "evidence-inventory-consumer", path: "inventory/src/inventory/event_consumer.py", symbol: "HANDLERS / process_message", description: "Inventory bindings for order and payment events." },
  { id: "evidence-inventory-outbox-worker", path: "inventory/src/inventory/outbox_worker.py", symbol: "run", description: "Inventory outbox relay." },
  { id: "evidence-inventory-expiry-worker", path: "inventory/src/inventory/tasks.py", symbol: "expire_reservations_task", description: "Reservation expiration Celery task." },
  { id: "evidence-orders-models", path: "orders/src/orders/infrastructure/models.py", symbol: "OrderModel / PromocodeModel / PromocodeUsageModel", description: "Order snapshots, promotion constraints, outbox and inbox." },
  { id: "evidence-order-service", path: "orders/src/orders/application/services/order.py", symbol: "OrderService", description: "Single/batch order transactions and event staging." },
  { id: "evidence-orders-consumer", path: "orders/src/orders/event_consumer.py", symbol: "HANDLERS / process_message", description: "Payment and reservation result handling." },
  { id: "evidence-orders-outbox-worker", path: "orders/src/orders/outbox_worker.py", symbol: "run", description: "Orders outbox relay." },
  { id: "evidence-payments-models", path: "payments/src/payments/infrastructure/models.py", symbol: "PaymentModel / OutboxEventModel / ProcessedEventModel", description: "Mock payment persistence and event state." },
  { id: "evidence-payment-service", path: "payments/src/payments/application/services/payment.py", symbol: "PaymentService", description: "Create and mock terminal payment transitions." },
  { id: "evidence-payments-consumer", path: "payments/src/payments/event_consumer.py", symbol: "handle_payment_requested", description: "Order PaymentRequested to mock payment projection." },
  { id: "evidence-payments-outbox-worker", path: "payments/src/payments/outbox_worker.py", symbol: "run", description: "Payments outbox relay." },
  { id: "evidence-notification-models", path: "notifications/src/notifications/infrastructure/models.py", symbol: "NotificationModel", description: "Notification read/delivery state and event-key deduplication." },
  { id: "evidence-notifications-consumer", path: "notifications/src/notifications/event_consumer.py", symbol: "HANDLERS", description: "Order and wishlist notification projections." },
  { id: "evidence-notifications-outbox-worker", path: "notifications/src/notifications/outbox_worker.py", symbol: "run", description: "Notifications outbox relay." },
  { id: "evidence-wishlist-models", path: "wishlist/src/wishlist/infrastructure/models.py", symbol: "WishlistItemModel / OutboxEventModel", description: "Wishlist uniqueness and per-user fan-out outbox." },
  { id: "evidence-wishlist-consumer", path: "wishlist/src/wishlist/event_consumer.py", symbol: "handle_drop_started", description: "Transactional DropStarted fan-out." },
  { id: "evidence-wishlist-repo", path: "wishlist/src/wishlist/infrastructure/repositories/wishlist.py", symbol: "stage_drop_notifications", description: "Unique drop/user event keys and nested-transaction deduplication." },
  { id: "evidence-wishlist-outbox-worker", path: "wishlist/src/wishlist/outbox_worker.py", symbol: "run", description: "Wishlist targeted-event relay." },
  { id: "evidence-drops-models", path: "drops/src/drops/infrastructure/models.py", symbol: "DropModel / DropItemModel / OutboxEventModel", description: "Drop schedule, policy constraints and lifecycle outbox." },
  { id: "evidence-drop-service", path: "drops/src/drops/application/services/drop.py", symbol: "DropService", description: "Lifecycle transitions and event payloads." },
  { id: "evidence-drop-scheduler", path: "drops/src/drops/scheduler.py", symbol: "run_scheduler_tick", description: "Locked one-shot due-drop start/end operation." },
  { id: "evidence-drop-task", path: "drops/src/drops/tasks.py", symbol: "run_scheduler_task", description: "Drops Celery lifecycle task." },
  { id: "evidence-drops-outbox-worker", path: "drops/src/drops/outbox_worker.py", symbol: "run", description: "Drop lifecycle outbox relay." },
  { id: "evidence-media-models", path: "media/src/media_service/infrastructure/models.py", symbol: "MediaAssetModel", description: "Media lifecycle metadata, constraints and cleanup indexes." },
  { id: "evidence-media-service", path: "media/src/media_service/application/services/assets.py", symbol: "AssetService", description: "Presign, completion validation, binding and deletion state transitions." },
  { id: "evidence-media-storage", path: "media/src/media_service/infrastructure/s3_storage.py", symbol: "S3ObjectStorage", description: "S3-compatible presign, HEAD, stream and delete boundary." },
  { id: "evidence-media-cleanup", path: "media/src/media_service/tasks.py", symbol: "cleanup_expired_assets_task", description: "Periodic expired/deleting object cleanup Celery task." },
  { id: "evidence-checkout-ui", path: "frontend/src/components/Checkout/CheckoutView.jsx", symbol: "handleSubmit", description: "Browser-orchestrated per-line reserve then batch order creation and rollback." },
  { id: "evidence-payment-ui", path: "frontend/src/components/Order/OrderDetailView.jsx", symbol: "handlePayment", description: "Current customer-driven mock payment confirmation flow." },
  { id: "evidence-frontend-api", path: "frontend/src/services/api.js", symbol: "apiJson", description: "Bearer token, single-flight refresh and request behavior." },
  { id: "evidence-prometheus", path: "deploy/prometheus/flashmarket-reliability.rules.yml", symbol: "groups", description: "RabbitMQ, outbox, DLQ and worker reliability alerts." },
  { id: "evidence-scrape-config", path: "deploy/prometheus/scrape-config.example.yml", symbol: "scrape_configs", description: "Example API and worker metrics discovery." },
  { id: "evidence-reliability-design", path: "docs/superpowers/specs/2026-08-13-rabbitmq-delivery-reliability-design.md", symbol: "full design", description: "Delivery guarantees, explicit non-goals and rollout rationale." },
  { id: "evidence-rabbit-runbook", path: "docs/runbooks/rabbitmq-reliability.md", symbol: "full runbook", description: "Operational checks, outbox diagnosis and guarded DLQ replay." },
  { id: "evidence-tests", path: "scripts/test_runner.py", symbol: "run_fast_tests / E2ERunner", description: "Repository test-suite registry and isolated saga runner." },
];

const technologies = [
  { id: "tech-fastapi", label: "FastAPI", category: "backend" },
  { id: "tech-python", label: "Python 3.14", category: "backend" },
  { id: "tech-sqlalchemy", label: "SQLAlchemy 2", category: "persistence" },
  { id: "tech-postgresql", label: "PostgreSQL", category: "database" },
  { id: "tech-redis", label: "Redis", category: "cache-state" },
  { id: "tech-rabbitmq", label: "RabbitMQ", category: "messaging" },
  { id: "tech-aio-pika", label: "aio-pika", category: "messaging" },
  { id: "tech-celery", label: "Celery 5.6", category: "task-execution" },
  { id: "tech-alembic", label: "Alembic", category: "persistence" },
  { id: "tech-react", label: "React 18", category: "frontend" },
  { id: "tech-vite", label: "Vite", category: "frontend-build" },
  { id: "tech-nginx", label: "Nginx", category: "edge" },
  { id: "tech-s3", label: "S3 / MinIO", category: "object-storage" },
  { id: "tech-prometheus", label: "Prometheus", category: "observability" },
  { id: "tech-docker", label: "Docker Compose", category: "runtime" },
  { id: "tech-ed25519", label: "Ed25519 JWT", category: "security" },
];

const infrastructure = [
  { id: "component-browser", name: "Browser", kind: "client", status: STATUS.IMPLEMENTED, summary: "React storefront/admin client; stores cart and current access token." },
  { id: "component-gateway", name: "Nginx Gateway", kind: "edge", status: STATUS.IMPLEMENTED, summary: "Public routing, local per-IP rate limits, trusted proxy handling and upstream timeouts.", evidenceIds: ["evidence-gateway"] },
  { id: "component-postgres", name: "PostgreSQL Cluster", kind: "database-cluster", status: STATUS.IMPLEMENTED, summary: "One external cluster containing nine service-owned logical databases.", evidenceIds: ["evidence-init-infra", "evidence-root-compose"] },
  { id: "component-redis", name: "Redis", kind: "cache-state", status: STATUS.IMPLEMENTED, summary: "External Redis split into DB 0/1/2 for Auth, Catalog and Inventory." },
  { id: "component-rabbitmq", name: "RabbitMQ", kind: "message-broker", status: STATUS.IMPLEMENTED, summary: "Integration events use /flashmarket; Celery commands use isolated /flashmarket-tasks.", evidenceIds: ["evidence-init-infra", "evidence-rabbit-topology", "evidence-celery-runtime"] },
  { id: "component-s3", name: "S3 / MinIO", kind: "object-storage", status: STATUS.IMPLEMENTED, summary: "Stores public media bytes; Media owns the corresponding metadata.", evidenceIds: ["evidence-media-storage"] },
  { id: "component-prometheus", name: "Prometheus", kind: "observability", status: STATUS.PARTIAL, summary: "Metrics and alert rules are present; the external production stack is outside this repository.", evidenceIds: ["evidence-prometheus", "evidence-scrape-config"] },
  { id: "component-celery", name: "Celery", kind: "task-framework", status: STATUS.IMPLEMENTED, summary: "Singleton Beat and four service-owned queues run periodic command jobs; domain events remain on aio-pika.", evidenceIds: ["evidence-celery-runtime", "evidence-celery-async", "evidence-celery-beat"] },
];

const services = [
  {
    id: "service-auth", slug: "auth", name: "Auth", status: STATUS.IMPLEMENTED,
    responsibility: "Identity, credentials, sessions, refresh rotation, RBAC source data, security audit and identity events.",
    owns: ["users", "password hashes", "roles and active status", "sessions", "refresh-token chains", "audit events", "identity outbox"],
    databaseId: "database-auth", redisUseCaseIds: ["redis-auth-session", "redis-auth-touch", "redis-auth-rate"],
    layerIds: ["api", "application", "domain", "persistence", "messaging", "workers"],
    endpointIds: ["endpoint-auth-register", "endpoint-auth-login", "endpoint-auth-refresh", "endpoint-auth-logout", "endpoint-auth-profile", "endpoint-auth-sessions", "endpoint-auth-admin"],
    publishesEventIds: ["event-user-registered", "event-user-logged-in", "event-token-refreshed", "event-refresh-token-reuse", "event-user-logged-out", "event-profile-updated", "event-password-changed", "event-user-role-changed", "event-user-status-changed", "event-session-revoked", "event-all-sessions-revoked"],
    consumesEventIds: [], workerIds: ["worker-auth-outbox", "worker-auth-cleanup"],
    decisionIds: ["highlight-key-isolation", "highlight-refresh-rotation", "highlight-failure-policy"],
    evidenceIds: ["evidence-auth-models", "evidence-auth-security", "evidence-auth-app", "evidence-auth-cache", "evidence-auth-rate"]
  },
  {
    id: "service-catalog", slug: "catalog", name: "Catalog", status: STATUS.IMPLEMENTED,
    responsibility: "Products, categories, brands, variants, public visibility and search.",
    owns: ["categories", "brands", "products", "product images", "SKU variants", "search projection"],
    databaseId: "database-catalog", redisUseCaseIds: ["redis-category-tree"],
    layerIds: ["api", "application", "domain", "infrastructure", "persistence"],
    endpointIds: ["endpoint-products-list", "endpoint-products-detail", "endpoint-products-batch", "endpoint-products-admin", "endpoint-categories", "endpoint-brands", "endpoint-variants"],
    publishesEventIds: [], consumesEventIds: [], workerIds: [],
    decisionIds: ["highlight-failure-policy"],
    evidenceIds: ["evidence-catalog-models", "evidence-catalog-search", "evidence-category-cache"]
  },
  {
    id: "service-inventory", slug: "inventory", name: "Inventory", status: STATUS.IMPLEMENTED,
    responsibility: "Stock authority, reservations, drop purchase enforcement, expiry and inventory state events.",
    owns: ["stock counters", "reservations", "reservation expiry", "inventory outbox and inbox"],
    databaseId: "database-inventory", redisUseCaseIds: ["redis-stock"],
    layerIds: ["api", "application", "domain", "infrastructure", "persistence", "messaging", "workers"],
    endpointIds: ["endpoint-stock-read", "endpoint-stock-admin", "endpoint-stock-reserve", "endpoint-stock-release", "endpoint-stock-commit"],
    publishesEventIds: ["event-inventory-reserved", "event-inventory-committed", "event-reservation-released"],
    consumesEventIds: ["event-order-created", "event-payment-succeeded", "event-payment-failed", "event-order-cancelled"],
    workerIds: ["worker-inventory-consumer", "worker-inventory-outbox", "worker-inventory-expiry"],
    decisionIds: ["highlight-stock-lock", "highlight-drop-advisory-lock", "highlight-revision-cache"],
    evidenceIds: ["evidence-inventory-models", "evidence-stock-service", "evidence-stock-repo", "evidence-stock-cache", "evidence-drop-policy"]
  },
  {
    id: "service-orders", slug: "orders", name: "Orders", status: STATUS.PARTIAL,
    responsibility: "Order lifecycle, checkout snapshots, promocodes and purchase-saga orchestration through events.",
    owns: ["orders", "checkout grouping", "commercial snapshots", "promocodes", "promocode usage", "order outbox and inbox"],
    databaseId: "database-orders", redisUseCaseIds: [],
    layerIds: ["api", "application", "domain", "infrastructure", "persistence", "messaging", "workers"],
    endpointIds: ["endpoint-order-create", "endpoint-order-batch", "endpoint-order-read", "endpoint-order-transition", "endpoint-promocodes"],
    publishesEventIds: ["event-order-created", "event-payment-requested", "event-order-confirmed", "event-order-cancelled"],
    consumesEventIds: ["event-payment-succeeded", "event-payment-failed", "event-reservation-released"],
    workerIds: ["worker-orders-consumer", "worker-orders-outbox"],
    decisionIds: ["highlight-batch-checkout", "highlight-inbox-outbox"],
    limitations: ["Request price and product snapshot are not verified against an authoritative server-side quote.", "reservation_id is indexed but not unique."],
    evidenceIds: ["evidence-orders-models", "evidence-order-service", "evidence-orders-consumer"]
  },
  {
    id: "service-payments", slug: "payments", name: "Payments", status: STATUS.PARTIAL,
    responsibility: "Mock payment attempts and payment result events.",
    owns: ["payment attempts", "mock provider status", "payment expiry field", "payment outbox and inbox"],
    databaseId: "database-payments", redisUseCaseIds: [],
    layerIds: ["api", "application", "domain", "infrastructure", "persistence", "messaging", "workers"],
    endpointIds: ["endpoint-payment-create", "endpoint-payment-read", "endpoint-payment-transition"],
    publishesEventIds: ["event-payment-succeeded", "event-payment-failed", "event-payment-cancelled"],
    consumesEventIds: ["event-payment-requested"], workerIds: ["worker-payments-consumer", "worker-payments-outbox"],
    decisionIds: ["highlight-inbox-outbox"],
    limitations: ["No PSP adapter, signed webhook, capture, refund or reconciliation.", "Customers currently drive mock terminal transitions.", "order_id is not unique."],
    evidenceIds: ["evidence-payments-models", "evidence-payment-service", "evidence-payments-consumer", "evidence-payment-ui"]
  },
  {
    id: "service-notifications", slug: "notifications", name: "Notifications", status: STATUS.PARTIAL,
    responsibility: "Per-user notification projection, read state and demo delivery state.",
    owns: ["notification records", "read state", "delivery state", "attachment URL", "notification outbox and inbox"],
    databaseId: "database-notifications", redisUseCaseIds: [],
    layerIds: ["api", "application", "domain", "infrastructure", "persistence", "messaging", "workers"],
    endpointIds: ["endpoint-notification-list", "endpoint-notification-read", "endpoint-notification-transition"],
    publishesEventIds: ["event-notification-sent"],
    consumesEventIds: ["event-order-created", "event-order-confirmed", "event-order-cancelled", "event-drop-available"],
    workerIds: ["worker-notifications-consumer", "worker-notifications-outbox"],
    decisionIds: ["highlight-inbox-outbox"], limitations: ["SMTP settings exist but no physical delivery worker/client is implemented."],
    evidenceIds: ["evidence-notification-models", "evidence-notifications-consumer"]
  },
  {
    id: "service-wishlist", slug: "wishlist", name: "Wishlist", status: STATUS.IMPLEMENTED,
    responsibility: "Wishlist membership and durable targeted fan-out when a drop starts.",
    owns: ["user-product wishlist membership", "per-user DropAvailable outbox keys", "wishlist inbox"],
    databaseId: "database-wishlist", redisUseCaseIds: [],
    layerIds: ["api", "application", "domain", "infrastructure", "persistence", "messaging", "workers"],
    endpointIds: ["endpoint-wishlist-items", "endpoint-wishlist-check"], publishesEventIds: ["event-drop-available"],
    consumesEventIds: ["event-drop-started"], workerIds: ["worker-wishlist-consumer", "worker-wishlist-outbox"],
    decisionIds: ["highlight-wishlist-fanout", "highlight-inbox-outbox"],
    evidenceIds: ["evidence-wishlist-models", "evidence-wishlist-consumer", "evidence-wishlist-repo"]
  },
  {
    id: "service-drops", slug: "drops", name: "Drops", status: STATUS.IMPLEMENTED,
    responsibility: "Flash-sale schedule, product membership, purchase policy and lifecycle events.",
    owns: ["drops", "drop items", "schedule", "per-user limit", "payment timeout policy", "drop outbox"],
    databaseId: "database-drops", redisUseCaseIds: [],
    layerIds: ["api", "application", "domain", "infrastructure", "persistence", "messaging", "workers"],
    endpointIds: ["endpoint-drop-public", "endpoint-drop-policy", "endpoint-drop-admin"],
    publishesEventIds: ["event-drop-scheduled", "event-drop-started", "event-drop-ended", "event-drop-cancelled"],
    consumesEventIds: [], workerIds: ["worker-drops-scheduler", "worker-drops-outbox"],
    decisionIds: ["highlight-wishlist-fanout"], limitations: ["Due rows are not locked, so multiple scheduler replicas can stage duplicate lifecycle events."],
    evidenceIds: ["evidence-drops-models", "evidence-drop-service", "evidence-drop-scheduler"]
  },
  {
    id: "service-media", slug: "media", name: "Media", status: STATUS.IMPLEMENTED,
    responsibility: "Direct upload authorization, authoritative media metadata, validation, binding and deletion lifecycle.",
    owns: ["media asset metadata", "upload lifecycle", "ownership and purpose", "checksum and validation result"],
    databaseId: "database-media", objectStorageId: "component-s3", redisUseCaseIds: [],
    layerIds: ["api", "application", "domain-policy", "infrastructure", "persistence", "workers"],
    endpointIds: ["endpoint-media-upload", "endpoint-media-complete", "endpoint-media-bind", "endpoint-media-delete", "endpoint-media-read"],
    publishesEventIds: [], consumesEventIds: [], workerIds: ["worker-media-cleanup"],
    decisionIds: ["highlight-media-validation"], limitations: ["Quota checks can race.", "External S3 I/O occurs while an asset row lock is held."],
    evidenceIds: ["evidence-media-models", "evidence-media-service", "evidence-media-storage", "evidence-media-cleanup"]
  },
];

const endpoints = [
  { id: "endpoint-auth-register", serviceId: "service-auth", method: "POST", path: "/api/v1/auth/register", access: "anonymous", summary: "Create a user, session and refresh chain." },
  { id: "endpoint-auth-login", serviceId: "service-auth", method: "POST", path: "/api/v1/auth/login", access: "anonymous", summary: "Authenticate, create a session and issue tokens." },
  { id: "endpoint-auth-refresh", serviceId: "service-auth", method: "POST", path: "/api/v1/auth/refresh", access: "refresh-cookie+csrf", summary: "Rotate a one-time refresh token and issue a new access token." },
  { id: "endpoint-auth-logout", serviceId: "service-auth", method: "POST", path: "/api/v1/auth/logout", access: "authenticated", summary: "Revoke the current session and clear token cookies." },
  { id: "endpoint-auth-profile", serviceId: "service-auth", method: "GET/PATCH", path: "/api/v1/users/me", access: "authenticated", summary: "Read or update the current profile." },
  { id: "endpoint-auth-sessions", serviceId: "service-auth", method: "GET/DELETE", path: "/api/v1/sessions[/{session_id}]", access: "authenticated", summary: "List or revoke one/all owned sessions." },
  { id: "endpoint-auth-admin", serviceId: "service-auth", method: "GET/PATCH", path: "/api/v1/admin/users/* and /audit-events", access: "admin", summary: "Manage roles/status and inspect audit events." },

  { id: "endpoint-products-list", serviceId: "service-catalog", method: "GET", path: "/api/v1/products", access: "anonymous", summary: "Filter, search, sort and paginate ACTIVE products." },
  { id: "endpoint-products-detail", serviceId: "service-catalog", method: "GET", path: "/api/v1/products/{slug}", access: "anonymous", summary: "Read product detail; UUID handling has a documented visibility gap." },
  { id: "endpoint-products-batch", serviceId: "service-catalog", method: "POST", path: "/api/v1/products/batch", access: "anonymous", summary: "Hydrate up to 100 ACTIVE products by ID." },
  { id: "endpoint-products-admin", serviceId: "service-catalog", method: "POST/PATCH/DELETE", path: "/api/v1/products[/{product_id}]", access: "admin", summary: "Create, update or archive a product." },
  { id: "endpoint-categories", serviceId: "service-catalog", method: "GET/POST", path: "/api/v1/categories", access: "anonymous-read/admin-write", summary: "Read the cached category tree or create a category." },
  { id: "endpoint-brands", serviceId: "service-catalog", method: "GET/POST/PATCH", path: "/api/v1/brands/*", access: "anonymous-read/admin-write", summary: "Read and manage brands." },
  { id: "endpoint-variants", serviceId: "service-catalog", method: "GET/POST/PATCH/DELETE", path: "/api/v1/products/{product_id}/variants/*", access: "anonymous-read/admin-write", summary: "Read and manage SKU variants." },

  { id: "endpoint-stock-read", serviceId: "service-inventory", method: "GET", path: "/api/v1/stocks/{product_id}", access: "anonymous", summary: "Read stock, with Redis read-through cache." },
  { id: "endpoint-stock-admin", serviceId: "service-inventory", method: "POST/PATCH", path: "/api/v1/stocks/{product_id}", access: "admin", summary: "Create/reset or change total stock." },
  { id: "endpoint-stock-reserve", serviceId: "service-inventory", method: "POST", path: "/api/v1/stocks/{product_id}/reserve", access: "owner-or-admin", summary: "Lock stock and create an expiring reservation." },
  { id: "endpoint-stock-release", serviceId: "service-inventory", method: "POST", path: "/api/v1/stocks/{product_id}/release", access: "owner-or-admin", summary: "Release a reservation and restore available stock." },
  { id: "endpoint-stock-commit", serviceId: "service-inventory", method: "POST", path: "/api/v1/stocks/{product_id}/commit", access: "admin", summary: "Convert a reservation into sold stock." },

  { id: "endpoint-order-create", serviceId: "service-orders", method: "POST", path: "/api/v1/orders", access: "owner-or-admin", summary: "Create an order from one reservation." },
  { id: "endpoint-order-batch", serviceId: "service-orders", method: "POST", path: "/api/v1/orders/batch", access: "owner-or-admin", summary: "Atomically create a checkout from reserved lines and apply a promocode." },
  { id: "endpoint-order-read", serviceId: "service-orders", method: "GET", path: "/api/v1/orders/{order_id} and /users/{user_id}", access: "owner-or-admin", summary: "Read an order or user order list." },
  { id: "endpoint-order-transition", serviceId: "service-orders", method: "POST", path: "/api/v1/orders/{order_id}/confirm|fail", access: "owner-or-admin", summary: "Current mock-compatible order terminal transitions." },
  { id: "endpoint-promocodes", serviceId: "service-orders", method: "GET/POST/PATCH", path: "/api/v1/promocodes/*", access: "admin; validation authenticated", summary: "Manage and validate promocodes." },

  { id: "endpoint-payment-create", serviceId: "service-payments", method: "POST", path: "/api/v1/payments", access: "owner-or-admin", summary: "Create a mock payment for an order." },
  { id: "endpoint-payment-read", serviceId: "service-payments", method: "GET", path: "/api/v1/payments/{payment_id} and /users/{user_id}", access: "owner-or-admin", summary: "Read a payment or user payment list." },
  { id: "endpoint-payment-transition", serviceId: "service-payments", method: "POST", path: "/api/v1/payments/{payment_id}/confirm|fail|cancel", access: "owner-or-admin", summary: "Drive the current mock payment terminal state." },

  { id: "endpoint-notification-list", serviceId: "service-notifications", method: "GET", path: "/api/v1/notifications/users/{user_id}", access: "owner-or-admin", summary: "List a user's notifications." },
  { id: "endpoint-notification-read", serviceId: "service-notifications", method: "POST", path: "/api/v1/notifications/{notification_id}/read", access: "owner-or-admin", summary: "Mark a notification read." },
  { id: "endpoint-notification-transition", serviceId: "service-notifications", method: "POST", path: "/api/v1/notifications/{notification_id}/send|fail", access: "owner-or-admin send; admin fail", summary: "Change demo delivery state; no SMTP side effect." },

  { id: "endpoint-wishlist-items", serviceId: "service-wishlist", method: "GET/POST/DELETE", path: "/api/v1/wishlist/users/{user_id}/items/*", access: "owner-or-admin", summary: "List, add or remove wishlist membership." },
  { id: "endpoint-wishlist-check", serviceId: "service-wishlist", method: "POST", path: "/api/v1/wishlist/users/{user_id}/check", access: "owner-or-admin", summary: "Check a bounded product set for membership." },

  { id: "endpoint-drop-public", serviceId: "service-drops", method: "GET", path: "/api/v1/drops/active|upcoming|{slug}", access: "anonymous", summary: "Discover public active/upcoming drops and detail." },
  { id: "endpoint-drop-policy", serviceId: "service-drops", method: "GET", path: "/api/v1/drops/id/{drop_id}", access: "anonymous/internal-caller", summary: "Provide Inventory with current drop policy and product membership." },
  { id: "endpoint-drop-admin", serviceId: "service-drops", method: "GET/POST/PATCH/DELETE", path: "/api/v1/admin/drops/*", access: "admin", summary: "Manage drop definition, items and lifecycle." },

  { id: "endpoint-media-upload", serviceId: "service-media", method: "POST", path: "/api/v1/media/uploads", access: "authenticated", summary: "Create metadata and an exact presigned S3 POST." },
  { id: "endpoint-media-complete", serviceId: "service-media", method: "POST", path: "/api/v1/media/assets/{asset_id}/complete", access: "owner-or-admin", summary: "Validate uploaded object and mark it READY." },
  { id: "endpoint-media-bind", serviceId: "service-media", method: "PATCH", path: "/api/v1/media/assets/{asset_id}/binding", access: "policy-dependent", summary: "Bind a READY asset to an allowed entity/purpose." },
  { id: "endpoint-media-delete", serviceId: "service-media", method: "DELETE", path: "/api/v1/media/assets/{asset_id}", access: "owner-or-admin", summary: "Request asynchronous object deletion." },
  { id: "endpoint-media-read", serviceId: "service-media", method: "GET", path: "/api/v1/media/assets/* and /entities/*", access: "owner/admin/public-by-policy", summary: "Read owned/admin assets or public entity assets." },
].map((item) => ({ ...item, status: STATUS.IMPLEMENTED, evidenceIds: ["evidence-openapi"] }));

const databases = [
  { id: "database-auth", serviceId: "service-auth", name: "auth", clusterId: "component-postgres", tableIds: ["table-users", "table-sessions", "table-refresh-tokens", "table-audit-events", "table-auth-outbox"] },
  { id: "database-catalog", serviceId: "service-catalog", name: "catalog", clusterId: "component-postgres", tableIds: ["table-categories", "table-brands", "table-products", "table-product-images", "table-product-variants"] },
  { id: "database-inventory", serviceId: "service-inventory", name: "inventory", clusterId: "component-postgres", tableIds: ["table-stocks", "table-reservations", "table-inventory-outbox", "table-inventory-inbox"] },
  { id: "database-orders", serviceId: "service-orders", name: "orders", clusterId: "component-postgres", tableIds: ["table-orders", "table-promocodes", "table-promocode-usages", "table-orders-outbox", "table-orders-inbox"] },
  { id: "database-payments", serviceId: "service-payments", name: "payments", clusterId: "component-postgres", tableIds: ["table-payments", "table-payments-outbox", "table-payments-inbox"] },
  { id: "database-notifications", serviceId: "service-notifications", name: "notifications", clusterId: "component-postgres", tableIds: ["table-notifications", "table-notifications-outbox", "table-notifications-inbox"] },
  { id: "database-wishlist", serviceId: "service-wishlist", name: "wishlist", clusterId: "component-postgres", tableIds: ["table-wishlist-items", "table-wishlist-outbox", "table-wishlist-inbox"] },
  { id: "database-drops", serviceId: "service-drops", name: "drops", clusterId: "component-postgres", tableIds: ["table-drops", "table-drop-items", "table-drops-outbox"] },
  { id: "database-media", serviceId: "service-media", name: "media", clusterId: "component-postgres", tableIds: ["table-media-assets"] },
].map((item) => ({ ...item, status: STATUS.IMPLEMENTED }));

const tables = [
  { id: "table-users", databaseId: "database-auth", name: "users", purpose: "Identity, normalized email, Argon2id hash, role and active state.", constraintIds: ["constraint-user-email"] },
  { id: "table-sessions", databaseId: "database-auth", name: "sessions", purpose: "Server-side login sessions and revocation state.", indexIds: ["index-session-user-created"] },
  { id: "table-refresh-tokens", databaseId: "database-auth", name: "refresh_tokens", purpose: "Hash-only one-time refresh chain.", constraintIds: ["constraint-refresh-hash"], indexIds: ["index-refresh-session-created"] },
  { id: "table-audit-events", databaseId: "database-auth", name: "audit_events", purpose: "Security and administration audit trail.", indexIds: ["index-audit-type-created", "index-audit-actor-created", "index-audit-subject-created"] },
  { id: "table-auth-outbox", databaseId: "database-auth", name: "outbox_events", purpose: "Durable identity integration event intent.", indexIds: ["index-auth-outbox-due"] },

  { id: "table-categories", databaseId: "database-catalog", name: "categories", purpose: "Hierarchical category source of truth.", constraintIds: ["constraint-category-slug"] },
  { id: "table-brands", databaseId: "database-catalog", name: "brands", purpose: "Brand source of truth.", constraintIds: ["constraint-brand-slug"] },
  { id: "table-products", databaseId: "database-catalog", name: "products", purpose: "Product content, price and visibility.", constraintIds: ["constraint-product-price", "constraint-product-slug"], indexIds: ["index-product-category-status", "index-product-brand-status", "index-product-fts", "index-product-trigram"] },
  { id: "table-product-images", databaseId: "database-catalog", name: "product_images", purpose: "Ordered product image references." },
  { id: "table-product-variants", databaseId: "database-catalog", name: "product_variants", purpose: "SKU, size and color variants.", constraintIds: ["constraint-variant-tuple", "constraint-variant-sku"], indexIds: ["index-variant-product-active"] },

  { id: "table-stocks", databaseId: "database-inventory", name: "stocks", purpose: "Authoritative total/available/reserved/sold counters and cache revision.", constraintIds: ["constraint-stock-counters", "constraint-stock-variant"], indexIds: ["index-stock-product-variant"] },
  { id: "table-reservations", databaseId: "database-inventory", name: "reservations", purpose: "Expiring reservation state and order/drop association.", indexIds: ["index-reservation-status-expiry", "index-reservation-drop-user"] },
  { id: "table-inventory-outbox", databaseId: "database-inventory", name: "outbox_events", purpose: "Durable inventory events.", indexIds: ["index-inventory-outbox-due"] },
  { id: "table-inventory-inbox", databaseId: "database-inventory", name: "processed_events", purpose: "Consumer event deduplication by event ID." },

  { id: "table-orders", databaseId: "database-orders", name: "orders", purpose: "Order lifecycle and immutable checkout/product/price snapshot.", constraintIds: ["constraint-order-values"], indexIds: ["index-order-reservation", "index-order-checkout"] },
  { id: "table-promocodes", databaseId: "database-orders", name: "promocodes", purpose: "Promotion policy and usage counters.", constraintIds: ["constraint-promocode-values"] },
  { id: "table-promocode-usages", databaseId: "database-orders", name: "promocode_usages", purpose: "Per-order and per-user promotion usage.", constraintIds: ["constraint-promo-usage"], indexIds: ["index-promo-user"] },
  { id: "table-orders-outbox", databaseId: "database-orders", name: "outbox_events", purpose: "Durable order and payment-request events.", indexIds: ["index-orders-outbox-due"] },
  { id: "table-orders-inbox", databaseId: "database-orders", name: "processed_events", purpose: "Consumer event deduplication by event ID." },

  { id: "table-payments", databaseId: "database-payments", name: "payments", purpose: "Mock payment attempt and status.", constraintIds: ["constraint-payment-amount"], indexIds: ["index-payment-order-user"] },
  { id: "table-payments-outbox", databaseId: "database-payments", name: "outbox_events", purpose: "Durable payment result events.", indexIds: ["index-payments-outbox-due"] },
  { id: "table-payments-inbox", databaseId: "database-payments", name: "processed_events", purpose: "Consumer event deduplication by event ID." },

  { id: "table-notifications", databaseId: "database-notifications", name: "notifications", purpose: "Per-user message, read state, delivery state and event key.", constraintIds: ["constraint-notification-event-key"], indexIds: ["index-notification-user"] },
  { id: "table-notifications-outbox", databaseId: "database-notifications", name: "outbox_events", purpose: "Durable NotificationSent events.", indexIds: ["index-notifications-outbox-due"] },
  { id: "table-notifications-inbox", databaseId: "database-notifications", name: "processed_events", purpose: "Consumer event deduplication by event ID." },

  { id: "table-wishlist-items", databaseId: "database-wishlist", name: "wishlist_items", purpose: "User-to-product wishlist membership.", constraintIds: ["constraint-wishlist-pair"], indexIds: ["index-wishlist-user-created"] },
  { id: "table-wishlist-outbox", databaseId: "database-wishlist", name: "outbox_events", purpose: "Unique per-drop/per-user notification fan-out.", constraintIds: ["constraint-wishlist-event-key"], indexIds: ["index-wishlist-outbox-due"] },
  { id: "table-wishlist-inbox", databaseId: "database-wishlist", name: "processed_events", purpose: "DropStarted consumer deduplication." },

  { id: "table-drops", databaseId: "database-drops", name: "drops", purpose: "Drop schedule and purchase policy.", constraintIds: ["constraint-drop-policy"], indexIds: ["index-drop-status-start"] },
  { id: "table-drop-items", databaseId: "database-drops", name: "drop_items", purpose: "Products participating in a drop.", constraintIds: ["constraint-drop-product"] },
  { id: "table-drops-outbox", databaseId: "database-drops", name: "outbox_events", purpose: "Durable lifecycle events.", indexIds: ["index-drops-outbox-due"] },

  { id: "table-media-assets", databaseId: "database-media", name: "media_assets", purpose: "Upload, validation, binding and deletion metadata.", constraintIds: ["constraint-media-size"], indexIds: ["index-media-entity", "index-media-expiration", "index-media-deletion"] },
].map((item) => ({ ...item, status: STATUS.IMPLEMENTED }));

const constraints = [
  { id: "constraint-user-email", tableId: "table-users", kind: "check+unique", columns: ["email"], rule: "email = lower(trim(email)); email unique", why: "Makes normalized email identity a database invariant." },
  { id: "constraint-refresh-hash", tableId: "table-refresh-tokens", kind: "unique", columns: ["token_hash"], rule: "one stored digest", why: "Prevents two rows representing the same refresh secret." },
  { id: "constraint-category-slug", tableId: "table-categories", kind: "unique", columns: ["slug"], rule: "unique category slug", why: "Stable public category identity." },
  { id: "constraint-brand-slug", tableId: "table-brands", kind: "unique", columns: ["slug"], rule: "unique brand slug", why: "Stable public brand identity." },
  { id: "constraint-product-price", tableId: "table-products", kind: "check", columns: ["price"], rule: "price > 0", why: "Rejects invalid persisted product price." },
  { id: "constraint-product-slug", tableId: "table-products", kind: "unique", columns: ["slug"], rule: "unique product slug", why: "Stable public product identity." },
  { id: "constraint-variant-tuple", tableId: "table-product-variants", kind: "unique", columns: ["product_id", "size", "color"], rule: "one option tuple per product", why: "Prevents duplicate selectable variants." },
  { id: "constraint-variant-sku", tableId: "table-product-variants", kind: "unique", columns: ["sku"], rule: "SKU unique", why: "Guarantees SKU identity." },
  { id: "constraint-stock-counters", tableId: "table-stocks", kind: "checks", columns: ["total", "available", "reserved", "sold"], rule: "all >= 0 and reserved + sold <= total", why: "Last-line stock invariant even if application logic regresses." },
  { id: "constraint-stock-variant", tableId: "table-stocks", kind: "unique-with-gap", columns: ["product_id", "variant_id"], rule: "unique pair", why: "Protects non-null SKU stock; PostgreSQL NULL semantics leave default stock partially protected.", status: STATUS.PARTIAL },
  { id: "constraint-order-values", tableId: "table-orders", kind: "checks", columns: ["quantity", "price"], rule: "quantity > 0 and price > 0", why: "Rejects invalid persisted line snapshots." },
  { id: "constraint-promocode-values", tableId: "table-promocodes", kind: "checks", columns: ["discount_value", "current_uses", "starts_at", "expires_at"], rule: "positive value, non-negative uses, valid period", why: "Keeps promotion policy internally valid." },
  { id: "constraint-promo-usage", tableId: "table-promocode-usages", kind: "unique", columns: ["promocode_id", "order_id"], rule: "one usage per promo/order and one usage row per order", why: "Database idempotency for promotion consumption." },
  { id: "constraint-payment-amount", tableId: "table-payments", kind: "check", columns: ["amount"], rule: "amount > 0", why: "Rejects zero/negative persisted payment attempts." },
  { id: "constraint-notification-event-key", tableId: "table-notifications", kind: "unique", columns: ["event_key"], rule: "unique when supplied", why: "Deduplicates targeted drop notifications." },
  { id: "constraint-wishlist-pair", tableId: "table-wishlist-items", kind: "unique", columns: ["user_id", "product_id"], rule: "one membership row", why: "Concurrent duplicate add cannot create duplicate membership." },
  { id: "constraint-wishlist-event-key", tableId: "table-wishlist-outbox", kind: "unique", columns: ["event_key"], rule: "drop:{drop}:user:{user}", why: "Makes fan-out restart/redelivery safe." },
  { id: "constraint-drop-policy", tableId: "table-drops", kind: "checks", columns: ["starts_at", "ends_at", "max_per_user", "payment_timeout_seconds"], rule: "end after start, limit >= 1, timeout >= 60", why: "Persisted drop policy is always actionable." },
  { id: "constraint-drop-product", tableId: "table-drop-items", kind: "unique", columns: ["drop_id", "product_id"], rule: "one product membership", why: "No duplicate product in one drop." },
  { id: "constraint-media-size", tableId: "table-media-assets", kind: "checks", columns: ["expected_size", "actual_size"], rule: "positive expected/actual sizes", why: "Rejects nonsensical persisted upload metadata." },
].map((item) => ({ status: STATUS.IMPLEMENTED, ...item }));

const indexes = [
  { id: "index-auth-outbox-due", tableId: "table-auth-outbox", columns: ["published_at", "next_attempt_at", "occurred_at"], query: "unpublished and due identity events ordered oldest first", whyOrder: "Null/equality delivery predicates precede chronological ordering.", without: "Relay scans and sorts growing history.", status: STATUS.IMPLEMENTED },
  { id: "index-session-user-created", tableId: "table-sessions", columns: ["user_id", "created_at"], query: "list a user's sessions chronologically", whyOrder: "User equality narrows before time ordering.", without: "Per-user session list scans all sessions." },
  { id: "index-refresh-session-created", tableId: "table-refresh-tokens", columns: ["session_id", "created_at"], query: "inspect/clean refresh chain for a session", whyOrder: "Session equality is selective; creation time orders the chain.", without: "Refresh-chain work scans unrelated tokens." },
  { id: "index-audit-type-created", tableId: "table-audit-events", columns: ["event_type", "created_at"], query: "filter audit by type and time", whyOrder: "Type filter before timeline.", without: "Admin investigations scan full audit history." },
  { id: "index-audit-actor-created", tableId: "table-audit-events", columns: ["actor_user_id", "created_at"], query: "actor audit timeline", whyOrder: "Actor equality before time.", without: "Actor lookup scans all events." },
  { id: "index-audit-subject-created", tableId: "table-audit-events", columns: ["subject_user_id", "created_at"], query: "subject audit timeline", whyOrder: "Subject equality before time.", without: "Subject lookup scans all events." },
  { id: "index-product-category-status", tableId: "table-products", columns: ["category_id", "status"], query: "public products in a category", whyOrder: "Optional category narrows first; status applies visibility.", without: "Category pages filter more product rows." },
  { id: "index-product-brand-status", tableId: "table-products", columns: ["brand_id", "status"], query: "public products for a brand", whyOrder: "Brand equality before status.", without: "Brand pages filter more product rows." },
  { id: "index-product-fts", tableId: "table-products", columns: ["weighted Russian tsvector(name, description)"], method: "GIN", query: "prefix full-text search with weighted rank", whyOrder: "Expression matches the query expression exactly.", without: "Search computes vectors and scans products." },
  { id: "index-product-trigram", tableId: "table-products", columns: ["name gin_trgm_ops"], method: "GIN", query: "trigram fallback for imperfect names", whyOrder: "Operator class matches similarity lookup.", without: "Fallback similarity scans names." },
  { id: "index-variant-product-active", tableId: "table-product-variants", columns: ["product_id", "is_active"], query: "list active variants for product detail", whyOrder: "Product equality narrows before active flag.", without: "Variant list scans unrelated products." },
  { id: "index-stock-product-variant", tableId: "table-stocks", columns: ["product_id", "variant_id"], unique: true, query: "exact stock authority lookup", whyOrder: "Product then optional SKU matches repository predicate.", without: "Reserve lookup is slower and non-null duplicates possible.", status: STATUS.PARTIAL },
  { id: "index-reservation-status-expiry", tableId: "table-reservations", columns: ["status", "expires_at"], query: "oldest RESERVED rows whose expiry is due", whyOrder: "Equality status precedes range/time ordering.", without: "Expiry worker scans committed/released history." },
  { id: "index-reservation-drop-user", tableId: "table-reservations", kind: "index-group", columns: ["drop_id (single-column)", "user_id (single-column)"], query: "sum active/committed quantity for one drop/user", whyOrder: "These are separate indexes, not an ordered composite index; PostgreSQL may combine them for the two predicates.", without: "Limit enforcement has no indexed entry for the drop/user filters." },
  { id: "index-order-reservation", tableId: "table-orders", columns: ["reservation_id"], query: "find existing/order-by-reservation", whyOrder: "Single equality lookup.", without: "Saga correlation scans orders.", status: STATUS.PARTIAL, limitation: "Not unique, so it does not close concurrent duplicate create." },
  { id: "index-order-checkout", tableId: "table-orders", columns: ["checkout_id"], query: "group lines from one checkout", whyOrder: "Single equality lookup.", without: "Checkout detail scans orders." },
  { id: "index-promo-user", tableId: "table-promocode-usages", columns: ["promocode_id", "user_id"], query: "count one user's uses of one promo", whyOrder: "Promo then user matches limit query.", without: "Per-user limit scans usage history." },
  { id: "index-payment-order-user", tableId: "table-payments", kind: "index-group", columns: ["order_id (single-column)", "user_id (single-column)"], query: "find payment for order and list user history", whyOrder: "These are separate lookup indexes; no composite column order is claimed.", without: "Payment lookup/history scans attempts.", status: STATUS.PARTIAL, limitation: "order_id is indexed, not unique." },
  { id: "index-notification-user", tableId: "table-notifications", columns: ["user_id"], query: "list a user's notification inbox", whyOrder: "Owner equality is the dominant predicate.", without: "Inbox reads scan all users." },
  { id: "index-wishlist-user-created", tableId: "table-wishlist-items", columns: ["user_id", "created_at"], query: "newest wishlist items for one user", whyOrder: "User equality before time order.", without: "Profile wishlist scans all memberships." },
  { id: "index-drop-status-start", tableId: "table-drops", kind: "index-group", columns: ["status (single-column)", "starts_at (single-column)"], query: "active/upcoming/due drop discovery", whyOrder: "These are separate indexes, so no composite column order is implied.", without: "Scheduler/public lists scan all drops." },
  { id: "index-media-entity", tableId: "table-media-assets", columns: ["entity_type", "entity_id", "purpose", "status"], query: "public READY assets bound to an entity/purpose", whyOrder: "Entity identity precedes purpose and lifecycle state.", without: "Product/drop media reads scan asset history." },
  { id: "index-media-expiration", tableId: "table-media-assets", columns: ["status", "upload_expires_at"], query: "expired PENDING upload candidates", whyOrder: "Lifecycle equality before due-time range.", without: "Cleanup scans READY/deleted assets." },
  { id: "index-media-deletion", tableId: "table-media-assets", columns: ["status", "delete_requested_at"], query: "DELETING candidates ordered by request time", whyOrder: "Lifecycle equality before due-time ordering.", without: "Deletion cleanup scans the asset table." },
  ...["inventory", "orders", "payments", "notifications", "drops"].map((service) => ({
    id: `index-${service}-outbox-due`, tableId: `table-${service}-outbox`,
    columns: ["status", "next_attempt_at", "created_at"],
    query: "pending/failed due outbox rows ordered oldest first",
    whyOrder: "Delivery state and due time filter before chronological selection.",
    without: "Relay repeatedly scans and sorts published history.", status: STATUS.IMPLEMENTED,
  })),
  { id: "index-wishlist-outbox-due", tableId: "table-wishlist-outbox", columns: ["status", "next_attempt_at", "created_at"], query: "due targeted fan-out rows", whyOrder: "Delivery state and due time precede chronological order.", without: "Fan-out relay scans published rows." },
].map((item) => ({ status: STATUS.IMPLEMENTED, ...item }));

const redisUseCases = [
  { id: "redis-auth-session", serviceId: "service-auth", kind: "session", keyPattern: "auth:session:{session_id}", value: "user UUID", ttl: "Until SQL session expiry; default maximum 30 days", writer: "login/refresh activation", reader: "Auth protected-request dependency", invalidation: "logout/admin/session revoke deletes key", failureBehaviour: "Fail closed with unavailable/401 semantics; SQL session alone is insufficient.", status: STATUS.IMPLEMENTED, evidenceIds: ["evidence-auth-cache"] },
  { id: "redis-auth-touch", serviceId: "service-auth", kind: "temporary-throttle", keyPattern: "auth:session-touch:{session_id}", value: "1", ttl: "Default 5 minutes", writer: "protected Auth request via SET NX EX", reader: "same request path", invalidation: "TTL or session revoke", failureBehaviour: "Fail closed on Auth session path.", status: STATUS.IMPLEMENTED, evidenceIds: ["evidence-auth-cache"] },
  { id: "redis-auth-rate", serviceId: "service-auth", kind: "rate-limit-counter", keyPattern: "auth:rate:{scope}:{sha256(identity)}", value: "integer request count", ttl: "Scope window: login 60s, register 3600s, refresh 300s, introspection 60s", writer: "transactional INCR + EXPIRE NX pipeline", reader: "register/login/refresh/introspection", invalidation: "TTL", failureBehaviour: "Fail closed with HTTP 503; over limit returns 429 and Retry-After.", status: STATUS.IMPLEMENTED, evidenceIds: ["evidence-auth-rate"] },
  { id: "redis-category-tree", serviceId: "service-catalog", kind: "read-through-cache", keyPattern: "catalog:categories:tree:v1", value: "serialized category tree JSON", ttl: "60 seconds by default", writer: "category tree cache fill", reader: "public category tree endpoint", invalidation: "best-effort DELETE after category commit; TTL fallback", failureBehaviour: "Fail open to PostgreSQL; stale value can survive until TTL if invalidation fails.", status: STATUS.IMPLEMENTED, evidenceIds: ["evidence-category-cache"] },
  { id: "redis-stock", serviceId: "service-inventory", kind: "read-through-cache", keyPattern: "inventory:stock:{product_id}:{variant_id|default}:v1", value: "hash: revision + serialized stock payload", ttl: "30 seconds by default", writer: "post-commit stock mutations through revision-aware Lua", reader: "public stock read", invalidation: "TTL; newer revision overwrites older", failureBehaviour: "Fail open to PostgreSQL; malformed/missing entries are ignored.", status: STATUS.IMPLEMENTED, evidenceIds: ["evidence-stock-cache"] },
];

const exchanges = [
  { id: "exchange-events", name: "flashmarket.events", type: "topic", durable: true, purpose: "Business integration events.", vhost: "/flashmarket", status: STATUS.IMPLEMENTED, evidenceIds: ["evidence-init-infra", "evidence-rabbit-topology"] },
  { id: "exchange-retry", name: "flashmarket.retry", type: "direct", durable: true, purpose: "Route expired per-consumer retries back to their main queue.", vhost: "/flashmarket", status: STATUS.IMPLEMENTED, evidenceIds: ["evidence-init-infra", "evidence-rabbit-topology"] },
  { id: "exchange-dead-letter", name: "flashmarket.dead-letter", type: "direct", durable: true, purpose: "Retain poison messages and queue overflow.", vhost: "/flashmarket", status: STATUS.IMPLEMENTED, evidenceIds: ["evidence-init-infra", "evidence-rabbit-topology"] },
];

const queueFamilies = [
  { id: "inventory", main: "inventory.events", serviceId: "service-inventory", routingKeys: ["orders.OrderCreated", "payments.PaymentSucceeded", "payments.PaymentFailed", "orders.OrderCancelled"] },
  { id: "orders", main: "orders.events", serviceId: "service-orders", routingKeys: ["payments.PaymentSucceeded", "payments.PaymentFailed", "inventory.ReservationReleased"] },
  { id: "payments", main: "payments.events", serviceId: "service-payments", routingKeys: ["orders.PaymentRequested"] },
  { id: "notifications", main: "notifications.events", serviceId: "service-notifications", routingKeys: ["orders.OrderCreated", "orders.OrderConfirmed", "orders.OrderCancelled", "wishlist.DropAvailable"] },
  { id: "wishlist", main: "wishlist.drop-events", serviceId: "service-wishlist", routingKeys: ["drops.DropStarted"] },
];

const queues = queueFamilies.flatMap((family) => {
  const mainId = `queue-${family.id}-main`;
  return [
    {
      id: mainId, name: family.main, kind: "main", serviceId: family.serviceId,
      exchangeId: "exchange-events", routingKeys: family.routingKeys,
      maxMessages: 20000, maxBytes: 134217728, overflow: "reject-publish-dlx",
      status: STATUS.IMPLEMENTED, evidenceIds: ["evidence-init-infra", "evidence-rabbit-topology"],
    },
    ...[5000, 30000, 120000].map((ttlMs, index) => ({
      id: `queue-${family.id}-retry-${index + 1}`,
      name: `${family.main}.retry.${index + 1}`,
      kind: "retry", serviceId: family.serviceId, exchangeId: "exchange-retry",
      attempt: index + 1, ttlMs, returnsToQueueId: mainId,
      maxMessages: 20000, maxBytes: 134217728, overflow: "reject-publish",
      status: STATUS.IMPLEMENTED, evidenceIds: ["evidence-init-infra", "evidence-rabbit-topology"],
    })),
    {
      id: `queue-${family.id}-dlq`, name: `${family.main}.dlq`, kind: "dead-letter",
      serviceId: family.serviceId, exchangeId: "exchange-dead-letter",
      maxMessages: 50000, maxBytes: 268435456, overflow: "reject-publish",
      replay: "manual guarded replay through flashmarket-dlq utility",
      status: STATUS.IMPLEMENTED, evidenceIds: ["evidence-init-infra", "evidence-rabbit-topology", "evidence-rabbit-runbook"],
    },
  ];
});

const authEvents = [
  ["user-registered", "user_registered", "Successful registration"],
  ["user-logged-in", "user_logged_in", "Successful login"],
  ["token-refreshed", "token_refreshed", "Successful one-time refresh rotation"],
  ["refresh-token-reuse", "refresh_token_reuse", "Consumed or revoked refresh token is reused"],
  ["user-logged-out", "user_logged_out", "Session logout"],
  ["profile-updated", "profile_updated", "Profile mutation"],
  ["password-changed", "password_changed", "Password mutation and session revocation"],
  ["user-role-changed", "user_role_changed", "Administrator role mutation"],
  ["user-status-changed", "user_status_changed", "Administrator active-status mutation"],
  ["session-revoked", "session_revoked", "Single session revocation"],
  ["all-sessions-revoked", "all_sessions_revoked", "All user sessions revoked"],
].map(([slug, eventName, trigger]) => ({
  id: `event-${slug}`, name: eventName, routingKey: `identity.${eventName}`,
  producerId: "service-auth", trigger,
  payloadFields: ["schema_version", "event_id", "occurred_at", "aggregate_type", "aggregate_id", "data"],
  exchangeId: "exchange-events", queueIds: [], consumerIds: [],
  sideEffects: ["No subscriber exists in this repository; the event is an integration extension point."],
  retry: "Outbox publish retry on transport failure; mandatory=false because no subscriber is declared.",
  idempotency: "Stable outbox/event/message ID.", delivery: "publisher-confirmed, subscriber-less",
  status: STATUS.IMPLEMENTED, evidenceIds: ["evidence-auth-app", "evidence-auth-models"],
}));

const events = [
  ...authEvents,
  {
    id: "event-inventory-reserved", name: "InventoryReserved", routingKey: "inventory.InventoryReserved", producerId: "service-inventory",
    trigger: "A reservation commits successfully.", payloadFields: ["reservation_id", "user_id", "product_id", "variant_id", "quantity", "order_id", "expires_at", "drop_id"],
    exchangeId: "exchange-events", queueIds: [], consumerIds: [], sideEffects: ["No repository subscriber."],
    retry: "Outbox retry on transport failure; mandatory=false.", idempotency: "Stable event ID and persisted reservation.", delivery: "publisher-confirmed, subscriber-less", status: STATUS.IMPLEMENTED,
    evidenceIds: ["evidence-stock-service"]
  },
  {
    id: "event-inventory-committed", name: "InventoryCommitted", routingKey: "inventory.InventoryCommitted", producerId: "service-inventory",
    trigger: "A successful payment commits reserved stock to sold.", payloadFields: ["reservation_id", "product_id", "order_id", "quantity"],
    exchangeId: "exchange-events", queueIds: [], consumerIds: [], sideEffects: ["No repository subscriber."],
    retry: "Outbox retry on transport failure; mandatory=false.", idempotency: "Reservation state guard and stable event ID.", delivery: "publisher-confirmed, subscriber-less", status: STATUS.IMPLEMENTED,
    evidenceIds: ["evidence-stock-service"]
  },
  {
    id: "event-reservation-released", name: "ReservationReleased", routingKey: "inventory.ReservationReleased", producerId: "service-inventory",
    trigger: "Manual release, payment failure, order cancellation or expiration.", payloadFields: ["reservation_id", "product_id", "order_id", "quantity", "reason"],
    exchangeId: "exchange-events", queueIds: ["queue-orders-main"], consumerIds: ["service-orders"],
    sideEffects: ["Cancel an awaiting/pending order."], retry: "Outbox backoff plus consumer retries at 5/30/120 seconds, then Orders DLQ.",
    idempotency: "Orders processed_events plus order state guard.", delivery: "at-least-once", status: STATUS.IMPLEMENTED,
    evidenceIds: ["evidence-stock-service", "evidence-orders-consumer"]
  },
  {
    id: "event-order-created", name: "OrderCreated", routingKey: "orders.OrderCreated", producerId: "service-orders",
    trigger: "Single or batch order creation commits.", payloadFields: ["order_id", "checkout_id", "reservation_id", "user_id", "product_id", "product_name", "amount", "currency", "payment_expires_at"],
    exchangeId: "exchange-events", queueIds: ["queue-inventory-main", "queue-notifications-main"], consumerIds: ["service-inventory", "service-notifications"],
    sideEffects: ["Bind order_id to reservation.", "Create an order-created notification."], retry: "Outbox backoff and independent per-consumer retry chains.",
    idempotency: "Independent transactional inbox in Inventory and Notifications.", delivery: "at-least-once", status: STATUS.IMPLEMENTED,
    evidenceIds: ["evidence-order-service", "evidence-stock-service", "evidence-notifications-consumer"]
  },
  {
    id: "event-payment-requested", name: "PaymentRequested", routingKey: "orders.PaymentRequested", producerId: "service-orders",
    trigger: "Order creation stages a payment request.", payloadFields: ["order_id", "reservation_id", "user_id", "amount", "currency", "payment_expires_at"],
    exchangeId: "exchange-events", queueIds: ["queue-payments-main"], consumerIds: ["service-payments"], sideEffects: ["Create or reuse a mock PENDING payment."],
    retry: "Outbox backoff plus Payments retry chain.", idempotency: "Payments inbox and existing-by-order application check; DB uniqueness is missing.",
    delivery: "at-least-once", status: STATUS.PARTIAL, evidenceIds: ["evidence-order-service", "evidence-payments-consumer"]
  },
  {
    id: "event-order-confirmed", name: "OrderConfirmed", routingKey: "orders.OrderConfirmed", producerId: "service-orders",
    trigger: "Payment success or current mock HTTP confirmation.", payloadFields: ["order_id", "reservation_id", "payment_id", "user_id"],
    exchangeId: "exchange-events", queueIds: ["queue-notifications-main"], consumerIds: ["service-notifications"], sideEffects: ["Create an order-confirmed notification."],
    retry: "Outbox backoff plus Notifications retry chain.", idempotency: "Notifications inbox and application duplicate check.", delivery: "at-least-once", status: STATUS.IMPLEMENTED,
    evidenceIds: ["evidence-order-service", "evidence-notifications-consumer"]
  },
  {
    id: "event-order-cancelled", name: "OrderCancelled", routingKey: "orders.OrderCancelled", producerId: "service-orders",
    trigger: "Payment failure, reservation release or current mock fail endpoint.", payloadFields: ["order_id", "reservation_id", "payment_id", "user_id", "reason"],
    exchangeId: "exchange-events", queueIds: ["queue-inventory-main", "queue-notifications-main"], consumerIds: ["service-inventory", "service-notifications"],
    sideEffects: ["Release an active reservation.", "Create an order-cancelled notification."], retry: "Outbox backoff and independent consumer retry chains.",
    idempotency: "Both consumer inboxes plus reservation/notification state guards.", delivery: "at-least-once", status: STATUS.IMPLEMENTED,
    evidenceIds: ["evidence-order-service", "evidence-stock-service", "evidence-notifications-consumer"]
  },
  {
    id: "event-payment-succeeded", name: "PaymentSucceeded", routingKey: "payments.PaymentSucceeded", producerId: "service-payments",
    trigger: "Current mock payment confirm transition.", payloadFields: ["payment_id", "order_id", "user_id", "amount", "currency"],
    exchangeId: "exchange-events", queueIds: ["queue-orders-main", "queue-inventory-main"], consumerIds: ["service-orders", "service-inventory"],
    sideEffects: ["Confirm order and stage OrderConfirmed.", "Commit reservation to sold stock."], retry: "Outbox backoff and independent consumer retries.",
    idempotency: "Transactional inboxes and aggregate state guards.", delivery: "at-least-once", status: STATUS.PARTIAL,
    evidenceIds: ["evidence-payment-service", "evidence-orders-consumer", "evidence-stock-service"]
  },
  {
    id: "event-payment-failed", name: "PaymentFailed", routingKey: "payments.PaymentFailed", producerId: "service-payments",
    trigger: "Current mock payment fail transition.", payloadFields: ["payment_id", "order_id", "user_id", "amount", "currency", "reason"],
    exchangeId: "exchange-events", queueIds: ["queue-orders-main", "queue-inventory-main"], consumerIds: ["service-orders", "service-inventory"],
    sideEffects: ["Cancel order.", "Release reservation and restore available stock."], retry: "Outbox backoff and independent consumer retries.",
    idempotency: "Transactional inboxes and aggregate state guards.", delivery: "at-least-once", status: STATUS.IMPLEMENTED,
    evidenceIds: ["evidence-payment-service", "evidence-orders-consumer", "evidence-stock-service"]
  },
  {
    id: "event-payment-cancelled", name: "PaymentCancelled", routingKey: "payments.PaymentCancelled", producerId: "service-payments",
    trigger: "Owner/admin cancellation.", payloadFields: ["payment_id", "order_id", "user_id", "amount", "currency"], exchangeId: "exchange-events",
    queueIds: [], consumerIds: [], sideEffects: ["No repository subscriber; order/reservation wait for another path such as expiry."],
    retry: "Outbox retry on transport failure; mandatory=false.", idempotency: "Persisted payment status and stable event ID.", delivery: "publisher-confirmed, subscriber-less", status: STATUS.PARTIAL,
    evidenceIds: ["evidence-payment-service"]
  },
  {
    id: "event-drop-scheduled", name: "DropScheduled", routingKey: "drops.DropScheduled", producerId: "service-drops", trigger: "Admin moves DRAFT to SCHEDULED.",
    payloadFields: ["drop_id", "name", "slug", "starts_at", "ends_at"], exchangeId: "exchange-events", queueIds: [], consumerIds: [], sideEffects: ["No repository subscriber."],
    retry: "Outbox transport retry; mandatory=false.", idempotency: "Stable event ID.", delivery: "publisher-confirmed, subscriber-less", status: STATUS.IMPLEMENTED, evidenceIds: ["evidence-drop-service"]
  },
  {
    id: "event-drop-started", name: "DropStarted", routingKey: "drops.DropStarted", producerId: "service-drops", trigger: "Admin or scheduler moves SCHEDULED to ACTIVE.",
    payloadFields: ["drop_id", "name", "slug", "product_ids", "max_per_user"], exchangeId: "exchange-events", queueIds: ["queue-wishlist-main"], consumerIds: ["service-wishlist"],
    sideEffects: ["Find users wishing any drop product and stage per-user DropAvailable events."], retry: "Outbox backoff plus Wishlist retry chain.",
    idempotency: "Wishlist inbox and unique drop/user event_key.", delivery: "at-least-once", status: STATUS.IMPLEMENTED,
    evidenceIds: ["evidence-drop-service", "evidence-wishlist-consumer", "evidence-wishlist-repo"]
  },
  {
    id: "event-drop-ended", name: "DropEnded", routingKey: "drops.DropEnded", producerId: "service-drops", trigger: "Admin or scheduler moves ACTIVE to ENDED.",
    payloadFields: ["drop_id", "slug"], exchangeId: "exchange-events", queueIds: [], consumerIds: [], sideEffects: ["No repository subscriber."],
    retry: "Outbox transport retry; mandatory=false.", idempotency: "Stable event ID.", delivery: "publisher-confirmed, subscriber-less", status: STATUS.IMPLEMENTED, evidenceIds: ["evidence-drop-service"]
  },
  {
    id: "event-drop-cancelled", name: "DropCancelled", routingKey: "drops.DropCancelled", producerId: "service-drops", trigger: "Admin cancels an eligible drop.",
    payloadFields: ["drop_id", "slug"], exchangeId: "exchange-events", queueIds: [], consumerIds: [], sideEffects: ["No repository subscriber."],
    retry: "Outbox transport retry; mandatory=false.", idempotency: "Stable event ID.", delivery: "publisher-confirmed, subscriber-less", status: STATUS.IMPLEMENTED, evidenceIds: ["evidence-drop-service"]
  },
  {
    id: "event-drop-available", name: "DropAvailable", routingKey: "wishlist.DropAvailable", producerId: "service-wishlist", trigger: "Transactional fan-out after DropStarted.",
    payloadFields: ["event_key", "user_id", "drop_id", "drop_name", "drop_slug"], exchangeId: "exchange-events", queueIds: ["queue-notifications-main"], consumerIds: ["service-notifications"],
    sideEffects: ["Create one targeted DROP_ALERT notification."], retry: "Wishlist outbox backoff plus Notifications retry chain.",
    idempotency: "Unique producer event_key, Notifications inbox and unique notification event_key.", delivery: "at-least-once", status: STATUS.IMPLEMENTED,
    evidenceIds: ["evidence-wishlist-repo", "evidence-notifications-consumer"]
  },
  {
    id: "event-notification-sent", name: "NotificationSent", routingKey: "notifications.NotificationSent", producerId: "service-notifications", trigger: "Current send state transition.",
    payloadFields: ["notification_id", "user_id", "channel", "sent_at"], exchangeId: "exchange-events", queueIds: [], consumerIds: [], sideEffects: ["No repository subscriber or physical delivery."],
    retry: "Outbox transport retry; mandatory=false.", idempotency: "Notification state and stable event ID.", delivery: "publisher-confirmed, subscriber-less", status: STATUS.PARTIAL,
    evidenceIds: ["evidence-notification-models"]
  },
];

const workerProcesses = [
  { id: "worker-auth-outbox", serviceId: "service-auth", role: "outbox", trigger: "poll Auth outbox", sideEffect: "publish identity events", retry: "scheduled outbox backoff", idempotency: "stable event ID", evidenceIds: ["evidence-auth-outbox-worker", "evidence-outbox-lease"] },
  { id: "worker-auth-cleanup", serviceId: "service-auth", role: "Celery maintenance", trigger: "auth.maintenance delivery; Beat every 3600 seconds", sideEffect: "remove expired auth state and old published outbox", retry: "late-ACK redelivery on worker loss; otherwise next Beat tick", idempotency: "bounded delete predicates", evidenceIds: ["evidence-auth-cli", "evidence-auth-task"] },
  { id: "worker-inventory-consumer", serviceId: "service-inventory", role: "consumer", queueIds: ["queue-inventory-main"], trigger: "inventory.events delivery", sideEffect: "bind/commit/release reservations", retry: "5/30/120s then DLQ", idempotency: "processed_events + state guard", evidenceIds: ["evidence-inventory-consumer"] },
  { id: "worker-inventory-outbox", serviceId: "service-inventory", role: "outbox", trigger: "poll due rows", sideEffect: "publish inventory events", retry: "lease + capped jitter backoff", idempotency: "stable event ID", evidenceIds: ["evidence-inventory-outbox-worker", "evidence-outbox-lease"] },
  { id: "worker-inventory-expiry", serviceId: "service-inventory", role: "Celery maintenance", trigger: "inventory.maintenance delivery; Beat every 5 seconds", sideEffect: "release expired reservations", retry: "late-ACK redelivery on worker loss; otherwise next Beat tick", idempotency: "SKIP LOCKED + reservation state", evidenceIds: ["evidence-inventory-expiry-worker"] },
  { id: "worker-orders-consumer", serviceId: "service-orders", role: "consumer", queueIds: ["queue-orders-main"], trigger: "orders.events delivery", sideEffect: "confirm/cancel orders", retry: "5/30/120s then DLQ", idempotency: "processed_events + state guard", evidenceIds: ["evidence-orders-consumer"] },
  { id: "worker-orders-outbox", serviceId: "service-orders", role: "outbox", trigger: "poll due rows", sideEffect: "publish order events", retry: "lease + capped jitter backoff", idempotency: "stable event ID", evidenceIds: ["evidence-orders-outbox-worker", "evidence-outbox-lease"] },
  { id: "worker-payments-consumer", serviceId: "service-payments", role: "consumer", queueIds: ["queue-payments-main"], trigger: "payments.events delivery", sideEffect: "create mock payment", retry: "5/30/120s then DLQ", idempotency: "processed_events + application lookup", evidenceIds: ["evidence-payments-consumer"] },
  { id: "worker-payments-outbox", serviceId: "service-payments", role: "outbox", trigger: "poll due rows", sideEffect: "publish payment events", retry: "lease + capped jitter backoff", idempotency: "stable event ID", evidenceIds: ["evidence-payments-outbox-worker", "evidence-outbox-lease"] },
  { id: "worker-notifications-consumer", serviceId: "service-notifications", role: "consumer", queueIds: ["queue-notifications-main"], trigger: "notifications.events delivery", sideEffect: "project user notification", retry: "5/30/120s then DLQ", idempotency: "processed_events + event/application key", evidenceIds: ["evidence-notifications-consumer"] },
  { id: "worker-notifications-outbox", serviceId: "service-notifications", role: "outbox", trigger: "poll due rows", sideEffect: "publish NotificationSent", retry: "lease + capped jitter backoff", idempotency: "stable event ID", evidenceIds: ["evidence-notifications-outbox-worker", "evidence-outbox-lease"] },
  { id: "worker-wishlist-consumer", serviceId: "service-wishlist", role: "consumer", queueIds: ["queue-wishlist-main"], trigger: "wishlist.drop-events delivery", sideEffect: "stage targeted DropAvailable fan-out", retry: "5/30/120s then DLQ", idempotency: "processed_events + unique event_key", evidenceIds: ["evidence-wishlist-consumer"] },
  { id: "worker-wishlist-outbox", serviceId: "service-wishlist", role: "outbox", trigger: "poll due rows", sideEffect: "publish targeted events", retry: "lease + capped jitter backoff", idempotency: "unique event_key and stable ID", evidenceIds: ["evidence-wishlist-outbox-worker", "evidence-outbox-lease"] },
  { id: "worker-drops-scheduler", serviceId: "service-drops", role: "Celery maintenance", trigger: "drops.maintenance delivery; Beat every 10 seconds", sideEffect: "start/end due drops", retry: "late-ACK redelivery on worker loss; otherwise next Beat tick", idempotency: "status guard + FOR UPDATE SKIP LOCKED", evidenceIds: ["evidence-drop-scheduler", "evidence-drop-task"] },
  { id: "worker-drops-outbox", serviceId: "service-drops", role: "outbox", trigger: "poll due rows", sideEffect: "publish lifecycle events", retry: "lease + capped jitter backoff", idempotency: "stable event ID", evidenceIds: ["evidence-drops-outbox-worker", "evidence-outbox-lease"] },
  { id: "worker-media-cleanup", serviceId: "service-media", role: "Celery maintenance", trigger: "media.maintenance delivery; Beat every 30 seconds", sideEffect: "delete expired/deleting S3 objects", retry: "late-ACK redelivery on worker loss; otherwise next Beat tick", idempotency: "SKIP LOCKED candidates and no-such-key tolerance", evidenceIds: ["evidence-media-cleanup"] },
].map((item) => ({ longRunning: true, queueIds: [], timeout: "role-specific health staleness threshold", status: STATUS.IMPLEMENTED, ...item }));

const oneShotProcesses = [
  { id: "process-auth-keygen", serviceId: "service-auth", role: "key-generation", trigger: "Compose startup dependency", sideEffect: "Create a non-overwriting Ed25519 key pair and split private/public volumes.", status: STATUS.IMPLEMENTED, evidenceIds: ["evidence-root-compose", "evidence-auth-keygen"] },
];

const celeryTasks = [
  { id: "celery-auth-cleanup", name: "flashmarket.auth.cleanup_expired_data", ownerId: "service-auth", queue: "auth.maintenance", schedule: "3600 seconds", sideEffect: "Delete retained expired Auth rows.", idempotency: "Time-bounded DELETE predicates.", evidenceIds: ["evidence-auth-task", "evidence-celery-beat"] },
  { id: "celery-inventory-expiry", name: "flashmarket.inventory.expire_reservations", ownerId: "service-inventory", queue: "inventory.maintenance", schedule: "5 seconds", sideEffect: "Release expired reservations and stage outbox events.", idempotency: "SKIP LOCKED claim and reservation state guard.", evidenceIds: ["evidence-inventory-expiry-worker", "evidence-celery-beat"] },
  { id: "celery-drops-scheduler", name: "flashmarket.drops.run_scheduler_tick", ownerId: "service-drops", queue: "drops.maintenance", schedule: "10 seconds", sideEffect: "Start and end due Drops with outbox events.", idempotency: "SKIP LOCKED due rows and lifecycle state guard.", evidenceIds: ["evidence-drop-task", "evidence-drop-scheduler", "evidence-celery-beat"] },
  { id: "celery-media-cleanup", name: "flashmarket.media.cleanup_expired_assets", ownerId: "service-media", queue: "media.maintenance", schedule: "30 seconds", sideEffect: "Delete expired/deleting objects and advance metadata state.", idempotency: "SKIP LOCKED candidates and missing-object tolerance.", evidenceIds: ["evidence-media-cleanup", "evidence-celery-beat"] },
];

const connections = [
  { id: "connection-browser-gateway", from: "component-browser", to: "component-gateway", protocol: "HTTP REST", purpose: "Public storefront, admin and API traffic.", contract: "Gateway-reachable OpenAPI operations and static frontend.", consistency: "synchronous", failureBehaviour: "Client receives gateway/upstream error; API helper may refresh once on 401." },
  ...services.map((service) => ({
    id: `connection-gateway-${service.slug}`, from: "component-gateway", to: service.id,
    protocol: "HTTP REST", purpose: `Route public ${service.name} API paths.`, contract: service.endpointIds,
    consistency: "synchronous", failureBehaviour: "Nginx returns upstream failure/timeout; no cross-service transaction.",
  })),
  { id: "connection-inventory-drops", from: "service-inventory", to: "service-drops", protocol: "HTTP REST", purpose: "Resolve drop membership, per-user limit and payment timeout before reserve.", contract: "GET /api/v1/drops/id/{drop_id}", consistency: "synchronous policy read followed by local transaction", failureBehaviour: "One-second timeout or non-success fails the reservation closed.", evidenceIds: ["evidence-drop-policy"] },
  { id: "connection-celery-rabbit", from: "component-celery", to: "component-rabbitmq", protocol: "Celery / AMQP", purpose: "Beat publishes periodic maintenance commands into the isolated task vhost.", contract: "Four named tasks and queues", consistency: "at-least-once command delivery", failureBehaviour: "Broker outage delays schedules; startup connection retry and the next tick recover.", evidenceIds: ["evidence-celery-runtime", "evidence-celery-beat"] },
  ...services.map((service) => ({
    id: `connection-${service.slug}-postgres`, from: service.id, to: service.databaseId,
    protocol: "PostgreSQL", purpose: `Persist ${service.name}-owned source-of-truth state.`, contract: "SQLAlchemy models and Alembic migrations",
    consistency: "strong within one local transaction", failureBehaviour: "Operation rolls back or readiness fails.",
  })),
  { id: "connection-auth-redis", from: "service-auth", to: "component-redis", protocol: "Redis", purpose: "Active sessions, touch throttle and rate limits.", contract: ["redis-auth-session", "redis-auth-touch", "redis-auth-rate"], consistency: "synchronous auxiliary security state", failureBehaviour: "Fail closed." },
  { id: "connection-catalog-redis", from: "service-catalog", to: "component-redis", protocol: "Redis", purpose: "Category tree read-through cache.", contract: ["redis-category-tree"], consistency: "bounded stale cache", failureBehaviour: "Fail open to PostgreSQL." },
  { id: "connection-inventory-redis", from: "service-inventory", to: "component-redis", protocol: "Redis", purpose: "Revision-aware stock read-through cache.", contract: ["redis-stock"], consistency: "bounded stale cache; DB authoritative", failureBehaviour: "Fail open to PostgreSQL." },
  { id: "connection-media-s3", from: "service-media", to: "component-s3", protocol: "S3 API", purpose: "Presign, inspect, stream and delete media objects.", contract: "Exact POST conditions plus object metadata", consistency: "DB metadata and object lifecycle coordinated by explicit states", failureBehaviour: "Completion fails or cleanup leaves retryable state." },
  ...services.filter((service) => service.publishesEventIds.length > 0).map((service) => ({
    id: `connection-${service.slug}-rabbit-publish`, from: service.id, to: "component-rabbitmq", protocol: "AMQP 0-9-1 / aio-pika",
    purpose: "Publish service outbox events.", contract: service.publishesEventIds, consistency: "asynchronous at-least-once for routed events",
    failureBehaviour: "Outbox row remains retryable with capped jittered backoff.",
  })),
  ...services.filter((service) => service.consumesEventIds.length > 0).map((service) => ({
    id: `connection-rabbit-${service.slug}-consume`, from: "component-rabbitmq", to: service.id, protocol: "AMQP 0-9-1 / aio-pika",
    purpose: "Deliver bound integration events.", contract: service.consumesEventIds, consistency: "asynchronous at-least-once",
    failureBehaviour: "Per-consumer delayed retries, then DLQ; inbox handles duplicates.",
  })),
  ...services.filter((service) => service.id !== "service-auth").map((service) => ({
    id: `connection-auth-keys-${service.slug}`, from: "service-auth", to: service.id,
    protocol: "read-only filesystem volume", purpose: "Distribute Ed25519 public verification keys without private signing material.",
    contract: "PEM key ring selected by JWT kid", consistency: "deployment-time key availability",
    failureBehaviour: "Missing/malformed keys fail startup or token verification.",
    evidenceIds: ["evidence-jwt-verifier", "evidence-local-jwt-design"],
  })),
].map((item) => ({ status: STATUS.IMPLEMENTED, ...item }));

const mechanisms = [
  {
    id: "mechanism-outbox", name: "Transactional Outbox", status: STATUS.IMPLEMENTED,
    summary: "Business state and publish intent commit together; a separate relay performs confirmed RabbitMQ delivery.",
    problem: "A direct publish after COMMIT can be lost forever if the process crashes between the database and broker calls.",
    implementation: [
      "Insert the business mutation and outbox row in one service database transaction.",
      "Claim one oldest due row through FOR UPDATE SKIP LOCKED and a short claim token/lease.",
      "Commit the claim, publish outside the SQL transaction, require a broker confirmation.",
      "Record success/failure only if the claim token still matches; failures receive full-jitter exponential backoff capped at 300 seconds."
    ],
    guarantees: ["No permanent DB-commit/publish-loss window.", "At-least-once delivery for routed events.", "Relay replicas divide due work without one long publish transaction."],
    limitations: ["Exactly-once is impossible across PostgreSQL and RabbitMQ here.", "Crash after confirm but before marking published can duplicate an event.", "Cross-event and aggregate ordering is not guaranteed.", "Only Auth has an outbox-retention cleanup."],
    tableIds: ["table-auth-outbox", "table-inventory-outbox", "table-orders-outbox", "table-payments-outbox", "table-notifications-outbox", "table-wishlist-outbox", "table-drops-outbox"],
    indexIds: ["index-auth-outbox-due", "index-inventory-outbox-due", "index-orders-outbox-due", "index-payments-outbox-due", "index-notifications-outbox-due", "index-wishlist-outbox-due", "index-drops-outbox-due"],
    evidenceIds: ["evidence-outbox-lease", "evidence-rabbit-delivery", "evidence-reliability-design"]
  },
  {
    id: "mechanism-consumer-delivery", name: "Retry + DLQ + Transactional Inbox", status: STATUS.IMPLEMENTED,
    summary: "Each consumer retries its own failures without replaying successful subscribers and deduplicates local effects transactionally.",
    problem: "A transient database failure must not lose the event, while a poison payload must not hot-loop forever.",
    implementation: ["Classify malformed payloads as permanent and send them directly to DLQ.", "Move transient failures through 5/30/120-second per-consumer queues.", "Publisher-confirm the retry/DLQ copy before ACKing the source message.", "Insert processed_events in the same transaction as the local side effect and any next outbox row."],
    guarantees: ["One initial attempt plus three delayed retries.", "No silent discard when moving a failed delivery.", "Duplicate message ID produces no duplicate local database effect."],
    limitations: ["DLQ replay is manual.", "An external side effect would need its own idempotency contract."],
    evidenceIds: ["evidence-rabbit-consumer", "evidence-rabbit-inbox", "evidence-rabbit-topology", "evidence-rabbit-runbook"]
  },
  {
    id: "mechanism-stock-concurrency", name: "Stock Reservation Concurrency", status: STATUS.IMPLEMENTED,
    summary: "PostgreSQL row locks and CHECK constraints preserve authoritative stock under concurrent reserve/commit/release operations.",
    problem: "Two requests can both observe the last unit and oversell without serialization.",
    implementation: ["SELECT the stock row FOR UPDATE.", "Check available quantity under the lock.", "Mutate counters, insert reservation and stage InventoryReserved before one COMMIT.", "Use CHECK constraints as the final persisted invariant."],
    guarantees: ["available, reserved, sold and total cannot become negative.", "reserved + sold cannot exceed total.", "Only one transaction at a time mutates the same stock row."],
    limitations: ["Duplicate HTTP commands are not idempotent.", "Nullable variant_id leaves default-stock uniqueness incomplete."],
    evidenceIds: ["evidence-stock-service", "evidence-stock-repo", "evidence-inventory-models"]
  },
  {
    id: "mechanism-drop-limit", name: "Drop Per-User Serialization", status: STATUS.IMPLEMENTED,
    summary: "A PostgreSQL transaction advisory lock serializes reservations for the same user and drop.",
    problem: "Parallel requests could each pass a count-before-insert max_per_user check.",
    implementation: ["Derive advisory-lock keys from user and drop UUIDs.", "Acquire pg_advisory_xact_lock.", "Sum active/committed quantity and enforce the returned drop policy before reserve."],
    guarantees: ["The per-user drop limit is serialized within PostgreSQL."],
    limitations: ["The preceding Drops HTTP policy read is not part of the SQL transaction.", "SQLite tests cannot prove PostgreSQL advisory behavior."],
    evidenceIds: ["evidence-stock-repo", "evidence-drop-policy"]
  },
  {
    id: "mechanism-refresh-rotation", name: "Refresh Token Rotation", status: STATUS.IMPLEMENTED,
    summary: "Refresh secrets are one-time, hash-only at rest and replay revokes the session.",
    problem: "A stolen reusable refresh token would remain a long-lived credential.",
    implementation: ["Store SHA-256 digest, never plaintext.", "Lock refresh token, session and user rows during rotation.", "Mark the old token consumed and link its replacement.", "Reusing a consumed/revoked token revokes the session."],
    guarantees: ["One refresh secret can successfully rotate once.", "Replay produces a security response rather than another valid chain."],
    limitations: ["Downstream access JWTs remain valid until their short expiry."],
    evidenceIds: ["evidence-auth-security", "evidence-auth-app", "evidence-auth-models"]
  },
  {
    id: "mechanism-media-validation", name: "Direct Upload Validation", status: STATUS.IMPLEMENTED,
    summary: "The browser uploads directly to S3, but Media verifies the object before it becomes READY.",
    problem: "Client MIME/filename metadata is not trustworthy and proxying all bytes through FastAPI is wasteful.",
    implementation: ["Issue a presigned POST with exact content type, length and asset metadata conditions.", "On complete, lock metadata and compare S3 HEAD fields.", "Read at most configured maximum plus one byte, verify magic bytes, fully decode through Pillow, enforce pixel cap and compute SHA-256."],
    guarantees: ["Only validated, policy-authorized objects become READY.", "API servers do not proxy the initial upload body."],
    limitations: ["S3 I/O occurs while holding an asset row lock.", "Concurrent quota checks can exceed per-user caps."],
    evidenceIds: ["evidence-media-service", "evidence-media-storage", "evidence-media-models"]
  },
  {
    id: "mechanism-cache-policy", name: "Failure Policy by Data Criticality", status: STATUS.IMPLEMENTED,
    summary: "Derived caches fail open to PostgreSQL; security-bearing session and rate state fails closed.",
    problem: "Treating all Redis data equally either harms availability or weakens security.",
    implementation: ["Catalog and Inventory catch Redis failures and read the authoritative database.", "Auth maps session/rate Redis failures to unavailable responses.", "Inventory cache writes carry a revision and Lua rejects older values."],
    guarantees: ["Cache outages cannot corrupt stock/catalog truth.", "Auth does not bypass missing security state."],
    limitations: ["Auth availability depends on Redis.", "Cache fail-open increases PostgreSQL load."],
    evidenceIds: ["evidence-auth-cache", "evidence-auth-rate", "evidence-category-cache", "evidence-stock-cache"]
  },
];

const consistencyBoundaries = [
  { id: "consistency-local-sql", label: "Local service transaction", kind: "strong", scope: "One service database", guarantee: "Business mutation, local constraints and local outbox/inbox changes commit or roll back together.", examples: ["Inventory stock + reservation + outbox", "Orders batch + promo usage + outbox", "Consumer inbox + local side effect + next outbox"], limitations: "No atomicity with another service database, Redis, S3 or RabbitMQ." },
  { id: "consistency-service-events", label: "Inter-service event flow", kind: "eventual", scope: "RabbitMQ-connected services", guarantee: "Confirmed durable delivery is retried until handled or retained in DLQ.", examples: ["PaymentSucceeded to Orders and Inventory", "DropStarted to Wishlist"], limitations: "Temporary divergence and no global ordering." },
  { id: "consistency-delivery", label: "Message delivery", kind: "at-least-once", scope: "Outbox relay and Rabbit consumer", guarantee: "A routed event may be delivered more than once but should not be silently lost at the known boundaries.", examples: ["Crash after broker confirm", "Consumer crash after DB commit before ACK"], limitations: "Consumers must remain idempotent." },
  { id: "consistency-cache", label: "Redis projections", kind: "bounded-stale", scope: "Catalog and Inventory caches", guarantee: "PostgreSQL remains authoritative; TTL and revision limit stale data.", examples: ["60-second category tree", "30-second stock hash"], limitations: "A client can briefly observe old derived data." },
  { id: "consistency-auth-revocation", label: "Downstream JWT revocation", kind: "eventual-security", scope: "Eight non-Auth APIs", guarantee: "Signature/claim validation is local and independent from Auth availability.", examples: ["Logout", "Role downgrade", "User block"], limitations: "An issued access token remains usable downstream until default five-minute expiry." },
].map((item) => ({ status: STATUS.IMPLEMENTED, ...item }));

const flows = [
  {
    id: "flow-auth-session", name: "Register, login and rotate refresh", status: STATUS.IMPLEMENTED,
    summary: "Identity creation and session security from rate limit to one-time refresh rotation.",
    steps: [
      { id: "flow-auth-1", nodeId: "component-gateway", title: "Enter Auth boundary", what: "Gateway routes register/login/refresh to Auth and applies edge rate limits.", why: "Reject abusive traffic before expensive password work.", consistency: "synchronous", failure: "Gateway or Auth unavailable.", protection: "Nginx limits, request timeout and JSON error." },
      { id: "flow-auth-2", nodeId: "component-redis", title: "Check distributed rate state", what: "Auth increments a hashed-identity counter with TTL.", why: "Coordinate limits across Auth API replicas.", consistency: "strong per Redis command pipeline", failure: "Redis unavailable.", protection: "Fail closed with 503." },
      { id: "flow-auth-3", nodeId: "service-auth", title: "Verify password safely", what: "Argon2id work runs behind a bounded semaphore; unknown users use a dummy hash.", why: "Protect CPU/memory and reduce enumeration timing.", consistency: "in-process", failure: "Work acquisition timeout or bad credentials.", protection: "Bounded concurrency and uniform verification path." },
      { id: "flow-auth-4", nodeId: "database-auth", title: "Commit identity/session state", what: "User/session/refresh digest/audit/outbox commit through one UoW.", why: "Keep identity state and emitted fact aligned.", consistency: "strong local SQL transaction", failure: "Database error.", protection: "Rollback all local changes." },
      { id: "flow-auth-5", nodeId: "service-auth", title: "Rotate later under lock", what: "Refresh locks the chain, consumes the old digest and inserts its replacement.", why: "Make the refresh secret one-time and detect replay.", consistency: "strong local SQL transaction", failure: "Consumed/revoked token reused.", protection: "Revoke the session; downstream JWT expiry remains the boundary." },
    ], evidenceIds: ["evidence-auth-app", "evidence-auth-security", "evidence-auth-rate"]
  },
  {
    id: "flow-reserve-product", name: "Reserve product", status: STATUS.IMPLEMENTED,
    summary: "Fail-closed drop policy plus PostgreSQL serialization prevents overselling.",
    steps: [
      { id: "flow-reserve-1", nodeId: "service-inventory", title: "Authorize owner and command", what: "Validate user, quantity, variant and optional drop ID.", why: "Establish the reservation business command.", consistency: "synchronous", failure: "Invalid ownership/input.", protection: "JWT owner/admin dependency and Pydantic bounds." },
      { id: "flow-reserve-2", nodeId: "service-drops", title: "Resolve drop policy when present", what: "Inventory calls Drops with a one-second timeout.", why: "Enforce product membership, max_per_user and payment timeout.", consistency: "synchronous external read", failure: "Drops timeout/error.", protection: "Fail the reservation closed." },
      { id: "flow-reserve-3", nodeId: "database-inventory", title: "Serialize limit and stock", what: "Acquire drop advisory lock then lock the stock row FOR UPDATE.", why: "Prevent parallel user-limit bypass and overselling.", consistency: "strong local SQL transaction", failure: "Lock wait/database error.", protection: "Transaction rollback and database timeouts." },
      { id: "flow-reserve-4", nodeId: "table-reservations", title: "Persist reservation and counters", what: "available decreases, reserved increases, reservation and InventoryReserved outbox row are inserted.", why: "Make stock change and publish intent atomic.", consistency: "strong local SQL transaction", failure: "Constraint violation or insufficient stock.", protection: "CHECK constraints and rollback." },
      { id: "flow-reserve-5", nodeId: "component-redis", title: "Refresh cache after commit", what: "Write the new revisioned stock snapshot through Lua.", why: "Keep read performance without risking database correctness.", consistency: "eventually refreshed cache", failure: "Redis unavailable/out-of-order writer.", protection: "Fail open; older revision is rejected." },
    ], evidenceIds: ["evidence-stock-service", "evidence-stock-repo", "evidence-drop-policy", "evidence-stock-cache"]
  },
  {
    id: "flow-purchase-success", name: "Successful checkout and payment saga", status: STATUS.PARTIAL,
    summary: "Browser-orchestrated reserves enter an event choreography; delivery is robust but payment authority is mock.",
    steps: [
      { id: "flow-success-1", nodeId: "component-browser", title: "Reserve every cart line", what: "Checkout calls Inventory separately for each line.", why: "Obtain expiring stock reservations before creating orders.", consistency: "multiple synchronous local transactions", failure: "A later line or browser fails.", protection: "Best-effort release; expiry worker is durable fallback." },
      { id: "flow-success-2", nodeId: "database-orders", title: "Create order batch", what: "Orders locks/validates promo, writes all order snapshots/usages and stages OrderCreated + PaymentRequested per line.", why: "Make the Orders-side checkout all-or-nothing.", consistency: "strong Orders transaction", failure: "Duplicate reservation/promo validation/database error.", protection: "Rollback entire batch; duplicate race remains without unique reservation_id." },
      { id: "flow-success-3", nodeId: "component-rabbitmq", title: "Deliver order facts", what: "Outbox relays publish confirmed events to Inventory, Payments and Notifications queues.", why: "Decouple service state transitions.", consistency: "at-least-once eventual", failure: "Broker/consumer unavailable.", protection: "Outbox backoff, retry queues and DLQ." },
      { id: "flow-success-4", nodeId: "service-payments", title: "Create and confirm mock payment", what: "PaymentRequested creates PENDING; the current client calls confirm.", why: "Exercise payment-result choreography in a demo project.", consistency: "local payment transactions", failure: "Client-supplied amount/terminal command is not a real PSP trust boundary.", protection: "Clearly mark PARTIAL; future verified provider required." },
      { id: "flow-success-5", nodeId: "component-rabbitmq", title: "Fan out PaymentSucceeded", what: "The same event reaches Orders and Inventory independently.", why: "Confirm order and convert reservation to sold stock.", consistency: "eventual and at-least-once", failure: "One consumer succeeds before the other.", protection: "Independent retry/inbox; temporary divergence is expected." },
      { id: "flow-success-6", nodeId: "service-notifications", title: "Project confirmation", what: "OrderConfirmed produces a user notification.", why: "Keep notification read model out of Orders.", consistency: "eventual", failure: "Notification consumer unavailable.", protection: "Retry chain and DLQ." },
    ], evidenceIds: ["evidence-checkout-ui", "evidence-order-service", "evidence-payment-ui", "evidence-rabbit-consumer"]
  },
  {
    id: "flow-payment-failure", name: "Payment failure compensation", status: STATUS.IMPLEMENTED,
    summary: "PaymentFailed independently cancels the order and releases stock; repeated paths converge.",
    steps: [
      { id: "flow-failure-1", nodeId: "service-payments", title: "Persist failed payment", what: "Payment state and PaymentFailed outbox commit together.", why: "Make result durable before informing other services.", consistency: "strong Payments transaction", failure: "Database error.", protection: "Rollback." },
      { id: "flow-failure-2", nodeId: "service-orders", title: "Cancel order", what: "Orders inboxes PaymentFailed, transitions order and stages OrderCancelled.", why: "Reflect the failed commercial outcome.", consistency: "eventual from Payments; strong locally", failure: "Duplicate or transient DB error.", protection: "Inbox, state guard and retry." },
      { id: "flow-failure-3", nodeId: "service-inventory", title: "Release reservation", what: "Inventory restores available stock and stages ReservationReleased.", why: "Compensate the earlier reserve.", consistency: "eventual from Payments; strong locally", failure: "Duplicate/cancel path races.", protection: "Inbox, stock row lock and reservation state guard." },
      { id: "flow-failure-4", nodeId: "service-notifications", title: "Notify cancellation", what: "OrderCancelled creates a cancellation notification.", why: "Expose converged result to the user.", consistency: "eventual", failure: "Consumer delayed.", protection: "Retry and DLQ." },
    ], evidenceIds: ["evidence-payment-service", "evidence-orders-consumer", "evidence-stock-service", "evidence-notifications-consumer"]
  },
  {
    id: "flow-reservation-expiry", name: "Reservation expiration", status: STATUS.IMPLEMENTED,
    summary: "An expiry worker recovers stock even if browser checkout never creates an order.",
    steps: [
      { id: "flow-expiry-1", nodeId: "worker-inventory-expiry", title: "Select due reservations", what: "Poll RESERVED rows with expires_at <= now using FOR UPDATE SKIP LOCKED.", why: "Let multiple workers divide safe recovery work.", consistency: "strong local SQL selection", failure: "Worker/database unavailable.", protection: "Heartbeat alert; next tick retries." },
      { id: "flow-expiry-2", nodeId: "database-inventory", title: "Restore stock", what: "Lock stock, mark reservation RELEASED, restore available and stage ReservationReleased.", why: "Recover abandoned capacity atomically.", consistency: "strong Inventory transaction", failure: "Constraint/database error.", protection: "Rollback." },
      { id: "flow-expiry-3", nodeId: "service-orders", title: "Cancel waiting order", what: "If an order exists, ReservationReleased cancels an eligible order.", why: "Converge commercial state with inventory timeout.", consistency: "eventual", failure: "Orders consumer delayed.", protection: "Outbox/consumer retry and inbox." },
      { id: "flow-expiry-4", nodeId: "service-payments", title: "Expose remaining gap", what: "Payments has no expiry/reconciliation worker.", why: "The explorer must show the real boundary.", consistency: "potentially divergent", failure: "Payment may remain PENDING or later succeed after cancellation.", protection: "None beyond state guards; reconciliation/refund is planned debt." },
    ], evidenceIds: ["evidence-stock-repo", "evidence-stock-service", "evidence-orders-consumer"]
  },
  {
    id: "flow-drop-notification", name: "Drop start to wishlist notification", status: STATUS.IMPLEMENTED,
    summary: "A durable two-hop fan-out targets only users watching participating products.",
    steps: [
      { id: "flow-drop-1", nodeId: "service-drops", title: "Start drop", what: "Admin/scheduler sets ACTIVE and stages DropStarted in one transaction.", why: "Publish only a committed lifecycle fact.", consistency: "strong Drops transaction", failure: "Duplicate scheduler race.", protection: "State checks; downstream dedup absorbs duplicate fact." },
      { id: "flow-drop-2", nodeId: "queue-wishlist-main", title: "Deliver to Wishlist", what: "RabbitMQ routes only DropStarted to wishlist.drop-events.", why: "Wishlist owns the user-product audience query.", consistency: "at-least-once", failure: "Consumer unavailable.", protection: "Retry queues/DLQ." },
      { id: "flow-drop-3", nodeId: "database-wishlist", title: "Stage per-user fan-out", what: "Inbox, audience query and unique drop/user outbox rows commit together.", why: "Avoid partial direct publication across a large audience.", consistency: "strong Wishlist transaction", failure: "Duplicate delivery or row conflict.", protection: "Inbox plus unique event_key." },
      { id: "flow-drop-4", nodeId: "service-notifications", title: "Create targeted notification", what: "DropAvailable creates a unique DROP_ALERT row.", why: "Persist a user-facing read model.", consistency: "eventual", failure: "Duplicate/retry.", protection: "Notifications inbox and unique event_key." },
    ], evidenceIds: ["evidence-drop-service", "evidence-wishlist-consumer", "evidence-wishlist-repo", "evidence-notifications-consumer"]
  },
  {
    id: "flow-media-lifecycle", name: "Media upload lifecycle", status: STATUS.IMPLEMENTED,
    summary: "Direct object upload is separated from authoritative validation and cleanup state.",
    steps: [
      { id: "flow-media-1", nodeId: "service-media", title: "Authorize and presign", what: "Validate purpose/owner/quota, insert PENDING metadata and return exact S3 POST conditions.", why: "Keep access policy in Media without proxying bytes.", consistency: "strong metadata transaction", failure: "Quota/policy/database/storage presign error.", protection: "Reject before upload; quota race remains." },
      { id: "flow-media-2", nodeId: "component-s3", title: "Upload directly", what: "Browser POSTs object bytes to S3/MinIO.", why: "Remove large upload bodies from FastAPI workers.", consistency: "object write independent from metadata transaction", failure: "Client/storage interruption.", protection: "PENDING expiry cleanup." },
      { id: "flow-media-3", nodeId: "service-media", title: "Complete and validate", what: "Lock asset, compare HEAD metadata, stream bounded bytes, inspect magic/decode/pixels and compute checksum.", why: "Do not trust client MIME or dimensions.", consistency: "serialized metadata transition", failure: "Invalid object or S3 unavailable.", protection: "Remain non-READY or return retryable dependency failure." },
      { id: "flow-media-4", nodeId: "worker-media-cleanup", title: "Delete asynchronously", what: "DELETING/expired candidates are selected SKIP LOCKED and removed from S3.", why: "Make deletion restartable and keep API latency bounded.", consistency: "eventual object cleanup", failure: "S3 unavailable.", protection: "Leave retryable state for next tick." },
    ], evidenceIds: ["evidence-media-service", "evidence-media-storage", "evidence-media-cleanup"]
  },
].map((flow) => ({ selectorLabel: flow.name, ...flow }));

const failureScenarios = [
  { id: "failure-last-item", question: "What if two users buy the last item?", problem: "Both requests could read available=1 and decrement independently.", mechanism: "Inventory locks the stock row FOR UPDATE, checks availability under the lock and relies on counter CHECK constraints.", result: "One transaction reserves; the other waits and then sees insufficient stock.", remainingLimitation: "Duplicate default stock rows remain possible because nullable variant_id weakens the composite unique constraint.", status: STATUS.IMPLEMENTED, evidenceIds: ["evidence-stock-service", "evidence-stock-repo", "evidence-inventory-models"] },
  { id: "failure-rabbit-down", question: "What if RabbitMQ is unavailable?", problem: "A committed local fact cannot be delivered immediately.", mechanism: "Outbox remains failed/due, records a sanitized error, schedules jittered backoff and the relay reconnects indefinitely.", result: "Local transaction succeeds and downstream convergence is delayed rather than silently lost.", remainingLimitation: "Outbox grows and saga latency rises; broker HA is outside this repository.", status: STATUS.IMPLEMENTED, evidenceIds: ["evidence-outbox-lease", "evidence-rabbit-delivery"] },
  { id: "failure-duplicate-message", question: "What if a consumer receives the same message twice?", problem: "At-least-once delivery permits redelivery.", mechanism: "processed_events is inserted in the same transaction as the side effect; a duplicate primary key turns processing into a no-op.", result: "The local database effect is applied once.", remainingLimitation: "Future external side effects need their own idempotency keys.", status: STATUS.IMPLEMENTED, evidenceIds: ["evidence-rabbit-inbox"] },
  { id: "failure-consumer-after-commit", question: "What if a worker crashes after its DB commit but before ACK?", problem: "RabbitMQ redelivers a message whose side effect already committed.", mechanism: "Transactional inbox remembers the event ID.", result: "The redelivery is acknowledged without repeating the local mutation.", remainingLimitation: "The guarantee is local to the service database.", status: STATUS.IMPLEMENTED, evidenceIds: ["evidence-rabbit-consumer", "evidence-rabbit-inbox"] },
  { id: "failure-publisher-after-confirm", question: "What if an outbox relay crashes after broker confirm?", problem: "RabbitMQ may have the event while SQL still says unpublished.", mechanism: "Lease expiry makes the row retryable; consumers deduplicate the repeated stable event ID.", result: "The design prefers duplicate delivery over silent loss.", remainingLimitation: "Exactly-once and strict ordering are not provided.", status: STATUS.IMPLEMENTED, evidenceIds: ["evidence-outbox-lease", "evidence-rabbit-inbox"] },
  { id: "failure-redis-cache", question: "What if Redis is unavailable for Catalog or Inventory?", problem: "Read-through cache cannot serve or accept updates.", mechanism: "Cache adapters catch Redis failure and query PostgreSQL; stock cache is not the lock/authority.", result: "Requests can remain correct with higher database load.", remainingLimitation: "Latency/load rises; failed category invalidation can leave a stale value until TTL.", status: STATUS.IMPLEMENTED, evidenceIds: ["evidence-category-cache", "evidence-stock-cache"] },
  { id: "failure-redis-auth", question: "What if Redis is unavailable for Auth?", problem: "Active-session and distributed rate state cannot be trusted.", mechanism: "Auth fails closed rather than accepting SQL/JWT alone.", result: "Security state is not bypassed.", remainingLimitation: "Protected Auth availability depends on Redis.", status: STATUS.IMPLEMENTED, evidenceIds: ["evidence-auth-cache", "evidence-auth-rate"] },
  { id: "failure-drops-timeout", question: "What if Drops is down during a drop reservation?", problem: "Inventory cannot prove product membership or purchase policy.", mechanism: "The one-second HTTP dependency fails closed.", result: "No reservation bypasses drop rules.", remainingLimitation: "Legitimate drop purchases are unavailable; no retry/circuit breaker/local projection exists.", status: STATUS.IMPLEMENTED, evidenceIds: ["evidence-drop-policy"] },
  { id: "failure-duplicate-http", question: "What if the client retries the same HTTP command?", problem: "Network uncertainty can repeat reserve/order/payment creation.", mechanism: "Some paths use application lookups and unique constraints.", result: "Wishlist/promo membership duplicates are rejected, but purchase commands are not uniformly idempotent.", remainingLimitation: "Reserve has no idempotency key; reservation-to-order and order-to-payment lack DB uniqueness.", status: STATUS.PARTIAL, evidenceIds: ["evidence-stock-service", "evidence-order-service", "evidence-payment-service"] },
  { id: "failure-late-payment", question: "What if payment succeeds after reservation timeout?", problem: "Inventory/order may already be released/cancelled while payment becomes successful.", mechanism: "Aggregate state guards prevent blindly reopening terminal local state.", result: "Stock is not necessarily recommitted, but states can diverge.", remainingLimitation: "No PSP refund or reconciliation worker closes the business inconsistency.", status: STATUS.PARTIAL, evidenceIds: ["evidence-orders-consumer", "evidence-stock-service", "evidence-payment-service"] },
  { id: "failure-browser-checkout", question: "What if the browser dies after reserve but before order creation?", problem: "No server-side checkout aggregate owns the multi-line orchestration.", mechanism: "Every reservation has TTL and the expiry worker releases it.", result: "Stock is eventually recovered.", remainingLimitation: "Recovery waits for expiry; partial reservations are visible meanwhile.", status: STATUS.IMPLEMENTED, evidenceIds: ["evidence-checkout-ui", "evidence-stock-repo"] },
  { id: "failure-poison-message", question: "What if an event payload is malformed?", problem: "Retrying a permanent schema defect wastes capacity forever.", mechanism: "PermanentMessageError bypasses delayed retries and moves the message directly to DLQ.", result: "The main queue keeps progressing and the bad payload is retained.", remainingLimitation: "Replay and repair are manual; most events have no schema version.", status: STATUS.PARTIAL, evidenceIds: ["evidence-rabbit-consumer", "evidence-rabbit-runbook"] },
  { id: "failure-queue-growth", question: "What if a consumer stops and its queue grows?", problem: "Unbounded queue memory/disk can destabilize the broker and host.", mechanism: "Policies cap main/retry queues at 20k/128MiB and DLQs at 50k/256MiB; overflow is rejected/dead-lettered and alerts fire near saturation.", result: "Broker resource use is bounded and saturation is visible.", remainingLimitation: "Bounded safety shifts work to operational recovery; a full DLQ can reject new failures.", status: STATUS.IMPLEMENTED, evidenceIds: ["evidence-init-infra", "evidence-prometheus"] },
  { id: "failure-s3", question: "What if S3 is unavailable during complete or cleanup?", problem: "Media metadata and object operation cannot progress together.", mechanism: "Completion fails without READY; cleanup leaves retryable state for a later tick.", result: "An unavailable store does not falsely validate/delete metadata.", remainingLimitation: "Slow I/O can hold database row locks.", status: STATUS.IMPLEMENTED, evidenceIds: ["evidence-media-service", "evidence-media-cleanup"] },
];

const interviewQuestions = [
  { id: "interview-why-microservices", question: "Why microservices here?", shortAnswer: "The repository separates identity, catalog, stock, orders, payments, notifications, wishlist, drops and media into data-owning bounded contexts.", deepAnswer: "The useful boundary is ownership and independent state machines, not service count. Each service has its own logical database and local transaction. The cost is event-driven convergence, duplicated operational scaffolding and shared infrastructure blast radius; this is a portfolio-scale trade-off, not a claim that microservices are always required.", evidenceIds: ["evidence-root-compose", "evidence-init-infra"] },
  { id: "interview-why-not-direct-publish", question: "Why not publish directly after COMMIT?", shortAnswer: "A process crash between COMMIT and publish permanently loses the event.", deepAnswer: "The outbox stores publish intent atomically with business state. A relay can recover after process or broker failure. It still cannot make PostgreSQL and RabbitMQ one exactly-once transaction, so stable IDs and inbox dedup complete the contract.", evidenceIds: ["evidence-outbox-lease", "evidence-rabbit-inbox"] },
  { id: "interview-why-outbox", question: "What exactly does Outbox guarantee?", shortAnswer: "A committed local fact remains discoverable for publication.", deepAnswer: "It provides at-least-once delivery intent, not global ordering or exactly-once execution. Confirm/mark crashes duplicate rather than lose events; consumers are designed accordingly.", evidenceIds: ["evidence-reliability-design"] },
  { id: "interview-why-celery", question: "Why Celery?", shortAnswer: "For scheduled command jobs, while domain events stay explicit on aio-pika.", deepAnswer: "Beat centralizes the four periodic schedules and RabbitMQ gives durable late-ACK delivery. Each service still owns its task and database transaction. Integration-event consumers and outbox relays remain on aio-pika because their routing, inbox deduplication and per-consumer retry/DLQ contract is already domain-specific.", evidenceIds: ["evidence-celery-runtime", "evidence-celery-beat", "evidence-rabbit-topology"] },
  { id: "interview-why-rabbit", question: "Why RabbitMQ?", shortAnswer: "It decouples cross-service state transitions and supports durable routing, per-consumer retries and DLQs.", deepAnswer: "The purchase flow does not require every service to be synchronously available. A topic exchange fans one fact to independent queues, while retry copies return only to the failed consumer rather than repeating successful subscribers.", evidenceIds: ["evidence-rabbit-topology", "evidence-rabbit-consumer"] },
  { id: "interview-why-redis", question: "Why Redis?", shortAnswer: "For short-lived sessions/rate state and bounded-stale read acceleration, never as stock authority.", deepAnswer: "Auth security state fails closed. Catalog and Inventory caches fail open to PostgreSQL. The differing failure policies follow data criticality rather than applying one generic cache rule.", evidenceIds: ["evidence-auth-cache", "evidence-category-cache", "evidence-stock-cache"] },
  { id: "interview-why-index", question: "Why is the outbox index ordered status, next_attempt_at, created_at?", shortAnswer: "It matches the relay's filter-then-oldest query.", deepAnswer: "Delivery status and due time narrow the eligible set; created_at then supplies stable oldest-first work. Reversing the order would make the leading column less useful for the worker's real predicate.", evidenceIds: ["evidence-outbox-lease"] },
  { id: "interview-why-transaction", question: "Where is the important transaction boundary?", shortAnswer: "Inside one service database: aggregate change plus outbox, or inbox plus side effect plus next outbox.", deepAnswer: "No distributed SQL transaction crosses services. The boundary deliberately converts cross-service atomicity into eventual consistency with durable facts and idempotent handlers.", evidenceIds: ["evidence-stock-service", "evidence-order-service", "evidence-rabbit-inbox"] },
  { id: "interview-overselling", question: "How is overselling prevented?", shortAnswer: "Inventory locks the stock row before checking and decrementing, then database CHECKs enforce counter invariants.", deepAnswer: "Redis is read acceleration only. The source-of-truth decision occurs under PostgreSQL FOR UPDATE; concurrent buyers serialize on the same row.", evidenceIds: ["evidence-stock-repo", "evidence-inventory-models"] },
  { id: "interview-duplicates", question: "What happens with duplicate events?", shortAnswer: "processed_events makes the local handler transaction idempotent.", deepAnswer: "The message ID is stable across publish/retry. The consumer inserts it before mutation in the same transaction. If it already exists, the handler skips the side effect and ACKs.", evidenceIds: ["evidence-rabbit-inbox", "evidence-rabbit-consumer"] },
  { id: "interview-service-down", question: "What happens if a service is down?", shortAnswer: "Synchronous callers fail immediately; asynchronous queues retain/retry work.", deepAnswer: "Inventory intentionally fails closed when Drops policy is unavailable. Event consumers can be offline while Rabbit queues accumulate within bounded policies; outbox relays retry broker failures. The interaction type determines the availability trade-off.", evidenceIds: ["evidence-drop-policy", "evidence-rabbit-topology"] },
  { id: "interview-eventual", question: "Why is eventual consistency acceptable?", shortAnswer: "Order, payment, stock and notification state can converge independently without making every API call depend on every service.", deepAnswer: "Local invariants remain strong. Cross-service temporary divergence is exposed through state machines and compensated by events. It is not acceptable for authoritative price/payment trust, which is why that current mock boundary is marked partial.", evidenceIds: ["evidence-audit"] },
  { id: "interview-lock-vs-constraint", question: "Why both a lock and a constraint?", shortAnswer: "The lock serializes the intended transition; the constraint rejects impossible persisted state if application logic fails.", deepAnswer: "They address different failure classes. FOR UPDATE coordinates concurrent writers. CHECK/UNIQUE remains the final database invariant and catches bugs or alternate write paths.", evidenceIds: ["evidence-stock-repo", "evidence-inventory-models"] },
];

const engineeringHighlights = [
  { id: "highlight-outbox", rank: 1, title: "Transactional outbox closes the DB/publish loss window", whyItMatters: "Business state and delivery intent survive process and broker failures.", mechanismId: "mechanism-outbox" },
  { id: "highlight-confirmed-delivery", rank: 2, title: "Confirmed mandatory publishing with tokenized leases", whyItMatters: "The relay marks delivery only after a broker outcome and scales without long SQL locks.", mechanismId: "mechanism-outbox" },
  { id: "highlight-inbox-outbox", rank: 3, title: "Transactional inbox composes with the next outbox", whyItMatters: "A duplicate inbound event cannot repeat local state or durable fan-out.", mechanismId: "mechanism-consumer-delivery" },
  { id: "highlight-retry-topology", rank: 4, title: "Per-consumer 5/30/120-second retry topology", whyItMatters: "One consumer failure does not replay work in already successful services.", mechanismId: "mechanism-consumer-delivery" },
  { id: "highlight-stock-lock", rank: 5, title: "PostgreSQL stock locks and CHECK invariants", whyItMatters: "Overselling protection remains correct without Redis.", mechanismId: "mechanism-stock-concurrency" },
  { id: "highlight-drop-advisory-lock", rank: 6, title: "Business-key advisory lock for drop limits", whyItMatters: "Concurrent requests for the same user/drop serialize without a global lock.", mechanismId: "mechanism-drop-limit" },
  { id: "highlight-revision-cache", rank: 7, title: "Revision-aware Lua cache writes", whyItMatters: "A delayed writer cannot overwrite a newer committed stock projection.", evidenceIds: ["evidence-stock-cache"] },
  { id: "highlight-batch-checkout", rank: 8, title: "Atomic Orders batch with locked promotion usage", whyItMatters: "All lines, deterministic discounts, usage and event intent commit together locally.", evidenceIds: ["evidence-order-service", "evidence-orders-models"] },
  { id: "highlight-key-isolation", rank: 9, title: "Verification-only JWT boundary and split key volumes", whyItMatters: "Downstream services cannot mint tokens because they never receive private signing material.", evidenceIds: ["evidence-jwt-verifier", "evidence-local-jwt-design"] },
  { id: "highlight-refresh-rotation", rank: 10, title: "Row-locked one-time refresh rotation", whyItMatters: "Replay revokes a session instead of extending a stolen credential.", mechanismId: "mechanism-refresh-rotation" },
  { id: "highlight-media-validation", rank: 11, title: "Direct upload with distrustful server-side validation", whyItMatters: "Large bytes bypass the API, but only decoded, bounded and checksummed objects become READY.", mechanismId: "mechanism-media-validation" },
  { id: "highlight-worker-health", rank: 12, title: "Worker health measures progress, not PID existence", whyItMatters: "A live-but-stuck relay or consumer becomes observable and eligible for guarded autoheal.", evidenceIds: ["evidence-heartbeat", "evidence-prometheus"] },
  { id: "highlight-queue-bounds", rank: 13, title: "Queue and DLQ resource bounds", whyItMatters: "A stopped consumer cannot grow broker memory/disk without limit.", evidenceIds: ["evidence-init-infra", "evidence-prometheus"] },
  { id: "highlight-failure-policy", rank: 14, title: "Redis failure policy follows data criticality", whyItMatters: "Derived caches preserve availability; session/rate security state does not fail open.", mechanismId: "mechanism-cache-policy" },
  { id: "highlight-wishlist-fanout", rank: 15, title: "Durable DropStarted to per-user notification fan-out", whyItMatters: "Inbox dedup and unique event keys make multi-user fan-out restart-safe.", evidenceIds: ["evidence-wishlist-consumer", "evidence-wishlist-repo"] },
];

const plannedCapabilities = [
  { id: "planned-real-payments", name: "Real payment provider, verified webhooks, refunds and reconciliation", status: STATUS.PLANNED },
  { id: "planned-notification-delivery", name: "Physical SMTP/provider notification delivery", status: STATUS.PLANNED },
  { id: "planned-tracing", name: "OpenTelemetry distributed tracing and trace-context propagation", status: STATUS.PLANNED },
  { id: "planned-secret-manager", name: "Managed secret storage and automated secret scanning", status: STATUS.PLANNED },
  { id: "planned-broker-ha", name: "RabbitMQ clustering/quorum topology and infrastructure DR", status: STATUS.UNCLEAR },
];

const heroStats = [
  { id: "stat-services", label: "Microservices", value: 9, methodology: "Generated public service registry and root runtime topology." },
  { id: "stat-databases", label: "Logical PostgreSQL databases", value: 9, methodology: "One service-owned logical database per backend service." },
  { id: "stat-events", label: "Integration event types", value: 27, methodology: "11 Auth identity events plus 16 business integration events." },
  { id: "stat-workers", label: "Long-running worker processes", value: 17, methodology: "7 outbox relays, 5 consumers, 4 Celery workers and singleton Celery Beat." },
  { id: "stat-queues", label: "Application RabbitMQ queues", value: 29, methodology: "5 event main + 15 retry + 5 DLQ queues, plus 4 Celery maintenance queues." },
  { id: "stat-redis", label: "Redis use cases", value: 5, methodology: "Session, touch throttle, rate counter, category cache and stock cache." },
  { id: "stat-test-suites", label: "Verified fast suites", value: 13, methodology: "9 service suites + shared JWT + shared Rabbit reliability + gateway + frontend during the 2026-08-14 audit." },
];

const systemMapLayers = [
  { id: "map-layer-http", label: "HTTP", protocols: ["HTTP REST"], defaultVisible: true },
  { id: "map-layer-events", label: "Events", protocols: ["AMQP 0-9-1 / aio-pika"], defaultVisible: true },
  { id: "map-layer-storage", label: "Storage", protocols: ["PostgreSQL", "S3 API"], defaultVisible: false },
  { id: "map-layer-redis", label: "Redis", protocols: ["Redis"], defaultVisible: false },
  { id: "map-layer-keys", label: "JWT keys", protocols: ["read-only filesystem volume"], defaultVisible: false },
  { id: "map-layer-celery", label: "Celery tasks", protocols: ["Celery", "Celery / AMQP"], defaultVisible: false },
];

const system = {
  id: "flashmarket", name: "FlashMarket", route: "/architecture", status: STATUS.PARTIAL,
  summary: "Nine FastAPI bounded contexts coordinate an e-commerce purchase flow through local PostgreSQL transactions, RabbitMQ choreography, service-owned Celery maintenance commands and deliberately non-authoritative Redis caches.",
  quickPaths: [
    { id: "quick-services", label: "Explore services", targetSectionId: "service-explorer" },
    { id: "quick-flow", label: "Follow a request", targetSectionId: "request-flow-explorer" },
    { id: "quick-reliability", label: "Inspect reliability", targetSectionId: "outbox-lab" },
  ],
  serviceIds: services.map((service) => service.id),
  infrastructureIds: infrastructure.map((component) => component.id),
  technologyIds: technologies.map((technology) => technology.id),
  heroStatIds: heroStats.map((stat) => stat.id),
  caveat: "The event/reliability platform is implemented; real payment authority, physical notification delivery and distributed tracing remain partial or planned.",
};

const projections = {
  heroStats,
  systemMapLayers,
  serviceExplorerSections: ["responsibility", "owns", "api", "internal-structure", "storage", "publishes", "consumes", "background-jobs", "engineering-decisions", "source-evidence"],
  labMechanismIds: mechanisms.map((mechanism) => mechanism.id),
  flowTabs: flows.map(({ id, name, status }) => ({ id, label: name, status })),
  interviewCardIds: interviewQuestions.map((item) => item.id),
  implementedIds: [...services, ...mechanisms, ...events].filter((item) => item.status === STATUS.IMPLEMENTED).map((item) => item.id),
  partialIds: [...services, ...mechanisms, ...events].filter((item) => item.status === STATUS.PARTIAL).map((item) => item.id),
  plannedIds: plannedCapabilities.filter((item) => item.status === STATUS.PLANNED).map((item) => item.id),
};

const architectureData = {
  meta: {
    schemaVersion: "1.0.0",
    auditedAt: "2026-08-14",
    sourceOfTruth: "docs/architecture/FLASHMARKET_ARCHITECTURE_AUDIT.md",
    route: "/architecture",
    relatedRoute: "/dev",
    contentLevels: ["overview", "service", "mechanism", "implementation-details"],
    countsAreAuditedSnapshots: true,
  },
  system,
  statuses: [
    { id: STATUS.IMPLEMENTED, label: "Implemented", meaning: "Confirmed by executable code/config/migration and usually tests." },
    { id: STATUS.PARTIAL, label: "Partial", meaning: "A substantial path exists but the business or operational boundary is incomplete." },
    { id: STATUS.PLANNED, label: "Planned", meaning: "Documented as future work without runtime implementation." },
    { id: STATUS.UNCLEAR, label: "Unclear", meaning: "The repository does not establish intent or production state." },
  ],
  technologies,
  services,
  infrastructure,
  connections,
  endpoints,
  events,
  exchanges,
  queues,
  workerProcesses,
  oneShotProcesses,
  celeryTasks,
  databases,
  tables,
  constraints,
  indexes,
  redisUseCases,
  mechanisms,
  flows,
  consistencyBoundaries,
  failureScenarios,
  interviewQuestions,
  engineeringHighlights,
  plannedCapabilities,
  evidence,
  projections,
};

export { STATUS as ARCHITECTURE_STATUS, architectureData };
export default architectureData;
