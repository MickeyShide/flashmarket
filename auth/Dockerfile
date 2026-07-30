FROM python:3.14.6-slim AS runtime

COPY --from=ghcr.io/astral-sh/uv:0.11.32 /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

RUN groupadd --system app && useradd --system --gid app --home-dir /app app

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

COPY alembic.ini ./
COPY migrations ./migrations
COPY src ./src
COPY scripts ./scripts
COPY docker/init-infra.py ./docker/init-infra.py
COPY docker/entrypoint.sh ./docker/entrypoint.sh

RUN uv sync --frozen --no-dev && \
    sed -i 's/\r$//' ./docker/entrypoint.sh && \
    chmod +x ./docker/entrypoint.sh

RUN mkdir -p /var/lib/flashmarket-auth/keys \
    && chown app:app /var/lib/flashmarket-auth/keys

USER app

EXPOSE 8000

ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["api", "auth_service.main:app"]