# FlashMarket Auth Service

Независимый Identity-микросервис FlashMarket. Он владеет пользователями,
сессиями, refresh-токенами и security audit. Остальные сервисы не обращаются к
его PostgreSQL напрямую.

## Возможности

- регистрация, login/logout, профиль и смена пароля;
- роли `CUSTOMER` и `ADMIN`, деактивация аккаунтов;
- Argon2id-хэширование паролей;
- access JWT с Ed25519/EdDSA, key ring, `kid` и публичным JWKS;
- ротация refresh-токенов и детектирование повторного использования;
- browser-режим `HttpOnly` cookie + double-submit CSRF;
- distributed rate limiting через Redis;
- активные сессии в Redis с немедленным отзывом и introspection;
- PostgreSQL как источник истины для `users`, `sessions`, `refresh_tokens`;
- CPython 3.14 и UUIDv7 для новых идентификаторов;
- domain events и transactional outbox с доставкой в RabbitMQ;
- нормализованный email, гарантированный DB constraint;
- security audit, request ID, JSON-логи и Prometheus-метрики;
- Alembic-миграции, cleanup истёкших данных и PostgreSQL integration-тест.

## Проверяемые security-гарантии

- Пароли хранятся только как `Argon2id`; соль создаёт библиотека, устаревший
  hash автоматически обновляется после успешного login.
- Неизвестный email и неверный пароль получают одинаковый `401
  invalid_credentials`; для неизвестного пользователя выполняется dummy Argon2
  verify, а в audit сохраняется только SHA-256 fingerprint email.
- Login ограничивается в Redis независимо по IP и нормализованному email:
  по умолчанию 20 попыток с IP и 5 попыток на аккаунт за 60 секунд.
- Email централизованно приводится к `trim + lowercase`; PostgreSQL дополнительно
  гарантирует формат через `CHECK` и уникальность через `UNIQUE`.
- Access JWT живёт 5 минут и содержит только идентификаторы, роль и обязательные
  служебные claims. Проверяются `alg`, подпись, `kid`, `exp`, `iss` и `aud`.
- Refresh-токен хранится только как SHA-256 digest, ротируется при каждом
  использовании, а replay старого токена отзывает всю серверную сессию.
- Logout, logout-all, смена пароля, блокировка аккаунта и смена роли немедленно
  удаляют активные сессии из Redis.
- Полный IP не сохраняется: IPv4 сокращается до `/24`, IPv6 до `/64`.
  Пароли, access/refresh-токены, cookies и `Authorization` не входят в audit и
  HTTP-логи.
- PostgreSQL integration-тесты проверяют конкурентную регистрацию и 50
  одновременных refresh-запросов: успешным может быть только один.
- Ownership сессий проверяется запросом `session_id + user_id`; чужая сессия
  возвращается как отсутствующая. Права на ресурсы остальных микросервисов
  проверяют сами владельцы этих ресурсов, а не frontend и не Auth.

## Запуск

```bash
cd auth
docker compose up --build
```

Compose:

1. создаёт активную Ed25519-пару в key ring внутри отдельного Docker volume;
2. ждёт готовности PostgreSQL;
3. применяет миграции отдельным `migrate` job;
4. ждёт Redis и RabbitMQ;
5. запускает API, outbox publisher и периодическую очистку.

Адреса по умолчанию:

- API: <http://localhost:8000>
- Swagger: <http://localhost:8000/docs>
- JWKS: <http://localhost:8000/.well-known/jwks.json>
- Metrics: <http://localhost:8000/metrics>
- PostgreSQL: `localhost:5432`
- Redis: `localhost:6379`
- RabbitMQ: `localhost:5672`
- RabbitMQ Management: <http://localhost:15672>

Если порты заняты:

```bash
AUTH_PORT=18000 AUTH_DB_PORT=15432 AUTH_REDIS_PORT=16379 \
AUTH_RABBITMQ_PORT=15672 AUTH_RABBITMQ_MANAGEMENT_PORT=25672 \
docker compose up --build
```

## Локальная разработка

```bash
cd auth
uv python install 3.14
uv sync --all-groups
uv run python scripts/generate_jwt_keys.py
cp .env.example .env
docker compose up -d db redis rabbitmq
uv run alembic upgrade head
uv run uvicorn auth_service.main:app --reload
# В другом терминале:
uv run python -m auth_service.outbox_worker
```

Ключи хранятся как `keys/private/<kid>.pem` и `keys/public/<kid>.pem` и
исключены из Git и Docker build context. Повторный запуск генератора с тем же
`kid` сохраняет пару.

Безопасная ротация:

```bash
uv run python scripts/generate_jwt_keys.py \
  --key-id flashmarket-auth-ed25519-v2
```

После генерации нужно установить
`AUTH_JWT_KEY_ID=flashmarket-auth-ed25519-v2` и перезапустить API. Новые токены
подписываются `v2`, а токены с `v1` продолжают проверяться по оставшемуся
публичному ключу. Старый публичный ключ можно удалить после истечения всех
access-токенов и запаса на кеширование JWKS. `--force` не используется для
штатной ротации: он заменяет ключ под тем же `kid` и немедленно ломает старые
токены.

## JWT и межсервисная проверка

Auth подписывает токен активным приватным ключом. Gateway и другие микросервисы
получают все допустимые публичные ключи:

```http
GET /.well-known/jwks.json
```

Они должны проверять `alg=EdDSA`, `kid`, `iss`, `aud`, `exp`, `sub`, `sid`,
`jti` и `type`. Для операций, где отзыв должен учитываться немедленно:

```http
POST /auth/introspect
Content-Type: application/json

{"token":"<access JWT>"}
```

Обычная локальная JWT-проверка не обращается к Auth. Access TTL по умолчанию —
5 минут.

Немедленный отзыв реализован через Redis: каждый защищённый запрос после
локальной проверки JWT сверяет `sid` и `sub` с активной сессией. Logout, смена
пароля, блокировка пользователя и изменение роли сначала удаляют соответствующие
ключи активных сессий. Поэтому уже выданный access JWT перестаёт приниматься
сразу, а не через пять минут. Если Redis недоступен, защищённые операции
закрываются с `503` (fail closed).

## События и transactional outbox

Изменение пользователя или сессии, audit-запись и запись `outbox_events`
коммитятся одним `Unit of Work`. Отдельный publisher читает записи через
`FOR UPDATE SKIP LOCKED`, публикует persistent-сообщение с publisher confirm и
только после подтверждения отмечает событие отправленным.

- exchange: `flashmarket.events` (`topic`, durable);
- routing key: `identity.<event_type>`;
- формат содержит `schema_version`, `event_id`, время, aggregate и `data`;
- ошибки получают exponential backoff;
- гарантия доставки — at least once, поэтому потребитель дедуплицирует сообщения
  по `event_id`.

Основные события: `user_registered`, `user_logged_in`, `token_refreshed`,
`user_logged_out`, `profile_updated`, `password_changed`,
`user_role_changed`, `user_status_changed`, `session_revoked` и
`all_sessions_revoked`.

## Архитектура application-слоя

HTTP-контроллеры вызывают use cases из компактных предметных модулей
`application/auth.py`, `users.py`, `sessions.py` и `admin.py`. Все их внешние
интерфейсы собраны в `application/contracts.py`: `UnitOfWork`,
`UserRepository`, `SessionRepository`, `AuditRepository` и `SessionStore`.
Application-слой не импортирует FastAPI, SQLAlchemy или Redis.

Конкретные SQLAlchemy repositories находятся в `infrastructure/persistence`.
`SessionRepository` управляет и сессиями, и refresh-токенами, поскольку
refresh-токен является частью жизненного цикла сессии. Отдельный generic
`BaseRepository[T]` намеренно не используется: интерфейсы содержат предметные
операции вроде `get_refresh_context_for_rotation`, `revoke_all_for_user` и
`get_active_for_update`.

ORM-сущности пока используются как модели данных между repository и use case.
Для текущего размера сервиса это сохраняет один набор моделей без отдельного
mapping-слоя. Если доменная логика существенно вырастет, их можно заменить
чистыми domain entities, не меняя use case-контракты repositories.

## Refresh-токен в браузере

По умолчанию `AUTH_REFRESH_TOKEN_TRANSPORT=cookie`:

- refresh хранится в `HttpOnly` cookie;
- отдельный CSRF token возвращается в ответе и non-HttpOnly cookie;
- `/auth/refresh` требует заголовок `X-CSRF-Token`;
- refresh и CSRF обновляются при каждой ротации.

Для CLI/mobile API можно включить `AUTH_REFRESH_TOKEN_TRANSPORT=body`. Тогда
refresh-токен возвращается и принимается в JSON. Browser frontend не должен
хранить его в `localStorage`.

В production cookie должен иметь `Secure` и имя с `__Host-`:

```env
AUTH_REFRESH_TOKEN_TRANSPORT=cookie
AUTH_REFRESH_COOKIE_SECURE=true
AUTH_REFRESH_COOKIE_NAME=__Host-flashmarket-refresh
AUTH_CSRF_COOKIE_NAME=__Host-flashmarket-csrf
```

## HTTP API

| Метод | Путь | Доступ | Назначение |
|---|---|---|---|
| `POST` | `/auth/register` | публичный | Создать `CUSTOMER` и сессию |
| `POST` | `/auth/login` | публичный | Войти и создать сессию |
| `POST` | `/auth/refresh` | refresh + CSRF | Ротировать refresh |
| `POST` | `/auth/introspect` | access token в body | Проверить активность |
| `POST` | `/auth/logout` | access token | Закрыть текущую сессию |
| `GET` | `/users/me` | access token | Получить профиль |
| `PATCH` | `/users/me` | access token | Изменить профиль |
| `POST` | `/users/me/password` | access token | Сменить пароль и отозвать сессии |
| `GET` | `/sessions` | access token | Получить сессии |
| `DELETE` | `/sessions/{id}` | access token | Отозвать сессию |
| `DELETE` | `/sessions` | access token | Отозвать все сессии |
| `GET` | `/admin/users` | `ADMIN` | Поиск и фильтрация пользователей |
| `PATCH` | `/admin/users/{id}/role` | `ADMIN` | Сменить роль |
| `PATCH` | `/admin/users/{id}/status` | `ADMIN` | Включить/отключить аккаунт |
| `GET` | `/admin/audit-events` | `ADMIN` | Security audit |
| `GET` | `/.well-known/jwks.json` | публичный | Публичный ключ |
| `GET` | `/health/live` | публичный | Liveness |
| `GET` | `/health/ready` | публичный | PostgreSQL + Redis readiness |
| `GET` | `/metrics` | инфраструктура | Prometheus metrics |

Access-токен передаётся как `Authorization: Bearer <token>`.

## Первый администратор

```bash
docker compose exec api .venv/bin/python -m auth_service.cli create-admin \
  --email admin@example.com \
  --password "replace-with-a-long-admin-password" \
  --full-name "FlashMarket Admin"
```

Если пользователь уже существует, команда требует одновременно
`--promote-existing` и его текущий пароль. При повышении старые сессии
отзываются.

## Очистка

Compose раз в час запускает:

```bash
uv run python -m auth_service.cli cleanup-expired
```

Периоды хранения задаются `AUTH_EXPIRED_DATA_RETENTION_DAYS` и
`AUTH_AUDIT_RETENTION_DAYS`.

## Проверки

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest
```

PostgreSQL integration-тест с конкурентной ротацией:

```bash
AUTH_TEST_DATABASE_URL=postgresql+asyncpg://flashmarket:flashmarket@localhost:5432/auth \
uv run pytest -m integration
```

Тест создаёт изолированную временную schema и удаляет только её.

## Git Flow и deploy

Workflow `.github/workflows/auth-deploy.yml` работает по следующей схеме:

- feature-ветки открывают pull request в `develop`;
- `develop` публикует образ `ghcr.io/<owner>/flashmarket-auth:develop`;
- release/hotfix pull request направляется в `main`;
- `main` публикует `:latest`;
- тег `auth-v*` публикует одноимённую версию образа;
- каждый опубликованный образ дополнительно получает неизменяемый тег `sha-*`.

На pull request образ только собирается, но не публикуется. Тесты и Docker build
обязательны. Ruff и mypy запускаются параллельно, записывают найденные проблемы
как warning в GitHub Actions summary и не участвуют в зависимостях deploy.
Workflow также можно запустить вручную через `workflow_dispatch`.

Push в `main`, тег `auth-v*` или ручной запуск после публикации образа выполняет
production deploy по SSH:

1. формирует production `.env` только из GitHub Variables и Secrets;
2. копирует на сервер Compose и `.env`;
3. авторизует сервер в GHCR временным `GITHUB_TOKEN`;
4. скачивает образ по точному digest, а не по изменяемому тегу;
5. поднимает PostgreSQL, Redis и RabbitMQ с постоянными Docker volumes;
6. запускает идемпотентный keygen и Alembic migrations;
7. перезапускает API, outbox и cleanup;
8. ждёт healthy-состояния API и проверяет публичный HTTPS endpoint.

В GitHub нужно создать Environment `production` и добавить Variables:

- `DEPLOY_HOST` — домен или IP сервера;
- `DEPLOY_USER` — отдельный deploy-пользователь;
- `AUTH_DOMAIN` — публичный домен Auth, DNS которого указывает на сервер;

Опционально можно переопределить `DEPLOY_PORT`, `DEPLOY_PATH`,
`AUTH_CORS_ORIGINS` и `AUTH_JWT_KEY_ID`. По умолчанию используются SSH-порт
`22`, путь `/home/<DEPLOY_USER>/flashmarket-auth`, CORS origin
`https://<AUTH_DOMAIN>` и `flashmarket-auth-ed25519-v1`.

Secrets:

- `DEPLOY_SSH_KEY` — приватный ключ deploy-пользователя;
- `AUTH_POSTGRES_PASSWORD` — пароль PostgreSQL;
- `AUTH_REDIS_PASSWORD` — пароль Redis;
- `AUTH_RABBITMQ_PASSWORD` — пароль RabbitMQ.

SSH deploy выполняется без проверки host key (`StrictHostKeyChecking=no`), поэтому
`DEPLOY_KNOWN_HOSTS` не нужен. Это упрощает подключение к новым серверам, но
снижает защиту от подмены SSH-сервера.

Пароли должны содержать 32–128 URL-safe символов. Их можно создать командой
`openssl rand -hex 32`.

Сервер может быть пустым: нужны только SSH, Docker с Compose plugin и доступ
deploy-пользователя к Docker. Workflow сам создаёт deploy-каталог и `.env`.
API публикуется на порту `8000`; в Nginx Proxy Manager создай Proxy Host для
`AUTH_DOMAIN` на `http://<IP_сервера>:8000` и включи SSL там. DNS `AUTH_DOMAIN`
должен заранее указывать на сервер.

Файл `.env.deploy.example` показывает итоговый формат, но на сервер вручную не
копируется. PostgreSQL, Redis, RabbitMQ, JWT-ключи и сертификаты сохраняются в
именованных Docker volumes и переживают обычные повторные deploy на том же
сервере. Новый сервер получает новые пустые volumes; перенос существующих
пользователей требует отдельного backup/restore PostgreSQL и JWT key volume.

## Production guardrails

При `AUTH_ENVIRONMENT=production` сервис не стартует, если:

- включены debug/docs;
- отключён rate limiting;
- используются стандартные DB credentials, localhost Redis или RabbitMQ;
- Redis подключён без TLS (`rediss://`);
- RabbitMQ подключён без TLS (`amqps://`);
- CORS/trusted hosts содержат `*`;
- cookie transport работает без `Secure` и `__Host-`.

Для однохостового deploy разрешены `redis://redis` и `amqp://rabbitmq` только
при явном `AUTH_ALLOW_INSECURE_INTERNAL_SERVICES=true`: оба сервиса находятся в
изолированной Docker network и наружу не публикуются. Любой другой production
host по-прежнему требует `rediss://` или `amqps://`.

JWT keygen создаёт ключ только при его отсутствии и хранит его в постоянном
Docker volume; API монтирует этот volume read-only. В Docker-образ и Git ключ не
включается. Для более строгой инфраструктуры volume можно заменить на внешний
Secret Manager или KMS.

## Структура

```text
auth/
├── keys/                   # private/<kid>.pem и public/<kid>.pem
├── migrations/
├── scripts/
├── src/auth_service/
│   ├── api/
│   ├── application/
│   │   ├── auth.py         # register/login/refresh/logout/introspection
│   │   ├── users.py        # профиль и пароль
│   │   ├── sessions.py     # просмотр и отзыв сессий
│   │   ├── admin.py        # роли, статусы и audit
│   │   └── contracts.py    # repositories, UoW и SessionStore
│   ├── domain/             # доменные события
│   ├── infrastructure/
│   │   ├── persistence/    # SQLAlchemy repositories и UoW
│   │   └── redis_session_store.py
│   ├── cache.py
│   ├── key_management.py
│   ├── observability.py
│   ├── outbox_worker.py
│   ├── rate_limit.py
│   └── ...
├── tests/
│   └── integration/
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
└── uv.lock
```
