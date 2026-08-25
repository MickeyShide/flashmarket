import React from 'react';
import { Skeleton } from '../Common/Skeleton';

export const OrdersTabSkeleton = () => {
  return (
    <div className="space-y-3">
      {[1, 2, 3].map((i) => (
        <div
          key={i}
          className="p-4 bg-white border border-border-color rounded-lg flex flex-col sm:flex-row sm:items-center justify-between gap-3"
        >
          <div className="flex-1">
            <Skeleton width="50%" height={14} className="mb-2" />
            <Skeleton width="75%" height={11} className="mb-1" />
            <Skeleton width="30%" height={10} />
          </div>

          <div className="flex items-center gap-3 self-end sm:self-center">
            <Skeleton width={90} height={24} className="rounded" />
          </div>
        </div>
      ))}
    </div>
  );
};
