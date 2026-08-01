import React, { useState, useEffect } from 'react';

export const CatalogControls = ({
  brandsData,
  activeBrandId,
  onSelectBrandSelect,
  activeSize,
  onSelectSize,
  priceFrom,
  priceTo,
  onPriceFromChange,
  onPriceToChange,
  activeSort,
  onSelectSort,
  onSearchChange
}) => {
  const [searchValue, setSearchValue] = useState('');

  useEffect(() => {
    const timer = setTimeout(() => {
      onSearchChange(searchValue.trim());
    }, 300);
    return () => clearTimeout(timer);
  }, [searchValue, onSearchChange]);

  const sizes = ['S', 'M', 'L', 'XL', 'OS'];

  return (
    <div className="max-w-[1280px] mx-auto my-4 md:my-6 px-3.5 md:px-6 flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3">
      {/* Left controls: Brand dropdown, Size dropdown, Sort dropdown */}
      <div className="flex flex-wrap items-center gap-2 md:gap-3">
        {/* Brand Dropdown Select */}
        <select
          className="font-mono text-[11px] font-extrabold tracking-wide uppercase px-3 py-[7px] bg-[#111111] text-white border border-[#333333] rounded cursor-pointer outline-none hover:border-black hover:bg-[#1A1A1A] transition-colors"
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

        <input
          type="number"
          min="0"
          placeholder="Цена от"
          className="w-24 font-mono text-[11px] px-3 py-[7px] bg-white border border-border-color rounded outline-none focus:border-black"
          value={priceFrom}
          onChange={(e) => onPriceFromChange(e.target.value)}
        />
        <input
          type="number"
          min="0"
          placeholder="Цена до"
          className="w-24 font-mono text-[11px] px-3 py-[7px] bg-white border border-border-color rounded outline-none focus:border-black"
          value={priceTo}
          onChange={(e) => onPriceToChange(e.target.value)}
        />

        {/* Size Filter Dropdown */}
        <select
          className="font-mono text-[11px] font-extrabold tracking-wide uppercase px-3 py-[7px] bg-white text-black border border-border-color rounded cursor-pointer outline-none hover:border-black transition-colors"
          value={activeSize || ''}
          onChange={(e) => onSelectSize(e.target.value || null)}
        >
          <option value="">Размер: Все</option>
          {sizes.map(sz => (
            <option key={sz} value={sz}>
              {sz}
            </option>
          ))}
        </select>

        {/* Sort Dropdown */}
        <select
          className="font-mono text-[11px] font-extrabold tracking-wide uppercase px-3 py-[7px] bg-white text-black border border-border-color rounded cursor-pointer outline-none hover:border-black transition-colors"
          value={activeSort || 'created_at'}
          onChange={(e) => onSelectSort(e.target.value)}
        >
          <option value="created_at">По новизне</option>
          <option value="price_asc">По цене (сначала дешевле)</option>
          <option value="price_desc">По цене (сначала дороже)</option>
          {searchValue && <option value="relevance">По релевантности</option>}
        </select>
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
