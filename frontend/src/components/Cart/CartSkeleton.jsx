import React from 'react';
import { Skeleton } from '../Common/Skeleton';

export const CartSkeleton = () => {
  return (
    <div className="space-y-4 mb-8">
      {[1, 2].map((i) => (
        <div
          key={i}
          className="p-4 border border-border-color rounded-lg bg-white flex flex-col sm:flex-row sm:items-center justify-between gap-4"
        >
          <div className="flex items-center gap-4 flex-1">
            <Skeleton width={56} height={56} className="rounded shrink-0" />
            <div className="flex-1">
              <Skeleton width="45%" height={14} className="mb-2" />
              <div className="flex items-center gap-2">
                <Skeleton width={80} height={10} />
                <Skeleton width={60} height={10} />
                <Skeleton width={50} height={10} />
              </div>
            </div>
          </div>

          <div className="flex items-center justify-between sm:justify-end gap-4 shrink-0">
            <Skeleton width={70} height={16} />
            <Skeleton width={24} height={24} className="rounded" />
          </div>
        </div>
      ))}
    </div>
  );
};
