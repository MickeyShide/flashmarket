import React from 'react';
import { Skeleton } from '../Common/Skeleton';

export const ProductDetailSkeleton = ({ onBack }) => {
  return (
    <div className="max-w-[1040px] mx-auto my-6 md:my-8 px-3.5 md:px-6">
      {/* Back button & Wishlist placeholder */}
      <div className="flex items-center justify-between mb-6">
        {onBack ? (
          <button
            className="text-[11px] font-bold uppercase tracking-wider cursor-pointer text-text-muted hover:text-black flex items-center gap-1"
            onClick={onBack}
          >
            ← Назад
          </button>
        ) : (
          <Skeleton width={60} height={14} />
        )}
        <Skeleton width={110} height={32} className="rounded-full" />
      </div>

      <div className="grid grid-cols-1 items-start gap-6 md:grid-cols-2 md:gap-9">
        {/* Left: Product gallery skeleton */}
        <div className="min-w-0">
          <div className="w-full h-[280px] md:h-[420px] rounded-lg overflow-hidden">
            <Skeleton className="w-full h-full" />
          </div>

          {/* Thumbnails row */}
          <div className="mt-3 flex flex-wrap gap-2">
            {[1, 2, 3, 4].map(i => (
              <Skeleton key={i} width={56} height={56} className="rounded-lg" />
            ))}
          </div>
        </div>

        {/* Right: Product Info skeleton */}
        <div className="flex min-w-0 flex-col justify-start">
          {/* Brand / Category */}
          <Skeleton width={140} height={12} className="mb-2" />

          {/* Title */}
          <Skeleton width="85%" height={28} className="mb-3" />

          {/* Price */}
          <Skeleton width={120} height={26} className="mb-5" />

          {/* Description lines */}
          <div className="space-y-2 mb-6">
            <Skeleton width="100%" height={12} />
            <Skeleton width="92%" height={12} />
            <Skeleton width="75%" height={12} />
          </div>

          {/* Sizes label & buttons */}
          <div className="mb-4">
            <Skeleton width={90} height={12} className="mb-2" />
            <div className="flex gap-2">
              {[1, 2, 3, 4].map(i => (
                <Skeleton key={i} width={48} height={40} className="rounded" />
              ))}
            </div>
          </div>

          {/* Stock Badge */}
          <Skeleton width={130} height={28} className="rounded mb-6" />

          {/* Add to Cart button */}
          <Skeleton width="100%" height={52} className="rounded" />
        </div>
      </div>
    </div>
  );
};
