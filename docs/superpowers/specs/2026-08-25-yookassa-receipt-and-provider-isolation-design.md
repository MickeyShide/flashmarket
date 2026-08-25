# YooKassa receipt delivery and provider isolation design

Date: 2026-08-25

Status: approved approach, pending written-spec review

## Context

The first production-hosted test-shop checkout reached YooKassa but was rejected
with HTTP 400:

```json
{
  "code": "invalid_request",
  "description": "Receipt is missing or illegal",
  "parameter": "receipt"
}
```

The payment request itself used the documented Smart Payment shape: exact RUB
amount, immediate capture, redirect confirmation, absolute return URL, stable
idempotence key, description, and metadata. The rejection occurred because the
test shop requires receipt data while FlashMarket only persisted a local receipt
snapshot and deliberately did not send it to YooKassa.

The investigation also found a separate provider-isolation defect. After the
runtime provider changed from `mock` to `yookassa`, a reconciliation worker sent
an old `mock-*` external identifier to YooKassa. Repository claim queries currently
select due financial work without restricting it to the configured provider.

Finally, the adapter logs only the provider error identifier and status. It drops
the safe `code`, `description`, and `parameter` fields that are required to
diagnose HTTP 400 responses.

## Goals

- Send a validated YooKassa `receipt` with every payment creation for a shop that
  requires receipt registration.
- Use the authenticated account email as the receipt customer contact.
- Reuse the authoritative immutable receipt item snapshot already produced by
  Orders and stored by Payments.
- Support orders created before customer contact was added by enriching a
  `NEEDS_CONTACT` snapshot exactly once before the first provider write.
- Send a consistent receipt item for full and partial refunds.
- Prevent work created for one provider from being sent to another provider.
- Preserve generic public API errors while logging safe, actionable YooKassa
  error fields.
- Keep all financial writes idempotent and avoid holding database transactions
  during provider network I/O.

## Non-goals

- Enabling live payments. The existing test-shop-only guard remains mandatory.
- Supporting arbitrary checkout-supplied item descriptions, prices, VAT codes,
  or totals. These remain server-authoritative.
- Looking up profile data synchronously from Auth during a payment-provider call.
- Migrating or replaying old mock payments as YooKassa payments automatically.
- Implementing a complete production fiscal-operator lifecycle for a legal
  merchant. This change only supplies the receipt contract required by the
  configured YooKassa test shop and records its submission state.

## Chosen approach

FlashMarket will propagate the account email into the receipt snapshot when a new
order is created. The checkout request will also carry that email so a legacy
snapshot in `NEEDS_CONTACT` can be enriched without recreating the order. Payments
will load and validate the stored snapshot, create a provider-neutral receipt
value object, and pass it through the provider contract. The YooKassa adapter will
be solely responsible for converting that value object to the YooKassa JSON shape.

This preserves the authoritative item data and avoids coupling Payments to Auth.
The email is a delivery contact, not an authorization claim; order ownership is
still established exclusively by the verified JWT principal before the email is
accepted.

## API and event changes

### Order creation

`CreateOrderRequest` and `CreateOrderBatchRequest` will accept one validated
receipt email. The frontend will populate it from the authenticated profile, not
from a new free-form field. Orders will copy it into `receipt_snapshot.customer`
for each emitted `PaymentRequested` event.

The email is normalized by trimming and lowercasing. It must satisfy the existing
receipt email contract and its length limit. Order item, amount, currency, tax,
subject, payment mode, and measure remain generated on the server.

### Checkout

`POST /api/v1/payments/orders/{order_id}/checkout` will accept a small optional
JSON body containing the receipt customer email. The body remains optional for
backward compatibility when the stored snapshot already has customer contact.

After verifying order ownership, Payments will lock the payment and its receipt:

1. If the snapshot already contains the same normalized email, continue.
2. If it has no customer and is `NEEDS_CONTACT`, attach the normalized email,
   regenerate canonical JSON and its hash, and mark it ready.
3. If no usable contact is available, return a domain validation error without
   contacting YooKassa.
4. If a different contact was already frozen, reject the mutation instead of
   silently changing fiscal input.

The snapshot becomes immutable once any provider create operation exists. Contact
enrichment and operation creation occur under the same database lock/transaction,
before network I/O.

## Provider receipt contract

A provider-neutral receipt contract will contain:

- customer email;
- currency (`RUB` for YooKassa);
- one to eighty items;
- item description, decimal quantity, exact integer minor-unit amount, VAT code,
  payment subject, payment mode, and measure.

The YooKassa adapter maps each item to:

```json
{
  "description": "Product name",
  "quantity": "1",
  "amount": {"value": "1590.00", "currency": "RUB"},
  "vat_code": 1,
  "payment_subject": "commodity",
  "payment_mode": "full_payment",
  "measure": "piece"
}
```

The sum of `quantity * amount` must equal the payment amount exactly before the
provider call. Floating-point arithmetic is prohibited. The full request payload,
including the receipt, is part of the canonical provider-operation hash so the
same idempotence key can never be reused with changed fiscal data.

## Refund receipts

YooKassa refunds will include receipt items derived from the original frozen
snapshot. Current FlashMarket payments contain one order item per payment, so:

- a full refund uses the original item amount;
- a partial refund uses the requested refund amount with quantity `1`, while
  retaining the original description, VAT code, subject, payment mode, and
  measure.

The refund receipt total must equal the refund amount exactly and is included in
the refund provider-operation hash. No client-supplied fiscal item fields are
accepted.

## Receipt persistence states

The local receipt input lifecycle will distinguish:

- `NEEDS_CONTACT`: authoritative items exist but customer contact is absent;
- `READY`: complete validated snapshot, not yet accepted in a provider request;
- `SUBMITTED`: YooKassa accepted a payment creation containing the receipt;
- `INVALID`: the stored snapshot cannot satisfy the provider contract.

Existing `SIMULATED` rows with valid customer contact will migrate to `READY`.
Rows without contact remain `NEEDS_CONTACT`. A successful create-payment response
sets the receipt to `SUBMITTED` in the same local transaction that records the
provider operation result. This state does not claim that a real fiscal operator
has completed registration.

## Provider isolation

All background claims must be scoped to the runtime provider:

- active payment attempts filter `PaymentAttemptModel.provider`;
- unknown provider operations join their payment and filter
  `PaymentModel.provider`;
- refunds join their payment and filter `PaymentModel.provider`;
- webhook inbox claims filter `WebhookInboxModel.provider`;
- reconciliation verifies that the payment, attempt, webhook, and runtime
  provider agree before applying remote data.

Old mock work will remain locally visible but will not be sent to YooKassa or
silently converted. New user action on a new YooKassa-backed order creates normal
YooKassa work. Cleanup or migration of abandoned mock orders is an explicit admin
operation outside this change.

## Error handling and observability

For provider HTTP errors with a JSON error object, the adapter will extract and
log only these safe fields:

- provider error ID;
- HTTP status;
- provider error code;
- provider parameter;
- provider description;
- operation name;
- FlashMarket request ID from request context when available.

Authorization headers, credentials, cookies, complete request bodies, and customer
contact are never logged. Public responses remain generic (`502` for a definite
provider rejection), with the FlashMarket request ID for support correlation.

Missing or invalid local receipt data is reported before provider I/O with a
specific application error. A definite YooKassa HTTP 400 marks only that concrete
attempt and operation failed. A later click creates a new attempt and a new
idempotence key. Timeout and transport ambiguity retain the existing `UNKNOWN`
financial safety behavior.

## Concurrency and failure behavior

- The payment row, active attempt, receipt, and provider operation are locked
  while fiscal input is frozen and the durable operation is prepared.
- The transaction is committed before calling YooKassa.
- Concurrent checkout calls converge on the same receipt snapshot, attempt,
  request hash, and idempotence key.
- A crash after YooKassa accepts the request follows the existing unknown-operation
  recovery path; the canonical payload includes the receipt.
- A failed earlier attempt does not reuse its idempotence key. The next attempt
  uses the same frozen receipt with a new operation identity.

## Compatibility and rollout

The checkout body is optional, so deployed older frontends continue to work for
new orders whose snapshots already contain email. The frontend and backend should
still deploy together so legacy `NEEDS_CONTACT` orders can be paid immediately.

The database migration is additive apart from the controlled receipt-status value
transition. Deployment order is:

1. apply the Payments migration;
2. deploy Payments API and workers with provider filtering and receipt support;
3. deploy Orders with receipt email propagation;
4. deploy the frontend checkout payload;
5. retry the failed test payment, producing attempt `a2` and a new idempotence key;
6. verify the payment and receipt request in the YooKassa event log;
7. verify that no subsequent YooKassa GET contains a `mock-*` identifier.

## Verification

Automated coverage must include:

- receipt serialization for exact RUB values and all supported fiscal fields;
- rejection of missing contact, malformed email, item-total mismatch, unsupported
  currency, and oversized item lists before network I/O;
- one-time legacy receipt contact enrichment and rejection after freeze;
- inclusion of receipt data in the provider-operation canonical hash;
- successful Smart Payment creation with receipt;
- full and partial refund receipt construction;
- concurrent checkout calls converging on one receipt and provider operation;
- failed attempt followed by a new attempt and idempotence key;
- provider error field logging with secret/contact redaction;
- provider-scoped claims for attempts, operations, refunds, and webhooks;
- a regression case proving `mock-*` IDs are never sent to YooKassa;
- Payments, Orders, frontend, OpenAPI, deployment, migration, lint, and type-check
  suites relevant to the changed files.

Production verification is complete only when the YooKassa test-shop log shows a
successful `POST /api/v3/payments` containing the expected receipt and the browser
redirects to the hosted confirmation page.
