import React from 'react';
import { Skeleton } from '../Common/Skeleton';

export const DropCardSkeleton = () => {
  return (
    <div className="bg-white border border-border-color rounded-lg overflow-hidden flex flex-col justify-between">
      {/* Banner / Cover */}
      <div className="w-full h-44 bg-gray-100 relative p-3">
        <Skeleton className="w-full h-full" />
      </div>

      {/* Info content */}
      <div className="p-4 flex flex-col flex-1 justify-between">
        <div>
          <Skeleton width="70%" height={16} className="mb-2" />
          <Skeleton width="100%" height={12} className="mb-1" />
          <Skeleton width="60%" height={12} className="mb-3" />
        </div>

        <div className="pt-2 border-t border-gray-100 flex items-center justify-between">
          <Skeleton width={70} height={10} />
          <Skeleton width={90} height={12} />
        </div>
      </div>
    </div>
  );
};
