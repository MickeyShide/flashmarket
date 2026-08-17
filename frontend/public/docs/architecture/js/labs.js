import {
  $, $$, announce, entityLabel, escapeHtml, list, readUrlState, renderEvidence, statusBadge, tagList, updateUrlState,
} from "./utils.js";

const OUTBOX_SEQUENCES = {
  without: [
    ["01", "UPDATE business row", "PostgreSQL"],
    ["02", "COMMIT", "State saved in database"],
    ["03", "PROCESS CRASH", "Crashes before broker publish"],
    ["04", "Event never reaches RabbitMQ", "Permanent data loss between services"],
  ],
  with: [
    ["01", "BEGIN TRANSACTION", "PostgreSQL"],
    ["02", "UPDATE business row + INSERT outbox event", "Same transaction"],
    ["03", "COMMIT", "Both business state and event are durable"],
    ["04", "PROCESS CRASH", "Pending event safely remains in outbox table"],
    ["05", "Relay restarts & polls pending rows", "SKIP LOCKED + lease lock"],
    ["06", "Published with confirm to RabbitMQ", "Guaranteed at-least-once delivery"],
  ],
};

function outboxMarkup(mode, mechanism, index) {
  const withOutbox = mode === "with";
  const sequence = OUTBOX_SEQUENCES[mode];

  return `
    <div class="outbox-simulator">
      <div class="simulator-tabs" role="tablist" aria-label="Outbox comparison">
        <button type="button" role="tab" data-outbox-mode="without" class="${!withOutbox ? "is-active" : ""}" aria-selected="${!withOutbox}">1. Naïve (Without Outbox)</button>
        <button type="button" role="tab" data-outbox-mode="with" class="${withOutbox ? "is-active" : ""}" aria-selected="${withOutbox}">2. FlashMarket (Transactional Outbox)</button>
      </div>

      <div class="simulation-stage">
        <div class="simulation-sequence">
          ${sequence.map(([num, title, detail], pos) => `
            <div class="sim-node" data-sim-step="${pos}">
              <span>${num}</span>
              <strong>${escapeHtml(title)}</strong>
              <small>${escapeHtml(detail)}</small>
            </div>`).join("")}
        </div>

        <div class="simulation-outcome" data-sim-outcome>
          ${withOutbox
            ? "Database update and outbox row are committed atomically. The event is durable even if the server crashes."
            : "Database commit succeeded, but broker publish never happened. The downstream service never receives the event."}
        </div>

        <div class="sim-actions">
          <button class="button ${withOutbox ? "button--primary" : "button--danger"}" type="button" data-simulate-crash>
            ${withOutbox ? "▶ Simulate Crash & Recovery" : "▶ Simulate Crash After COMMIT"}
          </button>
        </div>
      </div>
    </div>

    <article class="outbox-detail">
      <p class="eyebrow">FlashMarket Outbox Pattern</p>
      <h3>Atomic Commit + Asynchronous Relay</h3>
      <p>Business mutations and outbox events commit together in PostgreSQL. An independent aio-pika worker polls pending rows and publishes with publisher confirms.</p>

      <pre class="code-block"><code>BEGIN;
  UPDATE orders SET status = 'paid' WHERE id = :order_id;
  INSERT INTO outbox_events (
    id, event_type, payload, status
  ) VALUES (
    gen_random_uuid(), 'order.paid', :payload, 'pending'
  );
COMMIT;</code></pre>

      <div class="detail-columns">
        <div>
          <span class="fact-label">Guarantees</span>
          ${list(mechanism.guarantees)}
        </div>
        <div>
          <span class="fact-label">Trade-offs</span>
          ${list(mechanism.limitations)}
        </div>
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
    const btn = $("[data-simulate-crash]", lab);
    if (btn) btn.disabled = true;

    nodes.forEach((node) => node.classList.remove("is-active", "is-success", "is-failure"));

    for (let pos = 0; pos < nodes.length; pos += 1) {
      if (token !== runToken) return;
      nodes[pos].classList.add("is-active");
      await new Promise((r) => window.setTimeout(r, 380));
      nodes[pos].classList.remove("is-active");
      const isFail = mode === "without" && pos >= 2;
      nodes[pos].classList.add(isFail ? "is-failure" : "is-success");
    }

    if (token !== runToken) return;
    const success = mode === "with";
    outcome.textContent = success
      ? "✓ Recovered: Outbox relay woke up after restart, claimed the pending row with SKIP LOCKED, and successfully published to RabbitMQ."
      : "✕ Permanent Loss: Database committed, but the event died with the process. Downstream services are now inconsistent.";
    outcome.className = `simulation-outcome ${success ? "is-success" : "is-failure"}`;
    if (btn) btn.disabled = false;
    announce(success ? "Outbox crash recovered successfully" : "Event lost after commit in naive mode");
  }

  lab.addEventListener("click", (event) => {
    const tab = event.target.closest("[data-outbox-mode]");
    if (tab) {
      mode = tab.dataset.outboxMode;
      render();
      lab.querySelector(`[data-outbox-mode="${mode}"]`)?.focus();
      return;
    }
    if (event.target.closest("[data-simulate-crash]")) simulate();
  });

  render();
}

function concurrencyMarkup(mode) {
  const safe = mode === "flashmarket";
  const lanes = safe ? [
    ["User A (First request)", ["BEGIN", "SELECT stock FOR UPDATE", "available = 1", "reserve 1; available = 0", "COMMIT (Success)"]],
    ["User B (Concurrent request)", ["BEGIN", "SELECT stock FOR UPDATE", "Waits for User A lock...", "available = 0", "Rollback: Insufficient stock (Rejected)"]],
  ] : [
    ["User A", ["Read available = 1", "Check passes (1 > 0)", "Reserve 1 unit", "Write available = 0 (Success)"]],
    ["User B", ["Read available = 1 (Stale read)", "Check passes (1 > 0)", "Reserve 1 unit", "Write available = 0 (Oversold!)"]],
  ];

  return `
    <div class="segmented" role="tablist" aria-label="Concurrency modes">
      <button role="tab" type="button" data-race-mode="naive" class="${safe ? "" : "is-active"}" aria-selected="${!safe}">1. Naïve (Read-then-Write)</button>
      <button role="tab" type="button" data-race-mode="flashmarket" class="${safe ? "is-active" : ""}" aria-selected="${safe}">2. FlashMarket (PostgreSQL Row Lock / Atomic)</button>
    </div>

    <div class="race-stage">
      ${lanes.map(([title, steps], laneIdx) => `
        <article class="race-lane">
          <h3>${title}</h3>
          <div class="race-steps">
            ${steps.map((step, pos) => {
              let cls = "";
              if (safe) {
                if (laneIdx === 1 && pos === 2) cls = "is-blocked";
                else if (laneIdx === 1 && pos === 4) cls = "is-danger";
                else if (laneIdx === 0 && pos === 4) cls = "is-safe";
              } else {
                if (pos >= 2) cls = "is-danger";
              }
              return `<div class="race-step ${cls}">${escapeHtml(step)}</div>`;
            }).join("")}
          </div>
        </article>`).join("")}
      <div class="race-outcome ${safe ? "is-safe" : "is-danger"}">
        ${safe
          ? "✓ Invariant Preserved: Row-level lock forces serial evaluation. Only 1 unit is reserved; User B receives an out-of-stock response."
          : "✕ Race Condition: Both requests read available=1 simultaneously. 2 units are sold from stock of 1 (Overselling)."}
      </div>
    </div>`;
}

export function initConcurrency() {
  const lab = $("[data-concurrency-lab]");
  let mode = "naive";
  const render = () => { lab.innerHTML = concurrencyMarkup(mode); };

  lab.addEventListener("click", (event) => {
    const btn = event.target.closest("[data-race-mode]");
    if (btn) {
      mode = btn.dataset.raceMode;
      render();
      lab.querySelector(`[data-race-mode="${mode}"]`)?.focus();
      announce(`${btn.textContent} concurrency demo shown`);
    }
  });

  render();
}

export function renderDecisions(data, index) {
  const container = $("[data-decision-grid]");
  container.innerHTML = data.engineeringHighlights.map((hl) => {
    const mechanism = hl.mechanismId ? index.get(hl.mechanismId) : null;
    return `
      <article class="decision-card">
        <div class="card-topline">
          <span class="decision-card__rank">#0${hl.rank}</span>
          <span class="tag">Architecture Mechanism</span>
        </div>
        <h3>${escapeHtml(hl.title)}</h3>
        <p class="why">${escapeHtml(hl.whyItMatters)}</p>
        ${mechanism ? `
          <button class="text-button" type="button" data-mechanism-id="${mechanism.id}">How it works ↓</button>
          <div class="mechanism-expanded" data-mechanism-detail hidden>
            <div class="mechanism-block">
              <strong>Problem:</strong>
              <p>${escapeHtml(mechanism.problem)}</p>
            </div>
            <div class="mechanism-block">
              <strong>Guarantees:</strong>
              <p>${escapeHtml(mechanism.guarantees.join(" "))}</p>
            </div>
            <div class="mechanism-block">
              <strong>Trade-offs:</strong>
              <p>${escapeHtml(mechanism.limitations.join(" "))}</p>
            </div>
            ${renderEvidence(mechanism.evidenceIds, index)}
          </div>` : renderEvidence(hl.evidenceIds, index)}
      </article>`;
  }).join("");

  container.addEventListener("click", (event) => {
    const btn = event.target.closest("[data-mechanism-id]");
    if (!btn) return;
    const detail = btn.nextElementSibling;
    detail.hidden = !detail.hidden;
    btn.textContent = detail.hidden ? "How it works ↓" : "Hide details ↑";
  });
}

function databaseMarkup(database, data, index) {
  const service = index.get(database.serviceId);
  const tables = database.tableIds.map((id) => index.get(id)).filter(Boolean);
  const tableIds = new Set(tables.map((t) => t.id));
  const constraints = data.constraints.filter((c) => tableIds.has(c.tableId));
  const indexes = data.indexes.filter((i) => tableIds.has(i.tableId));

  return `
    <aside class="schema-panel">
      <div class="card-topline">
        <div>
          <span class="fact-label">Database</span>
          <h3>${escapeHtml(database.name)}</h3>
        </div>
        ${statusBadge(service.status)}
      </div>
      <p>${escapeHtml(service.responsibility)}</p>
      <div class="table-list">
        ${tables.map((t) => `
          <article class="table-card">
            <strong>${escapeHtml(t.name)}</strong>
            <p>${escapeHtml(t.purpose)}</p>
          </article>`).join("")}
      </div>
      ${constraints.length ? `
        <div class="invariant-list">
          <span class="fact-label">Invariants & Constraints</span>
          ${constraints.map((c) => `
            <div class="invariant">
              <code>${escapeHtml(c.kind)}: ${escapeHtml(c.rule)}</code>
              <p>${escapeHtml(c.why)}</p>
            </div>`).join("")}
        </div>` : ""}
    </aside>

    <div class="index-panel">
      <div class="card-topline">
        <div>
          <span class="fact-label">Worker & Query Optimization</span>
          <h3>${indexes.length} Custom Indexes</h3>
        </div>
        <span class="tag">${tables.length} tables</span>
      </div>
      <div class="index-list">
        ${indexes.map((idx) => `
          <article class="index-card">
            <div class="index-card__head">
              <div>
                <h4>${escapeHtml(idx.id)}</h4>
                <span class="index-columns">(${escapeHtml(idx.columns.join(", "))})</span>
              </div>
              <span class="tag">${escapeHtml(index.get(idx.tableId)?.name)}</span>
            </div>
            <dl>
              <div><dt>Query Pattern</dt><dd>${escapeHtml(idx.query)}</dd></div>
              <div><dt>Why This Order</dt><dd>${escapeHtml(idx.whyOrder)}</dd></div>
              <div><dt>Without Index</dt><dd>${escapeHtml(idx.without)}</dd></div>
            </dl>
          </article>`).join("") || "<p class='dim'>Standard primary key indexes only.</p>"}
      </div>
    </div>`;
}

export function initDatabases(data, index) {
  const select = $("[data-database-select]");
  const explorer = $("[data-database-explorer]");
  const allowed = new Set(data.databases.map((d) => d.id));
  let databaseId = readUrlState("database", allowed, "database-inventory");

  select.innerHTML = data.databases.map((db) => `
    <option value="${db.id}" ${db.id === databaseId ? "selected" : ""}>${escapeHtml(index.get(db.serviceId)?.name)} (${escapeHtml(db.name)})</option>`).join("");

  const render = () => {
    explorer.innerHTML = databaseMarkup(index.get(databaseId), data, index);
    updateUrlState({ database: databaseId });
  };

  select.addEventListener("change", () => {
    databaseId = select.value;
    render();
  });

  render();
}

export function renderWorkers(data, index) {
  const container = $("[data-worker-explorer]");
  container.innerHTML = `
    <article class="broker-card">
      <div class="card-topline">
        <div>
          <span class="fact-label">RabbitMQ Messaging Topology</span>
          <h3>5 Queue Families</h3>
        </div>
        <span class="tag">${data.queues.length} Queues</span>
      </div>
      <div class="broker-diagram">
        <div class="broker-row"><span>Outbox publisher</span><i>→</i><span>flashmarket.events (Topic)</span></div>
        <div class="broker-row"><span>Main queue</span><i>→</i><span>aio-pika consumer</span></div>
        <div class="broker-row"><span>5s · 30s · 120s</span><i>↺</i><span>Retry backoff queues</span></div>
        <div class="broker-row"><span>Exhausted</span><i>→</i><span>Dead Letter Queue (DLQ)</span></div>
      </div>
      <div class="empty-celery">
        <strong>Celery Beat Maintenance: ${data.celeryTasks.length} Periodic Tasks</strong>
        <p>Runs periodic cleanup (releasing expired reservations, outbox cleanup) via <code>/flashmarket-tasks</code> vhost.</p>
      </div>
      <div class="worker-grid">
        ${data.celeryTasks.map((t) => `
          <article class="worker-card">
            <strong>${escapeHtml(index.get(t.ownerId)?.name)}: ${escapeHtml(t.queue)}</strong>
            <p><code>${escapeHtml(t.name)}</code></p>
            <p><b>Schedule:</b> ${escapeHtml(t.schedule)}</p>
          </article>`).join("")}
      </div>
    </article>

    <div class="worker-list">
      <div class="card-topline">
        <div>
          <span class="fact-label">Process Execution Roles</span>
          <h3>${data.workerProcesses.length} Service Worker Roles</h3>
        </div>
        ${tagList(["Outbox relay", "aio-pika Consumer", "Celery Worker"])}
      </div>
      <div class="worker-grid">
        ${data.workerProcesses.map((w) => `
          <article class="worker-card">
            <div class="card-topline">
              <strong>${escapeHtml(index.get(w.serviceId)?.name)}: ${escapeHtml(w.role)}</strong>
              ${statusBadge(w.status)}
            </div>
            <p><b>Trigger:</b> ${escapeHtml(w.trigger)}</p>
            <p><b>Side effect:</b> ${escapeHtml(w.sideEffect)}</p>
          </article>`).join("")}
      </div>
    </div>`;
}

export function renderConsistency(data) {
  const grid = $("[data-consistency-grid]");
  if (!grid) return;
  grid.innerHTML = data.consistencyBoundaries.map((b) => `
    <article class="consistency-card">
      <span class="guarantee-kind">${escapeHtml(b.kind)}</span>
      <h3>${escapeHtml(b.label)}</h3>
      <p>${escapeHtml(b.guarantee)}</p>
      <div class="fact-grid">
        <div><strong>Scope</strong><span>${escapeHtml(b.scope)}</span></div>
        <div><strong>Examples</strong><span>${escapeHtml(b.examples.join(" · "))}</span></div>
      </div>
    </article>`).join("");
}

export function renderRedis(data, index) {
  const grid = $("[data-redis-grid]");
  if (!grid) return;
  grid.innerHTML = data.redisUseCases.map((item) => `
    <article class="redis-card">
      <div class="card-topline">
        <span class="tag">${escapeHtml(item.kind)}</span>
        ${statusBadge(item.status)}
      </div>
      <h3>${escapeHtml(index.get(item.serviceId)?.name)}</h3>
      <code>${escapeHtml(item.keyPattern)}</code>
      <div class="fact-grid">
        <div><strong>TTL:</strong> <span>${escapeHtml(item.ttl)}</span></div>
        <div><strong>Failure mode:</strong> <span>${escapeHtml(item.failureBehaviour)}</span></div>
      </div>
    </article>`).join("");
}

function failureMarkup(failure, index) {
  return `
    <article class="failure-detail">
      <div class="card-topline">
        ${statusBadge(failure.status)}
        <span class="tag">Fault Recovery</span>
      </div>
      <h3>${escapeHtml(failure.question)}</h3>
      <div class="failure-chain">
        <div><strong>1. Failure</strong><p>${escapeHtml(failure.problem)}</p></div>
        <div><strong>2. Protection</strong><p>${escapeHtml(failure.mechanism)}</p></div>
        <div><strong>3. Recovery</strong><p>${escapeHtml(failure.result)}</p></div>
        <div><strong>4. Bound</strong><p>${escapeHtml(failure.remainingLimitation)}</p></div>
      </div>
      ${renderEvidence(failure.evidenceIds, index)}
    </article>`;
}

export function initFailures(data, index) {
  const container = $("[data-failure-explorer]");
  const allowed = new Set(data.failureScenarios.map((f) => f.id));
  let failureId = readUrlState("failure", allowed, data.failureScenarios[0].id);

  function render() {
    container.innerHTML = `
      <div class="failure-list" aria-label="Failure scenarios">
        ${data.failureScenarios.map((f) => `
          <button type="button" data-failure-id="${f.id}" class="${f.id === failureId ? "is-active" : ""}">
            ${escapeHtml(f.question)}
          </button>`).join("")}
      </div>
      ${failureMarkup(index.get(failureId), index)}`;
    updateUrlState({ failure: failureId });
  }

  container.addEventListener("click", (event) => {
    const btn = event.target.closest("[data-failure-id]");
    if (btn) {
      failureId = btn.dataset.failureId;
      render();
      container.querySelector(`[data-failure-id="${failureId}"]`)?.focus();
      announce(`${index.get(failureId).question} selected`);
    }
  });

  render();
}

export function initInterview(data, index) {
  const listEl = $("[data-interview-list]");
  const expandBtn = $("[data-expand-interview]");

  listEl.innerHTML = data.interviewQuestions.map((item, pos) => `
    <details class="interview-item">
      <summary>
        <span class="interview-item__index">Q${String(pos + 1).padStart(2, "0")}</span>
        <strong>${escapeHtml(item.question)}</strong>
        <span class="expand-icon" aria-hidden="true">+</span>
      </summary>
      <div class="interview-answer">
        <div class="interview-short">
          <p><strong>Quick Answer:</strong><br>${escapeHtml(item.shortAnswer)}</p>
        </div>
        <div class="interview-deep">
          <p><strong>Technical Deep Dive:</strong><br>${escapeHtml(item.deepAnswer)}</p>
          ${renderEvidence(item.evidenceIds, index)}
        </div>
      </div>
    </details>`).join("");

  let expanded = false;
  expandBtn.addEventListener("click", () => {
    expanded = !expanded;
    $$("details", listEl).forEach((d) => { d.open = expanded; });
    expandBtn.textContent = expanded ? "Collapse all answers" : "Expand all answers";
  });
}

export function renderStatusBoard(data) {
  const board = $("[data-status-board]");
  if (!board) return;
  const implemented = [
    ...data.services.filter((s) => s.status === "implemented").map((s) => `${s.name} microservice boundary`),
    ...data.mechanisms.filter((m) => m.status === "implemented").map((m) => m.name),
  ].slice(0, 9);
  const partial = [
    ...data.services.filter((s) => s.status === "partial").map((s) => `${s.name}: ${s.limitations?.[0] || "Boundary limitations"}`),
    ...data.failureScenarios.filter((f) => f.status === "partial").map((f) => f.question),
  ];
  const future = data.plannedCapabilities.map((c) => `${c.name} [${c.status}]`);

  board.innerHTML = [
    ["Fully Implemented", implemented, "implemented"],
    ["Partial Scope", partial, "partial"],
    ["Planned Boundaries", future, "planned"],
  ].map(([title, items, status]) => `
    <article class="status-column">
      <h3>${statusBadge(status)} ${escapeHtml(title)}</h3>
      ${list(items)}
    </article>`).join("");
}
