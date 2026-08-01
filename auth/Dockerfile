FROM python:3.14.6-slim AS runtime

COPY --from=ghcr.io/astral-sh/uv:0.11.32 /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

RUN groupadd --system app && useradd --system --gid app --home-dir /app app

COPY auth/pyproject.toml auth/uv.lock auth/README.md ./
RUN uv sync --frozen --no-dev --no-install-project

COPY auth/alembic.ini ./
COPY auth/migrations ./migrations
COPY auth/src ./src
COPY auth/scripts ./scripts
COPY docker/init-infra.py ./docker/init-infra.py
COPY docker/entrypoint.sh ./docker/entrypoint.sh

RUN uv sync --frozen --no-dev --no-editable && \
    sed -i 's/\r$//' ./docker/entrypoint.sh && \
    chmod +x ./docker/entrypoint.sh && \
    chown -R app:app /app

RUN mkdir -p \
        /var/lib/flashmarket-auth/keys/private \
        /var/lib/flashmarket-auth/keys/public \
    && chown -R app:app /var/lib/flashmarket-auth/keys

ENV UV_NO_CACHE=1

USER app

EXPOSE 8000

ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["api", "auth_service.main:app"]
