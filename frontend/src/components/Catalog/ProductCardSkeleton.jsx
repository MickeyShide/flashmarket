import React from 'react';
import { Skeleton } from '../Common/Skeleton';

export const ProductCardSkeleton = () => {
  return (
    <div className="flex flex-col items-center text-center w-full">
      {/* Thumbnail Box */}
      <div className="w-full aspect-[3/4] max-h-[320px] bg-gray-100 rounded flex items-center justify-center relative mb-3 overflow-hidden">
        <Skeleton className="w-full h-full" />
      </div>

      {/* Brand Subtitle placeholder */}
      <div className="w-20 mb-1">
        <Skeleton variant="text" height={10} className="w-full mx-auto" />
      </div>

      {/* Product Title placeholder */}
      <div className="w-3/4 mb-1.5">
        <Skeleton variant="text" height={13} className="w-full mx-auto" />
      </div>

      {/* Price placeholder */}
      <div className="w-16">
        <Skeleton variant="text" height={14} className="w-full mx-auto" />
      </div>
    </div>
  );
};
