# Catalog Service — Техническое задание

> Исчерпывающая инструкция по реализации микросервиса Catalog для проекта FlashMarket.  
> Документ покрывает каждый файл, каждый класс, каждое поле, каждый метод — реализатору не нужно принимать архитектурных решений.

---

## 1. Место сервиса в проекте

```
flashmarket/
├── auth/          ← уже реализован
├── catalog/       ← ЭТО ТЗ
├── inventory/     ← будущий сервис
└── order/         ← будущий сервис
```

Catalog Service **не знает** о пользователях, корзинах, заказах, оплате и остатках.  
Его единственная зона ответственности — **каталог товаров и категорий**.

---

## 2. Стек технологий

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
| Package Manager | uv | любая актуальная |
| Linter/Formatter | ruff | ≥ 0.16 |
| Types | mypy (strict) | ≥ 2.1 |
| Tests | pytest + pytest-asyncio + httpx | |
| Test DB | aiosqlite (in-memory SQLite) | ≥ 0.22 |
| Build Backend | hatchling | |

---

## 3. Структура файлов

```
catalog/
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
│   └── catalog/
│       ├── __init__.py
│       ├── main.py
│       ├── config.py
│       │
│       ├── domain/
│       │   ├── __init__.py
│       │   ├── entities.py          # Enums: ProductStatus, Currency
│       │   └── exceptions.py        # Доменные исключения
│       │
│       ├── application/
│       │   ├── __init__.py
│       │   ├── schemas.py           # Pydantic request/response модели
│       │   └── services/
│       │       ├── __init__.py
│       │       ├── product.py       # ProductService
│       │       └── category.py      # CategoryService
│       │
│       ├── api/
│       │   ├── __init__.py
│       │   ├── dependencies.py      # DI: SessionDep, ServiceDep
│       │   ├── error_handlers.py    # Exception → JSONResponse маппинг
│       │   └── routes/
│       │       ├── __init__.py
│       │       ├── products.py      # /api/v1/products
│       │       ├── internal.py      # /api/v1/internal/products
│       │       ├── categories.py    # /api/v1/categories
│       │       └── health.py        # /health/ready
│       │
│       └── infrastructure/
│           ├── __init__.py
│           ├── database.py          # engine, SessionFactory, Base, get_db()
│           ├── models.py            # ORM модели: ProductModel, CategoryModel, ProductImageModel
│           └── repositories/
│               ├── __init__.py
│               ├── product.py       # ProductRepository
│               └── category.py      # CategoryRepository
│
└── tests/
    ├── __init__.py
    ├── conftest.py                  # фикстуры: app, client, db session
    ├── test_slug.py                 # slug generation + uniqueness
    ├── test_product_service.py      # создание, архивация, валидация
    ├── test_category_service.py     # дерево категорий
    ├── test_products_api.py         # HTTP: CRUD, поиск, фильтрация, сортировка
    └── test_categories_api.py       # HTTP: создание, дерево
```

---

## 4. pyproject.toml

```toml
[project]
name = "flashmarket-catalog"
version = "0.1.0"
description = "Product catalog service for FlashMarket"
readme = "README.md"
requires-python = ">=3.14"
dependencies = [
    "alembic>=1.18,<2",
    "asyncpg>=0.31,<1",
    "fastapi>=0.140,<1",
    "pydantic-settings>=2.14,<3",
    "sqlalchemy>=2.0,<3",
    "uvicorn[standard]>=0.51,<1",
    "python-slugify>=8.0,<9",
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
packages = ["src/catalog"]

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
files = ["src/catalog"]
plugins = ["pydantic.mypy"]
strict = true
pretty = true
show_error_codes = true
show_error_context = true
warn_unreachable = true
```

> [!IMPORTANT]
> Зависимость `python-slugify` используется для транслитерации и генерации slug. Не писать свой slug-генератор руками — использовать `slugify()` из этой библиотеки.

---

## 5. Конфигурация

### 5.1. `src/catalog/config.py`

Класс `Settings` наследует `pydantic_settings.BaseSettings`.

| Поле | Тип | Default | Описание |
|---|---|---|---|
| `app_name` | `str` | `"FlashMarket Catalog"` | Имя приложения |
| `environment` | `Literal["development", "test", "production"]` | `"development"` | Окружение |
| `debug` | `bool` | `False` | Режим отладки |
| `database_url` | `str` | `"postgresql+asyncpg://flashmarket:flashmarket@localhost:5432/catalog"` | URL базы данных |
| `docs_enabled` | `bool` | `True` | Swagger/ReDoc |
| `trusted_hosts` | `list[str]` | `["localhost", "127.0.0.1"]` | Trusted hosts |
| `cors_origins` | `list[str]` | `[]` | CORS origins |

**Конвенции** (как в auth):
- `env_prefix = "CATALOG_"`
- `env_file = ".env"`
- `extra = "ignore"`
- Функция `get_settings()` с декоратором `@lru_cache`
- Production-валидатор `@model_validator(mode="after")`:
  - `debug` must be `False`
  - `docs_enabled` must be `False`
  - default DB credentials запрещены

### 5.2. `.env.example`

```env
CATALOG_ENVIRONMENT=development
CATALOG_DEBUG=false
CATALOG_DATABASE_URL=postgresql+asyncpg://flashmarket:flashmarket@localhost:5432/catalog
CATALOG_DOCS_ENABLED=true
CATALOG_CORS_ORIGINS=["http://localhost:3000"]
CATALOG_TRUSTED_HOSTS=["localhost","127.0.0.1"]
```

---

## 6. Domain Layer

### 6.1. `src/catalog/domain/entities.py`

```python
# Два Enum-класса, оба StrEnum

class ProductStatus(StrEnum):
    ACTIVE = "ACTIVE"
    HIDDEN = "HIDDEN"
    ARCHIVED = "ARCHIVED"

class Currency(StrEnum):
    RUB = "RUB"
    USD = "USD"
    EUR = "EUR"
```

### 6.2. `src/catalog/domain/exceptions.py`

Все доменные исключения наследуют один базовый `CatalogError`, по паттерну auth:

| Класс | `code` | `message` |
|---|---|---|
| `CatalogError` | `"catalog_error"` | `"The operation could not be completed"` |
| `ProductNotFound` | `"product_not_found"` | `"Product not found"` |
| `CategoryNotFound` | `"category_not_found"` | `"Category not found"` |
| `DuplicateSlug` | `"duplicate_slug"` | `"A product with this slug already exists"` |
| `InvalidProductData` | `"invalid_product_data"` | `"Product data validation failed"` |

Каждый класс имеет атрибуты:
- `code: str` — уникальный код ошибки (class-level)
- `message: str` — дефолтное сообщение (class-level)
- `__init__(self, message: str | None = None) -> None` — конструктор сохраняет `self.public_message`

Паттерн полностью повторяет [errors.py](file:///c:/Users/mickey/Desktop/flashmarket/auth/src/auth_service/application/errors.py) из auth.

---

## 7. Infrastructure Layer

### 7.1. `src/catalog/infrastructure/database.py`

Повторяет паттерн [database.py](file:///c:/Users/mickey/Desktop/flashmarket/auth/src/auth_service/database.py) из auth:

```python
engine = create_async_engine(settings.database_url, pool_pre_ping=True)
SessionFactory = async_sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

async def get_db() -> AsyncIterator[AsyncSession]:
    async with SessionFactory() as session:
        try:
            yield session
        finally:
            await session.rollback()
```

### 7.2. `src/catalog/infrastructure/models.py` — ORM-модели

#### 7.2.1. `CategoryModel`

| Колонка | SQLAlchemy type | Python type | Constraints |
|---|---|---|---|
| `id` | `Uuid` | `uuid.UUID` | PK, default `uuid.uuid7` |
| `name` | `String(255)` | `str` | NOT NULL |
| `slug` | `String(255)` | `str` | NOT NULL, UNIQUE |
| `parent_id` | `Uuid`, FK → `categories.id` | `uuid.UUID \| None` | nullable, `ondelete="SET NULL"`, INDEX |
| `created_at` | `DateTime(timezone=True)` | `datetime` | NOT NULL, default `utc_now` |

**Relationships:**
- `children: Mapped[list[CategoryModel]]` — `relationship("CategoryModel", back_populates="parent", ...)` — lazy="selectin"
- `parent: Mapped[CategoryModel | None]` — `relationship("CategoryModel", back_populates="children", remote_side=[id])`

**`__tablename__`** = `"categories"`

**Индексы:**
- `slug` — UNIQUE (через `mapped_column(..., unique=True)`)
- `parent_id` — INDEX (через `mapped_column(..., index=True)`)

#### 7.2.2. `ProductModel`

| Колонка | SQLAlchemy type | Python type | Constraints |
|---|---|---|---|
| `id` | `Uuid` | `uuid.UUID` | PK, default `uuid.uuid7` |
| `slug` | `String(255)` | `str` | NOT NULL, UNIQUE, INDEX |
| `name` | `String(255)` | `str` | NOT NULL |
| `description` | `Text` | `str` | NOT NULL, default `""` |
| `price` | `Numeric(precision=12, scale=2)` | `Decimal` | NOT NULL, `CheckConstraint("price > 0")` |
| `currency` | `Enum(Currency, name="currency")` | `Currency` | NOT NULL, default `Currency.RUB`, server_default `"RUB"` |
| `status` | `Enum(ProductStatus, name="product_status")` | `ProductStatus` | NOT NULL, default `ProductStatus.HIDDEN`, server_default `"HIDDEN"` |
| `category_id` | `Uuid`, FK → `categories.id` | `uuid.UUID` | NOT NULL, `ondelete="RESTRICT"`, INDEX |
| `cover_image` | `String(2048)` | `str \| None` | nullable |
| `created_at` | `DateTime(timezone=True)` | `datetime` | NOT NULL, default `utc_now`, INDEX |
| `updated_at` | `DateTime(timezone=True)` | `datetime` | NOT NULL, default `utc_now`, onupdate `utc_now` |
| `published_at` | `DateTime(timezone=True)` | `datetime \| None` | nullable |

**Relationships:**
- `category: Mapped[CategoryModel]` — `relationship(lazy="joined")`
- `images: Mapped[list[ProductImageModel]]` — `relationship(back_populates="product", cascade="all, delete-orphan", passive_deletes=True, order_by="ProductImageModel.sort_order")` — lazy="selectin"

**`__tablename__`** = `"products"`

**`__table_args__`:**
```python
(
    CheckConstraint("price > 0", name="ck_products_price_positive"),
    Index("ix_products_status", "status"),
    Index("ix_products_price", "price"),
    Index("ix_products_category_status", "category_id", "status"),
)
```

> [!IMPORTANT]
> Поле `price` — `Numeric(12, 2)`, НЕ `Float`. Это критически важно для финансовых данных.

#### 7.2.3. `ProductImageModel`

| Колонка | SQLAlchemy type | Python type | Constraints |
|---|---|---|---|
| `id` | `Uuid` | `uuid.UUID` | PK, default `uuid.uuid7` |
| `product_id` | `Uuid`, FK → `products.id` | `uuid.UUID` | NOT NULL, `ondelete="CASCADE"`, INDEX |
| `url` | `String(2048)` | `str` | NOT NULL |
| `sort_order` | `Integer` | `int` | NOT NULL, default `0` |
| `created_at` | `DateTime(timezone=True)` | `datetime` | NOT NULL, default `utc_now` |

**Relationship:**
- `product: Mapped[ProductModel]` — `relationship(back_populates="images")`

**`__tablename__`** = `"product_images"`

#### 7.2.4. Вспомогательная функция `utc_now`

Определить в `src/catalog/infrastructure/database.py` или в отдельном `src/catalog/infrastructure/time.py`:

```python
from datetime import UTC, datetime

def utc_now() -> datetime:
    return datetime.now(UTC)
```

Используется как default для `created_at`, `updated_at` (по паттерну auth).

### 7.3. Repositories

#### 7.3.1. `src/catalog/infrastructure/repositories/product.py` — `ProductRepository`

Конструктор принимает `session: AsyncSession`, хранит в `self._session`.

**Методы:**

| Метод | Сигнатура | Описание |
|---|---|---|
| `create` | `(product: ProductModel) -> ProductModel` | `session.add(product)`, `session.flush()`, return product |
| `get_by_id` | `(product_id: UUID) -> ProductModel \| None` | `select(ProductModel).where(id == product_id)` с `selectinload(images)` и `joinedload(category)` |
| `get_by_slug` | `(slug: str) -> ProductModel \| None` | `select(ProductModel).where(slug == slug)` с `selectinload(images)` и `joinedload(category)` |
| `slug_exists` | `(slug: str) -> bool` | `select(func.count()).select_from(ProductModel).where(slug == slug)`, return `count > 0` |
| `search` | `(filters: ProductSearchQuery) -> ProductPage` | См. раздел «Поиск» ниже |
| `update` | `(product: ProductModel) -> ProductModel` | `session.flush()`, return product (мутации на ORM-объекте) |
| `replace_images` | `(product_id: UUID, images: list[ProductImageModel]) -> None` | Удаляет все старые `ProductImageModel` по `product_id`, добавляет новые через `session.add_all()`, `session.flush()` |

> [!IMPORTANT]
> Каждый `select` для ProductModel должен содержать `options(selectinload(ProductModel.images), joinedload(ProductModel.category))` чтобы избежать N+1.

**Поиск — метод `search`:**

Принимает dataclass `ProductSearchQuery`:

```python
@dataclass(frozen=True, slots=True)
class ProductSearchQuery:
    limit: int
    offset: int
    category_id: UUID | None = None
    status: ProductStatus | None = None
    price_from: Decimal | None = None
    price_to: Decimal | None = None
    search: str | None = None
    sort_by: str = "created_at"
    sort_order: str = "desc"
```

```python
@dataclass(frozen=True, slots=True)
class ProductPage:
    items: list[ProductModel]
    total: int
```

**Логика фильтрации** (построение `filters: list`):
1. `category_id` — `ProductModel.category_id == category_id`
2. `status` — `ProductModel.status == status`
3. `price_from` — `ProductModel.price >= price_from`
4. `price_to` — `ProductModel.price <= price_to`
5. `search` — `or_(ProductModel.name.ilike(f"%{search}%"), ProductModel.description.ilike(f"%{search}%"))`

**Логика сортировки** — маппинг строки в колонку:

| `sort_by` | Колонка |
|---|---|
| `"price"` | `ProductModel.price` |
| `"name"` | `ProductModel.name` |
| `"created_at"` (default) | `ProductModel.created_at` |

Направление: `asc()` или `desc()` в зависимости от `sort_order`.

**Два запроса:**
1. `select(ProductModel).where(*filters).options(...).order_by(...).limit(limit).offset(offset)` — items
2. `select(func.count()).select_from(ProductModel).where(*filters)` — total

Return `ProductPage(items=..., total=...)`.

#### 7.3.2. `src/catalog/infrastructure/repositories/category.py` — `CategoryRepository`

Конструктор принимает `session: AsyncSession`.

**Методы:**

| Метод | Сигнатура | Описание |
|---|---|---|
| `create` | `(category: CategoryModel) -> CategoryModel` | `session.add()`, `session.flush()`, return |
| `get_by_id` | `(category_id: UUID) -> CategoryModel \| None` | `select().where(id == ...)` |
| `slug_exists` | `(slug: str) -> bool` | аналогично product |
| `list_all` | `() -> list[CategoryModel]` | `select(CategoryModel).options(selectinload(CategoryModel.children)).where(parent_id.is_(None)).order_by(name)` — загружает только корневые категории, children подгружаются через selectinload рекурсивно |

> [!IMPORTANT]
> Для построения дерева категорий: загружать только корневые (`parent_id IS NULL`), children подтягиваются через `selectinload`. SQLAlchemy рекурсивно загрузит вложенные уровни. Для глубокой вложенности (> 2 уровней) использовать `selectinload(CategoryModel.children).selectinload(CategoryModel.children)` или написать рекурсивную сборку в service-слое.

---

## 8. Application Layer

### 8.1. `src/catalog/application/schemas.py` — Pydantic-модели

Все модели наследуют `pydantic.BaseModel`. Все используют `model_config = ConfigDict(from_attributes=True)` где нужно.

#### Request-модели

**`CreateCategoryRequest`**:

| Поле | Тип | Constraints | Описание |
|---|---|---|---|
| `name` | `str` | `min_length=1, max_length=255` | Имя категории |
| `slug` | `str` | `min_length=1, max_length=255, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$"` | Slug (ручной ввод) |
| `parent_id` | `uuid.UUID \| None` | — | Родительская категория |

**`CreateProductRequest`**:

| Поле | Тип | Constraints | Описание |
|---|---|---|---|
| `name` | `str` | `min_length=1, max_length=255` | Название |
| `description` | `str` | default `""` | Описание |
| `price` | `Decimal` | `gt=0` | Цена (Decimal, не float) |
| `currency` | `Currency` | default `Currency.RUB` | Валюта |
| `category_id` | `uuid.UUID` | required | ID категории |
| `cover_image` | `str \| None` | `max_length=2048` | URL обложки |
| `images` | `list[ImageInput]` | default `[]` | Список картинок |
| `status` | `ProductStatus` | default `ProductStatus.HIDDEN` | Начальный статус |

**`ImageInput`**:

| Поле | Тип | Constraints |
|---|---|---|
| `url` | `str` | `min_length=1, max_length=2048` |
| `sort_order` | `int` | `ge=0`, default `0` |

**`UpdateProductRequest`**:

Все поля опциональные (`None` по умолчанию), кроме:

| Поле | Тип | Constraints |
|---|---|---|
| `name` | `str \| None` | `min_length=1, max_length=255` |
| `description` | `str \| None` | — |
| `price` | `Decimal \| None` | `gt=0` |
| `currency` | `Currency \| None` | — |
| `category_id` | `uuid.UUID \| None` | — |
| `cover_image` | `str \| None` | `max_length=2048` |
| `images` | `list[ImageInput] \| None` | — |
| `status` | `ProductStatus \| None` | — |

**`ProductListParams`** (используется как `Query` параметры):

| Поле | Тип | Default | Constraints |
|---|---|---|---|
| `limit` | `int` | `20` | `ge=1, le=100` |
| `offset` | `int` | `0` | `ge=0` |
| `category_id` | `uuid.UUID \| None` | `None` | — |
| `status` | `ProductStatus \| None` | `None` | — |
| `price_from` | `Decimal \| None` | `None` | `ge=0` |
| `price_to` | `Decimal \| None` | `None` | `ge=0` |
| `search` | `str \| None` | `None` | `max_length=255` |
| `sort_by` | `Literal["price", "name", "created_at"]` | `"created_at"` | — |
| `sort_order` | `Literal["asc", "desc"]` | `"desc"` | — |

#### Response-модели

**`CategoryResponse`**:

| Поле | Тип |
|---|---|
| `id` | `uuid.UUID` |
| `name` | `str` |
| `slug` | `str` |
| `parent_id` | `uuid.UUID \| None` |
| `created_at` | `datetime` |

**`CategoryTreeNode`** (рекурсивная):

| Поле | Тип |
|---|---|
| `id` | `uuid.UUID` |
| `name` | `str` |
| `slug` | `str` |
| `children` | `list[CategoryTreeNode]` |

**`model_rebuild()`** вызвать после определения класса для разрешения forward reference.

**`ImageResponse`**:

| Поле | Тип |
|---|---|
| `id` | `uuid.UUID` |
| `url` | `str` |
| `sort_order` | `int` |

**`ProductResponse`**:

| Поле | Тип |
|---|---|
| `id` | `uuid.UUID` |
| `slug` | `str` |
| `name` | `str` |
| `description` | `str` |
| `price` | `Decimal` |
| `currency` | `Currency` |
| `status` | `ProductStatus` |
| `category_id` | `uuid.UUID` |
| `category_name` | `str` |
| `cover_image` | `str \| None` |
| `images` | `list[ImageResponse]` |
| `created_at` | `datetime` |
| `updated_at` | `datetime` |
| `published_at` | `datetime \| None` |

**`ProductListResponse`**:

| Поле | Тип |
|---|---|
| `items` | `list[ProductResponse]` |
| `total` | `int` |
| `limit` | `int` |
| `offset` | `int` |

**`ErrorDetail`**:

| Поле | Тип |
|---|---|
| `code` | `str` |
| `message` | `str` |
| `request_id` | `str \| None` |

**`ErrorResponse`**:

| Поле | Тип |
|---|---|
| `error` | `ErrorDetail` |

### 8.2. `src/catalog/application/services/product.py` — `ProductService`

**Конструктор:**

```python
def __init__(
    self,
    session: AsyncSession,
    product_repo: ProductRepository,
    category_repo: CategoryRepository,
) -> None:
```

**Методы:**

#### `generate_unique_slug(name: str) -> str`

1. Использовать `slugify(name)` из пакета `python-slugify`  
2. Проверить `product_repo.slug_exists(base_slug)`  
3. Если не существует → вернуть `base_slug`  
4. Если существует → попробовать `{base_slug}-2`, `{base_slug}-3`, ... до 100  
5. Если все заняты → raise `DuplicateSlug`  

> [!IMPORTANT]
> Гарантия уникальности — двойная: на уровне сервиса (проверка перед insert) + на уровне БД (UNIQUE constraint). При `IntegrityError` от БД — ловить и пробрасывать `DuplicateSlug`.

#### `create_product(data: CreateProductRequest) -> ProductModel`

1. Проверить что `category_repo.get_by_id(data.category_id)` вернул не None, иначе `CategoryNotFound`
2. Сгенерировать slug через `generate_unique_slug(data.name)`
3. Создать `ProductModel(...)` со всеми полями
4. Если `data.status == ProductStatus.ACTIVE` → установить `published_at = utc_now()`
5. Создать `ProductImageModel` для каждого элемента `data.images`
6. `product_repo.create(product)` — flush
7. Если images непустой — `product_repo.replace_images(product.id, image_models)`
8. `session.commit()`
9. `session.refresh(product)`
10. Вернуть product

#### `get_by_slug(slug: str) -> ProductModel`

1. `product_repo.get_by_slug(slug)`
2. Если `None` или `status != ProductStatus.ACTIVE` → raise `ProductNotFound`
3. Вернуть product

#### `get_by_id(product_id: UUID) -> ProductModel`

1. `product_repo.get_by_id(product_id)`
2. Если `None` → raise `ProductNotFound`
3. Вернуть product (любой статус — для internal endpoint)

#### `search(params: ProductListParams) -> ProductPage`

1. Маппить `ProductListParams` → `ProductSearchQuery`
2. По умолчанию для публичного поиска: если `params.status` не указан, фильтровать только `ACTIVE`
3. Вызвать `product_repo.search(query)`
4. Вернуть result

#### `update_product(product_id: UUID, data: UpdateProductRequest) -> ProductModel`

1. `product_repo.get_by_id(product_id)` → если None, raise `ProductNotFound`
2. Для каждого не-None поля в `data` — обновить атрибут на ORM-объекте
3. **Особая логика для `status`**: если новый статус `ACTIVE` и старый был не `ACTIVE` → установить `published_at = utc_now()`
4. Если `data.category_id` не None → проверить что категория существует, иначе `CategoryNotFound`
5. Если `data.images` не None → `product_repo.replace_images(product.id, new_images)`
6. `product.updated_at = utc_now()` (или через `onupdate` — он сработает при flush)
7. `product_repo.update(product)`
8. `session.commit()`
9. `session.refresh(product)`
10. Вернуть product

#### `archive_product(product_id: UUID) -> ProductModel`

1. `product_repo.get_by_id(product_id)` → если None, raise `ProductNotFound`
2. Установить `product.status = ProductStatus.ARCHIVED`
3. `product_repo.update(product)`
4. `session.commit()`
5. Вернуть product

### 8.3. `src/catalog/application/services/category.py` — `CategoryService`

**Конструктор:**

```python
def __init__(
    self,
    session: AsyncSession,
    category_repo: CategoryRepository,
) -> None:
```

**Методы:**

#### `create_category(data: CreateCategoryRequest) -> CategoryModel`

1. Если `data.parent_id` не None → `category_repo.get_by_id(data.parent_id)`, если None → raise `CategoryNotFound`
2. Проверить `category_repo.slug_exists(data.slug)` — если True → raise `DuplicateSlug`
3. Создать `CategoryModel(name=..., slug=..., parent_id=...)`
4. `category_repo.create(category)`
5. `session.commit()`
6. `session.refresh(category)`
7. Вернуть category

#### `get_category_tree() -> list[CategoryModel]`

1. `category_repo.list_all()` — возвращает корневые категории с children через selectinload
2. Вернуть result

#### `_build_tree_node(category: CategoryModel) -> CategoryTreeNode`

Рекурсивно преобразует ORM-объект в `CategoryTreeNode`. Используется в route-layer для формирования ответа.

---

## 9. API Layer

### 9.1. `src/catalog/api/dependencies.py`

Повторяет паттерн из [dependencies.py](file:///c:/Users/mickey/Desktop/flashmarket/auth/src/auth_service/api/dependencies.py) auth-сервиса:

```python
DbSession = Annotated[AsyncSession, Depends(get_db)]

def get_product_service(db: DbSession) -> ProductService:
    product_repo = ProductRepository(db)
    category_repo = CategoryRepository(db)
    return ProductService(session=db, product_repo=product_repo, category_repo=category_repo)

def get_category_service(db: DbSession) -> CategoryService:
    category_repo = CategoryRepository(db)
    return CategoryService(session=db, category_repo=category_repo)

ProductServiceDep = Annotated[ProductService, Depends(get_product_service)]
CategoryServiceDep = Annotated[CategoryService, Depends(get_category_service)]
```

### 9.2. `src/catalog/api/error_handlers.py`

Повторяет паттерн из [error_handlers.py](file:///c:/Users/mickey/Desktop/flashmarket/auth/src/auth_service/api/error_handlers.py) auth-сервиса:

```python
ERROR_STATUS: dict[type[CatalogError], int] = {
    ProductNotFound: status.HTTP_404_NOT_FOUND,
    CategoryNotFound: status.HTTP_404_NOT_FOUND,
    DuplicateSlug: status.HTTP_409_CONFLICT,
    InvalidProductData: status.HTTP_422_UNPROCESSABLE_ENTITY,
}
```

Единый обработчик `catalog_error_handler(request, exc: CatalogError) -> JSONResponse` — маппит exception в HTTP status code. Ответ в формате:

```json
{
  "error": {
    "code": "product_not_found",
    "message": "Product not found",
    "request_id": null
  }
}
```

`request_id` берётся из `request.state.request_id` (если есть).

### 9.3. Routes

Все роутеры используют `prefix="/api/v1"` на уровне включения в `app`, или каждый роутер имеет свой prefix.

**Общие ответы ошибок** (определить как dict для `responses` параметра):

```python
ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    404: {"model": ErrorResponse, "description": "Not Found"},
    409: {"model": ErrorResponse, "description": "Conflict"},
    422: {"model": ErrorResponse, "description": "Validation Error"},
}
```

#### 9.3.1. `src/catalog/api/routes/categories.py`

**Router:** `prefix="/api/v1/categories"`, `tags=["categories"]`

| Method | Path | Функция | Request Body | Response | Status | Описание |
|---|---|---|---|---|---|---|
| `POST` | `/` | `create_category` | `CreateCategoryRequest` | `CategoryResponse` | 201 | Создать категорию |
| `GET` | `/` | `list_categories` | — | `list[CategoryTreeNode]` | 200 | Дерево категорий |

**`create_category`:**
```python
async def create_category(
    data: CreateCategoryRequest,
    service: CategoryServiceDep,
) -> CategoryResponse:
```
- Вызывает `service.create_category(data)`
- Маппит ORM → `CategoryResponse`

**`list_categories`:**
```python
async def list_categories(
    service: CategoryServiceDep,
) -> list[CategoryTreeNode]:
```
- Вызывает `service.get_category_tree()`
- Рекурсивно маппит ORM → `CategoryTreeNode`

#### 9.3.2. `src/catalog/api/routes/products.py`

**Router:** `prefix="/api/v1/products"`, `tags=["products"]`

| Method | Path | Функция | Request | Response | Status | Описание |
|---|---|---|---|---|---|---|
| `POST` | `/` | `create_product` | `CreateProductRequest` | `ProductResponse` | 201 | Создать товар |
| `GET` | `/` | `list_products` | Query params (`ProductListParams`) | `ProductListResponse` | 200 | Список с фильтрами |
| `GET` | `/{slug}` | `get_product` | slug (path) | `ProductResponse` | 200 | Товар по slug (только ACTIVE) |
| `PATCH` | `/{product_id}` | `update_product` | `UpdateProductRequest` | `ProductResponse` | 200 | Обновить товар |
| `DELETE` | `/{product_id}` | `archive_product` | — | `ProductResponse` | 200 | Архивировать (soft delete) |

**`create_product`:**
```python
@router.post(
    "",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    responses=ERROR_RESPONSES,
    summary="Create a new product",
    description="Create a new product. Slug is generated automatically from the name.",
)
async def create_product(
    data: CreateProductRequest,
    service: ProductServiceDep,
) -> ProductResponse:
```

**`list_products`:**
```python
@router.get(
    "",
    response_model=ProductListResponse,
    responses=ERROR_RESPONSES,
    summary="List products with filtering, sorting and pagination",
)
async def list_products(
    params: Annotated[ProductListParams, Query()],
    service: ProductServiceDep,
) -> ProductListResponse:
```

> [!IMPORTANT]
> Публичный endpoint `/products` возвращает ТОЛЬКО товары со статусом `ACTIVE`. Если `params.status` не указан, service-слой по умолчанию фильтрует по `ACTIVE`.

**`get_product`:**
```python
@router.get(
    "/{slug}",
    response_model=ProductResponse,
    responses=ERROR_RESPONSES,
    summary="Get product by slug (public, ACTIVE only)",
)
async def get_product(
    slug: str,
    service: ProductServiceDep,
) -> ProductResponse:
```
- Возвращает 404 если товар `HIDDEN` или `ARCHIVED`

**`update_product`:**
```python
@router.patch(
    "/{product_id}",
    response_model=ProductResponse,
    responses=ERROR_RESPONSES,
    summary="Partially update a product",
)
async def update_product(
    product_id: uuid.UUID,
    data: UpdateProductRequest,
    service: ProductServiceDep,
) -> ProductResponse:
```

**`archive_product`:**
```python
@router.delete(
    "/{product_id}",
    response_model=ProductResponse,
    responses=ERROR_RESPONSES,
    summary="Archive a product (soft delete)",
    description="Sets the product status to ARCHIVED. The record is NOT deleted from the database.",
)
async def archive_product(
    product_id: uuid.UUID,
    service: ProductServiceDep,
) -> ProductResponse:
```

#### 9.3.3. `src/catalog/api/routes/internal.py`

**Router:** `prefix="/api/v1/internal"`, `tags=["internal"]`

| Method | Path | Функция | Response | Описание |
|---|---|---|---|---|
| `GET` | `/products/{product_id}` | `get_product_internal` | `ProductResponse` | Товар по UUID, любой статус |

```python
@router.get(
    "/products/{product_id}",
    response_model=ProductResponse,
    responses=ERROR_RESPONSES,
    summary="Get product by ID (internal, any status)",
    description="Internal endpoint for other services. Returns product regardless of status.",
)
async def get_product_internal(
    product_id: uuid.UUID,
    service: ProductServiceDep,
) -> ProductResponse:
```

#### 9.3.4. `src/catalog/api/routes/health.py`

**Router:** `prefix="/health"`, `tags=["health"]`

| Method | Path | Response |
|---|---|---|
| `GET` | `/ready` | `{"status": "ok"}` |

#### 9.3.5. Маппинг ORM → Response

Определить вспомогательную функцию (в `routes/products.py` или в отдельном модуле):

```python
def product_to_response(product: ProductModel) -> ProductResponse:
    return ProductResponse(
        id=product.id,
        slug=product.slug,
        name=product.name,
        description=product.description,
        price=product.price,
        currency=product.currency,
        status=product.status,
        category_id=product.category_id,
        category_name=product.category.name,
        cover_image=product.cover_image,
        images=[
            ImageResponse(id=img.id, url=img.url, sort_order=img.sort_order)
            for img in product.images
        ],
        created_at=product.created_at,
        updated_at=product.updated_at,
        published_at=product.published_at,
    )
```

---

## 10. Application Entry Point

### 10.1. `src/catalog/main.py`

Повторяет паттерн [main.py](file:///c:/Users/mickey/Desktop/flashmarket/auth/src/auth_service/main.py) auth-сервиса:

```python
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from catalog.api.error_handlers import catalog_error_handler
from catalog.api.routes import categories, health, internal, products
from catalog.config import get_settings
from catalog.domain.exceptions import CatalogError
from catalog.infrastructure.database import engine


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    yield
    await engine.dispose()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        debug=settings.debug,
        docs_url="/docs" if settings.docs_enabled else None,
        redoc_url="/redoc" if settings.docs_enabled else None,
        openapi_url="/openapi.json" if settings.docs_enabled else None,
        lifespan=lifespan,
    )
    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.trusted_hosts,
    )
    app.add_exception_handler(CatalogError, catalog_error_handler)
    app.include_router(health.router)
    app.include_router(categories.router)
    app.include_router(products.router)
    app.include_router(internal.router)
    return app


app = create_app()
```

### 10.2. `src/catalog/__init__.py`

Пустой или с `"""FlashMarket Catalog Service."""`.

---

## 11. Alembic

### 11.1. `alembic.ini`

```ini
[alembic]
script_location = %(here)s/migrations
prepend_sys_path = %(here)s/src
path_separator = os

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

### 11.2. `migrations/env.py`

Полностью повторяет [env.py](file:///c:/Users/mickey/Desktop/flashmarket/auth/migrations/env.py) из auth, с заменой import-путей:

```python
from catalog.infrastructure import models  # noqa: F401
from catalog.config import get_settings
from catalog.infrastructure.database import Base
```

### 11.3. `migrations/script.py.mako`

Стандартный шаблон Alembic.

### 11.4. Начальная миграция

Файл: `migrations/versions/0001_initial.py`

Создаётся через `alembic revision --autogenerate -m "initial"` после настройки всех моделей.

Должна создать три таблицы:
1. `categories`
2. `products`
3. `product_images`

Со всеми индексами, FK и constraints из раздела 7.

---

## 12. Docker

### 12.1. `Dockerfile`

```dockerfile
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
RUN uv sync --frozen --no-dev

USER app

EXPOSE 8000

CMD [".venv/bin/uvicorn", "catalog.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
```

### 12.2. `docker-compose.yml`

```yaml
name: flashmarket-catalog

x-catalog-runtime: &catalog-runtime
  image: flashmarket-catalog-api:local
  pull_policy: never

x-catalog-environment: &catalog-environment
  CATALOG_ENVIRONMENT: development
  CATALOG_DATABASE_URL: postgresql+asyncpg://flashmarket:flashmarket@db:5432/catalog
  CATALOG_CORS_ORIGINS: '["http://localhost:3000"]'

services:
  migrate:
    <<: *catalog-runtime
    environment:
      CATALOG_ENVIRONMENT: development
      CATALOG_DATABASE_URL: postgresql+asyncpg://flashmarket:flashmarket@db:5432/catalog
    command: [".venv/bin/alembic", "upgrade", "head"]
    depends_on:
      db:
        condition: service_healthy
    restart: "no"

  api:
    <<: *catalog-runtime
    build:
      context: .
    environment: *catalog-environment
    ports:
      - "127.0.0.1:${CATALOG_PORT:-8010}:8000"
    depends_on:
      migrate:
        condition: service_completed_successfully
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

  db:
    image: postgres:17-alpine
    environment:
      POSTGRES_DB: catalog
      POSTGRES_USER: flashmarket
      POSTGRES_PASSWORD: flashmarket
    ports:
      - "127.0.0.1:${CATALOG_DB_PORT:-5433}:5432"
    volumes:
      - catalog-postgres-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U flashmarket -d catalog"]
      interval: 5s
      timeout: 3s
      retries: 10
    restart: unless-stopped

volumes:
  catalog-postgres-data:
```

> [!NOTE]
> Порт API: **8010** (auth на 8000). Порт PostgreSQL: **5433** (auth на 5432).

### 12.3. `.dockerignore`

```
.venv/
__pycache__/
.pytest_cache/
.ruff_cache/
.mypy_cache/
.env
.git/
```

### 12.4. `.gitignore`

```
.env
.pytest_cache/
.ruff_cache/
.mypy_cache/
.venv/
__pycache__/
*.py[cod]
.coverage
htmlcov/
dist/
```

---

## 13. Тесты

### 13.1. `tests/conftest.py`

Повторяет паттерн [conftest.py](file:///c:/Users/mickey/Desktop/flashmarket/auth/tests/conftest.py) из auth:

```python
import os
from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

os.environ.setdefault("CATALOG_ENVIRONMENT", "test")

from catalog.infrastructure.database import Base, get_db  # noqa: E402
from catalog.main import app  # noqa: E402


@pytest.fixture
async def session_factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    test_engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
    )
    async with test_engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(test_engine, expire_on_commit=False)

    async def override_get_db() -> AsyncIterator[AsyncSession]:
        async with factory() as session:
            try:
                yield session
            finally:
                await session.rollback()

    app.dependency_overrides[get_db] = override_get_db
    yield factory
    app.dependency_overrides.clear()
    await test_engine.dispose()


@pytest.fixture
async def client(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncClient]:
    del session_factory
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client
```

> [!WARNING]
> SQLite не поддерживает `Numeric` с precision нативно. В тестах `Decimal` будет храниться как `REAL`. Для тестов точности `Decimal` при необходимости использовать mock или фикстуры. Основной функционал работает корректно с in-memory SQLite.

### 13.2. Тест-файлы и кейсы

#### `tests/test_slug.py` — Генерация slug

| Тест | Описание |
|---|---|
| `test_slug_basic_generation` | `"iPhone 17 Pro"` → `"iphone-17-pro"` |
| `test_slug_special_characters` | `"Café & Résumé!"` → `"cafe-resume"` (или подобное) |
| `test_slug_cyrillic` | `"Кроссовки Nike Air"` → `"krossovki-nike-air"` (транслитерация) |
| `test_slug_uniqueness_suffix` | Создать товар `"Test"` → `"test"`, создать ещё `"Test"` → `"test-2"` |
| `test_slug_uniqueness_chain` | Создать 3 товара с одинаковым названием → slug-и: `"test"`, `"test-2"`, `"test-3"` |
| `test_slug_format_validation` | Проверить что slug содержит только `a-z`, `0-9`, `-` |

#### `tests/test_product_service.py` — Бизнес-логика товаров

| Тест | Описание |
|---|---|
| `test_create_product` | Создание товара с корректными данными, проверка всех полей |
| `test_create_product_invalid_category` | Несуществующий `category_id` → `CategoryNotFound` |
| `test_create_product_sets_published_at` | Создание со статусом `ACTIVE` → `published_at` заполнен |
| `test_create_product_hidden_no_published` | Создание со статусом `HIDDEN` → `published_at is None` |
| `test_get_product_active` | Получение `ACTIVE` товара по slug → успех |
| `test_get_product_hidden_404` | Получение `HIDDEN` товара по slug → `ProductNotFound` |
| `test_get_product_archived_404` | Получение `ARCHIVED` товара по slug → `ProductNotFound` |
| `test_archive_product` | Архивация → `status == ARCHIVED` |
| `test_archive_nonexistent` | Архивация несуществующего → `ProductNotFound` |
| `test_update_product_partial` | PATCH только `name` → name изменился, slug не изменился |
| `test_update_product_status_sets_published` | Смена `HIDDEN → ACTIVE` → `published_at` заполнился |
| `test_price_must_be_positive` | `price <= 0` → ошибка валидации Pydantic |

#### `tests/test_category_service.py` — Бизнес-логика категорий

| Тест | Описание |
|---|---|
| `test_create_category` | Создание категории, проверка полей |
| `test_create_category_duplicate_slug` | Дублирующий slug → `DuplicateSlug` |
| `test_create_subcategory` | Создание с `parent_id` → parent существует |
| `test_create_subcategory_invalid_parent` | Несуществующий `parent_id` → `CategoryNotFound` |
| `test_category_tree` | Создать `Electronics` → `Phones`, `Tablets`; `Furniture`. Проверить дерево: 2 корня, `Electronics` имеет 2 children |

#### `tests/test_products_api.py` — HTTP-тесты товаров

| Тест | Описание |
|---|---|
| `test_create_product_201` | `POST /api/v1/products` → 201 + корректный JSON |
| `test_create_product_invalid_422` | Невалидные данные → 422 |
| `test_get_product_by_slug_200` | `GET /api/v1/products/{slug}` ACTIVE товар → 200 |
| `test_get_product_hidden_404` | `GET /api/v1/products/{slug}` HIDDEN → 404 |
| `test_list_products_pagination` | Создать 5 товаров, запросить `limit=2, offset=0` → 2 items, total=5 |
| `test_list_products_filter_category` | Фильтр по `category_id` |
| `test_list_products_filter_price_range` | Фильтр `price_from=100, price_to=500` |
| `test_list_products_search` | `search=iphone` → ILIKE по name/description |
| `test_list_products_sort_price_asc` | `sort_by=price, sort_order=asc` |
| `test_list_products_sort_name` | `sort_by=name` |
| `test_update_product_200` | `PATCH /api/v1/products/{id}` → 200 + обновлённые поля |
| `test_archive_product_200` | `DELETE /api/v1/products/{id}` → 200 + `status=ARCHIVED` |
| `test_internal_get_any_status` | `GET /api/v1/internal/products/{id}` для HIDDEN → 200 |

#### `tests/test_categories_api.py` — HTTP-тесты категорий

| Тест | Описание |
|---|---|
| `test_create_category_201` | `POST /api/v1/categories` → 201 |
| `test_get_category_tree_200` | `GET /api/v1/categories` → дерево |
| `test_create_duplicate_slug_409` | Дублирующий slug → 409 |

### 13.3. Паттерн тестов

Каждый тест:
1. Использует фикстуру `client: AsyncClient`
2. Через HTTP-запросы создаёт prerequisite data (категорию перед товаром)
3. Делает целевой запрос
4. Ассертит `response.status_code` и `response.json()`

Не использовать моки. Использовать реальную in-memory SQLite через SQLAlchemy.

---

## 14. Контракт ответов API (примеры)

### Создание категории

**Request:**
```http
POST /api/v1/categories
Content-Type: application/json

{
  "name": "Electronics",
  "slug": "electronics",
  "parent_id": null
}
```

**Response 201:**
```json
{
  "id": "01926c1a-...",
  "name": "Electronics",
  "slug": "electronics",
  "parent_id": null,
  "created_at": "2026-07-29T12:00:00Z"
}
```

### Дерево категорий

**Response 200:**
```json
[
  {
    "id": "...",
    "name": "Electronics",
    "slug": "electronics",
    "children": [
      {
        "id": "...",
        "name": "Phones",
        "slug": "phones",
        "children": []
      },
      {
        "id": "...",
        "name": "Tablets",
        "slug": "tablets",
        "children": []
      }
    ]
  },
  {
    "id": "...",
    "name": "Furniture",
    "slug": "furniture",
    "children": []
  }
]
```

### Создание товара

**Request:**
```http
POST /api/v1/products
Content-Type: application/json

{
  "name": "iPhone 17 Pro",
  "description": "Latest Apple smartphone",
  "price": "129990.00",
  "currency": "RUB",
  "category_id": "01926c1a-...",
  "cover_image": "https://cdn.example.com/iphone17.jpg",
  "images": [
    {"url": "https://cdn.example.com/iphone17-1.jpg", "sort_order": 0},
    {"url": "https://cdn.example.com/iphone17-2.jpg", "sort_order": 1}
  ],
  "status": "ACTIVE"
}
```

**Response 201:**
```json
{
  "id": "01926c1b-...",
  "slug": "iphone-17-pro",
  "name": "iPhone 17 Pro",
  "description": "Latest Apple smartphone",
  "price": "129990.00",
  "currency": "RUB",
  "status": "ACTIVE",
  "category_id": "01926c1a-...",
  "category_name": "Electronics",
  "cover_image": "https://cdn.example.com/iphone17.jpg",
  "images": [
    {"id": "...", "url": "https://cdn.example.com/iphone17-1.jpg", "sort_order": 0},
    {"id": "...", "url": "https://cdn.example.com/iphone17-2.jpg", "sort_order": 1}
  ],
  "created_at": "2026-07-29T12:00:00Z",
  "updated_at": "2026-07-29T12:00:00Z",
  "published_at": "2026-07-29T12:00:00Z"
}
```

### Список товаров

**Request:**
```http
GET /api/v1/products?limit=20&offset=0&search=iphone&sort_by=price&sort_order=asc
```

**Response 200:**
```json
{
  "items": [...],
  "total": 42,
  "limit": 20,
  "offset": 0
}
```

### Ошибка

**Response 404:**
```json
{
  "error": {
    "code": "product_not_found",
    "message": "Product not found",
    "request_id": null
  }
}
```

---

## 15. Порядок реализации

> [!TIP]
> Рекомендуемый порядок — снизу вверх (infrastructure → domain → application → api → tests).

| Шаг | Что делать |
|---|---|
| 1 | Инициализировать проект: `pyproject.toml`, `.python-version`, `.gitignore`, `.env.example`, `README.md` |
| 2 | `uv sync` — установить зависимости |
| 3 | `src/catalog/config.py` |
| 4 | `src/catalog/domain/entities.py` (enums) |
| 5 | `src/catalog/domain/exceptions.py` |
| 6 | `src/catalog/infrastructure/database.py` (engine, Base, get_db) |
| 7 | `src/catalog/infrastructure/models.py` (CategoryModel, ProductModel, ProductImageModel) |
| 8 | `alembic.ini` + `migrations/env.py` + `alembic revision --autogenerate` |
| 9 | `src/catalog/infrastructure/repositories/category.py` |
| 10 | `src/catalog/infrastructure/repositories/product.py` |
| 11 | `src/catalog/application/schemas.py` |
| 12 | `src/catalog/application/services/category.py` |
| 13 | `src/catalog/application/services/product.py` |
| 14 | `src/catalog/api/error_handlers.py` |
| 15 | `src/catalog/api/dependencies.py` |
| 16 | `src/catalog/api/routes/health.py` |
| 17 | `src/catalog/api/routes/categories.py` |
| 18 | `src/catalog/api/routes/products.py` |
| 19 | `src/catalog/api/routes/internal.py` |
| 20 | `src/catalog/main.py` |
| 21 | `tests/conftest.py` |
| 22 | Все тест-файлы |
| 23 | `Dockerfile` + `docker-compose.yml` |
| 24 | Прогнать `ruff check`, `ruff format`, `mypy`, `pytest` |

---

## 16. Чеклист качества

- [ ] `ruff check src/ tests/` — 0 ошибок
- [ ] `ruff format --check src/ tests/` — 0 ошибок
- [ ] `mypy` — 0 ошибок (strict mode)
- [ ] `pytest` — все тесты зелёные
- [ ] Нет `TODO`, `FIXME`, `XXX`, `HACK` в коде
- [ ] Нет `SELECT *` — только нужные поля или ORM-объекты с явными `options()`
- [ ] Нет N+1 — все relationships загружаются через `selectinload`/`joinedload`
- [ ] Нет raw SQL — только SQLAlchemy ORM
- [ ] Все запросы параметризованы (ORM гарантирует это)
- [ ] `price` — `Decimal`, не `float`
- [ ] Каждый endpoint имеет `response_model`, `summary`, `responses`
- [ ] Все типы аннотированы — `-> ReturnType`, параметры с типами
- [ ] Domain exceptions имеют `code` и `message`
- [ ] Slug — только `[a-z0-9-]`
- [ ] Уникальность slug гарантирована на уровне БД (UNIQUE) + сервиса (check)
- [ ] `DELETE` не удаляет запись, а меняет `status = ARCHIVED`
- [ ] Публичный `GET /products/{slug}` возвращает только `ACTIVE`
- [ ] Internal `GET /internal/products/{id}` возвращает любой статус
- [ ] Дерево категорий отдаётся рекурсивно

---

## 17. Что НЕ входит в scope

- Аутентификация/авторизация (это ответственность API Gateway + Auth Service)
- Остатки (Inventory Service)
- Заказы (Order Service)
- Загрузка файлов/изображений (отдельный Upload Service или CDN)
- Кэширование (Redis — можно добавить позже)
- Rate limiting (можно добавить позже)
- Observability/Prometheus метрики (можно добавить позже)
- Event publishing (outbox — можно добавить позже)
