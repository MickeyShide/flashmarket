import {
  $, $$, announce, entityLabel, escapeHtml, list, readUrlState, renderEvidence, statusBadge, tagList, updateUrlState,
} from "./utils.js";

export function renderHero(data) {
  $("[data-system-summary]").textContent = data.system.summary;
  const primaryStats = data.projections.heroStats.filter((stat) => [
    "stat-services", "stat-events", "stat-queues", "stat-workers",
  ].includes(stat.id));
  $("[data-hero-stats]").innerHTML = primaryStats.map((stat) => `
    <div class="stat"><strong>${escapeHtml(stat.value)}</strong><span>${escapeHtml(stat.label)}</span></div>`).join("");
  $("[data-technologies]").innerHTML = data.technologies.map((technology) => `<span>${escapeHtml(technology.label)}</span>`).join("");
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
        <div><p class="eyebrow">Service explorer / ${escapeHtml(service.slug)}</p><h2 id="service-dialog-title">${escapeHtml(service.name)}</h2>${statusBadge(service.status)}</div>
        <button class="icon-button" type="button" data-dialog-close aria-label="Close service details">×</button>
      </header>
      <section class="dialog-section"><h3>Responsibility</h3><p>${escapeHtml(service.responsibility)}</p></section>
      <section class="dialog-section"><h3>Owns / source of truth</h3>${list(service.owns)}</section>
      <section class="dialog-section deep-only">
        <h3>API / architecture-significant groups</h3>
        <div class="endpoint-list">${endpoints.map((endpoint) => `<div class="endpoint"><strong>${escapeHtml(endpoint.method)}</strong><div><code>${escapeHtml(endpoint.path)}</code><p>${escapeHtml(endpoint.summary)}</p></div></div>`).join("") || "<p>No public API group.</p>"}</div>
      </section>
      <section class="dialog-section"><h3>Internal structure</h3><div class="internal-chain">${service.layerIds.map((layer, position) => `${position ? "<i>→</i>" : ""}<span>${escapeHtml(layer)}</span>`).join("")}</div></section>
      <section class="dialog-section deep-only"><h3>Storage</h3><p><strong>PostgreSQL:</strong> ${escapeHtml(database?.name || "none")}</p>${tagList(tables.map((table) => table.name))}${redis.length ? `<p><strong>Redis:</strong></p>${tagList(redis.map((item) => item.kind))}` : ""}</section>
      <section class="dialog-section"><h3>Publishes</h3>${tagList(published.map((event) => event.name)) || "<p>No published integration events.</p>"}</section>
      <section class="dialog-section"><h3>Consumes</h3>${tagList(consumed.map((event) => event.name)) || "<p>No inbound integration events.</p>"}</section>
      <section class="dialog-section"><h3>Background processes</h3>${workers.length ? workers.map((worker) => `<article class="worker-card"><strong>${escapeHtml(worker.role)} · ${escapeHtml(worker.id)}</strong><p>${escapeHtml(worker.sideEffect)}</p></article>`).join("") : "<p>No long-running process role.</p>"}</section>
      <section class="dialog-section"><h3>Engineering highlights</h3>${list(decisions.map((decision) => `${decision.title} — ${decision.whyItMatters}`))}</section>
      ${service.limitations?.length ? `<section class="dialog-section"><h3>Remaining limitations</h3>${list(service.limitations)}</section>` : ""}
      ${renderEvidence(service.evidenceIds, index)}
    </div>`;
}

export function initServices(data, index) {
  const grid = $("[data-service-grid]");
  const dialog = $("[data-service-dialog]");
  const content = $("[data-service-dialog-content]");
  let dialogOpener = null;
  grid.innerHTML = data.services.map((service, position) => `
    <button class="service-card" type="button" data-service-id="${service.id}" aria-label="Explore ${escapeHtml(service.name)} service">
      <div class="card-topline"><span class="service-card__index">SVC-${String(position + 1).padStart(2, "0")}</span>${statusBadge(service.status)}</div>
      <div><h3>${escapeHtml(service.name)}</h3><p>${escapeHtml(service.responsibility)}</p></div>
      <div class="service-card__meta">${tagList([`${service.endpointIds.length} API groups`, `${service.publishesEventIds.length} publish`, `${service.consumesEventIds.length} consume`, `${service.workerIds.length} workers`])}</div>
    </button>`).join("");

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
    <div class="flow-player__top">
      <aside class="flow-rail">
        <div class="card-topline"><span class="status-badge status-badge--${flow.status}">${escapeHtml(flow.status)}</span><span class="step-counter">${flow.steps.length} STEPS</span></div>
        <h3>${escapeHtml(flow.name)}</h3>
        <p class="flow-rail__summary">${escapeHtml(flow.summary)}</p>
        <div class="flow-steps">${flow.steps.map((item, position) => `
          <button class="flow-step-button ${position === stepIndex ? "is-active" : ""}" type="button" data-flow-step="${position}" aria-current="${position === stepIndex ? "step" : "false"}">
            <span>${String(position + 1).padStart(2, "0")}</span><span>${escapeHtml(item.title)}</span>
          </button>`).join("")}</div>
      </aside>
      <article class="flow-detail">
        <header class="flow-detail__header"><div><span class="fact-label">Step / ${escapeHtml(entityLabel(node, step.nodeId))}</span><h3>${escapeHtml(step.title)}</h3></div><span class="step-counter">STEP ${stepIndex + 1} / ${flow.steps.length}</span></header>
        <div class="flow-facts">
          <div class="flow-fact"><strong>What happens</strong><p>${escapeHtml(step.what)}</p></div>
          <div class="flow-fact"><strong>Why this step exists</strong><p>${escapeHtml(step.why)}</p></div>
          <div class="flow-fact"><strong>Transaction / consistency</strong><p>${escapeHtml(step.consistency)}</p></div>
          <div class="flow-fact"><strong>Failure</strong><p>${escapeHtml(step.failure)}</p></div>
          <div class="flow-fact"><strong>Protection</strong><p>${escapeHtml(step.protection)}</p></div>
          <div class="flow-fact deep-only"><strong>Active data owner</strong><p>${escapeHtml(entityLabel(node, step.nodeId))}</p></div>
        </div>
        <footer class="flow-controls">
          <button class="button autoplay-button" type="button" data-flow-autoplay aria-pressed="false">Autoplay</button>
          <div class="flow-controls__main"><button class="button" type="button" data-flow-previous ${stepIndex === 0 ? "disabled" : ""}>← Previous</button><button class="button button--primary" type="button" data-flow-next ${stepIndex === flow.steps.length - 1 ? "disabled" : ""}>Next →</button></div>
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
  select.innerHTML = data.flows.map((flow) => `<option value="${flow.id}" ${flow.id === flowId ? "selected" : ""}>${escapeHtml(flow.name)} · ${flow.status}</option>`).join("");

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
    player.querySelector("[data-flow-autoplay]").setAttribute("aria-pressed", String(Boolean(autoplayTimer)));
    player.querySelector("[data-flow-autoplay]").textContent = autoplayTimer ? "Pause autoplay" : "Autoplay";
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
    if (step) { stopAutoplay(); move(Number(step.dataset.flowStep), `[data-flow-step="${step.dataset.flowStep}"]`); return; }
    if (event.target.closest("[data-flow-previous]")) { stopAutoplay(); move(stepIndex - 1, "[data-flow-previous]"); return; }
    if (event.target.closest("[data-flow-next]")) { stopAutoplay(); move(stepIndex + 1, "[data-flow-next]"); return; }
    if (event.target.closest("[data-flow-autoplay]")) {
      if (autoplayTimer) stopAutoplay();
      else autoplayTimer = window.setInterval(() => move(stepIndex + 1), 2600);
      render();
    }
  });
  render();
}

function journeyNode(label, value, empty = false) {
  return `<div class="journey-node ${empty ? "is-empty" : ""}"><small>${escapeHtml(label)}</small><strong>${escapeHtml(value)}</strong></div>`;
}

function eventMarkup(event, index) {
  const producer = index.get(event.producerId);
  const exchange = index.get(event.exchangeId);
  const queues = event.queueIds.map((id) => index.get(id)).filter(Boolean);
  const consumers = event.consumerIds.map((id) => index.get(id)).filter(Boolean);
  const queueLabel = queues.length ? (queues.length === 1 ? queues[0].name : `${queues.length} queues`) : "No bound queue";
  const consumerLabel = consumers.length ? (consumers.length === 1 ? consumers[0].name : `${consumers.length} consumers`) : "No subscriber";
  const databaseLabel = consumers.length ? consumers.map((service) => entityLabel(index.get(service.databaseId), service.databaseId)).join(" + ") : "No side effect";
  const stages = [
    ["Producer", producer?.name || event.producerId], ["Durability", "Outbox row"], ["Publisher", "Outbox relay"],
    ["Exchange", exchange?.name || event.exchangeId], ["Routing key", event.routingKey], ["Queue", queueLabel],
    ["Consumer", consumerLabel], ["Local state", databaseLabel],
  ];
  return `
    <div class="journey-canvas">
      <div class="journey-track">${stages.map(([label, value], position) => `${position ? '<i class="journey-arrow" aria-hidden="true"></i>' : ""}${journeyNode(label, value, !queues.length && position >= 5)}`).join("")}</div>
      <div class="journey-fanout"><strong>Fan-out:</strong> ${escapeHtml(queues.length ? queues.map((queue) => queue.name).join(" · ") : "Publisher confirms transport, but mandatory=false because no repository subscriber is declared.")}</div>
    </div>
    <article class="event-card">
      <div class="card-topline">${statusBadge(event.status)}<span class="tag">${escapeHtml(event.delivery)}</span></div>
      <h3>${escapeHtml(event.name)}</h3>
      <dl>
        <div><dt>Trigger</dt><dd>${escapeHtml(event.trigger)}</dd></div>
        <div><dt>Payload</dt><dd>${escapeHtml(event.payloadFields.join(" · "))}</dd></div>
        <div><dt>Routing</dt><dd>${escapeHtml(event.routingKey)}</dd></div>
        <div><dt>Side effects</dt><dd>${escapeHtml(event.sideEffects.join(" "))}</dd></div>
        <div><dt>Retry</dt><dd>${escapeHtml(event.retry)}</dd></div>
        <div><dt>Idempotency</dt><dd>${escapeHtml(event.idempotency)}</dd></div>
      </dl>
      ${renderEvidence(event.evidenceIds, index)}
    </article>`;
}

export function initEvents(data, index) {
  const select = $("[data-event-select]");
  const explorer = $("[data-event-explorer]");
  const allowed = new Set(data.events.map((event) => event.id));
  let eventId = readUrlState("event", allowed, data.events.find((event) => event.queueIds.length)?.id || data.events[0].id);
  select.innerHTML = data.events.map((event) => `<option value="${event.id}" ${event.id === eventId ? "selected" : ""}>${escapeHtml(event.name)} · ${escapeHtml(index.get(event.producerId)?.name)}</option>`).join("");
  const render = () => {
    explorer.innerHTML = eventMarkup(index.get(eventId), index);
    updateUrlState({ event: eventId });
  };
  select.addEventListener("change", () => { eventId = select.value; render(); announce(`${index.get(eventId).name} journey selected`); });
  render();
  return { selectEvent(id) { if (allowed.has(id)) { eventId = id; select.value = id; render(); } } };
}
