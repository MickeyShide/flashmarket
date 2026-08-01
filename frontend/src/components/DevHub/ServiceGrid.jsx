import React from 'react';

const STATUS_LABELS = { operational: 'Operational', unavailable: 'Unavailable', unknown: 'Unknown' };

export const ServiceGrid = ({ services, statuses, onSelectService, selectedServiceId }) => (
  <section className="border-b border-zinc-800 bg-[#0E0E0F] py-16">
    <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
      <div className="mb-9 flex flex-col justify-between gap-4 md:flex-row md:items-end">
        <div><div className="font-mono text-[10px] font-bold uppercase tracking-[0.22em] text-[#BFF532]">Service index</div><h2 className="mt-2 text-3xl font-black uppercase tracking-tight text-white sm:text-4xl">One gateway. Nine boundaries.</h2></div>
        <p className="max-w-md text-sm leading-6 text-zinc-400">Counts and prefixes come from the generated FastAPI contracts and current gateway configuration.</p>
      </div>
      <div className="grid gap-px border border-zinc-800 bg-zinc-800 md:grid-cols-2 lg:grid-cols-3">
        {services.map((service) => {
          const status = statuses[service.id] || 'unknown';
          const selected = selectedServiceId === service.id;
          return (
            <button key={service.id} onClick={() => onSelectService(service.id)} className={`group min-h-44 bg-zinc-950 p-6 text-left transition-colors hover:bg-zinc-900 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-[#BFF532] ${selected ? 'bg-zinc-900' : ''}`}>
              <div className="flex items-start justify-between gap-3 font-mono text-[9px] uppercase tracking-widest">
                <span className="text-zinc-500">{String(services.indexOf(service) + 1).padStart(2, '0')} / {service.id}</span>
                <span className={status === 'operational' ? 'text-[#BFF532]' : status === 'unavailable' ? 'text-rose-400' : 'text-amber-300'}>● {STATUS_LABELS[status]}</span>
              </div>
              <div className="mt-7 flex items-end justify-between gap-4">
                <h3 className="text-2xl font-black uppercase text-white group-hover:text-[#BFF532]">{service.name}</h3>
                <span className="font-mono text-xl font-bold text-zinc-600">{service.operationCount}</span>
              </div>
              <div className="mt-5 truncate border-t border-zinc-800 pt-3 font-mono text-[10px] text-zinc-500">{service.prefixes[0]}</div>
            </button>
          );
        })}
      </div>
    </div>
  </section>
);
