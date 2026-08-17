import React from 'react';

const METHOD_STYLES = {
  GET: 'text-[#2E7D32] bg-[#E8F5E9] border-[#C8E6C9]',
  POST: 'text-[#1565C0] bg-[#E3F2FD] border-[#BBDEFB]',
  PUT: 'text-[#E65100] bg-[#FFF3E0] border-[#FFE0B2]',
  PATCH: 'text-[#E65100] bg-[#FFF3E0] border-[#FFE0B2]',
  DELETE: 'text-[#C62828] bg-[#FFEBEE] border-[#FFCDD2]',
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
  <aside className="flex h-[700px] flex-col border-b border-border-color bg-[#FAFAFA] font-mono lg:border-b-0 lg:border-r">
    {/* Search & Filters Header */}
    <div className="space-y-2.5 border-b border-border-color p-3.5 bg-white">
      {/* Search Input */}
      <div className="relative">
        <input
          value={searchQuery}
          onChange={(event) => onSearchChange(event.target.value)}
          placeholder="Поиск по маршруту или описанию..."
          className="w-full border border-border-color bg-white px-3 py-2 text-[11px] text-black outline-none placeholder:text-text-muted focus:border-black rounded-sm font-sans"
        />
        {searchQuery && (
          <button
            onClick={() => onSearchChange('')}
            className="absolute right-2.5 top-2 text-text-muted hover:text-black text-xs font-bold cursor-pointer"
          >
            ✕
          </button>
        )}
      </div>

      {/* Service Dropdown Select */}
      <select
        value={serviceFilter || ''}
        onChange={(event) => onServiceFilterChange(event.target.value || null)}
        className="w-full border border-border-color bg-white px-3 py-1.5 text-[10px] uppercase tracking-wider text-black outline-none focus:border-black rounded-sm cursor-pointer font-mono"
      >
        <option value="">Все сервисы ({services.length})</option>
        {services.map((service) => (
          <option key={service.id} value={service.id}>
            {service.name} ({service.operationCount})
          </option>
        ))}
      </select>

      {/* Access Category Filter Chips */}
      <div className="grid grid-cols-4 gap-1 p-1 bg-[#F5F5F5] border border-border-color rounded-sm">
        {['all', 'anonymous', 'authenticated', 'admin'].map((filter) => {
          const isActive = accessFilter === filter;
          return (
            <button
              key={filter}
              onClick={() => onAccessFilterChange(filter)}
              title={filter}
              className={`py-1 text-[8.5px] uppercase font-black tracking-wider rounded-sm transition-colors text-center truncate cursor-pointer ${
                isActive ? 'bg-black text-[#BFF532]' : 'text-text-muted hover:text-black hover:bg-white'
              }`}
            >
              {filter === 'authenticated' ? 'auth' : filter === 'anonymous' ? 'public' : filter}
            </button>
          );
        })}
      </div>
    </div>

    {/* Endpoint List */}
    <div className="flex-1 overflow-y-auto divide-y divide-border-color bg-[#FAFAFA]">
      {endpoints.length === 0 ? (
        <p className="p-6 text-xs text-text-muted text-center font-sans">
          Операции по заданным фильтрам не найдены.
        </p>
      ) : (
        endpoints.map((endpoint) => {
          const isSelected = selectedEndpointId === endpoint.id;
          const methodClass = METHOD_STYLES[endpoint.method] || 'text-zinc-800 bg-zinc-100 border-zinc-200';

          return (
            <button
              key={endpoint.id}
              onClick={() => onSelectEndpoint(endpoint.id)}
              className={`block w-full px-3.5 py-3 text-left transition-colors focus:outline-none cursor-pointer ${
                isSelected
                  ? 'bg-white border-l-4 border-black text-black shadow-xs'
                  : 'hover:bg-white text-zinc-700'
              }`}
            >
              <div className="mb-1 flex items-center justify-between gap-2 text-[9.5px] uppercase tracking-wider font-extrabold">
                <span className={`px-1.5 py-0.5 rounded-sm border font-mono ${methodClass}`}>
                  {endpoint.method}
                </span>
                <span className={`text-[8.5px] px-1.5 py-0.5 rounded-sm border font-mono ${
                  endpoint.access === 'admin' 
                    ? 'text-red-700 bg-red-50 border-red-200' 
                    : endpoint.access === 'authenticated'
                    ? 'text-blue-700 bg-blue-50 border-blue-200'
                    : 'text-zinc-600 bg-zinc-100 border-zinc-200'
                }`}>
                  {endpoint.access === 'authenticated' ? 'auth' : endpoint.access}
                </span>
              </div>

              <div className="truncate text-[11px] font-bold text-black font-mono">
                {endpoint.path}
              </div>
              <div className="mt-0.5 truncate text-[10.5px] text-text-muted font-sans">
                {endpoint.summary}
              </div>
            </button>
          );
        })
      )}
    </div>
  </aside>
);

