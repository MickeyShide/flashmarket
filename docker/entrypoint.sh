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
    uv run python /app/docker/init-infra.py
    echo "Running database migrations (alembic upgrade head)..."
    uv run alembic upgrade head
    echo "Starting FastAPI application server..."
    exec uv run uvicorn "$2" --host 0.0.0.0 --port 8000 --no-access-log
    ;;

  consumer)
    ensure_prometheus_dir
    echo "Starting event consumer..."
    shift 1
    exec uv run python -m "$@"
    ;;

  outbox)
    ensure_prometheus_dir
    echo "Starting outbox worker..."
    shift 1
    exec uv run python -m "$@"
    ;;

  cleanup)
    ensure_prometheus_dir
    echo "Starting cleanup worker..."
    shift 1
    exec uv run "$@"
    ;;

  migrate)
    echo "Running database migrations (alembic upgrade head)..."
    exec uv run alembic upgrade head
    ;;

  *)
    exec uv run "$@"
    ;;
esac
