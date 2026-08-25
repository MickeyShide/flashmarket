/**
 * Prefetch & In-Memory Cache Service
 * Handles data prefetching and lazy chunk preloading on hover/focus.
 */

const PREFETCH_TTL_MS = 30000; // 30 seconds cache TTL
const prefetchCache = new Map(); // key -> { data, timestamp, promise }
const preloadedChunks = new Set();

// Chunk loaders mapping
const chunkLoaders = {
  product: () => import('../components/Product/ProductDetail'),
  'drop-detail': () => import('../components/Drops/DropDetail'),
  categories: () => import('../components/Catalog/CategoriesView'),
  cart: () => import('../components/Cart/CartView'),
  checkout: () => import('../components/Checkout/CheckoutView'),
  auth: () => import('../components/Profile/ProfileView'),
  'order-detail': () => import('../components/Order/OrderDetailView'),
  admin: () => import('../components/Admin/AdminView'),
};

/**
 * Preload a lazy React component chunk
 */
export function prefetchViewChunk(viewName) {
  if (preloadedChunks.has(viewName)) return;
  const loader = chunkLoaders[viewName];
  if (loader) {
    preloadedChunks.add(viewName);
    loader().catch(() => {
      preloadedChunks.delete(viewName);
    });
  }
}

/**
 * Get cached prefetch entry if valid and not expired
 */
export function getPrefetchEntry(path) {
  const entry = prefetchCache.get(path);
  if (!entry) return null;

  // In-flight promise
  if (entry.promise) {
    return entry.promise;
  }

  // Check TTL
  if (Date.now() - entry.timestamp > PREFETCH_TTL_MS) {
    prefetchCache.delete(path);
    return null;
  }

  return Promise.resolve(entry.data);
}

/**
 * Store data or promise into prefetch cache
 */
export function setPrefetchEntry(path, { data, promise }) {
  if (promise) {
    prefetchCache.set(path, {
      promise: promise
        .then((res) => {
          prefetchCache.set(path, { data: res, timestamp: Date.now() });
          return res;
        })
        .catch((err) => {
          prefetchCache.delete(path);
          throw err;
        }),
      timestamp: Date.now(),
    });
    return;
  }

  prefetchCache.set(path, { data, timestamp: Date.now() });
}

/**
 * Invalidate a specific path or paths matching a regex/prefix
 */
export function invalidatePrefetch(pattern) {
  if (!pattern) {
    prefetchCache.clear();
    return;
  }

  if (typeof pattern === 'string') {
    prefetchCache.delete(pattern);
    return;
  }

  if (pattern instanceof RegExp) {
    for (const key of prefetchCache.keys()) {
      if (pattern.test(key)) {
        prefetchCache.delete(key);
      }
    }
  }
}

/**
 * Low-level data prefetch helper
 */
export function prefetchData(path, fetchFn) {
  if (!path) return Promise.resolve(null);

  const existing = getPrefetchEntry(path);
  if (existing) return existing;

  const promise = fetchFn(path);
  setPrefetchEntry(path, { promise });
  return promise;
}

/**
 * Entity Prefetchers
 */

export function prefetchProduct(slug, apiJsonFn) {
  if (!slug) return;
  prefetchViewChunk('product');
  if (apiJsonFn) {
    const url = `/api/v1/products/${encodeURIComponent(slug)}`;
    prefetchData(url, () => apiJsonFn(url));
  }
}

export function prefetchDrop(identifier, apiJsonFn) {
  if (!identifier) return;
  prefetchViewChunk('drop-detail');
  if (apiJsonFn) {
    const isUuid = /^[0-9a-fA-F-]{36}$/.test(identifier);
    const url = isUuid
      ? `/api/v1/drops/id/${identifier}`
      : `/api/v1/drops/${encodeURIComponent(identifier)}`;
    prefetchData(url, () => apiJsonFn(url));
  }
}

export function prefetchCategories(apiJsonFn) {
  prefetchViewChunk('categories');
  if (apiJsonFn) {
    prefetchData('/api/v1/categories', () => apiJsonFn('/api/v1/categories'));
  }
}

export function prefetchOrder(orderId, apiJsonFn) {
  if (!orderId) return;
  prefetchViewChunk('order-detail');
  if (apiJsonFn) {
    const url = `/api/v1/orders/${orderId}`;
    prefetchData(url, () => apiJsonFn(url));
  }
}

export function prefetchCart() {
  prefetchViewChunk('cart');
  prefetchViewChunk('checkout');
}

export function prefetchProfile() {
  prefetchViewChunk('auth');
}

export function prefetchAdmin() {
  prefetchViewChunk('admin');
}
