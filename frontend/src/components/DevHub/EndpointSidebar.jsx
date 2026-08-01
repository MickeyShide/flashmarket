import React from 'react';

const METHOD_STYLES = {
  GET: 'text-emerald-400',
  POST: 'text-blue-400',
  PUT: 'text-amber-300',
  PATCH: 'text-amber-300',
  DELETE: 'text-rose-400',
};

export const EndpointSidebar = ({
  endpoints,
  services,
  selectedEndpointId,
  onSelectEndpoint,
  searchQuery,
  onSearchChange,
  accessFilter,
  onAccessFilterChange,
  serviceFilter,
  onServiceFilterChange,
}) => (
  <aside className="flex h-[720px] flex-col border-b border-zinc-800 bg-black font-mono lg:border-b-0 lg:border-r">
    <div className="space-y-3 border-b border-zinc-800 p-4">
      <label className="block">
        <span className="sr-only">Search API operations</span>
        <input value={searchQuery} onChange={(event) => onSearchChange(event.target.value)} placeholder="Search path or operation" className="w-full border border-zinc-800 bg-zinc-950 px-3 py-2.5 text-xs text-white outline-none placeholder:text-zinc-600 focus:border-[#BFF532]" />
      </label>
      <select value={serviceFilter || ''} onChange={(event) => onServiceFilterChange(event.target.value || null)} className="w-full border border-zinc-800 bg-zinc-950 px-3 py-2 text-[10px] uppercase tracking-wider text-zinc-300 outline-none focus:border-[#BFF532]">
        <option value="">All services</option>
        {services.map((service) => <option key={service.id} value={service.id}>{service.name} ({service.operationCount})</option>)}
      </select>
      <div className="grid grid-cols-4 gap-px bg-zinc-800">
        {['all', 'anonymous', 'authenticated', 'admin'].map((filter) => (
          <button key={filter} onClick={() => onAccessFilterChange(filter)} title={filter} className={`truncate bg-zinc-950 px-1 py-2 text-[8px] uppercase ${accessFilter === filter ? 'text-[#BFF532]' : 'text-zinc-500'}`}>
            {filter === 'authenticated' ? 'auth' : filter === 'anonymous' ? 'public' : filter}
          </button>
        ))}
      </div>
    </div>
    <div className="flex-1 overflow-y-auto [content-visibility:auto]">
      {endpoints.length === 0 ? <p className="p-6 text-xs text-zinc-500">No operations match these filters.</p> : endpoints.map((endpoint) => (
        <button key={endpoint.id} onClick={() => onSelectEndpoint(endpoint.id)} className={`block w-full border-b border-zinc-900 px-4 py-3 text-left hover:bg-zinc-900 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-[#BFF532] ${selectedEndpointId === endpoint.id ? 'bg-zinc-900' : ''}`}>
          <div className="mb-1.5 flex items-center justify-between gap-2 text-[9px] uppercase tracking-wider">
            <span className={`font-bold ${METHOD_STYLES[endpoint.method] || 'text-zinc-300'}`}>{endpoint.method}</span>
            <span className={endpoint.access === 'admin' ? 'text-rose-400' : 'text-zinc-600'}>{endpoint.access === 'authenticated' ? 'auth' : endpoint.access}</span>
          </div>
          <div className="truncate text-[11px] font-semibold text-zinc-200">{endpoint.path}</div>
          <div className="mt-1 truncate text-[10px] text-zinc-600">{endpoint.summary}</div>
        </button>
      ))}
    </div>
  </aside>
);
