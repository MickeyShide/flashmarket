import React from 'react';
import { Skeleton } from '../Common/Skeleton';
import { ProductGridSkeleton } from '../Catalog/ProductGridSkeleton';

export const DropDetailSkeleton = ({ onBack }) => {
  return (
    <div className="max-w-[1280px] mx-auto my-6 md:my-8 px-3.5 md:px-6">
      {onBack ? (
        <button
          className="text-[11px] font-bold uppercase tracking-wider mb-6 cursor-pointer text-text-muted hover:text-black flex items-center gap-1"
          onClick={onBack}
        >
          ← Назад
        </button>
      ) : (
        <Skeleton width={60} height={14} className="mb-6" />
      )}

      {/* Hero Drop Header Banner */}
      <div className="bg-black text-white rounded-lg p-6 md:p-10 mb-8 relative overflow-hidden flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div className="z-10 max-w-2xl w-full">
          <div className="flex items-center gap-2 mb-3">
            <Skeleton width={90} height={20} className="bg-white/20" />
            <Skeleton width={110} height={20} className="bg-white/20" />
          </div>

          <Skeleton width="60%" height={32} className="bg-white/20 mb-3" />
          <Skeleton width="90%" height={14} className="bg-white/20 mb-2" />
          <Skeleton width="70%" height={14} className="bg-white/20" />
        </div>

        <div className="z-10 bg-white/10 rounded-lg p-4 flex flex-col items-center shrink-0 w-36">
          <Skeleton width={80} height={12} className="bg-white/20 mb-2" />
          <Skeleton width={100} height={24} className="bg-white/20" />
        </div>
      </div>

      {/* Drop Products Grid */}
      <div className="mb-6 flex items-center justify-between">
        <Skeleton width={200} height={20} />
      </div>

      <ProductGridSkeleton count={4} />
    </div>
  );
};
