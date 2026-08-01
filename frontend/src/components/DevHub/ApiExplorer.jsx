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
    <section id="api-explorer" className="scroll-mt-16 bg-[#121212] border-b border-[#27272A] py-8 md:py-12">
      <div className="max-w-[1280px] mx-auto px-3.5 md:px-6">
        
        {/* Section Header matching FlashMarket store design */}
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-3 mb-6">
          <div>
            <div className="font-mono text-[9.5px] md:text-[10.5px] tracking-[1.5px] uppercase font-bold text-accent-lime mb-1">
              ИНТЕРАКТИВНЫЙ EXPLORER
            </div>
            <h2 className="font-sans font-black text-lg md:text-2xl tracking-[1px] md:tracking-[2.5px] uppercase text-white">
              API EXPLORER
            </h2>
          </div>
          <div className="font-mono text-[10.5px] uppercase tracking-wider text-zinc-400 font-extrabold">
            {filteredEndpoints.length} из {endpoints.length} операций
          </div>
        </div>

        {/* Mobile View Switcher Tabs */}
        <div className="grid grid-cols-3 gap-1 bg-[#18181B] border border-[#27272A] p-1 rounded font-mono text-[10px] uppercase font-bold lg:hidden mb-3">
          {['list', 'details', 'playground'].map((tab) => (
            <button
              key={tab}
              onClick={() => setMobileTab(tab)}
              className={`py-2 rounded transition-colors text-center ${
                mobileTab === tab ? 'bg-accent-lime text-black' : 'text-zinc-400 hover:text-white'
              }`}
            >
              {tab === 'list' ? 'Список' : tab === 'details' ? 'Схема' : 'Консоль'}
            </button>
          ))}
        </div>

        {/* Main Explorer Unified Frame */}
        <div className="grid min-h-[700px] overflow-hidden border border-[#27272A] bg-[#141414] rounded-md shadow-2xl lg:grid-cols-[300px_minmax(340px,1fr)_380px]">
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
