import React, { useEffect, useMemo, useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { ApiExplorer } from './ApiExplorer';
import { DevHubFooter } from './DevHubFooter';
import { DevHubHeader } from './DevHubHeader';
import { describeSystemStatus } from './openapi';
import { ServiceGrid } from './ServiceGrid';
import { useDeveloperHubData } from './useDeveloperHubData';

function LoadingSurface() {
  return (
    <main className="max-w-[1280px] mx-auto px-4 py-16 sm:px-6" aria-busy="true">
      <div className="mb-4 h-4 w-40 animate-pulse bg-zinc-200" />
      <div className="mb-8 h-10 max-w-xl animate-pulse bg-zinc-200" />
      <div className="grid gap-4 md:grid-cols-3">
        {[0, 1, 2, 3, 4, 5].map((item) => (
          <div key={item} className="h-40 animate-pulse bg-white border border-border-color p-6 rounded-sm">
            <div className="h-4 w-24 bg-zinc-200" />
            <div className="mt-6 h-6 w-36 bg-zinc-200" />
          </div>
        ))}
      </div>
    </main>
  );
}

function ContractError({ message, onBackToStore }) {
  return (
    <main className="max-w-[1280px] mx-auto flex min-h-[60vh] items-center px-4 py-16 sm:px-6">
      <div className="w-full border border-red-200 bg-white p-8 sm:p-12 shadow-sm rounded-sm">
        <div className="font-mono text-xs font-bold uppercase tracking-[0.2em] text-accent-red">Контракт недоступен</div>
        <h1 className="mt-3 text-2xl md:text-3xl font-black uppercase text-black font-sans">API спецификация недоступна</h1>
        <p className="mt-3 max-w-xl text-sm leading-6 text-text-muted font-sans">{message}</p>
        <button onClick={onBackToStore} className="mt-6 bg-black text-white hover:bg-[#BFF532] hover:text-black px-6 py-3 font-mono text-xs font-black uppercase tracking-wider rounded-sm transition-colors cursor-pointer">
          Вернуться в магазин
        </button>
      </div>
    </main>
  );
}

export const DevHub = ({ onBackToStore }) => {
  const { user, accessToken } = useAuth();
  const { loading, data, error, statuses } = useDeveloperHubData();
  const [selectedServiceId, setSelectedServiceId] = useState(null);
  const [selectedEndpointId, setSelectedEndpointId] = useState(null);

  const systemStatus = useMemo(
    () => describeSystemStatus(statuses, data?.metadata.serviceCount || 0),
    [statuses, data?.metadata.serviceCount]
  );

  useEffect(() => {
    const originalTitle = document.title;
    document.title = 'FlashMarket Developer Hub — Public API';
    window.scrollTo({ top: 0 });
    return () => {
      document.title = originalTitle;
    };
  }, []);

  const scrollTo = (sectionId) => {
    document.getElementById(sectionId)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  const handleOpenArchitecture = () => {
    window.open('/docs/architecture/', '_blank', 'noopener,noreferrer');
  };

  return (
    <div className="min-h-screen bg-bg-primary text-text-main font-sans selection:bg-[#BFF532] selection:text-black">
      <DevHubHeader
        user={user}
        accessToken={accessToken}
        systemStatus={systemStatus}
        onBackToStore={onBackToStore}
        onArchitectureClick={handleOpenArchitecture}
      />

      {/* Top Architecture Promo Banner */}
      <section className="bg-[#F9FAFB] border-b border-border-color py-6 md:py-8">
        <div className="max-w-[1280px] mx-auto px-3.5 md:px-6">
          <div className="bg-black text-white p-5 md:p-7 rounded-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-5 relative overflow-hidden border border-black">
            <div className="space-y-2 z-10 max-w-2xl">
              <div className="flex items-center gap-2 font-mono text-[9.5px] md:text-[10.5px] tracking-[1.5px] uppercase font-bold text-[#BFF532]">
                <span className="w-2 h-2 rounded-full bg-[#BFF532] animate-pulse"></span>
                СИСТЕМНАЯ АРХИТЕКТУРА FLASHMARKET
              </div>
              <h2 className="font-sans font-black text-base md:text-xl tracking-[0.5px] md:tracking-[1px] uppercase leading-tight">
                9 МИКРОСЕРВИСОВ · OUTBOX ПАТТЕРН · РАСПРЕДЕЛЕННАЯ НАДЕЖНОСТЬ
              </h2>
              <p className="text-xs text-zinc-300 font-sans leading-relaxed">
                Интерактивный эксплорер архитектуры: системная карта топологии, бизнес-флоу, лаборатории Outbox и Concurrency, RabbitMQ брокер и анализ PostgreSQL.
              </p>
            </div>
            <div className="z-10 flex flex-wrap gap-2 w-full md:w-auto">
              <button
                onClick={handleOpenArchitecture}
                className="w-full md:w-auto text-center bg-[#BFF532] text-black hover:bg-white px-5 py-3 text-[10.5px] font-mono font-black uppercase tracking-wider rounded-sm transition-all shadow-md flex items-center justify-center gap-2 cursor-pointer"
                title="Перейти к интерактивной карте архитектуры"
              >
                <span>ОТКРЫТЬ АРХИТЕКТУРУ</span>
                <span>↗</span>
              </button>
            </div>
          </div>
        </div>
      </section>

      {loading ? <LoadingSurface /> : null}
      {!loading && error ? <ContractError message={error} onBackToStore={onBackToStore} /> : null}
      {!loading && data ? (
        <>
          <ServiceGrid
            services={data.metadata.services}
            statuses={statuses}
            selectedServiceId={selectedServiceId}
            onSelectService={(serviceId) => {
              setSelectedServiceId(serviceId === selectedServiceId ? null : serviceId);
              scrollTo('api-explorer');
            }}
          />
          <ApiExplorer
            document={data.openapi}
            endpoints={data.endpoints}
            services={data.metadata.services}
            user={user}
            accessToken={accessToken}
            serviceFilter={selectedServiceId}
            onServiceFilterChange={setSelectedServiceId}
            selectedEndpointId={selectedEndpointId}
            onSelectedEndpointIdChange={setSelectedEndpointId}
          />
          <DevHubFooter
            onBackToTop={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
            onBackToStore={onBackToStore}
            onOpenArchitecture={handleOpenArchitecture}
          />
        </>
      ) : null}
    </div>
  );
};

export default DevHub;

