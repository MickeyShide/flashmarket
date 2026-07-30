FROM python:3.14.6-slim AS runtime

COPY --from=ghcr.io/astral-sh/uv:0.11.32 /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_CACHE_DIR=/tmp/.cache/uv

WORKDIR /app

RUN groupadd --system app && useradd --system --gid app --home-dir /app app

COPY orders/pyproject.toml orders/uv.lock orders/README.md ./
RUN uv sync --frozen --no-dev --no-install-project

COPY orders/alembic.ini ./
COPY orders/migrations ./migrations
COPY orders/src ./src
COPY docker/init-infra.py ./docker/init-infra.py
COPY docker/entrypoint.sh ./docker/entrypoint.sh

RUN uv sync --frozen --no-dev && \
    sed -i 's/\r$//' ./docker/entrypoint.sh && \
    chmod +x ./docker/entrypoint.sh

USER app

EXPOSE 8000

ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["api", "orders.main:app"]
