# FlashMarket Catalog Service

Product catalog microservice for the FlashMarket platform.

## Stack

- FastAPI + Uvicorn
- SQLAlchemy 2 (async) + asyncpg
- PostgreSQL 17
- Alembic migrations
- Pydantic v2

## Local Development

```bash
cp .env.example .env
uv sync
docker compose up db -d
uv run alembic upgrade head
uv run uvicorn catalog.main:app --reload
```

## Tests

```bash
uv run pytest
```

## Linting

```bash
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run mypy
```

## Docker

```bash
docker compose up --build
```

## Quality checklist

- `ruff check src/ tests/` - 0 errors
- `ruff format --check src/ tests/` - 0 errors
- `mypy` - 0 errors (strict mode)
- `pytest` - all tests green
