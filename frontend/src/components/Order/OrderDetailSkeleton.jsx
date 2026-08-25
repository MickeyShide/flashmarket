import React from 'react';
import { Skeleton } from '../Common/Skeleton';

export const OrderDetailSkeleton = ({ onBack }) => {
  return (
    <div className="max-w-[800px] mx-auto my-6 md:my-8 px-3.5 md:px-6">
      {onBack ? (
        <button
          className="text-[11px] font-bold uppercase mb-6 cursor-pointer text-text-muted hover:text-black"
          onClick={onBack}
        >
          ← Назад к заказам
        </button>
      ) : (
        <Skeleton width={110} height={14} className="mb-6" />
      )}

      <div className="bg-white border border-border-color rounded-lg p-6 space-y-6">
        {/* Order Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border-color pb-4">
          <div className="flex-1">
            <Skeleton width={60} height={10} className="mb-2" />
            <Skeleton width="60%" height={22} className="mb-2" />
            <Skeleton width="40%" height={12} />
          </div>
          <Skeleton width={110} height={28} className="rounded self-start sm:self-center" />
        </div>

        {/* Info Grid (4 blocks) */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="bg-gray-50 p-3 rounded border border-border-color">
              <Skeleton width={50} height={10} className="mb-2" />
              <Skeleton width={70} height={16} />
            </div>
          ))}
        </div>

        {/* Dates */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="bg-gray-50 p-3 rounded border border-border-color">
            <Skeleton width={70} height={10} className="mb-2" />
            <Skeleton width={120} height={14} />
          </div>
          <div className="bg-gray-50 p-3 rounded border border-border-color">
            <Skeleton width={80} height={10} className="mb-2" />
            <Skeleton width={120} height={14} />
          </div>
        </div>

        {/* IDs */}
        <div className="space-y-2">
          <div className="bg-gray-50 p-3 rounded border border-border-color">
            <Skeleton width={60} height={10} className="mb-2" />
            <Skeleton width="80%" height={12} />
          </div>
        </div>

        {/* Payment Action Skeleton */}
        <div className="border-t border-border-color pt-4">
          <Skeleton width={100} height={12} className="mb-3" />
          <Skeleton width={220} height={46} className="rounded" />
        </div>
      </div>
    </div>
  );
};
