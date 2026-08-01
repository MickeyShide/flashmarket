# FlashMarket — Полное описание проекта

> Платформа лимитированных дропов (flash-sale) с микросервисной архитектурой.
> Домен продакшена: `FlashMarket.shide.world`

---

## 1. Обзор

FlashMarket — e-commerce платформа для продажи лимитированных коллекций одежды, обуви и аксессуаров в формате flash-sale. Ядро проекта — 6 backend-микросервисов, Nginx API Gateway, SPA-фронтенд и общая инфраструктура (PostgreSQL, Redis, RabbitMQ).

Ключевые характеристики:

- **Микросервисная архитектура** — каждый сервис владеет своей базой данных и не лезет в чужую;
- **Event-driven взаимодействие** — transactional outbox + RabbitMQ для межсервисных событий;
- **Choreography-based saga** — покупка проходит через reserve → order → payment → confirm → notify;
- **Production-ready** — CI/CD на GitHub Actions, SSH deploy, Docker Compose на сервере;
- **Security-first** — Ed25519 JWT, Argon2id, rate limiting, CSRF, session introspection.

---

## 2. Архитектура

```
┌─────────────────────────────────────────────────────────────────┐
│                      NGINX API Gateway                          │
│                     (drop.shide.world)                          │
│  /api/v1/auth/*  → Auth         /api/v1/stocks/*    → Inventory │
│  /api/v1/products/* → Catalog   /api/v1/orders/*    → Orders    │
│  /api/v1/payments/*  → Payments /api/v1/notifications/* → Notif │
│  /*  → Frontend                                                 │
└─────────────┬───────────────────────────────────────────────────┘
              │
   ┌──────────┼──────────────────────────────────────────┐
   │          │          Docker Network                   │
   │  ┌───────┴───────┐                                  │
   │  │   Frontend    │  React + Vite + TailwindCSS      │
   │  │   (SPA)       │  port 3000                       │
   │  └───────────────┘                                  │
   │                                                     │
   │  ┌─────────┐ ┌─────────┐ ┌───────────┐ ┌─────────┐│
   │  │  Auth   │ │ Catalog │ │ Inventory │ │ Orders  ││
   │  │ :8000   │ │ :8000   │ │  :8000    │ │  :8000  ││
   │  └────┬────┘ └────┬────┘ └─────┬─────┘ └────┬────┘│
   │       │           │            │             │      │
   │  ┌────┴────┐ ┌────┴────┐ ┌────┴────┐ ┌─────┴────┐│
   │  │Payments │ │ Notif.  │ │  Redis  │ │ RabbitMQ ││
   │  │ :8000   │ │ :8000   │ │ :6379   │ │ :5672    ││
   │  └─────────┘ └─────────┘ └─────────┘ └──────────┘│
   │                                                     │
   │  ┌─────────────────────────────────────────────────┐│
   │  │               PostgreSQL 17                      ││
   │  │  databases: auth, catalog, inventory,            ││
   │  │             orders, payments, notifications      ││
   │  └─────────────────────────────────────────────────┘│
   └─────────────────────────────────────────────────────┘
```

### Сеть

Все сервисы работают в единой Docker network `shide-observability`. Gateway слушает порт 8080 (или настраиваемый `GATEWAY_PORT`) и маршрутизирует трафик по path prefix. Также поддерживается subdomain-роутинг (`auth.GATEWAY_DOMAIN`, `catalog.GATEWAY_DOMAIN` и т.д.).

---

## 3. Технологический стек

### Backend (все микросервисы)

| Технология | Версия | Назначение |
|---|---|---|
| Python | ≥ 3.14 (CPython) | Runtime |
| FastAPI | ≥ 0.140 | Web framework |
| SQLAlchemy 2 | async, asyncpg | ORM |
| PostgreSQL | 17 | Основная СУБД |
| Alembic | ≥ 1.18 | Миграции |
| Pydantic v2 | — | Валидация и схемы |
| pydantic-settings | ≥ 2.14 | Конфигурация из ENV |
| Redis | — | Сессии, rate limiting, кеш |
| RabbitMQ | — | Event bus (AMQP 0-9-1) |
| uv | latest | Package manager |
| ruff | ≥ 0.16 | Linter + formatter |
| mypy | strict | Static type checking |
| pytest | ≥ 9.1 | Тесты |
| Docker | — | Контейнеризация |
| Uvicorn | ≥ 0.51 | ASGI server |

### Frontend

| Технология | Версия | Назначение |
|---|---|---|
| React | ^18.2.0 | UI framework |
| Vite | ^5.2.0 | Build tool / dev server |
| TailwindCSS | ^3.4.3 | CSS utility framework |

### Infrastructure

| Компонент | Образ | Назначение |
|---|---|---|
| API Gateway | `nginx:1.30-alpine` | Reverse proxy, маршрутизация |
| PostgreSQL | `postgres:17-alpine` | Per-service databases |
| Redis | `redis:7-alpine` | Sessions, rate limiting |
| RabbitMQ | `rabbitmq:4-management-alpine` | Message broker |
| Prometheus | external `shide-prometheus` | Метрики |
| Grafana | external | Дашборды |

---

## 4. Микросервисы

### 4.1. Auth Service

**Путь:** `auth/` · **Порт:** 8000 · **БД:** `auth`

Независимый Identity-микросервис. Владеет пользователями, сессиями, refresh-токенами и security audit.

**Возможности:**
- Регистрация, login/logout, профиль и смена пароля
- Роли `CUSTOMER` и `ADMIN`, деактивация аккаунтов
- Argon2id-хэширование паролей
- Access JWT с Ed25519/EdDSA, key ring, `kid` и публичный JWKS
- Ротация refresh-токенов и детектирование повторного использования
- Browser-режим `HttpOnly` cookie + double-submit CSRF
- Distributed rate limiting через Redis (20 IP / 5 аккаунт за 60с)
- Активные сессии в Redis с немедленным отзывом и introspection
- Domain events и transactional outbox → RabbitMQ
- UUIDv7 для идентификаторов
- Security audit, request ID, JSON-логи и Prometheus-метрики
- Alembic-миграции, cleanup истёкших данных

**API эндпоинты:**

| Метод | Путь | Доступ | Назначение |
|---|---|---|---|
| `POST` | `/auth/register` | публичный | Регистрация |
| `POST` | `/auth/login` | публичный | Вход |
| `POST` | `/auth/refresh` | refresh + CSRF | Ротация refresh |
| `POST` | `/auth/introspect` | access token | Introspection |
| `POST` | `/auth/logout` | access token | Выход |
| `GET` | `/users/me` | access token | Профиль |
| `PATCH` | `/users/me` | access token | Изменить профиль |
| `POST` | `/users/me/password` | access token | Сменить пароль |
| `GET/DELETE` | `/sessions` | access token | Управление сессиями |
| `GET/PATCH` | `/admin/users/*` | ADMIN | Управление пользователями |
| `GET` | `/admin/audit-events` | ADMIN | Security audit |
| `GET` | `/.well-known/jwks.json` | публичный | JWKS |
| `GET` | `/health/live`, `/health/ready` | публичный | Health checks |
| `GET` | `/metrics` | инфраструктура | Prometheus |

**Архитектура:**

```
auth/src/auth_service/
├── api/                     # HTTP контроллеры
├── application/
│   ├── auth.py              # register/login/refresh/logout
│   ├── users.py             # профиль и пароль
│   ├── sessions.py          # управление сессиями
│   ├── admin.py             # роли, статусы, audit
│   └── contracts.py         # интерфейсы: UoW, Repositories, SessionStore
├── domain/                  # доменные события
├── infrastructure/
│   ├── persistence/         # SQLAlchemy repositories и UoW
│   └── redis_session_store.py
├── key_management.py        # Ed25519 key ring
├── outbox_worker.py         # transactional outbox publisher
├── rate_limit.py            # distributed rate limiting
└── observability.py         # Prometheus + JSON logging
```

**Events (outbox → RabbitMQ):** `user_registered`, `user_logged_in`, `token_refreshed`, `user_logged_out`, `profile_updated`, `password_changed`, `user_role_changed`, `user_status_changed`, `session_revoked`, `all_sessions_revoked`

**Exchange:** `flashmarket.events` (topic, durable) · **Routing key:** `identity.<event_type>`

**Docker Compose процессы:** `api`, `outbox`, `cleanup`

---

### 4.2. Catalog Service

**Путь:** `catalog/` · **Порт:** 8010 (хост 8010) · **БД:** `catalog`

Каталог товаров и категорий. Не знает о пользователях, корзинах, заказах или остатках.

**Возможности:**
- CRUD товаров с автогенерацией slug (python-slugify, транслитерация)
- Иерархическое дерево категорий (parent → children, selectinload)
- Галерея изображений с сортировкой
- Фильтрация по категории, цене, статусу; полнотекстовый поиск (ILIKE)
- Сортировка по цене, имени, дате создания
- Пагинация `limit`/`offset`
- Soft delete (ARCHIVED) — публичный API возвращает только ACTIVE
- Internal endpoint для межсервисного доступа к товарам любого статуса
- Бренды

**API эндпоинты:**

| Метод | Путь | Назначение |
|---|---|---|
| `POST` | `/api/v1/categories` | Создать категорию |
| `GET` | `/api/v1/categories` | Дерево категорий |
| `POST` | `/api/v1/products` | Создать товар |
| `GET` | `/api/v1/products` | Список с фильтрами |
| `GET` | `/api/v1/products/{slug}` | Товар по slug (только ACTIVE) |
| `PATCH` | `/api/v1/products/{product_id}` | Обновить товар |
| `DELETE` | `/api/v1/products/{product_id}` | Архивировать (soft delete) |
| `GET` | `/api/v1/internal/products/{id}` | Internal — любой статус |
| `GET/POST` | `/api/v1/brands` | Бренды |
| `GET` | `/health/ready` | Readiness |

**Доменные модели:** `ProductStatus` (ACTIVE, HIDDEN, ARCHIVED), `Currency` (RUB, USD, EUR)

**ORM:** `CategoryModel`, `ProductModel` (Numeric(12,2) для price), `ProductImageModel`

---

### 4.3. Inventory Service

**Путь:** `inventory/` · **Порт:** 8011 (хост) · **БД:** `inventory`

Управление стоковыми остатками и flash-sale резервациями.

**Доменные гарантии:**
- `available >= 0`
- `reserved + sold <= total`
- Нет overselling при конкурентной нагрузке (pessimistic row locking)
- Автоматическая экспирация резерваций по `INVENTORY_RESERVATION_TTL_SECONDS`

**API эндпоинты:**

| Метод | Путь | Назначение |
|---|---|---|
| `POST` | `/api/v1/stocks` | Создать/сбросить сток |
| `GET` | `/api/v1/stocks/{product_id}` | Текущий сток |
| `PATCH` | `/api/v1/stocks/{product_id}` | Обновить total |
| `POST` | `/api/v1/stocks/{product_id}/reserve` | Зарезервировать |
| `POST` | `/api/v1/stocks/{product_id}/commit` | Подтвердить продажу |
| `POST` | `/api/v1/stocks/{product_id}/release` | Освободить резерв |
| `POST` | `/internal/expire` | Экспирация резерваций (worker) |
| `GET` | `/health/ready` | Readiness |

**Events:** `InventoryReserved`, `InventoryCommitted`, `ReservationReleased`

**Docker Compose процессы:** `api`, `consumer`, `outbox`

---

### 4.4. Orders Service

**Путь:** `orders/` · **Порт:** 8012 (хост) · **БД:** `orders`

Жизненный цикл заказа и оркестрация saga.

**Состояния заказа:** `PENDING` → `AWAITING_PAYMENT` → `PAID` → `CONFIRMED` / `PAYMENT_FAILED` → `CANCELLED`

**API эндпоинты:**

| Метод | Путь | Назначение |
|---|---|---|
| `POST` | `/api/v1/orders` | Создать заказ из резервации |
| `GET` | `/api/v1/orders/{order_id}` | Получить заказ |
| `GET` | `/api/v1/orders?user_id=...` | Список заказов пользователя |
| `POST` | `/api/v1/orders/{id}/confirm` | Подтвердить оплату |
| `POST` | `/api/v1/orders/{id}/fail` | Отклонить оплату |
| `GET` | `/health/ready` | Readiness |

**Events:** `OrderCreated`, `PaymentRequested`, `OrderConfirmed`, `OrderCancelled`

**Docker Compose процессы:** `api`, `consumer`, `outbox`

---

### 4.5. Payments Service

**Путь:** `payments/` · **Порт:** 8014 (хост) · **БД:** `payments`

Управление платёжными попытками.

**Состояния платежа:** `PENDING` → `SUCCESS` / `FAILED` / `CANCELLED`

**API эндпоинты:**

| Метод | Путь | Назначение |
|---|---|---|
| `POST` | `/api/v1/payments` | Создать платёж |
| `GET` | `/api/v1/payments/{payment_id}` | Получить платёж |
| `GET` | `/api/v1/payments/users/{user_id}` | Платежи пользователя |
| `POST` | `/api/v1/payments/{id}/confirm` | Подтвердить |
| `POST` | `/api/v1/payments/{id}/fail` | Отклонить |
| `POST` | `/api/v1/payments/{id}/cancel` | Отменить |
| `GET` | `/health/ready` | Readiness |

**Events:** `PaymentSucceeded`, `PaymentFailed`, `PaymentCancelled`

**Docker Compose процессы:** `api`, `consumer`, `outbox`

---

### 4.6. Notifications Service

**Путь:** `notifications/` · **Порт:** 8016 (хост) · **БД:** `notifications`

Персистенция уведомлений и доставка.

**Состояния:** `PENDING` → `SENT` / `FAILED`

**API эндпоинты:**

| Метод | Путь | Назначение |
|---|---|---|
| `POST` | `/api/v1/notifications` | Создать уведомление |
| `GET` | `/api/v1/notifications/{id}` | Получить уведомление |
| `GET` | `/api/v1/notifications/users/{user_id}` | Уведомления пользователя |
| `POST` | `/api/v1/notifications/{id}/send` | Отметить отправленным |
| `POST` | `/api/v1/notifications/{id}/fail` | Отметить ошибкой |
| `GET` | `/health/ready` | Readiness |

**Events:** `NotificationSent`

**Docker Compose процессы:** `api`, `consumer`, `outbox`

---

## 5. Frontend

**Путь:** `frontend/` · **Порт:** 3000

React SPA на Vite с TailwindCSS.

**Стек:** React 18, Vite 5, TailwindCSS 3.4

**Структура компонентов:**

```
frontend/src/
├── App.jsx            # главный роутинг
├── main.jsx           # entry point
├── index.css          # стили (Tailwind)
├── components/
│   ├── Cart/          # корзина
│   ├── Catalog/       # каталог
│   ├── Checkout/      # оформление
│   ├── Layout/        # общий макет
│   ├── Order/         # заказы
│   ├── Product/       # детальная страница товара
│   └── Profile/       # профиль пользователя
├── config/            # конфигурация
├── context/           # React context (состояние)
├── services/          # API-клиенты
└── utils/             # утилиты (форматирование и т.д.)
```

**Dev server:** проксирует `/api/*`, `/auth/*`, `/users/*`, `/sessions/*` на backend.

**Production:** собирается Vite → `dist/`, раздаётся Nginx.

---

## 6. API Gateway

**Путь:** `gateway/` · **Образ:** `nginx:1.30-alpine`

Nginx reverse proxy с двумя режимами маршрутизации:

### Path-based routing (основной)

| Путь | Backend |
|---|---|
| `/api/v1/auth/*`, `/api/v1/users/*`, `/api/v1/sessions/*`, `/api/v1/admin/*` | Auth |
| `/auth/*`, `/users/*`, `/sessions/*`, `/admin/*`, `/.well-known/*` | Auth (legacy) |
| `/api/v1/products/*`, `/api/v1/categories/*`, `/api/v1/brands/*`, `/api/v1/internal/*` | Catalog |
| `/api/v1/stocks/*`, `/internal/*` | Inventory |
| `/api/v1/orders/*` | Orders |
| `/api/v1/payments/*` | Payments |
| `/api/v1/notifications/*` | Notifications |
| `/prometheus/*` | Prometheus |
| `/*` (fallback) | Frontend |

### Subdomain routing

Каждый сервис доступен через `<service>.GATEWAY_DOMAIN` (например, `auth.drop.shide.world`).

### Конфигурация

- `client_max_body_size 16k`
- Docker internal DNS resolver (`127.0.0.11`)
- `X-Real-IP`, `X-Forwarded-For`, `X-Forwarded-Proto` проброс
- Timeouts: connect 5s, read/send 30s
- Health endpoint: `/health` → `200 "ok"`
- `nginx_status` доступен только из внутренней сети

---

## 7. Event-Driven Architecture

### Transactional Outbox Pattern

Каждый сервис (Auth, Inventory, Orders, Payments, Notifications) реализует transactional outbox:

1. Изменение данных и запись `outbox_events` коммитятся одним `Unit of Work`
2. Отдельный outbox worker читает записи через `FOR UPDATE SKIP LOCKED`
3. Публикует persistent-сообщение в RabbitMQ с publisher confirm
4. Только после подтверждения отмечает событие отправленным
5. Ошибки получают exponential backoff
6. Гарантия доставки — **at least once**, потребитель дедуплицирует по `event_id`

### Exchange

- **Name:** `flashmarket.events`
- **Type:** `topic`, durable
- **Routing keys:** `identity.*`, `inventory.*`, `orders.*`, `payments.*`, `notifications.*`

### Choreography-based Purchase Saga

```
User → Reserve Stock → Create Order → Payment Created → Payment Confirmed
                         │                                      │
                         │   ┌──────────────────────────────────┘
                         │   │
                         ▼   ▼
                    Order CONFIRMED → Inventory COMMITTED → Notification SENT

Payment Failed → Order CANCELLED → Inventory RELEASED → Notification SENT
```

**Полный flow (happy path):**

1. `POST /stocks/{id}/reserve` → Inventory резервирует, emit `InventoryReserved`
2. `POST /orders` → Orders создаёт заказ `AWAITING_PAYMENT`, emit `OrderCreated` + `PaymentRequested`
3. Payments consumer получает `PaymentRequested`, создаёт `PENDING` платёж
4. `POST /payments/{id}/confirm` → Payments emit `PaymentSucceeded`
5. Orders consumer получает `PaymentSucceeded`, переводит заказ в `CONFIRMED`, emit `OrderConfirmed`
6. Inventory consumer получает `OrderConfirmed`, коммитит сток
7. Notifications consumer получает `OrderConfirmed`, создаёт уведомление

**Failure path:** `PaymentFailed` → Orders `CANCELLED` → Inventory releases stock → Notification

---

## 8. Инфраструктура

### Docker Compose

Проект имеет несколько уровней Compose-файлов:

| Файл | Назначение |
|---|---|
| `docker-compose.yml` (root) | Объединяет все сервисы через `extends` |
| `<service>/docker-compose.yml` | Standalone запуск сервиса |
| `<service>/docker-compose.deploy.yml` | Production deploy |
| `docker-compose.prod.yml` | Production gateway + frontend |

**Корневой docker-compose.yml** объединяет все сервисы:
- Auth: `auth`, `auth-outbox`, `auth-cleanup`
- Catalog: `catalog`
- Inventory: `inventory`, `inventory-consumer`, `inventory-outbox`
- Orders: `orders`, `orders-consumer`, `orders-outbox`
- Payments: `payments`, `payments-consumer`, `payments-outbox`
- Notifications: `notifications`, `notifications-consumer`, `notifications-outbox`
- Media: `media`, `media-cleanup` (uses the existing MinIO/S3 in `shide-observability`)
- Gateway: `gateway`
- Frontend: `frontend`

### PostgreSQL

Единый PostgreSQL инстанс с отдельными базами для каждого сервиса:

| Сервис | Database | Host port |
|---|---|---|
| Auth | `auth` | 5432 |
| Catalog | `catalog` | 5433 |
| Inventory | `inventory` | 5434 |
| Orders | `orders` | 5435 |
| Payments | `payments` | 5436 |
| Notifications | `notifications` | 5437 |
| Media | `media` | shared PostgreSQL |

### Init-Infra Script

`docker/init-infra.py` — запускается при старте каждого API сервиса:
- Создаёт базу данных если не существует (через `asyncpg`)
- Создаёт RabbitMQ vhost и устанавливает permissions (через Management API)
- Retry с exponential backoff (30 попыток, 2с пауза)
- Поддерживает IPv4 fallback для DNS resolution

### Entrypoint

`docker/entrypoint.sh` — универсальный entrypoint для всех backend-сервисов:
- `api` → init-infra → alembic migrate → uvicorn
- `consumer` → запуск event consumer
- `outbox` → запуск outbox worker
- `cleanup` → запуск cleanup worker
- `migrate` → init-infra → alembic migrate
- Подготовка `PROMETHEUS_MULTIPROC_DIR` для multiprocess метрик

### Seed Data

`seed.py` — скрипт наполнения тестовыми данными через API:
- 5 категорий (Верхняя одежда, Худи, Сумки, Аксессуары, Обувь)
- 4 бренда (Marcelo Miracles, Flash Sect, Routine, Flash Market)
- 8 товаров с ценами 3500–24900 ₽
- Стоковые записи (от 0 до 100 единиц)
- Тестовый пользователь (`test@flashmarket.ru / TestPassword123!`)
- 2 тестовых заказа (один ожидает оплату, один подтверждён)
- 3 уведомления (EMAIL, PUSH)

---

## 9. CI/CD

Каждый сервис имеет свой GitHub Actions workflow:

| Workflow | Файл |
|---|---|
| Auth | `.github/workflows/auth-deploy.yml` |
| Catalog | `.github/workflows/catalog-deploy.yml` |
| Gateway | `.github/workflows/gateway-deploy.yml` |
| Inventory | `.github/workflows/inventory-deploy.yml` |
| Orders | `.github/workflows/orders-deploy.yml` |
| Payments | `.github/workflows/payments-deploy.yml` |
| Notifications | `.github/workflows/notifications-deploy.yml` |

### Git Flow

- `feature/*` → PR в `develop` → `develop` публикует `:develop` образ
- `release/*` / `hotfix/*` → PR в `main` → `main` публикует `:latest`
- Тег `<service>-v*` → публикация версионного образа
- Каждый образ получает неизменяемый тег `sha-*`
- На PR образ только собирается, но не публикуется

### Deploy Pipeline

Push в `main` / тег / manual dispatch:
1. Build & push Docker image → `ghcr.io/<owner>/flashmarket-<service>`
2. SSH deploy на production сервер:
   - Формирование `.env` из GitHub Secrets/Variables
   - Копирование Compose и `.env` на сервер
   - Авторизация в GHCR временным `GITHUB_TOKEN`
   - Pull образа по exact digest (не по тегу)
   - Запуск инфраструктуры (PostgreSQL, Redis, RabbitMQ)
   - Миграции (Alembic)
   - Перезапуск сервисов
   - Health check публичного HTTPS endpoint

### GitHub Environment: `production`

**Variables:** `DEPLOY_HOST`, `DEPLOY_USER`, `AUTH_DOMAIN`

**Secrets:** `DEPLOY_SSH_KEY`, `*_POSTGRES_PASSWORD`, `*_REDIS_PASSWORD`, `*_RABBITMQ_PASSWORD`

---

## 10. Безопасность

### JWT

- **Алгоритм:** Ed25519 / EdDSA
- **Access TTL:** 5 минут
- **Key ring:** поддержка нескольких ключей через `kid`
- **JWKS:** `/.well-known/jwks.json`
- **Проверка:** `alg`, подпись, `kid`, `iss`, `aud`, `exp`, `sub`, `sid`, `jti`, `type`
- **Introspection:** `POST /auth/introspect` для немедленной проверки отзыва

### Пароли

- Argon2id хэширование, соль создаёт библиотека
- Устаревший hash обновляется после успешного login
- Timing-safe: неизвестный email получает dummy Argon2 verify
- Одинаковый `401 invalid_credentials` для неизвестного email и неверного пароля

### Rate Limiting

- Distributed через Redis
- По IP: 20 попыток / 60с
- По аккаунту: 5 попыток / 60с
- Независимо по IP и нормализованному email

### Sessions

- Активные сессии хранятся в Redis
- Немедленный отзыв при logout / смена пароля / блокировка / смена роли
- Redis fail → `503` (fail closed)
- Ownership: проверка `session_id + user_id`

### Refresh Tokens

- Хранятся только как SHA-256 digest
- Ротация при каждом использовании
- Replay старого токена → отзыв всей сессии
- Browser mode: `HttpOnly` cookie + double-submit CSRF

### Production Guardrails (Auth)

При `AUTH_ENVIRONMENT=production` сервис не стартует если:
- Включены debug/docs
- Отключён rate limiting
- Используются default DB credentials
- Redis/RabbitMQ без TLS (кроме Docker internal с явным allow)
- CORS/trusted hosts содержат `*`
- Cookie transport без `Secure` и `__Host-`

### Privacy

- IP сокращается: IPv4 до `/24`, IPv6 до `/64`
- Пароли, токены, cookies не попадают в audit и HTTP-логи

---

## 11. Observability

- **Prometheus метрики:** каждый сервис экспортирует `/metrics`
- **JSON-логи:** структурированное логирование
- **Request ID:** прокидывается через все слои
- **Health checks:** `liveness` и `readiness` probes
- **Grafana:** дашборды для контейнеров и метрик
- **Nginx status:** `/nginx_status` для внутреннего мониторинга

---

## 12. Тестирование

### Unit-тесты (per-service)

Каждый сервис содержит `tests/` с:
- In-memory SQLite через `aiosqlite` (подмена DB)
- `httpx.AsyncClient` с ASGI transport (без сети)
- Без моков — реальные запросы через SQLAlchemy

**Запуск:**
```bash
cd <service>
uv sync --all-groups
uv run pytest
```

### Integration-тесты (end-to-end)

`tests/test_purchase_saga.py` — тесты полного purchase saga:
- **Happy path:** catalog → stock → reserve → order → payment → confirm → notification
- **Failure path:** payment fail → order cancel → stock release → cancel notification
- Запускаются на полном Docker Compose стеке
- Polling с timeout для async event processing
- Используют `aio-pika` для RabbitMQ, `httpx` для HTTP

### Quality Checks

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest
```

---

## 13. Локальная разработка

### Быстрый старт (все сервисы)

```bash
# Создать сеть (если не существует)
docker network create shide-observability

# Запустить всё
docker compose up --build
```

### Отдельный сервис

```bash
cd <service>
cp .env.example .env
uv python install 3.14
uv sync --all-groups
docker compose up -d db redis rabbitmq  # зависимости
uv run alembic upgrade head
uv run uvicorn <service>.main:app --reload
```

### Seed данные

```bash
python seed.py
```

### Порты сервисов

| Сервис | API порт | DB порт |
|---|---|---|
| Gateway | 8080 | — |
| Frontend | 3000 | — |
| Auth | 8000 | 5432 |
| Catalog | 8010 | 5433 |
| Inventory | 8011 | 5434 |
| Orders | 8012 | 5435 |
| Payments | 8014 | 5436 |
| Notifications | 8016 | 5437 |
| Media | 4926 | shared PostgreSQL |
| Redis | 6379 | — |
| RabbitMQ | 5672 (AMQP), 15672 (Management) | — |

---

## 14. Структура репозитория

```
flashmarket/
├── .github/workflows/          # CI/CD для каждого сервиса
│   ├── auth-deploy.yml
│   ├── catalog-deploy.yml
│   ├── gateway-deploy.yml
│   ├── inventory-deploy.yml
│   ├── orders-deploy.yml
│   ├── payments-deploy.yml
│   ├── notifications-deploy.yml
│   └── media-ci.yml
│
├── auth/                       # Auth microservice
│   ├── src/auth_service/
│   ├── migrations/
│   ├── tests/
│   ├── keys/                   # JWT key ring (gitignored)
│   ├── scripts/                # key generation
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── docker-compose.deploy.yml
│
├── catalog/                    # Catalog microservice
│   ├── src/catalog/
│   ├── migrations/
│   ├── tests/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── docker-compose.deploy.yml
│
├── inventory/                  # Inventory microservice
│   ├── src/inventory/
│   ├── migrations/
│   ├── tests/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── docker-compose.deploy.yml
│
├── orders/                     # Orders microservice
│   ├── src/orders/
│   ├── migrations/
│   ├── tests/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── docker-compose.deploy.yml
│
├── payments/                   # Payments microservice
│   ├── src/payments/
│   ├── migrations/
│   ├── tests/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── docker-compose.deploy.yml
│
├── notifications/              # Notifications microservice
│   ├── src/notifications/
│   ├── migrations/
│   ├── tests/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── docker-compose.deploy.yml
│
├── frontend/                   # React SPA
│   ├── src/
│   │   ├── components/         # Cart, Catalog, Checkout, Layout, Order, Product, Profile
│   │   ├── config/
│   │   ├── context/
│   │   ├── services/
│   │   └── utils/
│   ├── Dockerfile
│   ├── package.json
│   └── vite.config.js
│
├── gateway/                    # Nginx API Gateway
│   ├── nginx.conf
│   └── docker-compose.yml
│
├── docker/                     # Shared infrastructure
│   ├── entrypoint.sh           # Universal entrypoint
│   ├── init-infra.py           # DB + RabbitMQ provisioning
│   └── rabbitmq/
│       └── enabled_plugins     # management + prometheus
│
├── tests/                      # Integration (saga) tests
│   ├── conftest.py
│   └── test_purchase_saga.py
│
├── docker-compose.yml          # Full stack (all services)
├── docker-compose.prod.yml     # Production gateway
├── seed.py                     # Test data seeder
├── .env.example                # Port configuration
└── catalog.md                  # Catalog service spec / TZ
```
