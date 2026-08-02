import React from 'react';
import { useInfiniteScroll } from '../../hooks/useInfiniteScroll';

const DEFAULT_BUTTON_CLASS = 'bg-black text-white px-8 py-3 rounded text-[11px] font-black tracking-[1.5px] uppercase cursor-pointer hover:bg-gray-900 disabled:opacity-50 transition-colors';

export const InfiniteScrollTrigger = ({
  hasMore,
  loading,
  error,
  onLoadMore,
  showButton = false,
  className = 'text-center mt-6',
  buttonClassName = DEFAULT_BUTTON_CLASS,
  loadingLabel = 'ЗАГРУЗКА...'
}) => {
  const sentinelRef = useInfiniteScroll({
    hasMore: hasMore && !error,
    isLoading: loading,
    onLoadMore
  });

  if (!hasMore && !loading) return null;

  const buttonVisible = showButton || Boolean(error);

  return (
    <div ref={sentinelRef} className={className} aria-busy={loading}>
      {loading && !showButton && <div className="spinner" aria-label="Загрузка" />}
      {hasMore && (showButton || !loading) && (
        <button
          type="button"
          className={buttonVisible ? buttonClassName : 'sr-only focus:not-sr-only'}
          disabled={loading}
          onClick={onLoadMore}
        >
          {loading ? loadingLabel : (error ? 'ПОВТОРИТЬ ЗАГРУЗКУ' : 'ЗАГРУЗИТЬ ЕЩЁ')}
        </button>
      )}
    </div>
  );
};
