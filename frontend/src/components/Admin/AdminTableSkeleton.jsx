import React from 'react';
import { Skeleton } from '../Common/Skeleton';

export const AdminTableSkeleton = ({ rows = 5 }) => {
  const items = Array.from({ length: rows }, (_, i) => i);

  return (
    <div className="bg-white border border-border-color rounded-lg overflow-hidden p-4 space-y-3">
      <div className="flex items-center justify-between pb-3 border-b border-border-color">
        <Skeleton width={140} height={16} />
        <Skeleton width={80} height={32} className="rounded" />
      </div>

      <div className="space-y-2.5">
        {items.map(i => (
          <div
            key={i}
            className="flex items-center justify-between p-3 bg-gray-50 rounded border border-border-color"
          >
            <div className="flex items-center gap-3 flex-1">
              <Skeleton width={40} height={40} className="rounded shrink-0" />
              <div className="flex-1 space-y-1.5">
                <Skeleton width="40%" height={14} />
                <Skeleton width="60%" height={10} />
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Skeleton width={60} height={20} className="rounded" />
              <Skeleton width={32} height={32} className="rounded" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
