# Shared RabbitMQ Vhost Reliability Design

## Problem

Production deploy workflows configure each FlashMarket service with a different RabbitMQ virtual host, while the services exchange events through the same `flashmarket.events` topic exchange. RabbitMQ virtual hosts are isolated namespaces, so an exchange declared in one vhost cannot deliver messages to queues in another.

Wishlist is currently configured for the `flashmarket` vhost, but that vhost does not exist in production. RabbitMQ therefore closes the connection during `Connection.Open`, the Wishlist consumer exits with code 1, and Docker continuously restarts it. The observed container had `OOMKilled=false` and more than eleven thousand restarts. Creating only the missing vhost would stop the restart loop, but events published by Drops in its separate vhost would still never reach Wishlist.

## Goal

Make cross-service RabbitMQ delivery work consistently and prevent deployment from reporting success when a required consumer cannot connect to the broker.

Success means:

- every FlashMarket publisher and consumer uses the `flashmarket` vhost;
- the shared vhost exists and the infrastructure user has configure, write, and read permissions;
- a failed vhost bootstrap fails deployment instead of becoming a warning;
- the Wishlist consumer stays alive across a temporary broker outage;
- deployment verifies both the API and the consumer;
- service-specific databases remain unchanged.

Memory limits, swap, and host capacity are a separate reliability project and are not changed by this fix.

## Considered Approaches

### Create only the missing Wishlist vhost

This immediately stops the current restart loop, but Drops remains connected to another vhost. Wishlist notifications therefore still do not work. This is useful only as incident containment.

### Bridge service-specific vhosts

RabbitMQ Federation or Shovel could copy events between vhosts. It adds routing configuration, more queues, more failure modes, and more memory usage on a four-gigabyte host. There is no current requirement for tenant-grade isolation, so this complexity is not justified.

### Use one application vhost

All event-driven services use the `flashmarket` vhost and retain logical isolation through the durable topic exchange, routing keys, and named queues. This matches the existing event contracts and local Compose configuration. This is the chosen approach.

## Configuration Changes

Use this URI shape everywhere:

`amqp://<user>:<password>@shide-rabbitmq:5672/flashmarket`

Update production workflow environment rendering for Auth, Catalog, Drops, Inventory, Orders, Payments, Notifications, and Wishlist. Update checked-in environment examples so local, test, and production documentation agree. Existing exchange names and routing keys do not change.

The current service-specific vhosts are not deleted. Keeping them makes rollback possible and avoids destructive cleanup during the migration.

## Bootstrap and Failure Handling

`docker/init-infra.py` remains responsible for creating the vhost and granting permissions through the RabbitMQ management API. For a configured RabbitMQ URL, failure to create the vhost or set permissions becomes fatal. The migration/bootstrap container must exit non-zero, causing deployment to stop before replacing running services.

The bootstrap remains idempotent: creating an existing vhost and reapplying the same permissions succeeds.

Wishlist consumer startup gains an outer reconnect loop with bounded exponential backoff. `aio_pika.connect_robust` continues to handle interruptions after a successful connection; the outer loop covers initial connection failures. A temporary RabbitMQ outage must not terminate the process and trigger Docker restart churn. Cancellation still exits promptly during deployment or shutdown.

## Deployment Sequence

Production migration uses an additive sequence:

1. Create the `flashmarket` vhost and grant the infrastructure user full permissions.
2. Deploy consumers and publishers configured for `flashmarket`.
3. Verify APIs, worker container state, and RabbitMQ connections.
4. Leave old service-specific vhosts intact for rollback.

Changing all workflows in one repository commit prevents future deployments from reintroducing mixed vhosts. Services may be redeployed sequentially; during the transition, old and new vhosts are temporarily isolated, so deployment should be completed as one maintenance operation. Transactional outbox records not yet published will be delivered after their worker moves to the shared vhost. Events already marked published in old vhosts are not automatically replayed.

## Deployment Verification

Wishlist deployment must reject a consumer that exits during the initial observation window. In addition to checking `.State.Running`, it checks that the restart count does not increase while the API readiness check completes. On failure, the workflow prints bounded consumer logs.

Repository contract tests enforce one canonical RabbitMQ vhost across deployment workflows and examples. This prevents configuration drift between independently deployed services.

## Testing

- Unit-test vhost parsing and fatal bootstrap behavior without contacting production infrastructure.
- Test Wishlist initial connection retry and cancellation behavior.
- Assert every event-driven production workflow renders `/flashmarket`.
- Assert environment examples use the same vhost.
- Run existing service tests, deployment workflow contract tests, and the purchase-saga tests.
- Render affected Compose configurations with representative environment values.

## Operational Verification

After deployment:

- `rabbitmqctl list_vhosts name` contains `flashmarket`;
- `rabbitmqctl list_permissions -p flashmarket` grants the infrastructure user `.*` for configure, write, and read;
- `rabbitmqctl list_connections user vhost peer_host state` shows FlashMarket workers on `flashmarket`;
- Wishlist consumer remains `Up` and its restart count is stable;
- a `drops.DropStarted` event produces the expected Wishlist/Notifications processing;
- Orders, Inventory, Payments, and Notifications saga tests still complete.

## Rollback

Restore the previous service-specific URLs and redeploy the affected services. Old vhosts remain present, so rollback does not require recreating broker resources. No database migration or destructive RabbitMQ operation is part of this change.
