# FlashMarket — Идеи, улучшения и технические решения

> Собранные бизнес-идеи, технические улучшения и новые решения для развития платформы.
> Приоритеты: 🔴 высокий · 🟡 средний · 🟢 низкий

---

## 1. Бизнес-функции

### 🔴 Интеграция с реальными платёжными системами

Сейчас payments — mock-сервис. Для монетизации нужна реальная интеграция.

**Кандидаты:**
- **ЮKassa** (Яндекс) — лидер рынка РФ, поддержка банковских карт, SBP, Apple/Google Pay
- **CloudPayments** — быстрая интеграция, рекуррентные платежи
- **Stripe** — для международного рынка
- **Тинькофф Acquiring** — низкие комиссии, SBP

**Реализация:**
- Adapter pattern в Payments service: `PaymentProvider` интерфейс → `YooKassaProvider`, `StripeProvider`
- Webhook endpoint для callback от провайдера
- Idempotency key для безопасных retry
- PCI DSS: токенизация на стороне провайдера, не хранить карточные данные

---

### 🔴 Wishlist / Избранное

Пользователи хотят сохранять товары для будущих покупок.

- Отдельная таблица `wishlists` в Auth или новый микросервис
- API: `POST/DELETE /api/v1/wishlist/{product_id}`, `GET /api/v1/wishlist`
- Уведомление когда wishlist-товар появляется в дропе
- Frontend: сердечко на карточке товара

---

### 🔴 Система дропов (Flash Sales)

Ключевая фича платформы, пока не реализована как отдельная сущность.

**Модель:**
- `Drop` — сущность: название, время начала/конца, список товаров, статус
- Countdown timer на фронте
- Автоматическое открытие/закрытие по расписанию (cron job или scheduled task)
- `DropService` — управление жизненным циклом
- Push/email уведомление за N минут до старта дропа

**Геймификация:**
- Очередь входа (queue system) при высокой нагрузке
- Лимит на количество товаров в одни руки
- Таймер на оплату (5 минут)

---

### 🟡 Промокоды и скидки

- `PromocodeService` — отдельный микросервис или модуль в Orders
- Типы: фиксированная сумма, процент, бесплатная доставка
- Ограничения: количество использований, срок действия, минимальная сумма
- Реферальные промокоды

---

### 🟡 Отзывы и рейтинги

- Отдельный `Reviews` микросервис
- Только покупатели (verified purchase) могут оставить отзыв
- Модерация: auto-approve или manual
- Средний рейтинг кешируется в Catalog

---

### 🟡 Система доставки

- Интеграция с СДЭК, Boxberry, Почтой России
- Расчёт стоимости по API
- Трекинг номер в заказе
- Webhook обновления статуса доставки

---

### 🟡 Размеры и варианты товаров (SKU)

Сейчас товар — это один артикул. Для одежды нужны:
- `ProductVariant`: размер (S, M, L, XL), цвет
- Сток привязан к варианту, не к продукту
- Фильтрация по размеру
- Таблица размеров

---

### 🟢 Подписка на уведомления

- Email подписка на новые дропы
- Telegram bot для уведомлений
- Push notifications (Web Push API)
- Подписка на конкретную категорию или бренд

---

### 🟢 Лоялити-программа

- Баллы за покупки
- Уровни: Bronze → Silver → Gold → Platinum
- Ранний доступ к дропам для высоких уровней
- Эксклюзивные товары

---

### 🟢 Мультиязычность

- i18n на фронте (react-intl или i18next)
- Мультиязычные описания товаров в Catalog
- Локализация email-уведомлений

---

## 2. Технические улучшения

### 🔴 Кеширование (Redis)

Сейчас Redis используется только Auth. Добавить:

- **Catalog:** кеш категорий (дерево редко меняется), кеш популярных товаров
- **Inventory:** кеш текущих остатков для быстрого чтения (invalidate при изменении)
- **Gateway-level:** кеш статических ответов (nginx proxy_cache)

**Стратегия:**
- Write-through для критичных данных (остатки)
- Cache-aside для каталога
- TTL 30-60с для горячих данных, 5-10 мин для каталога

---

### 🔴 Полнотекстовый поиск

ILIKE `%query%` не масштабируется. Варианты:

1. **PostgreSQL Full-Text Search** — `tsvector`, `tsquery`, GIN индексы
   - Минимум инфраструктуры, уже есть PostgreSQL
   - Поддержка русского языка через `russian` dictionary
   - `ts_rank` для ранжирования

2. **Meilisearch** — молниеносный поиск с typo-tolerance
   - Отдельный контейнер, sync через events
   - Фасетная фильтрация из коробки
   - Отлично для UX

3. **Elasticsearch / OpenSearch**
   - Enterprise-grade, но тяжеловесный для текущего масштаба

**Рекомендация:** Начать с PostgreSQL FTS, мигрировать на Meilisearch при росте каталога.

---

### 🔴 WebSocket для реального времени

Flash-sale требует real-time обновлений:

- Обновление остатков в реальном времени (сколько осталось)
- Countdown timer синхронизация
- Уведомления о статусе заказа
- LiveKit или Socket.IO для фронтенда

**Реализация:**
- Отдельный WebSocket gateway или sidecar
- Redis Pub/Sub для broadcast между инстансами
- Каналы: `stock:{product_id}`, `order:{order_id}`, `user:{user_id}`

---

### 🔴 API versioning и OpenAPI documentation

- Swagger UI уже есть per-service, но нет единого API portal
- Добавить API Gateway уровень OpenAPI spec
- Swagger UI на `/docs` за аутентификацией
- Версионирование: `/api/v2/` для breaking changes

---

### 🟡 Авторизация в микросервисах (authZ)

Сейчас Auth проверяет JWT, но authZ (permission check) не формализован.

**Предложения:**
- Shared JWT middleware library (Python package) для всех сервисов
- `@require_role("ADMIN")`, `@require_authenticated` декораторы
- RBAC: roles → permissions mapping
- Каждый сервис проверяет JWT локально через JWKS + introspection при необходимости

---

### 🟡 API Rate Limiting на Gateway

Сейчас rate limiting только в Auth. Нужно на уровне gateway:

- nginx `limit_req_zone` по IP
- Разные лимиты для разных path prefix
- Burst capacity для flash-sale
- Custom header `X-RateLimit-Remaining`

---

### 🟡 Database per service (отдельные PostgreSQL инстансы)

Сейчас один PostgreSQL с разными базами. При росте:

- Разнести на отдельные PostgreSQL инстансы
- Connection pooling (PgBouncer)
- Read replicas для каталога
- Возможность независимого масштабирования

---

### 🟡 Structured Logging и Tracing

- **OpenTelemetry** — distributed tracing через все сервисы
- Correlation ID (request_id) уже есть, нужно пробросить через RabbitMQ
- **Loki** или **Elasticsearch** для централизованных логов
- **Jaeger** / **Tempo** для trace visualization
- Trace context propagation через HTTP headers и AMQP headers

---

### 🟡 Graceful Degradation

- Circuit breaker pattern (tenacity или pybreaker)
- Fallback при недоступности Redis (Auth уже делает fail closed)
- Bulkhead: отдельные thread pools для критичных операций
- Retry с jitter для RabbitMQ reconnection

---

### 🟡 Database Connection Pooling

- Внешний PgBouncer перед PostgreSQL
- Или asyncpg pool tuning: `min_size`, `max_size`, `max_idle_timeout`
- Мониторинг connection pool health

---

### 🟡 Dead Letter Queue (DLQ)

- RabbitMQ DLQ для failed messages
- Retry policy: 3 attempts → DLQ
- Admin UI для просмотра и retry failed messages
- Alerting при накоплении DLQ

---

### 🟢 GraphQL Gateway

- Apollo Federation или Strawberry (Python)
- Единый GraphQL endpoint для фронта
- Schema stitching из OpenAPI specs сервисов
- Batching и caching на уровне gateway

---

### 🟢 gRPC для межсервисного взаимодействия

- gRPC вместо HTTP для internal API calls
- Protobuf schemas для строгой типизации
- Бинарный протокол = меньше overhead
- Streaming для push-обновлений

---

### 🟢 Feature Flags

- LaunchDarkly или self-hosted (Unleash, Flagsmith)
- Canary releases: 5% трафика на новую версию
- A/B тестирование на уровне UI
- Kill switch для проблемных фич

---

## 3. DevOps и инфраструктура

### 🔴 Kubernetes миграция

Текущий deploy — Docker Compose на одном сервере. При росте:

- **Helm charts** для каждого сервиса
- **HPA** (Horizontal Pod Autoscaler) — автоскейлинг при нагрузке
- **Namespace** isolation: `flashmarket-prod`, `flashmarket-staging`
- **Ingress controller** вместо Nginx Gateway
- **Managed PostgreSQL** (Yandex Cloud, AWS RDS)
- **Managed Redis** (Yandex Cloud Managed Redis, AWS ElastiCache)

---

### 🔴 Staging Environment

- Отдельный staging сервер для тестирования перед production
- Автоматический deploy из `develop` ветки
- Seed data для staging
- Smoke tests после deploy

---

### 🟡 Blue-Green / Canary Deployments

- Текущий deploy — простой restart, есть downtime
- Blue-green: два инстанса, переключение через nginx upstream
- Canary: weighted routing 90/10

---

### 🟡 Backup Strategy

- Automated PostgreSQL backups (pg_dump или WAL-G)
- S3-compatible storage для бекапов
- Point-in-time recovery
- Redis RDB/AOF persistence настройка
- Backup testing (restore verification)

---

### 🟡 Secret Management

- Сейчас секреты в GitHub Secrets + `.env`
- HashiCorp Vault или Yandex Lockbox
- Rotation policy для database credentials
- JWT keys в KMS вместо Docker volume

---

### 🟡 Container Security

- Trivy scan Docker images в CI
- Non-root users (уже сделано ✓)
- Read-only rootfs
- Security contexts в Kubernetes
- Dependabot для dependency updates

---

### 🟢 CDN для статики

- Frontend bundle через CDN (CloudFlare, Yandex CDN)
- Картинки товаров через CDN с image optimization
- S3 для user-uploaded content
- Cache headers optimization

---

### 🟢 Load Testing

- k6 или Locust для нагрузочного тестирования
- Сценарий flash-sale: 1000 concurrent users, 100 единиц товара
- Определить bottlenecks: DB locks, connection pool exhaustion
- SLA: p99 < 200ms для checkout flow

---

## 4. Frontend улучшения

### 🔴 SSR / SSG

- Next.js или Remix вместо чистого React SPA
- SEO: server-side rendering для product pages
- Мета-теги для Open Graph (preview в соц. сетях)
- Static generation для каталога (ISR — Incremental Static Regeneration)

---

### 🔴 PWA (Progressive Web App)

- Service Worker для offline browsing каталога
- Push notifications через Web Push API
- Install prompt (добавить на домашний экран)
- Оптимизация для мобильных: 3G/4G

---

### 🟡 Skeleton Loading

- Skeleton screens вместо спиннеров
- Optimistic UI updates
- Prefetch данных при hover на ссылку

---

### 🟡 Image Optimization

- Lazy loading изображений (Intersection Observer)
- WebP/AVIF форматы
- Responsive images (`srcset`)
- Blurhash placeholder
- Image upload service с resize/crop

---

### 🟡 State Management

- Zustand или Jotai вместо Context API (если состояние растёт)
- React Query / TanStack Query для серверного кеша
- Offline-first с background sync

---

### 🟢 Storybook

- Component library документация
- Visual regression testing
- Design system as code

---

### 🟢 E2E тесты фронтенда

- Playwright или Cypress
- Critical path: browse → add to cart → checkout → payment
- Visual regression с Percy или Chromatic
- Accessibility тесты (axe-core)

---

## 5. Аналитика и мониторинг

### 🔴 Бизнес-аналитика

- Conversion funnel: visit → product view → add to cart → checkout → payment
- Метрики: GMV, AOV, conversion rate, cart abandonment rate
- Дашборд для админов с ключевыми метриками
- Event tracking: Amplitude, Mixpanel или self-hosted (Posthog)

---

### 🟡 Alerting

- Prometheus Alertmanager
- Slack/Telegram уведомления при:
  - Сервис упал (health check failed)
  - Error rate > 5%
  - Response time p99 > 500ms
  - DLQ accumulation
  - Low disk space
  - Certificate expiration

---

### 🟡 SLI/SLO

- Определить Service Level Indicators:
  - Availability: 99.9%
  - Latency: p50 < 50ms, p99 < 200ms
  - Error rate: < 0.1%
- Дашборд соблюдения SLO
- Error budget policy

---

## 6. Потенциальные дополнительные сервисы

| Сервис | Назначение |
|---|---|
| **Upload Service** | Загрузка и обработка изображений, S3 storage |
| **Search Service** | Meilisearch wrapper с sync из Catalog events |
| **Email Service** | Реальная отправка email (SendGrid, Mailgun) |
| **SMS Service** | Отправка SMS (Twilio, SMS Aero) |
| **Analytics Service** | Сбор и обработка бизнес-событий |
| **Admin BFF** | Backend-for-Frontend для админ-панели |
| **Recommendation Service** | ML-based рекомендации ("с этим покупают") |
| **Audit Service** | Централизованный audit log из всех сервисов |
| **Scheduler Service** | Cron-like задачи: дропы, экспирация, отчёты |

---

## 7. Quick Wins (можно сделать быстро)

1. ✅ **Swagger UI** — уже есть per-service, собрать единый portal
2. 🔧 **Health dashboard** — простая страница со статусами всех сервисов
3. 🔧 **Docker Compose profiles** — `docker compose --profile monitoring up`
4. 🔧 **Makefile / Taskfile** — единые команды: `make dev`, `make test`, `make deploy`
5. 🔧 **Pre-commit hooks** — ruff + mypy перед коммитом
6. 🔧 **`.env` validation** — pydantic-settings уже валидирует, добавить в CI
7. 🔧 **API client SDK** — автогенерация TypeScript клиента из OpenAPI spec
8. 🔧 **Hot reload для фронта в Docker** — volume mount `src/` в dev mode
9. 🔧 **Dependabot** — автоматическое обновление Python/JS зависимостей
10. 🔧 **Changelog** — автоматический CHANGELOG.md из conventional commits
