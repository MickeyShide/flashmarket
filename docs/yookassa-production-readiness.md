# YooKassa production-readiness tracker

Updated: 2026-08-25

This is the living implementation tracker for the test-only, production-grade YooKassa architecture described in [the approved design](superpowers/specs/2026-08-25-yookassa-production-hardening-design.md).

Status markers:

- `[ ]` planned;
- `[~]` in progress;
- `[x]` implemented and verified;
- `[!]` externally blocked with a documented reason.

Live payments must remain disabled. An item is marked complete only after its relevant automated checks pass.

## 1. Baseline and CI

- [x] Smart Payment redirect, verified webhook state, full test refund, and return page baseline.
- [x] Pydantic parses `PAYMENTS_YOOKASSA_TEST_MODE_REQUIRED=true` while rejecting `false`.
- [x] Every public payment route has an explicit OpenAPI access classification.
- [x] Repository OpenAPI artifacts regenerate successfully.
- [x] Approved production-hardening design is committed.
- [x] Baseline pushed to `origin/main` (`d5f4626`).

## 2. Provider HTTP resilience

- [x] One process-lifetime pooled `httpx.AsyncClient` for API and worker processes.
- [x] Explicit connection/keep-alive pool limits.
- [x] Separate read/write concurrency gates.
- [x] Typed provider error taxonomy for rejection, rate limiting, and uncertain results.
- [x] Increasing backoff with jitter; no zero-delay retry.
- [x] Interactive retry budget separated from durable worker reconciliation retries.
- [x] Circuit breaker that does not turn uncertain writes into definite failures.
- [x] Sanitized provider error IDs and latency/concurrency metrics.

## 3. Durable provider operations

- [x] Additive `provider_operations` migration and repository.
- [x] Immutable canonical request payload and request hash.
- [x] Stable idempotence key bound to the request hash.
- [x] States `NEW`, `IN_FLIGHT`, `UNKNOWN`, `SUCCEEDED`, `FAILED`, `QUARANTINED`.
- [x] Never automatically POST an unknown operation after 24 hours.
- [x] Crash-after-provider-success recovery tests.
- [x] Bounded list-based recovery when no external ID is known.

## 4. Webhook ingestion

- [ ] Additive `webhook_inbox` migration and repository.
- [ ] Semantic deduplication without relying on a provider event ID.
- [ ] Handler persists then returns HTTP 200 without provider network I/O.
- [ ] Inbox worker verifies current provider state through GET.
- [ ] Duplicate, out-of-order, malformed, and permanent-mismatch handling.
- [ ] Retry and quarantine state with bounded attempts.
- [ ] Dedicated gateway location, body limit, source allowlist, and independent burst policy.

## 5. Reconciliation

- [~] Worker claims bounded batches with `FOR UPDATE SKIP LOCKED` (provider operations done; other queues pending).
- [~] No database transaction remains open during provider I/O (checkout/recovery done; refunds/webhooks pending).
- [x] Reconcile unknown create operations.
- [ ] Reconcile active/stale payment attempts.
- [ ] Reconcile pending refunds, including canceled refunds without a webhook.
- [ ] Backoff, jitter, heartbeat, lag, and quarantine metrics.

## 6. Multiple payment attempts

- [ ] Additive `payment_attempts` migration and repository.
- [ ] At most one active attempt per order-level payment.
- [ ] Concurrent checkout calls converge on one attempt and operation.
- [ ] Expired/canceled attempt creates a new attempt and idempotence key.
- [ ] Existing payment API remains compatible through the aggregate/read model.
- [ ] HTTP 202 preparation response exposes stable attempt state and retry hint.

## 7. Normalized refunds

- [ ] Additive `refunds` migration and repository.
- [ ] Full and partial refund accounting.
- [ ] Concurrent refundable-balance protection.
- [ ] Multiple refunds cannot exceed the captured amount.
- [ ] `rejected_by_timeout` creates a new operation/key with backoff.
- [ ] `insufficient_funds`, `rejected_by_payee`, and `general_decline` stop blind retries.
- [ ] Compatibility fields remain synchronized during migration.

## 8. Frontend flow

- [ ] Checkout handles immediate redirect and HTTP 202 preparation.
- [ ] Preparation and return polling use increasing delay plus jitter.
- [ ] Polling pauses in hidden tabs and remains bounded.
- [ ] Expired/canceled attempts offer a new attempt without a new order.
- [ ] Frontend tests and production build pass.

## 9. Ledger, receipts, and reports

- [ ] Append-only `financial_ledger` migration and idempotent posting.
- [ ] Successful payment and refund transitions create ledger entries atomically.
- [ ] Receipt contracts use immutable order-line snapshots and exact totals.
- [ ] Validate item limits, VAT code, subject, mode, measure, and customer contact.
- [ ] Persist simulated test-mode receipt state.
- [ ] Daily report import model, content-hash idempotency, and Moscow business date.
- [ ] Deterministic report fixtures and discrepancy quarantine.
- [!] Actual production fiscal register connection requires merchant/legal setup.
- [!] Actual YooKassa daily report retrieval requires a production merchant account.

## 10. Observability and final verification

- [ ] Provider latency/outcome, concurrency, and circuit metrics.
- [ ] Unknown-operation age/count metrics and alerts.
- [ ] Webhook inbox depth, lag, retries, and quarantine metrics.
- [ ] Attempt/refund/reconciliation age and drift metrics.
- [ ] No high-cardinality financial identifiers in metric labels.
- [ ] Migration upgrade verification.
- [ ] Payments unit/integration/concurrency suite.
- [ ] Ruff for changed code and strict mypy.
- [ ] Repository OpenAPI generation and tests.
- [ ] Frontend tests and production build.
- [ ] Final security and failure-mode audit.
- [ ] Final commits pushed to `origin/main`.

## Verification log

| Date | Stage | Checks | Result |
|---|---|---|---|
| 2026-08-25 | CI repair | Payments `25 passed`; strict mypy; changed-file Ruff/format; OpenAPI generation; OpenAPI tests `4 passed` | Pass |
| 2026-08-25 | Provider resilience | Payments `29 passed`; strict mypy; scoped Ruff/format | Pass |
| 2026-08-25 | Durable provider operations | Payments `31 passed`; strict mypy; scoped Ruff/format | Pass |
