import { useCallback, useEffect, useRef, useState } from 'react';

export const mergeUniqueByKey = (current, incoming, getKey = item => item.id) => {
  const seen = new Set(current.map(getKey));
  return [
    ...current,
    ...incoming.filter(item => {
      const key = getKey(item);
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    })
  ];
};

export const normalizePage = (data, offset = 0) => {
  const items = Array.isArray(data) ? data : (data?.items || []);
  return {
    items,
    total: Array.isArray(data) ? offset + items.length : (data?.total ?? offset + items.length)
  };
};

export const usePaginatedResource = ({ fetchPage, pageSize = 25, getKey = item => item.id }) => {
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState(null);

  const fetchPageRef = useRef(fetchPage);
  const getKeyRef = useRef(getKey);
  const generationRef = useRef(0);
  const requestRef = useRef(null);
  const nextOffsetRef = useRef(0);
  const exhaustedRef = useRef(false);
  const itemsRef = useRef([]);

  useEffect(() => {
    fetchPageRef.current = fetchPage;
  }, [fetchPage]);

  useEffect(() => {
    getKeyRef.current = getKey;
  }, [getKey]);

  useEffect(() => () => requestRef.current?.controller.abort(), []);

  const requestPage = useCallback(async (replace) => {
    if (!replace && requestRef.current) return false;

    if (replace) {
      generationRef.current += 1;
      requestRef.current?.controller.abort();
      nextOffsetRef.current = 0;
      exhaustedRef.current = false;
      itemsRef.current = [];
      setItems([]);
      setTotal(0);
      setError(null);
      setLoading(true);
      setLoadingMore(false);
    } else {
      setLoadingMore(true);
      setError(null);
    }

    const generation = generationRef.current;
    const offset = replace ? 0 : nextOffsetRef.current;
    const controller = new AbortController();
    const request = { controller, generation };
    requestRef.current = request;

    try {
      const data = await fetchPageRef.current({
        limit: pageSize,
        offset,
        signal: controller.signal
      });
      if (generation !== generationRef.current) return false;

      const page = normalizePage(data, offset);
      const nextItems = replace
        ? page.items
        : mergeUniqueByKey(itemsRef.current, page.items, getKeyRef.current);
      itemsRef.current = nextItems;
      setItems(nextItems);
      setTotal(page.total);
      nextOffsetRef.current = offset + pageSize;
      exhaustedRef.current = page.items.length === 0 || nextItems.length >= page.total;
      return true;
    } catch (requestError) {
      if (requestError.name !== 'AbortError' && generation === generationRef.current) {
        setError(requestError);
      }
      return false;
    } finally {
      if (requestRef.current === request) {
        requestRef.current = null;
        setLoading(false);
        setLoadingMore(false);
      }
    }
  }, [pageSize]);

  const reload = useCallback(() => requestPage(true), [requestPage]);
  const loadMore = useCallback(() => {
    if (exhaustedRef.current || requestRef.current) return Promise.resolve(false);
    return requestPage(false);
  }, [requestPage]);

  return {
    items,
    total,
    loading,
    loadingMore,
    error,
    hasMore: !exhaustedRef.current && items.length < total,
    reload,
    loadMore
  };
};
