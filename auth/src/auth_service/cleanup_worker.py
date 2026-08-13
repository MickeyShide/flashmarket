"""Periodic expired-session cleanup with health and metrics heartbeats."""

import subprocess
import sys
import time

from rabbitmq_reliability import ensure_worker_metrics_server, touch_heartbeat

HEARTBEAT_PATH = "/tmp/flashmarket-heartbeat.json"


def main() -> None:
    ensure_worker_metrics_server()
    while True:
        subprocess.run(
            [sys.executable, "-m", "auth_service.cli", "cleanup-expired"],
            check=True,
        )
        touch_heartbeat(HEARTBEAT_PATH, "auth_cleanup")
        time.sleep(3600)


if __name__ == "__main__":
    main()
