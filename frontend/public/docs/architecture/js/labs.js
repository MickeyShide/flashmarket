import {
  $, $$, announce, escapeHtml, list, renderEvidence,
} from "./utils.js";

const OUTBOX_SEQUENCES = {
  without: [
    ["01", "UPDATE business row", "PostgreSQL"],
    ["02", "COMMIT", "State saved in DB"],
    ["03", "PROCESS CRASH", "Server crashes before RabbitMQ publish"],
    ["04", "Event lost forever", "Downstream services never receive the event"],
  ],
  with: [
    ["01", "BEGIN TRANSACTION", "PostgreSQL"],
    ["02", "UPDATE row + INSERT outbox_event", "Both in single transaction"],
    ["03", "COMMIT", "Both state and event are durable"],
    ["04", "PROCESS CRASH", "Event remains safely in outbox table"],
    ["05", "Relay restarts & polls pending rows", "Claims row via SKIP LOCKED"],
    ["06", "Published to RabbitMQ", "Guaranteed at-least-once delivery"],
  ],
};

function outboxMarkup(mode, mechanism, index) {
  const withOutbox = mode === "with";
  const sequence = OUTBOX_SEQUENCES[mode];

  return `
    <div class="outbox-simulator">
      <div class="simulator-tabs" role="tablist">
        <button type="button" role="tab" data-outbox-mode="without" class="${!withOutbox ? "is-active" : ""}">1. Without Outbox (Naïve)</button>
        <button type="button" role="tab" data-outbox-mode="with" class="${withOutbox ? "is-active" : ""}">2. FlashMarket Outbox (Reliable)</button>
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
            : "Database commit succeeded, but broker publish never happened. Downstream services are out of sync."}
        </div>

        <button class="button ${withOutbox ? "button--primary" : "button--danger"}" type="button" data-simulate-crash>
          ${withOutbox ? "▶ Simulate Crash & Recovery" : "▶ Simulate Crash After COMMIT"}
        </button>
      </div>
    </div>`;
}

export function initOutbox(data, index) {
  const lab = $("[data-outbox-lab]");
  if (!lab) return;
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
    const btn = lab.querySelector("[data-simulate-crash]");
    if (btn) btn.disabled = true;

    nodes.forEach((node) => node.classList.remove("is-active", "is-success", "is-failure"));

    for (let pos = 0; pos < nodes.length; pos += 1) {
      if (token !== runToken) return;
      nodes[pos].classList.add("is-active");
      await new Promise((r) => window.setTimeout(r, 340));
      nodes[pos].classList.remove("is-active");
      const isFail = mode === "without" && pos >= 2;
      nodes[pos].classList.add(isFail ? "is-failure" : "is-success");
    }

    if (token !== runToken) return;
    const success = mode === "with";
    outcome.textContent = success
      ? "✓ Recovered: Outbox relay claimed pending row after restart and published to RabbitMQ."
      : "✕ Permanent Loss: Event died with process. Downstream state is inconsistent.";
    outcome.className = `simulation-outcome ${success ? "is-success" : "is-failure"}`;
    if (btn) btn.disabled = false;
  }

  lab.addEventListener("click", (e) => {
    const tab = e.target.closest("[data-outbox-mode]");
    if (tab) {
      mode = tab.dataset.outboxMode;
      render();
      return;
    }
    if (e.target.closest("[data-simulate-crash]")) simulate();
  });

  render();
}

function concurrencyMarkup(mode) {
  const safe = mode === "flashmarket";
  const lanes = safe ? [
    ["User A", ["BEGIN", "SELECT stock FOR UPDATE", "available = 1", "Reserve 1 (available = 0)", "COMMIT (Success)"]],
    ["User B", ["BEGIN", "SELECT stock FOR UPDATE", "Waits for row lock...", "available = 0", "Rollback: Out of stock"]],
  ] : [
    ["User A", ["Read available = 1", "Check passes", "Reserve 1 unit", "Write available = 0 (Success)"]],
    ["User B", ["Read available = 1 (Stale)", "Check passes", "Reserve 1 unit", "Write available = 0 (Oversold!)"]],
  ];

  return `
    <div class="segmented" role="tablist">
      <button role="tab" type="button" data-race-mode="naive" class="${safe ? "" : "is-active"}">1. Naïve (Overselling Race)</button>
      <button role="tab" type="button" data-race-mode="flashmarket" class="${safe ? "is-active" : ""}">2. FlashMarket (Row Lock / Atomic)</button>
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
          ? "✓ Invariant Preserved: Only 1 unit reserved; second buyer receives an out-of-stock response."
          : "✕ Overselling: Both buyers read available=1 simultaneously. 2 units sold from stock of 1."}
      </div>
    </div>`;
}

export function initConcurrency() {
  const lab = $("[data-concurrency-lab]");
  if (!lab) return;
  let mode = "naive";
  const render = () => { lab.innerHTML = concurrencyMarkup(mode); };

  lab.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-race-mode]");
    if (btn) {
      mode = btn.dataset.raceMode;
      render();
    }
  });

  render();
}

export function renderDecisions(data, index) {
  const container = $("[data-decision-grid]");
  if (!container) return;
  container.innerHTML = data.engineeringHighlights.map((hl) => {
    const mechanism = hl.mechanismId ? index.get(hl.mechanismId) : null;
    return `
      <article class="decision-card">
        <div class="card-topline">
          <span class="decision-card__rank">#0${hl.rank}</span>
          <span class="tag">Pattern</span>
        </div>
        <h3>${escapeHtml(hl.title)}</h3>
        <p class="why">${escapeHtml(hl.whyItMatters)}</p>
        ${mechanism ? `
          <button class="text-button" type="button" data-mechanism-id="${mechanism.id}">Details ↓</button>
          <div class="mechanism-expanded" hidden>
            <p><b>Guarantee:</b> ${escapeHtml(mechanism.guarantees.join(" "))}</p>
            <p><b>Trade-off:</b> ${escapeHtml(mechanism.limitations.join(" "))}</p>
          </div>` : ""}`;
  }).join("");

  container.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-mechanism-id]");
    if (!btn) return;
    const detail = btn.nextElementSibling;
    detail.hidden = !detail.hidden;
    btn.textContent = detail.hidden ? "Details ↓" : "Hide ↑";
  });
}

export function initInterview(data, index) {
  const listEl = $("[data-interview-list]");
  const expandBtn = $("[data-expand-interview]");
  if (!listEl) return;

  listEl.innerHTML = data.interviewQuestions.map((item, pos) => `
    <details class="interview-item">
      <summary>
        <span class="interview-item__index">Q${String(pos + 1).padStart(2, "0")}</span>
        <strong>${escapeHtml(item.question)}</strong>
        <span class="expand-icon" aria-hidden="true">+</span>
      </summary>
      <div class="interview-answer">
        <p><strong>Short answer:</strong> ${escapeHtml(item.shortAnswer)}</p>
        <p class="deep-text"><strong>Details:</strong> ${escapeHtml(item.deepAnswer)}</p>
      </div>
    </details>`).join("");

  let expanded = false;
  expandBtn?.addEventListener("click", () => {
    expanded = !expanded;
    $$("details", listEl).forEach((d) => { d.open = expanded; });
    expandBtn.textContent = expanded ? "Collapse all" : "Expand all";
  });
}
