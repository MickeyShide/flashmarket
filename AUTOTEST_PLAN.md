# План полного сценарного покрытия FlashMarket автотестами

## 1. Цель и границы анализа

Этот документ описывает автотесты, необходимые для покрытия 100% базовых функций проекта: обязательных позитивных, негативных, граничных и аварийных сценариев, без требования формальных 100% строк кода. План составлен по фактическому состоянию репозитория на 31.07.2026.

Обнаружено восемь backend-микросервисов: `auth`, `catalog`, `inventory`, `orders`, `payments`, `notifications`, `wishlist`, `drops`. `gateway` и `frontend` не владеют предметными данными, но являются публичными точками входа и поэтому включены как сквозные компоненты. Скрипты `seed.py`, `docker/init-infra.py` и `docker/entrypoint.sh` учитываются как эксплуатационные входы, но не считаются отдельными микросервисами.

В анализ вошли исходный код, маршруты FastAPI/Nginx, модели SQLAlchemy, Alembic-миграции, фоновые процессы, RabbitMQ-контракты, Redis, compose/CI-конфигурация, документация и все существующие тесты. S3/MinIO и реально вызываемые внешние HTTP API в коде не найдены. URL изображений хранятся как строки; тестовый payment provider полностью локальный. SMTP-параметры есть в `notifications/config.py`, но SMTP-клиент и отправка отсутствуют, поэтому SMTP не является текущей runtime-зависимостью.

### Условные обозначения

- `✅` — сценарий уже прямо проверяется существующим тестом.
- `◐` — проверяется только часть сценария, только через SQLite/мок либо без проверки важного состояния.
- `❌` — теста нет.
- `P0` — без сценария компонент нельзя признать рабочим.
- `P1` — необходим для надёжной эксплуатации.
- `P2` — редкий случай или дополнительная устойчивость.

### Неоднозначности, которые надо зафиксировать до закрытия P0

1. Только Auth проверяет JWT. Остальные API принимают произвольные `user_id` и открывают административные/изменяющие операции без principal. В плане принято безопасное ожидание: пользователь читает и меняет только свои ресурсы, mutations каталога/стока/дропов/промокодов и служебные переходы доступны только admin/internal identity. Если намеренно используется доверенный периметр, это должно быть формально закреплено, а contract-тесты должны проверять недоступность этих маршрутов извне.
2. `notifications/{id}/send` по backend-коду означает успешную доставку, а frontend использует его как «прочитано». До выбора семантики тест должен выявлять этот конфликт; придумывать отдельное поле read-state нельзя.
3. `orders.price` и `payments.amount` — целые числа, frontend передаёт копейки; промокоды используют `Decimal` в тех же вычислениях, а документация называет значения рублями. Единицу денег следует утвердить в контракте до фиксации ожидаемых сумм.
4. `drops.max_per_user` и `payment_timeout_seconds` хранятся и публикуются, но ни один сервис их не применяет. Они не считаются работающей бизнес-функцией; contract/E2E-тест должен зафиксировать отсутствие consumer/enforcement до реализации согласованного контракта.

## 2. Карта компонентов и реальных зависимостей

| Компонент | Ответственность | PostgreSQL | Redis | RabbitMQ | Фоновые процессы | Другие реальные зависимости |
|---|---|---:|---:|---:|---|---|
| Auth | пользователи, роли, JWT/JWKS, сессии, refresh, audit | Да | Да: sessions, touch, rate limit | Publisher | outbox, hourly cleanup, CLI admin/keygen | Ed25519 key ring, Argon2 |
| Catalog | категории, бренды, товары, изображения-URL, варианты, поиск | Да, `pg_trgm`/FTS | Нет | Нет | Нет | Нет S3/API |
| Inventory | stock counters, reservations, expiry, saga reactions | Да | Нет | Publisher + consumer | outbox; expiry только через `POST /internal/expire` | Нет |
| Orders | orders, promocodes, usage, saga state | Да | Нет | Publisher + consumer | outbox | Нет прямых HTTP-вызовов |
| Payments | mock payment attempts и payment events | Да | Нет | Publisher + consumer | outbox | Реального provider API нет |
| Notifications | notification records и delivery state | Да | Нет | Publisher + consumer | outbox | SMTP config не используется |
| Wishlist | список product UUID пользователя | Да | Нет | Нет | Нет | Catalog не вызывается |
| Drops | расписание/состав drops и lifecycle events | Да | Нет | Publisher | scheduler, outbox | Catalog/Inventory не вызываются |
| Gateway | path/subdomain reverse proxy, health, Prometheus proxy | Нет | Нет | Нет | Nginx + exporter | Docker DNS |
| Frontend | SPA, browser auth, cart, checkout orchestration, mock payment UI | Нет | browser localStorage/cookies | Нет | Нет | Только публичные HTTP API |

## 3. Фактическая тестовая база

Быстрые suites были запущены командой `uv run --no-sync pytest -q -p no:cacheprovider` с отключённой записью bytecode. Результат: Auth — 25 passed, 2 skipped; Catalog — 47 passed; Drops — 17 passed; Inventory — 14 passed, 1 skipped; Notifications — 7 passed; Orders — 24 passed; Payments — 8 passed; Wishlist — 16 passed. Пропущены локально только PostgreSQL concurrency-тесты, требующие environment URL. Два root E2E-теста не запускались, потому что требуют живой full stack.

Почти все service fixtures создают schema через `Base.metadata.create_all()` в SQLite, то есть не исполняют Alembic и не проверяют PostgreSQL semantics. Auth имеет два PostgreSQL concurrency-теста; Inventory — один. В CI PostgreSQL поднимается для шести старых сервисов, но фактически используется PostgreSQL-тестами только там, где fixture переключён на него. Drops и Wishlist вообще отсутствуют в workflows. Frontend/Gateway и root saga не имеют CI test job. `pytest-cov` не подключён.

## 4. Межсервисные контракты и purchase saga

| Producer | Routing key | Consumer(ы) | Обязательная проверка | Текущее покрытие |
|---|---|---|---|---|
| Orders | `orders.OrderCreated` | Notifications | schema, один notification на `event_id` | ◐ только root happy path, без duplicate delivery |
| Orders | `orders.PaymentRequested` | Payments | pending payment с теми же order/user/amount/currency, idempotency | ◐ root happy path нестабилен: payment читается без polling |
| Payments | `payments.PaymentSucceeded` | Orders, Inventory | order confirm и reservation commit атомарно в своих БД | ◐ root проверяет Order, но не Inventory |
| Payments | `payments.PaymentFailed` | Orders, Inventory | order cancel, reservation release, notification | ◐ root проверяет Order/notification, но не stock |
| Payments | `payments.PaymentCancelled` | Нет | Явно решить: компенсация или допустимое ожидание expiry | ❌ |
| Inventory | `inventory.ReservationReleased` | Orders | pending/awaiting order cancel, duplicate-safe | ❌ |
| Inventory | `inventory.InventoryReserved`, `inventory.InventoryCommitted` | Нет | Стабильность опубликованного контракта | ❌ consumer отсутствует |
| Orders | `orders.OrderConfirmed`, `orders.OrderCancelled` | Notifications; cancelled также Inventory | уведомление и компенсация | ◐ только часть root E2E |
| Notifications | `notifications.NotificationSent` | Нет | schema/outbox delivery | ❌ |
| Drops | четыре `drops.*` event | Нет | schema и delivery; назначение downstream не реализовано | ❌ |
| Auth | `identity.<snake_case event>` | Нет | schema, headers, retry/backoff | ◐ publisher unit есть, contract consumers отсутствуют |

Критическая фактическая несогласованность: Inventory ищет reservation по `order_id` из payment/order event. Root E2E резервирует без `order_id`, а frontend резервирует с временным UUID, после чего Orders создаёт другой `order.id`. Поэтому `PaymentSucceeded`, `PaymentFailed` и `OrderCancelled` не находят reservation и не изменяют stock. Имеющиеся E2E-тесты не проверяют `reserved/sold/available`, поэтому дефект остаётся зелёным.

Для всех RabbitMQ-тестов использовать реальный RabbitMQ container, durable topic exchange `flashmarket.events`, отдельный vhost/run-id, publisher confirms и polling по состоянию, а не `sleep`. Contract fixture должна валидировать routing key, `message_id`, `headers.event_id`, content type и JSON payload. Для at-least-once доставки нужен persistent inbox/deduplication contract; сейчас его нет ни в одном consumer.

Отдельный P0 configuration contract должен доказать, что producer и consumer одного события подключены к одному RabbitMQ vhost. Фактические compose URL используют разные vhost (`//orders` → `/orders`, `//payments` → `/payments`, `//inventory` → `/inventory`, `//notifications` → `/notifications`), а exchange в RabbitMQ ограничен vhost. Одинаковое имя `flashmarket.events` не делает эти exchanges общими; при текущей конфигурации межсервисные события не пересекают границу сервиса.

## 5. Auth Service

### Назначение, входы и данные

Auth владеет `users`, `sessions`, `refresh_tokens`, `audit_events`, `outbox_events`; подписывает EdDSA access JWT, публикует JWKS, хранит active-session markers/rate limits в Redis. Публичные входы существуют одновременно без префикса и под `/api/v1`: register, login, refresh, introspect, logout, profile, password, sessions, admin users/audit. Отдельные входы: `/.well-known/jwks.json`, `/health/live`, `/health/ready`, `/metrics`, CLI `create-admin`, CLI/compose cleanup и outbox worker.

Существующие тесты хорошо покрывают основной auth flow, refresh replay, CSRF-cookie mode, Argon2/JWT/JWKS, basic admin RBAC, audit privacy, outbox success/failure и две PostgreSQL гонки. Пробелы: реальные Redis failure modes/TTL, CLI/cleanup, readiness, обе копии маршрутов, миграции, транзакционные сбои между PostgreSQL и Redis, полная матрица admin filters/no-op/last-admin, outbox concurrency/reconnect и production middleware.

### Основные сценарии Auth

| ID | Приоритет | Уровень теста | Функция/сценарий | Предусловия | Действие | Ожидаемый результат | Зависимости | Текущее покрытие |
|---|---|---|---|---|---|---|---|---|
| AUTH-001 | P0 | API+integration | Регистрация и первая сессия | fresh DB/Redis, key ring | валидный mixed-case email, password, name | 201; CUSTOMER; email normalized; Argon2 hash; session+refresh+audit+outbox атомарны; Redis TTL активен; secrets не логируются | PostgreSQL, Redis | ◐ SQLite/fakeredis; PG атомарность/TTL нет |
| AUTH-002 | P0 | API+integration | Дубликат/конкурентная регистрация | одинаковый normalized email | 2–50 параллельных POST | ровно один 201, остальные 409; одна user/session/event chain | PostgreSQL | ✅ PG тест на 5 запросов; расширить state assertions |
| AUTH-003 | P0 | API | Валидация register/login и extra fields | нет | invalid email, 11/129 chars, whitespace password/name, extra keys | 422 без DB/Redis side effects | Нет | ◐ weak password есть, полная матрица нет |
| AUTH-004 | P0 | API+integration | Login success/unknown/wrong/disabled | users разных статусов | login | success создаёт session; failures одинаково 401 кроме disabled policy; dummy hash; audit fingerprint без email/token | PostgreSQL, Redis | ✅ основные ветки; disabled login частично через admin flow |
| AUTH-005 | P1 | Integration | Rate limit по IP/account/register/refresh/introspect | real Redis, короткое окно | достигнуть лимита и дождаться TTL | 429 + Retry-After; scopes независимы; после TTL запрос разрешён; Redis outage → 503 fail closed | Redis | ◐ fakeredis login/account; TTL/outage/остальные scopes нет |
| AUTH-006 | P0 | Security/API | Access JWT validation | active session/key ring | valid, expired, wrong alg/kid/signature/iss/aud/type, missing/bad UUID claims | только valid принимается; остальные 401/inactive, без fallback algorithm | Ed25519, Redis | ◐ valid/rotation есть; негативная claim matrix нет |
| AUTH-007 | P0 | API+integration | Refresh body rotation | active session/token | refresh дважды | первый 200 и replacement chain; replay 401, вся session revoked в DB/Redis, audit/outbox один раз | PostgreSQL, Redis | ✅ включая 50-way PG concurrency |
| AUTH-008 | P0 | Security/API | Cookie refresh и CSRF | cookie transport | missing/mismatch/header/cookie, valid rotation, invalid/replayed token | 403 для CSRF; valid меняет обе cookies; invalid очищает cookies; Secure/SameSite/HttpOnly атрибуты корректны | Redis | ◐ happy/missing header есть |
| AUTH-009 | P0 | API | Introspection и immediate revocation | valid access | до/после logout, password, role/status change, expiry; Redis down | correct active claims; после revocation active=false/401; outage 503 | Redis | ◐ logout есть; полная матрица/outage нет |
| AUTH-010 | P0 | API | Profile и password change | active principal | get, no-op patch, set/clear name, wrong/same/new password | ownership; validation; audit/outbox только при change; new password revokes все sessions/cookies | PostgreSQL, Redis | ◐ основные happy/wrong старый не покрыт |
| AUTH-011 | P0 | API+security | Session ownership и revocation | по 2 users/2 sessions | list, revoke own other/current, чужой UUID, revoke all | только свои данные; чужая 404; Redis+DB согласованы; tokens немедленно invalid | PostgreSQL, Redis | ✅ основные ownership flows; failure atomicity нет |
| AUTH-012 | P0 | API+security | Admin RBAC | CUSTOMER и ADMIN | list/filter/search/page; role/status change; audit list | customer 403; admin операции корректны; target sessions revoked; filters/count/order верны | PostgreSQL, Redis | ◐ базовые role/status/filter есть |
| AUTH-013 | P1 | Unit+API | Admin no-op/self/last-admin boundaries | один/несколько admins | same role/status, self-demote/self-disable, disable/demote последнего другого admin | no-op без audit; self forbidden; policy последнего admin явно закреплена | PostgreSQL | ◐ self cases есть; last-admin policy нет |
| AUTH-014 | P0 | Fault integration | PostgreSQL↔Redis consistency | fault injection commit/Redis | Redis fails after register commit; DB commit fails after Redis deactivation; retry | нет permanently orphaned/ghost session; поведение регистрации после partial failure документировано; fail closed | PostgreSQL, Redis | ❌ |
| AUTH-015 | P1 | Integration | Session touch throttling | active session, real Redis | несколько protected requests до/после interval | DB `last_seen_at` меняется не чаще interval; revoked/foreign session не touch; Redis outage 503 | PostgreSQL, Redis | ❌ |
| AUTH-016 | P0 | Integration | Transactional outbox | domain mutation | force rollback; two publishers; broker confirm/nack/unroutable/restart | event commit iff aggregate/audit commit; no double claim; persistent message; exponential retry и final success | PostgreSQL, RabbitMQ | ◐ success/failure single batch; concurrency/recovery нет |
| AUTH-017 | P1 | Contract | Все identity events | каждый use case | получить сообщение | routing key, event name, aggregate headers, payload и absence secrets соответствуют schema | RabbitMQ | ❌ |
| AUTH-018 | P1 | Integration | CLI create-admin | fresh/existing user | invalid input; create; duplicate; promote without/with flag and matching password | safe validation; ADMIN/audit/outbox; promotion revokes sessions; no accidental promote | PostgreSQL, Redis | ❌ |
| AUTH-019 | P1 | Integration | Cleanup retention | expired/recent/revoked rows | run `cleanup-expired` повторно | удалены только rows старше cutoffs; FK/cascade корректны; повтор идемпотентен | PostgreSQL | ❌ |
| AUTH-020 | P1 | API/ops | Health, metrics, middleware, startup keys | dependency/key faults | live/ready/metrics; bad/missing key; invalid Host/CORS/request-id | live process-only; ready 503 on DB/Redis; startup fail on key; metrics no secrets/cardinality explosion | PostgreSQL, Redis, keys | ❌ |
| AUTH-021 | P2 | Unit | IP/proxy/privacy boundaries | trusted/untrusted IPv4/IPv6 proxy | forwarded chains, malformed values, long UA | XFF trusted only from configured proxy; /24,/64; UA truncation; invalid IP omitted | Нет | ◐ anonymize only |
| AUTH-022 | P1 | Migration | Fresh/upgrade schema | empty DB и DB на каждой revision | `alembic upgrade head`, schema comparison, representative downgrade/upgrade | constraints/indexes/enums match models; data email normalized safely | PostgreSQL | ❌ |

### Фикстуры и критерий работоспособности Auth

Нужны factories `User`, `Session`, token/key-ring, frozen clock, real PostgreSQL/Redis/RabbitMQ containers, fake/real session store, exchange spy, fault-injecting UoW, log capture с secret scanner. Быстрый слой оставляет pure security/schema/use-case tests и ASGI+SQLite; обязательный infrastructure слой повторяет P0 persistence/security на PostgreSQL и real Redis.

Auth считается рабочим, когда все AUTH P0/P1 зелёные, все защищённые операции fail closed, refresh replay/registration race доказаны на PostgreSQL, DB/Redis partial failures имеют проверенное восстановление, все события атомарны и не содержат secrets, а migrations проходят на чистой и предыдущей schema.

## 6. Catalog Service

### Назначение, входы и данные

Catalog владеет categories/brands/products/product_images/product_variants. API: create/list categories; create/list/get brands; create/list/get/update/archive products; internal get-by-id; variant CRUD under product; health/metrics. PostgreSQL-only поиск использует `to_tsvector`, prefix tsquery и `pg_trgm`; SQLite использует ILIKE fallback. S3 отсутствует.

Существующие 47 тестов подробно проверяют category/product CRUD, slug, basic filters/search/sort, internal hidden product и variant CRUD. Нет отдельных brand tests, PostgreSQL FTS/migrations/concurrency, authZ, brand filters, product/variant transaction faults. Выявлено: `brand_slug` передаётся в repository query, но не применяется; variant get/update/delete не подтверждают принадлежность path `product_id`; product create/update не валидирует `brand_id`; public list позволяет явно запросить HIDDEN/ARCHIVED; concurrent slug generation не защищена обработкой DB unique error.

### Основные сценарии Catalog

| ID | Приоритет | Уровень теста | Функция/сценарий | Предусловия | Действие | Ожидаемый результат | Зависимости | Текущее покрытие |
|---|---|---|---|---|---|---|---|---|
| CAT-001 | P0 | API+integration | Category create/tree | root+children | valid create и list | normalized name, unique slug, correct nested tree/order, orphan fallback defined | PostgreSQL | ✅ SQLite; PG нет |
| CAT-002 | P0 | API | Category validation/errors | нет/missing parent | blank/name max/slug formats/duplicate/unknown parent | 422/409/404 envelope; rollback без partial row | PostgreSQL | ◐ duplicate/parent есть |
| CAT-003 | P0 | API | Brand create/list/get | brands | create; get by UUID/slug; list | fields/ordering/nullable values; duplicate 409; invalid/not found errors | PostgreSQL | ❌ отдельного покрытия нет |
| CAT-004 | P0 | API+transaction | Product create | valid category/brand/images | HIDDEN и ACTIVE products | slug, price/currency, category/brand names, images order, published_at semantics, one commit | PostgreSQL | ✅ базовое; brand/rollback нет |
| CAT-005 | P0 | Negative API | Product foreign references | missing category/brand | create/update | category/brand 404, не raw 500; no product/image partial state | PostgreSQL | ◐ category только |
| CAT-006 | P0 | Integration+concurrency | Unique product slug | same/transliterated/empty names | concurrent create, >100 collisions | deterministic suffix or declared conflict; no 500; DB uniqueness maintained | PostgreSQL | ◐ sequential chain only |
| CAT-007 | P0 | API | Public visibility/internal visibility | ACTIVE/HIDDEN/ARCHIVED | get/list/public status override/internal get | public reveals only allowed statuses; internal endpoint requires trusted identity; archived soft-deleted | PostgreSQL, auth policy | ◐ get/internal status; access/status override нет |
| CAT-008 | P0 | API+integration | Product search/filter | products by category/brand/status/price/text | combine filters incl `brand_id`, `brand_slug`, ranges, blank/no-hit | correct AND semantics, total/page; brand_slug actually filters | PostgreSQL FTS | ◐ category/price/basic search; brand_slug нет |
| CAT-009 | P1 | PostgreSQL integration | FTS/relevance/trigram | Russian/English text, typos/prefixes | search/sort relevance | expected ranking, prefix and typo matches; safe special characters | PostgreSQL `pg_trgm` | ❌ SQLite fallback only |
| CAT-010 | P1 | API | Pagination/sorting boundaries | >100 products/equal keys | limit 0/1/100/101, offsets, sorts asc/desc/relevance | validation and deterministic stable order/no duplicates between pages | PostgreSQL | ◐ basic pagination/sort |
| CAT-011 | P0 | API+transaction | Product partial update | product with images | each field, empty image replacement, ACTIVE transitions | only supplied fields change; slug stable; images atomic; first activation sets published_at; invalid range rolls back | PostgreSQL | ◐ basic name/price/status |
| CAT-012 | P0 | API | Archive semantics | each status | archive twice/nonexistent; retrieve/list after | first → ARCHIVED, second/not found defined; public hidden; internal retained | PostgreSQL | ✅ basic; list/internal after archive partial |
| CAT-013 | P0 | API | Variant create/list/get | product | explicit/auto SKU, no options, full fields, effective price | unique normalized SKU, option uniqueness, fallback product price, sort order | PostgreSQL | ✅ basic SQLite |
| CAT-014 | P0 | Security/API | Variant path ownership | products A/B, variant A | GET/PATCH/DELETE through product B path | 404 and no mutation; correct path succeeds | PostgreSQL | ❌ current service ignores product_id |
| CAT-015 | P0 | Integration+concurrency | Variant uniqueness/update | same SKU/options | parallel create; update to duplicate SKU/options | one success, domain 409 for correct constraint, rollback; no mislabeled duplicate | PostgreSQL | ◐ sequential create; update option conflict нет |
| CAT-016 | P1 | Integration | Variant cascade/effective precision | product variants/images | archive/delete model fixture; price override precision | lifecycle agreed; cascade on hard DB delete; numeric scale exact | PostgreSQL | ◐ effective price SQLite |
| CAT-017 | P0 | Security/API | Mutating/internal access | anonymous/customer/admin/internal | all create/update/delete/internal routes | access matrix enforced at service or trusted gateway boundary | Auth/gateway policy | ❌ endpoints open |
| CAT-018 | P1 | API/ops | Health/metrics/config | DB down; invalid prod config | probe/metrics/Host/CORS | readiness HTTP 503 on DB failure, not `200 {unavailable}`; metrics and guardrails correct | PostgreSQL | ❌ |
| CAT-019 | P1 | Migration | Alembic and search extensions | empty/old DB | upgrade head, schema diff, downgrade/upgrade | brands/variants/FKs/indexes/checks and `pg_trgm` match models | PostgreSQL | ❌ |

### Фикстуры и критерий работоспособности Catalog

Нужны category/brand/product/image/variant factories, deterministic clock/slug data, PostgreSQL container with migrations and `pg_trgm`, auth principals or trusted-proxy test adapter. Repository tests должны работать на PostgreSQL для FTS/constraints; SQLite оставить для fast API shape tests.

Catalog считается рабочим, когда public visibility и access boundaries доказаны, все CRUD/search/filter/variant paths и ошибки покрыты, concurrent slug/SKU не дают 500/duplicate, а Alembic schema и PostgreSQL search соответствуют моделям.

## 7. Inventory Service

### Назначение, входы и данные

Inventory владеет `stocks`, `reservations`, `outbox_events` и инвариантами `total/available/reserved/sold`. API создаёт/сбрасывает stock, читает, меняет total, reserve/commit/release; `/internal/expire` освобождает просроченные reservations. Consumer обрабатывает `PaymentSucceeded`, `PaymentFailed`, `OrderCancelled`; outbox публикует `InventoryReserved`, `InventoryCommitted`, `ReservationReleased`.

Существующие тесты проверяют базовый lifecycle, out-of-stock, expiry, serial no-oversell, variant reserve и outbox publish/failure. PostgreSQL concurrency-тест локально skipped, но настроен в inventory CI. Не проверяются consumers, retry/recovery, authZ, миграции и variant commit/release. Критические находки: migration `0002` добавляет composite unique, но не удаляет initial unique constraint/index на `product_id`, поэтому PostgreSQL не позволяет несколько variant stocks одного product; commit/release выбирают только stock с `variant_id IS NULL`; reset существующего stock выставляет `available=total`, не учитывая reserved/sold; expiry rows не блокируются.

### Основные сценарии Inventory

| ID | Приоритет | Уровень теста | Функция/сценарий | Предусловия | Действие | Ожидаемый результат | Зависимости | Текущее покрытие |
|---|---|---|---|---|---|---|---|---|
| INV-001 | P0 | API+integration | Create stock product/variant | product/variant UUID | create total 0/max/normal | counters initialized; one logical row per product+variant | PostgreSQL | ◐ SQLite product/one variant |
| INV-002 | P0 | Transaction | Reset existing stock | reserved/sold units exist | POST create/reset with total below/equal/above used | invariant preserved; below used → 409; available=`total-reserved-sold`; rollback on error | PostgreSQL | ❌ current reset can corrupt counters |
| INV-003 | P0 | API+integration | Get/update total | stock exists/missing | GET; PATCH boundaries | correct row incl variant; missing 404; cannot go below reserved+sold; exact available | PostgreSQL | ◐ get/product only; update untested |
| INV-004 | P0 | Concurrency | Atomic reserve/no oversell | stock N | >N parallel reserve | successes sum ≤ N; exact counters/reservations/events; losers 409 | PostgreSQL | ◐ one PG test; outbox/state detail limited |
| INV-005 | P0 | API+transaction | Reserve validation | stock 0/N | qty 0/max/max+1, unknown product/variant, exact available | 422/404/409; success decrements once; reservation TTL and event payload exact | PostgreSQL | ◐ happy/out-of-stock |
| INV-006 | P0 | Idempotency | Reservation/order identity | order_id repeated/concurrent | reserve same order twice | agreed idempotent same result or explicit 409; never two active reservations for one order | PostgreSQL | ❌ no DB uniqueness |
| INV-007 | P0 | API+integration | Commit product reservation | reserved with matching order | commit once/repeat/wrong order/product | RESERVED→COMMITTED once; reserved↓ sold↑; event atomic; repeat deterministic | PostgreSQL | ✅ happy; negative/repeat partial |
| INV-008 | P0 | API+integration | Commit/release variant reservation | variant stock reserved | commit/release by event/API | correct variant stock changes; base stock untouched | PostgreSQL | ❌ current lookup uses base stock only |
| INV-009 | P0 | API+integration | Manual release | active/committed/released reservation | release | active returns qty; terminal/missing → domain error; one event | PostgreSQL | ◐ happy only |
| INV-010 | P0 | Integration+concurrency | Expiry worker | expired/not-yet/terminal reservations | two concurrent `/internal/expire`, batch 0/1/N, repeat | each reservation released once; batch respected; no negative reserved/double available; events once | PostgreSQL | ◐ one single-thread test |
| INV-011 | P0 | Contract+consumer | PaymentSucceeded | reservation linked to actual order.id | deliver valid event, then duplicate | commit exactly once; ACK after DB commit; malformed payload retry/DLQ policy | PostgreSQL, RabbitMQ | ❌ |
| INV-012 | P0 | Contract+consumer | PaymentFailed/OrderCancelled | active reservation | deliver each, duplicate/out-of-order after success | release once if active; committed stock not reversed accidentally; reason propagated | PostgreSQL, RabbitMQ | ❌ |
| INV-013 | P0 | E2E | Order/reservation correlation | checkout-created reservation/order | success/failure saga | consumer finds reservation using shared stable identity; final stock exact | Full stack | ❌ existing E2E omits stock and uses mismatched IDs |
| INV-014 | P0 | Integration | Outbox atomicity/retry | reserve/commit/release | rollback, confirm/nack, worker restart, 2 publishers | state and event atomic; no double claim; failed event retried to published | PostgreSQL, RabbitMQ | ◐ publisher failure becomes `failed` and is never selected again |
| INV-015 | P0 | Security/API | Stock/internal access | anonymous/customer/admin/internal | create/reset/update/commit/release/expire/read/reserve | approved access matrix; arbitrary user_id impersonation rejected | Auth/gateway policy | ❌ all open |
| INV-016 | P1 | API/ops | Validation/error/health/metrics | malformed UUID/JSON, DB down | endpoints/probes | stable error envelope/request-id; readiness HTTP 503; metrics sane | PostgreSQL | ❌ readiness currently HTTP 200 unavailable |
| INV-017 | P0 | Migration | Variant migration/schema | DB at rev1 with data | upgrade rev2/head and insert base+multiple variants | old unique removed/migrated; intended NULL uniqueness; constraints/indexes match model | PostgreSQL | ❌ current migration conflicts |

### Фикстуры и критерий работоспособности Inventory

Нужны stock/reservation factories с base/variant cases, frozen clock, PostgreSQL container migrated from empty and rev1, RabbitMQ message factory, two independent sessions/workers, fault-injecting exchange. Inventory рабочий только если PostgreSQL доказывает отсутствие oversell, reset/expiry/variant paths сохраняют инварианты, saga success/failure меняет stock ровно один раз, failed outbox восстанавливается, а internal/mutation routes защищены.

## 8. Orders Service

### Назначение, входы и данные

Orders владеет order snapshot/lifecycle, promocodes, usages и outbox. API: create/get/list user orders, explicit confirm/fail; create/list/get/update/validate promocodes. Consumer реагирует на PaymentSucceeded/Failed и ReservationReleased. Outbox публикует OrderCreated, PaymentRequested, OrderConfirmed, OrderCancelled. `cancel_order()` существует как application entry, но HTTP-route отсутствует.

24 существующих теста покрывают основной API lifecycle, list, duplicates и большую часть арифметики/ограничений promocodes. Нет consumer/outbox/PostgreSQL/migration/authZ/concurrency/contract tests. `reservation_id` не уникален в DB, поэтому check-then-insert гонка; API доверяет переданным user/product/name/price/reservation без межсервисной проверки. Payment/order endpoints позволяют любому подтвердить/сломать чужой order. Discounted `price` вычисляется floor division, что может расходиться с `final_price`.

### Основные сценарии Orders

| ID | Приоритет | Уровень теста | Функция/сценарий | Предусловия | Действие | Ожидаемый результат | Зависимости | Текущее покрытие |
|---|---|---|---|---|---|---|---|---|
| ORD-001 | P0 | API+transaction | Create order from reservation | valid confirmed reservation contract | create | AWAITING_PAYMENT; immutable snapshot/totals; OrderCreated+PaymentRequested in same commit | PostgreSQL | ✅ SQLite basic/outbox rows |
| ORD-002 | P0 | Contract | Validate reservation/product/user snapshot | Catalog/Inventory fixtures | forged/missing/released/foreign reservation; price/name mismatch | reject before order or consume trusted event; no arbitrary amount/ownership | Catalog/Inventory contract | ❌ no verification exists |
| ORD-003 | P0 | Concurrency/idempotency | Duplicate reservation | one reservation | parallel creates/re-delivery | exactly one order/payment request; deterministic replay response/error; DB uniqueness | PostgreSQL | ◐ sequential 409 only |
| ORD-004 | P0 | API/security | Get/list ownership | users A/B | get/list чужого ID, pagination boundaries | only owner/admin; correct total/order/no cross-user leakage | Auth policy, PostgreSQL | ◐ list only, no auth |
| ORD-005 | P0 | State/API | Confirm payment | awaiting order | valid confirm, duplicate, mismatched payment/order/user/amount | CONFIRMED once and OrderConfirmed once; invalid 404/409 | PostgreSQL | ◐ happy/after fail |
| ORD-006 | P0 | State/API | Fail payment | awaiting order | fail, duplicate, after confirm | CANCELLED once and OrderCancelled once; no illegal reversal | PostgreSQL | ◐ happy only |
| ORD-007 | P1 | Unit | Explicit cancel application path | PENDING/AWAITING/CONFIRMED/CANCELLED | call `cancel_order` | only allowed states cancel and event reason preserved; expose route only if requirement chooses | Нет | ❌ |
| ORD-008 | P0 | Consumer/contract | PaymentSucceeded/Failed | awaiting order | real message, duplicate, unknown, malformed, out-of-order | legal transition once; ACK after commit; illegal/unknown no corrupt state; dedupe by event_id | PostgreSQL, RabbitMQ | ❌ |
| ORD-009 | P0 | Consumer/contract | ReservationReleased | pending/awaiting/confirmed order | event with/without order_id, duplicate | cancellable order cancelled once; confirmed unchanged; missing correlation handled explicitly | PostgreSQL, RabbitMQ | ❌ |
| ORD-010 | P0 | API | Promocode CRUD/validation | time-controlled codes | create/list/get/update; invalid dates/percentage/status | normalization, pagination, 404/409/422; DB checks; no partial update | PostgreSQL | ◐ create/duplicate and service validation; list/get/update gaps |
| ORD-011 | P0 | Unit+integration | Promo discount math | fixed/percentage/caps/min/currency | boundary amounts and fractional discounts | exact Decimal rounding and agreed money unit; discount≤amount; currency policy enforced | PostgreSQL | ✅ main math; currency/rounding boundaries missing |
| ORD-012 | P0 | Concurrency | max uses/per-user | limits 1/N | parallel order creation same/different users | never exceeds global/user limits; usage/current_uses exact | PostgreSQL locks | ❌ SQLite sequential only |
| ORD-013 | P0 | Transaction | Promo usage with order | valid promo | inject failure at order/event/usage stages; retry | order+usage+counter+two events commit/rollback together; no consumed promo without order | PostgreSQL | ◐ happy only |
| ORD-014 | P1 | API/contract | Validate endpoint is side-effect free | valid/invalid promo | repeated `/validate` | same calculation, usage/current_uses unchanged; invalid returns defined 200 payload | PostgreSQL | ✅ basic valid; state assertions/invalid matrix partial |
| ORD-015 | P0 | Money contract | `price`, `original_price`, `discount`, `final_price`, payment amount | multi-qty discount not divisible by qty | create and publish | displayed/order/payment totals remain exactly equal; no floor-loss ambiguity | Payments/frontend contract | ❌ |
| ORD-016 | P0 | Outbox integration | Publisher recovery/concurrency | pending events | rollback/nack/restart/two workers | persistent correct routing; failed retried; skip-locked prevents double claim | PostgreSQL, RabbitMQ | ❌ failed rows currently not retried |
| ORD-017 | P0 | Security/API | Admin/internal mutations | roles | promo CRUD, confirm/fail, create with other user | only approved role/service; direct public transition forbidden | Auth/gateway | ❌ |
| ORD-018 | P1 | Migration/ops | Schema, readiness, metrics | old/empty DB; DB down | migrations/probes | models match schema/FKs/checks/indexes; readiness HTTP 503 | PostgreSQL | ❌ |

### Фикстуры и критерий работоспособности Orders

Нужны order/reservation/payment event factories, promo/time/money matrices, migrated PostgreSQL, RabbitMQ, concurrent sessions, auth principals и failure injection around every flush/commit. Orders рабочий, когда доверенный reservation contract исключает подделку, один reservation создаёт один order, все state transitions/event replays идемпотентны, promo limits доказаны конкурентно, а все суммы совпадают с Payments/frontend.

## 9. Payments Service

### Назначение, входы и данные

Payments реализует только mock payment state: create/get/list, confirm/fail/cancel; consumer создаёт payment по `orders.PaymentRequested`; outbox публикует succeeded/failed/cancelled. Реального provider/webhook/API нет. Существующие 8 SQLite API-тестов покрывают CRUD/state happy paths и одну invalid transition; consumers, publisher, migrations, races, ownership и provider trust не покрыты.

### Основные сценарии Payments

| ID | Приоритет | Уровень теста | Функция/сценарий | Предусловия | Действие | Ожидаемый результат | Зависимости | Текущее покрытие |
|---|---|---|---|---|---|---|---|---|
| PAY-001 | P0 | API+transaction | Create pending payment | valid order contract | create | PENDING with exact order/user/amount/currency/provider; no event yet | PostgreSQL | ✅ SQLite |
| PAY-002 | P0 | Contract/security | Trusted order/amount | existing order | forged order/user/amount/currency | rejected or API internal-only; client cannot choose arbitrary charge | Orders/Auth policy | ❌ |
| PAY-003 | P0 | Idempotency/concurrency | One pending payment per order | no/prior pending/terminal | repeated and parallel create/events | repeated pending returns same ID; no duplicate pending rows under race; terminal retry policy explicit | PostgreSQL | ❌ sequential behavior only implicit |
| PAY-004 | P0 | State/API | Confirm | pending/missing/terminal | confirm once/twice/after fail/cancel | SUCCESS once, stable external_id, one PaymentSucceeded event; invalid 404/409 | PostgreSQL | ◐ happy + after fail |
| PAY-005 | P0 | State/API | Fail | pending/missing/terminal | fail | FAILED once, reason contract, one event | PostgreSQL | ✅ happy; boundaries missing |
| PAY-006 | P0 | State/API | Cancel | pending/missing/terminal | cancel | CANCELLED once and event; downstream compensation contract explicit | PostgreSQL, RabbitMQ | ◐ happy; no consumer for cancellation |
| PAY-007 | P0 | API/security | Get/list ownership and mutations | users A/B | access чужого payment, confirm чужой | owner/admin visibility; state changes only provider/internal identity | Auth policy | ❌ all open |
| PAY-008 | P0 | Consumer/contract | PaymentRequested | valid event | deliver, duplicate, malformed, out-of-order | pending payment once with exact fields; ACK after commit; dedupe event_id | PostgreSQL, RabbitMQ | ❌ |
| PAY-009 | P0 | Transaction | State+outbox atomicity | pending | fail before/after outbox flush/commit | payment and event change together; retry safe | PostgreSQL | ◐ API asserts event exists, fault paths absent |
| PAY-010 | P0 | Outbox | Publish/retry/concurrency | pending events | confirm/nack/unroutable/restart/2 workers | correct routing/headers/persistence; failed eventually published once logically | PostgreSQL, RabbitMQ | ❌ current failed status never retried |
| PAY-011 | P0 | Contract | Amount/currency match Orders | discounted/multi-qty orders | PaymentRequested→payment→success | exact amount/unit/currency round-trip | Orders, RabbitMQ | ❌ |
| PAY-012 | P1 | API | Validation/pagination/errors | many payments | amount 0/max/max+1, currency/provider lengths, offsets | 422/404 envelope; correct order/total/page | PostgreSQL | ◐ list basic |
| PAY-013 | P1 | Migration/ops | Schema/readiness/metrics/config | empty DB/DB down | migration/probes | amount check/indexes match model; readiness 503; prod config guardrails | PostgreSQL | ❌ |

### Фикстуры и критерий работоспособности Payments

Нужны payment/order-event factories, fake clock/external-id generator, migrated PostgreSQL, RabbitMQ, auth/internal principals и exchange failures. Не следует мокировать несуществующий Stripe/банк. Payments рабочий как mock-сервис, когда only-trusted transitions, concurrent idempotency, exact money contract и recoverable outbox доказаны. Реальная оплата не входит в DoD текущего кода.

## 10. Notifications Service

### Назначение, входы и данные

Notifications хранит notification records, создаёт их напрямую или из Order events, позволяет get/list и меняет PENDING→SENT либо статус на FAILED. Outbox публикует только NotificationSent. Фактической доставки email/SMS/PUSH нет; `smtp_*` settings не используются.

7 существующих SQLite API-тестов покрывают create/get/list/send/fail и send-after-fail. Не покрыты consumers, duplicate events, outbox, PostgreSQL, ownership, attempts policies и конфликт «send»/«read». `mark_failed` разрешает перевод SENT/FAILED снова в FAILED и увеличивает attempts; consumer всегда создаёт новую запись при redelivery.

### Основные сценарии Notifications

| ID | Приоритет | Уровень теста | Функция/сценарий | Предусловия | Действие | Ожидаемый результат | Зависимости | Текущее покрытие |
|---|---|---|---|---|---|---|---|---|
| NOT-001 | P0 | API+integration | Create notification record | valid user | EMAIL/SMS/PUSH, field boundaries | PENDING, attempts=0, no sent_at; required strings validated | PostgreSQL | ✅ happy only |
| NOT-002 | P0 | API/security | Get/list ownership | users A/B | get/list чужих IDs, pagination | owner/admin only; newest first; correct total/page | Auth policy, PostgreSQL | ◐ list only, no auth |
| NOT-003 | P0 | State/API | Mark sent | PENDING/missing/FAILED/SENT | send once/repeat | agreed legal transition only; sent_at once; NotificationSent atomic | PostgreSQL | ◐ happy + failed→send 409 |
| NOT-004 | P0 | State/API | Mark failed/retry semantics | PENDING/SENT/FAILED | fail with empty/long reason, repeat | only allowed states; attempts/error semantics fixed; no SENT→FAILED corruption unless explicit provider event | PostgreSQL | ◐ one happy; current transition unrestricted |
| NOT-005 | P0 | Contract | `send` versus «read» | frontend notification | click «Прочитано» | contract must not claim delivery unless that is intended; selected semantic asserted end-to-end | Frontend | ❌ conflict exists |
| NOT-006 | P0 | Consumer | OrderCreated | event | deliver/duplicate/malformed | exactly one correct pending notification per event; no fabricated recipient contract unless approved | PostgreSQL, RabbitMQ | ❌ |
| NOT-007 | P0 | Consumer | OrderConfirmed/Cancelled | events with/without reason | deliver, duplicates/out-of-order | correct subject/body/user; dedupe by event_id; ACK after commit | PostgreSQL, RabbitMQ | ◐ root asserts subject only |
| NOT-008 | P0 | Privacy/security | Recipient/body exposure | users A/B, sensitive payload | API/log/event operations | recipient/body visible only to owner/admin; logs/outbox do not leak unnecessary data | Auth policy | ❌ |
| NOT-009 | P0 | Outbox | NotificationSent publish/recovery | mark sent | rollback/nack/restart/2 workers | state/event atomic, routing correct, failed retried | PostgreSQL, RabbitMQ | ❌ failed rows never retried |
| NOT-010 | P1 | API | Validation/error boundaries | none | blank/max/max+1 fields, invalid UUID/channel, reason | 422/404 stable envelope and no writes | Нет | ❌ |
| NOT-011 | P1 | Ops | Health/metrics/config | DB down | probes | readiness HTTP 503; unused SMTP config does not imply false readiness | PostgreSQL | ❌ |
| NOT-012 | P1 | Migration | Schema consistency | empty/old DB | migrate/schema diff | fields/indexes/defaults match model | PostgreSQL | ❌ |

### Фикстуры и критерий работоспособности Notifications

Нужны order-event and notification factories, migrated PostgreSQL, RabbitMQ duplicate-message fixture, auth principals, frozen clock and log privacy assertions. SMTP container не нужен, пока нет SMTP code. Сервис считается рабочим как persistence/mock-delivery service, когда event redelivery не плодит записи, ownership соблюдается, state machine однозначна, outbox восстанавливается и frontend использует ту же семантику статуса.

## 11. Wishlist Service

### Назначение, входы и данные

Wishlist владеет только `(user_id, product_id, created_at)`. API add/remove/list/check и static health/metrics. Catalog не вызывается, RabbitMQ/Redis нет. 16 SQLite-тестов покрывают все четыре API, duplicate/remove missing, pagination/order, batch check и configured item limit.

Пробелы: ownership/authZ, PostgreSQL constraints/migrations/concurrency, product existence/lifecycle contract, atomic max-items limit, batch boundary/duplicate order, readiness фактически не проверяет DB.

### Основные сценарии Wishlist

| ID | Приоритет | Уровень теста | Функция/сценарий | Предусловия | Действие | Ожидаемый результат | Зависимости | Текущее покрытие |
|---|---|---|---|---|---|---|---|---|
| WISH-001 | P0 | API+integration | Add item | valid user/product | add | 201, one row, exact IDs/timestamp | PostgreSQL | ✅ SQLite |
| WISH-002 | P0 | Idempotency/concurrency | Duplicate add | item exists | sequential/parallel add | one success, rest stable 409 or agreed idempotent response; one row | PostgreSQL | ◐ sequential only |
| WISH-003 | P0 | Concurrency | Max items per user | count limit-1 | parallel different adds crossing limit | final count never exceeds config; deterministic errors | PostgreSQL | ◐ sequential only |
| WISH-004 | P0 | API | Remove item | own/missing/foreign | delete | own 204; missing 404; no cross-user delete | PostgreSQL, Auth | ◐ own/missing, no auth |
| WISH-005 | P0 | API | List/pagination/order | 0/N items | boundaries/offset past end | newest first with deterministic tie-break, correct total/page | PostgreSQL | ✅ basic SQLite |
| WISH-006 | P0 | API | Batch check | present/absent/repeated IDs | 1/50/0/51 items | found unique IDs; stable ordering contract or set semantics documented; 422 boundaries | PostgreSQL | ◐ simple one-found case |
| WISH-007 | P0 | Security | User identity binding | JWT A, path A/B | all endpoints | path cannot impersonate another user; admin policy explicit | Auth/gateway | ❌ |
| WISH-008 | P1 | Contract | Product existence/status | missing/archived product | add/check after archive | chosen behavior formalized: reject invalid product and cleanup/retain archived consistently | Catalog | ❌ no interaction exists |
| WISH-009 | P1 | Transaction/fault | DB errors | injected flush/commit error | add/remove | rollback, correct domain/5xx envelope, retry safe | PostgreSQL | ◐ IntegrityError duplicate only |
| WISH-010 | P1 | Ops | Health/metrics/config | DB down | `/health/ready` | HTTP 503 if DB unavailable; metrics correct | PostgreSQL | ❌ current probe always 200 |
| WISH-011 | P1 | Migration | Schema consistency | empty DB | upgrade/downgrade/schema diff | unique/index/model match | PostgreSQL | ❌ |

### Фикстуры и критерий работоспособности Wishlist

Нужны user/product/item factories, migrated PostgreSQL, concurrent sessions, catalog contract stub только после утверждения existence policy, auth principals. Wishlist рабочий, когда ownership, duplicate/max-limit races и DB readiness доказаны на PostgreSQL, а product lifecycle поведение явно зафиксировано.

## 12. Drops Service

### Назначение, входы и данные

Drops владеет drop schedule/status/items и outbox. Public API: active/upcoming/get visible slug. Admin API: create/list/get/update/schedule/start/end/cancel/add/remove. Scheduler каждые 10 секунд автоматически переводит due SCHEDULED→ACTIVE и ACTIVE→ENDED. События: scheduled/started/ended/cancelled.

17 SQLite-тестов покрывают основные state transitions, item mutations, часть public API и один scheduler tick. Нет outbox worker, PostgreSQL, migration, scheduler concurrency/recovery, update/list/get/cancel API matrix, authZ или gateway tests. Gateway сейчас направляет весь `/api/v1/admin/*` в Auth, поэтому `/api/v1/admin/drops/*` через основной host недоступен Drops. Events никем не потребляются; лимиты не исполняются downstream.

### Основные сценарии Drops

| ID | Приоритет | Уровень теста | Функция/сценарий | Предусловия | Действие | Ожидаемый результат | Зависимости | Текущее покрытие |
|---|---|---|---|---|---|---|---|---|
| DROP-001 | P0 | API+integration | Create DRAFT | future interval | valid/boundary request | DRAFT exact fields; starts future; ends>starts; unique slug | PostgreSQL | ✅ basic SQLite |
| DROP-002 | P0 | API | Validation/errors | now/past/invalid interval/limits | create | 422/domain conflict, no row; timezone-aware behavior stable | PostgreSQL, clock | ◐ duplicate/basic time |
| DROP-003 | P0 | API | Update DRAFT/SCHEDULED | each state | each field/partial invalid time/duplicate slug/past start | allowed states atomic; complete interval revalidated; forbidden states 409 | PostgreSQL | ❌ |
| DROP-004 | P0 | State/API | Schedule/start/end | valid drop/items | legal and every illegal transition, repeated calls | exact state machine; one event per transition | PostgreSQL | ✅ main transitions; full matrix/events partial |
| DROP-005 | P0 | State/API | Cancel | DRAFT/SCHEDULED/ACTIVE/ENDED/CANCELLED | cancel/repeat | allowed three → CANCELLED+event; terminals 409 | PostgreSQL | ◐ service basic |
| DROP-006 | P0 | API | Item add/remove | draft/scheduled/active | add duplicate/missing product; remove missing; ordering | unique membership; allowed states only; correct domain errors | PostgreSQL | ✅ core SQLite; ordering/product contract gaps |
| DROP-007 | P1 | Contract | Product existence/status | valid/missing/archived Catalog IDs | add/start | chosen Catalog contract validated; event contains intended products only | Catalog | ❌ backend trusts UUID |
| DROP-008 | P0 | Public visibility | all statuses | active/upcoming/get slug | lists/get | only correct statuses/order; DRAFT/CANCELLED hidden; ENDED visibility explicitly asserted | PostgreSQL | ◐ active/upcoming, get matrix absent |
| DROP-009 | P0 | Security/API | Admin access | anonymous/customer/admin | every admin route direct and through gateway | only admin; public routes remain public; no route collision | Auth, Gateway | ❌; gateway misroutes to Auth |
| DROP-010 | P0 | Scheduler integration | Due boundary | before/equal/after start/end | one tick | only due rows transition; started payload includes items; both changes atomic | PostgreSQL, frozen clock | ✅ one SQLite tick |
| DROP-011 | P0 | Scheduler concurrency/idempotency | same due drops | two ticks/workers/restart | run concurrently/repeatedly | one transition/event per drop; row locks prevent duplicates/lost state | PostgreSQL | ❌ no locks currently |
| DROP-012 | P0 | Outbox | Publisher recovery | all four events | confirm/nack/unroutable/restart/2 workers | correct routing/schema/persistence; failed retried | PostgreSQL, RabbitMQ | ❌ failed rows never retried |
| DROP-013 | P1 | Contract | `max_per_user`/timeout downstream | active drop | publish/attempt purchase | payload schema stable; enforcement status explicitly tested/marked unavailable until consumer exists | Inventory/Orders | ❌ no consumers |
| DROP-014 | P1 | Ops/migration | Schema/readiness/config | empty DB/DB down | migration/probes | constraints/indexes match; readiness 503 and actually checks DB | PostgreSQL | ❌ static readiness |

### Фикстуры и критерий работоспособности Drops

Нужны drop/item factories for all states, frozen clock, migrated PostgreSQL, RabbitMQ, two scheduler instances, auth principals, gateway container. Drops рабочий, когда admin path реально маршрутизируется и защищён, lifecycle/scheduler дают ровно одно событие при конкуренции, public visibility точна, outbox восстанавливается, а неиспользуемые downstream limit fields явно не выдаются за работающие ограничения.

## 13. Gateway и Frontend как публичные компоненты

Gateway содержит public health, path routing к восьми сервисам, subdomain routing, frontend fallback, Prometheus proxy и restricted `nginx_status`. Frontend реализует catalog filters/detail, local cart/stock, browser auth refresh, checkout reserve→order with compensating release, profile/sessions/orders/notifications и mock payment confirm. Автотестов нет, `package.json` не содержит test script.

### Основные сценарии Gateway/Frontend

| ID | Приоритет | Уровень теста | Функция/сценарий | Предусловия | Действие | Ожидаемый результат | Зависимости | Текущее покрытие |
|---|---|---|---|---|---|---|---|---|
| GW-001 | P0 | Integration | Path routing всех API | all services healthy | запросить каждый route family | ответ ровно целевого service; path/query/body/cookies preserved | Nginx, services | ❌ |
| GW-002 | P0 | Integration | `/api/v1/admin/drops` specificity | Auth и Drops | admin Drops request | уходит Drops, не Auth; auth admin остаётся Auth | Nginx | ❌ текущая конфигурация неверна |
| GW-003 | P0 | Security | Internal/admin exposure | external client | `/internal/expire`, catalog internal, admin mutations, metrics/prometheus/status | только утверждённые endpoints/identities доступны; `nginx_status` external denied | Nginx/Auth policy | ❌ |
| GW-004 | P1 | Integration | Proxy headers/body/timeouts/errors | trusted proxy/upstream down | forwarded IP, >16K body, slow/down service | spoofed XFF overwritten; limits/timeouts/502 predictable; Auth sees real trusted IP | Nginx | ❌ |
| GW-005 | P1 | Integration | Subdomains/frontend/SPA/health | DNS Host variants | routes/assets/deep URL/health | correct upstream, SPA fallback, health 200, unknown API not swallowed by frontend unexpectedly | Nginx, frontend | ❌ |
| FE-001 | P0 | Component | API client auth/refresh | mocked fetch/cookies/storage | normal response; one/many concurrent 401; refresh success/fail/403 | one refresh flight; all wait/retry or fail consistently; state cleared once | Browser APIs | ❌ current boolean does not queue concurrent callers |
| FE-002 | P0 | Component/E2E | Register/login/logout/profile/sessions | browser+Auth | full flow, expired/revoked token | correct UI/storage/cookies; no refresh token in localStorage; logout/session close updates UI | Auth/Gateway | ❌ |
| FE-003 | P0 | Component | Catalog/product/variant stock | catalog data | filter/search/load more/detail/select variant | stable pagination/error/retry; selected variant queries variant stock and price | Catalog/Inventory | ❌ UI currently uses base stock and hard-coded sizes |
| FE-004 | P0 | Component | Cart persistence/inventory boundaries | corrupt/full localStorage, changing stock | add/change/remove/reload | corrupt storage recovers; no qty above live stock; storage errors visible/handled | Browser storage, Inventory | ❌ |
| FE-005 | P0 | E2E | Checkout success | logged-in user, multi-item cart | submit | each reservation correlates to actual order; orders created; cart clears only after durable success | Inventory/Orders | ❌ temp order IDs diverge from actual IDs |
| FE-006 | P0 | E2E/fault | Checkout compensation | failure after reservation/order N | inject each API failure/retry/page close | only unconsumed reservations released; already-created orders not falsely reported rolled back; recoverable state retained | Inventory/Orders | ❌ current UI releases even reservations with created orders and always claims all freed |
| FE-007 | P0 | E2E | Payment success/failure | awaiting order | double click/network timeout/event delay | one payment; amount uses final total; eventual order+inventory+notification state; button idempotent | Payments/Orders/RabbitMQ | ❌ |
| FE-008 | P0 | Security/E2E | Cross-user UI/API access | users A/B | modify URL/IDs | no чужие orders/payments/notifications/wishlist/sessions visible or mutable | All services | ❌ |
| FE-009 | P1 | Component/E2E | Notifications semantics | pending notification | «Прочитано» | agreed read/delivery state only, no false NotificationSent | Notifications | ❌ |
| FE-010 | P1 | Build/smoke | Production bundle/Nginx | clean Node install | `npm ci`, build, serve | reproducible build, assets/SPA load, no console fatal errors | Node/Nginx | ❌ no lockfile/test script discovered |

Gateway готов, когда все routes, access boundaries, proxy headers and failure responses tested in a container. Frontend готов, когда component tests cover state/API error paths and browser E2E proves auth, catalog/cart, checkout compensation and payment saga without cross-user leaks.

## 14. Общая матрица покрытия

| Компонент | Unit/domain | API | PostgreSQL/migrations | Redis | Rabbit publisher | Rabbit consumer | Contract | E2E | Текущий уровень |
|---|---|---|---|---|---|---|---|---|---|
| Auth | Хороший | Хороший | Частично: 2 concurrency | Fakeredis | Частично | N/A | JWKS частично | Нет | ◐ ближе всех к базовой готовности |
| Catalog | Частично через API | Хороший core | Нет | N/A | N/A | N/A | Internal/auth отсутствует | Root частично | ◐ бренды/PG/access/search gaps |
| Inventory | Частично | Хороший basic lifecycle | 1 concurrency, migrations нет | N/A | 2 unit cases | Нет | Нет | Stock final state нет | ◐ критические variant/correlation gaps |
| Orders | Promo хороший, order basic | Хороший basic | Нет | N/A | Нет | Нет | Нет | Order status частично | ◐ saga/idempotency/access gaps |
| Payments | Basic | Basic | Нет | N/A | Нет | Нет | Нет | Happy/fail частично | ◐ mock CRUD only |
| Notifications | Basic | Basic | Нет | N/A | Нет | Нет | Нет | Subject частично | ◐ persistence only |
| Wishlist | Хороший basic | Хороший basic | Нет | N/A | N/A | N/A | Auth/Catalog нет | Нет | ◐ concurrency/ownership gaps |
| Drops | Lifecycle basic | Частично | Нет | N/A | Нет | N/A | Downstream нет | Нет | ◐ scheduler single-thread only |
| Gateway | N/A | Нет | N/A | N/A | N/A | N/A | Нет | Нет | ❌ routing/security untested |
| Frontend | Нет | Нет | N/A | Browser flow нет | N/A | N/A | Нет | Нет | ❌ no test tool/script |
| Purchase saga | N/A | 2 tests | Shared live DB only | Auth indirectly | Indirect | Indirect | Schema не валидируется | happy + fail | ❌ не в CI, не проверяет inventory, config blocks delivery |

## 15. Критические пробелы, обнаруженные в коде и конфигурации

1. P0 — разные RabbitMQ vhost изолируют одноимённые exchanges; Orders→Payments→Orders/Inventory/Notifications события не могут пройти в root compose.
2. P0 — order/reservation correlation расходится: Inventory ожидает реальный `order_id`, а E2E его не сохраняет, frontend передаёт временный UUID. Success не commit stock, failure/cancel не release stock; существующие E2E это не утверждают.
3. P0 — кроме Auth, сервисы не аутентифицируют и не авторизуют запросы: доступны чужие user resources, admin CRUD, stock/order/payment state transitions и internal expiry.
4. P0 — Gateway отправляет `/api/v1/admin/drops` в Auth из-за общего location `/api/v1/admin`; admin Drops через основной gateway недоступен.
5. P0 — generic outbox workers Inventory/Orders/Payments/Notifications/Drops переводят publish failure в `failed`, но выбирают только `pending`; автоматического retry нет.
6. P0 — consumers не имеют inbox/event-id deduplication. Notifications гарантированно создаст duplicate при redelivery; check-then-insert Payments/Orders допускает race duplicates.
7. P0 — Inventory migration variant stock не удаляет старую uniqueness по `product_id`; PostgreSQL не поддержит несколько variants. Commit/release variant дополнительно ищут только base stock.
8. P0 — Inventory reset существующего stock игнорирует reserved/sold и может создать неверный available либо DB error вместо domain response; expiry не защищён от двух workers.
9. P0 — root compose публикует одинаковые host ports для Payments/Wishlist (`4921`) и Notifications/Drops (`4922`), поэтому полный stack конфликтует без overrides.
10. P0 — PostgreSQL semantics/Alembic почти не тестируются: suites в основном используют SQLite `metadata.create_all`; migration/model drift и locks остаются незаметными.
11. P0 — readiness Catalog/Inventory/Orders/Payments/Notifications возвращает HTTP 200 с `unavailable`; Drops/Wishlist вообще не проверяют DB.
12. P0 — Catalog `brand_slug` filter фактически игнорируется, variant routes не проверяют соответствие path product, invalid `brand_id` не переводится в domain error, mutating/internal routes открыты.
13. P0 — Payments confirm/fail/cancel являются публичным mock control API; Notifications `/send` не отправляет сообщение и конфликтует с frontend «прочитано».
14. P1 — Drops events не имеют consumers; `max_per_user` и payment timeout нигде не применяются. PaymentCancelled также не имеет compensation consumer.
15. P1 — root E2E не включён в CI, делает немедленный GET payment без eventual polling и не использует реального Auth user; Frontend/Gateway/Drops/Wishlist не имеют CI test jobs.
16. P1 — root/docs конфигурация устарела: `project.md` описывает шесть сервисов, а код содержит восемь; README Orders содержит несовпадающий list route; `.env.example` не описывает Drops/Wishlist ports.

## 16. Рекомендуемый порядок реализации тестов

1. Test harness: общие factories/event schemas, Testcontainers PostgreSQL 17/Redis/RabbitMQ, migration fixtures, markers `unit/api/integration/contract/e2e`, уникальный run ID.
2. Blocking configuration smoke: один RabbitMQ vhost для saga test, уникальные host ports, Gateway admin Drops route, все readiness probes. Эти тесты должны сначала воспроизвести текущие отказы.
3. Security P0: единый auth contract/principal для всех сервисов, owner/admin/internal matrix и cross-user tests через direct API и Gateway.
4. Inventory PostgreSQL P0: migration variant case, reset invariant, reserve/expire concurrency, variant commit/release, stable order correlation.
5. Orders/Payments P0: DB uniqueness/idempotency, money contract, promo concurrency, trusted state transitions.
6. Consumer/Outbox P0: event schemas, common vhost, duplicate/out-of-order/malformed delivery, ACK/rollback, retry after broker recovery, two workers.
7. Full saga P0: authenticated checkout success, payment failure, timeout/cancel, duplicate delivery, process restarts; assert every DB-visible state including stock.
8. Auth resilience P0/P1: real Redis TTL/outage, DB↔Redis fault atomicity, CLI/cleanup/migrations.
9. Catalog/Wishlist/Drops/Notifications remaining API/PG contracts and boundaries.
10. Frontend component/browser E2E, then P2 observability/proxy/rare failure and load tests.

## 17. Требования к тестовому окружению

- Python 3.14 and `uv`; dependencies installed from each committed `uv.lock`. Frontend requires Node compatible with Dockerfile (Node 20) and a committed lockfile before reproducible `npm ci`.
- PostgreSQL 17. Каждый infrastructure run создаёт отдельные databases или containers; schema строится `alembic upgrade head`, не `metadata.create_all`. Нужны fixtures «empty», «previous revision with data» и schema-model diff.
- Redis той же major version, что production/shared infra. Реальный Redis обязателен для TTL, atomic pipeline, outage/restart; fakeredis остаётся в fast tests.
- RabbitMQ 4-compatible container с management/Prometheus plugins only where inspected. Все saga services в одном test vhost; queue names содержат run ID или очищаются. Проверять durable exchange/queues, confirms, mandatory return, redelivery and consumer restart.
- Auth key-ring генерируется в temporary directory с active+previous Ed25519 keys; private files never enter repository/artifacts.
- Clock/UUID/random generators injectable or monkeypatched at boundaries for TTL, scheduler, promocode and deterministic assertions.
- Network faults via stoppable containers/proxy: DB disconnect at commit, Redis loss, Rabbit confirm/nack/unroutable, consumer kill after DB commit before ACK.
- Browser E2E uses isolated context/localStorage/cookies per user and two contexts for ownership. No real bank/S3/SMTP container until code actually uses one.
- Logs, DBs, queues and ports are isolated per parallel worker. Tests use polling with explicit timeout and diagnostics, never fixed long sleeps.
- Current root compose assumes external `shide-observability` network/shared databases/Redis/RabbitMQ and has port collisions. Until a dedicated test compose exists, use unique `WISHLIST_PORT`/`DROPS_PORT` overrides and provision shared infra explicitly; otherwise full-stack command is not a valid green gate.

`docker/init-infra.py` itself needs integration tests for idempotent DB/vhost creation, URL parsing (especially `//service`), retry exhaustion and safe credentials logging. `docker/entrypoint.sh` needs container smoke tests for `api`, `migrate`, `consumer`, `outbox`, `cleanup` modes and non-zero exit on migration/init failure.

## 18. Команды запуска

### Фактически существующие service suites

| Сервис | Все текущие тесты | Быстрый слой | Infrastructure слой, который уже есть |
|---|---|---|---|
| Auth | `cd auth; uv run pytest` | `uv run pytest -m "not integration"` | `AUTH_TEST_DATABASE_URL=postgresql+asyncpg://... uv run pytest -m integration` |
| Catalog | `cd catalog; uv run pytest` | та же команда; markers пока нет | добавить `uv run pytest -m integration` на migrated PG |
| Inventory | `cd inventory; uv run pytest` | `uv run pytest -m "not integration"` | `INVENTORY_DATABASE_URL=postgresql+asyncpg://... uv run pytest tests/integration -m integration` |
| Orders | `cd orders; uv run pytest` | та же команда; markers пока нет | добавить PG/Rabbit contract command |
| Payments | `cd payments; uv run pytest` | та же команда; markers пока нет | добавить PG/Rabbit contract command |
| Notifications | `cd notifications; uv run pytest` | та же команда; markers пока нет | добавить PG/Rabbit contract command |
| Wishlist | `cd wishlist; uv run pytest` | та же команда | добавить migrated PG command |
| Drops | `cd drops; uv run pytest` | та же команда | добавить migrated PG/Rabbit/scheduler command |

PowerShell-команда для всех текущих быстрых suites из корня:

```powershell
$services = 'auth','catalog','inventory','orders','payments','notifications','wishlist','drops'
foreach ($service in $services) {
  Push-Location $service
  uv run pytest -m "not integration"
  if ($LASTEXITCODE -ne 0) { Pop-Location; exit $LASTEXITCODE }
  Pop-Location
}
```

Root saga после запуска исправленного full stack:

```powershell
uv run --project inventory pytest tests -m integration
```

Текущий stack можно попытаться поднять только после готовности external network/infra и устранения конфликтов портов/vhost; временный port workaround не исправляет RabbitMQ isolation:

```powershell
$env:WISHLIST_PORT='4924'
$env:DROPS_PORT='4925'
docker compose up -d --build
uv run --project inventory pytest tests -m integration
```

Frontend после добавления test runner: `cd frontend; npm ci; npm run test` для component tests, `npm run test:e2e` для browser tests, `npm run build` для smoke. Сейчас существуют только `npm run dev`, `npm run build`, `npm run preview`.

### Разделение быстрых и инфраструктурных тестов

- Fast PR (<5 минут): unit/domain/schema, use cases with fakes, ASGI API shape/error tests, frontend component tests; no Docker, no retries/time sleeps.
- Infrastructure PR (<15 минут): PostgreSQL migrations/repositories/concurrency, real Redis, individual publisher/consumer with RabbitMQ, Nginx routing, production build smoke.
- Contract: can run parallel to infrastructure; producer fixtures checked by every consumer and compatibility snapshots versioned in repository.
- Full E2E (<20 минут): containers for all services and one shared Rabbit vhost; serialized where global resources remain; success/failure/recovery flows.
- Nightly/load: high concurrency reservations/promocodes/payment idempotency, broker/DB restarts, cleanup/retention, soak scheduler. P0 smoke E2E still runs on every main/deploy candidate, not only nightly.

## 19. Требования к CI

1. Добавить required test workflows для Drops, Wishlist, Gateway и Frontend; root E2E/contract job должен зависеть от successful images/migrations.
2. Существующие `ruff`/`mypy` jobs помечены warning/`continue-on-error`; для изменяемого сервиса сделать lint/type/test required gates или документировать временный debt budget.
3. Не поднимать PostgreSQL впустую: fast job использует SQLite, отдельный PG job получает правильный env и запускает migration+integration markers. Все восемь services обязаны иметь fresh-migration smoke.
4. Поднять один RabbitMQ test vhost для связанной saga, а не service-isolated vhosts; отдельные queues остаются service-owned. До тестов проверять topology contract.
5. Matrix по сервисам: `uv sync --locked --all-groups`, fast tests, coverage; cache по соответствующему `uv.lock`. Frontend: `npm ci`, component tests, build.
6. Contract job публикует canonical messages и прогоняет consumers с duplicate/malformed/out-of-order cases. Failure оставляет broker/consumer logs и DB snapshot metadata.
7. E2E всегда применяет Alembic, ждёт `/health/ready` с HTTP status, создаёт пользователя через Auth, не подставляет случайный user UUID, использует polling для eventual state и проверяет stock/order/payment/notification/outbox.
8. Migration job проверяет upgrade from previous revision with representative data; downgrade только для revisions, заявленных reversible. Model/schema drift блокирует merge.
9. Tests must be deterministic: fixed seed/time, isolated ports/vhosts/databases, retries only around readiness/eventual assertions, automatic cleanup even on failure.
10. Publish JUnit, coverage XML/HTML, OpenAPI/contract diff, container logs. Secrets/tokens/cookies/private keys должны редактироваться перед artifacts.
11. Deploy не запускается, если P0 fast/infrastructure/contract/E2E gate упал. Flaky tests не перезапускаются молча; quarantine требует owner, issue and expiry.

## 20. Definition of Done по микросервисам

| Микросервис | Definition of Done |
|---|---|
| Auth | Все AUTH P0/P1; JWT/CSRF/RBAC/revocation/Redis failure green; PG races green; CLI/cleanup/migrations/outbox recovery green; no secret leakage. |
| Catalog | Все CAT P0/P1; brand/category/product/variant API and ownership; PostgreSQL FTS/filter/constraints/migrations; concurrency and visibility green. |
| Inventory | Все INV P0/P1; stock invariant under reset/reserve/expire/variant concurrency; correct saga correlation; consumer duplicate-safe; outbox retries; internal access protected. |
| Orders | Все ORD P0/P1; trusted reservation, one order per reservation, exact money/promo limits, legal duplicate-safe transitions, PG/Rabbit recovery and ownership. |
| Payments | Все PAY P0/P1 for mock scope; one pending attempt under race, trusted amount/state transitions, exact events and recovery, owner access. |
| Notifications | Все NOT P0/P1 for persistence/mock-delivery scope; order events deduped, state semantics agreed with frontend, ownership/privacy/outbox recovery/migrations green. |
| Wishlist | Все WISH P0/P1; owner binding, limit and duplicate race proof, product lifecycle policy, PG migrations/readiness green. |
| Drops | Все DROP P0/P1; protected and correctly routed admin API, full state matrix, concurrent scheduler exactly-once effect, event contracts/outbox recovery, public visibility. |

## 21. Общий Definition of Done проекта

Проект можно признать рабочим, когда:

- все P0 и P1 строки этого плана реализованы и зелёные; P2 имеют owner/решение;
- восемь services стартуют с чистых migrated PostgreSQL databases; gateway/frontend доступны без port conflicts;
- все saga producers/consumers используют совместимый exchange/vhost и versioned schemas;
- authenticated happy purchase заканчивается `Order CONFIRMED`, `Payment SUCCESS`, `Reservation COMMITTED`, `reserved=0`, `sold+=qty`, notification создана один раз;
- payment failure/cancel/expiry приводит к согласованной компенсации: order terminal state, reservation released exactly once, available restored, notification one time;
- duplicate/out-of-order messages, client retries and process restarts не создают duplicate business effects;
- owner/admin/internal access matrix закрывает cross-user and public mutation paths;
- readiness реально отражает обязательные зависимости, а deploy blocked on unhealthy service;
- full-stack P0 E2E, contract, migration and security suites are required CI checks;
- документация/commands/OpenAPI соответствуют найденным восьми сервисам и фактическим routes.

## 22. Рекомендуемые минимальные пороги coverage

Coverage — только страховочная метрика после выполнения сценарной матрицы:

| Компонент | Line | Branch | Дополнительное правило |
|---|---:|---:|---|
| Auth | 90% | 85% | 100% application error/state classes и security decision branches |
| Inventory, Orders, Payments | 90% | 85% | 100% state transitions, invariants, consumer handlers and outbox branches |
| Catalog, Drops, Notifications, Wishlist | 85% | 80% | 100% public handlers/domain error mappings and scheduler paths |
| Gateway config tests | N/A | N/A | 100% declared path/subdomain locations exercised |
| Frontend | 80% | 75% | 100% api refresh, checkout compensation, payment and auth state branches |

Не разрешать падение coverage относительно main и не исключать из отчёта consumers/workers/routes. Достижение процента без всех P0/P1 сценариев не удовлетворяет Definition of Done.

## 23. Контрольный реестр фактических точек входа

Реестр ниже получен повторной сверкой `include_router` и route decorators; он нужен как checklist, чтобы при реализации матрицы не потерять маршрут из-за группировки сценариев. Служебные `/docs`, `/redoc` и `/openapi.json`, автоматически создаваемые FastAPI в debug/non-production configuration, не считаются бизнес-функциями.

| Компонент | Фактические HTTP-точки входа | Не-HTTP entrypoints |
|---|---|---|
| Auth | `POST /auth/{register,login,refresh,introspect,logout}`; `GET/PATCH /users/me`; `POST /users/me/password`; `GET/DELETE /sessions`, `DELETE /sessions/{session_id}`; `GET /admin/users`; `PATCH /admin/users/{user_id}/{role,status}`; `GET /admin/audit-events`; те же business routers также подключены под `/api/v1`; `GET /.well-known/jwks.json`; `GET /health/{live,ready}`; `GET /metrics` | outbox worker; expired-session cleanup CLI/module; `create-admin`; Ed25519 key generation |
| Catalog | `POST/GET /api/v1/categories`; `POST/GET /api/v1/brands`; `GET /api/v1/brands/{slug_or_id}`; `POST/GET /api/v1/products`; `GET /api/v1/products/{slug}`; `PATCH/DELETE /api/v1/products/{product_id}`; `POST/GET /api/v1/products/{product_id}/variants/`; `GET/PATCH/DELETE /api/v1/products/{product_id}/variants/{variant_id}`; `GET /health/ready`; `GET /metrics` | нет фонового процесса |
| Inventory | `POST /api/v1/stocks`; `GET/PATCH /api/v1/stocks/{product_id}`; `POST /api/v1/stocks/{product_id}/{reserve,commit,release}`; `GET /health/ready`; `GET /metrics` | Rabbit consumer; outbox worker |
| Orders | `POST /api/v1/orders`; `GET /api/v1/orders/{order_id}`; `GET /api/v1/orders/users/{user_id}`; `POST /api/v1/orders/{order_id}/{confirm,fail}`; `POST/GET /api/v1/promocodes/`; `GET/PATCH /api/v1/promocodes/{promo_id}`; `POST /api/v1/promocodes/validate`; `GET /health/ready`; `GET /metrics` | Rabbit consumer; outbox worker; application-level `cancel_order` не имеет HTTP route |
| Payments | `POST /api/v1/payments`; `GET /api/v1/payments/{payment_id}`; `GET /api/v1/payments/users/{user_id}`; `POST /api/v1/payments/{payment_id}/{confirm,fail,cancel}`; `GET /health/ready`; `GET /metrics` | Rabbit consumer; outbox worker |
| Notifications | `POST /api/v1/notifications`; `GET /api/v1/notifications/{notification_id}`; `GET /api/v1/notifications/users/{user_id}`; `POST /api/v1/notifications/{notification_id}/send`; `POST /api/v1/notifications/{notification_id}/fail`; `GET /health/ready`; `GET /metrics` | Rabbit consumer; outbox worker |
| Wishlist | `POST /api/v1/wishlist/users/{user_id}/items`; `DELETE /api/v1/wishlist/users/{user_id}/items/{product_id}`; `GET /api/v1/wishlist/users/{user_id}/items`; `POST /api/v1/wishlist/users/{user_id}/check`; `GET /health/ready`; `GET /metrics` | нет фонового процесса |
| Drops | `GET /api/v1/drops/{active,upcoming}`; `GET /api/v1/drops/{slug}`; `POST/GET /api/v1/admin/drops/`; `GET/PATCH /api/v1/admin/drops/{drop_id}`; `POST /api/v1/admin/drops/{drop_id}/{schedule,start,end,cancel}`; `POST /api/v1/admin/drops/{drop_id}/items`; `DELETE /api/v1/admin/drops/{drop_id}/items/{product_id}`; `GET /health/ready`; `GET /metrics` | scheduler; outbox worker |
| Gateway | `GET /health`; reverse-proxy locations для `/api/v1/*`, прямых Auth prefixes, `/.well-known/*`, `/prometheus`, `/nginx_status`; host-based routes `api.*`, `auth.*`, `catalog.*`, `inventory.*`, `orders.*`, `payments.*`, `notifications.*`, `wishlist.*`, `drops.*`; `/` обслуживает Frontend | Nginx exporter; Docker healthcheck |
| Frontend | SPA routes `/`, `/catalog`, `/product/:slug`, `/login`, `/register`, `/profile`, `/orders`, `/wishlist`, `/drops`, `/drops/:slug`, `/admin/*`; вызовы Auth, Catalog, Inventory, Orders, Payments, Notifications, Wishlist и Drops через общий API client | Vite build; Nginx static serving и SPA fallback |

Отдельно проверены инфраструктурные entrypoints: восемь Alembic trees, общий `docker-entrypoint.sh` с `migrate/api/worker`, `scripts/seed.py`, корневые saga E2E tests и Compose healthchecks. S3, Redis вне Auth, реальные PSP/email/SMS/push providers и отдельный background worker у Catalog/Wishlist в коде не обнаружены и потому в матрицу не добавлены.

## 24. Финальная трассировочная сверка репозитория

Учтены все найденные runtime entrypoints: 8 FastAPI apps; Auth outbox/cleanup/CLI/keygen; Inventory/Orders/Payments/Notifications consumers+outbox; Drops scheduler+outbox; Inventory expiry endpoint; health/metrics/JWKS; Nginx gateway and exporter; frontend Nginx/SPA; init/migrate entrypoint; seed script; 2 root saga tests. Catalog, Wishlist не имеют background process; Auth не имеет consumer; Drops events и Auth events не имеют consumers; S3 и реальные payment/delivery APIs отсутствуют. Новые вымышленные сервисы или endpoints в план не добавлены.
