/**
 * FlashMarket System Architecture Data Model & Topology
 */

export const NODES = [
  // 1. Client / Edge
  {
    id: "node-component-browser",
    entityId: "component-browser",
    name: "Клиент / Браузер",
    subtitle: "Веб · Мобильные",
    type: "client",
    icon: "browser",
    style: { top: 130, left: 30, width: 100, height: 105 }
  },
  {
    id: "node-component-gateway",
    entityId: "component-gateway",
    name: "NGINX Gateway",
    subtitle: "Шлюз",
    type: "gateway",
    icon: "gateway",
    style: { top: 130, left: 165, width: 100, height: 105 }
  },

  // 2. Microservices
  {
    id: "node-service-auth",
    entityId: "service-auth",
    name: "Auth",
    subtitle: "JWT · Сессии",
    type: "service",
    icon: "auth",
    gridCol: 1,
    gridRow: 1,
    publishes: ["identity.user_registered", "identity.user_logged_in", "identity.session_revoked"],
    consumes: [],
    endpoints: [
      { id: "endpoint-auth-register", method: "POST", path: "/api/v1/auth/register", summary: "Регистрация нового пользователя" },
      { id: "endpoint-auth-login", method: "POST", path: "/api/v1/auth/login", summary: "Аутентификация и выдача JWT" },
      { id: "endpoint-auth-refresh", method: "POST", path: "/api/v1/auth/refresh", summary: "Ротация одноразового refresh-токена" },
      { id: "endpoint-auth-logout", method: "POST", path: "/api/v1/auth/logout", summary: "Отзыв сессии и удаление токенов" },
      { id: "endpoint-auth-me", method: "GET", path: "/api/v1/users/me", summary: "Получение профиля текущего пользователя" }
    ]
  },
  {
    id: "node-service-catalog",
    entityId: "service-catalog",
    name: "Catalog",
    subtitle: "Каталог · Товары",
    type: "service",
    icon: "catalog",
    gridCol: 2,
    gridRow: 1,
    publishes: [],
    consumes: [],
    endpoints: [
      { id: "endpoint-catalog-products", method: "GET", path: "/api/v1/products", summary: "Полнотекстовый поиск и фильтрация товаров" },
      { id: "endpoint-catalog-categories", method: "GET", path: "/api/v1/categories", summary: "Иерархическое дерево категорий" },
      { id: "endpoint-catalog-brands", method: "GET", path: "/api/v1/brands", summary: "Список брендов и коллекций" }
    ]
  },
  {
    id: "node-service-inventory",
    entityId: "service-inventory",
    name: "Inventory",
    subtitle: "Остатки · Брони",
    type: "service",
    icon: "inventory",
    gridCol: 3,
    gridRow: 1,
    publishes: ["inventory.InventoryReserved", "inventory.InventoryCommitted", "inventory.ReservationReleased"],
    consumes: ["orders.OrderCreated", "payments.PaymentSucceeded", "payments.PaymentFailed", "orders.OrderCancelled"],
    endpoints: [
      { id: "endpoint-stock-read", method: "GET", path: "/api/v1/stocks/{product_id}", summary: "Чтение доступных остатков товара" },
      { id: "endpoint-stock-reserve", method: "POST", path: "/api/v1/stocks/{product_id}/reserve", summary: "Бронирование остатков под заказ" },
      { id: "endpoint-stock-release", method: "POST", path: "/api/v1/stocks/{product_id}/release", summary: "Освобождение активной брони" },
      { id: "endpoint-stock-commit", method: "POST", path: "/api/v1/stocks/{product_id}/commit", summary: "Фиксация продажи после успешной оплаты" },
      { id: "endpoint-stock-admin", method: "POST", path: "/api/v1/stocks", summary: "Управление складскими запасами" }
    ]
  },
  {
    id: "node-service-orders",
    entityId: "service-orders",
    name: "Orders",
    subtitle: "Заказы · Промо",
    type: "service",
    icon: "orders",
    gridCol: 4,
    gridRow: 1,
    publishes: ["orders.OrderCreated", "orders.PaymentRequested", "orders.OrderConfirmed", "orders.OrderCancelled"],
    consumes: ["payments.PaymentSucceeded", "payments.PaymentFailed", "inventory.ReservationReleased"],
    endpoints: [
      { id: "endpoint-order-create", method: "POST", path: "/api/v1/orders", summary: "Создание единичного заказа по брони" },
      { id: "endpoint-order-batch", method: "POST", path: "/api/v1/orders/batch", summary: "Оформление корзины (чекаут) с промокодом" },
      { id: "endpoint-order-read", method: "GET", path: "/api/v1/orders/{order_id}", summary: "Получение информации и статуса заказа" },
      { id: "endpoint-order-transition", method: "POST", path: "/api/v1/orders/{order_id}/confirm|fail", summary: "Терминальный переход статуса заказа" },
      { id: "endpoint-promocodes", method: "POST", path: "/api/v1/promocodes/validate", summary: "Проверка и расчет скидки промокода" }
    ]
  },
  {
    id: "node-service-payments",
    entityId: "service-payments",
    name: "Payments",
    subtitle: "Эквайринг",
    type: "service",
    icon: "payments",
    gridCol: 5,
    gridRow: 1,
    publishes: ["payments.PaymentSucceeded", "payments.PaymentFailed"],
    consumes: ["orders.PaymentRequested"],
    endpoints: [
      { id: "endpoint-payment-create", method: "POST", path: "/api/v1/payments", summary: "Создание платежной сессии для заказа" },
      { id: "endpoint-payment-read", method: "GET", path: "/api/v1/payments/{payment_id}", summary: "Получение статуса платежа" },
      { id: "endpoint-payment-transition", method: "POST", path: "/api/v1/payments/{payment_id}/confirm|fail|cancel", summary: "Терминальные переходы статуса оплаты" }
    ]
  },
  {
    id: "node-service-notifications",
    entityId: "service-notifications",
    name: "Notifications",
    subtitle: "Уведомления",
    type: "service",
    icon: "notifications",
    gridCol: 1,
    gridRow: 2,
    publishes: [],
    consumes: ["wishlist.DropAvailable", "orders.OrderCreated", "orders.OrderConfirmed", "orders.OrderCancelled"],
    endpoints: [
      { id: "endpoint-notify-list", method: "GET", path: "/api/v1/notifications/users/{user_id}", summary: "Список уведомлений пользователя" },
      { id: "endpoint-notify-read", method: "POST", path: "/api/v1/notifications/{notification_id}/read", summary: "Пометка уведомления прочитанным" }
    ]
  },
  {
    id: "node-service-wishlist",
    entityId: "service-wishlist",
    name: "Wishlist",
    subtitle: "Избранное",
    type: "service",
    icon: "wishlist",
    gridCol: 2,
    gridRow: 2,
    publishes: ["wishlist.DropAvailable"],
    consumes: ["drops.DropStarted"],
    endpoints: [
      { id: "endpoint-wishlist-toggle", method: "POST", path: "/api/v1/wishlist/users/{user_id}/items", summary: "Добавление или удаление товара из избранного" },
      { id: "endpoint-wishlist-get", method: "GET", path: "/api/v1/wishlist/users/{user_id}/items", summary: "Получение списка избранных товаров пользователя" },
      { id: "endpoint-wishlist-check", method: "POST", path: "/api/v1/wishlist/users/{user_id}/check", summary: "Проверка наличия товаров в избранном" }
    ]
  },
  {
    id: "node-service-drops",
    entityId: "service-drops",
    name: "Drops",
    subtitle: "Лимитированные релизы",
    type: "service",
    icon: "drops",
    gridCol: 3,
    gridRow: 2,
    publishes: ["drops.DropScheduled", "drops.DropStarted", "drops.DropEnded", "drops.DropCancelled"],
    consumes: [],
    endpoints: [
      { id: "endpoint-drops-list", method: "GET", path: "/api/v1/drops/active|upcoming|{slug}", summary: "Получение активных и предстоящих дропов" },
      { id: "endpoint-drops-detail", method: "GET", path: "/api/v1/drops/id/{drop_id}", summary: "Информация о дропе и политике покупки" },
      { id: "endpoint-drops-admin", method: "GET/POST/PATCH/DELETE", path: "/api/v1/admin/drops/*", summary: "Административное управление дропами" }
    ]
  },
  {
    id: "node-service-media",
    entityId: "service-media",
    name: "Media",
    subtitle: "S3 · Изображения",
    type: "service",
    icon: "media",
    gridCol: 4,
    gridRow: 2,
    publishes: [],
    consumes: [],
    endpoints: [
      { id: "endpoint-media-upload", method: "POST", path: "/api/v1/media/uploads", summary: "Генерация presigned S3 POST URL" },
      { id: "endpoint-media-confirm", method: "POST", path: "/api/v1/media/assets/{asset_id}/complete", summary: "Валидация и перевод ассета в статус READY" },
      { id: "endpoint-media-admin", method: "GET", path: "/api/v1/media/admin/assets", summary: "Административный поиск и управление медиа" }
    ]
  },

  // 3. Queue & Background Workers
  {
    id: "node-component-rabbitmq",
    entityId: "component-rabbitmq",
    name: "RabbitMQ",
    subtitle: "Шина событий",
    type: "infra",
    icon: "rabbitmq",
    style: { top: 305, left: 410, width: 150, height: 60 }
  },
  {
    id: "node-component-celery",
    entityId: "component-celery",
    name: "Celery",
    subtitle: "Фоновые воркеры",
    type: "infra",
    icon: "celery",
    style: { top: 305, left: 620, width: 145, height: 60 }
  },

  // 4. Data Stores
  {
    id: "node-component-postgres",
    entityId: "component-postgres",
    name: "PostgreSQL",
    subtitle: "База данных",
    type: "infra",
    icon: "postgres",
    style: { top: 475, left: 230, width: 140, height: 60 }
  },
  {
    id: "node-component-redis",
    entityId: "component-redis",
    name: "Redis",
    subtitle: "Кэш / Состояния",
    type: "infra",
    icon: "redis",
    style: { top: 475, left: 400, width: 135, height: 60 }
  },
  {
    id: "node-component-s3",
    entityId: "component-s3",
    name: "S3 / MinIO",
    subtitle: "Хранилище файлов",
    type: "infra",
    icon: "s3",
    style: { top: 475, left: 565, width: 140, height: 60 }
  },
  {
    id: "node-component-prometheus",
    entityId: "component-prometheus",
    name: "Prometheus",
    subtitle: "Метрики",
    type: "infra",
    icon: "prometheus",
    style: { top: 475, left: 735, width: 145, height: 60 }
  }
];

export const ROUTE_EXPLANATIONS = {
  // Inventory
  "endpoint-stock-reserve": {
    nodes: ["node-component-gateway", "node-service-inventory", "node-service-drops", "node-component-postgres", "node-component-redis", "node-component-rabbitmq"],
    pairs: [
      ["node-component-gateway", "node-service-inventory"],
      ["node-service-inventory", "node-service-drops"],
      ["node-service-inventory", "node-component-postgres"],
      ["node-service-inventory", "node-component-redis"],
      ["node-service-inventory", "node-component-rabbitmq"]
    ],
    modules: [
      { name: "Drops", desc: "Синхронный GET /api/v1/drops/id/{drop_id} — валидация активности дропа и лимита покупки" },
      { name: "PostgreSQL", desc: "Блокировка SELECT ... FOR UPDATE на stocks, списание available, запись в reservations и outbox_events" },
      { name: "Redis", desc: "Обновление кэша остатков с проверкой ревизии через Lua-скрипт" },
      { name: "RabbitMQ", desc: "Публикация события inventory.InventoryReserved из outbox" }
    ]
  },
  "endpoint-stock-commit": {
    nodes: ["node-component-gateway", "node-service-inventory", "node-component-postgres", "node-component-redis", "node-component-rabbitmq"],
    pairs: [
      ["node-component-gateway", "node-service-inventory"],
      ["node-service-inventory", "node-component-postgres"],
      ["node-service-inventory", "node-component-redis"],
      ["node-service-inventory", "node-component-rabbitmq"]
    ],
    modules: [
      { name: "PostgreSQL", desc: "Перевод статуса брони в COMMITTED, перенос остатков reserved -> sold" },
      { name: "Redis", desc: "Обновление счетчика остатков в Redis DB 2" },
      { name: "RabbitMQ", desc: "Публикация события inventory.InventoryCommitted из outbox" }
    ]
  },
  "endpoint-stock-release": {
    nodes: ["node-component-gateway", "node-service-inventory", "node-component-postgres", "node-component-redis", "node-component-rabbitmq", "node-service-orders"],
    pairs: [
      ["node-component-gateway", "node-service-inventory"],
      ["node-service-inventory", "node-component-postgres"],
      ["node-service-inventory", "node-component-redis"],
      ["node-service-inventory", "node-component-rabbitmq"],
      ["node-service-orders", "node-component-rabbitmq"]
    ],
    modules: [
      { name: "PostgreSQL", desc: "Перевод брони в RELEASED, возврат остатков reserved -> available" },
      { name: "Redis", desc: "Сброс и обновление кэша остатков в Redis DB 2" },
      { name: "RabbitMQ", desc: "Публикация события inventory.ReservationReleased (слушает: Orders)" }
    ]
  },
  "endpoint-stock-read": {
    nodes: ["node-component-gateway", "node-service-inventory", "node-component-redis", "node-component-postgres"],
    pairs: [
      ["node-component-gateway", "node-service-inventory"],
      ["node-service-inventory", "node-component-redis"],
      ["node-service-inventory", "node-component-postgres"]
    ],
    modules: [
      { name: "Redis", desc: "Read-Through чтение кэша остатков" },
      { name: "PostgreSQL", desc: "Чтение таблицы stocks при промахе кэша (fail-open)" }
    ]
  },
  "endpoint-stock-admin": {
    nodes: ["node-component-gateway", "node-service-inventory", "node-component-postgres", "node-component-redis"],
    pairs: [
      ["node-component-gateway", "node-service-inventory"],
      ["node-service-inventory", "node-component-postgres"],
      ["node-service-inventory", "node-component-redis"]
    ],
    modules: [
      { name: "PostgreSQL", desc: "Создание или обновление записей в таблице stocks" },
      { name: "Redis", desc: "Инвалидация кэша остатков в Redis DB 2" }
    ]
  },

  // Orders
  "endpoint-order-create": {
    nodes: ["node-component-gateway", "node-service-orders", "node-component-postgres", "node-component-rabbitmq", "node-service-inventory", "node-service-payments", "node-service-notifications"],
    pairs: [
      ["node-component-gateway", "node-service-orders"],
      ["node-service-orders", "node-component-postgres"],
      ["node-service-orders", "node-component-rabbitmq"],
      ["node-service-inventory", "node-component-rabbitmq"],
      ["node-service-payments", "node-component-rabbitmq"],
      ["node-service-notifications", "node-component-rabbitmq"]
    ],
    modules: [
      { name: "PostgreSQL", desc: "Создание записи в orders со статусом AWAITING_PAYMENT" },
      { name: "RabbitMQ", desc: "Публикация событий orders.OrderCreated (слушают: Inventory, Notifications) и orders.PaymentRequested (слушает: Payments)" }
    ]
  },
  "endpoint-order-batch": {
    nodes: ["node-component-gateway", "node-service-orders", "node-component-postgres", "node-component-rabbitmq", "node-service-inventory", "node-service-payments", "node-service-notifications"],
    pairs: [
      ["node-component-gateway", "node-service-orders"],
      ["node-service-orders", "node-component-postgres"],
      ["node-service-orders", "node-component-rabbitmq"],
      ["node-service-inventory", "node-component-rabbitmq"],
      ["node-service-payments", "node-component-rabbitmq"],
      ["node-service-notifications", "node-component-rabbitmq"]
    ],
    modules: [
      { name: "PostgreSQL", desc: "Атомарное сохранение позиций заказа, фиксация использования промокода" },
      { name: "RabbitMQ", desc: "Публикация событий orders.OrderCreated и orders.PaymentRequested для каждой позиции" }
    ]
  },
  "endpoint-order-read": {
    nodes: ["node-component-gateway", "node-service-orders", "node-component-postgres"],
    pairs: [
      ["node-component-gateway", "node-service-orders"],
      ["node-service-orders", "node-component-postgres"]
    ],
    modules: [
      { name: "PostgreSQL", desc: "Чтение таблицы orders по order_id или user_id" }
    ]
  },
  "endpoint-order-transition": {
    nodes: ["node-component-gateway", "node-service-orders", "node-component-postgres", "node-component-rabbitmq", "node-service-inventory", "node-service-notifications"],
    pairs: [
      ["node-component-gateway", "node-service-orders"],
      ["node-service-orders", "node-component-postgres"],
      ["node-service-orders", "node-component-rabbitmq"],
      ["node-service-inventory", "node-component-rabbitmq"],
      ["node-service-notifications", "node-component-rabbitmq"]
    ],
    modules: [
      { name: "PostgreSQL", desc: "Обновление статуса заказа (CONFIRMED или CANCELLED)" },
      { name: "RabbitMQ", desc: "Публикация события orders.OrderConfirmed или orders.OrderCancelled" }
    ]
  },
  "endpoint-promocodes": {
    nodes: ["node-component-gateway", "node-service-orders", "node-component-postgres"],
    pairs: [
      ["node-component-gateway", "node-service-orders"],
      ["node-service-orders", "node-component-postgres"]
    ],
    modules: [
      { name: "PostgreSQL", desc: "Валидация срока действия, лимитов использования и расчет скидки" }
    ]
  },

  // Payments
  "endpoint-payment-create": {
    nodes: ["node-component-gateway", "node-service-payments", "node-component-postgres"],
    pairs: [
      ["node-component-gateway", "node-service-payments"],
      ["node-service-payments", "node-component-postgres"]
    ],
    modules: [
      { name: "PostgreSQL", desc: "Создание записи в таблице payments со статусом PENDING" }
    ]
  },
  "endpoint-payment-read": {
    nodes: ["node-component-gateway", "node-service-payments", "node-component-postgres"],
    pairs: [
      ["node-component-gateway", "node-service-payments"],
      ["node-service-payments", "node-component-postgres"]
    ],
    modules: [
      { name: "PostgreSQL", desc: "Чтение таблицы payments по payment_id" }
    ]
  },
  "endpoint-payment-transition": {
    nodes: ["node-component-gateway", "node-service-payments", "node-component-postgres", "node-component-rabbitmq", "node-service-orders", "node-service-inventory"],
    pairs: [
      ["node-component-gateway", "node-service-payments"],
      ["node-service-payments", "node-component-postgres"],
      ["node-service-payments", "node-component-rabbitmq"],
      ["node-service-orders", "node-component-rabbitmq"],
      ["node-service-inventory", "node-component-rabbitmq"]
    ],
    modules: [
      { name: "PostgreSQL", desc: "Перевод платежа в статус SUCCEEDED или FAILED" },
      { name: "RabbitMQ", desc: "Публикация события payments.PaymentSucceeded / payments.PaymentFailed (слушают: Orders, Inventory)" }
    ]
  },

  // Media
  "endpoint-media-upload": {
    nodes: ["node-component-gateway", "node-service-media", "node-component-postgres", "node-component-s3"],
    pairs: [
      ["node-component-gateway", "node-service-media"],
      ["node-service-media", "node-component-postgres"],
      ["node-service-media", "node-component-s3"]
    ],
    modules: [
      { name: "S3 / MinIO", desc: "Генерация presigned POST URL и политик валидации для прямой загрузки" },
      { name: "PostgreSQL", desc: "Создание метаданных в media_assets со статусом PENDING" }
    ]
  },
  "endpoint-media-confirm": {
    nodes: ["node-component-gateway", "node-service-media", "node-component-postgres", "node-component-s3"],
    pairs: [
      ["node-component-gateway", "node-service-media"],
      ["node-service-media", "node-component-postgres"],
      ["node-service-media", "node-component-s3"]
    ],
    modules: [
      { name: "S3 / MinIO", desc: "Проверка наличия объекта в хранилище, чтение сигнатуры и валидация размеров" },
      { name: "PostgreSQL", desc: "Перевод записи media_assets в статус READY" }
    ]
  },
  "endpoint-media-admin": {
    nodes: ["node-component-gateway", "node-service-media", "node-component-postgres"],
    pairs: [
      ["node-component-gateway", "node-service-media"],
      ["node-service-media", "node-component-postgres"]
    ],
    modules: [
      { name: "PostgreSQL", desc: "Поиск, фильтрация и пагинация по таблице media_assets" }
    ]
  },

  // Auth
  "endpoint-auth-register": {
    nodes: ["node-component-gateway", "node-service-auth", "node-component-postgres", "node-component-redis", "node-component-rabbitmq"],
    pairs: [
      ["node-component-gateway", "node-service-auth"],
      ["node-service-auth", "node-component-postgres"],
      ["node-service-auth", "node-component-redis"],
      ["node-service-auth", "node-component-rabbitmq"]
    ],
    modules: [
      { name: "PostgreSQL", desc: "Проверка уникальности email/логина и сохранение хэша Argon2id" },
      { name: "Redis", desc: "Инкремент счетчика rate limit" },
      { name: "RabbitMQ", desc: "Публикация события identity.user_registered из outbox" }
    ]
  },
  "endpoint-auth-login": {
    nodes: ["node-component-gateway", "node-service-auth", "node-component-postgres", "node-component-redis", "node-component-rabbitmq"],
    pairs: [
      ["node-component-gateway", "node-service-auth"],
      ["node-service-auth", "node-component-postgres"],
      ["node-service-auth", "node-component-redis"],
      ["node-service-auth", "node-component-rabbitmq"]
    ],
    modules: [
      { name: "PostgreSQL", desc: "Верификация пароля Argon2id, создание сессии и refresh-токена" },
      { name: "Redis", desc: "Сохранение активной сессии и проверка счетчиков запросов" },
      { name: "RabbitMQ", desc: "Публикация события identity.user_logged_in из outbox" }
    ]
  },
  "endpoint-auth-refresh": {
    nodes: ["node-component-gateway", "node-service-auth", "node-component-postgres", "node-component-redis"],
    pairs: [
      ["node-component-gateway", "node-service-auth"],
      ["node-service-auth", "node-component-postgres"],
      ["node-service-auth", "node-component-redis"]
    ],
    modules: [
      { name: "PostgreSQL", desc: "Проверка семейства refresh-токена, аннулирование использованного и выпуск нового" },
      { name: "Redis", desc: "Обновление времени активности сессии (touch)" }
    ]
  },
  "endpoint-auth-logout": {
    nodes: ["node-component-gateway", "node-service-auth", "node-component-postgres", "node-component-redis", "node-component-rabbitmq"],
    pairs: [
      ["node-component-gateway", "node-service-auth"],
      ["node-service-auth", "node-component-postgres"],
      ["node-service-auth", "node-component-redis"],
      ["node-service-auth", "node-component-rabbitmq"]
    ],
    modules: [
      { name: "PostgreSQL", desc: "Пометка сессии и цепочки refresh-токенов как отозванных" },
      { name: "Redis", desc: "Удаление сессии из кэша активных сессий" },
      { name: "RabbitMQ", desc: "Публикация события identity.session_revoked из outbox" }
    ]
  },
  "endpoint-auth-me": {
    nodes: ["node-component-gateway", "node-service-auth", "node-component-redis", "node-component-postgres"],
    pairs: [
      ["node-component-gateway", "node-service-auth"],
      ["node-service-auth", "node-component-redis"],
      ["node-service-auth", "node-component-postgres"]
    ],
    modules: [
      { name: "Redis", desc: "Проверка валидности сессии в кэше" },
      { name: "PostgreSQL", desc: "Чтение профиля пользователя из таблицы users" }
    ]
  },

  // Catalog
  "endpoint-catalog-products": {
    nodes: ["node-component-gateway", "node-service-catalog", "node-component-postgres"],
    pairs: [
      ["node-component-gateway", "node-service-catalog"],
      ["node-service-catalog", "node-component-postgres"]
    ],
    modules: [
      { name: "PostgreSQL", desc: "Полнотекстовый поиск tsvector по каталогу товаров, фильтрация по категориям и брендам" }
    ]
  },
  "endpoint-catalog-categories": {
    nodes: ["node-component-gateway", "node-service-catalog", "node-component-redis", "node-component-postgres"],
    pairs: [
      ["node-component-gateway", "node-service-catalog"],
      ["node-service-catalog", "node-component-redis"],
      ["node-service-catalog", "node-component-postgres"]
    ],
    modules: [
      { name: "Redis", desc: "Read-Through чтение кэшированного дерева категорий" },
      { name: "PostgreSQL", desc: "Чтение таблицы categories при промахе кэша" }
    ]
  },
  "endpoint-catalog-brands": {
    nodes: ["node-component-gateway", "node-service-catalog", "node-component-postgres"],
    pairs: [
      ["node-component-gateway", "node-service-catalog"],
      ["node-service-catalog", "node-component-postgres"]
    ],
    modules: [
      { name: "PostgreSQL", desc: "Выборка активных брендов из таблицы brands" }
    ]
  },

  // Wishlist
  "endpoint-wishlist-toggle": {
    nodes: ["node-component-gateway", "node-service-wishlist", "node-component-postgres"],
    pairs: [
      ["node-component-gateway", "node-service-wishlist"],
      ["node-service-wishlist", "node-component-postgres"]
    ],
    modules: [
      { name: "PostgreSQL", desc: "Вставка или удаление записи в таблице wishlist_items" }
    ]
  },
  "endpoint-wishlist-get": {
    nodes: ["node-component-gateway", "node-service-wishlist", "node-component-postgres"],
    pairs: [
      ["node-component-gateway", "node-service-wishlist"],
      ["node-service-wishlist", "node-component-postgres"]
    ],
    modules: [
      { name: "PostgreSQL", desc: "Выборка товаров пользователя из таблицы wishlist_items" }
    ]
  },
  "endpoint-wishlist-check": {
    nodes: ["node-component-gateway", "node-service-wishlist", "node-component-postgres"],
    pairs: [
      ["node-component-gateway", "node-service-wishlist"],
      ["node-service-wishlist", "node-component-postgres"]
    ],
    modules: [
      { name: "PostgreSQL", desc: "Проверка списка product_id на принадлежность избранному пользователя" }
    ]
  },

  // Drops
  "endpoint-drops-list": {
    nodes: ["node-component-gateway", "node-service-drops", "node-component-postgres"],
    pairs: [
      ["node-component-gateway", "node-service-drops"],
      ["node-service-drops", "node-component-postgres"]
    ],
    modules: [
      { name: "PostgreSQL", desc: "Выборка дропов по статусам SCHEDULED / ACTIVE / ENDED" }
    ]
  },
  "endpoint-drops-detail": {
    nodes: ["node-component-gateway", "node-service-drops", "node-component-postgres"],
    pairs: [
      ["node-component-gateway", "node-service-drops"],
      ["node-service-drops", "node-component-postgres"]
    ],
    modules: [
      { name: "PostgreSQL", desc: "Чтение параметров дропа, списка товаров и лимита покупки на пользователя" }
    ]
  },
  "endpoint-drops-admin": {
    nodes: ["node-component-gateway", "node-service-drops", "node-component-postgres", "node-component-rabbitmq"],
    pairs: [
      ["node-component-gateway", "node-service-drops"],
      ["node-service-drops", "node-component-postgres"],
      ["node-service-drops", "node-component-rabbitmq"]
    ],
    modules: [
      { name: "PostgreSQL", desc: "Создание/редактирование дропа и состава товаров" },
      { name: "RabbitMQ", desc: "Публикация события drops.DropScheduled при переводе в расписание" }
    ]
  },

  // Notifications
  "endpoint-notify-list": {
    nodes: ["node-component-gateway", "node-service-notifications", "node-component-postgres"],
    pairs: [
      ["node-component-gateway", "node-service-notifications"],
      ["node-service-notifications", "node-component-postgres"]
    ],
    modules: [
      { name: "PostgreSQL", desc: "Чтение списка уведомлений пользователя из таблицы notifications" }
    ]
  },
  "endpoint-notify-read": {
    nodes: ["node-component-gateway", "node-service-notifications", "node-component-postgres"],
    pairs: [
      ["node-component-gateway", "node-service-notifications"],
      ["node-service-notifications", "node-component-postgres"]
    ],
    modules: [
      { name: "PostgreSQL", desc: "Обновление статуса is_read в таблице notifications" }
    ]
  }
};

export const CELERY_TASKS = [
  {
    id: "celery-stock-expire",
    name: "flashmarket.inventory.expire_reservations",
    queue: "inventory.maintenance",
    schedule: "5 сек",
    scheduleFull: "Каждые 5 секунд",
    nodes: ["node-component-celery", "node-service-inventory", "node-component-postgres", "node-component-redis", "node-component-rabbitmq", "node-service-orders"],
    pairs: [
      ["node-component-celery", "node-service-inventory"],
      ["node-service-inventory", "node-component-postgres"],
      ["node-service-inventory", "node-component-redis"],
      ["node-service-inventory", "node-component-rabbitmq"],
      ["node-service-orders", "node-component-rabbitmq"]
    ],
    modules: [
      { name: "Celery Beat", desc: "Запуск каждые 5 сек (очередь inventory.maintenance)" },
      { name: "PostgreSQL", desc: "Поиск просроченных броней со статусом RESERVED через SELECT ... FOR UPDATE SKIP LOCKED" },
      { name: "Redis", desc: "Возврат стока reserved -> available в кэше Redis DB 2" },
      { name: "RabbitMQ", desc: "Публикация события inventory.ReservationReleased (слушает: Orders)" }
    ]
  },
  {
    id: "celery-drops-scheduler",
    name: "flashmarket.drops.run_scheduler_tick",
    queue: "drops.maintenance",
    schedule: "10 сек",
    scheduleFull: "Каждые 10 секунд",
    nodes: ["node-component-celery", "node-service-drops", "node-component-postgres", "node-component-rabbitmq", "node-service-wishlist", "node-service-notifications"],
    pairs: [
      ["node-component-celery", "node-service-drops"],
      ["node-service-drops", "node-component-postgres"],
      ["node-service-drops", "node-component-rabbitmq"],
      ["node-service-wishlist", "node-component-rabbitmq"],
      ["node-service-notifications", "node-component-rabbitmq"]
    ],
    modules: [
      { name: "Celery Beat", desc: "Запуск каждые 10 сек (очередь drops.maintenance)" },
      { name: "PostgreSQL", desc: "Перевод дропов SCHEDULED -> ACTIVE и ACTIVE -> ENDED по времени" },
      { name: "RabbitMQ", desc: "Публикация события drops.DropStarted (слушает: Wishlist) или drops.DropEnded" }
    ]
  },
  {
    id: "celery-media-cleanup",
    name: "flashmarket.media.cleanup_expired_assets",
    queue: "media.maintenance",
    schedule: "30 сек",
    scheduleFull: "Каждые 30 секунд",
    nodes: ["node-component-celery", "node-service-media", "node-component-postgres", "node-component-s3"],
    pairs: [
      ["node-component-celery", "node-service-media"],
      ["node-service-media", "node-component-postgres"],
      ["node-service-media", "node-component-s3"]
    ],
    modules: [
      { name: "Celery Beat", desc: "Запуск каждые 30 сек (очередь media.maintenance)" },
      { name: "Media", desc: "Выборка просроченных PENDING загрузок (>15 мин) и записей в статусе DELETING" },
      { name: "S3 / MinIO", desc: "Удаление объектов из S3-хранилища" },
      { name: "PostgreSQL", desc: "Обновление статуса записей media_assets на EXPIRED / DELETED" }
    ]
  },
  {
    id: "celery-auth-cleanup",
    name: "flashmarket.auth.cleanup_expired_data",
    queue: "auth.maintenance",
    schedule: "1 час",
    scheduleFull: "Каждые 3600 секунд",
    nodes: ["node-component-celery", "node-service-auth", "node-component-postgres"],
    pairs: [
      ["node-component-celery", "node-service-auth"],
      ["node-service-auth", "node-component-postgres"]
    ],
    modules: [
      { name: "Celery Beat", desc: "Запуск каждый 1 час (очередь auth.maintenance)" },
      { name: "Auth", desc: "Поиск просроченных сессий и использованных refresh-токенов" },
      { name: "PostgreSQL", desc: "Удаление устаревших строк из таблиц sessions и refresh_tokens" }
    ]
  }
];

export const SERVICE_EVENT_HANDLERS = {
  "service-wishlist": [
    {
      id: "handler-wishlist-drop-started",
      name: "drops.DropStarted",
      nodes: ["node-service-drops", "node-component-rabbitmq", "node-service-wishlist", "node-component-postgres", "node-service-notifications"],
      pairs: [
        ["node-service-drops", "node-component-rabbitmq"],
        ["node-service-wishlist", "node-component-rabbitmq"],
        ["node-service-wishlist", "node-component-postgres"],
        ["node-service-notifications", "node-component-rabbitmq"]
      ],
      modules: [
        { name: "RabbitMQ", desc: "Входящее событие drops.DropStarted от сервиса Drops" },
        { name: "PostgreSQL", desc: "Поиск пользователей с товарами дропа в избранном и запись событий в outbox" },
        { name: "RabbitMQ", desc: "Публикация персональных событий wishlist.DropAvailable (слушает: Notifications)" }
      ]
    }
  ],
  "service-inventory": [
    {
      id: "handler-inventory-order-created",
      name: "orders.OrderCreated",
      nodes: ["node-service-orders", "node-component-rabbitmq", "node-service-inventory", "node-component-postgres"],
      pairs: [
        ["node-service-orders", "node-component-rabbitmq"],
        ["node-service-inventory", "node-component-rabbitmq"],
        ["node-service-inventory", "node-component-postgres"]
      ],
      modules: [
        { name: "RabbitMQ", desc: "Входящее событие orders.OrderCreated от сервиса Orders" },
        { name: "PostgreSQL", desc: "Привязка order_id к reservation_id в таблице reservations" }
      ]
    },
    {
      id: "handler-inventory-payment-succeeded",
      name: "payments.PaymentSucceeded",
      nodes: ["node-service-payments", "node-component-rabbitmq", "node-service-inventory", "node-component-postgres", "node-component-redis"],
      pairs: [
        ["node-service-payments", "node-component-rabbitmq"],
        ["node-service-inventory", "node-component-rabbitmq"],
        ["node-service-inventory", "node-component-postgres"],
        ["node-service-inventory", "node-component-redis"]
      ],
      modules: [
        { name: "RabbitMQ", desc: "Входящее событие payments.PaymentSucceeded от Payments" },
        { name: "PostgreSQL", desc: "Перевод брони в COMMITTED, списание остатка (reserved -> sold)" },
        { name: "Redis", desc: "Обновление счетчика доступных остатков" },
        { name: "RabbitMQ", desc: "Публикация события inventory.InventoryCommitted" }
      ]
    },
    {
      id: "handler-inventory-payment-failed",
      name: "payments.PaymentFailed",
      nodes: ["node-service-payments", "node-component-rabbitmq", "node-service-inventory", "node-component-postgres", "node-component-redis"],
      pairs: [
        ["node-service-payments", "node-component-rabbitmq"],
        ["node-service-inventory", "node-component-rabbitmq"],
        ["node-service-inventory", "node-component-postgres"],
        ["node-service-inventory", "node-component-redis"]
      ],
      modules: [
        { name: "RabbitMQ", desc: "Входящее событие payments.PaymentFailed от Payments" },
        { name: "PostgreSQL", desc: "Перевод брони в RELEASED, возврат остатка (reserved -> available)" },
        { name: "Redis", desc: "Обновление кэша остатков" },
        { name: "RabbitMQ", desc: "Публикация события inventory.ReservationReleased (слушает: Orders)" }
      ]
    },
    {
      id: "handler-inventory-order-cancelled",
      name: "orders.OrderCancelled",
      nodes: ["node-service-orders", "node-component-rabbitmq", "node-service-inventory", "node-component-postgres", "node-component-redis"],
      pairs: [
        ["node-service-orders", "node-component-rabbitmq"],
        ["node-service-inventory", "node-component-rabbitmq"],
        ["node-service-inventory", "node-component-postgres"],
        ["node-service-inventory", "node-component-redis"]
      ],
      modules: [
        { name: "RabbitMQ", desc: "Входящее событие orders.OrderCancelled от Orders" },
        { name: "PostgreSQL", desc: "Освобождение брони, возврат остатка (reserved -> available)" },
        { name: "Redis", desc: "Обновление кэша остатков" },
        { name: "RabbitMQ", desc: "Публикация события inventory.ReservationReleased (слушает: Orders)" }
      ]
    }
  ],
  "service-orders": [
    {
      id: "handler-orders-payment-succeeded",
      name: "payments.PaymentSucceeded",
      nodes: ["node-service-payments", "node-component-rabbitmq", "node-service-orders", "node-component-postgres", "node-service-notifications"],
      pairs: [
        ["node-service-payments", "node-component-rabbitmq"],
        ["node-service-orders", "node-component-rabbitmq"],
        ["node-service-orders", "node-component-postgres"],
        ["node-service-notifications", "node-component-rabbitmq"]
      ],
      modules: [
        { name: "RabbitMQ", desc: "Входящее событие payments.PaymentSucceeded от Payments" },
        { name: "PostgreSQL", desc: "Обновление статуса заказа на CONFIRMED" },
        { name: "RabbitMQ", desc: "Публикация события orders.OrderConfirmed (слушает: Notifications)" }
      ]
    },
    {
      id: "handler-orders-payment-failed",
      name: "payments.PaymentFailed",
      nodes: ["node-service-payments", "node-component-rabbitmq", "node-service-orders", "node-component-postgres", "node-service-inventory"],
      pairs: [
        ["node-service-payments", "node-component-rabbitmq"],
        ["node-service-orders", "node-component-rabbitmq"],
        ["node-service-orders", "node-component-postgres"],
        ["node-service-inventory", "node-component-rabbitmq"]
      ],
      modules: [
        { name: "RabbitMQ", desc: "Входящее событие payments.PaymentFailed от Payments" },
        { name: "PostgreSQL", desc: "Обновление статуса заказа на CANCELLED, откат промокода" },
        { name: "RabbitMQ", desc: "Публикация события orders.OrderCancelled (слушают: Inventory, Notifications)" }
      ]
    },
    {
      id: "handler-orders-reservation-released",
      name: "inventory.ReservationReleased",
      nodes: ["node-service-inventory", "node-component-rabbitmq", "node-service-orders", "node-component-postgres"],
      pairs: [
        ["node-service-inventory", "node-component-rabbitmq"],
        ["node-service-orders", "node-component-rabbitmq"],
        ["node-service-orders", "node-component-postgres"]
      ],
      modules: [
        { name: "RabbitMQ", desc: "Входящее событие inventory.ReservationReleased от Inventory" },
        { name: "PostgreSQL", desc: "Отмена заказа со статусом CANCELLED, откат промокода" },
        { name: "RabbitMQ", desc: "Публикация события orders.OrderCancelled (слушает: Notifications)" }
      ]
    }
  ],
  "service-notifications": [
    {
      id: "handler-notifications-drop-available",
      name: "wishlist.DropAvailable",
      nodes: ["node-service-wishlist", "node-component-rabbitmq", "node-service-notifications", "node-component-postgres"],
      pairs: [
        ["node-service-wishlist", "node-component-rabbitmq"],
        ["node-service-notifications", "node-component-rabbitmq"],
        ["node-service-notifications", "node-component-postgres"]
      ],
      modules: [
        { name: "RabbitMQ", desc: "Входящее событие wishlist.DropAvailable от Wishlist" },
        { name: "PostgreSQL", desc: "Создание персонального уведомления DROP_ALERT в таблице notifications" }
      ]
    },
    {
      id: "handler-notifications-order-created",
      name: "orders.OrderCreated",
      nodes: ["node-service-orders", "node-component-rabbitmq", "node-service-notifications", "node-component-postgres"],
      pairs: [
        ["node-service-orders", "node-component-rabbitmq"],
        ["node-service-notifications", "node-component-rabbitmq"],
        ["node-service-notifications", "node-component-postgres"]
      ],
      modules: [
        { name: "RabbitMQ", desc: "Входящее событие orders.OrderCreated от Orders" },
        { name: "PostgreSQL", desc: "Создание уведомления об ожидании оплаты заказа" }
      ]
    },
    {
      id: "handler-notifications-order-confirmed",
      name: "orders.OrderConfirmed",
      nodes: ["node-service-orders", "node-component-rabbitmq", "node-service-notifications", "node-component-postgres"],
      pairs: [
        ["node-service-orders", "node-component-rabbitmq"],
        ["node-service-notifications", "node-component-rabbitmq"],
        ["node-service-notifications", "node-component-postgres"]
      ],
      modules: [
        { name: "RabbitMQ", desc: "Входящее событие orders.OrderConfirmed от Orders" },
        { name: "PostgreSQL", desc: "Создание уведомления об успешной оплате и подтверждении заказа" }
      ]
    },
    {
      id: "handler-notifications-order-cancelled",
      name: "orders.OrderCancelled",
      nodes: ["node-service-orders", "node-component-rabbitmq", "node-service-notifications", "node-component-postgres"],
      pairs: [
        ["node-service-orders", "node-component-rabbitmq"],
        ["node-service-notifications", "node-component-rabbitmq"],
        ["node-service-notifications", "node-component-postgres"]
      ],
      modules: [
        { name: "RabbitMQ", desc: "Входящее событие orders.OrderCancelled от Orders" },
        { name: "PostgreSQL", desc: "Создание уведомления об отмене заказа" }
      ]
    }
  ],
  "service-payments": [
    {
      id: "handler-payments-requested",
      name: "orders.PaymentRequested",
      nodes: ["node-service-orders", "node-component-rabbitmq", "node-service-payments", "node-component-postgres"],
      pairs: [
        ["node-service-orders", "node-component-rabbitmq"],
        ["node-service-payments", "node-component-rabbitmq"],
        ["node-service-payments", "node-component-postgres"]
      ],
      modules: [
        { name: "RabbitMQ", desc: "Входящее событие orders.PaymentRequested от Orders" },
        { name: "PostgreSQL", desc: "Создание платежной записи со статусом PENDING" }
      ]
    }
  ]
};
