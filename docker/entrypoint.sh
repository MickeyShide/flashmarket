#!/usr/bin/env sh
set -e

CMD="$1"

ensure_prometheus_dir() {
    if [ -n "${PROMETHEUS_MULTIPROC_DIR:-}" ]; then
        mkdir -p "$PROMETHEUS_MULTIPROC_DIR"
        rm -f "$PROMETHEUS_MULTIPROC_DIR"/*.db
    fi
}

case "$CMD" in
  api)
    echo "Ensuring shared infrastructure resources..."
    python /app/docker/init-infra.py
    echo "Running database migrations (alembic upgrade head)..."
    alembic upgrade head
    echo "Starting FastAPI application server..."
    exec uvicorn "$2" --host 0.0.0.0 --port 8000 --no-access-log
    ;;

  consumer)
    ensure_prometheus_dir
    echo "Starting event consumer..."
    shift 1
    exec python -m "$@"
    ;;

  outbox)
    ensure_prometheus_dir
    echo "Starting outbox worker..."
    shift 1
    exec python -m "$@"
    ;;

  cleanup)
    ensure_prometheus_dir
    echo "Starting cleanup worker..."
    shift 1
    exec "$@"
    ;;

  migrate)
    echo "Ensuring shared infrastructure resources..."
    python /app/docker/init-infra.py
    echo "Running database migrations (alembic upgrade head)..."
    exec alembic upgrade head
    ;;

  *)
    exec "$@"
    ;;
esac
