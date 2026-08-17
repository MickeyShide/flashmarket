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

export function updateInspector(nodeId, data, index) {
  const entity = index.get(nodeId);
  if (!entity) return;

  const nameEl = $("#inspector-name");
  const typeEl = $("#inspector-type");
  const avatarEl = $("#inspector-avatar");
  const respEl = $("#inspector-responsibility");
  const eventsEl = $("#inspector-events");
  const storageEl = $("#inspector-storage");
  const drawerBtn = $("#open-service-drawer-btn");

  if (avatarEl) {
    avatarEl.innerHTML = ICONS[nodeId] || ICONS["service-inventory"];
  }

  if (entity.entityType === "services") {
    const db = index.get(entity.databaseId);
    const published = entity.publishesEventIds.map((id) => index.get(id)).filter(Boolean);

    if (nameEl) nameEl.textContent = entity.name;
    if (typeEl) typeEl.textContent = "Microservice";
    if (respEl) respEl.textContent = entity.responsibility;

    if (eventsEl) {
      eventsEl.innerHTML = published.length
        ? published.map((e) => `<span class="event-chip">${escapeHtml(e.name)}</span>`).join("")
        : `<span class="event-chip" style="color:var(--dim)">None</span>`;
    }

    if (storageEl) {
      storageEl.innerHTML = `<span class="storage-chip">PostgreSQL (${escapeHtml(db?.name || entity.slug)})</span>`;
    }

    if (drawerBtn) {
      drawerBtn.style.display = "block";
      drawerBtn.dataset.currentServiceId = entity.id;
    }
  } else {
    if (nameEl) nameEl.textContent = entity.name;
    if (typeEl) typeEl.textContent = entity.kind || "Infrastructure";
    if (respEl) respEl.textContent = entity.summary || entity.responsibility || `${entity.name} component in FlashMarket stack.`;

    if (eventsEl) {
      eventsEl.innerHTML = `<span class="event-chip">Infrastructure Component</span>`;
    }

    if (storageEl) {
      storageEl.innerHTML = `<span class="storage-chip">${escapeHtml(entity.name)}</span>`;
    }

    if (drawerBtn) {
      drawerBtn.style.display = "none";
    }
  }
}

export function initCanvasConnections() {
  const svg = $("#connections-svg");
  if (!svg) return;

  // Render SVG curved connection paths exactly like the diagram
  svg.innerHTML = `
    <!-- Defs for arrowheads -->
    <defs>
      <marker id="arrow-http" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
        <path d="M 0 1 L 10 5 L 0 9 z" fill="#2563EB"/>
      </marker>
      <marker id="arrow-event" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
        <path d="M 0 1 L 10 5 L 0 9 z" fill="#EA580C"/>
      </marker>
      <marker id="arrow-black" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
        <path d="M 0 1 L 10 5 L 0 9 z" fill="#000000"/>
      </marker>
    </defs>

    <!-- Client to Gateway (Black solid) -->
    <path d="M 120 195 L 155 195" stroke="#000000" stroke-width="2" marker-end="url(#arrow-black)" />

    <!-- Gateway to Core Services (Blue HTTP solid) -->
    <!-- Gateway to Auth, Catalog, Inventory, Orders, Payments -->
    <path class="conn-http" d="M 255 195 H 275 V 100 H 335" marker-end="url(#arrow-http)" />
    <path class="conn-http" d="M 255 195 H 275 V 100 H 450" />
    <path class="conn-http" d="M 255 195 H 275 V 100 H 565" />
    <path class="conn-http" d="M 255 195 H 275 V 100 H 680" />
    <path class="conn-http" d="M 255 195 H 275 V 100 H 795" />

    <!-- Inter-service HTTP flows -->
    <path class="conn-http" d="M 430 100 L 450 100" marker-end="url(#arrow-http)" />
    <path class="conn-http" d="M 545 100 L 565 100" marker-end="url(#arrow-http)" />
    <path class="conn-http" d="M 660 100 L 680 100" marker-end="url(#arrow-http)" />
    <path class="conn-http" d="M 775 100 L 795 100" marker-end="url(#arrow-http)" />

    <!-- Gateway branching down to Row 2: Notifications, Wishlist, Drops, Media -->
    <path class="conn-http" d="M 275 195 V 200 H 335" marker-end="url(#arrow-http)" />
    <path class="conn-http" d="M 275 200 V 200 H 450" />
    <path class="conn-http" d="M 275 200 V 200 H 565" />
    <path class="conn-http" d="M 275 200 V 200 H 680" />

    <!-- Core Services to RabbitMQ (Orange Dashed Lines) -->
    <path class="conn-event" d="M 520 140 V 310" marker-end="url(#arrow-event)" />
    <path class="conn-event" d="M 615 140 C 615 220 540 240 520 310" marker-end="url(#arrow-event)" />
    <path class="conn-event" d="M 730 140 C 730 220 560 260 540 310" marker-end="url(#arrow-event)" />
    <path class="conn-event" d="M 845 140 C 845 240 600 270 560 310" marker-end="url(#arrow-event)" />
    <path class="conn-event" d="M 385 240 C 385 270 470 280 490 310" marker-end="url(#arrow-event)" />
    <path class="conn-event" d="M 500 240 C 500 270 510 280 520 310" marker-end="url(#arrow-event)" />
    <path class="conn-event" d="M 615 240 C 615 270 540 280 530 310" marker-end="url(#arrow-event)" />
    <path class="conn-event" d="M 730 240 C 730 270 560 280 540 310" marker-end="url(#arrow-event)" />

    <!-- RabbitMQ to Celery -->
    <path class="conn-event" d="M 590 340 L 650 340" marker-end="url(#arrow-event)" marker-start="url(#arrow-event)" />

    <!-- Celery to Payments / Orders -->
    <path class="conn-event" d="M 780 340 C 855 340 855 240 855 140" marker-end="url(#arrow-event)" />

    <!-- Data Stores (Dotted Purple Lines) -->
    <!-- Gateway to PostgreSQL -->
    <path class="conn-data" d="M 205 250 C 205 380 175 420 175 480" />
    <!-- Services to PostgreSQL -->
    <path class="conn-data" d="M 385 240 C 385 360 200 400 180 480" />
    <!-- Services to Redis -->
    <path class="conn-data" d="M 500 240 C 500 380 360 400 360 480" />
    <!-- Services to S3 -->
    <path class="conn-data" d="M 730 240 C 730 380 545 400 545 480" />
    <!-- RabbitMQ to Prometheus -->
    <path class="conn-data" d="M 520 370 C 520 440 735 440 735 480" />
  `;
}
