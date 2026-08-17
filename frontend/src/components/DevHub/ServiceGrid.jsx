import React from 'react';

const STATUS_CONFIG = {
  operational: { label: 'Работает', color: 'text-[#2E7D32]', bg: 'bg-[#E8F5E9]', border: 'border-[#C8E6C9]' },
  unavailable: { label: 'Недоступен', color: 'text-accent-red', bg: 'bg-red-50', border: 'border-red-200' },
  unknown: { label: 'Проверка', color: 'text-amber-700', bg: 'bg-amber-50', border: 'border-amber-200' },
};

export const ServiceGrid = ({ services, statuses, onSelectService, selectedServiceId }) => (
  <section className="bg-white border-b border-border-color py-8 md:py-12">
    <div className="max-w-[1280px] mx-auto px-3.5 md:px-6">
      
      {/* Section Header matching store style */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-3 mb-6 md:mb-8">
        <div>
          <div className="font-mono text-[9.5px] md:text-[10.5px] tracking-[1.5px] uppercase font-bold text-text-muted mb-1">
            СЕРВИСЫ ПЛАТФОРМЫ
          </div>
          <h2 className="font-sans font-black text-lg md:text-2xl tracking-[1px] md:tracking-[2.5px] uppercase text-black">
            МИКРОСЕРВИСЫ API
          </h2>
        </div>
        <p className="text-xs text-text-muted font-sans max-w-md">
          Официальные контракты 9 микросервисов FlashMarket. Выберите сервис для мгновенной фильтрации эндпоинтов в Explorer.
        </p>
      </div>

      {/* Grid matching store product cards spacing */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 md:gap-4">
        {services.map((service, idx) => {
          const statusKey = statuses[service.id] || 'unknown';
          const status = STATUS_CONFIG[statusKey] || STATUS_CONFIG.unknown;
          const isSelected = selectedServiceId === service.id;

          return (
            <button
              key={service.id}
              onClick={() => onSelectService(service.id)}
              className={`group p-5 rounded-sm border text-left transition-all cursor-pointer focus:outline-none ${
                isSelected
                  ? 'bg-[#F9FAFB] border-black ring-2 ring-black shadow-md'
                  : 'bg-white border-border-color hover:border-black hover:shadow-sm'
              }`}
            >
              <div className="flex items-center justify-between gap-2 font-mono text-[10px] tracking-wider uppercase mb-3">
                <span className="text-text-muted font-bold">
                  {String(idx + 1).padStart(2, '0')} / {service.id}
                </span>
                <span className={`font-mono text-[9px] font-extrabold px-2 py-0.5 rounded-sm border flex items-center gap-1.5 ${status.bg} ${status.color} ${status.border}`}>
                  <span className="w-1.5 h-1.5 rounded-full bg-current"></span>
                  {status.label}
                </span>
              </div>

              <div className="flex items-center justify-between gap-3 mb-2">
                <h3 className="font-sans font-black text-base md:text-lg tracking-[0.5px] uppercase text-black group-hover:text-black transition-colors">
                  {service.name}
                </h3>
                <span className="font-mono text-[10.5px] font-black px-2 py-0.5 rounded-sm bg-[#F5F5F5] text-black border border-border-color">
                  {service.operationCount} эндпоинтов
                </span>
              </div>

              <div className="border-t border-border-color pt-3 mt-3 flex items-center justify-between font-mono text-[10.5px] text-text-muted truncate">
                <span className="truncate">{service.prefixes[0]}</span>
                <span className="text-black font-black opacity-0 group-hover:opacity-100 transition-opacity ml-2">
                  ВЫБРАТЬ →
                </span>
              </div>
            </button>
          );
        })}
      </div>

    </div>
  </section>
);

