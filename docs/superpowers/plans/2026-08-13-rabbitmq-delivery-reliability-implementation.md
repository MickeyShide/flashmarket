# RabbitMQ Delivery Reliability Implementation Plan

## Objective

Implement the approved RabbitMQ reliability design in independently testable
layers while preserving existing queue names and service behavior. Delivery is
at-least-once: no failure path may silently discard the only message copy, and
duplicate delivery remains an explicit handler responsibility.

## Task 1: Shared transport package

Create:

- `shared/rabbitmq_reliability/pyproject.toml`
- `shared/rabbitmq_reliability/rabbitmq_reliability/__init__.py`
- `shared/rabbitmq_reliability/rabbitmq_reliability/config.py`
- `shared/rabbitmq_reliability/rabbitmq_reliability/topology.py`
- `shared/rabbitmq_reliability/rabbitmq_reliability/delivery.py`
- `shared/rabbitmq_reliability/rabbitmq_reliability/reconnect.py`
- `shared/rabbitmq_reliability/rabbitmq_reliability/heartbeat.py`
- `shared/rabbitmq_reliability/tests/`

The package must:

1. Describe one main queue plus three TTL retry queues and one DLQ.
2. Declare retry/DLQ exchanges and bindings without mutating existing main
   queue arguments.
3. Preserve AMQP message properties when copying to retry/DLQ.
4. ACK only after confirmed failure-copy publication.
5. Requeue the original if moving it fails.
6. Expose `PermanentMessageError` and classify all other exceptions as
   transient.
7. Provide mandatory confirmed publish with a finite timeout.
8. Provide reconnect with exponential backoff, jitter, reset, and cancellation.
9. Provide atomic heartbeat writes and a CLI freshness check.

Test first for attempts, destinations, property preservation, ACK/requeue order,
confirmed publish failures, reconnect behavior, and heartbeat freshness.

## Task 2: Package integration

Modify service dependency metadata and Dockerfiles for Auth, Inventory, Orders,
Payments, Notifications, Wishlist, and Drops:

1. Add the shared path dependency.
2. Copy the shared package before `uv sync` in Docker builds.
3. Refresh lock files with `uv lock`.
4. Verify editable local installs and production frozen installs both resolve.

Auth only uses the confirmed-publish/reconnect/heartbeat subset. The package API
must remain compatible with installed `aio-pika` 9.x and 10.x.

## Task 3: Consumer delivery safety

Modify:

- `inventory/src/inventory/event_consumer.py`
- `orders/src/orders/event_consumer.py`
- `payments/src/payments/event_consumer.py`
- `notifications/src/notifications/event_consumer.py`
- `wishlist/src/wishlist/event_consumer.py`

For every consumer:

1. Open a confirmed channel with returned-message exceptions.
2. Declare common retry/DLQ topology around the existing main queue.
3. Parse payload validation errors as `PermanentMessageError`.
4. Delegate ACK/retry/DLQ movement to the shared delivery helper.
5. Use mandatory publishing with a five-second timeout.
6. Use the common outer reconnect loop.
7. Run a periodic heartbeat while connected.

Add or update service tests proving handler success, permanent DLQ, transient
retry, exhausted retry, move failure requeue, reconnect, and cancellation.

## Task 4: RabbitMQ policy bootstrap

Modify `docker/init-infra.py` and repository topology tests:

1. Apply one named policy per existing main queue through the management API.
2. Set main queue max length 20,000, max bytes 128 MiB, overflow
   `reject-publish-dlx`, the common DLX, and the queue-specific DLQ routing key.
3. Keep policy creation idempotent and fatal after bounded bootstrap retries.
4. URL-encode vhost and policy names.
5. Do not delete or redeclare existing queues.
6. Unit-test request paths and policy bodies without network access.

New retry queues receive only their finite stage TTL and return-to-main DLX
arguments. RabbitMQ exposes one DLX destination per queue, so an independent
overflow-to-DLQ route would conflict with normal retry expiry and create either
loss or a hot requeue loop. DLQs stay unbounded and have no TTL; retry depth is
monitored.

## Task 5: Outbox schema and reusable scheduling

Add migrations and model fields for Inventory, Orders, Payments, Notifications,
Drops, and Wishlist:

- `next_attempt_at` nullable timestamp;
- `last_error` nullable text;
- `claimed_until` nullable timestamp;
- `claim_token` nullable UUID/string;
- an index covering due unpublished work.

Wishlist additionally gains its outbox table with unique `event_key`, payload,
event type, attempts, status/published time, and the delivery-control fields.

Add shared pure functions for full-jitter backoff and sanitized error text.
Migration tests/contracts verify additive upgrade and non-destructive downgrade.

## Task 6: Safe outbox relays

Modify:

- `auth/src/auth_service/outbox_worker.py`
- `inventory/src/inventory/outbox_worker.py`
- `orders/src/orders/outbox_worker.py`
- `payments/src/payments/outbox_worker.py`
- `notifications/src/notifications/outbox_worker.py`
- `drops/src/drops/outbox_worker.py`
- create `wishlist/src/wishlist/outbox_worker.py`

For each relay:

1. Select only due, unpublished, unclaimed/expired rows.
2. Claim rows in a short transaction with a unique token and lease expiry.
3. Publish claimed events one at a time outside the claim transaction.
4. Use confirms, return exceptions, and timeout; require `mandatory=True` for
   downstream integration events and classify terminal events explicitly.
5. Complete success/failure in a short compare-by-claim-token transaction.
6. Schedule failure with exponential full jitter capped at five minutes.
7. Clear claims on completion and recover expired claims after crashes.
8. Sleep after every poll cycle so neither successful nor failed batches spin.
9. Use shared reconnect and heartbeat behavior.

Keep stable `message_id` and `event_id` headers. Tests cover unroutable
publication, timeout, backoff, competing claims, expired claim recovery, and
crash-window duplicate tolerance.

## Task 7: Transactional Wishlist fan-out

Modify Wishlist models/repositories/consumer:

1. On `drops.DropStarted`, query matching users and insert one outbox row per
   drop/user in the same database transaction.
2. Use `drop:<drop_id>:user:<user_id>` as the unique event key.
3. Treat unique conflicts/redelivery as already staged, not as transient errors.
4. Remove direct RabbitMQ publication from the inbound consumer.
5. Publish staged `wishlist.DropAvailable` through the Wishlist outbox relay.

Tests prove redelivery creates no duplicate outbox rows and a relay failure
leaves every unsent user retryable.

## Task 8: Worker heartbeat healthchecks

Modify the entrypoint, background loops, deploy Compose, and local Compose:

1. Give each worker a unique `/tmp/flashmarket-heartbeat/<role>.json` path.
2. Consumers heartbeat periodically while their topology/connection is active.
3. Outbox workers heartbeat after each completed poll.
4. Inventory expiry, Drops scheduler, Media cleanup, and Auth cleanup heartbeat
   after each completed tick.
5. Add Docker healthchecks invoking `python -m rabbitmq_reliability.heartbeat`
   for RabbitMQ-related workers and an equivalent available command for Media.
6. Ensure the stale threshold exceeds normal poll/heartbeat intervals.

Contract tests require a healthcheck for every production background service.

## Task 9: Settings, examples, metrics, and runbook

Add bounded/validated settings to relevant service configurations and
`.env.example` files:

- publish timeout;
- retry delays;
- reconnect bounds;
- queue bounds;
- outbox max backoff and claim lease;
- heartbeat path/interval/staleness.

Add shared delivery counters and worker success timestamps. Add service gauges
for oldest pending outbox age where practical. Document management commands for
listing main/retry/DLQ depths, inspecting bindings/policies, replaying by explicit
operator action, and rollback without queue purges.

## Task 10: Verification and commit

Run:

1. Shared reliability package unit tests, Ruff, and mypy.
2. Full tests for all changed backend services.
3. Root contract and purchase-saga tests.
4. Production and local Compose rendering.
5. Migration upgrade/downgrade checks where test infrastructure permits.
6. `git diff --check` and inspection for unrelated changes.

Record any integration test that requires a live RabbitMQ/PostgreSQL environment
as an explicit staging verification rather than silently skipping it. Commit the
implementation as one reliability change only after all locally available
checks pass.
