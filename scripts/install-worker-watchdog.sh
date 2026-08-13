#!/bin/sh
set -eu

repo_dir=${1:-/opt/flashmarket}
install -d -m 0755 /opt/flashmarket/scripts /var/lib/flashmarket
install -m 0755 "$repo_dir/scripts/flashmarket_worker_watchdog.py" \
  /opt/flashmarket/scripts/flashmarket_worker_watchdog.py
install -m 0644 "$repo_dir/deploy/systemd/flashmarket-worker-watchdog.service" \
  /etc/systemd/system/flashmarket-worker-watchdog.service
install -m 0644 "$repo_dir/deploy/systemd/flashmarket-worker-watchdog.timer" \
  /etc/systemd/system/flashmarket-worker-watchdog.timer
systemctl daemon-reload
systemctl enable --now flashmarket-worker-watchdog.timer
systemctl start flashmarket-worker-watchdog.service
