# RabbitMQ Reliability Runbook

## Deployment order

1. Deploy infrastructure bootstrap first. It creates `flashmarket.retry`,
   `flashmarket.dead-letter`, all DLQs and main-queue policies.
2. Apply service migrations before restarting workers. The migrations add outbox retry and
   claim columns and create the Wishlist transactional outbox.
3. Start consumers before outbox relays so strict mandatory routes exist immediately.
4. Verify every consumer, outbox, scheduler and cleanup container is `healthy`.

## Fast checks

```bash
docker ps --format 'table {{.Names}}\t{{.Status}}'
docker exec shide-rabbitmq rabbitmqctl list_queues -p flashmarket \
  name messages_ready messages_unacknowledged consumers memory
docker exec shide-rabbitmq rabbitmqctl list_connections -p flashmarket \
  user peer_host state channels
```

Expected retry queues end in `.retry.1`, `.retry.2`, `.retry.3`; poison messages end in
`.dlq`. A non-zero DLQ is actionable. A retry queue may be briefly non-zero while its TTL
is running.

## Outbox diagnosis

For each service database, inspect unpublished rows ordered by `next_attempt_at`. A recent
`claimed_until` is normal; a claim older than 30 seconds is recoverable and will be picked
up automatically. Repeated `last_error` values usually identify an unroutable mandatory
event, broker outage, or publish timeout.

Do not edit `status` or delete outbox rows during an incident. Restore the route or broker
first and let scheduled retries deliver them.

## DLQ replay

1. Stop or scale down the affected consumer.
2. Inspect samples without automatic acknowledgement and fix the handler or payload issue.
3. Replay to the original topic routing key stored in
   `x-flashmarket-original-routing-key`, preserving `message_id` and `event_id`.
4. Purge or acknowledge the DLQ copy only after the replay is publisher-confirmed.
5. Start the consumer and watch both the main queue and DLQ.

Never bulk replay a DLQ into the main queue while the underlying failure remains; the
bounded retry chain will otherwise amplify load during an outage.

## Suggested alerts

- any `*.dlq` depth greater than zero for five minutes;
- main queue depth above 70% of 20,000 messages or 128 MiB;
- oldest unpublished outbox row older than five minutes;
- increasing `flashmarket_rabbitmq_publish_total{outcome!="confirmed"}`;
- any worker container unhealthy or repeatedly restarting;
- RabbitMQ memory/disk alarm active.
