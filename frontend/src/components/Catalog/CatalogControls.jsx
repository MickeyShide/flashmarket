import React, { useState, useEffect } from 'react';

export const CatalogControls = ({
  brandsData,
  activeBrandId,
  onSelectBrandSelect,
  activeStatus,
  onFilterStatus,
  onSearchChange
}) => {
  const [searchValue, setSearchValue] = useState('');

  useEffect(() => {
    const timer = setTimeout(() => {
      onSearchChange(searchValue.trim());
    }, 300);
    return () => clearTimeout(timer);
  }, [searchValue, onSearchChange]);

  const statuses = [
    { label: 'Все', value: null },
    { label: 'ACTIVE', value: 'ACTIVE' },
    { label: 'HIDDEN', value: 'HIDDEN' },
    { label: 'ARCHIVED', value: 'ARCHIVED' },
  ];

  return (
    <div className="max-w-[1280px] mx-auto my-4 md:my-6 px-3.5 md:px-6 flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3">
      {/* Left controls: Brand dropdown & Status Chips */}
      <div className="flex flex-wrap items-center gap-2 md:gap-3">
        {/* Brand Dropdown Select */}
        <select
          className="font-mono text-[11px] font-extrabold tracking-wide uppercase px-3 py-[7px] bg-[#111111] text-white border border-[#333333] rounded cursor-pointer outline-none hover:border-accent-lime hover:bg-[#1A1A1A] transition-colors"
          value={activeBrandId || ''}
          onChange={(e) => onSelectBrandSelect(e.target.value || null)}
        >
          <option value="">Бренд: Все</option>
          {brandsData.map(b => (
            <option key={b.id} value={b.id}>
              {b.name}
            </option>
          ))}
        </select>

        {/* Status Filter Chips */}
        <div className="flex items-center gap-1.5 overflow-x-auto py-0.5 no-scrollbar">
          {statuses.map((st, idx) => (
            <button
              key={idx}
              className={`px-3 py-[7px] rounded-full border text-[10.5px] font-extrabold tracking-wide uppercase whitespace-nowrap shrink-0 cursor-pointer transition-colors ${
                (activeStatus === st.value)
                  ? 'bg-black text-white border-black'
                  : 'bg-white text-text-muted border-border-color hover:text-black'
              }`}
              onClick={() => onFilterStatus(st.value)}
            >
              {st.label}
            </button>
          ))}
        </div>
      </div>

      {/* Right control: Search Input */}
      <div className="flex items-center bg-[#F9F9F9] border border-border-color rounded-full px-3.5 py-[7px] w-full md:w-[240px]">
        <input
          type="text"
          placeholder="Поиск по названию..."
          className="border-none outline-none bg-transparent w-full text-[11.5px] font-sans"
          value={searchValue}
          onChange={(e) => setSearchValue(e.target.value)}
        />
        {searchValue && (
          <button
            className="text-text-muted hover:text-black text-xs font-bold px-1"
            onClick={() => setSearchValue('')}
          >
            ✕
          </button>
        )}
      </div>
    </div>
  );
};
