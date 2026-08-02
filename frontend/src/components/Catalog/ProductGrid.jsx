import React from 'react';
import { ProductCard } from './ProductCard';
import { InfiniteScrollTrigger } from '../Common/InfiniteScrollTrigger';

export const ProductGrid = ({
  productsList,
  loading,
  error,
  onRetry,
  onOpenProduct,
  hasMore,
  loadingMore,
  loadMoreError,
  onLoadMore
}) => {
  return (
    <div className="max-w-[1280px] mx-auto px-3.5 md:px-6 pb-12 md:pb-16">
      {loading ? (
        <div className="spinner"></div>
      ) : error ? (
        <div className="bg-red-50 border border-red-200 text-red-700 p-6 rounded-lg text-center my-6">
          <div className="mb-3 font-semibold">Ошибка загрузки каталога: {error}</div>
          <button
            className="bg-black text-white text-xs font-bold uppercase px-4 py-2 rounded hover:bg-gray-800"
            onClick={onRetry}
          >
            Повторить
          </button>
        </div>
      ) : productsList.length === 0 ? (
        <div className="text-center py-16 text-text-muted font-bold text-sm uppercase tracking-wider">
          Товары не найдены
        </div>
      ) : (
        <>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-y-7 gap-x-2.5 md:gap-x-4.5">
            {productsList.map((p, index) => (
              <ProductCard
                key={p.id}
                product={p}
                eager={index < 4}
                onClick={() => onOpenProduct(p.slug)}
              />
            ))}
          </div>

          <InfiniteScrollTrigger
            hasMore={hasMore}
            loading={loadingMore}
            error={loadMoreError}
            onLoadMore={onLoadMore}
            showButton
            className="text-center mt-10"
          />
        </>
      )}
    </div>
  );
};
