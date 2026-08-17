import {
  $, $$, announce, entityLabel, escapeHtml, list, readUrlState, renderEvidence, statusBadge, tagList, updateUrlState,
} from "./utils.js";

export function renderHero(data) {
  const primaryStats = [
    { label: "Services", value: String(data.services.length) },
    { label: "Events", value: String(data.events.length) },
    { label: "Databases", value: String(data.databases.length) },
    { label: "Workers", value: String(data.workerProcesses.length) },
  ];
  const container = $("[data-hero-stats]");
  if (container) {
    container.innerHTML = primaryStats.map((stat) => `
      <div class="stat">
        <strong>${escapeHtml(stat.value)}</strong>
        <span>${escapeHtml(stat.label)}</span>
      </div>`).join("");
  }
}

function serviceDialogMarkup(service, data, index) {
  const database = index.get(service.databaseId);
  const tables = (database?.tableIds || []).map((id) => index.get(id)).filter(Boolean);
  const endpoints = service.endpointIds.map((id) => index.get(id)).filter(Boolean);
  const published = service.publishesEventIds.map((id) => index.get(id)).filter(Boolean);
  const consumed = service.consumesEventIds.map((id) => index.get(id)).filter(Boolean);
  const workers = service.workerIds.map((id) => index.get(id)).filter(Boolean);
  const decisions = service.decisionIds.map((id) => index.get(id)).filter(Boolean);

  return `
    <div class="dialog-shell">
      <header class="dialog-header">
        <div>
          <p class="eyebrow">Service / ${escapeHtml(service.slug)}</p>
          <h2 id="service-dialog-title">${escapeHtml(service.name)}</h2>
          ${statusBadge(service.status)}
        </div>
        <button class="icon-button" type="button" data-dialog-close aria-label="Close">✕</button>
      </header>

      <section class="dialog-section">
        <h3>Responsibility</h3>
        <p>${escapeHtml(service.responsibility)}</p>
      </section>

      <section class="dialog-section">
        <h3>Storage & Data Ownership</h3>
        <p><strong>Owns:</strong> ${escapeHtml(service.owns.join(", "))}</p>
        <p><strong>PostgreSQL DB:</strong> <code>${escapeHtml(database?.name || service.slug)}</code></p>
        ${tables.length ? tagList(tables.map((t) => t.name)) : ""}
      </section>

      <section class="dialog-section">
        <h3>Integration Events</h3>
        <div class="event-tags-group">
          <div><strong>Publishes:</strong> ${published.length ? tagList(published.map((e) => e.name)) : "<span class='dim'>None</span>"}</div>
          <div style="margin-top:6px"><strong>Consumes:</strong> ${consumed.length ? tagList(consumed.map((e) => e.name)) : "<span class='dim'>None</span>"}</div>
        </div>
      </section>

      <section class="dialog-section">
        <h3>Endpoints (${endpoints.length})</h3>
        <div class="endpoint-list">
          ${endpoints.slice(0, 8).map((ep) => `
            <div class="endpoint">
              <strong class="method-badge method-${ep.method.toLowerCase()}">${escapeHtml(ep.method)}</strong>
              <div>
                <code>${escapeHtml(ep.path)}</code>
                <p>${escapeHtml(ep.summary)}</p>
              </div>
            </div>`).join("")}
        </div>
      </section>

      ${workers.length ? `
        <section class="dialog-section">
          <h3>Workers (${workers.length})</h3>
          ${workers.map((w) => `
            <article class="worker-card">
              <strong>${escapeHtml(w.role)}</strong>
              <p>${escapeHtml(w.sideEffect)}</p>
            </article>`).join("")}
        </section>` : ""}

      ${decisions.length ? `
        <section class="dialog-section">
          <h3>Engineering Decisions</h3>
          ${list(decisions.map((d) => `<b>${d.title}</b>: ${d.whyItMatters}`))}
        </section>` : ""}

      ${renderEvidence(service.evidenceIds, index)}
    </div>`;
}

export function initServices(data, index) {
  const grid = $("[data-service-grid]");
  const dialog = $("[data-service-dialog]");
  const content = $("[data-service-dialog-content]");
  if (!grid || !dialog || !content) return { openService() {} };
  let dialogOpener = null;

  grid.innerHTML = data.services.map((service, pos) => {
    const db = index.get(service.databaseId);
    return `
      <button class="service-card" type="button" data-service-id="${service.id}">
        <div class="card-topline">
          <span class="service-card__index">#0${pos + 1}</span>
          ${statusBadge(service.status)}
        </div>
        <div class="service-card__body">
          <h3>${escapeHtml(service.name)}</h3>
          <p>${escapeHtml(service.responsibility)}</p>
        </div>
        <div class="service-card__meta">
          <span class="meta-pill">DB: ${escapeHtml(db?.name || service.slug)}</span>
          <span class="meta-pill">${service.publishesEventIds.length} Pub / ${service.consumesEventIds.length} Sub</span>
        </div>
      </button>`;
  }).join("");

  function openService(id) {
    const service = index.get(id);
    if (!service || service.entityType !== "services") return;
    dialogOpener = document.activeElement;
    content.innerHTML = serviceDialogMarkup(service, data, index);
    content.querySelector("[data-dialog-close]").addEventListener("click", () => dialog.close());
    dialog.showModal();
    content.querySelector("[data-dialog-close]").focus();
    updateUrlState({ service: id });
    announce(`${service.name} details opened`);
  }

  grid.addEventListener("click", (e) => {
    const card = e.target.closest("[data-service-id]");
    if (card) openService(card.dataset.serviceId);
  });
  dialog.addEventListener("click", (e) => {
    if (e.target === dialog) dialog.close();
  });
  dialog.addEventListener("close", () => {
    updateUrlState({ service: null });
    if (dialogOpener instanceof HTMLElement && dialogOpener.isConnected) dialogOpener.focus();
  });

  return { openService };
}

function flowMarkup(flow, stepIndex, index) {
  const step = flow.steps[stepIndex];
  const node = index.get(step.nodeId);

  return `
    <div class="flow-player__container">
      <div class="flow-player__header">
        <div class="card-topline">
          <span class="status-badge status-badge--${flow.status}">${escapeHtml(flow.status)}</span>
          <span class="step-counter">${flow.steps.length} STEPS</span>
        </div>
        <h3>${escapeHtml(flow.name)}</h3>
        <p class="flow-summary">${escapeHtml(flow.summary)}</p>
      </div>

      <!-- Pipeline Track -->
      <div class="flow-steps-track" role="tablist">
        ${flow.steps.map((item, pos) => `
          <button class="flow-step-pill ${pos === stepIndex ? "is-active" : ""}" type="button" data-flow-step="${pos}">
            <span class="step-num">${pos + 1}</span>
            <span class="step-name">${escapeHtml(item.title)}</span>
          </button>`).join("")}
      </div>

      <!-- Step Details Card -->
      <article class="flow-detail-card">
        <header class="flow-detail__head">
          <div>
            <span class="fact-label">Active Component: <b>${escapeHtml(entityLabel(node, step.nodeId))}</b></span>
            <h4>Step ${stepIndex + 1}: ${escapeHtml(step.title)}</h4>
          </div>
          <div class="flow-nav-buttons">
            <button class="button" type="button" data-flow-previous ${stepIndex === 0 ? "disabled" : ""}>←</button>
            <button class="button button--primary" type="button" data-flow-next ${stepIndex === flow.steps.length - 1 ? "disabled" : ""}>→</button>
          </div>
        </header>

        <div class="flow-facts-grid">
          <div class="flow-fact-box">
            <strong>What happens</strong>
            <p>${escapeHtml(step.what)}</p>
          </div>
          <div class="flow-fact-box">
            <strong>Transaction boundary</strong>
            <p>${escapeHtml(step.consistency)}</p>
          </div>
          <div class="flow-fact-box">
            <strong>Failure risk & protection</strong>
            <p>${escapeHtml(step.protection)}</p>
          </div>
        </div>
      </article>
    </div>`;
}

export function initFlows(data, index, { onStepChange }) {
  const select = $("[data-flow-select]");
  const player = $("[data-flow-player]");
  if (!select || !player) return;
  const allowed = new Set(data.flows.map((f) => f.id));
  let flowId = readUrlState("flow", allowed, data.flows[0].id);
  let stepIndex = Number(new URL(window.location.href).searchParams.get("step")) || 0;

  select.innerHTML = data.flows.map((f) => `
    <option value="${f.id}" ${f.id === flowId ? "selected" : ""}>${escapeHtml(f.name)}</option>`).join("");

  function render() {
    const flow = index.get(flowId);
    stepIndex = Math.max(0, Math.min(stepIndex, flow.steps.length - 1));
    player.innerHTML = flowMarkup(flow, stepIndex, index);
    updateUrlState({ flow: flowId, step: stepIndex || null });
    onStepChange?.(flow.steps[stepIndex].nodeId);
  }

  function move(nextIndex) {
    const flow = index.get(flowId);
    stepIndex = Math.max(0, Math.min(nextIndex, flow.steps.length - 1));
    render();
    announce(`${flow.name}, step ${stepIndex + 1} of ${flow.steps.length}`);
  }

  select.addEventListener("change", () => {
    flowId = select.value;
    stepIndex = 0;
    render();
  });

  player.addEventListener("click", (e) => {
    const step = e.target.closest("[data-flow-step]");
    if (step) { move(Number(step.dataset.flowStep)); return; }
    if (e.target.closest("[data-flow-previous]")) { move(stepIndex - 1); return; }
    if (e.target.closest("[data-flow-next]")) { move(stepIndex + 1); return; }
  });

  render();
}
