import architectureData from "../architecture-data.js";
import { initServices } from "./core-explorers.js";
import { initCanvasConnections, updateInspector } from "./system-map.js";
import { $, $$, createEntityIndex } from "./utils.js";

const data = architectureData;
const index = createEntityIndex(data);

function initNodeInteractions(services) {
  const nodes = $$(".node-card");
  if (!nodes.length) return;

  nodes.forEach((node) => {
    node.addEventListener("click", () => {
      nodes.forEach((n) => {
        n.classList.remove("is-selected", "is-active-service");
      });
      node.classList.add("is-selected", "is-active-service");

      const nodeId = node.dataset.nodeId;
      if (nodeId) {
        updateInspector(nodeId, data, index);
      }
    });
  });

  const detailBtn = $("#open-service-drawer-btn");
  if (detailBtn) {
    detailBtn.addEventListener("click", () => {
      const currentServiceId = detailBtn.dataset.currentServiceId || "service-inventory";
      services.openService(currentServiceId);
    });
  }
}

function initLegendFilters() {
  const filters = $$("[data-filter]");
  filters.forEach((btn) => {
    btn.addEventListener("click", () => {
      const type = btn.dataset.filter;
      btn.classList.toggle("is-active");
      const isActive = btn.classList.contains("is-active");

      const className = `conn-${type}`;
      $$(`.${className}`).forEach((path) => {
        path.style.display = isActive ? "" : "none";
      });
    });
  });
}

function initNavTabs() {
  const tabs = $$("[data-nav-filter]");
  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      tabs.forEach((t) => t.classList.remove("is-active"));
      tab.classList.add("is-active");

      const filter = tab.dataset.navFilter;
      if (filter === "overview") {
        $$(".connections-svg path").forEach((p) => { p.style.display = ""; });
        $$("[data-filter]").forEach((f) => f.classList.add("is-active"));
      } else if (filter === "services") {
        $$(".conn-http").forEach((p) => { p.style.display = ""; });
        $$(".conn-event, .conn-data").forEach((p) => { p.style.display = "none"; });
        $('[data-filter="http"]')?.classList.add("is-active");
        $('[data-filter="event"], [data-filter="data"]')?.classList.remove("is-active");
      } else if (filter === "events") {
        $$(".conn-event").forEach((p) => { p.style.display = ""; });
        $$(".conn-http, .conn-data").forEach((p) => { p.style.display = "none"; });
        $('[data-filter="event"]')?.classList.add("is-active");
        $('[data-filter="http"], [data-filter="data"]')?.classList.remove("is-active");
      } else if (filter === "data") {
        $$(".conn-data").forEach((p) => { p.style.display = ""; });
        $$(".conn-http, .conn-event").forEach((p) => { p.style.display = "none"; });
        $('[data-filter="data"]')?.classList.add("is-active");
        $('[data-filter="http"], [data-filter="event"]')?.classList.remove("is-active");
      } else if (filter === "api") {
        window.location.href = "/dev";
      }
    });
  });
}

function start() {
  const services = initServices(data, index);
  initCanvasConnections();
  initNodeInteractions(services);
  initLegendFilters();
  initNavTabs();

  // Set initial inspector state to Inventory service
  updateInspector("service-inventory", data, index);

  document.documentElement.classList.add("is-ready");
}

try {
  start();
} catch (err) {
  console.error("Failed to start architecture cockpit", err);
}
