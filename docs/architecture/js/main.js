import architectureData from "../architecture-data.js";
import { initServices } from "./core-explorers.js";
import { closeInspector, initCanvasConnections, openInspector, updateInspector, highlightNodeConnections } from "./system-map.js";
import { $, $$, createEntityIndex } from "./utils.js";

const data = architectureData;
const index = createEntityIndex(data);

let hasDragged = false;

export function initPanZoom() {
  const viewport = document.getElementById("main-app");
  const world = document.getElementById("map-world");
  if (!viewport || !world) return { centerWorld: () => {} };

  let zoom = 1;
  let panX = 0;
  let panY = 0;
  let isPanning = false;
  let startX = 0;
  let startY = 0;

  function applyTransform() {
    world.style.transform = `translate3d(${panX}px, ${panY}px, 0) scale(${zoom})`;
  }

  function centerWorld() {
    const vRect = viewport.getBoundingClientRect();
    const wWidth = 1000;
    const wHeight = 620;

    const isMobile = vRect.width < 768;
    const paddingX = isMobile ? 16 : 40;
    const paddingY = isMobile ? 24 : 40;

    const scaleX = (vRect.width - paddingX) / wWidth;
    const scaleY = (vRect.height - paddingY) / wHeight;
    const minZoom = isMobile ? 0.32 : 0.65;
    zoom = Math.min(Math.max(Math.min(scaleX, scaleY), minZoom), 1.15);

    panX = Math.round((vRect.width - wWidth * zoom) / 2);
    panY = isMobile
      ? Math.max(10, Math.round((vRect.height - wHeight * zoom) / 2) - 30)
      : Math.round((vRect.height - wHeight * zoom) / 2);
    applyTransform();
  }

  // Mouse Wheel Zoom centered at cursor
  viewport.addEventListener("wheel", (e) => {
    if (e.target.closest(".inspector-scroll-area") || e.target.closest(".side-dialog")) return;

    e.preventDefault();
    const zoomFactor = e.deltaY < 0 ? 1.1 : 0.9;
    const rect = viewport.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    const newZoom = Math.min(Math.max(zoom * zoomFactor, 0.35), 2.8);
    panX = mouseX - (mouseX - panX) * (newZoom / zoom);
    panY = mouseY - (mouseY - panY) * (newZoom / zoom);
    zoom = newZoom;
    applyTransform();
  }, { passive: false });

  // Mouse Drag / Pan
  viewport.addEventListener("mousedown", (e) => {
    if (
      e.target.closest(".inspector-sidebar") ||
      e.target.closest(".map-hud-legend") ||
      e.target.closest(".app-header") ||
      e.target.closest(".side-dialog")
    ) {
      return;
    }
    isPanning = true;
    hasDragged = false;
    startX = e.clientX - panX;
    startY = e.clientY - panY;
    viewport.classList.add("is-panning");
  });

  window.addEventListener("mousemove", (e) => {
    if (!isPanning) return;
    const dx = Math.abs(e.clientX - (startX + panX));
    const dy = Math.abs(e.clientY - (startY + panY));
    if (dx > 4 || dy > 4) {
      hasDragged = true;
    }
    panX = e.clientX - startX;
    panY = e.clientY - startY;
    applyTransform();
  });

  window.addEventListener("mouseup", () => {
    if (isPanning) {
      isPanning = false;
      viewport.classList.remove("is-panning");
    }
  });

  // Touch Support (Pinch to Zoom & Drag)
  let touchStartDist = 0;
  let initialZoom = 1;

  viewport.addEventListener("touchstart", (e) => {
    if (e.target.closest(".inspector-sidebar") || e.target.closest(".map-hud-legend")) return;
    if (e.touches.length === 1) {
      isPanning = true;
      hasDragged = false;
      startX = e.touches[0].clientX - panX;
      startY = e.touches[0].clientY - panY;
    } else if (e.touches.length === 2) {
      isPanning = false;
      const t1 = e.touches[0];
      const t2 = e.touches[1];
      touchStartDist = Math.hypot(t1.clientX - t2.clientX, t1.clientY - t2.clientY);
      initialZoom = zoom;
    }
  }, { passive: true });

  viewport.addEventListener("touchmove", (e) => {
    if (e.touches.length === 1 && isPanning) {
      hasDragged = true;
      panX = e.touches[0].clientX - startX;
      panY = e.touches[0].clientY - startY;
      applyTransform();
    } else if (e.touches.length === 2 && touchStartDist > 0) {
      const t1 = e.touches[0];
      const t2 = e.touches[1];
      const currentDist = Math.hypot(t1.clientX - t2.clientX, t1.clientY - t2.clientY);
      const ratio = currentDist / touchStartDist;
      zoom = Math.min(Math.max(initialZoom * ratio, 0.35), 2.8);
      applyTransform();
    }
  }, { passive: true });

  viewport.addEventListener("touchend", () => {
    isPanning = false;
    touchStartDist = 0;
  });

  // Close inspector when clicking empty canvas area
  viewport.addEventListener("click", (e) => {
    if (hasDragged) return;
    if (
      !e.target.closest(".node-card") &&
      !e.target.closest(".inspector-sidebar") &&
      !e.target.closest(".legend-block")
    ) {
      closeInspector();
      highlightNodeConnections(null);
    }
  });

  // Handle smart camera auto-framing for isolated subsets
  window.addEventListener("flashmarket:fit-map", (e) => {
    const box = e.detail?.boundingBox;
    if (!box) return;
    const vRect = viewport.getBoundingClientRect();
    const isMobile = vRect.width < 768;

    if (isMobile) {
      const drawerHeight = Math.min(vRect.height * 0.44, 300);
      const availWidth = Math.max(vRect.width - 32, 280);
      const availHeight = Math.max(vRect.height - drawerHeight - 36, 180);

      const scaleX = availWidth / (box.width + 48);
      const scaleY = availHeight / (box.height + 48);
      zoom = Math.min(Math.max(Math.min(scaleX, scaleY), 0.65), 1.0);

      const targetCenterX = availWidth / 2 + 16;
      const targetCenterY = availHeight / 2 + 16;

      panX = Math.round(targetCenterX - box.centerX * zoom);
      panY = Math.max(16, Math.round(targetCenterY - box.centerY * zoom));
    } else {
      // Desktop: Inspector is 380px sidebar on the right
      const inspectorWidth = 380;
      const availWidth = Math.max(vRect.width - inspectorWidth - 60, 400);
      const availHeight = Math.max(vRect.height - 80, 400);

      const scaleX = availWidth / (box.width + 120);
      const scaleY = availHeight / (box.height + 120);
      zoom = Math.min(Math.max(Math.min(scaleX, scaleY), 0.75), 1.0);

      const targetCenterX = availWidth / 2 + 20;
      const targetCenterY = vRect.height / 2;

      panX = Math.round(targetCenterX - box.centerX * zoom);
      panY = Math.round(targetCenterY - box.centerY * zoom);
    }
    applyTransform();
  });

  window.addEventListener("flashmarket:reset-map", () => {
    centerWorld();
  });

  centerWorld();
  window.addEventListener("resize", centerWorld);

  return { centerWorld };
}

function initNodeInteractions(services) {
  const nodes = $$(".node-card");
  if (!nodes.length) return;

  nodes.forEach((node) => {
    // Hover: preview connections when no service is selected
    node.addEventListener("mouseenter", () => {
      const selected = $(".node-card.is-selected");
      if (!selected) {
        const id = node.id || node.dataset.nodeId;
        highlightNodeConnections(id);
      }
    });

    node.addEventListener("mouseleave", () => {
      const selected = $(".node-card.is-selected");
      if (!selected) {
        highlightNodeConnections(null);
      }
    });

    // Click: open inspector, lock selection and isolate service connections
    node.addEventListener("click", (e) => {
      if (hasDragged) return;
      e.stopPropagation();

      nodes.forEach((n) => {
        n.classList.remove("is-selected", "is-active-service", "flow-highlight");
      });
      node.classList.add("is-selected", "is-active-service");

      const nodeId = node.dataset.nodeId;
      if (nodeId) {
        openInspector(nodeId, data, index);
      }
    });
  });

  const closeBtn = $("#close-inspector-btn");
  if (closeBtn) {
    closeBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      closeInspector();
    });
  }
}

function initLegendFilters() {
  const filters = $$("[data-filter]");
  filters.forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
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

function initMobileMenu() {
  const menuBtn = $("#mobile-menu-toggle");
  const drawer = $("#mobile-nav-drawer");
  if (!menuBtn || !drawer) return;

  menuBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    drawer.classList.toggle("is-open");
  });

  document.addEventListener("click", (e) => {
    if (!e.target.closest("#mobile-nav-drawer") && !e.target.closest("#mobile-menu-toggle")) {
      drawer.classList.remove("is-open");
    }
  });

  $$(".mobile-nav-item", drawer).forEach((item) => {
    item.addEventListener("click", () => {
      drawer.classList.remove("is-open");
    });
  });
}

function initNavTabs() {
  const tabs = $$("[data-nav-filter]");
  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      const filter = tab.dataset.navFilter;
      tabs.forEach((t) => {
        if (t.dataset.navFilter === filter) {
          t.classList.add("is-active");
        } else {
          t.classList.remove("is-active");
        }
      });

      if (filter === "overview") {
        $$(".connections-svg path").forEach((p) => { p.style.display = ""; });
      } else if (filter === "services") {
        $$(".conn-http").forEach((p) => { p.style.display = ""; });
        $$(".conn-event, .conn-data").forEach((p) => { p.style.display = "none"; });
      } else if (filter === "events") {
        $$(".conn-event").forEach((p) => { p.style.display = ""; });
        $$(".conn-http, .conn-data").forEach((p) => { p.style.display = "none"; });
      } else if (filter === "data") {
        $$(".conn-data").forEach((p) => { p.style.display = ""; });
        $$(".conn-http, .conn-event").forEach((p) => { p.style.display = "none"; });
      } else if (filter === "api") {
        window.location.href = "/dev";
      }
    });
  });
}

function start() {
  const services = initServices(data, index);
  initCanvasConnections();
  initPanZoom();
  initNodeInteractions(services);
  initMobileMenu();
  initNavTabs();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", start);
} else {
  start();
}
