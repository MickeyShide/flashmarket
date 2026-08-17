import {
  $, $$, announce, entityLabel, escapeHtml, list, readUrlState, renderEvidence, statusBadge, tagList, updateUrlState,
} from "./utils.js";

const OUTBOX_SEQUENCES = {
  without: [
    ["01", "UPDATE business row", "PostgreSQL"],
    ["02", "COMMIT", "state is durable"],
    ["03", "PROCESS CRASH", "before publish"],
    ["04", "Event never reaches RabbitMQ", "permanent loss"],
  ],
  with: [
    ["01", "BEGIN + UPDATE business row", "PostgreSQL"],
    ["02", "INSERT outbox event", "same transaction"],
    ["03", "COMMIT", "both are durable"],
    ["04", "PROCESS CRASH", "event still pending"],
    ["05", "Relay restarts and claims row", "SKIP LOCKED + lease"],
    ["06", "Confirmed publish", "RabbitMQ"],
    ["07", "Consumer commits + ACKs", "eventual delivery"],
  ],
};

function outboxMarkup(mode, mechanism, index) {
  const withOutbox = mode === "with";
  const sequence = OUTBOX_SEQUENCES[mode];
  return `
    <div class="outbox-simulator">
      <div class="simulator-tabs" role="tablist" aria-label="Outbox comparison">
        <button type="button" role="tab" data-outbox-mode="without" class="${!withOutbox ? "is-active" : ""}" aria-selected="${!withOutbox}">Without outbox</button>
        <button type="button" role="tab" data-outbox-mode="with" class="${withOutbox ? "is-active" : ""}" aria-selected="${withOutbox}">With outbox</button>
      </div>
      <div class="simulation-stage">
        <div class="simulation-sequence">${sequence.map(([number, title, detail], position) => `<div class="sim-node" data-sim-step="${position}"><span>${number}</span><strong>${escapeHtml(title)}</strong><small>${escapeHtml(detail)}</small></div>`).join("")}</div>
        <p class="simulation-outcome" data-sim-outcome>${withOutbox ? "The outbox row survives the application process." : "The database and broker are two independent durability boundaries."}</p>
        <button class="button ${withOutbox ? "button--primary" : "button--danger"}" type="button" data-simulate-crash>${withOutbox ? "Simulate crash and recovery" : "Simulate crash after COMMIT"}</button>
      </div>
    </div>
    <article class="outbox-detail">
      <p class="eyebrow">Real FlashMarket implementation</p>
      <h3>${escapeHtml(mechanism.name)}</h3>
      <p>${escapeHtml(mechanism.summary)}</p>
      <pre class="code-block">BEGIN
  UPDATE aggregate_state;
  INSERT INTO outbox_events (
    id, event_type, payload,
    status, next_attempt_at
  );
COMMIT;</pre>
      <div class="detail-columns deep-only">
        <div><span class="fact-label">Guarantees</span>${list(mechanism.guarantees)}</div>
        <div><span class="fact-label">Trade-offs / limits</span>${list(mechanism.limitations)}</div>
      </div>
      ${renderEvidence(mechanism.evidenceIds, index)}
    </article>`;
}

export function initOutbox(data, index) {
  const lab = $("[data-outbox-lab]");
  const mechanism = index.get("mechanism-outbox");
  let mode = "without";
  let runToken = 0;

  function render() {
    runToken += 1;
    lab.innerHTML = outboxMarkup(mode, mechanism, index);
  }

  async function simulate() {
    const token = ++runToken;
    const nodes = $$("[data-sim-step]", lab);
    const outcome = $("[data-sim-outcome]", lab);
    $("[data-simulate-crash]", lab).disabled = true;
    nodes.forEach((node) => node.classList.remove("is-active", "is-success", "is-failure"));
    for (let position = 0; position < nodes.length; position += 1) {
      if (token !== runToken) return;
      nodes[position].classList.add("is-active");
      await new Promise((resolve) => window.setTimeout(resolve, 420));
      nodes[position].classList.remove("is-active");
      const failure = mode === "without" && position >= 2;
      nodes[position].classList.add(failure ? "is-failure" : "is-success");
    }
    if (token !== runToken) return;
    const success = mode === "with";
    outcome.textContent = success
      ? "✓ Eventual delivery: the relay recovers the pending row after restart. Duplicate delivery is still possible and expected."
      : "✕ Database state changed, but no durable publish intent exists. The event is permanently lost.";
    outcome.className = `simulation-outcome ${success ? "is-success" : "is-failure"}`;
    $("[data-simulate-crash]", lab).disabled = false;
    announce(success ? "Outbox recovered event delivery after crash" : "Event lost after database commit and process crash");
  }

  lab.addEventListener("click", (event) => {
    const tab = event.target.closest("[data-outbox-mode]");
    if (tab) { mode = tab.dataset.outboxMode; render(); lab.querySelector(`[data-outbox-mode="${mode}"]`)?.focus(); return; }
    if (event.target.closest("[data-simulate-crash]")) simulate();
  });
  render();
}

function databaseMarkup(database, data, index) {
  const service = index.get(database.serviceId);
  const tables = database.tableIds.map((id) => index.get(id)).filter(Boolean);
  const tableIds = new Set(tables.map((table) => table.id));
  const constraints = data.constraints.filter((constraint) => tableIds.has(constraint.tableId));
  const indexes = data.indexes.filter((item) => tableIds.has(item.tableId));
  return `
    <aside class="schema-panel">
      <div class="card-topline"><div><span class="fact-label">Logical database</span><h3>${escapeHtml(database.name)}</h3></div>${statusBadge(service.status)}</div>
      <p>${escapeHtml(service.responsibility)}</p>
      <div class="table-list">${tables.map((table) => `<article class="table-card"><strong>${escapeHtml(table.name)}</strong><p>${escapeHtml(table.purpose)}</p></article>`).join("")}</div>
      <div class="invariant-list deep-only"><span class="fact-label">Database invariants</span>${constraints.map((constraint) => `<div class="invariant"><code>${escapeHtml(constraint.kind)} · ${escapeHtml(constraint.rule)}</code><p>${escapeHtml(constraint.why)}</p></div>`).join("") || "<p>No highlighted constraints.</p>"}</div>
    </aside>
    <div class="index-panel">
      <div class="card-topline"><div><span class="fact-label">Important access paths</span><h3>${indexes.length} highlighted indexes</h3></div><span class="tag">${tables.length} tables</span></div>
      <div class="index-list">${indexes.map((item) => `<article class="index-card">
        <div class="index-card__head"><div><h4>${escapeHtml(item.id)}</h4><span class="index-columns">(${escapeHtml(item.columns.join(", "))})</span></div><span class="tag">${escapeHtml(index.get(item.tableId)?.name)}</span></div>
        <dl><div><dt>Query pattern</dt><dd>${escapeHtml(item.query)}</dd></div><div><dt>Why this shape</dt><dd>${escapeHtml(item.whyOrder)}</dd></div><div><dt>Without it</dt><dd>${escapeHtml(item.without)}</dd></div><div><dt>Write trade-off</dt><dd>Additional index maintenance on each affected mutation.</dd></div></dl>
      </article>`).join("") || "<p>No architecture-significant index card for this database.</p>"}</div>
    </div>`;
}

export function initDatabases(data, index) {
  const select = $("[data-database-select]");
  const explorer = $("[data-database-explorer]");
  const allowed = new Set(data.databases.map((database) => database.id));
  let databaseId = readUrlState("database", allowed, "database-inventory");
  select.innerHTML = data.databases.map((database) => `<option value="${database.id}" ${database.id === databaseId ? "selected" : ""}>${escapeHtml(index.get(database.serviceId)?.name)} / ${escapeHtml(database.name)}</option>`).join("");
  const render = () => { explorer.innerHTML = databaseMarkup(index.get(databaseId), data, index); updateUrlState({ database: databaseId }); };
  select.addEventListener("change", () => { databaseId = select.value; render(); });
  render();
}

function concurrencyMarkup(mode) {
  const safe = mode === "flashmarket";
  const lanes = safe ? [
    ["User A", ["BEGIN", "SELECT stock FOR UPDATE", "available = 1", "reserve; available = 0", "COMMIT"]],
    ["User B", ["BEGIN", "SELECT stock FOR UPDATE", "waits for User A", "available = 0", "reject: insufficient stock"]],
  ] : [
    ["User A", ["read available = 1", "check passes", "reserve one unit", "write available = 0"]],
    ["User B", ["read available = 1", "check passes", "reserve one unit", "write available = 0"]],
  ];
  return `
    <div class="segmented" role="tablist" aria-label="Concurrency implementation">
      <button role="tab" type="button" data-race-mode="naive" class="${safe ? "" : "is-active"}" aria-selected="${!safe}">Naive implementation</button>
      <button role="tab" type="button" data-race-mode="flashmarket" class="${safe ? "is-active" : ""}" aria-selected="${safe}">FlashMarket</button>
    </div>
    <div class="race-stage">
      ${lanes.map(([title, steps], laneIndex) => `<article class="race-lane"><h3>${title}</h3><div class="race-steps">${steps.map((step, position) => {
        const className = safe ? (laneIndex === 1 && position === 2 ? "is-blocked" : position === steps.length - 1 ? "is-safe" : "") : position >= 2 ? "is-danger" : "";
        return `<div class="race-step ${className}">${escapeHtml(step)}</div>`;
      }).join("")}</div></article>`).join("")}
      <div class="race-outcome ${safe ? "is-safe" : ""}">${safe ? "✓ Invariant preserved: reserved + sold ≤ total; the second transaction observes committed stock under the row lock." : "✕ Overselling: two successful decisions were made from the same stale value."}</div>
    </div>`;
}

export function initConcurrency() {
  const lab = $("[data-concurrency-lab]");
  let mode = "naive";
  const render = () => { lab.innerHTML = concurrencyMarkup(mode); };
  lab.addEventListener("click", (event) => {
    const button = event.target.closest("[data-race-mode]");
    if (button) { mode = button.dataset.raceMode; const label = button.textContent; render(); lab.querySelector(`[data-race-mode="${mode}"]`)?.focus(); announce(`${label} concurrency timeline shown`); }
  });
  render();
}

export function renderWorkers(data, index) {
  const container = $("[data-worker-explorer]");
  container.innerHTML = `
    <article class="broker-card">
      <div class="card-topline"><div><span class="fact-label">Broker topology</span><h3>5 queue families</h3></div><span class="tag">${data.queues.length} queues</span></div>
      <div class="broker-diagram">
        <div class="broker-row"><span>Producer outbox</span><i>→</i><span>flashmarket.events</span></div>
        <div class="broker-row"><span>Main queue</span><i>→</i><span>Consumer process</span></div>
        <div class="broker-row"><span>5s · 30s · 120s</span><i>↺</i><span>Per-consumer retry</span></div>
        <div class="broker-row"><span>Permanent / exhausted</span><i>→</i><span>Bounded DLQ</span></div>
      </div>
      <div class="empty-celery"><strong>Celery maintenance: ${data.celeryTasks.length} tasks.</strong><br>Singleton Beat routes periodic commands through <code>/flashmarket-tasks</code>. Integration events remain on direct aio-pika consumers in <code>/flashmarket</code>.</div>
      <div class="worker-grid">${data.celeryTasks.map((task) => `<article class="worker-card"><strong>${escapeHtml(index.get(task.ownerId)?.name)} / ${escapeHtml(task.queue)}</strong><p><code>${escapeHtml(task.name)}</code></p><p><b>Schedule:</b> ${escapeHtml(task.schedule)}</p><p class="deep-only"><b>Idempotency:</b> ${escapeHtml(task.idempotency)}</p></article>`).join("")}</div>
    </article>
    <div class="worker-list">
      <div class="card-topline"><div><span class="fact-label">Service worker processes</span><h3>${data.workerProcesses.length} explicit roles + singleton Beat</h3></div>${tagList(["outbox", "consumer", "Celery maintenance"])}</div>
      <div class="worker-grid">${data.workerProcesses.map((worker) => `<article class="worker-card"><div class="card-topline"><strong>${escapeHtml(index.get(worker.serviceId)?.name)} / ${escapeHtml(worker.role)}</strong>${statusBadge(worker.status)}</div><p><b>Trigger:</b> ${escapeHtml(worker.trigger)}</p><p><b>Effect:</b> ${escapeHtml(worker.sideEffect)}</p><p class="deep-only"><b>Retry:</b> ${escapeHtml(worker.retry)}</p><p class="deep-only"><b>Idempotency:</b> ${escapeHtml(worker.idempotency)}</p></article>`).join("")}</div>
    </div>`;
}

export function renderConsistency(data) {
  $("[data-consistency-grid]").innerHTML = data.consistencyBoundaries.map((boundary) => `<article class="consistency-card"><span class="guarantee-kind">${escapeHtml(boundary.kind)}</span><h3>${escapeHtml(boundary.label)}</h3><p>${escapeHtml(boundary.guarantee)}</p><div class="fact-grid deep-only"><div><strong>Scope</strong><span>${escapeHtml(boundary.scope)}</span></div><div><strong>Examples</strong><span>${escapeHtml(boundary.examples.join(" · "))}</span></div><div><strong>Ends here</strong><span>${escapeHtml(boundary.limitations)}</span></div></div></article>`).join("");
}

export function renderRedis(data, index) {
  $("[data-redis-grid]").innerHTML = data.redisUseCases.map((item) => `<article class="redis-card"><div class="card-topline"><span class="tag">${escapeHtml(item.kind)}</span>${statusBadge(item.status)}</div><h3>${escapeHtml(index.get(item.serviceId)?.name)}</h3><code>${escapeHtml(item.keyPattern)}</code><div class="fact-grid"><div><strong>TTL</strong><span>${escapeHtml(item.ttl)}</span></div><div class="deep-only"><strong>Invalidation</strong><span>${escapeHtml(item.invalidation)}</span></div><div><strong>Failure behaviour</strong><span>${escapeHtml(item.failureBehaviour)}</span></div></div>${renderEvidence(item.evidenceIds, index)}</article>`).join("");
}

function failureMarkup(failure, index) {
  return `<article class="failure-detail"><div class="card-topline">${statusBadge(failure.status)}<span class="tag">failure / recovery</span></div><h3>${escapeHtml(failure.question)}</h3><div class="failure-chain"><div><strong>Failure</strong><p>${escapeHtml(failure.problem)}</p></div><div><strong>Existing protection</strong><p>${escapeHtml(failure.mechanism)}</p></div><div><strong>Recovery / result</strong><p>${escapeHtml(failure.result)}</p></div><div><strong>Remaining limitation</strong><p>${escapeHtml(failure.remainingLimitation)}</p></div></div>${renderEvidence(failure.evidenceIds, index)}</article>`;
}

export function initFailures(data, index) {
  const container = $("[data-failure-explorer]");
  const allowed = new Set(data.failureScenarios.map((failure) => failure.id));
  let failureId = readUrlState("failure", allowed, data.failureScenarios[0].id);
  function render() {
    container.innerHTML = `<div class="failure-list" aria-label="Failure scenarios">${data.failureScenarios.map((failure) => `<button type="button" data-failure-id="${failure.id}" class="${failure.id === failureId ? "is-active" : ""}">${escapeHtml(failure.question)}</button>`).join("")}</div>${failureMarkup(index.get(failureId), index)}`;
    updateUrlState({ failure: failureId });
  }
  container.addEventListener("click", (event) => {
    const button = event.target.closest("[data-failure-id]");
    if (button) { failureId = button.dataset.failureId; render(); container.querySelector(`[data-failure-id="${failureId}"]`)?.focus(); announce(`${index.get(failureId).question} selected`); }
  });
  render();
}

export function renderDecisions(data, index) {
  const container = $("[data-decision-grid]");
  container.innerHTML = data.engineeringHighlights.map((highlight) => {
    const mechanism = highlight.mechanismId ? index.get(highlight.mechanismId) : null;
    return `<article class="decision-card"><span class="decision-card__rank">DECISION / ${String(highlight.rank).padStart(2, "0")}</span><h3>${escapeHtml(highlight.title)}</h3><p class="why">${escapeHtml(highlight.whyItMatters)}</p>${mechanism ? `<button class="text-button deep-only" type="button" data-mechanism-id="${mechanism.id}">Inspect mechanism ↓</button><div class="deep-only" data-mechanism-detail hidden><p><strong>Problem:</strong> ${escapeHtml(mechanism.problem)}</p><p><strong>Guarantee:</strong> ${escapeHtml(mechanism.guarantees.join(" "))}</p><p><strong>Trade-off:</strong> ${escapeHtml(mechanism.limitations.join(" "))}</p>${renderEvidence(mechanism.evidenceIds, index)}</div>` : renderEvidence(highlight.evidenceIds, index)}</article>`;
  }).join("");
  container.addEventListener("click", (event) => {
    const button = event.target.closest("[data-mechanism-id]");
    if (!button) return;
    const detail = button.nextElementSibling;
    detail.hidden = !detail.hidden;
    button.textContent = detail.hidden ? "Inspect mechanism ↓" : "Hide mechanism ↑";
  });
}

export function initInterview(data, index) {
  const listElement = $("[data-interview-list]");
  const expand = $("[data-expand-interview]");
  listElement.innerHTML = data.interviewQuestions.map((item, position) => `<details class="interview-item"><summary><span class="interview-item__index">Q${String(position + 1).padStart(2, "0")}</span><strong>${escapeHtml(item.question)}</strong><span aria-hidden="true">+</span></summary><div class="interview-answer"><p><strong>Short answer</strong><br>${escapeHtml(item.shortAnswer)}</p><div><p><strong>Deep answer</strong><br>${escapeHtml(item.deepAnswer)}</p>${renderEvidence(item.evidenceIds, index)}</div></div></details>`).join("");
  let expanded = false;
  expand.addEventListener("click", () => {
    expanded = !expanded;
    $$("details", listElement).forEach((detail) => { detail.open = expanded; });
    expand.textContent = expanded ? "Collapse all answers" : "Expand all answers";
  });
}

export function renderStatusBoard(data) {
  const implemented = [
    ...data.services.filter((item) => item.status === "implemented").map((item) => `${item.name} service boundary`),
    ...data.mechanisms.filter((item) => item.status === "implemented").map((item) => item.name),
  ].slice(0, 11);
  const partial = [
    ...data.services.filter((item) => item.status === "partial").map((item) => `${item.name}: ${item.limitations?.[0] || "boundary incomplete"}`),
    ...data.failureScenarios.filter((item) => item.status === "partial").map((item) => item.question),
  ];
  const future = data.plannedCapabilities.map((item) => `${item.name} [${item.status}]`);
  $("[data-status-board]").innerHTML = [
    ["Implemented", implemented, "implemented"], ["Partial", partial, "partial"], ["Planned / unclear", future, "planned"],
  ].map(([title, items, status]) => `<article class="status-column"><h3>${statusBadge(status)} ${escapeHtml(title)}</h3>${list(items)}</article>`).join("");
}
