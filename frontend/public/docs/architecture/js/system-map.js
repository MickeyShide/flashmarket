import {
  $, $$, entityLabel, escapeHtml, getConnectionKind, resolveVisualNode, statusBadge,
} from "./utils.js";

const POSITIONS = {
  "component-browser": [8, 12],
  "component-gateway": [25, 12],
  "service-auth": [9, 36],
  "service-catalog": [29, 36],
  "service-inventory": [49, 36],
  "service-orders": [69, 36],
  "service-payments": [89, 36],
  "service-notifications": [18, 58],
  "service-wishlist": [39, 58],
  "service-drops": [60, 58],
  "service-media": [81, 58],
  "component-rabbitmq": [24, 82],
  "component-redis": [44, 82],
  "component-postgres": [64, 82],
  "component-s3": [84, 82],
  "component-prometheus": [12, 94],
  "component-celery": [88, 94],
};

const FILTERS = [
  { id: "all", label: "All Links" },
  { id: "http", label: "HTTP (Sync)" },
  { id: "event", label: "Events (RabbitMQ)" },
  { id: "data", label: "PostgreSQL / Storage" },
];

function mapNodeKind(entity) {
  return entity.id.startsWith("service-") ? "service" : "infrastructure";
}

function connectionPath(from, to, offset = 0) {
  const [x1, y1] = POSITIONS[from] || [50, 50];
  const [x2, y2] = POSITIONS[to] || [50, 50];
  const bend = offset * 1.5;
  const mx = (x1 + x2) / 2 + (y2 - y1) * bend / 100;
  const my = (y1 + y2) / 2 - (x2 - x1) * bend / 100;
  return `M ${x1} ${y1} Q ${mx} ${my} ${x2} ${y2}`;
}

export function renderInspector(target, data, index) {
  const title = $("#inspector-title");
  const content = $("[data-inspector-content]");
  if (!title || !content) return;

  if (target.entityType === "services") {
    const service = target;
    const db = index.get(service.databaseId);
    const published = service.publishesEventIds.map((id) => index.get(id)).filter(Boolean);
    const consumed = service.consumesEventIds.map((id) => index.get(id)).filter(Boolean);
    const endpoints = service.endpointIds.map((id) => index.get(id)).filter(Boolean);

    title.innerHTML = `${escapeHtml(service.name)} Microservice ${statusBadge(service.status)}`;
    content.innerHTML = `
      <div class="insp-section">
        <strong>Responsibility</strong>
        <p>${escapeHtml(service.responsibility)}</p>
      </div>

      <div class="insp-section">
        <strong>Database</strong>
        <p><code>${escapeHtml(db?.name || service.slug)}</code> (Private PostgreSQL instance)</p>
      </div>

      <div class="insp-section">
        <strong>Outbox Events Published (${published.length})</strong>
        <div class="insp-tags">${published.map((e) => `<code>${escapeHtml(e.name)}</code>`).join(" ") || "<span class='dim'>None</span>"}</div>
      </div>

      <div class="insp-section">
        <strong>Events Consumed (${consumed.length})</strong>
        <div class="insp-tags">${consumed.map((e) => `<code>${escapeHtml(e.name)}</code>`).join(" ") || "<span class='dim'>None</span>"}</div>
      </div>

      <div class="insp-section">
        <strong>Public API (${endpoints.length} routes)</strong>
        <div class="insp-endpoints">
          ${endpoints.slice(0, 4).map((ep) => `
            <div class="insp-ep">
              <span class="ep-method">${escapeHtml(ep.method)}</span>
              <code>${escapeHtml(ep.path)}</code>
            </div>`).join("")}
        </div>
      </div>

      <button class="button button--primary" style="width:100%;margin-top:10px" type="button" data-open-drawer-btn="${service.id}">Open Full Spec Drawer →</button>`;
    return;
  }

  if (target.protocol || target.from) {
    const conn = target;
    const from = index.get(conn.from);
    const to = index.get(conn.to);
    const contract = Array.isArray(conn.contract) ? conn.contract.join(", ") : conn.contract;

    title.innerHTML = `${escapeHtml(entityLabel(from, conn.from))} → ${escapeHtml(entityLabel(to, conn.to))}`;
    content.innerHTML = `
      <div class="insp-section">
        <strong>Protocol & Transport</strong>
        <p><b>${escapeHtml(conn.protocol)}</b> (${escapeHtml(conn.purpose)})</p>
      </div>

      <div class="insp-section">
        <strong>Contract / Event Name</strong>
        <p><code>${escapeHtml(contract || "Repository Contract")}</code></p>
      </div>

      <div class="insp-section">
        <strong>Consistency Guarantee</strong>
        <p>${escapeHtml(conn.consistency)}</p>
      </div>

      <div class="insp-section">
        <strong>Failure Behavior</strong>
        <p>${escapeHtml(conn.failureBehaviour)}</p>
      </div>`;
  }
}

export function initSystemMap(data, index, { onOpenService }) {
  const map = $("[data-system-map]");
  const controls = $("[data-map-filters]");
  if (!map || !controls) return { highlightRoute() {} };

  const nodes = [...data.infrastructure, ...data.services].filter((entity) => POSITIONS[entity.id]);
  const edges = data.connections.map((connection, position) => {
    const from = resolveVisualNode(connection.from, data, index);
    const to = resolveVisualNode(connection.to, data, index);
    return { ...connection, visualFrom: from, visualTo: to, kind: getConnectionKind(connection), offset: (position % 5) - 2 };
  }).filter((edge) => POSITIONS[edge.visualFrom] && POSITIONS[edge.visualTo] && edge.visualFrom !== edge.visualTo);

  controls.innerHTML = FILTERS.map((filter) => `
    <button type="button" data-map-filter="${filter.id}" class="${filter.id === "all" ? "is-active" : ""}">
      ${filter.label}
    </button>`).join("");

  map.innerHTML = `
    <svg class="map-svg" viewBox="0 0 100 100" preserveAspectRatio="none" aria-label="System connections">
      ${edges.map((edge) => `
        <path class="map-edge map-edge--${edge.kind}" d="${connectionPath(edge.visualFrom, edge.visualTo, edge.offset)}"
          vector-effect="non-scaling-stroke" tabindex="0"
          data-connection-id="${edge.id}" data-from="${edge.visualFrom}" data-to="${edge.visualTo}" data-kind="${edge.kind}">
          <title>${escapeHtml(edge.protocol)}: ${escapeHtml(edge.purpose)}</title>
        </path>`).join("")}
    </svg>
    ${nodes.map((node) => {
      const [left, top] = POSITIONS[node.id];
      const kind = mapNodeKind(node);
      const sub = kind === "service" ? "microservice" : node.kind;
      return `
        <button type="button" class="map-node map-node--${kind}" style="left:${left}%;top:${top}%" data-map-node="${node.id}" data-status="${node.status}">
          <strong>${escapeHtml(node.name)}</strong>
          <small>${escapeHtml(sub)}</small>
        </button>`;
    }).join("")}`;

  let activeFilter = "all";
  let pinnedNode = null;

  function applyFilter(filter) {
    activeFilter = filter;
    $$('[data-map-filter]', controls).forEach((btn) => btn.classList.toggle("is-active", btn.dataset.mapFilter === filter));
    $$(".map-edge", map).forEach((edge) => {
      const visible = filter === "all" || edge.dataset.kind === filter || (filter === "data" && edge.dataset.kind === "key");
      edge.classList.toggle("is-hidden", !visible);
    });
    const celery = $('[data-map-node="component-celery"]', map);
    if (celery) celery.hidden = filter !== "all";
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

  function highlightRoute(fromId, toId) {
    const vFrom = resolveVisualNode(fromId, data, index);
    const vTo = resolveVisualNode(toId, data, index);

    $$(".map-node", map).forEach((node) => {
      const isSrc = node.dataset.mapNode === vFrom;
      const isDst = node.dataset.mapNode === vTo;
      node.classList.toggle("is-pulse-src", isSrc);
      node.classList.toggle("is-pulse-dst", isDst);
    });

    $$(".map-edge", map).forEach((edge) => {
      const isMatch = (edge.dataset.from === vFrom && edge.dataset.to === vTo) ||
                      (edge.dataset.from === vTo && edge.dataset.to === vFrom);
      edge.classList.toggle("is-route-active", isMatch);
    });
  }

  controls.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-map-filter]");
    if (btn) applyFilter(btn.dataset.mapFilter);
  });

  map.addEventListener("mouseover", (e) => {
    const node = e.target.closest("[data-map-node]");
    if (node) focusRelations(node.dataset.mapNode);
  });

  map.addEventListener("mouseout", (e) => {
    if (e.target.closest("[data-map-node]") && !e.relatedTarget?.closest?.("[data-map-node]")) focusRelations(pinnedNode);
  });

  map.addEventListener("click", (e) => {
    const node = e.target.closest("[data-map-node]");
    if (node) {
      pinnedNode = node.dataset.mapNode;
      $$(".map-node", map).forEach((item) => item.classList.toggle("is-selected", item === node));
      focusRelations(pinnedNode);
      const entity = index.get(pinnedNode);
      if (entity) renderInspector(entity, data, index);
      return;
    }
    const path = e.target.closest("[data-connection-id]");
    if (path) {
      const conn = index.get(path.dataset.connectionId);
      if (conn) renderInspector(conn, data, index);
    }
  });

  document.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-open-drawer-btn]");
    if (btn) onOpenService(btn.dataset.openDrawerBtn);
  });

  applyFilter(activeFilter);
  return { highlightRoute };
}
