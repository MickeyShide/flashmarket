import React, { useEffect, useMemo, useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { ApiExplorer } from './ApiExplorer';
import { ArchitectureOverview } from './ArchitectureOverview';
import { DemoFlows } from './DemoFlows';
import { DevHubFooter } from './DevHubFooter';
import { DevHubHeader } from './DevHubHeader';
import { DevHubHero } from './DevHubHero';
import { describeSystemStatus } from './openapi';
import { ServiceGrid } from './ServiceGrid';
import { useDeveloperHubData } from './useDeveloperHubData';

function LoadingSurface() {
  return (
    <main className="mx-auto max-w-7xl px-4 py-24 sm:px-6 lg:px-8" aria-busy="true">
      <div className="mb-5 h-3 w-36 animate-pulse bg-[#BFF532]/50" />
      <div className="mb-10 h-14 max-w-3xl animate-pulse bg-zinc-800" />
      <div className="grid gap-px border border-zinc-800 bg-zinc-800 md:grid-cols-3">
        {[0, 1, 2, 3, 4, 5].map((item) => (
          <div key={item} className="h-40 animate-pulse bg-zinc-950 p-6">
            <div className="h-4 w-20 bg-zinc-800" />
            <div className="mt-8 h-7 w-36 bg-zinc-800" />
          </div>
        ))}
      </div>
    </main>
  );
}

function ContractError({ message, onBackToStore }) {
  return (
    <main className="mx-auto flex min-h-[70vh] max-w-3xl items-center px-4 py-24 sm:px-6">
      <div className="w-full border border-rose-500/30 bg-zinc-950 p-8 sm:p-12">
        <div className="font-mono text-xs font-bold uppercase tracking-[0.2em] text-rose-400">Contract unavailable</div>
        <h1 className="mt-4 text-3xl font-black uppercase text-white">API reference unavailable</h1>
        <p className="mt-4 max-w-xl text-sm leading-6 text-zinc-400">{message}</p>
        <button onClick={onBackToStore} className="mt-8 bg-[#BFF532] px-5 py-3 font-mono text-xs font-bold uppercase text-black">
          Back to store
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

  const selectEndpoint = (endpoint) => {
    setSelectedServiceId(endpoint.serviceId);
    setSelectedEndpointId(endpoint.id);
    scrollTo('api-explorer');
  };

  return (
    <div className="min-h-screen bg-[#0B0B0C] text-zinc-100 selection:bg-[#BFF532] selection:text-black">
      <DevHubHeader user={user} accessToken={accessToken} systemStatus={systemStatus} onBackToStore={onBackToStore} />
      {loading ? <LoadingSurface /> : null}
      {!loading && error ? <ContractError message={error} onBackToStore={onBackToStore} /> : null}
      {!loading && data ? (
        <>
          <DevHubHero
            metadata={data.metadata}
            endpoints={data.endpoints}
            onExploreClick={() => scrollTo('api-explorer')}
            onArchitectureClick={() => scrollTo('architecture-overview')}
          />
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
          <ArchitectureOverview services={data.metadata.services} />
          <DemoFlows endpoints={data.endpoints} onSelectEndpoint={selectEndpoint} />
          <DevHubFooter onBackToTop={() => window.scrollTo({ top: 0, behavior: 'smooth' })} onBackToStore={onBackToStore} />
        </>
      ) : null}
    </div>
  );
};

export default DevHub;
