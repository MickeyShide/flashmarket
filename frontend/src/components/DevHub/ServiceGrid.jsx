import React from 'react';

const STATUS_LABELS = { operational: 'Работает', unavailable: 'Недоступен', unknown: 'Проверка' };

export const ServiceGrid = ({ services, statuses, onSelectService, selectedServiceId }) => (
  <section className="bg-[#121212] border-b border-[#27272A] py-8 md:py-12">
    <div className="max-w-[1280px] mx-auto px-3.5 md:px-6">
      
      {/* Section Header matching store style */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-3 mb-6 md:mb-8">
        <div>
          <div className="font-mono text-[9.5px] md:text-[10.5px] tracking-[1.5px] uppercase font-bold text-accent-lime mb-1">
            СЕРВИСЫ ПЛАТФОРМЫ
          </div>
          <h2 className="font-sans font-black text-lg md:text-2xl tracking-[1px] md:tracking-[2.5px] uppercase text-white">
            МИКРОСЕРВИСЫ API
          </h2>
        </div>
        <p className="text-xs text-zinc-400 font-sans max-w-md">
          Официальные контракты микросервисов FlashMarket. Выберите сервис для фильтрации API-эндпоинтов.
        </p>
      </div>

      {/* Grid matching store product cards spacing */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 md:gap-4">
        {services.map((service, idx) => {
          const status = statuses[service.id] || 'unknown';
          const isSelected = selectedServiceId === service.id;

          return (
            <button
              key={service.id}
              onClick={() => onSelectService(service.id)}
              className={`group p-5 rounded-md border text-left transition-all cursor-pointer focus:outline-none ${
                isSelected
                  ? 'bg-[#27272A] border-accent-lime shadow-[0_0_15px_rgba(191,245,50,0.15)] ring-1 ring-accent-lime'
                  : 'bg-[#18181B] border-[#27272A] hover:border-[#3F3F46] hover:bg-[#202023]'
              }`}
            >
              <div className="flex items-center justify-between gap-2 font-mono text-[10px] tracking-wider uppercase mb-3">
                <span className="text-zinc-400 font-bold">
                  {String(idx + 1).padStart(2, '0')} / {service.id}
                </span>
                <span className={`font-bold flex items-center gap-1.5 ${
                  status === 'operational' ? 'text-accent-lime' : status === 'unavailable' ? 'text-red-400' : 'text-amber-400'
                }`}>
                  <span className="w-1.5 h-1.5 rounded-full bg-current"></span>
                  {STATUS_LABELS[status]}
                </span>
              </div>

              <div className="flex items-center justify-between gap-3 mb-2">
                <h3 className="font-sans font-black text-base md:text-lg tracking-[0.5px] uppercase text-white group-hover:text-accent-lime transition-colors">
                  {service.name}
                </h3>
                <span className="font-mono text-[11px] font-black px-2 py-0.5 rounded bg-[#27272A] text-zinc-300 border border-[#3F3F46]">
                  {service.operationCount} эндпоинтов
                </span>
              </div>

              <div className="border-t border-[#27272A] pt-3 mt-3 flex items-center justify-between font-mono text-[10.5px] text-zinc-400 truncate">
                <span className="truncate">{service.prefixes[0]}</span>
                <span className="text-accent-lime opacity-0 group-hover:opacity-100 transition-opacity font-bold ml-2">
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
