# FlashMarket: Карта API Роутов и Межсервисных Связей

> **Версия**: 1.0  
> **Статус**: Актуальная спецификация  
> **Назначение**: Полный справочник всех REST эндпоинтов микросервисов платформы, прав доступа, синхронных вызовов (HTTP, Redis, DB) и асинхронных потоков данных (RabbitMQ Outbox, Consumers, Celery).

---

## Оглавление

1. [Архитектурный обзор взаимодействий](#1-архитектурный-обзор-взаимодействий)
2. [Inventory Service (Склад и Резервации)](#2-inventory-service-склад-и-резервации)
3. [Orders Service (Заказы и Промокоды)](#3-orders-service-заказы-и-промокоды)
4. [Payments Service (Платежи)](#4-payments-service-платежи)
5. [Catalog Service (Каталог товаров, Категории, Бренды, Варианты)](#5-catalog-service-каталог-товаров-категории-бренды-варианты)
6. [Auth Service (Аутентификация, Пользователи, Сессии, Аудит)](#6-auth-service-аутентификация-пользователи-сессии-аудит)
7. [Drops Service (Flash-Sale Кампании)](#7-drops-service-flash-sale-кампании)
8. [Wishlist Service (Список желаемого)](#8-wishlist-service-список-желаемого)
9. [Notifications Service (Уведомления)](#9-notifications-service-уведомления)
10. [Media Service (Медиафайлы и Presigned S3)](#10-media-service-медиафайлы-и-presigned-s3)
11. [API Gateway (Маршрутизация и Rate Limiting)](#11-api-gateway-маршрутизация-и-rate-limiting)
12. [Общие системные эндпоинты (Health & Metrics)](#12-общие-системные-эндпоинты-health--metrics)

---

## 1. Архитектурный обзор взаимодействий

Платформа **FlashMarket** использует гибридную архитектуру взаимодействия:
- **Синхронное взаимодействие (HTTP REST)**: Используется клиентами через API Gateway, а также в критических точках верификации бизнес-политик (например, запрос от `Inventory` в `Drops` для проверки условий flash-распродажи).
- **Кэширование и сессии (Redis)**: Разделено по базам данных:
  - `DB 0`: Сессии Auth, blacklists, distributed rate limiting, CSRF токены.
  - `DB 1`: Кэш дерева категорий Catalog.
  - `DB 2`: Read-Through кэш товарных остатков Inventory.
- **Асинхронное взаимодействие (RabbitMQ Topic Exchange `flashmarket.events`)**:
  - Все сервисы-источники фиксируют события в таблицах `outbox_events` в рамках локальной ACID-транзакции (Transactional Outbox Pattern).
  - Фоновые воркеры считывают `outbox_events` и публикуют сообщения с подтверждением доставки (Publisher Confirms).
  - Консьюмеры гарантируют идемпотентность через таблицу `processed_events` и проверки статусов сущностей.
- **Периодическое обслуживание (Celery Beat & Workers)**: Фоновые задачи на базе Redis/RabbitMQ для экспирации броней и отмены просроченных чекаутов.

---

## 2. Inventory Service (Склад и Резервации)

**Основная роль**: Управление физическими остатками (`total`, `available`, `reserved`, `sold`), пессимистические блокировки (`FOR UPDATE`), жизненный цикл бронирования.

### API Роуты

| Метод и Роут | Доступ | Описание и логика БД | Синхронные связи | Асинхронные события (Outbox) |
| :--- | :--- | :--- | :--- | :--- |
| `POST /api/v1/stocks` | `ADMIN` | Создание или сброс записи стока для `product_id`/`variant_id`. Таблица `stocks`. | Инвалидирует / обновляет кэш остатка в **Redis DB 2**. | — |
| `GET /api/v1/stocks/{product_id}` | `Anonymous` / Все | Получение текущих счетчиков стока. | **Redis DB 2**: Read-Through кэш (при промахе чтение из Postgres). | — |
| `PATCH /api/v1/stocks/{product_id}` | `ADMIN` | Корректировка общего числа `total` с проверкой `available >= 0`. `SELECT ... FOR UPDATE`. | Обновляет кэш в **Redis DB 2**. | — |
| `POST /api/v1/stocks/{product_id}/reserve` | `Owner` / `ADMIN` | 1. `SELECT ... FOR UPDATE` строки стока.<br>2. Проверка доступного остатка.<br>3. `available -= qty`, `reserved += qty`.<br>4. Вставка записи в `reservations` (`status=RESERVED`). | Если передан `drop_id`: синхронный HTTP-вызов `GET /api/v1/drops/id/{drop_id}` в **Drops** для проверки политики участия. | В рамках той же SQL-транзакции записывает `InventoryReserved` в `outbox_events`. |
| `POST /api/v1/stocks/{product_id}/commit` | `ADMIN` (Internal) | 1. `SELECT ... FOR UPDATE` резервации и стока.<br>2. `reserved -= qty`, `sold += qty`.<br>3. Перевод резервации в `COMMITTED`. | Обновляет кэш в **Redis DB 2**. | Записывает `InventoryCommitted` в `outbox_events`. |
| `POST /api/v1/stocks/{product_id}/release` | `Owner` / `ADMIN` | 1. `SELECT ... FOR UPDATE` резервации и стока.<br>2. `reserved -= qty`, `available += qty`.<br>3. Перевод резервации в `RELEASED`. | Обновляет кэш в **Redis DB 2**. | Записывает `ReservationReleased` в `outbox_events`. |

### Обрабатываемые очереди (RabbitMQ Consumer `inventory.events`)
- `orders.OrderCreated`: Привязывает `order_id` к активной резервации.
- `payments.PaymentSucceeded`: Фиксирует покупку (`RESERVED → COMMITTED`, `reserved → sold`).
- `payments.PaymentFailed`: Освобождает бронь (`RESERVED → RELEASED`, `reserved → available`).
- `orders.OrderCancelled`: Освобождает бронь при отмене заказа.

### Фоновые задачи (Celery)
- `flashmarket.inventory.expire_reservations` (очередь `inventory.maintenance`, расписание: каждые 5 сек):
  Выбирает просроченные брони (`SELECT ... WHERE expires_at < NOW() FOR UPDATE SKIP LOCKED`), переводит в `EXPIRED`, возвращает `available` и регистрирует `ReservationReleased` в Outbox.

---

## 3. Orders Service (Заказы и Промокоды)

**Основная роль**: Оформление заказов, расчет скидок по промокодам, чекауты.

### API Роуты

| Метод и Роут | Доступ | Описание и логика БД | Синхронные связи | Асинхронные события (Outbox) |
| :--- | :--- | :--- | :--- | :--- |
| `POST /api/v1/orders` | `Owner` / `ADMIN` | Создание одиночного заказа на основе ранее созданной резервации. Запись в `orders` (`status=PENDING`). | — | Публикует `orders.OrderCreated` через `outbox_events`. |
| `POST /api/v1/orders/batch` | `Owner` / `ADMIN` | Создание группового чекаута из нескольких строк с применением промокода. | — | Публикует пачку `orders.OrderCreated` в `outbox_events`. |
| `GET /api/v1/orders/{order_id}` | `Owner` / `ADMIN` | Чтение заказа и его строк (`order_items`) по UUID. | — | — |
| `GET /api/v1/orders/users/{user_id}` | `Owner` / `ADMIN` | Пагинированный список заказов пользователя. | — | — |
| `POST /api/v1/orders/{order_id}/confirm` | `ADMIN` (Internal) | Ручное/mock подтверждение оплаты заказа (`PENDING → PAID`). | — | — |
| `POST /api/v1/orders/{order_id}/fail` | `ADMIN` (Internal) | Перевод заказа в статус `CANCELLED`. | — | Публикует `orders.OrderCancelled` в `outbox_events`. |
| `POST /api/v1/promocodes` | `ADMIN` | Создание промокода (процентный/фиксированный, лимит использований, даты). | — | — |
| `GET /api/v1/promocodes` | `ADMIN` | Список промокодов с пагинацией. | — | — |
| `GET /api/v1/promocodes/{promo_id}` | `ADMIN` | Детальная информация о промокоде. | — | — |
| `PATCH /api/v1/promocodes/{promo_id}` | `ADMIN` | Редактирование лимитов и дат действия промокода. | — | — |
| `POST /api/v1/promocodes/validate` | `Owner` / `ADMIN` | Проверка валидности промокода и расчет скидки для суммы заказа. | — | — |

### Обрабатываемые очереди (RabbitMQ Consumer `orders.events`)
- `payments.PaymentSucceeded`: Переводит заказ в `PAID`/`CONFIRMED`.
- `payments.PaymentFailed`: Переводит заказ в `CANCELLED`, публикует `orders.OrderCancelled`.
- `inventory.ReservationReleased`: Отменяет ожидающий заказ (`PENDING → CANCELLED`), если бронь истекла.

### Фоновые задачи (Celery)
- `flashmarket.orders.expire_checkouts` (очередь `orders.maintenance`, расписание: каждые 5 сек):
  Находит просроченные по времени чекауты/заказы и отменяет их с генерацией `OrderCancelled`.

---

## 4. Payments Service (Платежи)

**Основная роль**: Проведение платежей, фиксация транзакций, управление mock/external терминальными статусами оплаты.

### API Роуты

| Метод и Роут | Доступ | Описание и логика БД | Синхронные связи | Асинхронные события (Outbox) |
| :--- | :--- | :--- | :--- | :--- |
| `POST /api/v1/payments` | `Owner` / `ADMIN` | Создание платежной сессии для заказа в статусе `PENDING`. Таблица `payments`. | — | — |
| `GET /api/v1/payments/{payment_id}` | `Owner` / `ADMIN` | Получение информации о статусе и сумме платежа. | — | — |
| `GET /api/v1/payments/users/{user_id}` | `Owner` / `ADMIN` | Список платежей пользователя. | — | — |
| `POST /api/v1/payments/{payment_id}/confirm` | `Owner` / `ADMIN` | Перевод платежа в статус `SUCCEEDED`. | — | Публикует `payments.PaymentSucceeded` в Outbox (триггерит списание в Inventory и подтверждение в Orders). |
| `POST /api/v1/payments/{payment_id}/fail` | `Owner` / `ADMIN` | Перевод платежа в статус `FAILED`. | — | Публикует `payments.PaymentFailed` в Outbox (триггерит возврат стока в Inventory и отмену в Orders). |
| `POST /api/v1/payments/{payment_id}/cancel` | `Owner` / `ADMIN` | Перевод платежа в статус `CANCELLED`. | — | Публикует `payments.PaymentFailed` в Outbox. |

---

## 5. Catalog Service (Каталог товаров, Категории, Бренды, Варианты)

**Основная роль**: Витрина товаров, управление категориями, брендами и SKU-вариантами.

### API Роуты

| Метод и Роут | Доступ | Описание и логика БД | Синхронные связи | Асинхронные связи |
| :--- | :--- | :--- | :--- | :--- |
| `GET /api/v1/products` | `Anonymous` / Все | Поиск, фильтрация (по категории, бренду, цене), сортировка и пагинация активных товаров (`status=ACTIVE`). | — | — |
| `GET /api/v1/products/{slug}` | `Anonymous` / Все | Получение карточки товара по slug или UUID. | — | — |
| `POST /api/v1/products/batch` | `Anonymous` / Все | Пакетная гидратация товаров по списку `product_ids` (до 100 шт). | — | — |
| `POST /api/v1/products` | `ADMIN` | Создание товара, генерация slug, сохранение галереи картинок. | — | — |
| `PATCH /api/v1/products/{product_id}` | `ADMIN` | Частичное обновление данных товара. | — | — |
| `DELETE /api/v1/products/{product_id}` | `ADMIN` | Soft delete товара (`status=ARCHIVED`). | — | — |
| `GET /api/v1/categories` | `Anonymous` / Все | Получение полного иерархического дерева категорий. | **Redis DB 1**: чтение кэшированного дерева категорий. | — |
| `POST /api/v1/categories` | `ADMIN` | Создание категории (поддержка `parent_id`). | Инвалидирует кэш в **Redis DB 1**. | — |
| `GET /api/v1/brands` | `Anonymous` / Все | Список брендов с логотипами. | — | — |
| `GET /api/v1/brands/{slug_or_id}` | `Anonymous` / Все | Получение бренда по slug или UUID. | — | — |
| `POST /api/v1/brands` | `ADMIN` | Создание нового бренда. | — | — |
| `PATCH /api/v1/brands/{brand_id}` | `ADMIN` | Редактирование бренда. | — | — |
| `GET /api/v1/products/{id}/variants` | `Anonymous` / Все | Список всех вариантов (SKU) для товара. | — | — |
| `GET /api/v1/products/{id}/variants/{v_id}` | `Anonymous` / Все | Получение конкретного варианта по ID. | — | — |
| `POST /api/v1/products/{id}/variants` | `ADMIN` | Добавление нового варианта (размер/цвет) к товару. | — | — |
| `PATCH /api/v1/products/{id}/variants/{v_id}` | `ADMIN` | Редактирование варианта. | — | — |
| `DELETE /api/v1/products/{id}/variants/{v_id}` | `ADMIN` | Удаление варианта товара. | — | — |

---

## 6. Auth Service (Аутентификация, Пользователи, Сессии, Аудит)

**Основная роль**: Выпуск асимметрично подписанных JWT (EdDSA / RS256), хранение сессий, аудит действий и авторизация.

### API Роуты

| Метод и Роут | Доступ | Описание и логика БД | Синхронные связи | Асинхронные связи |
| :--- | :--- | :--- | :--- | :--- |
| `POST /api/v1/auth/register` | `Anonymous` | Регистрация пользователя, хеширование пароля (Argon2id), создание сессии. | **Redis DB 0**: Rate limit по IP; сохранение сессии. | — |
| `POST /api/v1/auth/login` | `Anonymous` | Аутентификация, создание `LoginSession`, выдача пары Access/Refresh токенов. | **Redis DB 0**: Rate limit по IP и email; сохранение сессии. | — |
| `POST /api/v1/auth/refresh` | `Refresh Cookie` + CSRF | Одноразовая ротация Refresh Token, отзыв старого токена, выдача нового Access Token. | **Redis DB 0**: проверка и атомарная замена токена в цепочке. | — |
| `POST /api/v1/auth/introspect` | `Authenticated` | Проверка активности Access Token и статуса сессии. | **Redis DB 0**: проверка blacklist и активности `session_id`. | — |
| `POST /api/v1/auth/logout` | `Authenticated` | Отзыв сессии текущего клиента, удаление cookies. | **Redis DB 0**: удаление сессии / запись в blacklist. | — |
| `GET /api/v1/users/me` | `Authenticated` | Чтение профиля текущего пользователя. | — | — |
| `PATCH /api/v1/users/me` | `Authenticated` | Обновление личных данных (имя и др.). | — | — |
| `POST /api/v1/users/me/password` | `Authenticated` | Смена пароля с автоматическим отзывом всех остальных сессий. | **Redis DB 0**: массовый отзыв сессий пользователя. | — |
| `GET /api/v1/sessions` | `Authenticated` | Список активных сессий пользователя с пометкой текущей. | Чтение из Postgres и **Redis DB 0**. | — |
| `DELETE /api/v1/sessions/{session_id}` | `Authenticated` | Принудительное завершение конкретной сессии. | **Redis DB 0**: отзыв сессии. | — |
| `DELETE /api/v1/sessions` | `Authenticated` | Принудительное завершение всех сессий пользователя. | **Redis DB 0**: полный отзыв сессий пользователя. | — |
| `GET /api/v1/admin/users` | `ADMIN` | Пагинированный список всех пользователей с фильтрацией по ролям и статусам. | — | — |
| `PATCH /api/v1/admin/users/{id}/role` | `ADMIN` | Изменение роли пользователя (`CUSTOMER` / `ADMIN`). | **Redis DB 0**: сброс прав в активных сессиях. | — |
| `PATCH /api/v1/admin/users/{id}/status` | `ADMIN` | Блокировка/активация аккаунта. | **Redis DB 0**: блокировка сессий. | — |
| `GET /api/v1/admin/audit-events` | `ADMIN` | Журнал событий безопасности (входы, смены паролей, изменения прав). | Чтение из таблицы `audit_events`. | — |
| `GET /.well-known/jwks.json` | `Anonymous` / Все | Публичные ключи для верификации JWT всеми остальными микросервисами платформы без сетевых походов в Auth. | Чтение из in-memory конфигурации JWKS. | — |

---

## 7. Drops Service (Flash-Sale Кампании)

**Основная роль**: Управление временными окнами распродаж (дропами), привязкой акционных товаров и лимитами на пользователя.

### API Роуты

| Метод и Роут | Доступ | Описание и логика БД | Синхронные связи | Асинхронные связи |
| :--- | :--- | :--- | :--- | :--- |
| `GET /api/v1/drops/active` | `Anonymous` / Все | Список активных в данный момент распродаж (`status=ACTIVE`). | — | — |
| `GET /api/v1/drops/upcoming` | `Anonymous` / Все | Список запланированных будущих дропов (`status=SCHEDULED`). | — | — |
| `GET /api/v1/drops/id/{drop_id}` | `Anonymous` / Internal | **Критический роут**: возвращает конфигурацию политики дропа (`max_per_user`, `payment_timeout_seconds`, список товаров). | **Синхронно вызывается сервисом Inventory** перед бронированием остатка. | — |
| `GET /api/v1/drops/{slug}` | `Anonymous` / Все | Страница дропа по slug со списком товаров (скрывает DRAFT и CANCELLED). | — | — |
| `POST /api/v1/admin/drops` | `ADMIN` | Создание новой кампании в статусе `DRAFT`. | — | — |
| `GET /api/v1/admin/drops` | `ADMIN` | Полный список всех дропов для панели управления. | — | — |
| `GET /api/v1/admin/drops/{drop_id}` | `ADMIN` | Получение дропа со всеми товарами и внутренними параметрами. | — | — |
| `PATCH /api/v1/admin/drops/{drop_id}` | `ADMIN` | Редактирование параметров дропа в статусе `DRAFT` или `SCHEDULED`. | — | — |
| `POST /api/v1/admin/drops/{id}/schedule` | `ADMIN` | Перевод статуса `DRAFT → SCHEDULED`. | — | — |
| `POST /api/v1/admin/drops/{id}/start` | `ADMIN` | Перевод статуса `SCHEDULED → ACTIVE` (старт продаж). | — | — |
| `POST /api/v1/admin/drops/{id}/end` | `ADMIN` | Завершение дропа `ACTIVE → ENDED`. | — | — |
| `POST /api/v1/admin/drops/{id}/cancel` | `ADMIN` | Отмена дропа `CANCELLED`. | — | — |
| `POST /api/v1/admin/drops/{id}/items` | `ADMIN` | Добавление товара в дроп (специальная цена, лимит на пользователя). | — | — |
| `DELETE /api/v1/admin/drops/{id}/items/{prod_id}` | `ADMIN` | Удаление товара из дропа. | — | — |

---

## 8. Wishlist Service (Список желаемого)

**Основная роль**: Персональные вишлисты пользователей с защитой от состояний гонки (Race Conditions) через PostgreSQL Advisory Locks.

### API Роуты

| Метод и Роут | Доступ | Описание и логика БД | Синхронные связи | Асинхронные связи |
| :--- | :--- | :--- | :--- | :--- |
| `POST /api/v1/wishlist/users/{user_id}/items` | `Owner` / `ADMIN` | Добавление товара в вишлист пользователя. Использует SHA-256 64-bit advisory lock по `user_id`. | — | — |
| `DELETE /api/v1/wishlist/users/{user_id}/items/{product_id}` | `Owner` / `ADMIN` | Удаление товара из вишлиста пользователя. | — | — |
| `GET /api/v1/wishlist/users/{user_id}/items` | `Owner` / `ADMIN` | Пагинированный список сохраненных товаров пользователя. | — | — |
| `POST /api/v1/wishlist/users/{user_id}/check` | `Owner` / `ADMIN` | Пакетная проверка наличия массива `product_ids` в вишлисте пользователя. | — | — |

---

## 9. Notifications Service (Уведомления)

**Основная роль**: Регистрация, хранение и управление статусом отправки пользовательских уведомлений.

### API Роуты

| Метод и Роут | Доступ | Описание и логика БД | Синхронные связи | Асинхронные события (Outbox) |
| :--- | :--- | :--- | :--- | :--- |
| `POST /api/v1/notifications` | `ADMIN` | Создание системного уведомления для пользователя. Запись в `notifications`. | — | Публикует `notifications.NotificationCreated` в Outbox. |
| `GET /api/v1/notifications/users/{user_id}` | `Owner` / `ADMIN` | Пагинированный список уведомлений пользователя. | — | — |
| `GET /api/v1/notifications/{id}` | `Owner` / `ADMIN` | Получение деталей конкретного уведомления. | — | — |
| `POST /api/v1/notifications/{id}/read` | `Owner` / `ADMIN` | Пометка уведомления как прочитанного (`is_read=True`). | — | — |
| `POST /api/v1/notifications/{id}/send` | `Owner` / `ADMIN` | Эмуляция успешной отправки уведомления (`status=SENT`). | — | Публикует `notifications.NotificationSent` в Outbox. |
| `POST /api/v1/notifications/{id}/fail` | `ADMIN` | Фиксация ошибки отправки (`status=FAILED`). | — | — |

### Обрабатываемые очереди (RabbitMQ Consumer `notifications.events`)
- `orders.OrderCreated`: Создает уведомление об успешном оформлении заказа.
- `orders.OrderCancelled`: Создает уведомление об отмене заказа.

---

## 10. Media Service (Медиафайлы и Presigned S3)

**Основная роль**: Загрузка файлов напрямую в MinIO / S3 через Presigned POST URL, валидация метаданных и привязка к сущностям платформы.

### API Роуты

| Метод и Роут | Доступ | Описание и логика БД | Синхронные связи | Асинхронные связи |
| :--- | :--- | :--- | :--- | :--- |
| `POST /api/v1/media/uploads` | `Authenticated` | Создание записи ассета в статусе `PENDING` и генерация Presigned S3 POST URL + form fields. | **MinIO / S3**: генерация подписи. | — |
| `POST /api/v1/media/assets/{id}/complete` | `Owner` / `ADMIN` | Валидация загруженного в S3 файла (размер, MIME) и перевод в `READY`. | **MinIO / S3**: проверка HeadObject. | — |
| `PATCH /api/v1/media/assets/{id}/binding` | `Owner` / `ADMIN` | Привязка готового ассета к сущности (`PRODUCT`, `BRAND`, `DROP`, `AVATAR`). | — | — |
| `GET /api/v1/media/assets/mine` | `Authenticated` | Список ассетов, загруженных текущим пользователем. | — | — |
| `GET /api/v1/media/admin/assets` | `ADMIN` | Поиск и фильтрация всех медиа-ассетов платформы. | — | — |
| `GET /api/v1/media/assets/{id}` | `Owner` / `ADMIN` / `Public` | Получение метаданных и публичного URL ассета. | — | — |
| `GET /api/v1/media/entities/{type}/{id}/assets` | `Anonymous` / Все | Получение всех активных медиафайлов, привязанных к конкретной сущности (например, товару). | — | — |
| `DELETE /api/v1/media/assets/{id}` | `Owner` / `ADMIN` | Мягкое удаление ассета (`status=DELETED`). | — | — |

---

## 11. API Gateway (Маршрутизация и Rate Limiting)

Единая точка входа (**Nginx** reverse proxy), которая распределяет запросы к микросервисам по префиксам и субдоменам, а также защищает сервисы профилями Rate Limiting.

```text
               ┌─────────────────────── API GATEWAY (Nginx) ───────────────────────┐
               │                                                                   │
               ├── /api/v1/auth/*, /users/*, /sessions/*, /admin/* ──► Auth        │ (Rate: 5 req/s)
               ├── /api/v1/products/*, /categories/*, /brands/* ─────► Catalog     │ (Rate: 50 req/s)
               ├── /api/v1/stocks/* ─────────────────────────────────► Inventory   │ (Rate: 20 req/s)
               ├── /api/v1/orders/*, /promocodes/* ──────────────────► Orders      │ (Rate: 10 req/s)
               ├── /api/v1/payments/* ───────────────────────────────► Payments    │ (Rate: 10 req/s)
               ├── /api/v1/drops/*, /admin/drops/* ──────────────────► Drops       │ (Rate: 50 req/s)
               ├── /api/v1/wishlist/* ───────────────────────────────► Wishlist    │ (Rate: 10 req/s)
               ├── /api/v1/notifications/* ──────────────────────────► Notifs      │ (Rate: 20 req/s)
               ├── /api/v1/media/* ──────────────────────────────────► Media       │ (Rate: 10 req/s)
               └── /* ───────────────────────────────────────────────► Frontend    │ (SPA / Static)
```

### Профили Rate Limiting в Gateway

| Профиль | Обслуживаемые роуты и сервисы | Базовый лимит | Burst (Nodelay) |
| :--- | :--- | :--- | :--- |
| `auth` | Auth, users, sessions, администрирование пользователей | 5 req/s | 10 |
| `transaction` | Orders, payments, promocodes, wishlist, media | 10 req/s | 20 |
| `catalog` | Products, categories, brands, drops | 50 req/s | 100 |
| `general` | Inventory, notifications | 20 req/s | 40 |

---

## 12. Общие системные эндпоинты (Health & Metrics)

Каждый из микросервисов платформы реализует унифицированные роуты наблюдаемости (Observability):

* `GET /health`: Liveness-проба для Docker / Kubernetes (проверяет запуск процесса).
* `GET /health/ready`: Readiness-проба (проверяет доступность PostgreSQL, Redis и RabbitMQ).
* `GET /metrics`: Эндпоинт метрик Prometheus (длительность HTTP-запросов, задержки Outbox, счетчики ошибок, активные соединения).
