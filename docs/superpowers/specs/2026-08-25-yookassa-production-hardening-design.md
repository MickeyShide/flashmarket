# YooKassa Production Hardening Design

**Date:** 2026-08-25  
**Status:** Approved in conversation; awaiting written-spec review  
**Scope:** Make the existing YooKassa Smart Payment integration operationally safe under load while preserving a mandatory test-only mode.

## Context

FlashMarket already has a test-only YooKassa Smart Payment integration with server-authoritative amounts, one-stage capture, redirect confirmation, provider status verification, transactional outbox events, refunds, and a frontend return page.

The integration is suitable for test payments but is not yet safe for production-like load. Its provider calls do not use a shared connection pool, retries have no meaningful delay, webhook processing performs synchronous provider I/O, database transactions may remain open around network calls, one order supports only one payment attempt, and there is no durable reconciliation process for uncertain operations.

The owner does not currently have a legal entity, individual entrepreneur status, or self-employed status. The implementation must therefore remain technically incapable of accepting live payments. Production-grade architecture will be implemented and tested exclusively against YooKassa test mode.

## Goals

- Keep the existing Payments service as the sole owner of financial state.
- Preserve the public API where compatibility is practical.
- Make payment creation, webhook delivery, reconciliation, and refunds safe under concurrency and transient provider failures.
- Prevent duplicate financial operations across process crashes and YooKassa's 24-hour idempotency window.
- Support multiple payment attempts for one order and multiple refunds for one successful payment.
- Avoid holding database connections or locks during provider network calls.
- Provide durable operational state, observability, contract tests, and a maintained readiness checklist.
- Preserve two independent live-payment guards: configuration must require test mode, and every provider object must contain `test: true` before it can affect local state.

## Non-goals and external blockers

- Enabling live payments is out of scope.
- Supplying live credentials, signing a YooKassa contract, configuring a production merchant account, and connecting a fiscal register are externally blocked.
- Fetching actual daily merchant reports is externally blocked without a production account. The repository will provide import interfaces, durable reconciliation state, and test fixtures.
- This work will not collect raw bank card data. Smart Payment remains a hosted redirect flow.

## Chosen approach

Use an evolutionary, additive redesign inside the existing Payments service. New normalized tables and workers become the source of operational truth while the current `payments` table remains a compatibility aggregate/read model during migration.

This approach is preferred over minimal patches because minimal patches cannot safely represent repeated attempts or multiple refunds. It is preferred over a full replacement service because the existing service already has useful domain rules, outbox infrastructure, authentication, and integration tests.

## Domain model

### Payment aggregate

The existing `payments` row remains the order-level compatibility aggregate. It stores the authoritative order, user, total amount, currency, and summarized current state expected by Orders and the existing frontend.

### PaymentAttempt

Each attempt to pay an order is represented separately.

Required fields include:

- local attempt identifier and order-level payment identifier;
- monotonically increasing attempt number;
- amount and currency copied from the immutable order payment snapshot;
- provider and provider object identifier;
- local and provider statuses;
- confirmation URL and provider expiration time;
- provider cancellation party and reason;
- test-mode flag;
- creation and update timestamps.

An order may have many final attempts but at most one active attempt. A partial unique index enforces the active-attempt invariant.

### ProviderOperation

Every financial POST sent to YooKassa has a durable operation row.

Required fields include:

- operation type (`create_payment`, `create_refund`);
- related local entity identifier;
- immutable idempotence key;
- canonical request payload and request hash;
- state (`NEW`, `IN_FLIGHT`, `UNKNOWN`, `SUCCEEDED`, `FAILED`, `QUARANTINED`);
- provider object identifier when known;
- first request, last attempt, and next attempt timestamps;
- attempt count;
- last HTTP/error classification and sanitized response snapshot.

The same idempotence key may only be used with the same request hash. An unknown POST must never be automatically submitted after 24 hours from its first request. Such an operation is reconciled through bounded provider reads/listing or moved to quarantine.

### Refund

Refunds are separate entities rather than fields on the payment aggregate. Each refund stores its own amount, currency, provider ID, status, cancellation details, reason, and timestamps. The sum of successful and in-flight refunds cannot exceed the captured payment amount.

### WebhookInbox

Every accepted provider notification is stored durably before acknowledgment. Because YooKassa notifications do not expose a standalone event identifier, semantic deduplication uses provider, object type, external object ID, event, and target status. The raw body and source address are retained with a bounded size for diagnosis.

Inbox states are `PENDING`, `PROCESSING`, `PROCESSED`, `RETRY`, and `QUARANTINED`.

### FinancialLedger and reconciliation

An append-only ledger records successful payments, successful refunds, provider income amount/fees when available, and report reconciliation adjustments. Ledger entries are idempotent by provider object and financial event type. Existing mutable payment state is not used as the accounting history.

Daily report imports are stored with a content hash, merchant date in Europe/Moscow, import status, and per-line match status. Importing the same report twice is harmless. Discrepancies are quarantined for review and never mutate order state automatically.

## Core invariants

- Payment amount and currency originate only from the immutable order payment snapshot.
- A provider operation's request body cannot change after its first send.
- A provider POST with an uncertain result is not automatically retried after the provider's 24-hour idempotency window.
- Browser redirects and return URLs never prove payment success.
- Only a server-fetched and fully verified YooKassa object can change financial state.
- Provider amount, currency, metadata, external identifier, and `test` flag must match local state.
- Domain state changes and emitted outbox events commit atomically.
- No database transaction or row lock spans a provider network call.
- Secrets and full provider payloads containing sensitive data are never logged.
- Live mode remains impossible until a future, explicit design removes both test-only guards.

## Payment checkout flow

Checkout uses a hybrid fast path:

1. In a short transaction, create or reuse the active `PaymentAttempt` and claim a `ProviderOperation`.
2. Commit and release the database connection.
3. Call YooKassa through a process-lifetime pooled HTTP client and a bounded concurrency gate.
4. On a quick successful response, verify it and persist the provider ID, status, confirmation URL, and sanitized response in a second short transaction.
5. Return the confirmation URL to the client.
6. On a transport timeout, HTTP 429, or HTTP 5xx, mark the operation `UNKNOWN`, return HTTP 202 with a stable local operation/attempt reference, and let reconciliation continue.
7. On a permanent 4xx request error, mark the operation failed and expose a sanitized failure state.

Concurrent checkout calls converge on the same active attempt and provider operation. If an existing attempt is canceled or its confirmation period has expired, a new attempt with a new idempotence key is created.

## Provider client and resilience

One `httpx.AsyncClient` is created per process in application/worker lifespan and closed at shutdown. It uses explicit connect, read, write, and pool timeouts plus bounded connection and keep-alive pools.

Provider concurrency is limited independently for reads and financial writes. Retries use increasing delay with randomized jitter. Interactive requests perform at most one short retry; durable background workers own longer retries.

Error classes distinguish:

- invalid credentials/authorization;
- permanent request rejection;
- provider rate limiting;
- uncertain transport or server result;
- malformed provider response;
- local verification mismatch.

A circuit breaker prevents a YooKassa outage from consuming every API worker or database connection. It must not convert uncertain financial writes into definite failures.

## Webhook flow

The gateway defines a dedicated exact/prefix location for YooKassa callbacks before the general payments route. It applies HTTPS, body-size limits, YooKassa source allowlisting, and a separate technical burst policy. Published source ranges are configuration, not application constants, so they can be updated when YooKassa changes them.

The HTTP handler performs only bounded parsing and a durable inbox insert. It responds with HTTP 200 after the insert commits. If durable storage is unavailable, it returns a non-200 response so YooKassa retries delivery.

An inbox worker:

1. claims rows with `FOR UPDATE SKIP LOCKED`;
2. retrieves the current provider object through GET;
3. verifies identity, amount, currency, metadata, and test mode;
4. applies a legal state-machine transition in a short transaction;
5. creates outbox and ledger entries atomically;
6. marks the inbox event processed.

Permanent malformed or mismatched events are quarantined and acknowledged rather than producing a 24-hour redelivery storm. Duplicate and out-of-order notifications are harmless because the worker retrieves current provider state and transitions are monotonic.

## Reconciliation workers

Reconciliation workers process uncertain provider operations, active payment attempts, pending refunds, and stale inbox events. Work is claimed in bounded batches using `FOR UPDATE SKIP LOCKED`; the transaction is closed before network I/O.

Each item has `next_attempt_at`, attempt count, and last error classification. Backoff is increasing and includes jitter. Workers have independent concurrency gates and heartbeat/age metrics.

For an unknown create operation approaching 24 hours, reconciliation first uses known provider identifiers. If none is known, it performs a bounded payment-list scan around the original request time and matches strict metadata and amount. Failure to establish a unique match moves the operation to quarantine; it never causes a blind POST after 24 hours.

## Refund flow

Refund creation reserves refundable balance and creates a durable provider operation in a short transaction. The provider call occurs outside the transaction, followed by a short result transaction.

Cancellation reasons have explicit policy:

- `rejected_by_timeout`: create a new operation with a new key and increasing delay;
- `insufficient_funds`: stop automatic retry and alert operations;
- `rejected_by_payee`: require resolution before a new attempt;
- `general_decline`: quarantine for manual investigation.

Pending refunds are reconciled by GET because the standard webhook set only guarantees a successful-refund event. Partial and concurrent refunds are protected by locked/CAS refundable-balance accounting.

## Frontend behavior

The existing hosted redirect remains. Checkout handles both immediate success and HTTP 202:

- immediate confirmation URL: store the order reference and redirect;
- preparing/unknown: display a stable preparation state and poll the local attempt endpoint using backoff and jitter;
- canceled/expired attempt: offer a new attempt without creating a new order;
- return page: poll local state with increasing delay, stop on final state, and never call YooKassa directly.

Polling is bounded and visibility-aware so hidden tabs and large traffic bursts do not generate synchronized requests.

## Fiscalization and reports

Receipt payloads are built from an immutable order-line snapshot and validate exact totals, item limits, quantity precision, VAT code, payment subject, payment mode, measure, and customer contact requirements.

Because the merchant is test-only, the implementation provides receipt interfaces, schemas, fixtures, persistence, and simulated processing without enabling live fiscalization.

Daily report reconciliation provides an importer and deterministic test fixtures. Actual report retrieval remains externally blocked. Report dates are interpreted in Europe/Moscow while internal timestamps remain UTC.

## Observability

Metrics must avoid payment/order IDs as labels. Required signals include:

- provider request count and latency by operation/outcome;
- provider concurrency saturation and circuit state;
- age/count of unknown operations;
- webhook ingest latency, inbox depth, processing lag, retries, and quarantine count;
- active/expired payment attempts;
- pending/refused refund count and age;
- reconciliation batch duration and discrepancies;
- outbox age and worker heartbeat.

Structured logs use request/operation correlation IDs and sanitized provider error IDs. Alerts cover sustained unknown operations, webhook lag, reconciliation drift, circuit opening, and worker heartbeat loss.

## API and compatibility

Existing payment read endpoints remain available and read the compatibility aggregate. New attempt/operation status responses use HTTP 202 for in-progress preparation and include a retry hint. All public routes receive explicit `x-flashmarket-access` classification.

The project OpenAPI generator remains a required CI check. The current YooKassa OpenAPI specification and changelog are used for contract tests and periodic compatibility review, but generated third-party clients are not trusted without tests.

## Delivery plan and living tracker

Implementation state is maintained in `docs/yookassa-production-readiness.md` with these markers:

- `[ ]` planned;
- `[~]` in progress;
- `[x]` implemented and verified;
- `[!]` externally blocked with a documented reason.

The implementation sequence is:

1. Fix Pydantic environment parsing and explicit OpenAPI access metadata, then push.
2. Add the living tracker.
3. Introduce the pooled provider client, error taxonomy, backoff/jitter, and concurrency limits.
4. Add provider operations and safe unknown-operation recovery.
5. Add webhook inbox, dedicated gateway policy, and inbox worker.
6. Add reconciliation workers.
7. Add multiple payment attempts and expiry/retry behavior.
8. Add normalized refunds and reason-specific policies.
9. Update frontend HTTP 202 and polling behavior.
10. Add ledger, report import/reconciliation, receipt contracts, and operational metrics.
11. Run final security, concurrency, migration, OpenAPI, backend, and frontend verification.

Each implementation stage updates the tracker and is committed separately after relevant tests pass.

## Verification and completion criteria

Required verification includes:

- migration upgrade tests and schema constraints;
- unit and integration tests for Payments;
- Ruff and strict mypy;
- repository OpenAPI generation;
- frontend tests and production build when frontend changes;
- concurrent checkout and refund tests;
- repeated and out-of-order webhook tests;
- timeout after remote success and crash-before-local-commit tests;
- HTTP 429 and repeated HTTP 500 tests;
- lost-webhook reconciliation tests;
- 24-hour idempotency expiry tests;
- provider outage tests proving DB/HTTP pools remain bounded;
- mandatory rejection of `test: false`.

The work is complete when every in-repository item in the living tracker is verified, all required checks pass, changes are pushed, and only genuinely external tasks are marked `[!]`. Live payments remain disabled.
