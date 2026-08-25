import React from 'react';
import { ProductCardSkeleton } from './ProductCardSkeleton';

export const ProductGridSkeleton = ({ count = 8 }) => {
  const items = Array.from({ length: count }, (_, i) => i);

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-y-7 gap-x-2.5 md:gap-x-4.5">
      {items.map(index => (
        <ProductCardSkeleton key={index} />
      ))}
    </div>
  );
};
