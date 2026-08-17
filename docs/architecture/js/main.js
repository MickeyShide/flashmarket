import architectureData from "../architecture-data.js";
import { initServices } from "./core-explorers.js";
import { initSystemMap, renderInspector } from "./system-map.js";
import { $, $$, createEntityIndex } from "./utils.js";

const data = architectureData;
const index = createEntityIndex(data);

const SCENARIOS = {
  buy: [
    { from: "component-browser", to: "component-gateway", label: "[1/5] Client → Gateway: POST /api/v1/orders/checkout", target: "service-orders" },
    { from: "component-gateway", to: "service-orders", label: "[2/5] Orders Service initializes checkout & requests inventory", target: "service-orders" },
    { from: "service-orders", to: "service-inventory", label: "[3/5] Orders → Inventory: Atomic stock reservation query", target: "service-inventory" },
    { from: "service-inventory", to: "component-postgres", label: "[4/5] Inventory DB: COMMIT (Stock -1) + INSERT outbox_events", target: "component-postgres" },
    { from: "service-inventory", to: "component-rabbitmq", label: "[5/5] Outbox Relay publishes 'stock_reserved' → Payments & Notifications", target: "component-rabbitmq" },
  ],
  drop: [
    { from: "component-browser", to: "service-drops", label: "[1/4] Client visits Drop Page at release time", target: "service-drops" },
    { from: "service-drops", to: "component-redis", label: "[2/4] Drops reads cached countdown & allocation from Redis", target: "component-redis" },
    { from: "service-drops", to: "service-inventory", label: "[3/4] Drops calls Inventory for flash reservation claim", target: "service-inventory" },
    { from: "service-inventory", to: "component-postgres", label: "[4/4] PostgreSQL executes single-query atomic decrement", target: "component-postgres" },
  ],
  outbox: [
    { from: "service-orders", to: "component-postgres", label: "[1/4] Orders executes BEGIN; UPDATE status; INSERT outbox; COMMIT;", target: "component-postgres" },
    { from: "service-orders", to: "service-orders", label: "[2/4] PROCESS CRASH! Server dies before network publish.", target: "service-orders" },
    { from: "service-orders", to: "component-postgres", label: "[3/4] Outbox relay restarts & claims pending row via SKIP LOCKED", target: "component-postgres" },
    { from: "component-postgres", to: "component-rabbitmq", label: "[4/4] Relay sends confirmed event to RabbitMQ. Zero loss.", target: "component-rabbitmq" },
  ],
  cleanup: [
    { from: "component-celery", to: "service-inventory", label: "[1/3] Celery Beat triggers periodic cleanup on /flashmarket-tasks", target: "component-celery" },
    { from: "service-inventory", to: "component-postgres", label: "[2/3] Worker finds expired reservations (created > 15m ago)", target: "component-postgres" },
    { from: "component-postgres", to: "service-inventory", label: "[3/3] Stock released back to available pool. State restored.", target: "service-inventory" },
  ],
};

function initScenarioRunner(map) {
  const tabs = $$("[data-scenario]");
  const playBtn = $("[data-play-flow]");
  const prevBtn = $("[data-step-prev]");
  const nextBtn = $("[data-step-next]");
  const statusEl = $("[data-flow-status]");
  if (!tabs.length || !statusEl) return;

  let currentKey = "buy";
  let stepIndex = 0;
  let timer = null;

  function setStep(idx) {
    const list = SCENARIOS[currentKey];
    stepIndex = Math.max(0, Math.min(idx, list.length - 1));
    const step = list[stepIndex];
    statusEl.innerHTML = `<b>Step ${stepIndex + 1}/${list.length}:</b> ${step.label}`;
    map.highlightRoute(step.from, step.to);

    if (prevBtn) prevBtn.disabled = stepIndex === 0;
    if (nextBtn) nextBtn.disabled = stepIndex === list.length - 1;

    const targetEntity = index.get(step.target);
    if (targetEntity) renderInspector(targetEntity, data, index);
  }

  function play() {
    if (timer) {
      clearInterval(timer);
      timer = null;
      if (playBtn) playBtn.textContent = "▶ Play Animation";
      return;
    }
    if (playBtn) playBtn.textContent = "⏸ Pause";
    const list = SCENARIOS[currentKey];
    if (stepIndex >= list.length - 1) stepIndex = -1;

    timer = setInterval(() => {
      if (stepIndex < list.length - 1) {
        setStep(stepIndex + 1);
      } else {
        clearInterval(timer);
        timer = null;
        if (playBtn) playBtn.textContent = "▶ Play Animation";
      }
    }, 1600);
  }

  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      if (timer) { clearInterval(timer); timer = null; }
      tabs.forEach((t) => t.classList.toggle("is-active", t === tab));
      currentKey = tab.dataset.scenario;
      setStep(0);
      if (playBtn) playBtn.textContent = "▶ Play Animation";
    });
  });

  playBtn?.addEventListener("click", play);
  prevBtn?.addEventListener("click", () => { if (timer) clearInterval(timer); setStep(stepIndex - 1); });
  nextBtn?.addEventListener("click", () => { if (timer) clearInterval(timer); setStep(stepIndex + 1); });

  setStep(0);
}

function start() {
  const services = initServices(data, index);
  const map = initSystemMap(data, index, { onOpenService: services.openService });
  initScenarioRunner(map);

  // Set default inspector to Inventory Service
  const initial = index.get("service-inventory");
  if (initial) renderInspector(initial, data, index);

  document.documentElement.classList.add("is-ready");
}

try {
  start();
} catch (error) {
  console.error("Architecture Cockpit failed to start", error);
}
