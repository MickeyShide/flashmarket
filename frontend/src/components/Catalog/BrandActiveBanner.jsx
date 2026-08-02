import React from 'react';

export const BrandActiveBanner = ({ activeBrand, resetBrandFilter, activeCategory, resetCategoryFilter }) => {
  if (!activeBrand && !activeCategory) return null;

  return (
    <div className="max-w-[1280px] mx-auto my-3 md:my-4 px-3.5 md:px-6 flex flex-col gap-3">
      {activeCategory && (
        <div className="bg-[#0A0A0A] text-white rounded-lg p-4 md:p-5 flex items-center justify-between gap-4 border border-[#1F1F1F] shadow-lg">
          <div>
            <div className="font-mono text-[9px] tracking-[1.5px] text-accent-lime uppercase font-bold mb-1">
              КАТАЛОГ // КАТЕГОРИЯ
            </div>
            <div className="text-[18px] md:text-[20px] font-black tracking-[1.5px] uppercase leading-tight">
              {activeCategory.name.toUpperCase()}
            </div>
            <div className="text-[11px] text-[#888888] mt-0.5">
              {activeCategory.description || `Товары в категории «${activeCategory.name}».`}
            </div>
          </div>
          <button
            className="inline-flex items-center gap-1.5 bg-white/10 text-white border border-white/15 px-3.5 py-2 rounded-full text-[10px] font-extrabold tracking-wider uppercase cursor-pointer whitespace-nowrap hover:bg-white hover:text-black hover:border-white transition-colors shrink-0"
            onClick={resetCategoryFilter}
          >
            <span>✕</span> Сбросить категорию
          </button>
        </div>
      )}

      {activeBrand && (
        <div className="bg-[#0A0A0A] text-white rounded-lg p-4 md:p-5 flex items-center justify-between gap-4 border border-[#1F1F1F] shadow-lg">
          <div>
            <div className="font-mono text-[9px] tracking-[1.5px] text-accent-lime uppercase font-bold mb-1">
              КАТАЛОГ // БРЕНД
            </div>
            <div className="text-[18px] md:text-[20px] font-black tracking-[1.5px] uppercase leading-tight">
              {activeBrand.name.toUpperCase()}
            </div>
            <div className="text-[11px] text-[#888888] mt-0.5">
              {activeBrand.description || `Коллекция бренда «${activeBrand.name}».`}
            </div>
          </div>
          <button
            className="inline-flex items-center gap-1.5 bg-white/10 text-white border border-white/15 px-3.5 py-2 rounded-full text-[10px] font-extrabold tracking-wider uppercase cursor-pointer whitespace-nowrap hover:bg-white hover:text-black hover:border-white transition-colors shrink-0"
            onClick={resetBrandFilter}
          >
            <span>✕</span> Сбросить бренд
          </button>
        </div>
      )}
    </div>
  );
};
