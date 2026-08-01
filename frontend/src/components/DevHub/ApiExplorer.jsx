import React, { useDeferredValue, useEffect, useMemo, useState } from 'react';
import { EndpointDetails } from './EndpointDetails';
import { EndpointSidebar } from './EndpointSidebar';
import { RequestPlayground } from './RequestPlayground';

export const ApiExplorer = ({
  document,
  endpoints,
  services,
  user,
  accessToken,
  serviceFilter,
  onServiceFilterChange,
  selectedEndpointId,
  onSelectedEndpointIdChange,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const deferredSearch = useDeferredValue(searchQuery.trim().toLowerCase());
  const [accessFilter, setAccessFilter] = useState('all');
  const [mobileTab, setMobileTab] = useState('details');

  const filteredEndpoints = useMemo(
    () => endpoints.filter((endpoint) => {
      if (serviceFilter && endpoint.serviceId !== serviceFilter) return false;
      if (accessFilter !== 'all' && endpoint.access !== accessFilter) return false;
      if (!deferredSearch) return true;
      return `${endpoint.path} ${endpoint.summary} ${endpoint.serviceId} ${endpoint.method}`.toLowerCase().includes(deferredSearch);
    }),
    [endpoints, serviceFilter, accessFilter, deferredSearch]
  );

  const selectedEndpoint = useMemo(
    () => filteredEndpoints.find((endpoint) => endpoint.id === selectedEndpointId) || filteredEndpoints[0] || null,
    [filteredEndpoints, selectedEndpointId]
  );

  useEffect(() => {
    if (selectedEndpoint && selectedEndpoint.id !== selectedEndpointId) {
      onSelectedEndpointIdChange(selectedEndpoint.id);
    }
  }, [selectedEndpoint, selectedEndpointId, onSelectedEndpointIdChange]);

  return (
    <section id="api-explorer" className="scroll-mt-16 border-b border-zinc-800 bg-[#0B0B0C] py-16">
      <div className="mx-auto max-w-[1500px] px-4 sm:px-6 lg:px-8">
        <div className="mb-7 flex flex-col justify-between gap-4 md:flex-row md:items-end">
          <div><div className="font-mono text-[10px] font-bold uppercase tracking-[0.22em] text-[#BFF532]">Live contract / real requests</div><h2 className="mt-2 text-3xl font-black uppercase text-white sm:text-4xl">API Explorer</h2></div>
          <div className="font-mono text-[10px] uppercase tracking-widest text-zinc-500">{filteredEndpoints.length} of {endpoints.length} operations</div>
        </div>

        <div className="mb-3 grid grid-cols-3 gap-px border border-zinc-800 bg-zinc-800 font-mono text-[10px] uppercase lg:hidden">
          {['list', 'details', 'playground'].map((tab) => (
            <button key={tab} onClick={() => setMobileTab(tab)} className={`bg-zinc-950 px-2 py-3 ${mobileTab === tab ? 'text-[#BFF532]' : 'text-zinc-500'}`}>{tab}</button>
          ))}
        </div>

        <div className="grid min-h-[720px] overflow-hidden border border-zinc-800 bg-zinc-950 lg:grid-cols-[300px_minmax(360px,1fr)_390px]">
          <div className={`${mobileTab === 'list' ? 'block' : 'hidden'} lg:block`}>
            <EndpointSidebar
              endpoints={filteredEndpoints}
              services={services}
              selectedEndpointId={selectedEndpoint?.id}
              onSelectEndpoint={(id) => { onSelectedEndpointIdChange(id); setMobileTab('details'); }}
              searchQuery={searchQuery}
              onSearchChange={setSearchQuery}
              accessFilter={accessFilter}
              onAccessFilterChange={setAccessFilter}
              serviceFilter={serviceFilter}
              onServiceFilterChange={onServiceFilterChange}
            />
          </div>
          <div className={`${mobileTab === 'details' ? 'block' : 'hidden'} min-w-0 lg:block`}>
            <EndpointDetails endpoint={selectedEndpoint} document={document} />
          </div>
          <div className={`${mobileTab === 'playground' ? 'block' : 'hidden'} lg:block`}>
            <RequestPlayground endpoint={selectedEndpoint} user={user} accessToken={accessToken} />
          </div>
        </div>
      </div>
    </section>
  );
};
