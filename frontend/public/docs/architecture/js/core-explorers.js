import {
  $, $$, announce, entityLabel, escapeHtml, list, readUrlState, renderEvidence, statusBadge, tagList, updateUrlState,
} from "./utils.js";

export function renderHero(data) {
  const primaryStats = [
    { label: "Microservices", value: String(data.services.length) },
    { label: "Integration Events", value: String(data.events.length) },
    { label: "Databases (PostgreSQL)", value: String(data.databases.length) },
    { label: "Background Workers", value: String(data.workerProcesses.length) },
  ];
  $("[data-hero-stats]").innerHTML = primaryStats.map((stat) => `
    <div class="stat">
      <strong>${escapeHtml(stat.value)}</strong>
      <span>${escapeHtml(stat.label)}</span>
    </div>`).join("");

  $("[data-technologies]").innerHTML = data.technologies.map((tech) => `
    <span class="tech-tag">${escapeHtml(tech.label)}</span>`).join("");
}

function serviceDialogMarkup(service, data, index) {
  const database = index.get(service.databaseId);
  const tables = (database?.tableIds || []).map((id) => index.get(id)).filter(Boolean);
  const endpoints = service.endpointIds.map((id) => index.get(id)).filter(Boolean);
  const published = service.publishesEventIds.map((id) => index.get(id)).filter(Boolean);
  const consumed = service.consumesEventIds.map((id) => index.get(id)).filter(Boolean);
  const workers = service.workerIds.map((id) => index.get(id)).filter(Boolean);
  const redis = service.redisUseCaseIds.map((id) => index.get(id)).filter(Boolean);
  const decisions = service.decisionIds.map((id) => index.get(id)).filter(Boolean);

  return `
    <div class="dialog-shell">
      <header class="dialog-header">
        <div>
          <p class="eyebrow">Service / ${escapeHtml(service.slug)}</p>
          <h2 id="service-dialog-title">${escapeHtml(service.name)}</h2>
          ${statusBadge(service.status)}
        </div>
        <button class="icon-button" type="button" data-dialog-close aria-label="Close service details">✕</button>
      </header>

      <section class="dialog-section">
        <h3>Responsibility</h3>
        <p>${escapeHtml(service.responsibility)}</p>
      </section>

      <section class="dialog-section">
        <h3>State & Ownership</h3>
        <p><strong>Owns:</strong> ${escapeHtml(service.owns.join(", "))}</p>
        <p><strong>Database:</strong> <code>${escapeHtml(database?.name || "none")}</code> (PostgreSQL)</p>
        ${tables.length ? tagList(tables.map((t) => t.name)) : ""}
        ${redis.length ? `<div style="margin-top:8px"><strong>Redis:</strong> ${tagList(redis.map((r) => r.kind))}</div>` : ""}
      </section>

      <section class="dialog-section">
        <h3>Integration Events</h3>
        <div class="event-tags-group">
          <div><strong>Publishes:</strong> ${published.length ? tagList(published.map((e) => e.name)) : "<span class='dim'>None</span>"}</div>
          <div style="margin-top:6px"><strong>Consumes:</strong> ${consumed.length ? tagList(consumed.map((e) => e.name)) : "<span class='dim'>None</span>"}</div>
        </div>
      </section>

      <section class="dialog-section">
        <h3>API Endpoints (${endpoints.length})</h3>
        <div class="endpoint-list">
          ${endpoints.map((ep) => `
            <div class="endpoint">
              <strong class="method-badge method-${ep.method.toLowerCase()}">${escapeHtml(ep.method)}</strong>
              <div>
                <code>${escapeHtml(ep.path)}</code>
                <p>${escapeHtml(ep.summary)}</p>
              </div>
            </div>`).join("") || "<p class='dim'>No public endpoints.</p>"}
        </div>
      </section>

      <section class="dialog-section">
        <h3>Background Workers (${workers.length})</h3>
        ${workers.length ? workers.map((w) => `
          <article class="worker-card">
            <strong>${escapeHtml(w.role)}</strong>
            <p>${escapeHtml(w.sideEffect)}</p>
          </article>`).join("") : "<p class='dim'>No background worker.</p>"}
      </section>

      ${decisions.length ? `
        <section class="dialog-section">
          <h3>Key Engineering Decisions</h3>
          ${list(decisions.map((d) => `<b>${d.title}</b> — ${d.whyItMatters}`))}
        </section>` : ""}

      ${renderEvidence(service.evidenceIds, index)}
    </div>`;
}

export function initServices(data, index) {
  const grid = $("[data-service-grid]");
  const dialog = $("[data-service-dialog]");
  const content = $("[data-service-dialog-content]");
  let dialogOpener = null;

  grid.innerHTML = data.services.map((service, position) => {
    const database = index.get(service.databaseId);
    return `
      <button class="service-card" type="button" data-service-id="${service.id}" aria-label="Open ${escapeHtml(service.name)} service details">
        <div class="card-topline">
          <span class="service-card__index">SVC-${String(position + 1).padStart(2, "0")}</span>
          ${statusBadge(service.status)}
        </div>
        <div class="service-card__body">
          <h3>${escapeHtml(service.name)}</h3>
          <p>${escapeHtml(service.responsibility)}</p>
        </div>
        <div class="service-card__meta">
          <span class="meta-pill">DB: ${escapeHtml(database?.name || service.slug)}</span>
          <span class="meta-pill">${service.publishesEventIds.length} Pub / ${service.consumesEventIds.length} Sub</span>
          <span class="meta-pill-action">Details →</span>
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
    announce(`${service.name} service details opened`);
  }

  grid.addEventListener("click", (event) => {
    const card = event.target.closest("[data-service-id]");
    if (card) openService(card.dataset.serviceId);
  });
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) dialog.close();
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
        <div>
          <div class="card-topline">
            <span class="status-badge status-badge--${flow.status}">${escapeHtml(flow.status)}</span>
            <span class="step-counter">${flow.steps.length} STEPS</span>
          </div>
          <h3>${escapeHtml(flow.name)}</h3>
          <p class="flow-summary">${escapeHtml(flow.summary)}</p>
        </div>
      </div>

      <!-- Pipeline Track -->
      <div class="flow-steps-track" role="tablist" aria-label="Flow steps">
        ${flow.steps.map((item, position) => `
          <button class="flow-step-pill ${position === stepIndex ? "is-active" : ""}" type="button" data-flow-step="${position}" aria-selected="${position === stepIndex}">
            <span class="step-num">${String(position + 1).padStart(2, "0")}</span>
            <span class="step-name">${escapeHtml(item.title)}</span>
          </button>`).join("")}
      </div>

      <!-- Step Details Grid -->
      <article class="flow-detail-card">
        <header class="flow-detail__head">
          <div>
            <span class="fact-label">Active Node: <b>${escapeHtml(entityLabel(node, step.nodeId))}</b></span>
            <h4>Step ${stepIndex + 1}: ${escapeHtml(step.title)}</h4>
          </div>
          <span class="step-counter">STEP ${stepIndex + 1} / ${flow.steps.length}</span>
        </header>

        <div class="flow-facts-grid">
          <div class="flow-fact-box">
            <strong>1. What happens</strong>
            <p>${escapeHtml(step.what)}</p>
          </div>
          <div class="flow-fact-box">
            <strong>2. Transaction boundary</strong>
            <p>${escapeHtml(step.consistency)}</p>
          </div>
          <div class="flow-fact-box">
            <strong>3. Failure scenario</strong>
            <p>${escapeHtml(step.failure)}</p>
          </div>
          <div class="flow-fact-box">
            <strong>4. Protection mechanism</strong>
            <p>${escapeHtml(step.protection)}</p>
          </div>
        </div>

        <footer class="flow-controls">
          <button class="button autoplay-button" type="button" data-flow-autoplay aria-pressed="false">Autoplay</button>
          <div class="flow-nav-buttons">
            <button class="button" type="button" data-flow-previous ${stepIndex === 0 ? "disabled" : ""}>← Previous</button>
            <button class="button button--primary" type="button" data-flow-next ${stepIndex === flow.steps.length - 1 ? "disabled" : ""}>Next →</button>
          </div>
        </footer>
      </article>
    </div>`;
}

export function initFlows(data, index, { onStepChange }) {
  const select = $("[data-flow-select]");
  const player = $("[data-flow-player]");
  const allowed = new Set(data.flows.map((flow) => flow.id));
  let flowId = readUrlState("flow", allowed, data.flows[0].id);
  let stepIndex = Number(new URL(window.location.href).searchParams.get("step")) || 0;
  let autoplayTimer = null;

  select.innerHTML = data.flows.map((flow) => `
    <option value="${flow.id}" ${flow.id === flowId ? "selected" : ""}>${escapeHtml(flow.name)}</option>`).join("");

  function stopAutoplay() {
    if (autoplayTimer) window.clearInterval(autoplayTimer);
    autoplayTimer = null;
  }

  function render() {
    const flow = index.get(flowId);
    stepIndex = Math.max(0, Math.min(stepIndex, flow.steps.length - 1));
    player.innerHTML = flowMarkup(flow, stepIndex, index);
    updateUrlState({ flow: flowId, step: stepIndex || null });
    onStepChange?.(flow.steps[stepIndex].nodeId);
    const btn = player.querySelector("[data-flow-autoplay]");
    if (btn) {
      btn.setAttribute("aria-pressed", String(Boolean(autoplayTimer)));
      btn.textContent = autoplayTimer ? "Pause" : "Autoplay";
    }
  }

  function move(nextIndex, focusSelector = null) {
    const flow = index.get(flowId);
    stepIndex = Math.max(0, Math.min(nextIndex, flow.steps.length - 1));
    if (stepIndex === flow.steps.length - 1) stopAutoplay();
    render();
    if (focusSelector) {
      const safeSelector = focusSelector === "[data-flow-next]" && stepIndex === flow.steps.length - 1
        ? "[data-flow-previous]"
        : focusSelector;
      player.querySelector(safeSelector)?.focus();
    }
    announce(`${flow.name}, step ${stepIndex + 1} of ${flow.steps.length}`);
  }

  select.addEventListener("change", () => {
    stopAutoplay();
    flowId = select.value;
    stepIndex = 0;
    render();
  });

  player.addEventListener("click", (event) => {
    const step = event.target.closest("[data-flow-step]");
    if (step) {
      stopAutoplay();
      move(Number(step.dataset.flowStep), `[data-flow-step="${step.dataset.flowStep}"]`);
      return;
    }
    if (event.target.closest("[data-flow-previous]")) {
      stopAutoplay();
      move(stepIndex - 1, "[data-flow-previous]");
      return;
    }
    if (event.target.closest("[data-flow-next]")) {
      stopAutoplay();
      move(stepIndex + 1, "[data-flow-next]");
      return;
    }
    if (event.target.closest("[data-flow-autoplay]")) {
      if (autoplayTimer) stopAutoplay();
      else autoplayTimer = window.setInterval(() => move(stepIndex + 1), 2400);
      render();
    }
  });

  render();
}

function journeyNode(label, value, empty = false) {
  return `
    <div class="journey-node ${empty ? "is-empty" : ""}">
      <small>${escapeHtml(label)}</small>
      <strong>${escapeHtml(value)}</strong>
    </div>`;
}

function eventMarkup(event, index) {
  const producer = index.get(event.producerId);
  const exchange = index.get(event.exchangeId);
  const queues = event.queueIds.map((id) => index.get(id)).filter(Boolean);
  const consumers = event.consumerIds.map((id) => index.get(id)).filter(Boolean);
  const queueLabel = queues.length ? (queues.length === 1 ? queues[0].name : `${queues.length} queues`) : "No bound queue";
  const consumerLabel = consumers.length ? (consumers.length === 1 ? consumers[0].name : `${consumers.length} consumers`) : "No subscriber";
  const databaseLabel = consumers.length ? consumers.map((s) => entityLabel(index.get(s.databaseId), s.databaseId)).join(" + ") : "No side effect";

  const stages = [
    ["Producer", producer?.name || event.producerId],
    ["Durability", "Outbox row"],
    ["Relay", "aio-pika publisher"],
    ["Exchange", exchange?.name || event.exchangeId],
    ["Routing", event.routingKey],
    ["Queue", queueLabel],
    ["Consumer", consumerLabel],
    ["State change", databaseLabel],
  ];

  return `
    <div class="journey-canvas">
      <div class="journey-track">
        ${stages.map(([label, value], pos) => `
          ${pos ? '<i class="journey-arrow" aria-hidden="true"></i>' : ""}
          ${journeyNode(label, value, !queues.length && pos >= 5)}`).join("")}
      </div>
      <div class="journey-fanout">
        <strong>Queue Fan-out:</strong> ${escapeHtml(queues.length ? queues.map((q) => q.name).join(" · ") : "Publisher confirms enabled; no bound consumer queue.")}
      </div>
    </div>
    <article class="event-card">
      <div class="card-topline">
        ${statusBadge(event.status)}
        <span class="tag">${escapeHtml(event.delivery)}</span>
      </div>
      <h3>${escapeHtml(event.name)}</h3>
      <dl class="event-details-list">
        <div><dt>Trigger</dt><dd>${escapeHtml(event.trigger)}</dd></div>
        <div><dt>Routing key</dt><dd><code>${escapeHtml(event.routingKey)}</code></dd></div>
        <div><dt>Payload fields</dt><dd>${escapeHtml(event.payloadFields.join(", "))}</dd></div>
        <div><dt>Idempotency</dt><dd>${escapeHtml(event.idempotency)}</dd></div>
        <div><dt>Retry policy</dt><dd>${escapeHtml(event.retry)}</dd></div>
      </dl>
      ${renderEvidence(event.evidenceIds, index)}
    </article>`;
}

export function initEvents(data, index) {
  const select = $("[data-event-select]");
  const explorer = $("[data-event-explorer]");
  const allowed = new Set(data.events.map((event) => event.id));
  let eventId = readUrlState("event", allowed, data.events.find((e) => e.queueIds.length)?.id || data.events[0].id);

  select.innerHTML = data.events.map((e) => `
    <option value="${e.id}" ${e.id === eventId ? "selected" : ""}>${escapeHtml(e.name)} (${escapeHtml(index.get(e.producerId)?.name)})</option>`).join("");

  const render = () => {
    explorer.innerHTML = eventMarkup(index.get(eventId), index);
    updateUrlState({ event: eventId });
  };

  select.addEventListener("change", () => {
    eventId = select.value;
    render();
    announce(`${index.get(eventId).name} event selected`);
  });

  render();
  return {
    selectEvent(id) {
      if (allowed.has(id)) {
        eventId = id;
        select.value = id;
        render();
      }
    }
  };
}
