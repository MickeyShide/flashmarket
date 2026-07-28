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
RUN uv sync --frozen --no-dev

RUN mkdir -p /var/lib/flashmarket-auth/keys \
    && chown app:app /var/lib/flashmarket-auth/keys

USER app

EXPOSE 8000

CMD [".venv/bin/uvicorn", "auth_service.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
