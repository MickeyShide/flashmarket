import architectureData from "../architecture-data.js";
import { initEvents, initFlows, initServices, renderHero } from "./core-explorers.js";
import {
  initConcurrency, initDatabases, initFailures, initInterview, initOutbox,
  renderDecisions, renderStatusBoard, renderWorkers,
} from "./labs.js";
import { initSystemMap } from "./system-map.js";
import { $, $$, announce, createEntityIndex, entityLabel, escapeHtml, updateUrlState } from "./utils.js";

const data = architectureData;
const index = createEntityIndex(data);

function initMode() {
  const allowed = new Set(["presentation", "deep"]);
  const requested = new URL(window.location.href).searchParams.get("mode");
  let mode = allowed.has(requested) ? requested : "deep";

  const apply = (nextMode) => {
    mode = nextMode;
    document.documentElement.dataset.mode = mode;
    $$('[data-mode]').forEach((button) => {
      const active = button.dataset.mode === mode;
      button.classList.toggle("is-active", active);
      button.setAttribute("aria-pressed", String(active));
    });
    updateUrlState({ mode: mode === "deep" ? null : mode });
    announce(`${mode === "deep" ? "Deep dive" : "Overview"} mode enabled`);
  };

  $(".mode-switch")?.addEventListener("click", (event) => {
    const button = event.target.closest("[data-mode]");
    if (button) apply(button.dataset.mode);
  });
  apply(mode);
}

function searchDocuments() {
  const docs = [];
  const add = (type, entity, subtitle, keywords = []) => docs.push({
    type,
    id: entity.id,
    title: entityLabel(entity, entity.id),
    subtitle,
    haystack: [entityLabel(entity, entity.id), subtitle, ...keywords].join(" ").toLowerCase(),
  });

  data.services.forEach((item) => add("service", item, item.responsibility, [...item.owns, item.slug]));
  data.events.forEach((item) => add("event", item, item.routingKey, [item.trigger, ...item.payloadFields]));
  data.flows.forEach((item) => add("flow", item, item.summary, item.steps.flatMap((step) => [step.title, step.what])));
  data.mechanisms.forEach((item) => add("mechanism", item, item.summary, [item.problem, ...item.guarantees]));
  data.tables.forEach((item) => add("table", item, `${index.get(item.databaseId)?.name} DB`, [item.purpose]));
  data.indexes.forEach((item) => add("index", item, item.query, [item.columns.join(" "), item.whyOrder]));
  data.failureScenarios.forEach((item) => add("failure", item, item.problem, [item.mechanism, item.result]));
  data.evidence.forEach((item) => add("source", item, item.path, [item.symbol, item.description]));
  return docs;
}

function initSearch(apis) {
  const dialog = $("[data-search-dialog]");
  const input = $("[data-search-input]");
  const results = $("[data-search-results]");
  if (!dialog || !input || !results) return;

  const documents = searchDocuments();
  let dialogOpener = null;

  const open = () => {
    dialogOpener = document.activeElement;
    if (!dialog.open) dialog.showModal();
    input.value = "";
    results.innerHTML = "<p>Search services, events, flows, tables, indexes, and source evidence.</p>";
    window.setTimeout(() => input.focus(), 0);
  };
  const close = () => dialog.close();

  function renderResults(query) {
    const normalized = query.trim().toLowerCase();
    if (!normalized) {
      results.innerHTML = "<p>Type to search architecture entities and implementation evidence.</p>";
      return;
    }
    const terms = normalized.split(/\s+/).filter(Boolean);
    const matches = documents
      .map((doc) => ({
        doc,
        score: terms.reduce((score, term) => score + (doc.title.toLowerCase().includes(term) ? 4 : doc.haystack.includes(term) ? 1 : -10), 0)
      }))
      .filter(({ score }) => score >= terms.length)
      .sort((a, b) => b.score - a.score || a.doc.title.localeCompare(b.doc.title))
      .slice(0, 16)
      .map(({ doc }) => doc);

    results.innerHTML = matches.length
      ? matches.map((item) => `
        <button type="button" class="search-result" data-result-type="${item.type}" data-result-id="${item.id}">
          <small>${item.type}</small>
          <div>
            <strong>${escapeHtml(item.title)}</strong>
            <span>${escapeHtml(item.subtitle)}</span>
          </div>
          <span aria-hidden="true">↗</span>
        </button>`).join("")
      : `<p>No entity matches “${escapeHtml(query)}”. Try a service name, event, index, or table.</p>`;
  }

  function navigate(type, id) {
    if (type === "service") { close(); apis.services.openService(id); return; }
    if (type === "event") { close(); apis.events.selectEvent(id); $("#events")?.scrollIntoView(); return; }
    if (type === "flow") {
      close();
      const select = $("[data-flow-select]");
      if (select) { select.value = id; select.dispatchEvent(new Event("change")); }
      $("#flows")?.scrollIntoView();
      return;
    }
    if (type === "failure") {
      close();
      $("#failures")?.scrollIntoView();
      window.setTimeout(() => $(`[data-failure-id="${id}"]`)?.click(), 100);
      return;
    }
    if (type === "table" || type === "index") {
      const entity = index.get(id);
      const databaseId = type === "table" ? entity.databaseId : index.get(entity.tableId)?.databaseId;
      close();
      const select = $("[data-database-select]");
      if (select) { select.value = databaseId; select.dispatchEvent(new Event("change")); }
      $("#database")?.scrollIntoView();
      return;
    }
    if (type === "mechanism") {
      close();
      $("#highlights")?.scrollIntoView();
      window.setTimeout(() => $(`[data-mechanism-id="${id}"]`)?.click(), 100);
      return;
    }
    if (type === "source") {
      const evidence = index.get(id);
      results.innerHTML = `
        <div class="evidence-item">
          <code>${escapeHtml(evidence.path)}</code>
          <strong>${escapeHtml(evidence.symbol)}</strong>
          <p>${escapeHtml(evidence.description)}</p>
        </div>
        <button class="search-result" type="button" data-search-back>
          <small>Search</small>
          <strong>← Back to results</strong>
        </button>`;
    }
  }

  $("[data-search-open]")?.addEventListener("click", open);
  $("[data-search-close]")?.addEventListener("click", close);
  input.addEventListener("input", () => renderResults(input.value));
  results.addEventListener("click", (event) => {
    const result = event.target.closest("[data-result-id]");
    if (result) navigate(result.dataset.resultType, result.dataset.resultId);
    if (event.target.closest("[data-search-back]")) renderResults(input.value);
  });
  dialog.addEventListener("click", (event) => { if (event.target === dialog) close(); });
  dialog.addEventListener("close", () => {
    if (dialogOpener instanceof HTMLElement && dialogOpener.isConnected) dialogOpener.focus();
  });
  document.addEventListener("keydown", (event) => {
    if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
      event.preventDefault();
      open();
    }
  });
}

function initSectionNavigation() {
  const links = $$(".section-nav a");
  const byId = new Map(links.map((link) => [link.hash.slice(1), link]));
  const observer = new IntersectionObserver((entries) => {
    const visible = entries.filter((entry) => entry.isIntersecting).sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
    if (!visible) return;
    links.forEach((link) => link.classList.toggle("is-active", link === byId.get(visible.target.id)));
  }, { rootMargin: "-20% 0px -60%", threshold: [0, .1, .4] });
  byId.forEach((_, id) => { const sec = document.getElementById(id); if (sec) observer.observe(sec); });
}

function validateRuntimeData() {
  const required = ["services", "events", "connections", "flows", "databases", "queues", "evidence"];
  const missing = required.filter((k) => !Array.isArray(data[k]));
  if (missing.length) throw new Error(`Architecture data missing collections: ${missing.join(", ")}`);
  const ids = new Set();
  for (const entity of index.values()) {
    if (ids.has(entity.id)) throw new Error(`Duplicate architecture ID: ${entity.id}`);
    ids.add(entity.id);
  }
}

function start() {
  validateRuntimeData();
  renderHero(data);
  initMode();
  const services = initServices(data, index);
  const map = initSystemMap(data, index, { onOpenService: services.openService });
  initFlows(data, index, { onStepChange: (nodeId) => map.focusNode(nodeId, { flow: true }) });
  const events = initEvents(data, index);
  initOutbox(data, index);
  initDatabases(data, index);
  initConcurrency();
  renderWorkers(data, index);
  initFailures(data, index);
  renderDecisions(data, index);
  initInterview(data, index);
  renderStatusBoard(data);
  initSearch({ services, events });
  initSectionNavigation();
  document.documentElement.classList.add("is-ready");
}

try {
  start();
} catch (error) {
  console.error("Architecture Explorer failed to start", error);
  document.body.insertAdjacentHTML("afterbegin", `<div role="alert" style="padding:16px;background:#ffeded;color:#e53935;font-weight:bold">Architecture Explorer could not start: ${escapeHtml(error.message)}.</div>`);
}
