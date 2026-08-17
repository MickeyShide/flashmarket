import {
  $, $$, announce, entityLabel, escapeHtml, getConnectionKind, resolveVisualNode, statusBadge,
} from "./utils.js";

const POSITIONS = {
  "component-browser": [8, 8],
  "component-gateway": [25, 8],
  "service-auth": [9, 29],
  "service-catalog": [29, 29],
  "service-inventory": [49, 29],
  "service-orders": [69, 29],
  "service-payments": [89, 29],
  "service-notifications": [18, 51],
  "service-wishlist": [39, 51],
  "service-drops": [60, 51],
  "service-media": [81, 51],
  "component-rabbitmq": [24, 76],
  "component-redis": [44, 76],
  "component-postgres": [64, 76],
  "component-s3": [84, 76],
  "component-prometheus": [12, 92],
  "component-celery": [88, 92],
};

const FILTERS = [
  { id: "all", label: "All Links" },
  { id: "http", label: "HTTP (Sync)" },
  { id: "event", label: "Events (AMQP)" },
  { id: "data", label: "DB / Cache" },
];

function mapNodeKind(entity) {
  return entity.id.startsWith("service-") ? "service" : "infrastructure";
}

function connectionPath(from, to, offset = 0) {
  const [x1, y1] = POSITIONS[from] || [50, 50];
  const [x2, y2] = POSITIONS[to] || [50, 50];
  const bend = offset * 1.6;
  const mx = (x1 + x2) / 2 + (y2 - y1) * bend / 100;
  const my = (y1 + y2) / 2 - (x2 - x1) * bend / 100;
  return `M ${x1} ${y1} Q ${mx} ${my} ${x2} ${y2}`;
}

function renderInspector(connection, index) {
  const container = $("[data-connection-inspector]");
  if (!container) return;
  const from = index.get(connection.from);
  const to = index.get(connection.to);
  const contract = Array.isArray(connection.contract) ? connection.contract.join(", ") : connection.contract;

  container.innerHTML = `
    <p class="eyebrow">Link Inspector</p>
    <h3>${escapeHtml(entityLabel(from, connection.from))} → ${escapeHtml(entityLabel(to, connection.to))}</h3>
    <div style="margin-bottom:8px">${statusBadge(connection.status)}</div>
    <dl class="inspector-list">
      <div><dt>Protocol</dt><dd><b>${escapeHtml(connection.protocol)}</b></dd></div>
      <div><dt>Payload / Event</dt><dd><code>${escapeHtml(contract || connection.purpose)}</code></dd></div>
      <div><dt>Guarantee</dt><dd>${escapeHtml(connection.consistency)}</dd></div>
      <div><dt>Failure mode</dt><dd>${escapeHtml(connection.failureBehaviour)}</dd></div>
    </dl>`;
}

function renderServiceInspector(service, data, index) {
  const container = $("[data-connection-inspector]");
  if (!container) return;
  const db = index.get(service.databaseId);
  const published = service.publishesEventIds.map((id) => index.get(id)).filter(Boolean);
  const consumed = service.consumesEventIds.map((id) => index.get(id)).filter(Boolean);

  container.innerHTML = `
    <p class="eyebrow">Service Inspector</p>
    <h3>${escapeHtml(service.name)}</h3>
    <div style="margin-bottom:8px">${statusBadge(service.status)}</div>
    <p style="font-size:11.5px;color:var(--muted);margin-bottom:10px">${escapeHtml(service.responsibility)}</p>
    <dl class="inspector-list">
      <div><dt>Database</dt><dd><code>${escapeHtml(db?.name || service.slug)}</code> (PostgreSQL)</dd></div>
      <div><dt>Publishes (${published.length})</dt><dd>${published.map((e) => `<code>${escapeHtml(e.name)}</code>`).join(" ") || "None"}</dd></div>
      <div><dt>Consumes (${consumed.length})</dt><dd>${consumed.map((e) => `<code>${escapeHtml(e.name)}</code>`).join(" ") || "None"}</dd></div>
      <div><dt>Outbox Pattern</dt><dd>Enabled (aio-pika relay)</dd></div>
    </dl>
    <button class="button button--primary" style="margin-top:12px;width:100%" type="button" data-open-drawer-btn="${service.id}">View Endpoints & Tables →</button>`;
}

function showTooltip(event, connection, index) {
  const tooltip = $("[data-connection-tooltip]");
  if (!tooltip) return;
  const from = entityLabel(index.get(connection.from), connection.from);
  const to = entityLabel(index.get(connection.to), connection.to);
  tooltip.innerHTML = `<strong>${escapeHtml(connection.protocol)}</strong><span>${escapeHtml(from)} → ${escapeHtml(to)}</span><span>${escapeHtml(connection.purpose)}</span>`;
  tooltip.hidden = false;
  const x = Math.min(event.clientX + 12, window.innerWidth - 260);
  const y = Math.min(event.clientY + 12, window.innerHeight - 100);
  tooltip.style.left = `${Math.max(8, x)}px`;
  tooltip.style.top = `${Math.max(8, y)}px`;
}

export function initSystemMap(data, index, { onOpenService }) {
  const map = $("[data-system-map]");
  const controls = $("[data-map-filters]");
  if (!map || !controls) return { focusNode() {}, highlightFlowRoute() {} };

  const nodes = [...data.infrastructure, ...data.services]
    .filter((entity) => POSITIONS[entity.id]);
  const edges = data.connections.map((connection, position) => {
    const from = resolveVisualNode(connection.from, data, index);
    const to = resolveVisualNode(connection.to, data, index);
    return { ...connection, visualFrom: from, visualTo: to, kind: getConnectionKind(connection), offset: (position % 5) - 2 };
  }).filter((edge) => POSITIONS[edge.visualFrom] && POSITIONS[edge.visualTo] && edge.visualFrom !== edge.visualTo);

  controls.innerHTML = FILTERS.map((filter) => `
    <button type="button" data-map-filter="${filter.id}" class="${filter.id === "all" ? "is-active" : ""}" aria-pressed="${filter.id === "all"}">
      ${filter.label}
    </button>`).join("");

  map.innerHTML = `
    <svg class="map-svg" viewBox="0 0 100 100" preserveAspectRatio="none" aria-label="System connections">
      ${edges.map((edge) => `
        <path class="map-edge map-edge--${edge.kind}" d="${connectionPath(edge.visualFrom, edge.visualTo, edge.offset)}"
          vector-effect="non-scaling-stroke" tabindex="0" role="button"
          data-connection-id="${edge.id}" data-from="${edge.visualFrom}" data-to="${edge.visualTo}" data-kind="${edge.kind}">
          <title>${escapeHtml(edge.protocol)}: ${escapeHtml(edge.purpose)}</title>
        </path>`).join("")}
    </svg>
    ${nodes.map((node) => {
      const [left, top] = POSITIONS[node.id];
      const kind = mapNodeKind(node);
      const secondary = kind === "service" ? "microservice" : node.kind;
      return `<button type="button" class="map-node map-node--${kind}" style="left:${left}%;top:${top}%" data-map-node="${node.id}" data-status="${node.status}">
        <strong>${escapeHtml(node.name)}</strong><small>${escapeHtml(secondary)}</small>
      </button>`;
    }).join("")}`;

  let activeFilter = "all";
  let pinnedNode = null;

  function applyFilter(filter) {
    activeFilter = filter;
    $$('[data-map-filter]', controls).forEach((button) => {
      const active = button.dataset.mapFilter === filter;
      button.classList.toggle("is-active", active);
      button.setAttribute("aria-pressed", String(active));
    });
    $$(".map-edge", map).forEach((edge) => {
      const visible = filter === "all" || edge.dataset.kind === filter || (filter === "data" && edge.dataset.kind === "key");
      edge.classList.toggle("is-hidden", !visible);
    });
    const celery = $('[data-map-node="component-celery"]', map);
    if (celery) celery.hidden = filter !== "all" && filter !== "celery";
    focusRelations(pinnedNode);
  }

  function focusRelations(nodeId) {
    const visibleEdges = $$(".map-edge", map).filter((edge) => !edge.classList.contains("is-hidden"));
    const relatedNodeIds = new Set(nodeId ? [nodeId] : []);
    visibleEdges.forEach((edge) => {
      const related = nodeId && (edge.dataset.from === nodeId || edge.dataset.to === nodeId);
      edge.classList.toggle("is-related", Boolean(related));
      edge.classList.toggle("is-muted", Boolean(nodeId && !related));
      if (related) {
        relatedNodeIds.add(edge.dataset.from);
        relatedNodeIds.add(edge.dataset.to);
      }
    });
    $$(".map-node", map).forEach((node) => node.classList.toggle("is-muted", Boolean(nodeId && !relatedNodeIds.has(node.dataset.mapNode))));
  }

  function focusNode(nodeId, { flow = false } = {}) {
    const visualId = resolveVisualNode(nodeId, data, index);
    $$(".map-node", map).forEach((node) => {
      const isMatch = node.dataset.mapNode === visualId;
      node.classList.toggle("is-flow-active", flow && isMatch);
    });
    if (flow && visualId) focusRelations(visualId);
  }

  controls.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-map-filter]");
    if (btn) applyFilter(btn.dataset.mapFilter);
  });

  map.addEventListener("mouseover", (e) => {
    const node = e.target.closest("[data-map-node]");
    if (node) focusRelations(node.dataset.mapNode);
    const path = e.target.closest("[data-connection-id]");
    if (path) showTooltip(e, index.get(path.dataset.connectionId), index);
  });
  map.addEventListener("mousemove", (e) => {
    const path = e.target.closest("[data-connection-id]");
    if (path) showTooltip(e, index.get(path.dataset.connectionId), index);
  });
  map.addEventListener("mouseout", (e) => {
    if (e.target.closest("[data-map-node]") && !e.relatedTarget?.closest?.("[data-map-node]")) focusRelations(pinnedNode);
    if (e.target.closest("[data-connection-id]")) $("[data-connection-tooltip]").hidden = true;
  });

  map.addEventListener("click", (e) => {
    const node = e.target.closest("[data-map-node]");
    if (node) {
      pinnedNode = node.dataset.mapNode;
      $$(".map-node", map).forEach((item) => item.classList.toggle("is-selected", item === node));
      focusRelations(pinnedNode);
      const entity = index.get(pinnedNode);
      if (entity && entity.entityType === "services") {
        renderServiceInspector(entity, data, index);
      }
    }
    const path = e.target.closest("[data-connection-id]");
    if (path) renderInspector(index.get(path.dataset.connectionId), index);
  });

  document.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-open-drawer-btn]");
    if (btn) onOpenService(btn.dataset.openDrawerBtn);
  });

  applyFilter(activeFilter);
  return { focusNode };
}
