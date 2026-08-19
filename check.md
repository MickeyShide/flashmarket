# Production-ready backend checklist для Flashmarket

Это можно использовать как **реальный чек-лист зрелости проекта**, а не как список технологий ради технологий.

Обозначения:

* **P0** — без этого я бы не называл систему production-ready.
* **P1** — должно быть в серьёзном production-проекте.
* **P2** — следующий уровень зрелости; зависит от нагрузки и требований.

Для pet-проекта уровня Flashmarket хорошая цель: **закрыть почти все P0 и большую часть P1**, а P2 реализовывать выборочно там, где это действительно демонстрирует инженерную глубину.

---

# 1. Архитектура системы

* [x] **P0** У каждого микросервиса есть чёткая ответственность.
* [x] **P0** Нет сервисов типа `common-service`, который постепенно становится свалкой.
* [x] **P0** Понятно, какие данные принадлежат какому сервису.
* [x] **P0** Сервисы не ходят напрямую в таблицы друг друга.
* [x] **P0** Межсервисное взаимодействие происходит через явные API/events.
* [x] **P0** Нет циклических зависимостей между сервисами без серьёзного обоснования.
* [x] **P0** Определены основные synchronous flows.
* [x] **P0** Определены основные asynchronous flows.
* [x] **P0** Понятны transaction boundaries.
* [x] **P0** Понятны consistency boundaries.
* [x] **P0** Для каждого важного бизнес-процесса определён source of truth.
* [x] **P1** Есть архитектурная диаграмма.
* [x] **P1** Есть sequence diagrams для критичных flows.
* [x] **P1** Архитектурные решения зафиксированы в ADR или аналогичном формате.
* [x] **P1** Реализован принцип минимальной связанности сервисов.
* [x] **P1** Есть явные публичные и внутренние interfaces.
* [x] **P1** Нет shared database как скрытой связи микросервисов.
* [x] **P2** Есть versioning архитектурных контрактов.
* [x] **P2** Описаны допустимые зависимости между слоями приложения.

---

# 2. Конфигурация

* [x] **P0** Конфигурация отделена от кода.
* [x] **P0** Secrets не лежат в git.
* [x] **P0** Есть `.env.example`.
* [x] **P0** Production secrets не имеют небезопасных default values.
* [x] **P0** Приложение не запускается с дефолтным JWT secret.
* [x] **P0** Конфигурация валидируется при startup.
* [x] **P0** Невалидная конфигурация приводит к fail-fast.
* [x] **P0** Разделены dev/test/prod environments.
* [x] **P1** Настройки представлены типизированными объектами.
* [x] **P1** Есть явные defaults только для безопасных параметров.
* [x] **P1** Конфигурация worker и API согласована.
* [x] **P1** Все timeout/retry/TTL configurable.
* [x] **P1** Логирование конфигурации не раскрывает secrets.
* [ ] **P2** Secrets приходят из secret manager.
* [ ] **P2** Есть ротация секретов без пересборки приложения.

---

# 3. API

* [x] **P0** API имеет versioning, например `/api/v1`.
* [x] **P0** Все endpoints имеют корректные HTTP methods.
* [x] **P0** Корректно используются `200`, `201`, `204`, `400`, `401`, `403`, `404`, `409`, `422`, `429`, `5xx`.
* [x] **P0** Validation происходит до выполнения бизнес-логики.
* [x] **P0** Клиент не может передавать серверные поля вроде `owner_id`, если не должен.
* [x] **P0** Ошибки возвращаются в едином формате.
* [x] **P0** Internal stack trace не уходит клиенту.
* [x] **P0** Pagination ограничена максимальным размером страницы.
* [x] **P0** Нет endpoints, которые могут случайно вернуть миллионы строк.
* [x] **P0** Неавторизованные действия защищены.
* [x] **P0** Проверяется ownership ресурсов.
* [x] **P1** OpenAPI документация соответствует реальному поведению.
* [x] **P1** Request/response schemas не завязаны напрямую на ORM models.
* [x] **P1** Ошибки имеют machine-readable error codes.
* [x] **P1** Определена политика backward compatibility.
* [x] **P1** PATCH действительно частичный.
* [x] **P1** PUT семантически соответствует полной замене, если используется.
* [x] **P1** Есть ограничения длины строк и коллекций.
* [x] **P1** Есть защита от чрезмерно больших request bodies.
* [x] **P1** Есть request timeout.
* [x] **P2** Есть contract testing между сервисами.
* [ ] **P2** Есть API deprecation policy.

---

# 4. Authentication

* [x] **P0** Пароли хранятся только как безопасный hash.
* [x] **P0** Используется современный password hashing algorithm.
* [x] **P0** Password verification не блокирует async event loop.
* [x] **P0** Access token имеет expiration.
* [x] **P0** Refresh token имеет expiration.
* [x] **P0** Refresh token нельзя бесконечно использовать повторно, если архитектура предполагает rotation.
* [x] **P0** Logout действительно инвалидирует нужную сессию.
* [x] **P0** Заблокированный пользователь не может продолжать использовать активную сессию, если это требование системы.
* [x] **P0** Проверяются `iss`, `aud`, `exp` JWT, если они используются.
* [x] **P0** Секрет подписи достаточно сильный.
* [x] **P0** Нет user enumeration через разные ответы login endpoint.
* [x] **P0** Login защищён rate limiting.
* [x] **P1** Refresh token rotation.
* [x] **P1** Detection refresh token reuse.
* [x] **P1** Можно отозвать отдельную сессию.
* [x] **P1** Можно отозвать все сессии пользователя.
* [x] **P1** Ведётся security audit login/logout/reset.
* [x] **P2** Поддерживаются key rotation/JWKS, если действительно нужно.

---

# 5. Authorization

* [x] **P0** Authentication и authorization не смешаны.
* [x] **P0** Роли проверяются на backend.
* [x] **P0** Admin endpoints нельзя открыть обычному пользователю.
* [x] **P0** Проверяется ownership каждой пользовательской сущности.
* [x] **P0** Нельзя изменить `user_id` в request и получить доступ к чужому объекту.
* [x] **P0** Нет IDOR.
* [x] **P0** Permission checks выполняются до side effects.
* [x] **P1** RBAC централизован, а не раскидан хаотично по роутерам.
* [x] **P1** Есть тесты horizontal privilege escalation.
* [x] **P1** Есть тесты vertical privilege escalation.

---

# 6. PostgreSQL — общая корректность

* [x] **P0** Schema создаётся только migrations.
* [x] **P0** ORM models и migrations синхронизированы.
* [x] **P0** Есть PK у всех основных таблиц.
* [x] **P0** FK используются там, где важна referential integrity.
* [x] **P0** `NOT NULL` стоит там, где `NULL` не является допустимым состоянием.
* [x] **P0** Есть UNIQUE constraints для реально уникальных сущностей.
* [x] **P0** Есть CHECK constraints для критичных invariants.
* [x] **P0** Денежные значения не хранятся как binary float.
* [x] **P0** Datetime хранится консистентно.
* [x] **P0** Есть понятная политика UTC.
* [x] **P0** Нет implicit autocommit, нарушающего бизнес-транзакции.
* [x] **P0** Ошибка приводит к rollback.
* [x] **P1** Foreign keys имеют нужное поведение `ON DELETE`.
* [x] **P1** Нет случайных cascade deletes.
* [x] **P1** Все большие таблицы имеют подходящие indexes.
* [x] **P1** Нет очевидно дублирующих indexes.
* [x] **P1** Query plans проверены для нескольких критичных запросов.
* [x] **P1** Нет `SELECT *` в горячих запросах без необходимости.
* [ ] **P2** Есть регулярный анализ slow queries.
* [ ] **P2** Настроен `pg_stat_statements`.

---

# 7. Транзакции

* [x] **P0** Каждый критичный use case имеет понятную transaction boundary.
* [x] **P0** Связанные изменения состояния выполняются одной transaction.
* [x] **P0** Не происходит commit посередине операции без необходимости.
* [x] **P0** Не происходит commit в repository без явной архитектурной причины.
* [x] **P0** При exception transaction откатывается.
* [x] **P0** Нельзя получить partially persisted business operation.
* [x] **P0** Outbox INSERT и business UPDATE находятся в одной transaction, если используется transactional outbox.
* [x] **P1** Долгие network calls не выполняются внутри DB transaction без причины.
* [x] **P1** Понятно, какие isolation assumptions использует код.
* [x] **P1** Retry транзакций не вызывает повторный внешний side effect.
* [ ] **P2** Deadlock scenarios анализировались.

---

# 8. Concurrency

* [x] **P0** Проанализированы read-modify-write операции.
* [x] **P0** Stock нельзя увести ниже нуля.
* [x] **P0** Последний товар нельзя продать двум людям.
* [x] **P0** Один reservation нельзя освободить дважды с неправильным изменением stock.
* [x] **P0** Один order нельзя оплатить дважды.
* [x] **P0** Один refund нельзя выполнить дважды.
* [x] **P0** Critical counters обновляются атомарно.
* [x] **P0** Нельзя создать duplicate entity из двух concurrent requests.
* [x] **P0** DB constraints являются последней линией защиты там, где возможно.
* [x] **P0** Используемый locking работает между несколькими процессами и instances.
* [x] **P1** Есть concurrency integration tests.
* [x] **P1** Проверены race conditions на 10–100 параллельных операциях.
* [x] **P1** Row locks не захватываются на слишком большой период.
* [x] **P1** Lock ordering не создаёт очевидных deadlocks.
* [ ] **P2** Проведено нагрузочное тестирование contention hotspots.

---

# 9. Inventory

* [x] **P0** Stock не становится отрицательным.
* [x] **P0** `available`, `reserved`, `sold` не расходятся между собой.
* [x] **P0** Reservation создаётся атомарно со списанием доступного остатка.
* [x] **P0** Reservation имеет однозначный lifecycle.
* [x] **P0** Повторный reserve request имеет определённое поведение.
* [x] **P0** Release reservation идемпотентен.
* [x] **P0** Commit reservation идемпотентен.
* [x] **P0** Expired reservation нельзя затем случайно успешно commit.
* [x] **P0** Нет двойного возврата stock.
* [x] **P0** Если cleanup worker выполняется повторно, stock остаётся корректным.
* [x] **P1** Reservation имеет `expires_at`.
* [x] **P1** Есть индекс для поиска истёкших reservations.
* [x] **P1** Expiration не зависит от клиентских часов.
* [x] **P1** Есть тест `stock=1 + N concurrent reservations`.
* [x] **P1** Есть reconciliation механизм хотя бы административного уровня.
* [x] **P2** Есть механизм защиты от hot SKU contention.

---

# 10. Drops / flash sale

* [x] **P0** Drop имеет серверное время начала.
* [x] **P0** До начала drop нельзя купить товар.
* [x] **P0** После завершения нельзя создать новый reserve.
* [x] **P0** Высокая конкурентность на старте не ломает inventory.
* [x] **P0** Нельзя обойти ограничения прямым API request.
* [x] **P0** Ограничение покупки на пользователя enforce'ится backend.
* [x] **P1** Есть protection от duplicate purchase.
* [x] **P1** Start/end transitions идемпотентны.
* [x] **P1** Планировщик может безопасно выполнить одну операцию несколько раз.
* [x] **P2** Возможно prewarming cache перед началом drop.
* [x] **P2** Hot products имеют отдельную стратегию нагрузки.

---

# 11. Orders

* [x] **P0** Order имеет явный lifecycle.
* [x] **P0** Невозможные state transitions запрещены.
* [x] **P0** Нельзя оплатить `cancelled` order.
* [x] **P0** Нельзя повторно cancel завершённый order с неправильными последствиями.
* [x] **P0** Order фиксирует фактическую цену на момент покупки.
* [x] **P0** Изменение catalog price позже не изменяет существующий order.
* [x] **P0** Клиент не определяет authoritative price.
* [x] **P0** Quantity проверяется backend.
* [x] **P0** Order creation идемпотентен там, где client retry возможен.
* [x] **P1** Есть history/state timestamps.
* [x] **P1** Есть audit критичных transitions.
* [x] **P1** Необработанные/зависшие orders можно найти.
* [x] **P2** Есть reconciliation job для inconsistent orders.

---

# 12. Payments

Если Payments есть даже как mock/service abstraction:

* [x] **P0** Payment имеет собственный lifecycle.
* [x] **P0** Payment callback/webhook идемпотентен.
* [x] **P0** Повторный webhook не создаёт второй side effect.
* [x] **P0** Нельзя доверять `amount` от клиента.
* [x] **P0** Amount сверяется с order.
* [x] **P0** Currency проверяется.
* [x] **P0** Успешный timeout scenario продуман: клиент получил timeout, а платёж прошёл.
* [x] **P0** Late payment после expiration имеет определённое поведение.
* [x] **P0** Refund идемпотентен.
* [x] **P0** Нет двойного refund.
* [x] **P0** Payment status нельзя произвольно менять API запросом.
* [ ] **P1** Provider request имеет idempotency key, если provider поддерживает.
* [ ] **P1** Есть reconciliation с payment provider.
* [ ] **P1** Webhook signature проверяется.
* [x] **P1** Есть audit payment events.
* [ ] **P2** Есть отдельная ledger/accounting модель, если финансовая сложность проекта этого требует.

---

# 13. Transactional Outbox

* [x] **P0** Event создаётся в той же transaction, что business state.
* [x] **P0** Event имеет уникальный ID.
* [x] **P0** Event хранит type.
* [x] **P0** Event хранит payload.
* [x] **P0** Есть timestamp создания.
* [x] **P0** Есть механизм pending/published или эквивалент.
* [x] **P0** Publisher переживает restart.
* [x] **P0** RabbitMQ outage не приводит к потере события.
* [x] **P0** Publish success + crash before marking published не ломает систему.
* [x] **P0** Duplicate publication допустима и безопасна.
* [x] **P0** Несколько publisher workers не ломают друг другу обработку.
* [x] **P1** Используется подходящий locking.
* [x] **P1** `SKIP LOCKED`, если архитектура polling это предполагает.
* [x] **P1** Есть batch processing.
* [x] **P1** Есть индекс под выборку pending events.
* [x] **P1** Есть retry/backoff.
* [x] **P1** Есть max attempts или обработка poison events.
* [x] **P1** Есть cleanup старых published rows.
* [x] **P1** Outbox не растёт бесконечно.
* [x] **P1** Event ordering явно определён либо явно не гарантируется.
* [ ] **P2** Есть partitioning/archive при больших объёмах.

---

# 14. RabbitMQ

* [x] **P0** Exchange существует и правильно конфигурируется.
* [x] **P0** Routing keys централизованы или хотя бы согласованы.
* [x] **P0** Queue bindings корректны.
* [x] **P0** Durable queues используются для важных сообщений.
* [x] **P0** Persistent messages используются где необходимо.
* [x] **P0** Consumer ack происходит после успешной обработки.
* [x] **P0** Failure до commit не приводит к потере сообщения.
* [x] **P0** Повторная доставка безопасна.
* [x] **P0** Consumer не бесконечно hot-requeue'ит broken message.
* [x] **P1** Настроен prefetch.
* [x] **P1** Есть retry policy.
* [x] **P1** Есть DLQ для permanent failures либо эквивалентная стратегия.
* [x] **P1** Есть dead-letter inspection/replay процесс.
* [x] **P1** Connection автоматически восстанавливается.
* [x] **P1** Broker startup dependency корректно обрабатывается.
* [x] **P1** Malformed event не убивает consumer loop.
* [x] **P1** Unknown event type обрабатывается контролируемо.
* [x] **P1** Есть event schema/version.
* [x] **P2** Метрики queue depth.
* [x] **P2** Alert на растущий backlog.
* [x] **P2** Alert на DLQ.

---

# 15. Idempotent consumers

* [x] **P0** Все критичные consumers предполагают возможность duplicate delivery.
* [x] **P0** Есть unique event ID.
* [x] **P0** Повторная обработка не создаёт повторный business effect.
* [x] **P0** Deduplication race-safe.
* [x] **P0** `SELECT if exists → INSERT` не является единственной защитой без DB constraint.
* [x] **P0** Idempotency record и business side effect находятся в одной transaction, если это требуется.
* [x] **P1** Processed event storage очищается/архивируется.
* [x] **P1** Есть тест duplicate event × 2.
* [x] **P1** Есть тест duplicate event concurrent × N.
* [x] **P2** Продумано поведение event replay.

---

# 16. Event contracts

* [x] **P0** Event имеет понятное имя.
* [x] **P0** Event semantics описана.
* [x] **P0** Producer не публикует внутреннюю ORM сущность напрямую.
* [x] **P0** Payload сериализуем.
* [x] **P0** Consumer валидирует event.
* [x] **P1** Event schema versioned.
* [x] **P1** Добавление нового optional field backward compatible.
* [x] **P1** Удаление/переименование fields контролируется.
* [x] **P1** Старый consumer способен пережить новую версию producer во время rolling deploy.
* [ ] **P2** Есть schema registry или аналог, если масштаб оправдывает.

---

# 17. Celery

* [x] **P0** Каждая task имеет понятную ответственность.
* [x] **P0** Task не содержит огромную бизнес-логику без отдельного use case.
* [x] **P0** Retry используется только для retryable errors.
* [x] **P0** Permanent error не retry'ится бесконечно.
* [x] **P0** Есть max retries.
* [x] **P0** Есть retry backoff.
* [x] **P0** Duplicate execution безопасен для критичных tasks.
* [x] **P0** Worker crash после side effect не приводит к corruption.
* [x] **P0** Task не принимает огромные ORM objects в payload.
* [x] **P0** Task получает IDs/minimal payload.
* [x] **P1** Настроены soft/hard time limits.
* [x] **P1** Долгие tasks observable.
* [x] **P1** Queue разделяются по workload, если это необходимо.
* [x] **P1** Есть отдельная queue для тяжёлых задач при необходимости.
* [x] **P1** Celery Beat не запускается в нескольких экземплярах без защиты.
* [x] **P1** Scheduled task идемпотентна.
* [ ] **P2** Autoscaling workers.
* [ ] **P2** Separate worker pools для CPU-heavy и I/O-heavy jobs.

---

# 18. Redis

* [x] **P0** Redis не является случайным source of truth для критичных данных.
* [x] **P0** Каждый тип key имеет namespace.
* [x] **P0** Temporary keys имеют TTL.
* [x] **P0** Нет бесконечно растущих наборов keys без cleanup.
* [x] **P0** Cache failure не corrupt'ит бизнес-данные.
* [x] **P0** Redis outage имеет определённое поведение.
* [x] **P0** Auth/session Redis может быть fail-closed, если безопасность этого требует.
* [x] **P0** Catalog cache может fail-open в PostgreSQL, если допустимо.
* [x] **P1** Cache invalidation определена.
* [x] **P1** Нет очевидных stale cache race conditions.
* [x] **P1** TTL имеет jitter для массовых cache entries, если есть stampede risk.
* [x] **P1** Hot keys известны.
* [x] **P1** Используются atomic Redis commands там, где требуется.
* [x] **P1** Lua используется только там, где действительно нужна атомарность нескольких операций.
* [x] **P2** Cache stampede protection.
* [x] **P2** Metrics hit/miss ratio.

---

# 19. Distributed locks

Если используются:

* [x] **P0** Lock имеет TTL.
* [x] **P0** Lock имеет unique owner token.
* [x] **P0** Unlock возможен только владельцем.
* [x] **P0** Unlock реализован атомарно.
* [x] **P0** Не используется небезопасное `GET → DEL`.
* [x] **P0** Продумано истечение lock во время операции.
* [x] **P1** Lock contention измеряется.
* [x] **P1** Lock не используется вместо DB transaction там, где DB решает проблему лучше.
* [x] **P1** Multi-instance behaviour протестировано.

---

# 20. Cache strategy

* [x] **P0** Понятно, что кэшируется.
* [x] **P0** Понятно, зачем это кэшируется.
* [x] **P0** Понятно, какой TTL.
* [x] **P0** Понятно, кто инвалидирует.
* [x] **P0** Cache miss корректно работает.
* [x] **P0** Cache hit возвращает эквивалентные данные.
* [x] **P0** Ошибка Redis не превращается в `500`, если допустим DB fallback.
* [x] **P1** Есть защита от cache stampede.
* [x] **P1** Есть negative caching там, где полезно.
* [x] **P1** Не кэшируется sensitive информация без необходимости.
* [ ] **P2** Cache effectiveness измеряется.

---

# 21. Media / S3 / MinIO

* [x] **P0** Клиент не может выбрать произвольный filesystem path.
* [x] **P0** Object key генерирует backend.
* [x] **P0** Проверяется MIME/type, если uploads разрешены.
* [x] **P0** Ограничен максимальный размер upload.
* [x] **P0** Нельзя загрузить бесконечный stream.
* [x] **P0** Private files не становятся public случайно.
* [x] **P0** Credentials не отдаются клиенту.
* [x] **P1** Используются presigned URLs там, где это полезно.
* [x] **P1** Есть cleanup orphan objects.
* [x] **P1** DB и object storage eventual consistency продумана.
* [x] **P1** Удаление DB row не оставляет бесконечно мусорные files.
* [ ] **P2** CDN используется при необходимости.

---

# 22. Rate limiting

* [x] **P0** Login защищён.
* [x] **P0** Registration защищена.
* [x] **P0** Password reset защищён.
* [x] **P0** Expensive endpoints защищены.
* [x] **P0** Ограничения нельзя легко обходить случайной сменой header.
* [x] **P1** Rate limit работает между несколькими instances.
* [x] **P1** Ответ содержит корректный `429`.
* [x] **P1** Есть понятное retry behaviour.
* [x] **P1** Отдельные лимиты для authenticated и anonymous users.
* [ ] **P2** Adaptive/risk-based limiting, если действительно необходимо.

---

# 23. Input validation

* [x] **P0** Negative quantity запрещена.
* [x] **P0** `quantity=0` обрабатывается явно.
* [x] **P0** Negative price запрещена.
* [x] **P0** Очень большие числа ограничены.
* [x] **P0** Пустые обязательные strings запрещены.
* [x] **P0** Unicode/whitespace нормализуются там, где это важно.
* [x] **P0** Email нормализуется.
* [x] **P0** UUID не доверяется без проверки существования и ownership.
* [x] **P0** Enum принимает только допустимые значения.
* [x] **P0** Client-generated timestamps не используются как authoritative server time.
* [x] **P1** Проверяются business validation rules, а не только Pydantic types.

---

# 24. Time

* [x] **P0** Backend использует UTC.
* [x] **P0** Нет смеси naive/aware datetime.
* [x] **P0** Expiration сравнивается сервером.
* [x] **P0** `expires_at == now` имеет определённую семантику.
* [x] **P0** TTL не зависит от timezone клиента.
* [x] **P1** Fake clock/time fixture используется в тестах вместо `sleep`.
* [x] **P1** Scheduled jobs корректны при restart.
* [x] **P2** Clock skew между instances не должен ломать critical invariants.

---

# 25. Error handling

* [x] **P0** Domain errors отличаются от infrastructure errors.
* [x] **P0** Expected business error не превращается в `500`.
* [x] **P0** DB exception вызывает rollback.
* [x] **P0** Connection error логируется.
* [x] **P0** Не используется повсеместный `except Exception: pass`.
* [x] **P0** Permanent failure не retry'ится без причины.
* [x] **P0** Transient failure можно retry.
* [x] **P1** Ошибки классифицированы.
* [x] **P1** Error logs содержат context.
* [x] **P1** Sensitive данные не попадают в exception logs.
* [ ] **P2** Error budgets/SLI связаны с типами ошибок.

---

# 26. Timeouts

* [x] **P0** HTTP client имеет connect timeout.
* [x] **P0** HTTP client имеет read timeout.
* [x] **P0** DB pool не ждёт бесконечно.
* [x] **P0** Redis commands имеют timeout.
* [x] **P0** RabbitMQ connection имеет timeout/reconnect.
* [x] **P0** External payment/API вызовы ограничены timeout.
* [x] **P0** Celery tasks не могут зависнуть навсегда.
* [x] **P1** Timeout values конфигурируются.
* [x] **P1** Timeout propagates through request chain в разумных пределах.

---

# 27. Retry

* [x] **P0** Retry выполняется только для transient failures.
* [x] **P0** Есть максимальное число попыток.
* [x] **P0** Есть exponential backoff.
* [x] **P1** Есть jitter.
* [x] **P0** Retry не создаёт duplicate side effect.
* [x] **P0** Retry POST либо идемпотентен, либо защищён idempotency key.
* [x] **P1** Retry storms не способны завалить восстановившийся сервис.
* [x] **P1** Retry metrics собираются.

---

# 28. Circuit breaker / degraded mode

* [x] **P1** Для критичных внешних зависимостей продумано поведение при длительном outage.
* [x] **P1** Сервис не держит тысячи зависших connections.
* [x] **P1** Необязательная зависимость может отключиться без падения всего приложения.
* [x] **P1** Есть degraded mode там, где он имеет смысл.
* [x] **P2** Circuit breaker реализован для действительно проблемных remote dependencies.

---

# 29. Startup

* [x] **P0** Приложение fail-fast при критичной startup ошибке.
* [x] **P0** DB connection проверяется.
* [x] **P0** Неверная migration/schema обнаруживается.
* [x] **P0** Не происходит silent startup с частично сломанной конфигурацией.
* [x] **P1** Необязательная инфраструктура может деградировать контролируемо.
* [x] **P1** Startup не создаёт race между несколькими instances.
* [x] **P1** Initialization task идемпотентна.

---

# 30. Graceful shutdown

* [x] **P0** HTTP сервер перестаёт принимать новые requests.
* [x] **P0** In-flight requests получают время завершиться.
* [x] **P0** DB pool закрывается.
* [x] **P0** Redis connection закрывается.
* [x] **P0** RabbitMQ consumer прекращает забирать новые messages.
* [x] **P0** Неacknowledged message возвращается broker'у при аварийном завершении.
* [x] **P0** Worker shutdown не теряет task.
* [x] **P1** Есть configurable shutdown timeout.
* [x] **P1** SIGTERM протестирован.

---

# 31. Connection pools

* [x] **P0** SQLAlchemy pool имеет разумные limits.
* [x] **P0** `pool_size × replicas` не превышает возможности PostgreSQL.
* [x] **P0** Connections возвращаются в pool.
* [x] **P0** Session не живёт дольше request/use case.
* [x] **P0** HTTP clients переиспользуются.
* [x] **P0** Redis clients переиспользуются.
* [x] **P1** Pool exhaustion observable.
* [x] **P1** Pool timeout настроен.
* [ ] **P2** Используется PgBouncer, если требуется масштабом.

---

# 32. Database migrations

* [x] **P0** `alembic upgrade head` работает на пустой БД.
* [x] **P0** Все текущие models соответствуют head migration.
* [x] **P0** Migration не предполагает наличие данных, которых может не быть.
* [x] **P0** `NOT NULL` добавляется безопасно.
* [x] **P0** Новые constraints учитывают существующие rows.
* [x] **P0** Enum migrations безопасны.
* [x] **P1** Есть strategy expand → migrate → contract для breaking schema changes.
* [x] **P1** Старый код может временно работать с новой schema во время rolling deploy.
* [x] **P1** Нет долгих table locks без понимания последствий.
* [x] **P1** Backup перед destructive migration.
* [ ] **P2** Migration time оценивается на production-sized dataset.

---

# 33. Logging

* [x] **P0** Есть structured logs.
* [x] **P0** Каждый request имеет request/correlation ID.
* [x] **P0** Event processing имеет event ID.
* [x] **P0** Order/reservation/payment IDs попадают в relevant logs.
* [x] **P0** Password/token/secret не логируются.
* [x] **P0** Полный payment payload не логируется без необходимости.
* [x] **P0** Stack trace есть для unexpected exceptions.
* [x] **P1** Логи имеют service name.
* [x] **P1** Логи имеют environment.
* [x] **P1** Логи имеют severity.
* [x] **P1** Можно проследить один business flow между сервисами.
* [x] **P1** Log volume контролируется.
* [ ] **P2** Centralized logging.

---

# 34. Metrics

* [x] **P0** Request count.
* [x] **P0** Request latency.
* [x] **P0** Error rate.
* [x] **P0** Worker task count.
* [x] **P0** Worker failures.
* [x] **P0** RabbitMQ consumer failures.
* [x] **P1** Queue depth.
* [x] **P1** Outbox pending count.
* [x] **P1** Oldest pending outbox age.
* [x] **P1** Reservation expiration backlog.
* [x] **P1** DB connection pool usage.
* [x] **P1** Redis errors.
* [x] **P1** Cache hit rate.
* [x] **P1** Payment failures.
* [x] **P1** Order completion rate.
* [x] **P1** Inventory conflict/rejection rate.
* [x] **P2** Business metrics dashboards.

---

# 35. Health checks

* [x] **P0** `/health/live`.
* [x] **P0** `/health/ready`.
* [x] **P0** Liveness не падает только потому, что внешний сервис временно умер.
* [x] **P0** Readiness отражает способность принимать traffic.
* [x] **P0** Health endpoints лёгкие.
* [x] **P0** Health check не создаёт новую DB connection storm.
* [x] **P1** Worker health observable.
* [x] **P1** RabbitMQ consumers observable.
* [x] **P1** Celery Beat health observable.

---

# 36. Alerting

* [ ] **P1** High 5xx rate.
* [ ] **P1** High latency.
* [x] **P1** DB unavailable.
* [ ] **P1** DB pool exhausted.
* [x] **P1** RabbitMQ unavailable.
* [ ] **P1** Queue backlog растёт.
* [ ] **P1** Outbox backlog растёт.
* [ ] **P1** Oldest outbox event слишком старый.
* [ ] **P1** DLQ имеет сообщения.
* [ ] **P1** Celery worker down.
* [ ] **P1** Reservation cleanup отстаёт.
* [ ] **P1** Payment error spike.
* [ ] **P2** SLO-based alerts вместо отдельных low-level alerts.

---

# 37. Tracing

* [x] **P1** Correlation ID переносится между HTTP сервисами.
* [x] **P1** Correlation ID/event ID переносится через RabbitMQ.
* [x] **P1** Можно увидеть цепочку `request → service → outbox → event → consumer`.
* [ ] **P2** OpenTelemetry.
* [ ] **P2** Distributed tracing backend.
* [ ] **P2** Sampling policy.

---

# 38. Prometheus

Если уже есть:

* [x] **P0** `/metrics` не раскрывает secrets.
* [x] **P0** Labels не имеют unbounded cardinality.
* [x] **P0** `user_id`, `order_id`, UUID не используются как Prometheus labels.
* [x] **P1** Histogram buckets подходят latency проекта.
* [x] **P1** Есть custom business metrics.
* [x] **P1** Worker metrics.
* [x] **P1** RabbitMQ/outbox metrics.

---

# 39. Security headers / HTTP security

* [x] **P0** CORS настроен явно.
* [x] **P0** `*` не используется с credentials.
* [x] **P0** Trusted hosts настроены.
* [x] **P0** Proxy headers принимаются только от trusted proxy.
* [x] **P0** HTTPS подразумевается в production.
* [x] **P1** HSTS на edge.
* [x] **P1** Security headers добавляет gateway.
* [x] **P1** Cookies имеют `Secure`, `HttpOnly`, `SameSite`, если auth использует cookies.

---

# 40. Application security

* [x] **P0** SQL injection невозможна через raw SQL interpolation.
* [x] **P0** Command injection отсутствует.
* [x] **P0** Path traversal отсутствует.
* [x] **P0** SSRF mitigated для user-controlled URLs.
* [x] **P0** Secrets не находятся в repository history.
* [x] **P0** Internal admin API защищено.
* [x] **P0** Debug endpoints выключены.
* [x] **P0** Production debug mode выключен.
* [x] **P0** Не выдаются внутренние hostnames/errors пользователю.
* [x] **P1** Dependency vulnerabilities сканируются.
* [x] **P1** Container запускается не от root.
* [x] **P1** Principle of least privilege для DB users.
* [x] **P1** Отдельные credentials на сервис.
* [x] **P1** RabbitMQ permissions ограничены.
* [ ] **P2** Threat model документирован.
* [ ] **P2** SAST/DAST в CI.

---

# 41. Secrets

* [x] **P0** Нет `.env` в git.
* [x] **P0** Нет passwords в Dockerfile.
* [x] **P0** Нет tokens в logs.
* [x] **P0** Нет secrets в frontend bundle.
* [x] **P1** Разные secrets для разных environments.
* [x] **P1** Разные DB users для сервисов.
* [x] **P1** Можно rotate secrets.
* [ ] **P2** Vault/KMS/Secret Manager.

---

# 42. Dependency management

* [x] **P0** Dependencies зафиксированы lock-файлом.
* [x] **P0** Reproducible build.
* [x] **P0** Нет случайных `latest`.
* [ ] **P1** Dependabot/Renovate или аналог.
* [ ] **P1** Security scanning.
* [x] **P1** Deprecated dependencies отслеживаются.
* [x] **P1** Python version фиксирована.
* [ ] **P2** SBOM генерируется.

---

# 43. Docker

* [x] **P0** Каждый service собирается.
* [x] **P0** Dockerfile reproducible.
* [x] **P0** `.dockerignore` существует.
* [x] **P0** Secrets не копируются в image.
* [x] **P0** Image не содержит лишний dev мусор.
* [x] **P0** Процесс получает SIGTERM.
* [x] **P1** Multi-stage build.
* [x] **P1** Non-root user.
* [x] **P1** Healthcheck.
* [x] **P1** Image имеет pinned base version.
* [x] **P1** Image разумного размера.
* [ ] **P2** Image vulnerability scanning.

---

# 44. Docker Compose / local environment

* [x] **P0** Весь проект можно поднять одной понятной командой.
* [x] **P0** RabbitMQ vhosts/users создаются автоматически.
* [x] **P0** DB databases/users создаются автоматически.
* [x] **P0** Нет manual secret steps, не описанных в README.
* [x] **P0** Volumes определены.
* [x] **P0** Ports не конфликтуют.
* [x] **P0** Healthchecks есть у инфраструктуры.
* [x] **P0** `depends_on` не принимается за полноценную readiness гарантию.
* [x] **P1** Есть отдельный test compose profile.
* [x] **P1** Есть observability profile.

---

# 45. Reverse proxy / Gateway

* [x] **P0** Есть единая внешняя точка входа.
* [x] **P0** Internal services не обязаны быть доступны напрямую снаружи.
* [x] **P0** Proxy корректно передаёт request ID.
* [x] **P0** Есть request size limit.
* [x] **P0** Есть timeout.
* [x] **P0** Есть корректная работа client IP.
* [x] **P1** Rate limiting можно применять на edge.
* [x] **P1** TLS termination.
* [x] **P1** Compression.
* [ ] **P2** Canary/traffic splitting.

---

# 46. CI

* [x] **P0** Tests запускаются на каждый PR.
* [x] **P0** Linter.
* [x] **P0** Formatter check.
* [x] **P0** Type checker.
* [x] **P0** Migration validation.
* [x] **P0** Build Docker images.
* [x] **P0** Failure CI блокирует merge.
* [x] **P1** Integration tests с PostgreSQL.
* [x] **P1** Integration tests с Redis.
* [x] **P1** Messaging tests.
* [x] **P1** Security/dependency scan.
* [x] **P1** Coverage report.
* [x] **P1** Changed migration detection.
* [ ] **P2** Performance regression tests.

---

# 47. CD

* [x] **P1** Deploy воспроизводимый.
* [x] **P1** Нет ручного копирования файлов на сервер.
* [x] **P1** Environment configuration передаётся отдельно.
* [x] **P1** Migration запускается контролируемо.
* [x] **P1** Failed deploy можно rollback.
* [x] **P1** Старый и новый service могут кратковременно работать одновременно.
* [x] **P1** Deployment не теряет in-flight messages.
* [ ] **P2** Blue/green или canary.
* [ ] **P2** Automated rollback по health metrics.

---

# 48. Testing — unit

* [x] **P0** Domain rules покрыты.
* [x] **P0** State transitions покрыты.
* [x] **P0** Money calculations покрыты.
* [x] **P0** Validation edge cases покрыты.
* [x] **P0** Tests deterministic.
* [x] **P0** Нет бессмысленного overmock.
* [x] **P1** Test names описывают behaviour.
* [x] **P1** Fixtures переиспользуются разумно.
* [x] **P1** Тест не повторяет implementation.

---

# 49. Testing — integration

* [x] **P0** Repository проверяется на настоящем PostgreSQL.
* [x] **P0** Constraints проверяются настоящей БД.
* [x] **P0** Transactions проверяются.
* [x] **P0** Rollback проверяется.
* [x] **P0** Redis behaviour проверяется на реальном Redis там, где атомарность важна.
* [x] **P1** Alembic migrations проверяются.
* [x] **P1** Outbox integration проверяется.
* [x] **P1** Consumers integration проверяются.

---

# 50. Testing — API

* [x] **P0** Happy paths.
* [x] **P0** `401`.
* [x] **P0** `403`.
* [x] **P0** `404`.
* [x] **P0** `409`.
* [x] **P0** Validation errors.
* [x] **P0** Ownership.
* [x] **P1** Pagination.
* [x] **P1** Filtering.
* [x] **P1** Sorting.
* [x] **P1** Duplicate requests.

---

# 51. Testing — concurrency

* [x] **P0** Last-item reservation.
* [x] **P0** Concurrent release.
* [x] **P0** Concurrent order creation, если relevant.
* [x] **P0** Concurrent idempotency processing.
* [x] **P0** Concurrent outbox publishers.
* [x] **P1** N=20–100 parallel attempts.
* [x] **P1** Проверяется финальная БД, а не только HTTP status.
* [x] **P1** Тест воспроизводим и не основан на `sleep`.

---

# 52. Testing — messaging

* [x] **P0** Event приходит один раз.
* [x] **P0** Event приходит дважды.
* [x] **P0** Consumer падает до commit.
* [x] **P0** Consumer падает после side effect — если возможный сценарий.
* [x] **P0** Invalid event.
* [x] **P1** Retry.
* [x] **P1** DLQ.
* [x] **P1** Out-of-order event.
* [x] **P1** Old version event.

---

# 53. E2E

Минимум несколько действительно важных flows:

* [x] **P0** Register/Login → authenticated request.
* [x] **P0** Catalog → reserve → order → payment success.
* [x] **P0** Reservation expiration → stock release.
* [x] **P0** Payment failure → корректное состояние order/reservation.
* [x] **P1** Last item race.
* [x] **P1** RabbitMQ temporary outage → eventual recovery.
* [x] **P1** Duplicate event → один business effect.

---

# 54. Test coverage

* [x] **P0** Coverage измеряется.
* [x] **P0** Coverage не является единственной целью.
* [x] **P0** Critical business code хорошо покрыт.
* [x] **P0** Critical branches покрыты.
* [x] **P1** Regression test появляется для каждого серьёзного найденного бага.
* [x] **P1** Есть список intentionally uncovered infrastructure glue.
* [ ] **P2** Mutation testing для особо критичной domain logic.

---

# 55. Load testing

* [ ] **P1** Есть базовый load test.
* [ ] **P1** Catalog read нагрузка.
* [ ] **P1** Auth нагрузка.
* [ ] **P1** Reservation нагрузка.
* [ ] **P1** Flash sale burst.
* [ ] **P1** RabbitMQ consumer throughput.
* [ ] **P1** Outbox publisher throughput.
* [ ] **P1** Измерены p50/p95/p99.
* [ ] **P1** Измерено error rate.
* [ ] **P1** Проверено поведение pool exhaustion.
* [ ] **P2** Stress test до точки деградации.
* [ ] **P2** Soak test несколько часов.

---

# 56. Resilience testing

* [ ] **P1** Убить Redis во время работы.
* [ ] **P1** Убить RabbitMQ.
* [ ] **P1** Убить Celery worker.
* [ ] **P1** Убить API instance.
* [ ] **P1** Сделать PostgreSQL временно недоступным.
* [ ] **P1** Добавить latency external service.
* [x] **P1** Проверить restart publisher.
* [x] **P1** Проверить restart consumer.
* [x] **P1** Проверить restart между DB commit и publish.
* [ ] **P2** Автоматизированные chaos tests.

---

# 57. Backups

* [x] **P0** PostgreSQL backup существует.
* [ ] **P0** Backup выполняется автоматически.
* [ ] **P0** Backup хранится отдельно от основной БД.
* [ ] **P0** Restore хотя бы один раз реально проверялся.
* [x] **P1** Определены retention periods.
* [x] **P1** Object storage backup/versioning определены.
* [ ] **P1** RPO понятен.
* [ ] **P1** RTO понятен.
* [ ] **P2** Point-in-time recovery.

---

# 58. Disaster recovery

* [ ] **P1** Есть инструкция восстановления PostgreSQL.
* [ ] **P1** Есть инструкция восстановления RabbitMQ/config.
* [ ] **P1** Есть инструкция пересоздания Redis.
* [ ] **P1** Есть инструкция восстановления service secrets.
* [x] **P1** Infrastructure можно поднять из кода/config.
* [ ] **P1** Есть recovery procedure для stuck outbox.
* [ ] **P1** Есть procedure для DLQ replay.
* [ ] **P2** DR rehearsal.

---

# 59. Data lifecycle

* [x] **P1** Понятно, сколько хранить audit logs.
* [x] **P1** Понятно, сколько хранить sessions.
* [x] **P1** Понятно, сколько хранить outbox.
* [x] **P1** Понятно, сколько хранить processed events.
* [x] **P1** Expired reservations очищаются.
* [x] **P1** Orphan media очищаются.
* [x] **P1** Soft-deleted rows когда-нибудь purge'ятся, если soft delete используется.
* [ ] **P2** Archive cold data.

---

# 60. Privacy / sensitive data

* [x] **P0** Собираются только необходимые данные.
* [x] **P0** Пароли никогда не доступны в plaintext.
* [x] **P0** Tokens не логируются.
* [x] **P0** Sensitive fields не попадают в metrics.
* [x] **P1** Есть возможность удалить пользовательские данные там, где требуется.
* [x] **P1** Есть data retention policy.
* [x] **P1** Backup handling учитывает sensitive data.

---

# 61. Audit

* [x] **P1** Login failures.
* [x] **P1** Password/security actions.
* [x] **P1** Admin actions.
* [x] **P1** Stock manual adjustments.
* [x] **P1** Order status manual changes.
* [x] **P1** Refunds.
* [x] **P1** Sensitive permission changes.
* [x] **P1** Audit entry нельзя незаметно изменить обычным пользователем.

---

# 62. Admin functionality

* [x] **P0** Admin API защищено RBAC.
* [x] **P0** Admin не может случайно создать invalid business state.
* [x] **P0** Manual stock change валидируется.
* [x] **P0** Dangerous operations требуют явного действия.
* [x] **P1** Admin changes audit'ятся.
* [x] **P1** Bulk actions ограничены.
* [x] **P1** Есть idempotency для опасных повторяемых действий.
* [ ] **P2** Four-eyes approval для особо опасных действий, если бизнес требует.

---

# 63. Search/filtering

* [x] **P0** Filters валидируются.
* [x] **P0** Sorting принимает только whitelist полей.
* [x] **P0** Нельзя передать произвольный SQL field.
* [x] **P1** Индексы соответствуют частым filters.
* [x] **P1** Search query ограничена.
* [x] **P1** Pagination стабильно работает при concurrent inserts.
* [ ] **P2** Cursor pagination для больших datasets.

---

# 64. Performance

* [x] **P0** Нет N+1 на основных endpoints.
* [x] **P0** Нет загрузки всей таблицы в память.
* [x] **P0** Нет блокирующего network/file I/O внутри event loop.
* [x] **P0** Pagination обязательна для больших коллекций.
* [x] **P0** Indexes есть под hot queries.
* [x] **P1** Response payload не содержит лишние данные.
* [x] **P1** Batch operations используются разумно.
* [x] **P1** Connection reuse.
* [x] **P1** Slow endpoints измеряются.
* [ ] **P2** Profiling CPU/memory.

---

# 65. Python async

* [x] **P0** Нет забытых `await`.
* [x] **P0** Sync HTTP client не используется внутри async handler.
* [x] **P0** Sync DB driver не используется внутри async handler.
* [x] **P0** CPU-heavy password hashing вынесен из event loop.
* [x] **P0** Background `create_task` не используется для критичной гарантированной работы.
* [x] **P0** Detached task exceptions не теряются.
* [x] **P1** Есть правильный lifecycle async clients.
* [x] **P1** Semaphores/limits стоят перед массовым fan-out.
* [x] **P1** Не создаются тысячи coroutines без backpressure.

---

# 66. Memory

* [x] **P0** Upload streaming не загружает огромный файл целиком.
* [x] **P0** Большие DB query результаты пагинированы.
* [x] **P0** Consumer не накапливает бесконечный batch.
* [x] **P1** Memory usage измеряется.
* [x] **P1** Нет бесконечных in-memory caches.
* [ ] **P2** Memory leak/soak testing.

---

# 67. Message schemas

* [x] **P0** Payload строго валидируется.
* [x] **P0** UUID/date/decimal сериализуются однозначно.
* [x] **P0** Sensitive fields не публикуются без необходимости.
* [x] **P1** Schema имеет version.
* [x] **P1** Producer/consumer compatibility тестируется.
* [x] **P1** Unknown extra fields не ломают старый consumer, если политика совместимости это допускает.

---

# 68. Business invariants

Для Flashmarket отдельно зафиксировать и протестировать invariants вроде:

* [x] **P0** `available_stock >= 0`.
* [x] **P0** Один reservation не может одновременно быть `active` и `released`.
* [x] **P0** Один reservation не возвращает stock дважды.
* [x] **P0** Один успешно оплаченный order не оплачивается повторно.
* [x] **P0** Refund не превышает оплаченный amount.
* [x] **P0** Order total определяется backend.
* [x] **P0** User purchase limit нельзя обойти параллельными requests.
* [x] **P0** Expired reservation нельзя превратить в valid purchase без отдельного предусмотренного flow.
* [x] **P0** Duplicate message не меняет business result.
* [x] **P1** Максимально возможное число invariants дополнительно enforced DB.

---

# 69. State machines

* [x] **P0** Состояния явно определены.
* [x] **P0** Разрешённые transitions определены.
* [x] **P0** Неразрешённые transitions отклоняются.
* [x] **P0** Повтор текущего transition идемпотентен либо контролируемо ошибочен.
* [x] **P0** Concurrent transitions безопасны.
* [x] **P1** Transition имеет timestamp.
* [x] **P1** Transition имеет reason/context при необходимости.
* [x] **P1** State changes audit'ятся для важных сущностей.

---

# 70. Consistency

* [x] **P0** Понятно, где strong consistency.
* [x] **P0** Понятно, где eventual consistency.
* [x] **P0** UI/client не предполагает мгновенное обновление там, где система eventual.
* [x] **P0** Eventual state имеет recovery path.
* [x] **P0** Inconsistent временное состояние допустимо бизнесом.
* [x] **P1** Есть reconciliation для важных distributed entities.
* [x] **P2** Consistency expectations документированы для каждого flow.

---

# 71. Sagas / compensation

Если distributed checkout требует:

* [x] **P0** Определён happy path.
* [x] **P0** Определён failure после reserve.
* [x] **P0** Определён failure после order creation.
* [x] **P0** Определён payment failure.
* [x] **P0** Compensation идемпотентна.
* [x] **P0** Повтор compensation безопасен.
* [x] **P0** Crash между шагами восстанавливаем.
* [x] **P1** Saga state observable.
* [x] **P1** Зависшие saga можно найти.
* [x] **P1** Есть reconciliation/recovery job.
* [ ] **P2** Отдельный orchestrator — только если сложность действительно оправдывает.

---

# 72. Data ownership

* [x] **P0** Catalog является source of truth для product metadata.
* [x] **P0** Inventory — source of truth для stock, если так спроектировано.
* [x] **P0** Orders — source of truth для order lifecycle.
* [x] **P0** Payments — source of truth для payment lifecycle.
* [x] **P0** Auth — source of truth для identity/session.
* [x] **P0** Другие сервисы не обновляют эти данные напрямую.
* [x] **P1** Cached/read-model копии явно отличаются от authoritative data.

---

# 73. Service-to-service HTTP

* [x] **P0** Есть timeout.
* [x] **P0** Ошибка remote service не скрывается.
* [x] **P0** Retry безопасен.
* [x] **P0** Internal auth есть, если сеть не считается trusted.
* [x] **P0** Response validation есть.
* [x] **P1** Correlation ID передаётся.
* [x] **P1** Есть connection pooling.
* [x] **P1** Есть bulkhead/concurrency limit.
* [x] **P1** Нет длинных synchronous chains `A→B→C→D→E` для критичного request path без необходимости.

---

# 74. Nginx/API Gateway

* [x] **P0** Routes определены явно.
* [x] **P0** Нет случайного доступа к internal endpoints.
* [x] **P0** Client body limit.
* [x] **P0** Proxy timeout.
* [x] **P0** Forwarded headers безопасны.
* [x] **P0** WebSocket настройки корректны, если используется.
* [x] **P1** Rate limit.
* [x] **P1** Access logs.
* [x] **P1** Request ID generation/propagation.

---

# 75. Documentation

* [x] **P0** README объясняет, что делает проект.
* [x] **P0** README объясняет, как его запустить.
* [x] **P0** Есть архитектурная схема.
* [x] **P0** Описаны микросервисы.
* [x] **P0** Описана инфраструктура.
* [x] **P0** Описаны основные env variables.
* [x] **P0** Описаны migration commands.
* [x] **P0** Описаны test commands.
* [x] **P1** Описаны events.
* [x] **P1** Описаны queues.
* [x] **P1** Описаны critical flows.
* [x] **P1** Описаны consistency guarantees.
* [x] **P1** Описаны failure modes.
* [x] **P1** ADR.
* [x] **P1** Runbooks.
* [x] **P2** Полностью интерактивная architecture explorer — то, что ты как раз сейчас делаешь.

---

# 76. Runbooks

Для важных проблем должна быть короткая инструкция:

* [ ] **P1** RabbitMQ недоступен.
* [ ] **P1** Redis недоступен.
* [ ] **P1** PostgreSQL недоступен.
* [x] **P1** Outbox backlog.
* [x] **P1** DLQ растёт.
* [ ] **P1** Celery worker умер.
* [x] **P1** Reservation cleanup не работает.
* [ ] **P1** Payment events зависли.
* [ ] **P1** Migration failed.
* [ ] **P1** Rollback deployment.
* [ ] **P1** Restore backup.

---

# 77. Operational tooling

* [x] **P1** Можно посмотреть pending outbox.
* [x] **P1** Можно посмотреть DLQ.
* [x] **P1** Можно безопасно replay event.
* [x] **P1** Можно посмотреть stuck order.
* [x] **P1** Можно посмотреть reservation lifecycle.
* [x] **P1** Можно проверить payment state.
* [x] **P1** Есть safe admin action для reconciliation.
* [x] **P1** Dangerous manual SQL не является основным способом эксплуатации системы.

---

# 78. Deployment readiness

* [x] **P0** Один commit однозначно соответствует версии приложения.
* [x] **P0** Version/build SHA доступен в running service.
* [x] **P0** Можно определить, какая версия сейчас работает.
* [x] **P0** Все migrations применены.
* [x] **P0** Health checks зелёные.
* [x] **P0** Smoke tests проходят.
* [x] **P1** Rollback проверен.
* [x] **P1** Deployment checklist существует.
* [x] **P1** Нет manual undocumented production step.

---

# 79. Smoke tests после deploy

* [x] **P0** `/health`.
* [x] **P0** Login.
* [x] **P0** Catalog.
* [x] **P0** Основная DB доступна.
* [x] **P0** Redis доступен/правильно деградирует.
* [x] **P0** RabbitMQ publishing работает.
* [x] **P0** Worker получает task/message.
* [x] **P1** Test order/reservation flow.
* [x] **P1** Outbox event действительно доходит до consumer.

---

# 80. Production data safety

* [x] **P0** Production DB не используется tests.
* [x] **P0** Dev scripts не могут случайно очистить production.
* [x] **P0** Seed script не запускается автоматически в production.
* [x] **P0** `DROP TABLE` tooling защищено.
* [x] **P1** Production credentials отличны от dev.
* [x] **P1** Dangerous CLI требует explicit confirmation/environment validation.

---

# 81. Feature flags

* [x] **P2** Опасную новую функциональность можно включать постепенно.
* [ ] **P2** Feature flag имеет owner/expiration.
* [x] **P2** Старые flags удаляются.
* [x] **P2** Critical correctness не зависит от клиентского flag.

---

# 82. Compatibility при deployment

* [x] **P1** Новый producer не ломает старого consumer.
* [x] **P1** Новый consumer понимает старые сообщения.
* [x] **P1** Новая schema совместима со старой версией приложения во время rollout.
* [x] **P1** Event field не удаляется сразу.
* [x] **P1** DB column не удаляется до удаления использования из всех deployments.

---

# 83. Scaling

* [x] **P1** API stateless настолько, насколько возможно.
* [x] **P1** Можно поднять несколько API replicas.
* [x] **P1** Session не привязана к RAM конкретного process.
* [x] **P1** Consumers можно масштабировать горизонтально.
* [x] **P1** Outbox publishers можно масштабировать безопасно.
* [x] **P1** Scheduled jobs не начинают выполняться N раз при N replicas.
* [x] **P1** PostgreSQL connection budget учитывает replicas.
* [ ] **P2** Autoscaling rules.
* [ ] **P2** Partitioning/sharding только при реальной необходимости.

---

# 84. Backpressure

* [x] **P1** Consumer не забирает больше messages, чем способен обработать.
* [x] **P1** Prefetch ограничен.
* [x] **P1** HTTP fan-out ограничен.
* [x] **P1** Bulk endpoints имеют max batch size.
* [x] **P1** Upload size ограничен.
* [x] **P1** Queue backlog observable.
* [ ] **P2** Load shedding при экстремальной нагрузке.

---

# 85. Flash-sale specific resilience

Для Flashmarket особенно ценно:

* [x] **P0** Burst в момент старта drop не создаёт overselling.
* [x] **P0** Повторный click клиента не создаёт несколько reservations.
* [x] **P0** Timeout клиента не заставляет его случайно купить дважды.
* [x] **P0** Backend authoritative по времени старта.
* [x] **P0** Backend authoritative по stock.
* [x] **P0** Backend authoritative по цене.
* [x] **P0** Cleanup expired reservations выдерживает большой batch.
* [x] **P1** Hot SKU contention протестирован.
* [x] **P1** Catalog можно агрессивно кэшировать.
* [x] **P1** Critical write path не зависит от cache.
* [x] **P1** Queue backlog после всплеска постепенно разгребается.
* [x] **P2** Prewarming.
* [ ] **P2** Load shedding.
* [ ] **P2** Queue prioritization.

---

# 86. Failure scenarios, которые проект обязан уметь объяснить

Ты должен уметь прямо ответить, что произойдёт, если:

* [x] **P0** Два пользователя одновременно покупают последний товар.
* [x] **P0** Один request отправился дважды.
* [x] **P0** Один event пришёл дважды.
* [x] **P0** Event пришёл позже другого event.
* [x] **P0** API process умер после DB commit.
* [x] **P0** Publisher умер после RabbitMQ publish.
* [x] **P0** Consumer умер до DB commit.
* [x] **P0** Consumer умер после DB commit, но до ack.
* [x] **P0** Redis полностью умер.
* [x] **P0** RabbitMQ полностью умер.
* [x] **P0** PostgreSQL временно недоступен.
* [ ] **P0** Celery worker умер.
* [x] **P0** Payment provider timeout'нул.
* [x] **P0** Payment provider ответил success после client timeout.
* [x] **P0** Payment пришёл после expiration reservation.
* [x] **P1** Один микросервис недоступен 5 минут.
* [x] **P1** Несколько instances стартуют одновременно.
* [x] **P1** Миграция произошла одновременно с rolling deployment.

Если на вопрос ответ:

> ну, наверное...

— это ещё gap.

---

# 87. Что обязательно должно быть видно на твоей Architecture странице

В твоём случае я бы считал отдельным чеклистом:

* [x] Все микросервисы.
* [x] Responsibility каждого.
* [x] Data ownership.
* [x] HTTP связи.
* [x] Event связи.
* [x] PostgreSQL зависимости.
* [x] Redis зависимости.
* [x] RabbitMQ.
* [x] Celery.
* [x] Outbox.
* [x] Producer → event → consumer.
* [x] 3–5 основных business flows.
* [x] Transaction boundaries.
* [x] Eventual consistency boundaries.
* [x] 5–8 главных engineering decisions.
* [x] Atomic stock reservation.
* [x] Idempotency.
* [x] Failure recovery.
* [x] Несколько реально интересных indexes.
* [x] Несколько реальных SQL/DB механизмов.
* [x] Что происходит при crash.
* [x] Что происходит при duplicate.
* [x] Что происходит при concurrency.
* [x] Source evidence по клику.
* [x] Planned вещи визуально не выдаются за implemented.

---

# 88. Минимальные engineering highlights, которые я бы хотел видеть в Flashmarket

* [x] Atomic stock reservation.
* [x] Transactional Outbox.
* [x] Idempotent event consumers.
* [x] Reservation expiration.
* [x] Safe reservation release.
* [x] Reliable asynchronous event delivery.
* [x] RabbitMQ retry strategy.
* [x] Dead-letter handling.
* [x] Celery task idempotency.
* [x] Correct transaction boundaries.
* [x] Database-level invariants.
* [x] Useful PostgreSQL indexes.
* [x] Redis cache strategy.
* [x] Explicit Redis failure strategy.
* [x] Secure JWT/session lifecycle.
* [x] Rate limiting.
* [x] Structured logs.
* [x] Request/event correlation.
* [x] Metrics.
* [x] Concurrency integration tests.
* [x] Distributed failure tests.

---

# 89. Definition of Done для отдельного микросервиса

Я бы считал service более-менее законченным, когда:

* [x] Есть понятная responsibility.
* [x] API готов.
* [x] Schemas валидируются.
* [x] Auth/authorization готовы.
* [x] Business logic отделена.
* [x] DB schema готова.
* [x] Alembic migrations готовы.
* [x] Constraints готовы.
* [x] Indexes готовы.
* [x] Transactions корректны.
* [x] Concurrency рассмотрена.
* [x] Events определены.
* [x] Outbox работает, если service публикует события.
* [x] Consumers идемпотентны.
* [x] Redis semantics определена.
* [x] Errors нормализованы.
* [x] Logging есть.
* [x] Metrics есть.
* [x] Healthcheck есть.
* [x] Unit tests есть.
* [x] Integration tests есть.
* [x] API tests есть.
* [x] Concurrency tests есть, где нужны.
* [x] Failure scenarios протестированы.
* [x] Docker работает.
* [x] Startup/shutdown корректны.
* [x] README/docs обновлены.

---

# 90. Production release gate

Перед тем как мысленно поставить Flashmarket статус **«готов к продакшену»**, я бы потребовал хотя бы следующее:

## Correctness

* [x] Нет известных CRITICAL bugs.
* [x] Нет известных HIGH data-integrity bugs.
* [x] Critical invariants enforce'ятся.
* [x] Concurrency протестирована.
* [x] Transactions проверены.
* [x] Duplicate operations безопасны.

## Distributed systems

* [x] Outbox не теряет committed events.
* [x] Consumers идемпотентны.
* [x] RabbitMQ outage переживается.
* [x] Worker restart переживается.
* [x] Retry semantics безопасна.
* [x] Poison messages не крутятся бесконечно.

## Security

* [x] Auth работает корректно.
* [x] Authorization протестована.
* [x] Secrets защищены.
* [x] Rate limits есть.
* [x] Нет очевидных critical vulnerabilities.

## Data

* [x] Migrations работают с нуля.
* [x] Backup работает.
* [x] Restore реально проверен.
* [x] DB constraints защищают critical state.

## Operations

* [x] Logs.
* [x] Metrics.
* [x] Healthchecks.
* [x] Alerts.
* [x] Runbooks.
* [x] Graceful shutdown.

## Testing

* [x] Unit suite green.
* [x] Integration suite green.
* [x] API suite green.
* [x] Critical E2E green.
* [x] Concurrency suite green.
* [x] Messaging duplicate/retry tests green.

## Deployment

* [x] Reproducible Docker build.
* [x] CI green.
* [x] Deploy reproducible.
* [x] Rollback возможен.
* [x] Smoke tests green.

---

# Как я бы использовал этот checklist именно для Flashmarket

Не пытайся тупо сделать **500/500 галочек**. Это легко превращается в бессмысленный enterprise cosplay.

Сначала добей:

**P0 correctness → P0 distributed systems → P0 security → P0 testing → P0 observability.**

После этого бери P1, которые помогают именно Flashmarket:

1. Flash-sale concurrency.
2. Transactional outbox.
3. Idempotent consumers.
4. Reservation expiration.
5. Payment/order consistency.
6. RabbitMQ failure recovery.
7. Redis degradation.
8. PostgreSQL indexes.
9. Metrics + tracing.
10. Load testing.

Если всё это реально реализовано и протестировано, Flashmarket уже будет выглядеть не как «CRUD из девяти микросервисов», а как законченная backend-система, где продуманы **данные, конкурентность, сбои, доставка сообщений, эксплуатация и восстановление**.
