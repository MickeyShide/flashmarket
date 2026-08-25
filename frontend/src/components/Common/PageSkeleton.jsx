import React from 'react';
import { Skeleton } from './Skeleton';

export const PageSkeleton = () => {
  return (
    <div className="max-w-[1280px] mx-auto my-6 md:my-8 px-3.5 md:px-6 w-full animate-fadeIn">
      {/* Top bar skeleton */}
      <div className="flex items-center justify-between mb-8">
        <Skeleton width={120} height={16} />
        <Skeleton width={80} height={16} />
      </div>

      {/* Main content grid skeleton */}
      <div className="space-y-6">
        <Skeleton width="40%" height={32} className="mb-4" />
        <Skeleton width="70%" height={14} className="mb-8" />

        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="flex flex-col items-center">
              <Skeleton className="w-full aspect-[3/4] rounded-lg mb-3" />
              <Skeleton width="60%" height={12} className="mb-2" />
              <Skeleton width="40%" height={12} />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
