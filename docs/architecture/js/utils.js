export const $ = (selector, root = document) => root.querySelector(selector);
export const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

export function escapeHtml(value = "") {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

export function createEntityIndex(data) {
  const groups = [
    "services", "infrastructure", "connections", "endpoints", "events", "exchanges",
    "queues", "workerProcesses", "oneShotProcesses", "databases", "tables", "constraints",
    "indexes", "redisUseCases", "mechanisms", "flows", "consistencyBoundaries",
    "failureScenarios", "interviewQuestions", "engineeringHighlights", "plannedCapabilities", "evidence",
  ];
  return new Map(groups.flatMap((group) => (data[group] || []).map((item) => [item.id, { ...item, entityType: group }])));
}

export function entityLabel(entity, fallback = "Unknown") {
  return entity?.name || entity?.title || entity?.label || entity?.question || entity?.path || fallback;
}

export function statusBadge(status = "implemented") {
  return `<span class="status-badge status-badge--${escapeHtml(status)}">${escapeHtml(status)}</span>`;
}

export function tagList(values = [], limit = values.length) {
  const visible = values.slice(0, limit);
  const remainder = values.length - visible.length;
  return `${visible.map((value) => `<span class="tag">${escapeHtml(value)}</span>`).join("")}${remainder > 0 ? `<span class="tag">+${remainder}</span>` : ""}`;
}

export function renderEvidence(ids = [], index, title = "Source evidence") {
  if (!ids.length) return "";
  const items = ids.map((id) => index.get(id)).filter(Boolean);
  if (!items.length) return "";
  return `
    <div class="source-evidence deep-only">
      <span class="fact-label">${escapeHtml(title)}</span>
      ${items.map((item) => `
        <article class="evidence-item">
          <code>${escapeHtml(item.path)}</code>
          <strong>${escapeHtml(item.symbol)}</strong>
          <p>${escapeHtml(item.description)}</p>
        </article>`).join("")}
    </div>`;
}

export function list(values = []) {
  if (!values.length) return `<p class="muted">None in the current repository.</p>`;
  return `<ul class="plain-list">${values.map((value) => `<li>${escapeHtml(value)}</li>`).join("")}</ul>`;
}

export function resolveVisualNode(id, data, index) {
  const entity = index.get(id);
  if (!entity) return id;
  if (entity.entityType === "databases") return "component-postgres";
  if (entity.entityType === "tables") {
    const database = index.get(entity.databaseId);
    return database ? "component-postgres" : id;
  }
  if (entity.entityType === "queues" || entity.entityType === "exchanges") return "component-rabbitmq";
  if (entity.entityType === "workerProcesses" || entity.entityType === "oneShotProcesses") return entity.serviceId;
  return id;
}

export function getConnectionKind(connection) {
  const protocol = connection.protocol || "";
  if (protocol.includes("HTTP")) return "http";
  if (protocol.includes("AMQP") || protocol.includes("Celery")) return "event";
  if (protocol.includes("filesystem")) return "key";
  return "data";
}

export function announce(message) {
  const region = $("[data-live-region]");
  if (!region) return;
  region.textContent = "";
  requestAnimationFrame(() => { region.textContent = message; });
}

export function updateUrlState(patch = {}) {
  const url = new URL(window.location.href);
  Object.entries(patch).forEach(([key, value]) => {
    if (value === null || value === undefined || value === "") url.searchParams.delete(key);
    else url.searchParams.set(key, value);
  });
  history.replaceState(null, "", `${url.pathname}${url.search}${url.hash}`);
}

export function readUrlState(key, allowed, fallback) {
  const value = new URL(window.location.href).searchParams.get(key);
  return value && allowed.has(value) ? value : fallback;
}

export function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}
