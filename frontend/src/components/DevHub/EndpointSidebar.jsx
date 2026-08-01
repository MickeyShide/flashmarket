import React from 'react';

const METHOD_STYLES = {
  GET: 'text-emerald-400',
  POST: 'text-blue-400',
  PUT: 'text-amber-400',
  PATCH: 'text-amber-400',
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
  <aside className="flex h-[700px] flex-col border-b border-[#27272A] bg-[#141414] font-mono lg:border-b-0 lg:border-r">
    {/* Search & Filters Header */}
    <div className="space-y-2.5 border-b border-[#27272A] p-3.5">
      {/* Search Input */}
      <div className="relative">
        <input
          value={searchQuery}
          onChange={(event) => onSearchChange(event.target.value)}
          placeholder="Поиск по маршруту или описанию..."
          className="w-full border border-[#333333] bg-[#1A1A1A] px-3 py-2 text-[11px] text-white outline-none placeholder:text-zinc-500 focus:border-accent-lime rounded-sm"
        />
        {searchQuery && (
          <button
            onClick={() => onSearchChange('')}
            className="absolute right-2.5 top-2 text-zinc-400 hover:text-white text-xs font-bold"
          >
            ✕
          </button>
        )}
      </div>

      {/* Service Dropdown Select */}
      <select
        value={serviceFilter || ''}
        onChange={(event) => onServiceFilterChange(event.target.value || null)}
        className="w-full border border-[#333333] bg-[#1A1A1A] px-3 py-1.5 text-[10px] uppercase tracking-wider text-zinc-200 outline-none focus:border-accent-lime rounded-sm cursor-pointer"
      >
        <option value="">Все сервисы</option>
        {services.map((service) => (
          <option key={service.id} value={service.id}>
            {service.name} ({service.operationCount})
          </option>
        ))}
      </select>

      {/* Access Category Filter Chips */}
      <div className="grid grid-cols-4 gap-1 p-1 bg-[#1A1A1A] border border-[#27272A] rounded-sm">
        {['all', 'anonymous', 'authenticated', 'admin'].map((filter) => {
          const isActive = accessFilter === filter;
          return (
            <button
              key={filter}
              onClick={() => onAccessFilterChange(filter)}
              title={filter}
              className={`py-1 text-[8.5px] uppercase font-black tracking-wider rounded-sm transition-colors text-center truncate ${
                isActive ? 'bg-accent-lime text-black' : 'text-zinc-400 hover:text-white hover:bg-[#27272A]'
              }`}
            >
              {filter === 'authenticated' ? 'auth' : filter === 'anonymous' ? 'public' : filter}
            </button>
          );
        })}
      </div>
    </div>

    {/* Endpoint List */}
    <div className="flex-1 overflow-y-auto divide-y divide-[#202023]">
      {endpoints.length === 0 ? (
        <p className="p-6 text-xs text-zinc-500 text-center font-sans">
          Операции по заданным фильтрам не найдены.
        </p>
      ) : (
        endpoints.map((endpoint) => {
          const isSelected = selectedEndpointId === endpoint.id;
          return (
            <button
              key={endpoint.id}
              onClick={() => onSelectEndpoint(endpoint.id)}
              className={`block w-full px-3.5 py-3 text-left transition-colors focus:outline-none ${
                isSelected
                  ? 'bg-[#27272A] border-l-2 border-accent-lime text-white'
                  : 'hover:bg-[#1D1D20] text-zinc-300'
              }`}
            >
              <div className="mb-1 flex items-center justify-between gap-2 text-[9.5px] uppercase tracking-wider font-extrabold">
                <span className={METHOD_STYLES[endpoint.method] || 'text-zinc-300'}>
                  {endpoint.method}
                </span>
                <span className={`text-[8.5px] px-1.5 py-0.2 rounded ${
                  endpoint.access === 'admin' 
                    ? 'text-rose-400 bg-rose-500/10' 
                    : endpoint.access === 'authenticated'
                    ? 'text-cyan-400 bg-cyan-500/10'
                    : 'text-zinc-500 bg-zinc-800'
                }`}>
                  {endpoint.access === 'authenticated' ? 'auth' : endpoint.access}
                </span>
              </div>

              <div className="truncate text-[11px] font-bold text-white font-mono">
                {endpoint.path}
              </div>
              <div className="mt-0.5 truncate text-[10.5px] text-zinc-400 font-sans">
                {endpoint.summary}
              </div>
            </button>
          );
        })
      )}
    </div>
  </aside>
);
