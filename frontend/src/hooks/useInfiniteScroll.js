import { useEffect, useRef } from 'react';

export const observeInfiniteScroll = ({
  target,
  hasMore,
  isLoading,
  onLoadMore,
  rootMargin = '400px 0px'
}) => {
  if (
    !target ||
    !hasMore ||
    isLoading ||
    typeof globalThis.IntersectionObserver !== 'function'
  ) {
    return () => {};
  }

  let requested = false;
  const observer = new globalThis.IntersectionObserver((entries) => {
    if (entries.some(entry => entry.isIntersecting) && !requested) {
      requested = true;
      try {
        Promise.resolve(onLoadMore()).finally(() => {
          requested = false;
        });
      } catch (e) {
        requested = false;
      }
    }
  }, { rootMargin });

  observer.observe(target);
  return () => observer.disconnect();
};

export const useInfiniteScroll = ({
  hasMore,
  isLoading,
  onLoadMore,
  rootMargin = '400px 0px'
}) => {
  const sentinelRef = useRef(null);
  const onLoadMoreRef = useRef(onLoadMore);

  useEffect(() => {
    onLoadMoreRef.current = onLoadMore;
  }, [onLoadMore]);

  useEffect(() => observeInfiniteScroll({
    target: sentinelRef.current,
    hasMore,
    isLoading,
    onLoadMore: () => onLoadMoreRef.current(),
    rootMargin
  }), [hasMore, isLoading, rootMargin]);

  return sentinelRef;
};
