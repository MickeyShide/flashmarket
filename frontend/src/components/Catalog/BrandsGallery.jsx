import React, { useState } from 'react';
import { DEFAULT_BRAND_COVERS } from '../../config/constants';

export const BrandsGallery = ({ brandsData, onSelectBrand, activeCategoryId, activeBrandId }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  if (activeCategoryId || activeBrandId) return null; // Hidden when a category or brand filter is active

  if (!brandsData || brandsData.length === 0) {
    return (
      <div className="max-w-[1280px] mx-auto my-4 mb-6 px-4 md:px-6">
        <div className="text-text-muted text-sm">Загрузка брендов...</div>
      </div>
    );
  }

  const initialCount = 4; // Exactly 1 row on desktop
  const visibleBrands = isExpanded ? brandsData : brandsData.slice(0, initialCount);
  const hasMore = brandsData.length > initialCount;

  return (
    <div className="max-w-[1280px] mx-auto my-4 mb-6 md:mb-8 px-3.5 md:px-6">
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2.5 md:gap-4">
        {visibleBrands.map(brand => {
          const desc = brand.description || 'Коллекция эксклюзивных релизов бренда';
          const imgUrl = brand.logo_url || DEFAULT_BRAND_COVERS[brand.slug] || DEFAULT_BRAND_COVERS['flash-market'];
          const coverStyle = imgUrl
            ? { background: `linear-gradient(180deg, rgba(0,0,0,0.2) 0%, rgba(0,0,0,0.85) 100%), url('${imgUrl}') center/cover no-repeat` }
            : {};

          return (
            <div
              key={brand.id}
              className="group relative bg-[#0A0A0A] rounded-lg p-5 md:p-6 text-white overflow-hidden cursor-pointer flex flex-col justify-between min-h-[140px] md:min-h-[150px] border border-[#1F1F1F] transition-all duration-250 hover:-translate-y-1 hover:border-[#444444] hover:shadow-2xl"
              onClick={() => onSelectBrand(brand.id)}
            >
              {imgUrl && (
                <div className="absolute inset-0 z-0 transition-transform duration-500 group-hover:scale-105" style={coverStyle} />
              )}
              <div className="absolute inset-0 bg-radial-gradient from-white/10 to-transparent pointer-events-none z-10" />

              {/* Header inside card */}
              <div className="flex justify-end items-center z-20 relative">
                <div className="w-7 h-7 rounded-full bg-white/10 flex items-center justify-center transition-all duration-200 group-hover:bg-white group-hover:translate-x-0.5">
                  <svg className="w-3.5 h-3.5 stroke-white group-hover:stroke-black stroke-[2.5] fill-none" viewBox="0 0 24 24">
                    <line x1="5" y1="12" x2="19" y2="12"></line>
                    <polyline points="12 5 19 12 12 19"></polyline>
                  </svg>
                </div>
              </div>

              {/* Body inside card */}
              <div className="z-20 relative mt-4">
                <div className="text-[15px] md:text-[17px] font-black tracking-[1.5px] uppercase leading-tight mb-1">
                  {brand.name}
                </div>
                <div className="text-[11px] text-[#888888] tracking-wide truncate">
                  {desc}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {hasMore && (
        <div className="flex justify-center mt-3.5 md:mt-4">
          {!isExpanded ? (
            <button
              onClick={() => setIsExpanded(true)}
              className="px-5 py-2 rounded-full border border-gray-300 bg-white text-xs font-black tracking-wider uppercase text-black hover:border-black hover:bg-black hover:text-white transition-all shadow-sm flex items-center gap-1.5 cursor-pointer"
            >
              <span>Показать ещё ({brandsData.length - initialCount})</span>
              <svg className="w-3.5 h-3.5 stroke-current stroke-2 fill-none" viewBox="0 0 24 24">
                <polyline points="6 9 12 15 18 9"></polyline>
              </svg>
            </button>
          ) : (
            <button
              onClick={() => setIsExpanded(false)}
              className="px-4 py-1.5 rounded-full text-[11px] font-extrabold tracking-wider uppercase text-text-muted hover:text-black transition-colors cursor-pointer flex items-center gap-1"
            >
              <span>Свернуть</span>
              <svg className="w-3.5 h-3.5 stroke-current stroke-2 fill-none" viewBox="0 0 24 24">
                <polyline points="18 15 12 9 6 15"></polyline>
              </svg>
            </button>
          )}
        </div>
      )}
    </div>
  );
};
