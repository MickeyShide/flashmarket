import React, { useState, useEffect, useRef, useCallback } from 'react';
import { NODES, ROUTE_EXPLANATIONS, CELERY_TASKS, SERVICE_EVENT_HANDLERS } from './architectureData';
import { NodeIcon } from './ArchitectureIcons';

function getModuleIconKey(name = '') {
  const n = name.toLowerCase();
  if (n.includes('rabbit')) return 'rabbitmq';
  if (n.includes('postgre') || n.includes('postgres') || n.includes('pg_')) return 'postgres';
  if (n.includes('redis')) return 'redis';
  if (n.includes('s3') || n.includes('minio') || n.includes('storage')) return 's3';
  if (n.includes('prometheus') || n.includes('metrics')) return 'prometheus';
  if (n.includes('celery') || n.includes('worker') || n.includes('beat')) return 'celery';
  if (n.includes('nginx') || n.includes('gateway')) return 'gateway';
  if (n.includes('auth')) return 'auth';
  if (n.includes('catalog')) return 'catalog';
  if (n.includes('inventory')) return 'inventory';
  if (n.includes('order')) return 'orders';
  if (n.includes('payment')) return 'payments';
  if (n.includes('notif')) return 'notifications';
  if (n.includes('wishlist')) return 'wishlist';
  if (n.includes('drop')) return 'drops';
  if (n.includes('media')) return 'media';
  return 'gateway';
}

/* ─── Bottom Sheet Heights (mobile) ─── */
const SHEET_COLLAPSED = 72;   // just header
const SHEET_MID = 0.45;       // 45% of viewport
const SHEET_FULL = 0.88;      // 88% of viewport

export const ArchitectureInspector = ({
  nodeId,
  onClose,
  onIsolateRoute,
  onResetServiceIsolation,
}) => {
  const [subView, setSubView] = useState('main');
  const [selectedDetail, setSelectedDetail] = useState(null);
  const [isMobile, setIsMobile] = useState(typeof window !== 'undefined' ? window.innerWidth < 768 : false);

  /* ── Bottom Sheet state (mobile) ── */
  const [sheetHeight, setSheetHeight] = useState(SHEET_MID);
  const sheetRef = useRef(null);
  const dragRef = useRef({ startY: 0, startHeight: 0, isDragging: false });

  // Track mobile vs desktop
  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth < 768);
    window.addEventListener('resize', check);
    return () => window.removeEventListener('resize', check);
  }, []);

  // Find entity
  const entity = NODES.find((n) => n.entityId === nodeId || n.id === nodeId);

  // Reset view when node changes
  useEffect(() => {
    setSubView('main');
    setSelectedDetail(null);
    setSheetHeight(SHEET_MID);
  }, [nodeId]);

  /* ── Sheet drag handlers ── */
  const handleDragStart = useCallback((clientY) => {
    dragRef.current = {
      startY: clientY,
      startHeight: sheetRef.current ? sheetRef.current.getBoundingClientRect().height : window.innerHeight * sheetHeight,
      isDragging: true,
    };
  }, [sheetHeight]);

  const handleDragMove = useCallback((clientY) => {
    if (!dragRef.current.isDragging) return;
    const delta = dragRef.current.startY - clientY;
    const newH = dragRef.current.startHeight + delta;
    const vh = window.innerHeight;
    const ratio = Math.max(SHEET_COLLAPSED / vh, Math.min(newH / vh, SHEET_FULL));
    setSheetHeight(ratio);
  }, []);

  const handleDragEnd = useCallback(() => {
    if (!dragRef.current.isDragging) return;
    dragRef.current.isDragging = false;
    const vh = window.innerHeight;
    const currentH = sheetHeight * vh;

    // Snap to nearest position
    const collapsedThreshold = SHEET_COLLAPSED + 40;
    const midH = vh * SHEET_MID;
    const fullH = vh * SHEET_FULL;

    if (currentH < collapsedThreshold) {
      // Close sheet
      onClose();
      return;
    }
    if (currentH < (midH + SHEET_COLLAPSED) / 2) {
      setSheetHeight(SHEET_COLLAPSED / vh);
    } else if (currentH < (midH + fullH) / 2) {
      setSheetHeight(SHEET_MID);
    } else {
      setSheetHeight(SHEET_FULL);
    }
  }, [sheetHeight, onClose]);

  // Touch handlers for sheet drag
  const onSheetTouchStart = (e) => {
    if (e.target.closest('.sheet-scroll-content')) {
      const el = e.target.closest('.sheet-scroll-content');
      if (el.scrollTop > 0) return; // Let scroll handle it
    }
    handleDragStart(e.touches[0].clientY);
  };
  const onSheetTouchMove = (e) => handleDragMove(e.touches[0].clientY);
  const onSheetTouchEnd = () => handleDragEnd();

  // Mouse handlers for sheet drag (for testing)
  const onSheetMouseDown = (e) => {
    if (!e.target.closest('.sheet-drag-handle')) return;
    handleDragStart(e.clientY);
    const onMove = (ev) => handleDragMove(ev.clientY);
    const onUp = () => { handleDragEnd(); window.removeEventListener('mousemove', onMove); window.removeEventListener('mouseup', onUp); };
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
  };

  if (!entity) return null;

  const isCelery = entity.entityId === 'component-celery';

  // Handle Route Click
  const handleRouteClick = (ep) => {
    const sNodeId = entity.id;
    const fallbackNodes = ['node-component-gateway', sNodeId];
    const fallbackPairs = [['node-component-gateway', sNodeId]];

    const expl = ROUTE_EXPLANATIONS[ep.id] || {
      modules: [{ name: entity.name, desc: ep.summary || 'Обрабатывает API запрос' }],
      nodes: fallbackNodes,
      pairs: fallbackPairs,
    };

    setSelectedDetail({
      type: 'route',
      method: ep.method,
      path: ep.path,
      modules: expl.modules,
    });
    setSubView('detail');
    onIsolateRoute({ pairs: expl.pairs, nodes: expl.nodes });
  };

  // Handle Event Click
  const handleEventClick = (handler) => {
    setSelectedDetail({
      type: 'event',
      method: 'EVENT',
      path: `Событие: ${handler.name}`,
      modules: handler.modules,
    });
    setSubView('detail');

    onIsolateRoute({ pairs: handler.pairs, nodes: handler.nodes });
  };

  // Handle Celery Task Click
  const handleTaskClick = (task) => {
    setSelectedDetail({
      type: 'task',
      method: task.schedule,
      path: task.name,
      modules: task.modules,
    });
    setSubView('detail');

    onIsolateRoute({ pairs: task.pairs, nodes: task.nodes });
  };

  // Back to Main View
  const handleBackToRoutes = () => {
    setSubView('main');
    setSelectedDetail(null);
    onResetServiceIsolation();
  };

  const handlers = SERVICE_EVENT_HANDLERS[entity.entityId] || [];

  /* ── Collapsed header preview for mobile ── */
  const collapsedHeader = (
    <div className="flex items-center gap-2.5 w-full">
      <div className="w-8 h-8 rounded-full bg-emerald-50 flex items-center justify-center text-zinc-800 shrink-0">
        <NodeIcon iconKey={entity.icon} className="w-4 h-4" />
      </div>
      <div className="flex-1 min-w-0">
        <h2 className="text-[14px] font-black text-black leading-tight m-0 truncate">{entity.name}</h2>
        <span className="text-[10px] text-zinc-400 font-mono">
          {entity.type === 'service' ? 'Микросервис' : 'Инфраструктура'}
        </span>
      </div>
      <button
        type="button"
        onClick={(e) => { e.stopPropagation(); onClose(); }}
        className="w-7 h-7 flex items-center justify-center rounded-full bg-zinc-100 hover:bg-black hover:text-white transition-colors text-xs font-bold shrink-0 cursor-pointer"
        aria-label="Закрыть"
      >
        ✕
      </button>
    </div>
  );

  /* ── Content Body (shared between desktop and mobile expanded) ── */
  const contentBody = (
    <>
      {/* MAIN VIEW */}
      {subView === 'main' && (
        <div className="flex flex-col h-full overflow-hidden">
          {/* Content Area */}
          <div className="flex-1 overflow-y-auto space-y-3 py-2.5 pr-1 sheet-scroll-content">
            {/* Events Area */}
            {entity.type === 'service' && ((entity.publishes && entity.publishes.length > 0) || (entity.consumes && entity.consumes.length > 0)) && (
              <div className="space-y-1.5">
                <span className="text-[8.5px] font-mono font-black text-zinc-400 tracking-wider block uppercase">
                  СОБЫТИЯ
                </span>

                {entity.publishes && entity.publishes.length > 0 && (
                  <div>
                    <span className="text-[9px] font-black text-amber-600 tracking-wide block mb-1">
                      ОТПРАВЛЯЕТ (OUTBOX):
                    </span>
                    <div className="flex flex-wrap gap-1">
                      {entity.publishes.map((ev) => (
                        <span key={ev} className="px-2 py-0.5 rounded bg-amber-50 border border-amber-200 text-amber-700 font-mono text-[9px] font-bold">
                          {ev}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {entity.consumes && entity.consumes.length > 0 && (
                  <div className="mt-1.5">
                    <span className="text-[9px] font-black text-blue-600 tracking-wide block mb-1">
                      СЛУШАЕТ (INBOX):
                    </span>
                    <div className="flex flex-wrap gap-1">
                      {entity.consumes.map((ev) => {
                        const handler = handlers.find((h) => h.name === ev);
                        return (
                          <button
                            key={ev}
                            type="button"
                            onClick={() => handler && handleEventClick(handler)}
                            className="px-2 py-1 rounded bg-blue-50 border border-blue-200 text-blue-700 font-mono text-[9px] font-bold hover:bg-blue-100 transition-colors cursor-pointer min-h-[32px]"
                          >
                            {ev}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Celery Queues */}
            {isCelery && (
              <div className="space-y-1.5">
                <span className="text-[8.5px] font-mono font-black text-amber-600 tracking-wider block uppercase">
                  ОЧЕРЕДИ ОБСЛУЖИВАНИЯ:
                </span>
                <div className="flex flex-wrap gap-1">
                  {['inventory.maintenance', 'drops.maintenance', 'media.maintenance', 'auth.maintenance'].map((q) => (
                    <span key={q} className="px-2 py-0.5 rounded bg-zinc-100 border border-zinc-200 text-zinc-700 font-mono text-[9px] font-bold">
                      {q}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* PostgreSQL Details */}
            {entity.entityId === 'component-postgres' && (
              <div className="space-y-2">
                <span className="text-[8.5px] font-mono font-black text-blue-600 tracking-wider block uppercase">
                  РЕЛЯЦИОННЫЕ ТАБЛИЦЫ И СХЕМЫ
                </span>
                <div className="flex flex-wrap gap-1">
                  {['users', 'sessions', 'refresh_tokens', 'categories', 'brands', 'products', 'product_variants', 'stocks', 'reservations', 'orders', 'promocodes', 'payments', 'notifications', 'wishlist_items', 'drops', 'media_assets', 'outbox_events', 'processed_events'].map((tbl) => (
                    <span key={tbl} className="px-2 py-0.5 rounded bg-blue-50 border border-blue-200 text-blue-800 font-mono text-[9px] font-bold">
                      {tbl}
                    </span>
                  ))}
                </div>
                <span className="text-[8.5px] font-mono font-black text-zinc-400 tracking-wider block uppercase mt-2">
                  ПОДКЛЮЧЕННЫЕ СЕРВИСЫ
                </span>
                <div className="flex flex-wrap gap-1">
                  {['Auth', 'Catalog', 'Inventory', 'Orders', 'Payments', 'Drops', 'Media', 'Wishlist', 'Notifications'].map((s) => (
                    <span key={s} className="px-2 py-0.5 rounded bg-zinc-100 border border-zinc-200 text-zinc-700 font-mono text-[9px] font-bold">
                      {s}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Redis Details */}
            {entity.entityId === 'component-redis' && (
              <div className="space-y-2">
                <span className="text-[8.5px] font-mono font-black text-red-600 tracking-wider block uppercase">
                  КЭШИРУЕМЫЕ СТРУКТУРЫ ДАННЫХ
                </span>
                <div className="flex flex-wrap gap-1">
                  {['auth:session:*', 'auth:session-touch:*', 'auth:rate:*', 'catalog:categories:tree:v1', 'inventory:stock:*'].map((keyPattern) => (
                    <span key={keyPattern} className="px-2 py-0.5 rounded bg-red-50 border border-red-200 text-red-700 font-mono text-[9px] font-bold">
                      {keyPattern}
                    </span>
                  ))}
                </div>
                <span className="text-[8.5px] font-mono font-black text-zinc-400 tracking-wider block uppercase mt-2">
                  БАЗЫ ДАННЫХ REDIS
                </span>
                <div className="flex flex-wrap gap-1">
                  {['DB 0: Auth Sessions & Rate Limit', 'DB 1: Catalog Categories Tree', 'DB 2: Inventory Stock Cache'].map((db) => (
                    <span key={db} className="px-2 py-0.5 rounded bg-red-50 border border-red-200 text-red-700 font-mono text-[9px] font-bold">
                      {db}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* RabbitMQ Details */}
            {entity.entityId === 'component-rabbitmq' && (
              <div className="space-y-2">
                <span className="text-[8.5px] font-mono font-black text-orange-600 tracking-wider block uppercase">
                  ТОПИКИ И ЭКСЧЕНДЖИ СОБЫТИЙ
                </span>
                <div className="flex flex-wrap gap-1">
                  {['flashmarket.events (topic)', 'flashmarket.retry (direct)', 'flashmarket.dead-letter (direct)', 'inventory.events', 'orders.events', 'payments.events', 'notifications.events', 'wishlist.drop-events'].map((ex) => (
                    <span key={ex} className="px-2 py-0.5 rounded bg-amber-50 border border-amber-200 text-amber-800 font-mono text-[9px] font-bold">
                      {ex}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* S3 Details */}
            {entity.entityId === 'component-s3' && (
              <div className="space-y-2">
                <span className="text-[8.5px] font-mono font-black text-emerald-600 tracking-wider block uppercase">
                  S3 / MINIO ХРАНИЛИЩЕ
                </span>
                <div className="flex flex-wrap gap-1">
                  {['flashmarket-media (продуктовые изображения и ассеты)'].map((b) => (
                    <span key={b} className="px-2 py-0.5 rounded bg-emerald-50 border border-emerald-200 text-emerald-800 font-mono text-[9px] font-bold">
                      {b}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Gateway Details */}
            {entity.entityId === 'component-gateway' && (
              <div className="space-y-2">
                <span className="text-[8.5px] font-mono font-black text-emerald-600 tracking-wider block uppercase">
                  ФУНКЦИИ ШЛЮЗА
                </span>
                <div className="flex flex-wrap gap-1">
                  {['Reverse Proxy Routing', 'Per-IP Rate Limiting', 'Trusted Proxy (X-Forwarded-For)', 'Static SPA Delivery', 'Health Probes & Timeouts'].map((f) => (
                    <span key={f} className="px-2 py-0.5 rounded bg-green-50 border border-green-200 text-green-800 font-mono text-[9px] font-bold">
                      {f}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Routes / Celery Tasks / Event Handlers */}
            <div className="space-y-1.5">
              <span className="text-[8.5px] font-mono font-black text-zinc-400 tracking-wider block uppercase">
                {isCelery ? 'ПЕРИОДИЧЕСКИЕ ТАСКИ (CELERY BEAT)' : 'API РОУТЫ И СОБЫТИЯ'}
              </span>

              <div className="space-y-1.5">
                {/* Celery Tasks */}
                {isCelery &&
                  CELERY_TASKS.map((task) => (
                    <button
                      key={task.id}
                      type="button"
                      onClick={() => handleTaskClick(task)}
                      className="w-full flex items-center gap-2 p-2 rounded-lg bg-zinc-50 border border-zinc-200 hover:border-blue-500 hover:bg-white transition-all text-left group min-h-[44px]"
                    >
                      <strong className="px-1.5 py-0.5 rounded bg-orange-100 text-orange-700 font-mono text-[8px] font-black shrink-0">
                        {task.schedule}
                      </strong>
                      <span className="font-mono text-[10.5px] font-bold text-zinc-800 break-all flex-1">
                        {task.name}
                      </span>
                      <span className="text-zinc-400 group-hover:text-black transition-colors text-xs font-bold">→</span>
                    </button>
                  ))}

                {/* API Endpoints */}
                {entity.endpoints &&
                  entity.endpoints.map((ep) => {
                    const method = ep.method.toUpperCase();
                    let badgeBg = 'bg-blue-100 text-blue-700';
                    if (method === 'GET') badgeBg = 'bg-emerald-100 text-emerald-700';
                    if (method === 'DELETE') badgeBg = 'bg-red-100 text-red-700';
                    if (method === 'PATCH' || method === 'PUT') badgeBg = 'bg-amber-100 text-amber-700';

                    return (
                      <button
                        key={ep.id}
                        type="button"
                        onClick={() => handleRouteClick(ep)}
                        className="w-full flex items-center gap-2 p-2 rounded-lg bg-zinc-50 border border-zinc-200 hover:border-blue-500 hover:bg-white transition-all text-left group min-h-[44px]"
                      >
                        <strong className={`px-1.5 py-0.5 rounded font-mono text-[8px] font-black shrink-0 ${badgeBg}`}>
                          {method}
                        </strong>
                        <span className="font-mono text-[10.5px] font-bold text-zinc-800 break-all flex-1">
                          {ep.path}
                        </span>
                        <span className="text-zinc-400 group-hover:text-black transition-colors text-xs font-bold">→</span>
                      </button>
                    );
                  })}

                {/* Async Event Handlers */}
                {handlers.map((h) => (
                  <button
                    key={h.id}
                    type="button"
                    onClick={() => handleEventClick(h)}
                    className="w-full flex items-center gap-2 p-2 rounded-lg bg-zinc-50 border border-zinc-200 hover:border-blue-500 hover:bg-white transition-all text-left group min-h-[44px]"
                  >
                    <strong className="px-1.5 py-0.5 rounded bg-orange-100 text-orange-700 font-mono text-[8px] font-black shrink-0">
                      EVENT
                    </strong>
                    <span className="font-mono text-[10.5px] font-bold text-zinc-800 break-all flex-1">
                      Событие: {h.name}
                    </span>
                    <span className="text-zinc-400 group-hover:text-black transition-colors text-xs font-bold">→</span>
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* DETAIL VIEW */}
      {subView === 'detail' && selectedDetail && (
        <div className="flex flex-col h-full overflow-hidden">
          {/* Header with Back Button */}
          <div className="flex items-center pb-2.5 border-b border-zinc-100 shrink-0">
            <div className="flex items-center gap-2 min-w-0 w-full overflow-hidden">
              <button
                type="button"
                onClick={handleBackToRoutes}
                className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-zinc-100 hover:bg-black hover:text-white font-sans text-[11px] font-bold tracking-wide transition-colors cursor-pointer text-zinc-800 shrink-0 border border-zinc-200/60 min-h-[36px]"
              >
                <span>←</span>
                <span>Назад</span>
              </button>

              <div className="inline-flex items-center gap-1.5 px-2 py-1 rounded-lg bg-zinc-100 border border-zinc-200/80 text-zinc-800 font-mono text-[10px] font-bold min-w-0 flex-1 truncate">
                <strong className={`px-1 py-0.5 rounded font-mono text-[8px] font-black shrink-0 ${
                  selectedDetail.method === 'GET' ? 'bg-emerald-100 text-emerald-800' :
                  selectedDetail.method === 'POST' ? 'bg-blue-100 text-blue-800' :
                  selectedDetail.method === 'DELETE' ? 'bg-red-100 text-red-800' :
                  selectedDetail.method === 'PATCH' || selectedDetail.method === 'PUT' ? 'bg-amber-100 text-amber-800' :
                  'bg-orange-100 text-orange-800'
                }`}>
                  {selectedDetail.method}
                </strong>
                <span className="truncate text-zinc-900 font-bold">
                  {selectedDetail.path.replace('Событие: ', '')}
                </span>
              </div>
            </div>
          </div>

          {/* Detail Content */}
          <div className="flex-1 overflow-y-auto space-y-2 py-2 pr-1 sheet-scroll-content">
            <div className="space-y-2">
              {selectedDetail.modules.map((m, idx) => {
                const iconKey = getModuleIconKey(m.name);
                return (
                  <div
                    key={idx}
                    className="flex items-start gap-2.5 p-2.5 bg-white border border-zinc-200/90 rounded-xl hover:border-zinc-300 transition-colors shadow-[0_1px_2px_rgba(0,0,0,0.03)]"
                  >
                    <div className="w-7 h-7 rounded-lg bg-zinc-50 border border-zinc-100 flex items-center justify-center shrink-0 mt-0.5">
                      <NodeIcon iconKey={iconKey} className="w-3.5 h-3.5" />
                    </div>
                    <div className="flex-1 min-w-0 space-y-0.5">
                      <span className="font-sans text-[11px] font-black text-black block leading-tight">{m.name}</span>
                      <span className="font-sans text-[10.5px] text-zinc-600 leading-snug block">{m.desc}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </>
  );

  /* ═══════════════════ MOBILE: Bottom Sheet ═══════════════════ */
  if (isMobile) {
    const sheetPixelHeight = typeof sheetHeight === 'number' && sheetHeight <= 1
      ? Math.round(window.innerHeight * sheetHeight)
      : sheetHeight;
    const isCollapsed = sheetPixelHeight <= SHEET_COLLAPSED + 20;

    return (
      <aside
        ref={sheetRef}
        className="fixed z-50 bottom-0 left-0 right-0 bg-white border-t border-zinc-200 rounded-t-2xl shadow-2xl flex flex-col text-left no-pan no-wheel"
        style={{
          height: `${sheetPixelHeight}px`,
          maxHeight: '92vh',
          transition: dragRef.current.isDragging ? 'none' : 'height 0.3s cubic-bezier(0.16, 1, 0.3, 1)',
          boxSizing: 'border-box',
          paddingBottom: 'env(safe-area-inset-bottom, 0px)',
        }}
        onTouchStart={onSheetTouchStart}
        onTouchMove={onSheetTouchMove}
        onTouchEnd={onSheetTouchEnd}
        onMouseDown={onSheetMouseDown}
        role="dialog"
        aria-label={`Детали: ${entity.name}`}
      >
        {/* Drag Handle */}
        <div className="sheet-drag-handle flex flex-col items-center pt-2 pb-1.5 shrink-0 cursor-grab active:cursor-grabbing">
          <div className="w-9 h-1 bg-zinc-300 rounded-full" />
        </div>

        {/* Header */}
        <div className="px-3.5 pb-2 border-b border-zinc-100 shrink-0">
          {collapsedHeader}
        </div>

        {/* Expandable Content */}
        {!isCollapsed && (
          <div className="flex-1 overflow-hidden px-3.5 pt-1">
            {contentBody}
          </div>
        )}
      </aside>
    );
  }

  /* ═══════════════════ DESKTOP: Side Panel ═══════════════════ */
  return (
    <aside
      className="absolute z-30 top-3 bottom-3 right-3 w-[380px] max-w-[calc(100vw-40px)] bg-white border border-zinc-200 rounded-2xl shadow-2xl flex flex-col p-4 text-left transition-all duration-300 no-pan no-wheel"
      style={{ boxSizing: 'border-box' }}
      role="dialog"
      aria-label={`Детали: ${entity.name}`}
    >
      {/* Header */}
      <div className="flex items-center justify-between pb-2.5 border-b border-zinc-100 shrink-0">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-full bg-emerald-50 flex items-center justify-center text-zinc-800 shrink-0">
            <NodeIcon iconKey={entity.icon} className="w-4 h-4" />
          </div>
          <div>
            <h2 className="text-[15px] font-black text-black leading-tight m-0">{entity.name}</h2>
            <span className="text-[10px] text-zinc-400 font-mono">
              {entity.type === 'service' ? 'Микросервис' : 'Инфраструктура'}
            </span>
          </div>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="w-7 h-7 flex items-center justify-center rounded-full bg-zinc-100 hover:bg-black hover:text-white transition-colors text-xs font-bold cursor-pointer"
          aria-label="Закрыть"
        >
          ✕
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden pt-1">
        {contentBody}
      </div>
    </aside>
  );
};
