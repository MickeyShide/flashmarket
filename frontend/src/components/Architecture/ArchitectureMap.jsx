import React, { useRef, useEffect, useState, useCallback, useMemo } from 'react';
import { NODES } from './architectureData';
import { NodeIcon } from './ArchitectureIcons';
import {
  BASE_NODE_POSITIONS,
  MOBILE_NODE_POSITIONS,
  getBoundingBoxForPositions,
} from './architectureLayout';

/* ─────────────────────────────── helpers ─────────────────────────────── */
const isMobileWidth = (w) => w < 768;

const FILTER_TABS = [
  { id: 'all', label: 'Все связи', icon: '📌', shortLabel: 'Все' },
  { id: 'api', label: 'HTTP', icon: '🌐', shortLabel: 'HTTP' },
  { id: 'events', label: 'RabbitMQ', icon: '⚡', shortLabel: 'RMQ' },
  { id: 'database', label: 'PostgreSQL', icon: '🗄️', shortLabel: 'PG' },
  { id: 'storage', label: 'Redis & S3', icon: '📦', shortLabel: 'R&S3' },
];

/* ═══════════════════════════════ COMPONENT ═══════════════════════════════ */
export const ArchitectureMap = ({
  selectedNodeId,
  onSelectNode,
  isolatedNodes,
  activeCategoryFilter = 'overview',
}) => {
  const containerRef = useRef(null);
  const [containerSize, setContainerSize] = useState({ width: 0, height: 0 });

  /* ── Determine mobile vs desktop from actual container ── */
  const isMobile = isMobileWidth(containerSize.width || (typeof window !== 'undefined' ? window.innerWidth : 1024));

  /* ── Choose layout positions ── */
  const positions = useMemo(() => isMobile ? MOBILE_NODE_POSITIONS : BASE_NODE_POSITIONS, [isMobile]);
  const boundingBox = useMemo(() => getBoundingBoxForPositions(positions), [positions]);

  /* SVG canvas dimensions — just enough to contain all nodes with padding */
  const canvasW = useMemo(() => Math.ceil(boundingBox.maxX + 40), [boundingBox]);
  const canvasH = useMemo(() => Math.ceil(boundingBox.maxY + 40), [boundingBox]);

  /* ── Zoom & Pan state ── */
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isPanning, setIsPanning] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });

  /* ── Container measurement ── */
  const measureContainer = useCallback(() => {
    if (containerRef.current) {
      const rect = containerRef.current.getBoundingClientRect();
      if (rect.width > 50 && rect.height > 50) {
        setContainerSize({ width: rect.width, height: rect.height });
        return { width: rect.width, height: rect.height };
      }
    }
    const w = typeof window !== 'undefined' ? window.innerWidth : 1024;
    const h = typeof window !== 'undefined' ? window.innerHeight - 120 : 600;
    return { width: w, height: Math.max(h, 400) };
  }, []);

  /* ── Fit / Center canvas ── */
  const fitView = useCallback((dims, box, mobile) => {
    const cw = dims?.width || containerSize.width || 800;
    const ch = dims?.height || containerSize.height || 600;

    const graphW = box ? box.maxX + 40 : canvasW;
    const graphH = box ? box.maxY + 40 : canvasH;

    const paddingX = mobile ? 12 : 32;
    const paddingY = mobile ? 12 : 32;

    const scaleX = (cw - paddingX * 2) / graphW;
    const scaleY = (ch - paddingY * 2) / graphH;

    let newZoom;
    if (mobile) {
      // On mobile, ensure labels remain readable — don't zoom out too far
      newZoom = Math.min(Math.max(Math.min(scaleX, scaleY), 0.65), 1.3);
    } else {
      // Desktop: never scale up past 1.0 — graph should look compact and precise
      newZoom = Math.min(Math.max(Math.min(scaleX, scaleY), 0.5), 1.0);
    }

    const newPanX = Math.round((cw - graphW * newZoom) / 2);
    const newPanY = Math.round((ch - graphH * newZoom) / 2);

    setZoom(newZoom);
    setPan({ x: newPanX, y: Math.max(mobile ? 4 : 8, newPanY) });
  }, [containerSize, canvasW, canvasH]);

  /* ── Initial fit & resize handling ── */
  useEffect(() => {
    const dims = measureContainer();
    const mobile = isMobileWidth(dims.width);
    const box = getBoundingBoxForPositions(mobile ? MOBILE_NODE_POSITIONS : BASE_NODE_POSITIONS);
    fitView(dims, box, mobile);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    let resizeTimer;
    const handleResize = () => {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(() => {
        const dims = measureContainer();
        const mobile = isMobileWidth(dims.width);
        const box = getBoundingBoxForPositions(mobile ? MOBILE_NODE_POSITIONS : BASE_NODE_POSITIONS);
        fitView(dims, box, mobile);
      }, 150);
    };
    window.addEventListener('resize', handleResize);

    let observer = null;
    if (typeof ResizeObserver !== 'undefined' && containerRef.current) {
      observer = new ResizeObserver(() => {
        const dims = measureContainer();
        setContainerSize(dims);
      });
      observer.observe(containerRef.current);
    }

    return () => {
      window.removeEventListener('resize', handleResize);
      clearTimeout(resizeTimer);
      if (observer) observer.disconnect();
    };
  }, [measureContainer, fitView]);

  /* ── Re-fit when isolation / selection changes ── */
  useEffect(() => {
    if (isolatedNodes && isolatedNodes.length > 0) {
      // Frame the isolated subset
      const dims = measureContainer();
      const mobile = isMobileWidth(dims.width);
      const activePositions = {};
      const pos = mobile ? MOBILE_NODE_POSITIONS : BASE_NODE_POSITIONS;
      isolatedNodes.forEach((id) => {
        if (pos[id]) activePositions[id] = pos[id];
      });
      if (Object.keys(activePositions).length > 0) {
        const subBox = getBoundingBoxForPositions(activePositions);
        const cw = mobile ? dims.width : Math.max(dims.width - 400, 400);
        const ch = mobile ? Math.max(dims.height * 0.55, 300) : Math.max(dims.height - 60, 400);

        const scaleX = cw / (subBox.width + 100);
        const scaleY = ch / (subBox.height + 100);
        const targetZoom = Math.min(Math.max(Math.min(scaleX, scaleY), 0.55), 1.2);

        const centerX = mobile ? dims.width / 2 : cw / 2;
        const centerY = mobile ? ch / 2 : dims.height / 2;

        setZoom(targetZoom);
        setPan({
          x: Math.round(centerX - subBox.centerX * targetZoom),
          y: Math.round(centerY - subBox.centerY * targetZoom),
        });
      }
    } else {
      const dims = measureContainer();
      const mobile = isMobileWidth(dims.width);
      const box = getBoundingBoxForPositions(mobile ? MOBILE_NODE_POSITIONS : BASE_NODE_POSITIONS);
      fitView(dims, box, mobile);
    }
  }, [isolatedNodes]); // eslint-disable-line react-hooks/exhaustive-deps

  /* ── Node positions ── */
  const nodePositions = useMemo(() => {
    const res = {};
    Object.entries(positions).forEach(([id, base]) => {
      const x = base.x;
      const y = base.y;
      res[id] = {
        x, y,
        left: x, top: y,
        width: base.width, height: base.height,
        right: x + base.width,
        bottom: y + base.height,
        centerX: x + base.width / 2,
        centerY: y + base.height / 2,
      };
    });
    return res;
  }, [positions]);

  /* ── Native wheel handler (prevent page scroll, enable zoom) ── */
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const onWheelNative = (e) => {
      if (e.target.closest('.no-wheel')) return;
      e.preventDefault();
      e.stopPropagation();

      const rect = el.getBoundingClientRect();
      const mouseX = e.clientX - rect.left;
      const mouseY = e.clientY - rect.top;

      const zoomFactor = e.deltaY < 0 ? 1.09 : 0.91;
      setZoom((prevZoom) => {
        const newZoom = Math.min(Math.max(prevZoom * zoomFactor, 0.3), 2.5);
        setPan((prevPan) => ({
          x: Math.round(mouseX - (mouseX - prevPan.x) * (newZoom / prevZoom)),
          y: Math.round(mouseY - (mouseY - prevPan.y) * (newZoom / prevZoom)),
        }));
        return newZoom;
      });
    };

    const onGesture = (e) => {
      e.preventDefault();
      e.stopPropagation();
    };

    el.addEventListener('wheel', onWheelNative, { passive: false });
    el.addEventListener('gesturestart', onGesture, { passive: false });
    el.addEventListener('gesturechange', onGesture, { passive: false });

    return () => {
      el.removeEventListener('wheel', onWheelNative);
      el.removeEventListener('gesturestart', onGesture);
      el.removeEventListener('gesturechange', onGesture);
    };
  }, []);

  /* ── Mouse pan ── */
  const handleMouseDown = (e) => {
    if (e.target.closest('[data-node-id]') || e.target.closest('.no-pan')) return;
    setIsPanning(true);
    setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
  };
  const handleMouseMove = (e) => {
    if (!isPanning) return;
    setPan({ x: e.clientX - dragStart.x, y: e.clientY - dragStart.y });
  };
  const handleMouseUp = () => setIsPanning(false);

  /* ── Touch pan & pinch ── */
  const touchState = useRef({ lastDist: null, lastCenter: null, startPan: null });

  const handleTouchStart = (e) => {
    if (e.touches.length === 1) {
      if (e.target.closest('[data-node-id]')) return;
      setIsPanning(true);
      setDragStart({ x: e.touches[0].clientX - pan.x, y: e.touches[0].clientY - pan.y });
      touchState.current.startPan = { x: pan.x, y: pan.y };
    } else if (e.touches.length === 2) {
      setIsPanning(false);
      const dist = Math.hypot(
        e.touches[0].clientX - e.touches[1].clientX,
        e.touches[0].clientY - e.touches[1].clientY
      );
      touchState.current.lastDist = dist;
      touchState.current.lastCenter = {
        x: (e.touches[0].clientX + e.touches[1].clientX) / 2,
        y: (e.touches[0].clientY + e.touches[1].clientY) / 2,
      };
    }
  };

  const handleTouchMove = (e) => {
    if (e.touches.length === 1 && isPanning) {
      setPan({
        x: e.touches[0].clientX - dragStart.x,
        y: e.touches[0].clientY - dragStart.y,
      });
    } else if (e.touches.length === 2 && touchState.current.lastDist) {
      const dist = Math.hypot(
        e.touches[0].clientX - e.touches[1].clientX,
        e.touches[0].clientY - e.touches[1].clientY
      );
      const factor = dist / touchState.current.lastDist;

      const center = {
        x: (e.touches[0].clientX + e.touches[1].clientX) / 2,
        y: (e.touches[0].clientY + e.touches[1].clientY) / 2,
      };

      setZoom((prev) => {
        const newZ = Math.min(Math.max(prev * factor, 0.3), 2.5);
        if (containerRef.current) {
          const rect = containerRef.current.getBoundingClientRect();
          const cx = center.x - rect.left;
          const cy = center.y - rect.top;
          setPan((prevPan) => ({
            x: Math.round(cx - (cx - prevPan.x) * (newZ / prev)),
            y: Math.round(cy - (cy - prevPan.y) * (newZ / prev)),
          }));
        }
        return newZ;
      });
      touchState.current.lastDist = dist;
      touchState.current.lastCenter = center;
    }
  };

  const handleTouchEnd = () => {
    setIsPanning(false);
    touchState.current.lastDist = null;
    touchState.current.lastCenter = null;
    touchState.current.startPan = null;
  };

  /* Handle tap on empty canvas to deselect */
  const handleCanvasTap = (e) => {
    if (e.target.closest('[data-node-id]') || e.target.closest('.no-pan')) return;
    if (selectedNodeId) {
      onSelectNode(null);
    }
  };

  /* ═══════════════════ SVG Edge Paths ═══════════════════ */
  const svgPaths = useMemo(() => {
    const p = nodePositions;
    if (!p['node-service-inventory']) return [];
    const paths = [];

    // 1. Inter-Service Synchronous Direct Calls (HTTP)
    const inv = p['node-service-inventory'];
    const drp = p['node-service-drops'];
    if (inv && drp) {
      paths.push({
        id: 'inv-drops-http', from: 'node-service-inventory', to: 'node-service-drops', type: 'http',
        d: `M ${Math.round(inv.centerX)} ${Math.round(inv.bottom)} C ${Math.round(inv.centerX)} ${Math.round((inv.bottom + drp.top) / 2)}, ${Math.round(drp.centerX)} ${Math.round((inv.bottom + drp.top) / 2)}, ${Math.round(drp.centerX)} ${Math.round(drp.top)}`,
      });
    }

    const orders = p['node-service-orders'];
    const payments = p['node-service-payments'];
    if (orders && payments) {
      paths.push({
        id: 'orders-payments-http', from: 'node-service-orders', to: 'node-service-payments', type: 'http',
        d: `M ${Math.round(orders.right)} ${Math.round(orders.centerY)} L ${Math.round(payments.left)} ${Math.round(payments.centerY)}`,
      });
    }

    const wish = p['node-service-wishlist'];
    const cat = p['node-service-catalog'];
    if (wish && cat) {
      paths.push({
        id: 'wishlist-catalog-http', from: 'node-service-wishlist', to: 'node-service-catalog', type: 'http',
        d: `M ${Math.round(wish.centerX)} ${Math.round(wish.top)} C ${Math.round(wish.centerX)} ${Math.round((wish.top + cat.bottom) / 2)}, ${Math.round(cat.centerX)} ${Math.round((wish.top + cat.bottom) / 2)}, ${Math.round(cat.centerX)} ${Math.round(cat.bottom)}`,
      });
    }

    // 2. RabbitMQ & Celery event connections
    const rmq = p['node-component-rabbitmq'];
    const cel = p['node-component-celery'];

    if (rmq) {
      const eventPublishers = [
        { id: 'node-service-auth', slotRatio: 0.15 },
        { id: 'node-service-notifications', slotRatio: 0.28 },
        { id: 'node-service-wishlist', slotRatio: 0.42 },
        { id: 'node-service-inventory', slotRatio: 0.58 },
        { id: 'node-service-drops', slotRatio: 0.72 },
        { id: 'node-service-orders', slotRatio: 0.85 },
        { id: 'node-service-payments', slotRatio: 0.95 },
      ];

      eventPublishers.forEach(({ id, slotRatio }) => {
        const s = p[id];
        if (!s) return;
        const targetX = Math.round(rmq.left + rmq.width * slotRatio);
        const midY = Math.round((s.bottom + rmq.top) / 2);
        paths.push({
          id: `rmq-${id}`, from: id, to: 'node-component-rabbitmq', type: 'event',
          d: `M ${Math.round(s.centerX)} ${Math.round(s.bottom)} C ${Math.round(s.centerX)} ${midY}, ${targetX} ${midY}, ${targetX} ${Math.round(rmq.top)}`,
        });
      });

      if (cel) {
        paths.push({
          id: 'rmq-celery', from: 'node-component-rabbitmq', to: 'node-component-celery', type: 'event',
          d: `M ${Math.round(rmq.right)} ${Math.round(rmq.centerY)} L ${Math.round(cel.left)} ${Math.round(cel.centerY)}`,
        });
      }
    }

    // 3. PostgreSQL connections
    const pg = p['node-component-postgres'];
    if (pg) {
      const all9Services = [
        { id: 'node-service-auth', slotRatio: 0.12 },
        { id: 'node-service-notifications', slotRatio: 0.22 },
        { id: 'node-service-catalog', slotRatio: 0.32 },
        { id: 'node-service-wishlist', slotRatio: 0.44 },
        { id: 'node-service-inventory', slotRatio: 0.55 },
        { id: 'node-service-drops', slotRatio: 0.66 },
        { id: 'node-service-orders', slotRatio: 0.77 },
        { id: 'node-service-media', slotRatio: 0.88 },
        { id: 'node-service-payments', slotRatio: 0.96 },
      ];

      all9Services.forEach(({ id, slotRatio }) => {
        const s = p[id];
        if (!s) return;
        const targetX = Math.round(pg.left + pg.width * slotRatio);
        const midY = Math.round((s.bottom + pg.top) / 2);
        paths.push({
          id: `pg-${id}`, from: id, to: 'node-component-postgres', type: 'postgres',
          d: `M ${Math.round(s.centerX)} ${Math.round(s.bottom)} C ${Math.round(s.centerX)} ${midY + 15}, ${targetX} ${midY - 15}, ${targetX} ${Math.round(pg.top)}`,
        });
      });
    }

    // 4. Redis connections
    const red = p['node-component-redis'];
    if (red) {
      const redisUsers = [
        { id: 'node-service-auth', slotRatio: 0.25 },
        { id: 'node-service-catalog', slotRatio: 0.5 },
        { id: 'node-service-inventory', slotRatio: 0.75 },
      ];

      redisUsers.forEach(({ id, slotRatio }) => {
        const s = p[id];
        if (!s) return;
        const targetX = Math.round(red.left + red.width * slotRatio);
        const midY = Math.round((s.bottom + red.top) / 2);
        paths.push({
          id: `red-${id}`, from: id, to: 'node-component-redis', type: 'redis',
          d: `M ${Math.round(s.centerX)} ${Math.round(s.bottom)} C ${Math.round(s.centerX)} ${midY}, ${targetX} ${midY}, ${targetX} ${Math.round(red.top)}`,
        });
      });

      if (cel) {
        paths.push({
          id: 'celery-redis', from: 'node-component-celery', to: 'node-component-redis', type: 'redis',
          d: `M ${Math.round(cel.left + 25)} ${Math.round(cel.bottom)} C ${Math.round(cel.left + 25)} ${Math.round((cel.bottom + red.top) / 2)}, ${Math.round(red.right - 20)} ${Math.round((cel.bottom + red.top) / 2)}, ${Math.round(red.right - 20)} ${Math.round(red.top)}`,
        });
      }
    }

    // 5. S3 connections
    const s3 = p['node-component-s3'];
    const media = p['node-service-media'];
    if (s3 && media) {
      paths.push({
        id: 's3-media', from: 'node-service-media', to: 'node-component-s3', type: 's3',
        d: `M ${Math.round(media.centerX)} ${Math.round(media.bottom)} C ${Math.round(media.centerX)} ${Math.round((media.bottom + s3.top) / 2)}, ${Math.round(s3.centerX + 15)} ${Math.round((media.bottom + s3.top) / 2)}, ${Math.round(s3.centerX + 15)} ${Math.round(s3.top)}`,
      });
    }
    if (s3 && cel && isolatedNodes?.includes('node-component-celery') && isolatedNodes?.includes('node-component-s3')) {
      paths.push({
        id: 's3-celery', from: 'node-component-celery', to: 'node-component-s3', type: 's3',
        d: `M ${Math.round(cel.centerX - 15)} ${Math.round(cel.bottom)} L ${Math.round(s3.centerX + 15)} ${Math.round(s3.top)}`,
      });
    }

    // 6. Prometheus
    const prom = p['node-component-prometheus'];
    if (cel && prom) {
      paths.push({
        id: 'prom-celery', from: 'node-component-celery', to: 'node-component-prometheus', type: 'prom',
        d: `M ${Math.round(cel.centerX + 25)} ${Math.round(cel.bottom)} C ${Math.round(cel.centerX + 25)} ${Math.round((cel.bottom + prom.top) / 2)}, ${Math.round(prom.centerX)} ${Math.round((cel.bottom + prom.top) / 2)}, ${Math.round(prom.centerX)} ${Math.round(prom.top)}`,
      });
    }

    return paths;
  }, [nodePositions, isolatedNodes]);

  /* ═══════════════════ Layer filter state ═══════════════════ */
  const [layerFilter, setLayerFilter] = useState('all');

  const isNodeActive = (nodeId) => {
    if (isolatedNodes && isolatedNodes.length > 0) {
      return isolatedNodes.includes(nodeId);
    }
    if (layerFilter === 'all') return true;
    if (layerFilter === 'api') {
      return ['node-service-inventory', 'node-service-drops', 'node-service-orders', 'node-service-payments', 'node-service-wishlist', 'node-service-catalog'].includes(nodeId);
    }
    if (layerFilter === 'events') {
      return (
        nodeId === 'node-component-rabbitmq' ||
        nodeId === 'node-component-celery' ||
        ['node-service-auth', 'node-service-inventory', 'node-service-orders', 'node-service-payments', 'node-service-notifications', 'node-service-wishlist', 'node-service-drops'].includes(nodeId)
      );
    }
    if (layerFilter === 'database') {
      return nodeId === 'node-component-postgres' || nodeId.startsWith('node-service-');
    }
    if (layerFilter === 'storage') {
      return (
        ['node-component-redis', 'node-component-s3', 'node-component-prometheus', 'node-component-celery', 'node-service-auth', 'node-service-catalog', 'node-service-inventory', 'node-service-media'].includes(nodeId)
      );
    }
    return true;
  };

  const isPathActive = (fromId, toId, type) => {
    if (isolatedNodes && isolatedNodes.length > 0) {
      return isolatedNodes.includes(fromId) && isolatedNodes.includes(toId);
    }
    if (layerFilter === 'all') return true;
    if (layerFilter === 'api') return type === 'http';
    if (layerFilter === 'events') return type === 'event';
    if (layerFilter === 'database') return type === 'postgres';
    if (layerFilter === 'storage') return type === 'redis' || type === 's3' || type === 'prom';
    return true;
  };

  const isLayerFocus = layerFilter !== 'all';

  /* ── Mobile filter dropdown state ── */
  const [showMobileFilter, setShowMobileFilter] = useState(false);
  const filterRef = useRef(null);

  useEffect(() => {
    const handleClick = (e) => {
      if (filterRef.current && !filterRef.current.contains(e.target)) {
        setShowMobileFilter(false);
      }
    };
    document.addEventListener('mousedown', handleClick);
    document.addEventListener('touchstart', handleClick);
    return () => {
      document.removeEventListener('mousedown', handleClick);
      document.removeEventListener('touchstart', handleClick);
    };
  }, []);

  /* ═══════════════════ RENDER ═══════════════════ */
  return (
    <div
      ref={containerRef}
      className={`relative w-full flex-1 overflow-hidden select-none touch-none ${
        isPanning ? 'cursor-grabbing' : 'cursor-grab'
      }`}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
      onTouchStart={handleTouchStart}
      onTouchMove={handleTouchMove}
      onTouchEnd={handleTouchEnd}
      onClick={handleCanvasTap}
      role="application"
      aria-label="Карта архитектуры FlashMarket"
      style={{
        minHeight: isMobile ? '400px' : '560px',
        height: '100%',
        overscrollBehavior: 'contain',
        backgroundImage: 'radial-gradient(rgba(0, 0, 0, 0.06) 1.2px, transparent 1.2px)',
        backgroundSize: '26px 26px',
        backgroundColor: '#FAFAFA',
      }}
    >



      {/* ──────── Map World Container ──────── */}
      <div
        id="map-world-inner"
        className="absolute pointer-events-auto"
        style={{
          width: `${canvasW}px`,
          height: `${canvasH}px`,
          transformOrigin: '0 0',
          transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
          transition: isPanning ? 'none' : 'transform 0.4s cubic-bezier(0.16, 1, 0.3, 1)',
        }}
      >
        {/* ──── SVG Connections Layer ──── */}
        <svg
          className="absolute inset-0 w-full h-full pointer-events-none z-10 overflow-visible"
          viewBox={`0 0 ${canvasW} ${canvasH}`}
          aria-hidden="true"
        >
          {svgPaths.map((path) => {
            const active = isPathActive(path.from, path.to, path.type);
            let strokeColor = '#2563EB';
            let strokeDash = 'none';

            if (path.type === 'event') {
              strokeColor = '#EA580C'; strokeDash = '5 3.5';
            } else if (path.type === 'postgres') {
              strokeColor = '#7C3AED'; strokeDash = '3 3';
            } else if (path.type === 'redis') {
              strokeColor = '#DC2626'; strokeDash = '3 3';
            } else if (path.type === 's3') {
              strokeColor = '#16A34A'; strokeDash = '3 3';
            } else if (path.type === 'prom') {
              strokeColor = '#6B7280'; strokeDash = '3 3';
            }

            const isHighPriority = active && (isolatedNodes || isLayerFocus);
            const baseOpacity = isHighPriority ? 1 : path.type === 'postgres' ? 0.35 : 0.65;

            return (
              <path
                key={path.id}
                d={path.d}
                fill="none"
                stroke={strokeColor}
                strokeWidth={isHighPriority ? 2.4 : 1.4}
                strokeDasharray={strokeDash}
                strokeLinecap="round"
                strokeLinejoin="round"
                opacity={active ? baseOpacity : 0.03}
                style={{
                  filter: isHighPriority ? 'drop-shadow(0 0 3px rgba(0,0,0,0.15))' : 'none',
                  transition: 'opacity 0.25s ease, stroke-width 0.25s ease',
                }}
              />
            );
          })}
        </svg>

        {/* ──── Nodes Layer ──── */}
        <div className="relative w-full h-full z-20">
          {/* Services backdrop — desktop only */}
          {!isMobile && (
            <div
              className="absolute border border-dashed border-zinc-300 rounded-2xl bg-white/40 pointer-events-none"
              style={{
                top: positions['node-service-auth']?.y - 10 || 25,
                left: positions['node-service-auth']?.x - 10 || 25,
                width: (positions['node-service-payments']?.x || 575) + (positions['node-service-payments']?.width || 110) - (positions['node-service-auth']?.x || 35) + 20,
                height: (positions['node-service-media']?.y || 108) + (positions['node-service-media']?.height || 56) - (positions['node-service-auth']?.y || 35) + 20,
                opacity: isolatedNodes || isLayerFocus ? 0.35 : 1,
                transition: 'opacity 0.35s ease',
              }}
            >
              <span className="absolute -top-2.5 left-1/2 -translate-x-1/2 bg-[#FAFAFA] px-2.5 font-mono text-[9px] font-black text-zinc-400 tracking-wider whitespace-nowrap">
                МИКРОСЕРВИСЫ
              </span>
            </div>
          )}

          {/* Mobile services backdrop */}
          {isMobile && (
            <div
              className="absolute border border-dashed border-zinc-300/70 rounded-xl bg-white/30 pointer-events-none"
              style={{
                top: 10,
                left: 5,
                width: 370,
                height: 190,
                opacity: isolatedNodes || isLayerFocus ? 0.25 : 0.8,
                transition: 'opacity 0.35s ease',
              }}
            />
          )}

          {/* ── Service Nodes ── */}
          {NODES.filter((n) => n.type === 'service').map((service) => {
            const active = isNodeActive(service.id);
            const selected = selectedNodeId === service.entityId;
            const pos = positions[service.id];
            if (!pos) return null;

            return (
              <div
                key={service.id}
                data-node-id={service.id}
                onClick={(e) => { e.stopPropagation(); onSelectNode(service.entityId); }}
                role="button"
                tabIndex={0}
                aria-label={`Сервис: ${service.name}`}
                aria-pressed={selected}
                onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onSelectNode(service.entityId); } }}
                className={`absolute flex items-center gap-1.5 md:gap-2 px-2 md:px-2.5 bg-white border border-zinc-200 rounded-xl shadow-sm cursor-pointer transition-all duration-200 ${
                  active ? 'opacity-100 hover:border-black hover:shadow-md' : 'opacity-20'
                } ${selected ? 'ring-2 ring-black shadow-lg z-30' : ''}`}
                style={{
                  top: pos.y,
                  left: pos.x,
                  width: pos.width,
                  height: pos.height,
                  minHeight: '44px',
                }}
              >
                <span className="absolute top-1.5 right-1.5 w-1.5 h-1.5 rounded-full bg-emerald-500 shadow-[0_0_6px_#10B981]" />
                <div className={`${isMobile ? 'w-5 h-5' : 'w-7 h-7'} rounded-lg bg-zinc-100 flex items-center justify-center shrink-0`}>
                  <NodeIcon iconKey={service.icon} className={isMobile ? 'w-3.5 h-3.5' : 'w-4 h-4'} />
                </div>
                <span className={`font-black ${isMobile ? 'text-[10px]' : 'text-[11px]'} text-zinc-900 tracking-tight leading-tight truncate`}
                  title={service.name}
                >
                  {service.name}
                </span>
              </div>
            );
          })}

          {/* ── RabbitMQ Node ── */}
          {(() => {
            const rmqPos = positions['node-component-rabbitmq'];
            if (!rmqPos) return null;
            return (
              <div
                data-node-id="node-component-rabbitmq"
                onClick={(e) => { e.stopPropagation(); onSelectNode('component-rabbitmq'); }}
                role="button"
                tabIndex={0}
                aria-label="Инфраструктура: RabbitMQ"
                onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onSelectNode('component-rabbitmq'); } }}
                className={`absolute flex items-center gap-2 md:gap-2.5 px-2.5 md:px-3 bg-white border border-zinc-200 rounded-xl shadow-sm cursor-pointer transition-all duration-200 ${
                  isNodeActive('node-component-rabbitmq') ? 'opacity-100 hover:border-amber-500 hover:shadow-md' : 'opacity-20'
                } ${selectedNodeId === 'component-rabbitmq' ? 'ring-2 ring-amber-500 shadow-lg z-30' : ''}`}
                style={{ top: rmqPos.y, left: rmqPos.x, width: rmqPos.width, height: rmqPos.height, minHeight: '42px' }}
              >
                <div className={`${isMobile ? 'w-5 h-5' : 'w-7 h-7'} rounded-lg bg-amber-50 flex items-center justify-center shrink-0`}>
                  <NodeIcon iconKey="rabbitmq" className={isMobile ? 'w-3.5 h-3.5' : 'w-4 h-4'} />
                </div>
                <strong className={`${isMobile ? 'text-[10px]' : 'text-[12px]'} font-black text-black block leading-tight`}>RabbitMQ</strong>
              </div>
            );
          })()}

          {/* ── Celery Node ── */}
          {(() => {
            const celPos = positions['node-component-celery'];
            if (!celPos) return null;
            return (
              <div
                data-node-id="node-component-celery"
                onClick={(e) => { e.stopPropagation(); onSelectNode('component-celery'); }}
                role="button"
                tabIndex={0}
                aria-label="Инфраструктура: Celery"
                onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onSelectNode('component-celery'); } }}
                className={`absolute flex items-center gap-2 md:gap-2.5 px-2.5 md:px-3 bg-white border border-zinc-200 rounded-xl shadow-sm cursor-pointer transition-all duration-200 ${
                  isNodeActive('node-component-celery') ? 'opacity-100 hover:border-orange-500 hover:shadow-md' : 'opacity-20'
                } ${selectedNodeId === 'component-celery' ? 'ring-2 ring-orange-500 shadow-lg z-30' : ''}`}
                style={{ top: celPos.y, left: celPos.x, width: celPos.width, height: celPos.height, minHeight: '42px' }}
              >
                <div className={`${isMobile ? 'w-5 h-5' : 'w-7 h-7'} rounded-lg bg-orange-50 flex items-center justify-center shrink-0`}>
                  <NodeIcon iconKey="celery" className={isMobile ? 'w-3.5 h-3.5' : 'w-4 h-4'} />
                </div>
                <strong className={`${isMobile ? 'text-[10px]' : 'text-[12px]'} font-black text-black block leading-tight`}>Celery</strong>
              </div>
            );
          })()}

          {/* ── Bottom Row Infrastructure Nodes ── */}
          {NODES.filter((n) => n.type === 'infra' && n.id.startsWith('node-component-') && !['node-component-rabbitmq', 'node-component-celery'].includes(n.id)).map((infra) => {
            const active = isNodeActive(infra.id);
            const selected = selectedNodeId === infra.entityId;
            const pos = positions[infra.id];
            if (!pos) return null;

            return (
              <div
                key={infra.id}
                data-node-id={infra.id}
                onClick={(e) => { e.stopPropagation(); onSelectNode(infra.entityId); }}
                role="button"
                tabIndex={0}
                aria-label={`Инфраструктура: ${infra.name}`}
                onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onSelectNode(infra.entityId); } }}
                className={`absolute flex items-center gap-2 md:gap-2.5 px-2.5 md:px-3 bg-white border border-zinc-200 rounded-xl shadow-sm cursor-pointer transition-all duration-200 ${
                  active ? 'opacity-100 hover:border-black hover:shadow-md' : 'opacity-20'
                } ${selected ? 'ring-2 ring-black shadow-lg z-30' : ''}`}
                style={{ top: pos.y, left: pos.x, width: pos.width, height: pos.height, minHeight: '42px' }}
              >
                <div className={`${isMobile ? 'w-5 h-5' : 'w-7 h-7'} rounded-lg bg-zinc-100 flex items-center justify-center shrink-0`}>
                  <NodeIcon iconKey={infra.icon} className={isMobile ? 'w-3.5 h-3.5' : 'w-4 h-4'} />
                </div>
                <strong className={`${isMobile ? 'text-[10px]' : 'text-[11.5px]'} font-black text-black block leading-tight truncate`}
                  title={infra.name}
                >
                  {infra.name}
                </strong>
              </div>
            );
          })}
        </div>
      </div>

      {/* No zoom controls — removed per explicit requirement */}
    </div>
  );
};
