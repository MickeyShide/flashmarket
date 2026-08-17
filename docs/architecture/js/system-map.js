import { $, $$, createEntityIndex, escapeHtml } from "./utils.js";

const ICONS = {
  "service-inventory": `<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#2E7D32" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m7.5 4.27 9 5.15"/><path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z"/><path d="m3.3 7 8.7 5 8.7-5"/><path d="M12 22V12"/></svg>`,
  "service-auth": `<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#1565C0" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="18" height="11" x="3" y="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>`,
  "service-catalog": `<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#1565C0" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="7" height="7" x="3" y="3" rx="1"/><rect width="7" height="7" x="14" y="3" rx="1"/><rect width="7" height="7" x="14" y="14" rx="1"/><rect width="7" height="7" x="3" y="14" rx="1"/></svg>`,
  "service-orders": `<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#E65100" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="8" cy="21" r="1"/><circle cx="19" cy="21" r="1"/><path d="M2.05 2.05h2l2.66 12.42a2 2 0 0 0 2 1.58h9.78a2 2 0 0 0 1.95-1.57l1.65-7.43H5.12"/></svg>`,
  "service-payments": `<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#6A1B9A" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="20" height="14" x="2" y="5" rx="2"/><line x1="2" x2="22" y1="10" y2="10"/></svg>`,
  "service-notifications": `<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#E65100" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/></svg>`,
  "service-wishlist": `<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#C2185B" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z"/></svg>`,
  "service-drops": `<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#00897B" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2H2v10l9.29 9.29c.94.94 2.48.94 3.42 0l6.58-6.58c.94-.94.94-2.48 0-3.42L12 2Z"/><circle cx="7" cy="7" r=".5" fill="currentColor"/></svg>`,
  "service-media": `<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#3949AB" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="18" height="18" x="3" y="3" rx="2" ry="2"/><circle cx="9" cy="9" r="2"/><path d="m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21"/></svg>`,
  "component-gateway": `<svg width="26" height="26" viewBox="0 0 24 24" fill="none"><path d="M12 2L2 7v10l10 5 10-5V7L12 2z" fill="#009639"/><path d="M8 8v8l8-8v8" stroke="#ffffff" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
  "component-rabbitmq": `<svg width="26" height="26" viewBox="0 0 24 24" fill="none"><path d="M12 2L4 7v10l8 5 8-5V7l-8-5z" fill="#FF6600"/><circle cx="12" cy="12" r="3" fill="#ffffff"/></svg>`,
  "component-celery": `<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#FF6600" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>`,
  "component-postgres": `<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#336791" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/><path d="M3 12c0 1.66 4 3 9 3s9-1.34 9-3"/></svg>`,
  "component-redis": `<svg width="26" height="26" viewBox="0 0 24 24" fill="none"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" stroke="#D82C20" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
  "component-s3": `<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#2E7D32" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 11V6a2 2 0 0 0-2-2H7a2 2 0 0 0-2 2v5"/><path d="M21 11H3v8a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-8Z"/><path d="M10 15h4"/></svg>`,
  "component-prometheus": `<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#E65100" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z"/></svg>`,
};

const ROUTE_EXPLANATIONS = {
  // 1. Inventory Routes
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

  // 2. Orders Routes
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

  // 3. Payments Routes
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

  // 4. Media Routes
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
  "endpoint-media-complete": {
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
  "endpoint-media-bind": {
    nodes: ["node-component-gateway", "node-service-media", "node-component-postgres"],
    pairs: [
      ["node-component-gateway", "node-service-media"],
      ["node-service-media", "node-component-postgres"]
    ],
    modules: [
      { name: "PostgreSQL", desc: "Обновление entity_type, entity_id и purpose в media_assets" }
    ]
  },
  "endpoint-media-delete": {
    nodes: ["node-component-gateway", "node-service-media", "node-component-postgres", "node-component-s3"],
    pairs: [
      ["node-component-gateway", "node-service-media"],
      ["node-service-media", "node-component-postgres"],
      ["node-service-media", "node-component-s3"]
    ],
    modules: [
      { name: "PostgreSQL", desc: "Перевод записи media_assets в статус DELETING" },
      { name: "S3 / MinIO", desc: "Асинхронное удаление объекта через фоновый воркер Celery" }
    ]
  },
  "endpoint-media-read": {
    nodes: ["node-component-gateway", "node-service-media", "node-component-postgres", "node-component-s3"],
    pairs: [
      ["node-component-gateway", "node-service-media"],
      ["node-service-media", "node-component-postgres"],
      ["node-service-media", "node-component-s3"]
    ],
    modules: [
      { name: "PostgreSQL", desc: "Чтение метаданных из таблицы media_assets" },
      { name: "S3 / MinIO", desc: "Отдача публичной ссылки на объект S3" }
    ]
  },

  // 5. Drops Routes
  "endpoint-drop-policy": {
    nodes: ["node-component-gateway", "node-service-drops", "node-service-inventory", "node-component-postgres"],
    pairs: [
      ["node-component-gateway", "node-service-drops"],
      ["node-service-drops", "node-component-postgres"],
      ["node-service-inventory", "node-service-drops"]
    ],
    modules: [
      { name: "Inventory", desc: "Синхронный межсервисный вызов перед созданием брони" },
      { name: "PostgreSQL", desc: "Чтение таблиц drops и drop_items (активность, лимиты, таймаут)" }
    ]
  },
  "endpoint-drop-public": {
    nodes: ["node-component-gateway", "node-service-drops", "node-component-postgres"],
    pairs: [
      ["node-component-gateway", "node-service-drops"],
      ["node-service-drops", "node-component-postgres"]
    ],
    modules: [
      { name: "PostgreSQL", desc: "Выборка дропов по статусам SCHEDULED / ACTIVE / ENDED" }
    ]
  },
  "endpoint-drop-admin": {
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

  // 6. Auth Routes
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
      { name: "Redis", desc: "Сохранение активной сессии в Redis DB 0" },
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
      { name: "Redis", desc: "Обновление времени активности сессии в Redis DB 0" }
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
      { name: "Redis", desc: "Удаление сессии из кэша активных токенов" },
      { name: "RabbitMQ", desc: "Публикация события identity.session_revoked из outbox" }
    ]
  },
  "endpoint-auth-profile": {
    nodes: ["node-component-gateway", "node-service-auth", "node-component-redis", "node-component-postgres"],
    pairs: [
      ["node-component-gateway", "node-service-auth"],
      ["node-service-auth", "node-component-redis"],
      ["node-service-auth", "node-component-postgres"]
    ],
    modules: [
      { name: "Redis", desc: "Проверка валидности сессии в кэше" },
      { name: "PostgreSQL", desc: "Чтение и обновление профиля в таблице users" }
    ]
  },
  "endpoint-auth-sessions": {
    nodes: ["node-component-gateway", "node-service-auth", "node-component-postgres", "node-component-redis"],
    pairs: [
      ["node-component-gateway", "node-service-auth"],
      ["node-service-auth", "node-component-postgres"],
      ["node-service-auth", "node-component-redis"]
    ],
    modules: [
      { name: "PostgreSQL", desc: "Чтение и отзыв сессий в таблице sessions" },
      { name: "Redis", desc: "Инвалидация отозванных сессий в кэше" }
    ]
  },
  "endpoint-auth-admin": {
    nodes: ["node-component-gateway", "node-service-auth", "node-component-postgres"],
    pairs: [
      ["node-component-gateway", "node-service-auth"],
      ["node-service-auth", "node-component-postgres"]
    ],
    modules: [
      { name: "PostgreSQL", desc: "Обновление прав и блокировка в таблице users, аудит действий" }
    ]
  },

  // 7. Catalog Routes
  "endpoint-products-list": {
    nodes: ["node-component-gateway", "node-service-catalog", "node-component-postgres"],
    pairs: [
      ["node-component-gateway", "node-service-catalog"],
      ["node-service-catalog", "node-component-postgres"]
    ],
    modules: [
      { name: "PostgreSQL", desc: "Полнотекстовый поиск tsvector по каталогу товаров, фильтрация по категориям и брендам" }
    ]
  },
  "endpoint-products-detail": {
    nodes: ["node-component-gateway", "node-service-catalog", "node-component-postgres"],
    pairs: [
      ["node-component-gateway", "node-service-catalog"],
      ["node-service-catalog", "node-component-postgres"]
    ],
    modules: [
      { name: "PostgreSQL", desc: "Чтение products, categories, brands, variants" }
    ]
  },
  "endpoint-products-batch": {
    nodes: ["node-component-gateway", "node-service-catalog", "node-component-postgres"],
    pairs: [
      ["node-component-gateway", "node-service-catalog"],
      ["node-service-catalog", "node-component-postgres"]
    ],
    modules: [
      { name: "PostgreSQL", desc: "Чтение списка товаров WHERE id IN (...)" }
    ]
  },
  "endpoint-products-admin": {
    nodes: ["node-component-gateway", "node-service-catalog", "node-component-postgres"],
    pairs: [
      ["node-component-gateway", "node-service-catalog"],
      ["node-service-catalog", "node-component-postgres"]
    ],
    modules: [
      { name: "PostgreSQL", desc: "Создание, обновление или архивация товаров и SKU-вариантов" }
    ]
  },
  "endpoint-categories": {
    nodes: ["node-component-gateway", "node-service-catalog", "node-component-redis", "node-component-postgres"],
    pairs: [
      ["node-component-gateway", "node-service-catalog"],
      ["node-service-catalog", "node-component-redis"],
      ["node-service-catalog", "node-component-postgres"]
    ],
    modules: [
      { name: "Redis", desc: "Read-Through кэш категорий в Redis DB 1" },
      { name: "PostgreSQL", desc: "Чтение таблицы categories при промахе кэша" }
    ]
  },
  "endpoint-brands": {
    nodes: ["node-component-gateway", "node-service-catalog", "node-component-postgres"],
    pairs: [
      ["node-component-gateway", "node-service-catalog"],
      ["node-service-catalog", "node-component-postgres"]
    ],
    modules: [
      { name: "PostgreSQL", desc: "Выборка активных брендов из таблицы brands" }
    ]
  },
  "endpoint-variants": {
    nodes: ["node-component-gateway", "node-service-catalog", "node-component-postgres"],
    pairs: [
      ["node-component-gateway", "node-service-catalog"],
      ["node-service-catalog", "node-component-postgres"]
    ],
    modules: [
      { name: "PostgreSQL", desc: "Чтение таблицы product_variants" }
    ]
  },

  // 8. Wishlist Routes
  "endpoint-wishlist-items": {
    nodes: ["node-component-gateway", "node-service-wishlist", "node-component-postgres"],
    pairs: [
      ["node-component-gateway", "node-service-wishlist"],
      ["node-service-wishlist", "node-component-postgres"]
    ],
    modules: [
      { name: "PostgreSQL", desc: "Чтение, добавление или удаление строк в таблице wishlist_items" }
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

  // 9. Notifications Routes
  "endpoint-notification-list": {
    nodes: ["node-component-gateway", "node-service-notifications", "node-component-postgres"],
    pairs: [
      ["node-component-gateway", "node-service-notifications"],
      ["node-service-notifications", "node-component-postgres"]
    ],
    modules: [
      { name: "PostgreSQL", desc: "Чтение списка уведомлений пользователя из таблицы notifications" }
    ]
  },
  "endpoint-notification-read": {
    nodes: ["node-component-gateway", "node-service-notifications", "node-component-postgres"],
    pairs: [
      ["node-component-gateway", "node-service-notifications"],
      ["node-service-notifications", "node-component-postgres"]
    ],
    modules: [
      { name: "PostgreSQL", desc: "Обновление статуса is_read в таблице notifications" }
    ]
  },
  "endpoint-notification-transition": {
    nodes: ["node-component-gateway", "node-service-notifications", "node-component-postgres"],
    pairs: [
      ["node-component-gateway", "node-service-notifications"],
      ["node-service-notifications", "node-component-postgres"]
    ],
    modules: [
      { name: "PostgreSQL", desc: "Обновление статуса доставки в таблице notifications" }
    ]
  }
};

export function highlightNodes(nodeIds = []) {
  $$(".node-card").forEach((n) => n.classList.remove("flow-highlight"));
  nodeIds.forEach((id) => {
    const el = document.getElementById(id) || $(`[data-node-id="${id}"]`);
    if (el) el.classList.add("flow-highlight");
  });
}

const BASE_NODE_POSITIONS = {
  'node-component-browser': { x: 20, y: 140, width: 100, height: 110 },
  'node-component-gateway': { x: 155, y: 140, width: 100, height: 110 },
  'node-service-auth': { x: 310, y: 64, width: 98, height: 78 },
  'node-service-catalog': { x: 420, y: 64, width: 98, height: 78 },
  'node-service-inventory': { x: 531, y: 64, width: 98, height: 78 },
  'node-service-orders': { x: 641, y: 64, width: 98, height: 78 },
  'node-service-payments': { x: 752, y: 64, width: 98, height: 78 },
  'node-service-notifications': { x: 310, y: 154, width: 98, height: 78 },
  'node-service-wishlist': { x: 420, y: 154, width: 98, height: 78 },
  'node-service-drops': { x: 531, y: 154, width: 98, height: 78 },
  'node-service-media': { x: 641, y: 154, width: 98, height: 78 },
  'node-component-rabbitmq': { x: 450, y: 310, width: 140, height: 60 },
  'node-component-celery': { x: 650, y: 310, width: 130, height: 60 },
  'node-component-postgres': { x: 100, y: 480, width: 150, height: 60 },
  'node-component-redis': { x: 290, y: 480, width: 140, height: 60 },
  'node-component-s3': { x: 470, y: 480, width: 150, height: 60 },
  'node-component-prometheus': { x: 660, y: 480, width: 150, height: 60 },
};

const ALL_SERVICES = [
  'node-service-auth',
  'node-service-catalog',
  'node-service-inventory',
  'node-service-orders',
  'node-service-payments',
  'node-service-notifications',
  'node-service-wishlist',
  'node-service-drops',
  'node-service-media',
];

const ALL_QUEUES = [
  'node-component-rabbitmq',
  'node-component-celery',
];

const ALL_DBS = [
  'node-component-postgres',
  'node-component-redis',
  'node-component-s3',
  'node-component-prometheus',
];

export function computeCompactLayout(isolatedNodes) {
  const offsets = {};
  Object.keys(BASE_NODE_POSITIONS).forEach((id) => {
    offsets[id] = { x: 0, y: 0 };
  });

  if (!isolatedNodes || isolatedNodes.length === 0) {
    return {
      offsets,
      boundingBox: {
        minX: 0,
        minY: 0,
        maxX: 1000,
        maxY: 620,
        width: 1000,
        height: 620,
        centerX: 500,
        centerY: 310,
      },
    };
  }

  const activeSet = new Set(isolatedNodes);
  const hasBrowser = activeSet.has('node-component-browser');
  const hasGateway = activeSet.has('node-component-gateway');
  const activeServices = ALL_SERVICES.filter((id) => activeSet.has(id));
  const activeQueues = ALL_QUEUES.filter((id) => activeSet.has(id));
  const activeDbs = ALL_DBS.filter((id) => activeSet.has(id));

  const target = {};
  const startX = 30;
  const startY = 30;

  // 1. Position Browser & Gateway on the left column
  let servicesStartX = startX;
  if (hasBrowser && hasGateway) {
    target['node-component-browser'] = { x: startX, y: startY };
    target['node-component-gateway'] = { x: startX + 115, y: startY };
    servicesStartX = startX + 235;
  } else if (hasGateway) {
    target['node-component-gateway'] = { x: startX, y: startY };
    servicesStartX = startX + 125;
  } else if (hasBrowser) {
    target['node-component-browser'] = { x: startX, y: startY };
    servicesStartX = startX + 125;
  }

  // 2. Position Microservices in Row 1 horizontally aligned
  const serviceCardW = 98;
  const serviceGapX = 18;
  const sY = hasGateway || hasBrowser ? startY + 16 : startY;

  activeServices.forEach((sId, i) => {
    target[sId] = { x: servicesStartX + i * (serviceCardW + serviceGapX), y: sY };
  });

  const servicesEndX = servicesStartX + Math.max(1, activeServices.length) * (serviceCardW + serviceGapX) - serviceGapX;
  const servicesEndY = sY + 78;

  // 3. Position Queues & Workers (RabbitMQ / Celery) in Row 2 directly below services
  const queueY = servicesEndY + 44;
  const queueCardW = 140;
  const queueGapX = 18;

  activeQueues.forEach((qId, i) => {
    target[qId] = { x: servicesStartX + i * (queueCardW + queueGapX), y: queueY };
  });

  const queueEndY = activeQueues.length > 0 ? queueY + 60 : servicesEndY;

  // 4. Position Databases & Storage (PostgreSQL, Redis, S3, Prometheus) in Row 3 directly below queues
  const dbY = queueEndY + 44;
  const dbCardW = 145;
  const dbGapX = 18;

  activeDbs.forEach((dbId, i) => {
    target[dbId] = { x: servicesStartX + i * (dbCardW + dbGapX), y: dbY };
  });

  // Calculate delta offsets and active bounding box
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;

  isolatedNodes.forEach((id) => {
    const base = BASE_NODE_POSITIONS[id];
    if (!base) return;
    const t = target[id] || base;
    offsets[id] = { x: Math.round(t.x - base.x), y: Math.round(t.y - base.y) };

    const nodeW = base.width;
    const nodeH = base.height;
    if (t.x < minX) minX = t.x;
    if (t.y < minY) minY = t.y;
    if (t.x + nodeW > maxX) maxX = t.x + nodeW;
    if (t.y + nodeH > maxY) maxY = t.y + nodeH;
  });

  if (!isFinite(minX)) {
    minX = 0;
    minY = 0;
    maxX = 1000;
    maxY = 620;
  }

  const boundingBox = {
    minX,
    minY,
    maxX,
    maxY,
    width: maxX - minX,
    height: maxY - minY,
    centerX: (minX + maxX) / 2,
    centerY: (minY + maxY) / 2,
  };

  return { offsets, boundingBox };
}

let svgMorphFrame = null;
export function startSvgMorphLoop() {
  if (svgMorphFrame) cancelAnimationFrame(svgMorphFrame);
  const startTime = performance.now();
  const duration = 520;
  const loop = (t) => {
    renderConnections();
    if (t - startTime < duration) {
      svgMorphFrame = requestAnimationFrame(loop);
    } else {
      renderConnections();
      svgMorphFrame = null;
    }
  };
  svgMorphFrame = requestAnimationFrame(loop);
}

export function isolateConnections({ nodeId = null, pairs = null, nodes = [] } = {}) {
  const svg = $("#connections-svg");
  const nodesLayer = $(".nodes-layer");
  if (!svg) return;

  if (!nodeId && (!pairs || !pairs.length) && (!nodes || !nodes.length)) {
    window._currentIsolation = null;
    svg.classList.remove("isolate-mode", "has-focus");
    if (nodesLayer) nodesLayer.classList.remove("isolate-nodes-mode");
    $$(".node-card").forEach((card) => {
      card.style.transform = "";
      card.classList.remove("flow-highlight", "node-isolated-hidden", "node-isolated-active", "is-selected");
    });
    window.dispatchEvent(new CustomEvent("flashmarket:reset-map"));
    startSvgMorphLoop();
    return;
  }

  svg.classList.add("isolate-mode");
  if (nodesLayer) nodesLayer.classList.add("isolate-nodes-mode");

  const cleanNodeId = nodeId ? (nodeId.startsWith("node-") ? nodeId : `node-${nodeId}`) : null;

  const activeNodeIds = new Set();
  const SERVICE_EVENT_INTERACTIONS = {
    "node-service-auth": ["node-service-notifications"],
    "node-service-catalog": ["node-service-wishlist", "node-service-drops"],
    "node-service-inventory": ["node-service-orders", "node-service-payments", "node-service-drops"],
    "node-service-orders": ["node-service-payments", "node-service-inventory", "node-service-notifications"],
    "node-service-payments": ["node-service-orders", "node-service-notifications"],
    "node-service-notifications": ["node-service-auth", "node-service-orders", "node-service-payments", "node-service-drops"],
    "node-service-wishlist": ["node-service-catalog", "node-service-drops"],
    "node-service-drops": ["node-service-inventory", "node-service-catalog", "node-service-wishlist", "node-service-notifications", "node-component-celery"],
    "node-service-media": ["node-component-celery", "node-component-s3"],
  };

  if (cleanNodeId) {
    activeNodeIds.add(cleanNodeId);
    if (cleanNodeId.startsWith("node-service-")) {
      activeNodeIds.add("node-component-gateway");
      activeNodeIds.add("node-component-rabbitmq");
      activeNodeIds.add("node-component-postgres");
      if (["node-service-inventory", "node-service-auth", "node-service-catalog"].includes(cleanNodeId)) {
        activeNodeIds.add("node-component-redis");
      }
      const related = SERVICE_EVENT_INTERACTIONS[cleanNodeId] || [];
      related.forEach((r) => activeNodeIds.add(r));
    }
  }
  if (nodes && nodes.length) {
    nodes.forEach((n) => activeNodeIds.add(n.startsWith("node-") ? n : `node-${n}`));
  }
  if (pairs && pairs.length) {
    pairs.forEach(([pFrom, pTo]) => {
      activeNodeIds.add(pFrom.startsWith("node-") ? pFrom : `node-${pFrom}`);
      activeNodeIds.add(pTo.startsWith("node-") ? pTo : `node-${pTo}`);
    });
  }

  // Filter SVG paths to ONLY active connections and add connected endpoints
  $$(".connections-svg path").forEach((p) => {
    const from = p.dataset.from;
    const to = p.dataset.to;

    let isMatch = false;

    if (pairs && pairs.length) {
      isMatch = pairs.some(([pFrom, pTo]) => (
        (from === pFrom && to === pTo) || (from === pTo && to === pFrom)
      ));
    } else if (cleanNodeId) {
      isMatch = (from === cleanNodeId || to === cleanNodeId || from === nodeId || to === nodeId);
    }

    if (isMatch) {
      p.classList.add("conn-active-isolate");
      if (from) activeNodeIds.add(from.startsWith("node-") ? from : `node-${from}`);
      if (to) activeNodeIds.add(to.startsWith("node-") ? to : `node-${to}`);
    }
  });

  window._currentIsolation = {
    nodeId,
    pairs,
    nodes,
    activeNodeIds: Array.from(activeNodeIds),
  };

  // Calculate compact layout and apply transforms to ALL connected nodes
  const activeArr = Array.from(activeNodeIds);
  const { offsets, boundingBox } = computeCompactLayout(activeArr);

  // Apply transforms to active cards and hide inactive cards
  $$(".node-card").forEach((card) => {
    const cId = card.id || card.dataset.nodeId;
    const cleanCId = cId ? (cId.startsWith("node-") ? cId : `node-${cId}`) : null;
    if (activeNodeIds.has(cId) || activeNodeIds.has(cleanCId)) {
      const off = offsets[cId] || offsets[cleanCId] || { x: 0, y: 0 };
      card.style.transform = `translate3d(${off.x}px, ${off.y}px, 0)`;
      card.classList.add("node-isolated-active", "flow-highlight");
      card.classList.remove("node-isolated-hidden");
    } else {
      card.style.transform = "";
      card.classList.add("node-isolated-hidden");
      card.classList.remove("node-isolated-active", "flow-highlight", "is-selected");
    }
  });

  window.dispatchEvent(new CustomEvent("flashmarket:fit-map", { detail: { boundingBox } }));
  startSvgMorphLoop();
}

const CELERY_TASKS = [
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

const SERVICE_EVENT_HANDLERS = {
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

function getModuleIcon(name = '') {
  const n = name.toLowerCase();
  if (n.includes('rabbit')) return ICONS['component-rabbitmq'] || '';
  if (n.includes('postgre') || n.includes('postgres') || n.includes('pg_')) return ICONS['component-postgres'] || '';
  if (n.includes('redis')) return ICONS['component-redis'] || '';
  if (n.includes('s3') || n.includes('minio') || n.includes('storage')) return ICONS['component-s3'] || '';
  if (n.includes('prometheus') || n.includes('metrics')) return ICONS['component-prometheus'] || '';
  if (n.includes('celery') || n.includes('worker') || n.includes('beat')) return ICONS['component-celery'] || '';
  if (n.includes('nginx') || n.includes('gateway')) return ICONS['component-gateway'] || '';
  if (n.includes('auth')) return ICONS['service-auth'] || '';
  if (n.includes('catalog')) return ICONS['service-catalog'] || '';
  if (n.includes('inventory')) return ICONS['service-inventory'] || '';
  if (n.includes('order')) return ICONS['service-orders'] || '';
  if (n.includes('payment')) return ICONS['service-payments'] || '';
  if (n.includes('notif')) return ICONS['service-notifications'] || '';
  if (n.includes('wishlist')) return ICONS['service-wishlist'] || '';
  if (n.includes('drop')) return ICONS['service-drops'] || '';
  if (n.includes('media')) return ICONS['service-media'] || '';
  return ICONS['component-gateway'] || '';
}

function renderModuleCards(modules = []) {
  if (!modules || !modules.length) return "";
  return `
    <div class="route-module-list">
      ${modules.map((m) => `
        <div class="route-module-item">
          <div class="route-module-icon">
            ${getModuleIcon(m.name)}
          </div>
          <div class="route-module-content">
            <span class="route-module-name">${escapeHtml(m.name)}</span>
            <span class="route-module-desc">${escapeHtml(m.desc)}</span>
          </div>
        </div>
      `).join("")}
    </div>
  `;
}

export function updateInspector(nodeId, data, index) {
  const entity = index.get(nodeId);
  if (!entity) return;

  const nameEl = $("#inspector-name");
  const typeEl = $("#inspector-type");
  const avatarEl = $("#inspector-avatar");
  const respEl = $("#inspector-responsibility");
  const eventsSec = $("#inspector-events-section");
  const eventsEl = $("#inspector-events");
  const storageEl = $("#inspector-storage");
  const routesSec = $("#inspector-routes-section");
  const routesTitleEl = $("#inspector-routes-title") || (routesSec ? routesSec.querySelector(".section-title") : null);
  const routesEl = $("#inspector-routes");
  const routeDetailEl = $("#inspector-route-detail-content");
  const viewMain = $("#inspector-view-main");
  const viewDetail = $("#inspector-view-detail");
  const detailBreadcrumbsEl = $("#inspector-detail-breadcrumbs");
  const detailBackBtn = $("#inspector-detail-back-btn");

  if (avatarEl) {
    avatarEl.innerHTML = ICONS[nodeId] || ICONS["service-inventory"];
  }

  // Reset to Step 1 (Main Service View)
  if (viewMain) viewMain.style.display = "flex";
  if (viewDetail) viewDetail.style.display = "none";

  if (detailBackBtn) {
    detailBackBtn.onclick = (e) => {
      e.stopPropagation();
      if (viewDetail) viewDetail.style.display = "none";
      if (viewMain) viewMain.style.display = "flex";
      if (routesEl) {
        $$(".route-pill-btn", routesEl).forEach((b) => b.classList.remove("is-active"));
      }
      isolateConnections({ nodeId });
    };
  }

  // SPECIAL CASE: Celery Task Framework
  if (entity.id === "component-celery" || nodeId === "component-celery" || nodeId === "node-component-celery") {
    if (nameEl) nameEl.textContent = "Celery";
    if (typeEl) typeEl.textContent = "Фоновые воркеры & Beat";
    if (respEl) respEl.textContent = "Периодические фоновые команды (Celery Beat) и межсервисное обслуживание через изолированный брокер /flashmarket-tasks.";

    if (eventsSec && eventsEl) {
      eventsSec.style.display = "block";
      eventsEl.innerHTML = `
        <div style="display:flex;flex-direction:column;gap:4px">
          <span style="font-size:9.5px;font-weight:800;color:var(--amber);letter-spacing:0.5px">ОЧЕРЕДИ ОБСЛУЖИВАНИЯ:</span>
          <div style="display:flex;flex-wrap:wrap;gap:4px">
            <span class="event-chip">inventory.maintenance</span>
            <span class="event-chip">drops.maintenance</span>
            <span class="event-chip">media.maintenance</span>
            <span class="event-chip">auth.maintenance</span>
          </div>
        </div>`;
    }

    if (storageEl) storageEl.style.display = "none";

    if (routesSec && routesEl) {
      routesSec.style.display = "block";
      if (routesTitleEl) routesTitleEl.textContent = "ПЕРИОДИЧЕСКИЕ ТАСКИ (CELERY BEAT)";

      routesEl.innerHTML = CELERY_TASKS.map((task) => `
        <button type="button" class="route-pill-btn" data-task-id="${escapeHtml(task.id)}">
          <strong class="method-badge" style="background:#FFF3E0;color:#EA580C;font-size:8px">${escapeHtml(task.schedule)}</strong>
          <span class="route-path-text">${escapeHtml(task.name)}</span>
        </button>
      `).join("");

      $$(".route-pill-btn", routesEl).forEach((btn) => {
        btn.addEventListener("click", (e) => {
          e.stopPropagation();
          $$(".route-pill-btn", routesEl).forEach((b) => b.classList.remove("is-active"));
          btn.classList.add("is-active");

          const taskId = btn.dataset.taskId;
          const task = CELERY_TASKS.find((t) => t.id === taskId);
          if (!task) return;

          if (detailBreadcrumbsEl) {
            detailBreadcrumbsEl.innerHTML = `
              <div class="detail-badge-route">
                <strong class="method-badge" style="background:#FFF3E0;color:#EA580C;font-size:8px">${escapeHtml(task.schedule)}</strong>
                <span class="detail-badge-route-path">${escapeHtml(task.name)}</span>
              </div>
            `;
          }

          if (routeDetailEl) {
            routeDetailEl.innerHTML = renderModuleCards(task.modules);
          }

          if (viewMain) viewMain.style.display = "none";
          if (viewDetail) viewDetail.style.display = "flex";

          isolateConnections({ pairs: task.pairs, nodes: task.nodes });
        });
      });
    }

    return;
  }

  // STANDARD MICROSERVICES
  if (entity.entityType === "services") {
    if (routesTitleEl) routesTitleEl.textContent = "РОУТЫ И СОБЫТИЯ";

    const published = (entity.publishesEventIds || []).map((id) => index.get(id)).filter(Boolean);
    const consumed = (entity.consumesEventIds || []).map((id) => index.get(id)).filter(Boolean);
    const endpoints = (entity.endpointIds || []).map((id) => index.get(id)).filter(Boolean);

    if (nameEl) nameEl.textContent = entity.name;
    if (typeEl) typeEl.textContent = "Микросервис";
    if (respEl) respEl.textContent = entity.responsibility;

    if (eventsSec && eventsEl) {
      if (!published.length && !consumed.length) {
        eventsSec.style.display = "none";
        eventsEl.innerHTML = "";
      } else {
        eventsSec.style.display = "block";
        let eventsHtml = "";
        if (published.length) {
          eventsHtml += `<div style="margin-bottom:6px"><span style="font-size:9.5px;font-weight:800;color:var(--amber);letter-spacing:0.5px">ОТПРАВЛЯЕТ (OUTBOX):</span><div style="display:flex;flex-wrap:wrap;gap:4px;margin-top:3px">` +
            published.map((e) => `<span class="event-chip" style="background:#FFFBEB;color:#B45309;border-color:#FDE68A">${escapeHtml(e.name)}</span>`).join("") + `</div></div>`;
        }
        if (consumed.length) {
          eventsHtml += `<div><span style="font-size:9.5px;font-weight:800;color:var(--blue);letter-spacing:0.5px">СЛУШАЕТ (INBOX):</span><div style="display:flex;flex-wrap:wrap;gap:4px;margin-top:3px">` +
            consumed.map((e) => `<span class="event-chip event-chip-btn" data-event-name="${escapeHtml(e.name)}" style="background:#EFF6FF;color:#1D4ED8;border-color:#BFDBFE;cursor:pointer;user-select:none">${escapeHtml(e.name)}</span>`).join("") + `</div></div>`;
        }
        eventsEl.innerHTML = eventsHtml;

        // Make inbox event chips click to trigger the corresponding event handler button
        $$(".event-chip-btn", eventsEl).forEach((chip) => {
          chip.addEventListener("click", () => {
            const evName = chip.dataset.eventName;
            const targetBtn = Array.from($$(".route-pill-btn", routesEl)).find((b) => b.textContent.includes(evName));
            if (targetBtn) {
              targetBtn.click();
            }
          });
        });
      }
    }

    if (storageEl) {
      storageEl.style.display = "none";
    }

    if (routesSec && routesEl) {
      routesSec.style.display = "block";
      const handlers = SERVICE_EVENT_HANDLERS[entity.id] || [];

      let buttonsHtml = "";

      // 1. API Endpoints
      if (endpoints.length) {
        buttonsHtml += endpoints.map((ep) => `
          <button type="button" class="route-pill-btn" data-type="route" data-endpoint-id="${escapeHtml(ep.id)}">
            <strong class="method-badge method-${ep.method.toLowerCase()}">${escapeHtml(ep.method)}</strong>
            <span class="route-path-text">${escapeHtml(ep.path)}</span>
          </button>
        `).join("");
      }

      // 2. Async Event Handlers
      if (handlers.length) {
        buttonsHtml += handlers.map((h) => `
          <button type="button" class="route-pill-btn" data-type="event" data-handler-id="${escapeHtml(h.id)}">
            <strong class="method-badge" style="background:#FFF3E0;color:#EA580C;font-size:8px">EVENT</strong>
            <span class="route-path-text">Событие: ${escapeHtml(h.name)}</span>
          </button>
        `).join("");
      }

      if (!endpoints.length && !handlers.length) {
        routesEl.innerHTML = `<span class="dim" style="font-size:11px">Внутренний сервис</span>`;
      } else {
        routesEl.innerHTML = buttonsHtml;
      }

      // Attach click listeners to all route and event buttons
      $$(".route-pill-btn", routesEl).forEach((btn) => {
        btn.addEventListener("click", (e) => {
          e.stopPropagation();
          $$(".route-pill-btn", routesEl).forEach((b) => b.classList.remove("is-active"));
          btn.classList.add("is-active");

          const type = btn.dataset.type;
          const serviceIconSvg = ICONS[nodeId] || ICONS[entity.id] || ICONS["service-inventory"];

          if (type === "event") {
            const handlerId = btn.dataset.handlerId;
            const handler = handlers.find((h) => h.id === handlerId);
            if (!handler) return;

            if (detailBreadcrumbsEl) {
              detailBreadcrumbsEl.innerHTML = `
                <div class="detail-badge-route">
                  <strong class="method-badge" style="background:#FFF3E0;color:#EA580C;font-size:8px">EVENT</strong>
                  <span class="detail-badge-route-path">${escapeHtml(handler.name)}</span>
                </div>
              `;
            }

            if (routeDetailEl) {
              routeDetailEl.innerHTML = renderModuleCards(handler.modules);
            }

            if (viewMain) viewMain.style.display = "none";
            if (viewDetail) viewDetail.style.display = "flex";

            isolateConnections({ pairs: handler.pairs, nodes: handler.nodes });
          } else {
            // Standard route
            const epId = btn.dataset.endpointId;
            const ep = index.get(epId);

            const sNodeId = entity.id.startsWith("node-") ? entity.id : `node-${entity.id}`;
            const fallbackNodes = ["node-component-gateway", sNodeId];
            const fallbackPairs = [["node-component-gateway", sNodeId]];

            const expl = ROUTE_EXPLANATIONS[epId] || {
              modules: [
                { name: entity.name, desc: ep?.summary || "Обрабатывает API запрос" }
              ],
              nodes: fallbackNodes,
              pairs: fallbackPairs
            };

            if (detailBreadcrumbsEl && ep) {
              detailBreadcrumbsEl.innerHTML = `
                <div class="detail-badge-route">
                  <strong class="method-badge method-${ep.method.toLowerCase()}">${escapeHtml(ep.method)}</strong>
                  <span class="detail-badge-route-path">${escapeHtml(ep.path)}</span>
                </div>
              `;
            }

            if (routeDetailEl) {
              routeDetailEl.innerHTML = renderModuleCards(expl.modules);
            }

            if (viewMain) viewMain.style.display = "none";
            if (viewDetail) viewDetail.style.display = "flex";

            isolateConnections({ pairs: expl.pairs, nodes: expl.nodes });
          }
        });
      });
    }
  } else {
    if (nameEl) nameEl.textContent = entity.name;
    if (typeEl) typeEl.textContent = entity.kind || "Infrastructure";
    if (respEl) respEl.textContent = entity.summary || entity.responsibility || `${entity.name} component in FlashMarket stack.`;

    if (eventsSec) {
      eventsSec.style.display = "none";
    }
    if (eventsEl) {
      eventsEl.innerHTML = "";
    }

    if (storageEl) {
      storageEl.innerHTML = `<span class="storage-chip">${escapeHtml(entity.name)}</span>`;
    }

    if (routesSec) {
      routesSec.style.display = "none";
    }
  }
}

export function openInspector(nodeId, data, index) {
  updateInspector(nodeId, data, index);
  const sidebar = $("#inspector-sidebar");
  if (sidebar) {
    sidebar.classList.add("is-open");
  }
  isolateConnections({ nodeId });
}

export function closeInspector() {
  const sidebar = $("#inspector-sidebar");
  if (sidebar) {
    sidebar.classList.remove("is-open");
  }
  $$(".node-card").forEach((n) => n.classList.remove("is-selected", "is-active-service", "flow-highlight", "node-isolated-hidden", "node-isolated-active"));
  isolateConnections();
}

export function highlightNodeConnections(nodeId) {
  const svg = $("#connections-svg");
  if (!svg) return;
  if (!nodeId) {
    svg.classList.remove("has-focus");
    $$(".connections-svg path").forEach((p) => p.classList.remove("conn-highlight"));
    return;
  }
  const cleanId = nodeId.startsWith("node-") ? nodeId : `node-${nodeId}`;
  svg.classList.add("has-focus");
  $$(".connections-svg path").forEach((p) => {
    const from = p.dataset.from;
    const to = p.dataset.to;
    if (from === cleanId || to === cleanId || from === nodeId || to === nodeId) {
      p.classList.add("conn-highlight");
    } else {
      p.classList.remove("conn-highlight");
    }
  });
}

function getNodeBox(el, world) {
  if (!el || !world) return null;
  const eRect = el.getBoundingClientRect();
  const wRect = world.getBoundingClientRect();
  const scale = wRect.width > 0 ? (wRect.width / 1000) : 1;
  return {
    left: Math.round((eRect.left - wRect.left) / scale),
    top: Math.round((eRect.top - wRect.top) / scale),
    right: Math.round((eRect.right - wRect.left) / scale),
    bottom: Math.round((eRect.bottom - wRect.top) / scale),
    width: Math.round(eRect.width / scale),
    height: Math.round(eRect.height / scale),
    centerX: Math.round(((eRect.left - wRect.left) + eRect.width / 2) / scale),
    centerY: Math.round(((eRect.top - wRect.top) + eRect.height / 2) / scale),
  };
}

export function renderConnections() {
  const svg = $("#connections-svg");
  const world = $("#map-world");
  if (!svg || !world) return;

  const width = 1000;
  const height = 620;

  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
  svg.setAttribute("width", `${width}`);
  svg.setAttribute("height", `${height}`);

  const client = getNodeBox($("#node-component-browser"), world);
  const gateway = getNodeBox($("#node-component-gateway"), world);
  const cluster = getNodeBox($("#cluster-microservices"), world);

  const auth = getNodeBox($("#node-service-auth"), world);
  const catalog = getNodeBox($("#node-service-catalog"), world);
  const inventory = getNodeBox($("#node-service-inventory"), world);
  const orders = getNodeBox($("#node-service-orders"), world);
  const payments = getNodeBox($("#node-service-payments"), world);

  const notifications = getNodeBox($("#node-service-notifications"), world);
  const wishlist = getNodeBox($("#node-service-wishlist"), world);
  const drops = getNodeBox($("#node-service-drops"), world);
  const media = getNodeBox($("#node-service-media"), world);

  const rabbitmq = getNodeBox($("#node-component-rabbitmq"), world);
  const celery = getNodeBox($("#node-component-celery"), world);

  const postgres = getNodeBox($("#node-component-postgres"), world);
  const redis = getNodeBox($("#node-component-redis"), world);
  const s3 = getNodeBox($("#node-component-s3"), world);
  const prometheus = getNodeBox($("#node-component-prometheus"), world);

  if (!client || !gateway || !auth || !inventory || !rabbitmq || !postgres) {
    return;
  }

  const currentIso = window._currentIsolation;
  const isIsolated = Boolean(svg.classList.contains("isolate-mode") && currentIso);

  const getPathClass = (from, to, baseClass) => {
    if (!isIsolated) return baseClass;
    const { nodeId, pairs, nodes, activeNodeIds } = currentIso;
    const cleanNodeId = nodeId ? (nodeId.startsWith("node-") ? nodeId : `node-${nodeId}`) : null;

    let isActive = false;
    if (pairs && pairs.length) {
      isActive = pairs.some(([pFrom, pTo]) => {
        const cF = pFrom.startsWith("node-") ? pFrom : `node-${pFrom}`;
        const cT = pTo.startsWith("node-") ? pTo : `node-${pTo}`;
        return (from === cF && to === cT) || (from === cT && to === cF);
      });
    } else if (cleanNodeId) {
      isActive = (from === cleanNodeId || to === cleanNodeId || from === nodeId || to === nodeId);
    } else if (nodes && nodes.length) {
      const nSet = new Set(nodes.map((n) => (n.startsWith("node-") ? n : `node-${n}`)));
      isActive = nSet.has(from) && nSet.has(to);
    }

    if (!isActive && activeNodeIds && activeNodeIds.length > 0) {
      const aSet = new Set(activeNodeIds);
      if (aSet.has(from) && aSet.has(to)) {
        isActive = true;
      }
    }

    return isActive ? `${baseClass} conn-active-isolate` : baseClass;
  };

  const channelX = Math.round((gateway.right + (cluster ? cluster.left : auth.left)) / 2);
  const row1BusY = cluster ? Math.round(cluster.top + 10) : Math.round(auth.top - 12);
  const row2BusY = notifications ? Math.round((auth.bottom + notifications.top) / 2) : Math.round(auth.bottom + 12);

  let paths = [];

  // 1. Client to Gateway (Black solid)
  paths.push(`
    <!-- Client to Gateway -->
    <path class="${getPathClass("node-component-browser", "node-component-gateway", "conn-client")}" data-from="node-component-browser" data-to="node-component-gateway" d="M ${Math.round(client.right)} ${Math.round(client.centerY)} L ${Math.round(gateway.left)} ${Math.round(gateway.centerY)}" stroke="#000000" stroke-width="2.2" marker-end="url(#arrow-black)" />
  `);

  // 2. Gateway to Core Services (Blue HTTP solid)
  const r1Services = [
    { id: "node-service-auth", node: auth },
    { id: "node-service-catalog", node: catalog },
    { id: "node-service-inventory", node: inventory },
    { id: "node-service-orders", node: orders },
    { id: "node-service-payments", node: payments }
  ];
  r1Services.forEach(({ id, node }) => {
    if (!node) return;
    let d;
    if (isIsolated) {
      const midX = Math.round((gateway.right + node.left) / 2);
      d = `M ${Math.round(gateway.right)} ${Math.round(gateway.centerY)} C ${midX} ${Math.round(gateway.centerY)}, ${midX} ${Math.round(node.centerY)}, ${Math.round(node.left)} ${Math.round(node.centerY)}`;
    } else {
      d = `M ${Math.round(gateway.right)} ${Math.round(gateway.centerY)} H ${channelX} V ${row1BusY} H ${Math.round(node.centerX)} V ${Math.round(node.top)}`;
    }
    paths.push(`
      <path class="${getPathClass("node-component-gateway", id, "conn-http")}" data-from="node-component-gateway" data-to="${id}" d="${d}" marker-end="url(#arrow-http)" />
    `);
  });

  const r2Services = [
    { id: "node-service-notifications", node: notifications },
    { id: "node-service-wishlist", node: wishlist },
    { id: "node-service-drops", node: drops },
    { id: "node-service-media", node: media }
  ];
  r2Services.forEach(({ id, node }) => {
    if (!node) return;
    let d;
    if (isIsolated) {
      const midX = Math.round((gateway.right + node.left) / 2);
      d = `M ${Math.round(gateway.right)} ${Math.round(gateway.centerY)} C ${midX} ${Math.round(gateway.centerY)}, ${midX} ${Math.round(node.centerY)}, ${Math.round(node.left)} ${Math.round(node.centerY)}`;
    } else {
      d = `M ${Math.round(gateway.right)} ${Math.round(gateway.centerY)} H ${channelX} V ${row2BusY} H ${Math.round(node.centerX)} V ${Math.round(node.top)}`;
    }
    paths.push(`
      <path class="${getPathClass("node-component-gateway", id, "conn-http")}" data-from="node-component-gateway" data-to="${id}" d="${d}" marker-end="url(#arrow-http)" />
    `);
  });

  // 3. Only Inter-Service HTTP Call: Inventory -> Drops (Drop Policy)
  if (inventory && drops) {
    paths.push(`
      <!-- Inter-Service HTTP: Inventory -> Drops -->
      <path class="${getPathClass("node-service-inventory", "node-service-drops", "conn-http")}" data-from="node-service-inventory" data-to="node-service-drops" d="M ${Math.round(inventory.centerX)} ${Math.round(inventory.bottom)} C ${Math.round(inventory.centerX)} ${Math.round(drops.top - 16)}, ${Math.round(drops.centerX)} ${Math.round(drops.top - 16)}, ${Math.round(drops.centerX)} ${Math.round(drops.top)}" stroke="#2563EB" stroke-width="2.2" marker-end="url(#arrow-http)" />
    `);
  }

  // 4. Core Services to RabbitMQ (Async Events - Orange Dashed)
  const eventProducers = [
    { id: "node-service-orders", node: orders },
    { id: "node-service-payments", node: payments },
    { id: "node-service-inventory", node: inventory },
    { id: "node-service-notifications", node: notifications },
    { id: "node-service-wishlist", node: wishlist },
    { id: "node-service-drops", node: drops }
  ].filter((item) => Boolean(item.node));

  eventProducers.forEach((item, i) => {
    const count = eventProducers.length;
    const rmqSlotX = Math.round(rabbitmq.left + 14 + (i * (rabbitmq.width - 28)) / Math.max(1, count - 1));
    const midY = Math.round((item.node.bottom + rabbitmq.top) / 2);
    paths.push(`
      <path class="${getPathClass(item.id, "node-component-rabbitmq", "conn-event")}" data-from="${item.id}" data-to="node-component-rabbitmq" d="M ${Math.round(item.node.centerX)} ${Math.round(item.node.bottom)} C ${Math.round(item.node.centerX)} ${midY}, ${rmqSlotX} ${midY}, ${rmqSlotX} ${Math.round(rabbitmq.top)}" marker-end="url(#arrow-event)" />
    `);
  });

  // RabbitMQ <-> Celery
  if (rabbitmq && celery) {
    paths.push(`
      <!-- RabbitMQ <-> Celery -->
      <path class="${getPathClass("node-component-rabbitmq", "node-component-celery", "conn-event")}" data-from="node-component-rabbitmq" data-to="node-component-celery" d="M ${Math.round(rabbitmq.right)} ${Math.round(rabbitmq.centerY)} L ${Math.round(celery.left)} ${Math.round(celery.centerY)}" marker-start="url(#arrow-event)" marker-end="url(#arrow-event)" />
    `);
  }

  if (celery) {
    if (media) {
      const cMidY = Math.round((celery.top + media.bottom) / 2);
      paths.push(`
        <!-- Celery to Media (Cleanup task) -->
        <path class="${getPathClass("node-component-celery", "node-service-media", "conn-event")}" data-from="node-component-celery" data-to="node-service-media" d="M ${Math.round(celery.centerX + 20)} ${Math.round(celery.top)} C ${Math.round(celery.centerX + 20)} ${cMidY}, ${Math.round(media.centerX)} ${cMidY}, ${Math.round(media.centerX)} ${Math.round(media.bottom)}" marker-end="url(#arrow-event)" />
      `);
    }

    if (inventory) {
      const invMidY = Math.round((celery.top + inventory.bottom) / 2);
      paths.push(`
        <!-- Celery to Inventory (Expiry task) -->
        <path class="${getPathClass("node-component-celery", "node-service-inventory", "conn-event")}" data-from="node-component-celery" data-to="node-service-inventory" d="M ${Math.round(celery.centerX - 20)} ${Math.round(celery.top)} C ${Math.round(celery.centerX - 20)} ${invMidY}, ${Math.round(inventory.centerX + 15)} ${invMidY}, ${Math.round(inventory.centerX + 15)} ${Math.round(inventory.bottom)}" marker-end="url(#arrow-event)" />
      `);
    }

    if (drops) {
      const dropsMidY = Math.round((celery.top + drops.bottom) / 2);
      paths.push(`
        <!-- Celery to Drops (Scheduler task) -->
        <path class="${getPathClass("node-component-celery", "node-service-drops", "conn-event")}" data-from="node-component-celery" data-to="node-service-drops" d="M ${Math.round(celery.centerX - 5)} ${Math.round(celery.top)} C ${Math.round(celery.centerX - 5)} ${dropsMidY}, ${Math.round(drops.centerX)} ${dropsMidY}, ${Math.round(drops.centerX)} ${Math.round(drops.bottom)}" marker-end="url(#arrow-event)" />
      `);
    }

    if (auth) {
      const authMidY = Math.round((celery.top + auth.bottom) / 2);
      paths.push(`
        <!-- Celery to Auth (Data cleanup task) -->
        <path class="${getPathClass("node-component-celery", "node-service-auth", "conn-event")}" data-from="node-component-celery" data-to="node-service-auth" d="M ${Math.round(celery.centerX - 35)} ${Math.round(celery.top)} C ${Math.round(celery.centerX - 35)} ${authMidY}, ${Math.round(auth.centerX)} ${authMidY}, ${Math.round(auth.centerX)} ${Math.round(auth.bottom)}" marker-end="url(#arrow-event)" />
      `);
    }
  }

  // 5. Data Stores & Infrastructure (Purple Dotted)
  const pgUsers = [
    { id: "node-service-auth", node: auth },
    { id: "node-service-catalog", node: catalog },
    { id: "node-service-inventory", node: inventory },
    { id: "node-service-orders", node: orders },
    { id: "node-service-payments", node: payments },
    { id: "node-service-notifications", node: notifications },
    { id: "node-service-wishlist", node: wishlist },
    { id: "node-service-drops", node: drops },
    { id: "node-service-media", node: media }
  ].filter((item) => Boolean(item.node));

  pgUsers.forEach((item, i) => {
    const count = pgUsers.length;
    const pgSlotX = Math.round(postgres.left + 14 + (i * (postgres.width - 28)) / Math.max(1, count - 1));
    const pgMidY = Math.round((item.node.bottom + postgres.top) / 2);
    paths.push(`
      <path class="${getPathClass(item.id, "node-component-postgres", "conn-data")}" data-from="${item.id}" data-to="node-component-postgres" d="M ${Math.round(item.node.centerX)} ${Math.round(item.node.bottom)} C ${Math.round(item.node.centerX)} ${pgMidY}, ${pgSlotX} ${pgMidY}, ${pgSlotX} ${Math.round(postgres.top)}" marker-end="url(#arrow-data)" />
    `);
  });

  const redisUsers = [
    { id: "node-service-auth", node: auth },
    { id: "node-service-catalog", node: catalog },
    { id: "node-service-inventory", node: inventory }
  ].filter((item) => Boolean(item.node));

  redisUsers.forEach((item, i) => {
    const count = redisUsers.length;
    const redSlotX = Math.round(redis.left + 16 + (i * (redis.width - 32)) / Math.max(1, count - 1));
    const redMidY = Math.round((item.node.bottom + redis.top) / 2);
    paths.push(`
      <path class="${getPathClass(item.id, "node-component-redis", "conn-data")}" data-from="${item.id}" data-to="node-component-redis" d="M ${Math.round(item.node.centerX)} ${Math.round(item.node.bottom)} C ${Math.round(item.node.centerX)} ${redMidY}, ${redSlotX} ${redMidY}, ${redSlotX} ${Math.round(redis.top)}" marker-end="url(#arrow-data)" />
    `);
  });

  if (s3 && media) {
    const s3MidY = Math.round((media.bottom + s3.top) / 2);
    paths.push(`
      <!-- Media to S3 / MinIO -->
      <path class="${getPathClass("node-service-media", "node-component-s3", "conn-data")}" data-from="node-service-media" data-to="node-component-s3" d="M ${Math.round(media.centerX)} ${Math.round(media.bottom)} C ${Math.round(media.centerX)} ${s3MidY}, ${Math.round(s3.centerX)} ${s3MidY}, ${Math.round(s3.centerX)} ${Math.round(s3.top)}" marker-end="url(#arrow-data)" />
    `);
  }

  if (prometheus && (celery || rabbitmq)) {
    const promSource = celery || rabbitmq;
    const promMidY = Math.round((promSource.bottom + prometheus.top) / 2);
    paths.push(`
      <!-- Celery to Prometheus Exporter -->
      <path class="${getPathClass("node-component-celery", "node-component-prometheus", "conn-data")}" data-from="node-component-celery" data-to="node-component-prometheus" d="M ${Math.round(promSource.centerX)} ${Math.round(promSource.bottom)} C ${Math.round(promSource.centerX)} ${promMidY}, ${Math.round(prometheus.centerX)} ${promMidY}, ${Math.round(prometheus.centerX)} ${Math.round(prometheus.top)}" marker-end="url(#arrow-data)" />
    `);
  }

  const inactiveFilters = Array.from($$("[data-filter]"))
    .filter((b) => !b.classList.contains("is-active"))
    .map((b) => b.dataset.filter);

  svg.innerHTML = `
    <!-- Defs for arrowheads -->
    <defs>
      <marker id="arrow-http" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
        <path d="M 0 1 L 10 5 L 0 9 z" fill="#2563EB"/>
      </marker>
      <marker id="arrow-event" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
        <path d="M 0 1 L 10 5 L 0 9 z" fill="#EA580C"/>
      </marker>
      <marker id="arrow-data" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
        <path d="M 0 1 L 10 5 L 0 9 z" fill="#7C3AED"/>
      </marker>
      <marker id="arrow-black" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
        <path d="M 0 1 L 10 5 L 0 9 z" fill="#000000"/>
      </marker>
    </defs>
    ${paths.join("")}
  `;

  inactiveFilters.forEach((type) => {
    $$(`.conn-${type}`).forEach((p) => { p.style.display = "none"; });
  });
}

export function initCanvasConnections() {
  renderConnections();
  requestAnimationFrame(() => renderConnections());
  setTimeout(() => renderConnections(), 100);

  window.addEventListener("resize", () => renderConnections());
}
