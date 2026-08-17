#!/usr/bin/env sh
set -e

CMD="$1"

ensure_prometheus_dir() {
    if [ -n "${PROMETHEUS_MULTIPROC_DIR:-}" ]; then
        mkdir -p "$PROMETHEUS_MULTIPROC_DIR"
    fi
}

case "$CMD" in
  api)
    export FLASHMARKET_PROCESS_ROLE=api
    ensure_prometheus_dir
    echo "Ensuring shared infrastructure resources..."
    python /app/docker/init-infra.py
    echo "Running database migrations (alembic upgrade head)..."
    alembic upgrade head
    echo "Starting FastAPI application server..."
    exec uvicorn "$2" --host 0.0.0.0 --port 8000 --no-access-log
    ;;

  consumer)
    export FLASHMARKET_PROCESS_ROLE=worker
    ensure_prometheus_dir
    echo "Starting event consumer..."
    shift 1
    exec python -m "$@"
    ;;

  outbox)
    export FLASHMARKET_PROCESS_ROLE=worker
    ensure_prometheus_dir
    echo "Starting outbox worker..."
    shift 1
    exec python -m "$@"
    ;;

  cleanup)
    export FLASHMARKET_PROCESS_ROLE=worker
    ensure_prometheus_dir
    echo "Starting cleanup worker..."
    shift 1
    exec "$@"
    ;;

  celery-worker)
    export FLASHMARKET_PROCESS_ROLE=worker
    ensure_prometheus_dir
    echo "Starting Celery maintenance worker..."
    shift 1
    exec celery "$@"
    ;;

  celery-beat)
    export FLASHMARKET_PROCESS_ROLE=worker
    ensure_prometheus_dir
    echo "Starting singleton Celery Beat scheduler..."
    shift 1
    exec celery "$@"
    ;;

  migrate)
    export FLASHMARKET_PROCESS_ROLE=worker
    echo "Ensuring shared infrastructure resources..."
    python /app/docker/init-infra.py
    echo "Running database migrations (alembic upgrade head)..."
    exec alembic upgrade head
    ;;

  *)
    exec "$@"
    ;;
esac
