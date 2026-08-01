# FlashMarket — Подробные технические задания

> Детальные ТЗ для реализации ключевых функций платформы.
> Каждое ТЗ написано для джуниор-разработчика: описан каждый файл, каждая модель, каждый метод.
> Архитектурные решения принимать **не нужно** — всё указано.

---

## Содержание

1. [ТЗ-1: Wishlist Service (Избранное)](#тз-1-wishlist-service-избранное)
2. [ТЗ-2: Drops Service (Flash-Sale дропы)](#тз-2-drops-service-flash-sale-дропы)
3. [ТЗ-3: Промокоды (Promocodes)](#тз-3-промокоды-promocodes)
4. [ТЗ-4: Размеры и варианты товаров (SKU)](#тз-4-размеры-и-варианты-товаров-sku)

---

# ТЗ-1: Wishlist Service (Избранное)

## 1. Место сервиса в проекте

```
flashmarket/
├── auth/
├── catalog/
├── inventory/
├── orders/
├── payments/
├── notifications/
├── wishlist/       ← ЭТО ТЗ
├── gateway/
└── frontend/
```

Wishlist Service — **новый микросервис**. Он хранит список избранных товаров пользователя. Сервис **не знает** о каталоге, ценах, остатках и заказах. Он хранит только пару `(user_id, product_id)` и timestamp.

---

## 2. Стек технологий

Полностью повторяет стек остальных сервисов:

| Слой | Технология | Версия |
|---|---|---|
| Runtime | Python | ≥ 3.14 |
| Web Framework | FastAPI | ≥ 0.140 |
| ORM | SQLAlchemy 2 (async) | ≥ 2.0 |
| DB Driver | asyncpg | ≥ 0.31 |
| Migrations | Alembic | ≥ 1.18 |
| Validation | Pydantic v2 | встроен в FastAPI |
| Settings | pydantic-settings | ≥ 2.14 |
| HTTP Server | uvicorn | ≥ 0.51 |
| Package Manager | uv | актуальная |
| Linter/Formatter | ruff | ≥ 0.16 |
| Types | mypy (strict) | ≥ 2.1 |
| Tests | pytest + pytest-asyncio + httpx | |
| Test DB | aiosqlite (in-memory) | ≥ 0.22 |
| Build Backend | hatchling | |

> [!IMPORTANT]
> Никакой RabbitMQ. Wishlist **не публикует** domain events — это простой CRUD-сервис. RabbitMQ и outbox добавим позже если понадобится уведомлять пользователя о поступлении wishlist-товара в дроп.

---

## 3. Структура файлов

```
wishlist/
├── .dockerignore
├── .env.example
├── .gitignore
├── .python-version                 # содержит "3.14"
├── Dockerfile
├── docker-compose.yml
├── alembic.ini
├── pyproject.toml
├── README.md
│
├── migrations/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       └── 0001_initial.py
│
├── src/
│   └── wishlist/
│       ├── __init__.py
│       ├── main.py
│       ├── config.py
│       │
│       ├── domain/
│       │   ├── __init__.py
│       │   └── exceptions.py
│       │
│       ├── application/
│       │   ├── __init__.py
│       │   ├── schemas.py
│       │   └── services/
│       │       ├── __init__.py
│       │       └── wishlist.py
│       │
│       ├── api/
│       │   ├── __init__.py
│       │   ├── dependencies.py
│       │   ├── error_handlers.py
│       │   └── routes/
│       │       ├── __init__.py
│       │       ├── wishlist.py
│       │       └── health.py
│       │
│       └── infrastructure/
│           ├── __init__.py
│           ├── database.py
│           ├── models.py
│           └── repositories/
│               ├── __init__.py
│               └── wishlist.py
│
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_wishlist_service.py
    └── test_wishlist_api.py
```

---

## 4. pyproject.toml

```toml
[project]
name = "flashmarket-wishlist"
version = "0.1.0"
description = "Wishlist service for FlashMarket"
readme = "README.md"
requires-python = ">=3.14"
dependencies = [
    "alembic>=1.18,<2",
    "asyncpg>=0.31,<1",
    "fastapi>=0.140,<1",
    "pydantic-settings>=2.14,<3",
    "sqlalchemy>=2.0,<3",
    "uvicorn[standard]>=0.51,<1",
]

[dependency-groups]
dev = [
    "aiosqlite>=0.22,<1",
    "httpx>=0.28,<1",
    "mypy>=2.1,<3",
    "pytest>=9.1,<10",
    "pytest-asyncio>=1.4,<2",
    "ruff>=0.16,<1",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/wishlist"]

[tool.pytest.ini_options]
addopts = "-q"
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.ruff]
line-length = 100
target-version = "py314"

[tool.ruff.lint]
select = ["ASYNC", "B", "E", "F", "I", "UP"]

[tool.mypy]
python_version = "3.14"
files = ["src/wishlist"]
plugins = ["pydantic.mypy"]
strict = true
pretty = true
show_error_codes = true
show_error_context = true
warn_unreachable = true
```

---

## 5. Конфигурация — `src/wishlist/config.py`

Полностью повторяет паттерн [config.py](file:///c:/Users/mickey/Desktop/flashmarket/catalog/src/catalog/config.py) из catalog:

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="WISHLIST_",
        extra="ignore",
    )

    app_name: str = "FlashMarket Wishlist"
    environment: Literal["development", "test", "production"] = "development"
    debug: bool = False
    database_url: str = "postgresql+asyncpg://shide:shide@shide-postgres:5432/wishlist"
    log_file_path: str | None = None
    prometheus_multiproc_dir: str | None = None
    docs_enabled: bool = True
    trusted_hosts: list[str] = Field(default_factory=lambda: ["localhost", "127.0.0.1"])
    cors_origins: list[str] = Field(default_factory=list)
    allow_insecure_internal_services: bool = False
    max_items_per_user: int = 200  # лимит избранных на пользователя
```

Production validator — копия из catalog.

---

## 6. Domain Layer

### 6.1. `src/wishlist/domain/exceptions.py`

Паттерн полностью повторяет [exceptions.py](file:///c:/Users/mickey/Desktop/flashmarket/inventory/src/inventory/domain/exceptions.py) из inventory:

| Класс | `code` | `message` |
|---|---|---|
| `WishlistError` | `"wishlist_error"` | `"The operation could not be completed"` |
| `ItemAlreadyInWishlist` | `"item_already_in_wishlist"` | `"Product is already in wishlist"` |
| `ItemNotInWishlist` | `"item_not_in_wishlist"` | `"Product is not in wishlist"` |
| `WishlistLimitReached` | `"wishlist_limit_reached"` | `"Wishlist item limit reached"` |

---

## 7. Infrastructure Layer

### 7.1. `src/wishlist/infrastructure/database.py`

Копия [database.py](file:///c:/Users/mickey/Desktop/flashmarket/inventory/src/inventory/infrastructure/database.py) из inventory (engine, Base, utc_now, get_db), с заменой import пути на `wishlist.config`.

### 7.2. `src/wishlist/infrastructure/models.py` — ORM-модель

#### `WishlistItemModel`

| Колонка | SQLAlchemy type | Python type | Constraints |
|---|---|---|---|
| `id` | `Uuid` | `uuid.UUID` | PK, default `uuid.uuid7` |
| `user_id` | `Uuid` | `uuid.UUID` | NOT NULL, INDEX |
| `product_id` | `Uuid` | `uuid.UUID` | NOT NULL |
| `created_at` | `DateTime(timezone=True)` | `datetime` | NOT NULL, default `utc_now` |

**`__tablename__`** = `"wishlist_items"`

**`__table_args__`:**
```python
(
    UniqueConstraint("user_id", "product_id", name="uq_wishlist_user_product"),
    Index("ix_wishlist_items_user_created", "user_id", "created_at"),
)
```

> [!IMPORTANT]
> Уникальность пары `(user_id, product_id)` гарантируется на уровне БД через `UniqueConstraint`. Это главная защита от дубликатов. Сервис также проверяет перед insert, но constraint — последний рубеж.

> [!IMPORTANT]
> `product_id` — это **НЕ FK** на таблицу `products`. Сервис Wishlist не имеет доступа к базе данных Catalog. Это просто `UUID`, который frontend знает из Catalog API. Валидность product_id не проверяется на стороне wishlist.

### 7.3. `src/wishlist/infrastructure/repositories/wishlist.py` — `WishlistRepository`

Конструктор: `def __init__(self, session: AsyncSession) -> None`

**Методы:**

| Метод | Сигнатура | Описание |
|---|---|---|
| `add` | `(item: WishlistItemModel) -> WishlistItemModel` | `session.add(item)`, `session.flush()`, return item |
| `remove` | `(user_id: UUID, product_id: UUID) -> bool` | `DELETE FROM wishlist_items WHERE user_id = ... AND product_id = ...`. Return `True` если строка удалена, `False` если не найдена |
| `get_by_user` | `(user_id: UUID, limit: int, offset: int) -> WishlistPage` | Список items пользователя, сортировка по `created_at DESC` |
| `exists` | `(user_id: UUID, product_id: UUID) -> bool` | `SELECT 1 FROM wishlist_items WHERE ...`, return boolean |
| `count_by_user` | `(user_id: UUID) -> int` | `SELECT count(*) FROM wishlist_items WHERE user_id = ...` |
| `get_product_ids_for_user` | `(user_id: UUID, product_ids: list[UUID]) -> set[UUID]` | Из переданного списка вернуть те, что уже в wishlist. Нужно для фронтенда, чтобы отображать сердечко на карточках каталога. Запрос: `SELECT product_id FROM wishlist_items WHERE user_id = ... AND product_id IN (...)` |

**Dataclass для пагинации:**

```python
@dataclass(frozen=True, slots=True)
class WishlistPage:
    items: list[WishlistItemModel]
    total: int
```

---

## 8. Application Layer

### 8.1. `src/wishlist/application/schemas.py` — Pydantic-модели

#### Request-модели

**`AddToWishlistRequest`:**

| Поле | Тип | Constraints |
|---|---|---|
| `product_id` | `uuid.UUID` | required |

**`WishlistListParams`:**

| Поле | Тип | Default | Constraints |
|---|---|---|---|
| `limit` | `int` | `20` | `ge=1, le=100` |
| `offset` | `int` | `0` | `ge=0` |

**`CheckWishlistRequest`:**

| Поле | Тип | Constraints |
|---|---|---|
| `product_ids` | `list[uuid.UUID]` | `min_length=1, max_length=50` |

#### Response-модели

**`WishlistItemResponse`:**

| Поле | Тип |
|---|---|
| `id` | `uuid.UUID` |
| `user_id` | `uuid.UUID` |
| `product_id` | `uuid.UUID` |
| `created_at` | `datetime` |

`model_config = ConfigDict(from_attributes=True)`

**`WishlistListResponse`:**

| Поле | Тип |
|---|---|
| `items` | `list[WishlistItemResponse]` |
| `total` | `int` |
| `limit` | `int` |
| `offset` | `int` |

**`WishlistCheckResponse`:**

| Поле | Тип | Описание |
|---|---|---|
| `product_ids` | `list[uuid.UUID]` | Список product_id которые в wishlist |

**`ErrorDetail`** и **`ErrorResponse`** — копия из inventory/catalog.

### 8.2. `src/wishlist/application/services/wishlist.py` — `WishlistService`

**Конструктор:**

```python
def __init__(
    self,
    session: AsyncSession,
    repo: WishlistRepository,
    max_items: int,
) -> None:
```

**Методы:**

#### `add_item(user_id: UUID, data: AddToWishlistRequest) -> WishlistItemModel`

1. Проверить `repo.exists(user_id, data.product_id)` — если True → raise `ItemAlreadyInWishlist`
2. Проверить `repo.count_by_user(user_id)` — если `>= max_items` → raise `WishlistLimitReached`
3. Создать `WishlistItemModel(user_id=..., product_id=...)`
4. `repo.add(item)`
5. `session.commit()`
6. Вернуть item

> [!IMPORTANT]
> При `IntegrityError` от БД (race condition — два параллельных add) — ловить и пробрасывать `ItemAlreadyInWishlist`.

#### `remove_item(user_id: UUID, product_id: UUID) -> None`

1. `repo.remove(user_id, product_id)` — если False → raise `ItemNotInWishlist`
2. `session.commit()`

#### `list_items(user_id: UUID, params: WishlistListParams) -> WishlistPage`

1. `repo.get_by_user(user_id, params.limit, params.offset)`
2. Вернуть result

#### `check_items(user_id: UUID, product_ids: list[UUID]) -> set[UUID]`

1. `repo.get_product_ids_for_user(user_id, product_ids)`
2. Вернуть result

---

## 9. API Layer

### 9.1. `src/wishlist/api/dependencies.py`

```python
DbSession = Annotated[AsyncSession, Depends(get_db)]

def get_wishlist_service(db: DbSession) -> WishlistService:
    repo = WishlistRepository(db)
    settings = get_settings()
    return WishlistService(session=db, repo=repo, max_items=settings.max_items_per_user)

WishlistServiceDep = Annotated[WishlistService, Depends(get_wishlist_service)]
```

### 9.2. `src/wishlist/api/error_handlers.py`

```python
ERROR_STATUS: dict[type[WishlistError], int] = {
    ItemAlreadyInWishlist: status.HTTP_409_CONFLICT,
    ItemNotInWishlist: status.HTTP_404_NOT_FOUND,
    WishlistLimitReached: status.HTTP_422_UNPROCESSABLE_ENTITY,
}
```

### 9.3. Routes — `src/wishlist/api/routes/wishlist.py`

**Router:** `prefix="/api/v1/wishlist"`, `tags=["wishlist"]`

| Method | Path | Функция | Request | Response | Status | Описание |
|---|---|---|---|---|---|---|
| `POST` | `/users/{user_id}/items` | `add_item` | `AddToWishlistRequest` | `WishlistItemResponse` | 201 | Добавить товар |
| `DELETE` | `/users/{user_id}/items/{product_id}` | `remove_item` | — | `204 No Content` | 204 | Удалить товар |
| `GET` | `/users/{user_id}/items` | `list_items` | Query `WishlistListParams` | `WishlistListResponse` | 200 | Список избранного |
| `POST` | `/users/{user_id}/check` | `check_items` | `CheckWishlistRequest` | `WishlistCheckResponse` | 200 | Проверить есть ли товары в wishlist |

> [!IMPORTANT]
> `user_id` передаётся как path parameter. В будущем его нужно будет брать из JWT, но пока сервис без аутентификации — принимаем `user_id` явно.

### 9.4. Health — `src/wishlist/api/routes/health.py`

`GET /health/ready` → `{"status": "ok"}`

---

## 10. Docker

### Dockerfile

Копия [Dockerfile](file:///c:/Users/mickey/Desktop/flashmarket/inventory/Dockerfile) из inventory с заменой `inventory` → `wishlist`. Без RabbitMQ. Без consumer/outbox.

### docker-compose.yml

```yaml
name: flashmarket-wishlist

x-wishlist-runtime: &wishlist-runtime
  image: flashmarket-wishlist-api:local
  pull_policy: never

x-wishlist-environment: &wishlist-environment
  WISHLIST_ENVIRONMENT: development
  WISHLIST_DATABASE_URL: postgresql+asyncpg://${INFRA_USER:-shide}:${POSTGRES_PASSWORD:-shide}@shide-postgres:5432/wishlist
  WISHLIST_CORS_ORIGINS: '["http://localhost:3000"]'
  WISHLIST_ALLOW_INSECURE_INTERNAL_SERVICES: 'true'

services:
  api:
    <<: *wishlist-runtime
    build:
      context: .
    environment: *wishlist-environment
    ports:
      - "127.0.0.1:${WISHLIST_PORT:-4921}:8000"
    healthcheck:
      test:
        - CMD
        - python
        - -c
        - "import urllib.request; urllib.request.urlopen('http://localhost:8000/health/ready')"
      interval: 5s
      timeout: 3s
      retries: 10
      start_period: 10s
    restart: unless-stopped

networks:
  default:
    name: shide-observability
    external: true
```

> [!NOTE]
> Порт API: **4921**. Нет consumer и outbox контейнеров — это простой CRUD-сервис.

---

## 11. Gateway интеграция

Добавить в [nginx.conf](file:///c:/Users/mickey/Desktop/flashmarket/gateway/nginx.conf):

```nginx
upstream wishlist {
    server wishlist:8000;
}

# в секции server:
location /api/v1/wishlist {
    proxy_pass http://wishlist;
}
```

Добавить subdomain-роутинг:

```nginx
server {
    listen 80;
    server_name wishlist.${GATEWAY_DOMAIN};
    server_tokens off;
    location / {
        proxy_pass http://wishlist;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $remote_addr;
        proxy_set_header X-Forwarded-Proto $http_x_forwarded_proto;
    }
}
```

Добавить в корневой [docker-compose.yml](file:///c:/Users/mickey/Desktop/flashmarket/docker-compose.yml):

```yaml
  wishlist:
    extends:
      file: wishlist/docker-compose.yml
      service: api
    depends_on: !reset {}
```

---

## 12. Тесты

### `tests/conftest.py`

Копия из catalog — in-memory SQLite, `override_get_db`.

### `tests/test_wishlist_service.py`

| Тест | Описание |
|---|---|
| `test_add_item` | Добавить товар, проверить поля |
| `test_add_duplicate` | Повторное добавление → `ItemAlreadyInWishlist` |
| `test_remove_item` | Удалить товар → success |
| `test_remove_nonexistent` | Удалить несуществующий → `ItemNotInWishlist` |
| `test_list_items_empty` | Пустой wishlist → `items: [], total: 0` |
| `test_list_items_pagination` | Добавить 5, запросить `limit=2` → 2 items, total=5 |
| `test_list_items_order` | Items отсортированы по `created_at DESC` |
| `test_check_items` | Добавить A и B, check [A, B, C] → [A, B] |
| `test_limit_reached` | Установить `max_items=3`, добавить 3, попробовать 4-й → `WishlistLimitReached` |

### `tests/test_wishlist_api.py`

| Тест | Описание |
|---|---|
| `test_add_item_201` | `POST /api/v1/wishlist/users/{id}/items` → 201 |
| `test_add_duplicate_409` | Повторный POST → 409 |
| `test_remove_item_204` | `DELETE /api/v1/wishlist/users/{id}/items/{product_id}` → 204 |
| `test_remove_nonexistent_404` | DELETE несуществующего → 404 |
| `test_list_items_200` | `GET /api/v1/wishlist/users/{id}/items` → 200 + список |
| `test_check_items_200` | `POST /api/v1/wishlist/users/{id}/check` → 200 + список |

---

## 13. Порядок реализации

| Шаг | Что делать |
|---|---|
| 1 | Создать `wishlist/` директорию: `pyproject.toml`, `.python-version`, `.gitignore`, `.env.example`, `README.md` |
| 2 | `uv sync` — установить зависимости |
| 3 | `config.py` |
| 4 | `domain/exceptions.py` |
| 5 | `infrastructure/database.py` |
| 6 | `infrastructure/models.py` (WishlistItemModel) |
| 7 | `alembic.ini` + `migrations/env.py` + `alembic revision --autogenerate` |
| 8 | `infrastructure/repositories/wishlist.py` |
| 9 | `application/schemas.py` |
| 10 | `application/services/wishlist.py` |
| 11 | `api/error_handlers.py` |
| 12 | `api/dependencies.py` |
| 13 | `api/routes/health.py` |
| 14 | `api/routes/wishlist.py` |
| 15 | `main.py` |
| 16 | `tests/conftest.py` |
| 17 | Все тест-файлы |
| 18 | `Dockerfile` + `docker-compose.yml` |
| 19 | Gateway: `nginx.conf` + корневой `docker-compose.yml` |
| 20 | `ruff check`, `ruff format`, `mypy`, `pytest` |

---

## 14. Чеклист качества

- [ ] `ruff check src/ tests/` — 0 ошибок
- [ ] `ruff format --check src/ tests/` — 0 ошибок
- [ ] `mypy` — 0 ошибок (strict mode)
- [ ] `pytest` — все тесты зелёные
- [ ] UniqueConstraint на `(user_id, product_id)` работает
- [ ] IntegrityError при race condition пробрасывается как `ItemAlreadyInWishlist`
- [ ] Пагинация: `limit` + `offset` + `total` работают корректно
- [ ] `check_items` принимает до 50 product_id за раз
- [ ] Все эндпоинты имеют `response_model`, `summary`, `responses`

---
---

# ТЗ-2: Drops Service (Flash-Sale дропы)

## 1. Место сервиса в проекте

```
flashmarket/
├── auth/
├── catalog/
├── inventory/
├── orders/
├── payments/
├── notifications/
├── drops/          ← ЭТО ТЗ
├── gateway/
└── frontend/
```

Drops Service — **новый микросервис**. Он управляет flash-sale событиями: определяет какие товары участвуют, когда дроп начинается и заканчивается, и какие лимиты действуют. Сервис **не управляет** стоками и заказами — это делают Inventory и Orders. Drops только управляет расписанием и составом дропа.

---

## 2. Стек технологий

Как у всех backend-сервисов (см. ТЗ-1) **плюс RabbitMQ** — потому что Drops публикует события о начале и окончании дропа.

Дополнительные зависимости:
```toml
"aio-pika>=9.0,<10",
```

---

## 3. Структура файлов

```
drops/
├── .dockerignore
├── .env.example
├── .gitignore
├── .python-version
├── Dockerfile
├── docker-compose.yml
├── alembic.ini
├── pyproject.toml
├── README.md
│
├── migrations/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       └── 0001_initial.py
│
├── src/
│   └── drops/
│       ├── __init__.py
│       ├── main.py
│       ├── config.py
│       ├── observability.py
│       ├── outbox_worker.py
│       ├── scheduler.py              # планировщик открытия/закрытия дропов
│       │
│       ├── domain/
│       │   ├── __init__.py
│       │   ├── entities.py
│       │   └── exceptions.py
│       │
│       ├── application/
│       │   ├── __init__.py
│       │   ├── schemas.py
│       │   └── services/
│       │       ├── __init__.py
│       │       └── drop.py
│       │
│       ├── api/
│       │   ├── __init__.py
│       │   ├── dependencies.py
│       │   ├── error_handlers.py
│       │   └── routes/
│       │       ├── __init__.py
│       │       ├── drops.py
│       │       ├── admin.py
│       │       └── health.py
│       │
│       └── infrastructure/
│           ├── __init__.py
│           ├── database.py
│           ├── models.py
│           └── repositories/
│               ├── __init__.py
│               ├── drop.py
│               └── outbox.py
│
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_drop_service.py
    ├── test_drops_api.py
    └── test_scheduler.py
```

---

## 4. Domain Layer

### 4.1. `src/drops/domain/entities.py`

```python
class DropStatus(StrEnum):
    """Lifecycle status of a flash-sale drop."""

    DRAFT = "DRAFT"             # создан, не опубликован
    SCHEDULED = "SCHEDULED"     # запланирован, ожидает starts_at
    ACTIVE = "ACTIVE"           # идёт прямо сейчас
    ENDED = "ENDED"             # завершён нормально
    CANCELLED = "CANCELLED"     # отменён администратором


class DropEventType(StrEnum):
    """Outbox event types published by the drops service."""

    DROP_SCHEDULED = "DropScheduled"
    DROP_STARTED = "DropStarted"
    DROP_ENDED = "DropEnded"
    DROP_CANCELLED = "DropCancelled"
```

### 4.2. `src/drops/domain/exceptions.py`

| Класс | `code` | `message` |
|---|---|---|
| `DropError` | `"drop_error"` | `"The operation could not be completed"` |
| `DropNotFound` | `"drop_not_found"` | `"Drop not found"` |
| `InvalidDropState` | `"invalid_drop_state"` | `"Invalid drop state transition"` |
| `DropTimeConflict` | `"drop_time_conflict"` | `"Drop time range is invalid"` |
| `DuplicateDropSlug` | `"duplicate_drop_slug"` | `"A drop with this slug already exists"` |
| `ProductAlreadyInDrop` | `"product_already_in_drop"` | `"Product is already in this drop"` |

---

## 5. Infrastructure Layer

### 5.1. `src/drops/infrastructure/models.py` — ORM-модели

#### `DropModel`

| Колонка | SQLAlchemy type | Python type | Constraints |
|---|---|---|---|
| `id` | `Uuid` | `uuid.UUID` | PK, default `uuid.uuid7` |
| `name` | `String(255)` | `str` | NOT NULL |
| `slug` | `String(255)` | `str` | NOT NULL, UNIQUE, INDEX |
| `description` | `Text` | `str` | NOT NULL, default `""` |
| `cover_image` | `String(2048)` | `str \| None` | nullable |
| `status` | `String(20)` | `DropStatus` | NOT NULL, default `DropStatus.DRAFT` |
| `starts_at` | `DateTime(timezone=True)` | `datetime` | NOT NULL |
| `ends_at` | `DateTime(timezone=True)` | `datetime` | NOT NULL |
| `max_per_user` | `Integer` | `int` | NOT NULL, default `1` — лимит единиц на пользователя |
| `payment_timeout_seconds` | `Integer` | `int` | NOT NULL, default `300` — время на оплату (5 мин) |
| `created_at` | `DateTime(timezone=True)` | `datetime` | NOT NULL, default `utc_now` |
| `updated_at` | `DateTime(timezone=True)` | `datetime` | NOT NULL, default `utc_now`, onupdate |

**`__tablename__`** = `"drops"`

**`__table_args__`:**
```python
(
    CheckConstraint("ends_at > starts_at", name="ck_drops_valid_time_range"),
    CheckConstraint("max_per_user >= 1", name="ck_drops_max_per_user_positive"),
    CheckConstraint("payment_timeout_seconds >= 60", name="ck_drops_payment_timeout_min"),
    Index("ix_drops_status", "status"),
    Index("ix_drops_starts_at", "starts_at"),
)
```

**Relationships:**
- `items: Mapped[list[DropItemModel]]` — `relationship(back_populates="drop", cascade="all, delete-orphan", lazy="selectin")`

#### `DropItemModel`

| Колонка | SQLAlchemy type | Python type | Constraints |
|---|---|---|---|
| `id` | `Uuid` | `uuid.UUID` | PK, default `uuid.uuid7` |
| `drop_id` | `Uuid`, FK → `drops.id` | `uuid.UUID` | NOT NULL, `ondelete="CASCADE"`, INDEX |
| `product_id` | `Uuid` | `uuid.UUID` | NOT NULL |
| `sort_order` | `Integer` | `int` | NOT NULL, default `0` |
| `created_at` | `DateTime(timezone=True)` | `datetime` | NOT NULL, default `utc_now` |

**`__tablename__`** = `"drop_items"`

**`__table_args__`:**
```python
(
    UniqueConstraint("drop_id", "product_id", name="uq_drop_items_drop_product"),
)
```

> [!IMPORTANT]
> `product_id` — это **НЕ FK** на таблицу `products`. Сервис Drops не имеет доступа к базе Catalog. Frontend передаёт product_id, который знает из Catalog API.

#### `OutboxEventModel`

Полная копия [OutboxEventModel](file:///c:/Users/mickey/Desktop/flashmarket/inventory/src/inventory/infrastructure/models.py#L109-L131) из inventory.

### 5.2. `src/drops/infrastructure/repositories/drop.py` — `DropRepository`

**Методы:**

| Метод | Сигнатура | Описание |
|---|---|---|
| `create` | `(drop: DropModel) -> DropModel` | `session.add`, flush, return |
| `get_by_id` | `(drop_id: UUID) -> DropModel \| None` | С `selectinload(items)` |
| `get_by_slug` | `(slug: str) -> DropModel \| None` | С `selectinload(items)` |
| `slug_exists` | `(slug: str) -> bool` | SELECT count |
| `list_active` | `() -> list[DropModel]` | `status == ACTIVE`, ordered by `starts_at` |
| `list_upcoming` | `() -> list[DropModel]` | `status == SCHEDULED`, ordered by `starts_at` |
| `list_all` | `(limit: int, offset: int) -> DropPage` | Все дропы, сортировка `starts_at DESC` |
| `get_due_to_start` | `(now: datetime) -> list[DropModel]` | `status == SCHEDULED AND starts_at <= now` |
| `get_due_to_end` | `(now: datetime) -> list[DropModel]` | `status == ACTIVE AND ends_at <= now` |
| `update` | `(drop: DropModel) -> DropModel` | flush, return |
| `add_item` | `(item: DropItemModel) -> DropItemModel` | add, flush, return |
| `remove_item` | `(drop_id: UUID, product_id: UUID) -> bool` | DELETE, return bool |

---

## 6. Application Layer

### 6.1. `src/drops/application/schemas.py`

#### Request-модели

**`CreateDropRequest`:**

| Поле | Тип | Constraints |
|---|---|---|
| `name` | `str` | `min_length=1, max_length=255` |
| `slug` | `str` | `min_length=1, max_length=255, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$"` |
| `description` | `str` | default `""` |
| `cover_image` | `str \| None` | `max_length=2048` |
| `starts_at` | `datetime` | required, с timezone |
| `ends_at` | `datetime` | required, с timezone |
| `max_per_user` | `int` | default `1`, `ge=1, le=100` |
| `payment_timeout_seconds` | `int` | default `300`, `ge=60, le=3600` |

Pydantic validator: `ends_at > starts_at`, иначе `ValueError`.

**`UpdateDropRequest`:**

Все поля опциональные.

**`AddDropItemRequest`:**

| Поле | Тип | Constraints |
|---|---|---|
| `product_id` | `uuid.UUID` | required |
| `sort_order` | `int` | default `0`, `ge=0` |

**`DropListParams`:**

| Поле | Тип | Default |
|---|---|---|
| `limit` | `int` | `20`, `ge=1, le=100` |
| `offset` | `int` | `0`, `ge=0` |
| `status` | `DropStatus \| None` | `None` |

#### Response-модели

**`DropItemResponse`:**

| Поле | Тип |
|---|---|
| `id` | `uuid.UUID` |
| `product_id` | `uuid.UUID` |
| `sort_order` | `int` |

**`DropResponse`:**

| Поле | Тип |
|---|---|
| `id` | `uuid.UUID` |
| `name` | `str` |
| `slug` | `str` |
| `description` | `str` |
| `cover_image` | `str \| None` |
| `status` | `DropStatus` |
| `starts_at` | `datetime` |
| `ends_at` | `datetime` |
| `max_per_user` | `int` |
| `payment_timeout_seconds` | `int` |
| `items` | `list[DropItemResponse]` |
| `created_at` | `datetime` |
| `updated_at` | `datetime` |

**`DropListResponse`:**

| Поле | Тип |
|---|---|
| `items` | `list[DropResponse]` |
| `total` | `int` |
| `limit` | `int` |
| `offset` | `int` |

### 6.2. `src/drops/application/services/drop.py` — `DropService`

**Методы:**

#### `create_drop(data: CreateDropRequest) -> DropModel`

1. Проверить `repo.slug_exists(data.slug)` — если True → raise `DuplicateDropSlug`
2. Проверить `data.starts_at > utc_now()` — дроп нельзя создать в прошлом
3. Создать `DropModel(...)` со `status=DRAFT`
4. `repo.create(drop)`
5. `session.commit()`
6. Вернуть drop

#### `schedule_drop(drop_id: UUID) -> DropModel`

1. Получить drop, проверить `status == DRAFT` — иначе `InvalidDropState`
2. Установить `status = SCHEDULED`
3. Записать outbox event `DropScheduled`
4. `session.commit()`
5. Вернуть drop

#### `start_drop(drop_id: UUID) -> DropModel`

1. Получить drop, проверить `status == SCHEDULED` — иначе `InvalidDropState`
2. Установить `status = ACTIVE`
3. Записать outbox event `DropStarted` с payload: `{drop_id, name, slug, product_ids, max_per_user}`
4. `session.commit()`
5. Вернуть drop

#### `end_drop(drop_id: UUID) -> DropModel`

1. Получить drop, проверить `status == ACTIVE` — иначе `InvalidDropState`
2. Установить `status = ENDED`
3. Записать outbox event `DropEnded`
4. `session.commit()`
5. Вернуть drop

#### `cancel_drop(drop_id: UUID) -> DropModel`

1. Получить drop, проверить `status in (DRAFT, SCHEDULED, ACTIVE)` — иначе `InvalidDropState`
2. Установить `status = CANCELLED`
3. Записать outbox event `DropCancelled`
4. `session.commit()`
5. Вернуть drop

#### `add_item(drop_id: UUID, data: AddDropItemRequest) -> DropItemModel`

1. Получить drop — если None → `DropNotFound`
2. Проверить `status in (DRAFT, SCHEDULED)` — товары нельзя добавлять в активный дроп
3. Создать `DropItemModel(...)`
4. `repo.add_item(item)` — при IntegrityError → `ProductAlreadyInDrop`
5. `session.commit()`
6. Вернуть item

#### `remove_item(drop_id: UUID, product_id: UUID) -> None`

1. `repo.remove_item(drop_id, product_id)` — если False → `404`
2. `session.commit()`

---

## 7. API Layer

### 7.1. Публичные маршруты — `src/drops/api/routes/drops.py`

**Router:** `prefix="/api/v1/drops"`, `tags=["drops"]`

| Method | Path | Функция | Response | Описание |
|---|---|---|---|---|
| `GET` | `/active` | `list_active` | `list[DropResponse]` | Текущие активные дропы |
| `GET` | `/upcoming` | `list_upcoming` | `list[DropResponse]` | Ожидаемые дропы |
| `GET` | `/{slug}` | `get_drop` | `DropResponse` | Дроп по slug (ACTIVE, SCHEDULED, ENDED) |

> [!IMPORTANT]
> Публичный API **не показывает** дропы в статусе DRAFT и CANCELLED.

### 7.2. Админские маршруты — `src/drops/api/routes/admin.py`

**Router:** `prefix="/api/v1/admin/drops"`, `tags=["admin-drops"]`

| Method | Path | Функция | Request | Response | Status | Описание |
|---|---|---|---|---|---|---|
| `POST` | `/` | `create_drop` | `CreateDropRequest` | `DropResponse` | 201 | Создать дроп |
| `GET` | `/` | `list_drops` | Query `DropListParams` | `DropListResponse` | 200 | Список (все статусы) |
| `GET` | `/{drop_id}` | `get_drop` | — | `DropResponse` | 200 | Дроп по ID |
| `PATCH` | `/{drop_id}` | `update_drop` | `UpdateDropRequest` | `DropResponse` | 200 | Обновить |
| `POST` | `/{drop_id}/schedule` | `schedule_drop` | — | `DropResponse` | 200 | DRAFT → SCHEDULED |
| `POST` | `/{drop_id}/start` | `start_drop` | — | `DropResponse` | 200 | SCHEDULED → ACTIVE |
| `POST` | `/{drop_id}/end` | `end_drop` | — | `DropResponse` | 200 | ACTIVE → ENDED |
| `POST` | `/{drop_id}/cancel` | `cancel_drop` | — | `DropResponse` | 200 | → CANCELLED |
| `POST` | `/{drop_id}/items` | `add_item` | `AddDropItemRequest` | `DropItemResponse` | 201 | Добавить товар |
| `DELETE` | `/{drop_id}/items/{product_id}` | `remove_item` | — | 204 | — | Удалить товар |

---

## 8. Scheduler — `src/drops/scheduler.py`

Отдельный процесс (запускается как `python -m drops.scheduler`), который каждые 10 секунд проверяет:

1. **Дропы к открытию:** `status == SCHEDULED AND starts_at <= now` → вызвать `start_drop()`
2. **Дропы к закрытию:** `status == ACTIVE AND ends_at <= now` → вызвать `end_drop()`

```python
async def scheduler_loop() -> None:
    settings = get_settings()
    while True:
        try:
            async with SessionFactory() as session, session.begin():
                repo = DropRepository(session)
                # Start due drops
                due_to_start = await repo.get_due_to_start(utc_now())
                for drop in due_to_start:
                    drop.status = DropStatus.ACTIVE
                    await _emit_event(session, DropEventType.DROP_STARTED, {...})
                    logger.info("Drop %s started", drop.slug)

                # End due drops
                due_to_end = await repo.get_due_to_end(utc_now())
                for drop in due_to_end:
                    drop.status = DropStatus.ENDED
                    await _emit_event(session, DropEventType.DROP_ENDED, {...})
                    logger.info("Drop %s ended", drop.slug)
        except Exception:
            logger.exception("Scheduler iteration failed")

        await asyncio.sleep(10)
```

### Docker Compose

В `docker-compose.yml` добавить:

```yaml
  scheduler:
    <<: *drops-runtime
    environment:
      <<: *drops-environment
    command:
      - consumer    # reuse entrypoint's consumer mode
      - drops.scheduler
    restart: unless-stopped
```

---

## 9. Outbox Worker — `src/drops/outbox_worker.py`

Копия [outbox_worker.py](file:///c:/Users/mickey/Desktop/flashmarket/inventory/src/inventory/outbox_worker.py) из inventory с routing keys:

```python
EVENT_ROUTING_KEYS: dict[str, str] = {
    DropEventType.DROP_SCHEDULED: "drops.DropScheduled",
    DropEventType.DROP_STARTED: "drops.DropStarted",
    DropEventType.DROP_ENDED: "drops.DropEnded",
    DropEventType.DROP_CANCELLED: "drops.DropCancelled",
}
```

---

## 10. Диаграмма состояний

```
  DRAFT ──schedule──▶ SCHEDULED ──start──▶ ACTIVE ──end──▶ ENDED
    │                     │                   │
    └────cancel───────────┘───────cancel──────┘──────▶ CANCELLED
```

---

## 11. Тесты

| Тест | Описание |
|---|---|
| `test_create_drop` | Создать дроп, проверить поля, status=DRAFT |
| `test_create_duplicate_slug_409` | Дублирующий slug → 409 |
| `test_schedule_drop` | DRAFT → SCHEDULED |
| `test_start_drop` | SCHEDULED → ACTIVE |
| `test_end_drop` | ACTIVE → ENDED |
| `test_cancel_draft` | DRAFT → CANCELLED |
| `test_cancel_active` | ACTIVE → CANCELLED |
| `test_invalid_state_transition` | ENDED → ACTIVE → InvalidDropState |
| `test_add_item_to_draft` | Добавить товар к DRAFT дропу |
| `test_add_item_to_active_fails` | Добавить товар к ACTIVE → ошибка |
| `test_add_duplicate_item_409` | Повторное добавление → 409 |
| `test_remove_item` | Удалить товар из дропа |
| `test_list_active` | Получить только ACTIVE дропы |
| `test_list_upcoming` | Получить только SCHEDULED дропы |
| `test_scheduler_starts_drop` | Создать SCHEDULED с `starts_at` в прошлом, запустить scheduler iteration → ACTIVE |
| `test_scheduler_ends_drop` | Создать ACTIVE с `ends_at` в прошлом → ENDED |

---
---

# ТЗ-3: Промокоды (Promocodes)

## 1. Место в проекте

Промокоды реализуются как **модуль в Orders Service**, а не как отдельный микросервис. Причины:
- Промокод применяется **при создании заказа** — это ответственность Orders
- Не нужен отдельный DB, consumer, outbox — всё уже есть в Orders
- Минимальная сложность для MVP

```
orders/src/orders/
├── ...существующие файлы...
├── domain/
│   ├── entities.py          # добавить PromocodeStatus, DiscountType
│   └── exceptions.py        # добавить PromocodeError и наследники
├── infrastructure/
│   ├── models.py            # добавить PromocodeModel, PromocodeUsageModel
│   └── repositories/
│       └── promocode.py     # НОВЫЙ: PromocodeRepository
├── application/
│   ├── schemas.py           # добавить request/response модели
│   └── services/
│       └── promocode.py     # НОВЫЙ: PromocodeService
└── api/routes/
    └── promocodes.py        # НОВЫЙ: маршруты промокодов
```

---

## 2. Domain Layer — дополнения

### `orders/src/orders/domain/entities.py` — добавить:

```python
class DiscountType(StrEnum):
    """Type of discount applied by a promocode."""

    FIXED = "FIXED"           # фиксированная сумма (например, 500 ₽)
    PERCENTAGE = "PERCENTAGE" # процент (например, 10%)


class PromocodeStatus(StrEnum):
    """Lifecycle status of a promocode."""

    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    DISABLED = "DISABLED"
```

### `orders/src/orders/domain/exceptions.py` — добавить:

| Класс | `code` | `message` |
|---|---|---|
| `PromocodeError` | `"promocode_error"` | `"Promocode operation failed"` |
| `PromocodeNotFound` | `"promocode_not_found"` | `"Promocode not found"` |
| `PromocodeExpired` | `"promocode_expired"` | `"Promocode has expired"` |
| `PromocodeDisabled` | `"promocode_disabled"` | `"Promocode is disabled"` |
| `PromocodeLimitReached` | `"promocode_limit_reached"` | `"Promocode usage limit reached"` |
| `PromocodeAlreadyUsed` | `"promocode_already_used"` | `"You have already used this promocode"` |
| `PromocodeMinAmountNotMet` | `"promocode_min_amount"` | `"Order amount is below minimum for this promocode"` |
| `DuplicatePromocodeCode` | `"duplicate_promocode_code"` | `"A promocode with this code already exists"` |

---

## 3. Infrastructure Layer

### ORM-модели (добавить в `orders/src/orders/infrastructure/models.py`)

#### `PromocodeModel`

| Колонка | SQLAlchemy type | Python type | Constraints |
|---|---|---|---|
| `id` | `Uuid` | `uuid.UUID` | PK, default `uuid.uuid7` |
| `code` | `String(50)` | `str` | NOT NULL, UNIQUE, INDEX, uppercase |
| `discount_type` | `String(20)` | `DiscountType` | NOT NULL |
| `discount_value` | `Numeric(12, 2)` | `Decimal` | NOT NULL, `> 0` |
| `currency` | `String(3)` | `str` | NOT NULL, default `"RUB"` |
| `min_order_amount` | `Numeric(12, 2)` | `Decimal \| None` | nullable — минимальная сумма заказа |
| `max_discount_amount` | `Numeric(12, 2)` | `Decimal \| None` | nullable — потолок скидки для % |
| `max_uses` | `Integer` | `int \| None` | nullable — общий лимит использований |
| `max_uses_per_user` | `Integer` | `int` | NOT NULL, default `1` |
| `current_uses` | `Integer` | `int` | NOT NULL, default `0` |
| `status` | `String(20)` | `PromocodeStatus` | NOT NULL, default `ACTIVE` |
| `starts_at` | `DateTime(tz)` | `datetime` | NOT NULL |
| `expires_at` | `DateTime(tz)` | `datetime` | NOT NULL |
| `created_at` | `DateTime(tz)` | `datetime` | NOT NULL, default `utc_now` |

**`__tablename__`** = `"promocodes"`

**`__table_args__`:**
```python
(
    CheckConstraint("discount_value > 0", name="ck_promocodes_value_positive"),
    CheckConstraint("current_uses >= 0", name="ck_promocodes_uses_non_negative"),
    CheckConstraint("expires_at > starts_at", name="ck_promocodes_valid_period"),
)
```

> [!IMPORTANT]
> `discount_value` — это `Decimal`, НЕ `float`. Для `PERCENTAGE` значение в диапазоне 0.01–100.00 (процент). Для `FIXED` — абсолютная сумма в валюте.

> [!IMPORTANT]
> `code` хранится в uppercase. При проверке промокода на входе вызывать `.strip().upper()`.

#### `PromocodeUsageModel`

| Колонка | SQLAlchemy type | Python type | Constraints |
|---|---|---|---|
| `id` | `Uuid` | `uuid.UUID` | PK, default `uuid.uuid7` |
| `promocode_id` | `Uuid`, FK → `promocodes.id` | `uuid.UUID` | NOT NULL, INDEX |
| `user_id` | `Uuid` | `uuid.UUID` | NOT NULL, INDEX |
| `order_id` | `Uuid` | `uuid.UUID` | NOT NULL, UNIQUE |
| `discount_amount` | `Numeric(12, 2)` | `Decimal` | NOT NULL — фактическая скидка |
| `created_at` | `DateTime(tz)` | `datetime` | NOT NULL, default `utc_now` |

**`__tablename__`** = `"promocode_usages"`

**`__table_args__`:**
```python
(
    UniqueConstraint("promocode_id", "order_id", name="uq_usage_promocode_order"),
    Index("ix_usage_promocode_user", "promocode_id", "user_id"),
)
```

### `PromocodeRepository`

| Метод | Сигнатура | Описание |
|---|---|---|
| `create` | `(promo: PromocodeModel) -> PromocodeModel` | add, flush |
| `get_by_code` | `(code: str) -> PromocodeModel \| None` | WHERE code = upper(code), `FOR UPDATE` (pessimistic lock) |
| `get_by_id` | `(promo_id: UUID) -> PromocodeModel \| None` | SELECT |
| `list_all` | `(limit, offset) -> PromocodePage` | Все, сортировка `created_at DESC` |
| `update` | `(promo: PromocodeModel) -> PromocodeModel` | flush |
| `count_user_usages` | `(promo_id: UUID, user_id: UUID) -> int` | COUNT usages |
| `add_usage` | `(usage: PromocodeUsageModel) -> PromocodeUsageModel` | add, flush |

> [!IMPORTANT]
> `get_by_code` использует `FOR UPDATE` (pessimistic lock). Это предотвращает race condition когда два запроса одновременно пытаются использовать последнее доступное использование промокода.

---

## 4. Application Layer

### `PromocodeService`

#### `create_promocode(data: CreatePromocodeRequest) -> PromocodeModel`

1. `code = data.code.strip().upper()`
2. Проверить уникальность — если exists → `DuplicatePromocodeCode`
3. Если `discount_type == PERCENTAGE` — проверить `0 < discount_value <= 100`
4. Создать model, commit, return

#### `validate_and_apply(code: str, user_id: UUID, order_amount: Decimal) -> PromocodeResult`

Это главный метод. Вызывается при создании заказа.

1. `code = code.strip().upper()`
2. `promo = repo.get_by_code(code)` — если None → `PromocodeNotFound`
3. Проверить `promo.status == ACTIVE` — иначе `PromocodeDisabled`
4. Проверить `utc_now() >= promo.starts_at` и `utc_now() <= promo.expires_at` — иначе `PromocodeExpired`
5. Проверить `promo.max_uses is None or promo.current_uses < promo.max_uses` — иначе `PromocodeLimitReached`
6. Проверить `repo.count_user_usages(promo.id, user_id) < promo.max_uses_per_user` — иначе `PromocodeAlreadyUsed`
7. Проверить `promo.min_order_amount is None or order_amount >= promo.min_order_amount` — иначе `PromocodeMinAmountNotMet`
8. Рассчитать скидку:
   ```python
   if promo.discount_type == DiscountType.FIXED:
       discount = min(promo.discount_value, order_amount)
   else:  # PERCENTAGE
       discount = order_amount * promo.discount_value / 100
       if promo.max_discount_amount:
           discount = min(discount, promo.max_discount_amount)
   discount = discount.quantize(Decimal("0.01"))
   ```
9. Return `PromocodeResult(promocode_id=promo.id, discount_amount=discount, final_amount=order_amount - discount)`

> [!IMPORTANT]
> Этот метод **не** записывает usage и не инкрементирует `current_uses`. Это делает Orders service после успешного создания заказа, вызывая `record_usage()`.

#### `record_usage(promo_id: UUID, user_id: UUID, order_id: UUID, discount_amount: Decimal) -> None`

1. Создать `PromocodeUsageModel(...)`
2. `repo.add_usage(usage)`
3. Инкрементировать `promo.current_uses += 1`
4. `repo.update(promo)`

> [!NOTE]
> `validate_and_apply` и `record_usage` вызываются в рамках одной транзакции в Orders service.

---

## 5. API Layer — `orders/src/orders/api/routes/promocodes.py`

**Router:** `prefix="/api/v1/promocodes"`, `tags=["promocodes"]`

| Method | Path | Функция | Request | Response | Status | Описание |
|---|---|---|---|---|---|---|
| `POST` | `/` | `create_promocode` | `CreatePromocodeRequest` | `PromocodeResponse` | 201 | Создать (admin) |
| `GET` | `/` | `list_promocodes` | Query params | `PromocodeListResponse` | 200 | Список (admin) |
| `GET` | `/{promo_id}` | `get_promocode` | — | `PromocodeResponse` | 200 | Получить (admin) |
| `PATCH` | `/{promo_id}` | `update_promocode` | `UpdatePromocodeRequest` | `PromocodeResponse` | 200 | Обновить (admin) |
| `POST` | `/validate` | `validate_promocode` | `ValidatePromocodeRequest` | `PromocodeValidationResponse` | 200 | Проверить промокод (public) |

**`ValidatePromocodeRequest`:**

| Поле | Тип |
|---|---|
| `code` | `str` |
| `user_id` | `uuid.UUID` |
| `order_amount` | `Decimal` |

**`PromocodeValidationResponse`:**

| Поле | Тип |
|---|---|
| `valid` | `bool` |
| `discount_amount` | `Decimal` |
| `final_amount` | `Decimal` |
| `error` | `str \| None` |

---

## 6. Интеграция с Orders

В метод создания заказа (существующий `POST /api/v1/orders`) добавить опциональное поле:

```python
class CreateOrderRequest(BaseModel):
    # ...существующие поля...
    promocode: str | None = None  # НОВОЕ: опциональный промокод
```

В `OrderService.create_order()`:

```python
discount_amount = Decimal("0")
promocode_id = None

if data.promocode:
    result = promocode_service.validate_and_apply(
        code=data.promocode,
        user_id=data.user_id,
        order_amount=data.price,
    )
    discount_amount = result.discount_amount
    promocode_id = result.promocode_id

# создать заказ с final_price = data.price - discount_amount
order = OrderModel(
    ...
    original_price=data.price,
    discount_amount=discount_amount,
    final_price=data.price - discount_amount,
    promocode_id=promocode_id,
)

# после commit:
if promocode_id:
    promocode_service.record_usage(promocode_id, data.user_id, order.id, discount_amount)
```

### Миграция OrderModel — новые колонки:

| Колонка | Тип | Описание |
|---|---|---|
| `original_price` | `Numeric(12, 2)` | Цена до скидки (бывшее `price`) |
| `discount_amount` | `Numeric(12, 2)` | Сумма скидки, default `0` |
| `final_price` | `Numeric(12, 2)` | Итоговая цена |
| `promocode_id` | `Uuid`, nullable | FK → `promocodes.id`, nullable |

---

## 7. Gateway

Добавить в `nginx.conf`:

```nginx
location /api/v1/promocodes {
    proxy_pass http://orders;
}
```

---

## 8. Тесты

| Тест | Описание |
|---|---|
| `test_create_promocode` | Создать промокод, проверить поля |
| `test_create_duplicate_code_409` | Дублирующий code → 409 |
| `test_validate_fixed_discount` | FIXED 500₽ на заказ 2000₽ → скидка 500, итого 1500 |
| `test_validate_percentage_discount` | 10% на заказ 10000₽ → скидка 1000, итого 9000 |
| `test_validate_percentage_with_cap` | 20% с max_discount_amount=500 на 10000₽ → скидка 500 |
| `test_validate_expired` | Истёкший промокод → PromocodeExpired |
| `test_validate_disabled` | Отключённый промокод → PromocodeDisabled |
| `test_validate_limit_reached` | max_uses=1, использован → PromocodeLimitReached |
| `test_validate_user_limit` | max_uses_per_user=1, использован → PromocodeAlreadyUsed |
| `test_validate_min_amount` | min_order_amount=5000, заказ 3000 → PromocodeMinAmountNotMet |
| `test_discount_not_exceed_order` | FIXED 5000₽ на заказ 3000₽ → скидка 3000 (не больше суммы) |
| `test_code_case_insensitive` | `"flash10"` и `"FLASH10"` → один промокод |
| `test_order_with_promocode` | Создать заказ с промокодом → final_price с учётом скидки |

---
---

# ТЗ-4: Размеры и варианты товаров (SKU)

## 1. Место в проекте

Реализуется как расширение **Catalog Service** + изменения в **Inventory Service**.

```
catalog/src/catalog/
├── infrastructure/
│   ├── models.py              # добавить ProductVariantModel
│   └── repositories/
│       └── variant.py         # НОВЫЙ
├── application/
│   ├── schemas.py             # добавить variant схемы
│   └── services/
│       └── variant.py         # НОВЫЙ
└── api/routes/
    └── variants.py            # НОВЫЙ

inventory/src/inventory/
├── infrastructure/
│   └── models.py              # StockModel: добавить variant_id
└── application/
    └── ...                    # изменить логику привязки стока
```

---

## 2. Концепция

**Сейчас:** `Product` → `Stock` (один сток на продукт)

**Будет:** `Product` → `ProductVariant[]` → `Stock` (один сток на вариант)

Пример:
```
Product: "Flash Sect Oversized Hoodie"
├── Variant: size=S, color=Black, sku=FSH-BLK-S   → Stock: 15 шт
├── Variant: size=M, color=Black, sku=FSH-BLK-M   → Stock: 25 шт
├── Variant: size=L, color=Black, sku=FSH-BLK-L   → Stock: 10 шт
├── Variant: size=S, color=White, sku=FSH-WHT-S   → Stock: 8 шт
└── Variant: size=M, color=White, sku=FSH-WHT-M   → Stock: 12 шт
```

---

## 3. Catalog Service — новая модель

### `ProductVariantModel` (добавить в `catalog/src/catalog/infrastructure/models.py`)

| Колонка | SQLAlchemy type | Python type | Constraints |
|---|---|---|---|
| `id` | `Uuid` | `uuid.UUID` | PK, default `uuid.uuid7` |
| `product_id` | `Uuid`, FK → `products.id` | `uuid.UUID` | NOT NULL, `ondelete="CASCADE"`, INDEX |
| `sku` | `String(100)` | `str` | NOT NULL, UNIQUE, INDEX |
| `size` | `String(20)` | `str \| None` | nullable — "XS", "S", "M", "L", "XL", "XXL", "ONE SIZE" |
| `color` | `String(50)` | `str \| None` | nullable — название цвета |
| `color_hex` | `String(7)` | `str \| None` | nullable — "#000000" |
| `material` | `String(100)` | `str \| None` | nullable |
| `weight_grams` | `Integer` | `int \| None` | nullable |
| `price_override` | `Numeric(12, 2)` | `Decimal \| None` | nullable — если цена варианта отличается от product.price |
| `is_active` | `Boolean` | `bool` | NOT NULL, default `True` |
| `sort_order` | `Integer` | `int` | NOT NULL, default `0` |
| `created_at` | `DateTime(tz)` | `datetime` | NOT NULL, default `utc_now` |

**`__tablename__`** = `"product_variants"`

**`__table_args__`:**
```python
(
    UniqueConstraint("product_id", "size", "color", name="uq_variant_product_size_color"),
    Index("ix_variants_product_active", "product_id", "is_active"),
)
```

**Relationship на ProductModel:**
```python
# Добавить в ProductModel:
variants: Mapped[list[ProductVariantModel]] = relationship(
    back_populates="product",
    cascade="all, delete-orphan",
    passive_deletes=True,
    order_by="ProductVariantModel.sort_order",
    lazy="selectin",
)
```

> [!IMPORTANT]
> `sku` — Stock Keeping Unit — уникальный идентификатор варианта. Формат: `{BRAND_PREFIX}-{COLOR_CODE}-{SIZE}`. SKU генерируется автоматически или задаётся вручную.

> [!IMPORTANT]
> `price_override` — опциональная цена варианта. Если `None`, используется `product.price`. Это позволяет ставить разные цены на разные размеры/материалы.

---

## 4. Catalog Service — schemas

### Request

**`CreateVariantRequest`:**

| Поле | Тип | Constraints |
|---|---|---|
| `sku` | `str \| None` | `max_length=100` — если None, генерируется автоматически |
| `size` | `str \| None` | `max_length=20` |
| `color` | `str \| None` | `max_length=50` |
| `color_hex` | `str \| None` | `pattern=r"^#[0-9a-fA-F]{6}$"` |
| `material` | `str \| None` | `max_length=100` |
| `weight_grams` | `int \| None` | `ge=0` |
| `price_override` | `Decimal \| None` | `gt=0` |
| `is_active` | `bool` | default `True` |
| `sort_order` | `int` | default `0`, `ge=0` |

**`UpdateVariantRequest`:** все поля опциональные.

### Response

**`VariantResponse`:**

| Поле | Тип |
|---|---|
| `id` | `uuid.UUID` |
| `product_id` | `uuid.UUID` |
| `sku` | `str` |
| `size` | `str \| None` |
| `color` | `str \| None` |
| `color_hex` | `str \| None` |
| `material` | `str \| None` |
| `weight_grams` | `int \| None` |
| `price_override` | `Decimal \| None` |
| `effective_price` | `Decimal` — computed: `price_override or product.price` |
| `is_active` | `bool` |
| `sort_order` | `int` |
| `created_at` | `datetime` |

Добавить `variants: list[VariantResponse]` в существующий `ProductResponse`.

---

## 5. Catalog Service — API

**Router:** `prefix="/api/v1/products/{product_id}/variants"`, `tags=["variants"]`

| Method | Path | Функция | Request | Response | Status |
|---|---|---|---|---|---|
| `POST` | `/` | `create_variant` | `CreateVariantRequest` | `VariantResponse` | 201 |
| `GET` | `/` | `list_variants` | — | `list[VariantResponse]` | 200 |
| `GET` | `/{variant_id}` | `get_variant` | — | `VariantResponse` | 200 |
| `PATCH` | `/{variant_id}` | `update_variant` | `UpdateVariantRequest` | `VariantResponse` | 200 |
| `DELETE` | `/{variant_id}` | `delete_variant` | — | 204 | 204 |

---

## 6. Inventory Service — изменения

### StockModel — добавить колонку:

| Колонка | Тип | Описание |
|---|---|---|
| `variant_id` | `Uuid`, nullable, INDEX | ID варианта. NULL для товаров без вариантов (обратная совместимость) |

**Уникальность:** заменить `unique=True` на `product_id` на:
```python
UniqueConstraint("product_id", "variant_id", name="uq_stocks_product_variant")
```

### Изменения в API

В `StockCreateRequest` добавить:
```python
variant_id: uuid.UUID | None = None
```

В `POST /api/v1/stocks/{product_id}/reserve` добавить:
```python
variant_id: uuid.UUID | None = None
```

Логика:
- Если у товара есть варианты → `variant_id` обязателен при резервации
- Если у товара нет вариантов → `variant_id` должен быть None (обратная совместимость)

### StockResponse — добавить:
```python
variant_id: uuid.UUID | None
```

---

## 7. Миграция данных

Новая Alembic миграция для catalog:
1. Создать таблицу `product_variants`
2. Миграция данных не требуется — существующие товары просто не будут иметь вариантов

Новая Alembic миграция для inventory:
1. Добавить колонку `variant_id` (nullable) в `stocks`
2. Обновить unique constraint
3. Существующие стоки остаются с `variant_id = NULL`

---

## 8. Автогенерация SKU

В `VariantService`:

```python
def generate_sku(product_name: str, size: str | None, color: str | None) -> str:
    parts = []
    # Первые 3 буквы каждого слова в product_name
    for word in product_name.split()[:3]:
        parts.append(slugify(word)[:3].upper())
    prefix = "-".join(parts) or "ITEM"

    if color:
        parts.append(slugify(color)[:3].upper())
    if size:
        parts.append(size.upper())

    return "-".join(filter(None, [prefix, slugify(color or "")[:3].upper() if color else None, size.upper() if size else None]))
```

Если сгенерированный SKU уже существует — добавить суффикс `-2`, `-3` (аналогично slug в products).

---

## 9. Тесты

| Тест | Описание |
|---|---|
| `test_create_variant` | Создать вариант для товара |
| `test_create_variant_auto_sku` | SKU генерируется автоматически |
| `test_create_variant_custom_sku` | SKU задан вручную |
| `test_duplicate_sku_409` | Дублирующий SKU → 409 |
| `test_duplicate_size_color_409` | Одинаковые size+color для одного product → 409 |
| `test_list_variants` | Получить список вариантов товара |
| `test_update_variant` | Обновить size/color |
| `test_delete_variant` | Удалить вариант |
| `test_product_response_includes_variants` | GET product → включает variants[] |
| `test_effective_price_uses_override` | price_override=500 → effective_price=500 |
| `test_effective_price_uses_product` | price_override=None → effective_price=product.price |
| `test_stock_with_variant` | Создать сток для варианта |
| `test_reserve_with_variant` | Зарезервировать конкретный вариант |
| `test_stock_without_variant_backward_compat` | Товар без вариантов работает как раньше |

---

## 10. Чеклист качества

- [ ] Товары без вариантов работают как раньше (обратная совместимость!)
- [ ] SKU уникален глобально (UNIQUE constraint)
- [ ] Пара (product_id, size, color) уникальна
- [ ] `effective_price` вычисляется корректно
- [ ] Inventory привязывается к variant_id когда он есть
- [ ] Все существующие тесты проходят без изменений
- [ ] Новые тесты покрывают все CRUD операции
