# RabbitMQ Reliability Runbook

## Deployment order

1. Deploy infrastructure bootstrap first. It creates `flashmarket.retry`,
   `flashmarket.dead-letter`, all DLQs and main-queue policies.
2. Apply service migrations before restarting workers. The migrations add outbox retry and
   claim columns and create the Wishlist transactional outbox.
3. Start consumers before outbox relays so strict mandatory routes exist immediately.
4. Verify every consumer, outbox, scheduler and cleanup container is `healthy`.
5. Install the host watchdog once as root:
   `sh scripts/install-worker-watchdog.sh /opt/flashmarket`.
6. Mount `deploy/prometheus/flashmarket-reliability.rules.yml` into Prometheus and merge
   `deploy/prometheus/scrape-config.example.yml` into its configuration. Route both
   `warning` and `critical` alerts to the production Alertmanager receiver.

The `Reliability Operations Deploy` workflow uploads the bundle and installs the
watchdog idempotently. Configure the protected server host key as the
`DEPLOY_KNOWN_HOSTS` environment secret (the literal `known_hosts` line verified out of
band). Set `PROMETHEUS_RULES_DIR` only when the host directory is mounted at
`/etc/prometheus/rules` in `shide-prometheus`; the workflow validates the rules inside
the running container before sending `SIGHUP`. The example scrape jobs still need to be
merged once because they depend on the external observability Compose topology.

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
is running. Main and retry queues are capped at 20,000 messages/128 MiB; DLQs are capped
at 50,000 messages/256 MiB. A full retry/DLQ rejects new publications instead of consuming
unbounded broker memory.

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

Use the guarded utility from any service image (credentials are read from `RABBITMQ_URL`):

```bash
flashmarket-dlq orders.events.dlq status
flashmarket-dlq orders.events.dlq replay --limit 20
flashmarket-dlq orders.events.dlq replay --limit 20 --yes
```

The middle command is intentionally a dry run. The final command republishes one message
at a time with mandatory routing and publisher confirms, then acknowledges the DLQ copy.

## Watchdog checks

```bash
systemctl status flashmarket-worker-watchdog.timer
journalctl -u flashmarket-worker-watchdog.service --since -1h
cat /var/lib/flashmarket/worker-watchdog.json
```

Only unhealthy containers with `flashmarket.autoheal=true` are eligible. Restarts are
rate-limited to one per container every five minutes, so a bad deploy cannot create a hot
restart loop.

## Suggested alerts

- any `*.dlq` depth greater than zero for five minutes;
- main queue depth above 70% of 20,000 messages or 128 MiB;
- oldest unpublished outbox row older than five minutes;
- increasing `flashmarket_rabbitmq_publish_total{outcome!="confirmed"}`;
- any worker container unhealthy or repeatedly restarting;
- RabbitMQ memory/disk alarm active.
