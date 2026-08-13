# Host memory protection runbook

This runbook applies the host-side half of FlashMarket's OOM protection. Run it
on the production Linux host as an operator with `sudo` access. Repository
deployments enforce application-container limits separately.

## 1. Capture the baseline

```bash
free -h
swapon --show
docker stats --no-stream
docker ps --format 'table {{.Names}}\t{{.Status}}'
docker inspect $(docker ps -q) \
  --format '{{.Name}} limit={{.HostConfig.Memory}} reservation={{.HostConfig.MemoryReservation}} pids={{.HostConfig.PidsLimit}} oom={{.State.OOMKilled}} restarts={{.RestartCount}}'
```

Do not remove `drop-api`, `drop-nginx`, or any other apparently stale container
until its owner confirms that it is unused. Stop confirmed obsolete containers
before changing memory limits so the new baseline is meaningful.

## 2. Create persistent 2 GiB swap

The reliability operations workflow performs this step idempotently with
`scripts/install-host-memory-protection.sh`. For a manual rollout, run that
script as root from a verified repository checkout:

```bash
sudo sh scripts/install-host-memory-protection.sh
```

The script refuses to overwrite an existing `/swapfile` unless it is already a
valid swap area. The equivalent low-level commands are retained below for
incident recovery and review.

The following target is deliberately explicit. Do not substitute a broad or
computed path.

```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
grep -q '^/swapfile ' /etc/fstab || \
  echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
printf 'vm.swappiness=10\n' | sudo tee /etc/sysctl.d/99-flashmarket-memory.conf
sudo sysctl --system
free -h
swapon --show
sysctl vm.swappiness
```

Expected result: 2 GiB swap is visible and `vm.swappiness = 10`. Swap is a
shock absorber, not additional working capacity.

## 3. Validate the application Compose model

In every deployed service directory:

```bash
docker compose --env-file .env config >/tmp/flashmarket-compose-rendered.yml
grep -E 'mem_limit|mem_reservation|pids_limit|max-size|max-file' \
  /tmp/flashmarket-compose-rendered.yml
```

After deployment, verify the effective cgroup values:

```bash
docker inspect $(docker ps -q --filter 'name=flashmarket-') \
  --format '{{.Name}} limit={{.HostConfig.Memory}} reservation={{.HostConfig.MemoryReservation}} pids={{.HostConfig.PidsLimit}}'
```

Roll out maintenance workers first, then event workers, standard APIs, and
finally Auth/Inventory/Orders/Payments. Observe each group for at least ten
minutes:

```bash
watch -n 5 'free -h; docker stats --no-stream; docker ps --format "table {{.Names}}\t{{.Status}}"'
```

## 4. External infrastructure recommendations

The observability Compose project is outside this repository. Measure its
24-hour peaks before applying these starting ceilings:

| Container | Limit |
|---|---:|
| PostgreSQL | 512 MiB |
| RabbitMQ | 384 MiB |
| Redis | 128 MiB |
| Prometheus | 384 MiB |
| Grafana | 256 MiB |
| Loki | 256 MiB |
| MinIO | 256 MiB |
| Exporters and agents combined | 256 MiB |

For PostgreSQL, first confirm `shared_buffers`, `work_mem`, and observed
connections. For RabbitMQ, confirm the configured memory watermark. For
Prometheus and Loki, shorten retention before imposing a ceiling below their
measured peak.

## 5. Alert rules

Adapt metric labels to the installed node-exporter/cAdvisor version:

```yaml
groups:
  - name: flashmarket-memory
    rules:
      - alert: HostMemoryLow
        expr: node_memory_MemAvailable_bytes < 512 * 1024 * 1024
        for: 5m
        labels: {severity: critical}
        annotations: {summary: "Host available memory is below 512 MiB"}

      - alert: HostSwapInUse
        expr: node_memory_SwapTotal_bytes - node_memory_SwapFree_bytes > 512 * 1024 * 1024
        for: 10m
        labels: {severity: warning}
        annotations: {summary: "Host swap use exceeds 512 MiB"}

      - alert: ContainerMemoryNearLimit
        expr: container_memory_working_set_bytes / container_spec_memory_limit_bytes > 0.85
        for: 5m
        labels: {severity: warning}
        annotations: {summary: "Container memory exceeds 85% of its limit"}

      - alert: ContainerRestarting
        expr: changes(container_start_time_seconds[15m]) > 2
        labels: {severity: critical}
        annotations: {summary: "Container restarted repeatedly"}
```

Docker exposes `OOMKilled` through `docker inspect`; if the installed metrics
stack does not export it, run this lightweight diagnostic from the host and
alert on any `true` result:

```bash
docker inspect $(docker ps -aq) \
  --format '{{.Name}} {{.State.OOMKilled}} {{.RestartCount}}' | grep ' true '
```

## 6. Controlled staging smoke test

Do not run this on production. On a staging Linux host, start a disposable
container with a 64 MiB limit and allocate more than that. Confirm only the
disposable container is OOM-killed and critical containers remain healthy.

## Rollback

Redeploy the previous Compose revision to remove application limits. Leave swap
enabled while investigating; disabling swap under load can itself exhaust RAM.
If swap removal is later required, first verify enough available memory, then
run `sudo swapoff /swapfile`, remove the exact `/swapfile` entry from
`/etc/fstab`, and delete only `/swapfile`.
