import architectureData from "../architecture-data.js";
import { initFlows, initServices, renderHero } from "./core-explorers.js";
import { initConcurrency, initInterview, initOutbox, renderDecisions } from "./labs.js";
import { initSystemMap } from "./system-map.js";
import { $, $$, createEntityIndex, entityLabel, escapeHtml } from "./utils.js";

const data = architectureData;
const index = createEntityIndex(data);

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
    results.innerHTML = "<p class='dim' style='padding:12px'>Search services, events, flows, and patterns…</p>";
    window.setTimeout(() => input.focus(), 0);
  };
  const close = () => dialog.close();

  function renderResults(query) {
    const normalized = query.trim().toLowerCase();
    if (!normalized) {
      results.innerHTML = "<p class='dim' style='padding:12px'>Type to search…</p>";
      return;
    }
    const terms = normalized.split(/\s+/).filter(Boolean);
    const matches = documents
      .map((doc) => ({
        doc,
        score: terms.reduce((score, term) => score + (doc.title.toLowerCase().includes(term) ? 4 : doc.haystack.includes(term) ? 1 : -10), 0)
      }))
      .filter(({ score }) => score >= terms.length)
      .slice(0, 12)
      .map(({ doc }) => doc);

    results.innerHTML = matches.length
      ? matches.map((item) => `
        <button type="button" class="search-result" data-result-type="${item.type}" data-result-id="${item.id}">
          <small>${item.type}</small>
          <div>
            <strong>${escapeHtml(item.title)}</strong>
            <span>${escapeHtml(item.subtitle)}</span>
          </div>
        </button>`).join("")
      : `<p class='dim' style='padding:12px'>No results found for “${escapeHtml(query)}”.</p>`;
  }

  function navigate(type, id) {
    if (type === "service") { close(); apis.services.openService(id); return; }
    if (type === "flow") {
      close();
      const select = $("[data-flow-select]");
      if (select) { select.value = id; select.dispatchEvent(new Event("change")); }
      $("#flows")?.scrollIntoView();
      return;
    }
    if (type === "mechanism") {
      close();
      $("#highlights")?.scrollIntoView();
      return;
    }
  }

  $("[data-search-open]")?.addEventListener("click", open);
  $("[data-search-close]")?.addEventListener("click", close);
  input.addEventListener("input", () => renderResults(input.value));
  results.addEventListener("click", (e) => {
    const res = e.target.closest("[data-result-id]");
    if (res) navigate(res.dataset.resultType, res.dataset.resultId);
  });
  dialog.addEventListener("click", (e) => { if (e.target === dialog) close(); });
  dialog.addEventListener("close", () => {
    if (dialogOpener instanceof HTMLElement && dialogOpener.isConnected) dialogOpener.focus();
  });
  document.addEventListener("keydown", (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
      e.preventDefault();
      open();
    }
  });
}

function initSectionNavigation() {
  const links = $$(".section-nav a");
  const byId = new Map(links.map((l) => [l.hash.slice(1), l]));
  const observer = new IntersectionObserver((entries) => {
    const visible = entries.filter((e) => e.isIntersecting).sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
    if (!visible) return;
    links.forEach((l) => l.classList.toggle("is-active", l === byId.get(visible.target.id)));
  }, { rootMargin: "-20% 0px -60%", threshold: [0, .1, .4] });
  byId.forEach((_, id) => { const sec = document.getElementById(id); if (sec) observer.observe(sec); });
}

function validateRuntimeData() {
  const required = ["services", "events", "connections", "flows", "databases", "queues", "evidence"];
  const missing = required.filter((k) => !Array.isArray(data[k]));
  if (missing.length) throw new Error(`Missing collections: ${missing.join(", ")}`);
}

function start() {
  validateRuntimeData();
  renderHero(data);
  const services = initServices(data, index);
  const map = initSystemMap(data, index, { onOpenService: services.openService });
  initFlows(data, index, { onStepChange: (nodeId) => map.focusNode(nodeId, { flow: true }) });
  initOutbox(data, index);
  initConcurrency();
  renderDecisions(data, index);
  initInterview(data, index);
  initSearch({ services });
  initSectionNavigation();
  document.documentElement.classList.add("is-ready");
}

try {
  start();
} catch (error) {
  console.error("Architecture page failed to start", error);
}
