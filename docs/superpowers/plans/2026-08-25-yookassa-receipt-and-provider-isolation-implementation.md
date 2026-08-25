# YooKassa receipt delivery and provider isolation implementation plan

Date: 2026-08-25

Design: [YooKassa receipt delivery and provider isolation](../specs/2026-08-25-yookassa-receipt-and-provider-isolation-design.md)

## Commit 1: receipt contracts and YooKassa serialization

- Extend the provider-neutral payment/refund contracts with validated receipt values.
- Convert the existing canonical receipt snapshot without float arithmetic.
- Serialize payment and refund receipts in the YooKassa adapter.
- Parse and safely log YooKassa error code, parameter, description, and error ID.
- Add pure adapter and redaction tests.

## Commit 2: authoritative contact propagation and durable checkout

- Add normalized receipt email fields to single and batch order creation.
- Include the customer in `PaymentRequested.receipt_snapshot`.
- Add an optional checkout receipt-customer body for legacy orders.
- Lock, enrich, validate, and freeze the persisted receipt before provider operation creation.
- Include the canonical receipt in the provider-operation payload and hash.
- Mark accepted receipt input as submitted with the successful provider operation.
- Build exact full and partial refund receipts from the frozen snapshot.
- Add API, service, retry, concurrency, and refund tests.

## Commit 3: provider isolation

- Scope attempt, unknown-operation, refund, and webhook claims to the runtime provider.
- Verify provider agreement before applying remote state.
- Add a regression test proving `mock-*` identifiers are never sent to YooKassa.

## Commit 4: migration, generated artifacts, and rollout documentation

- Migrate receipt status values from `SIMULATED` to `READY`.
- Regenerate the repository OpenAPI artifacts.
- Update deployment and production-readiness tests if the API schema changes.
- Run Payments, Orders, frontend, migration, OpenAPI, lint, and type-check suites.
- Update the living readiness tracker with exact verification evidence.

## Production verification

- Push all commits and wait for affected deployment workflows.
- Retry the failed order to create a new attempt and idempotence key.
- Confirm YooKassa accepts `POST /api/v3/payments` with a receipt.
- Confirm the browser receives and follows `confirmation_url`.
- Confirm no new YooKassa request contains a `mock-*` payment identifier.
